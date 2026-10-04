//! Observe native user intent independently of whether the extension starts.
use gio::{glib, prelude::*};
use std::time::Duration;
use tokio::sync::watch;

const UUID: &str = "convertibled@convertibled.org";

fn expected(enabled: &glib::StrV, disabled: &glib::StrV, suspended: bool) -> Option<bool> {
    if enabled.len() > 512 || disabled.len() > 512 {
        return None;
    }
    Some(!suspended && enabled.iter().any(|id| id == UUID) && !disabled.iter().any(|id| id == UUID))
}

fn observe(sender: watch::Sender<Option<bool>>) {
    // dconf notifications use a GLib context, kept off the async service loop.
    let context = glib::MainContext::new();
    let _ = context.with_thread_default(|| {
        let Some(schema) = gio::SettingsSchemaSource::default()
            .and_then(|source| source.lookup("org.gnome.shell", true))
        else {
            return;
        };
        for (name, signature) in [
            ("enabled-extensions", "as"),
            ("disabled-extensions", "as"),
            ("disable-user-extensions", "b"),
        ] {
            if !schema.has_key(name) || schema.key(name).value_type().as_str() != signature {
                return;
            }
        }
        let settings = gio::Settings::new_full(&schema, gio::SettingsBackend::NONE, None);
        let publish = move |settings: &gio::Settings| {
            sender.send_replace(expected(
                &settings.strv("enabled-extensions"),
                &settings.strv("disabled-extensions"),
                settings.boolean("disable-user-extensions"),
            ));
        };
        publish(&settings);
        settings.connect_changed(None, move |settings, _| publish(settings));
        glib::MainLoop::new(Some(&context), false).run();
    });
}

pub async fn report(system: zbus::Connection) {
    let (sender, mut receiver) = watch::channel(None);
    if std::thread::Builder::new()
        .name("gnome-intent".into())
        .spawn(move || observe(sender))
        .is_err()
    {
        return;
    }
    // Retry after unlock, daemon restart or a transient bus failure. Unknown is
    // explicitly reported, never converted into permission to skip Shell health.
    let mut retry = tokio::time::interval(Duration::from_secs(5));
    let mut changes_open = true;
    loop {
        tokio::select! { _ = retry.tick() => {}, changed = receiver.changed(), if changes_open => {
            changes_open = changed.is_ok();
        }}
        let intent = if changes_open {
            *receiver.borrow_and_update()
        } else {
            None
        };
        let _ = tokio::time::timeout(Duration::from_secs(3), async {
            let proxy = zbus::Proxy::new(
                &system,
                "org.convertibled.Daemon1",
                "/org/convertibled/Daemon1",
                "org.convertibled.Daemon1",
            )
            .await?;
            proxy
                .call::<_, _, ()>(
                    "ReportShellExpectation",
                    &(
                        env!("CARGO_PKG_VERSION"),
                        intent.is_some(),
                        intent.unwrap_or(false),
                    ),
                )
                .await
        })
        .await;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn native_enablement_respects_explicit_and_global_disabling() {
        let own = glib::StrV::from([UUID]);
        let empty = glib::StrV::default();
        assert_eq!(expected(&own, &empty, false), Some(true));
        assert_eq!(expected(&own, &own, false), Some(false));
        assert_eq!(expected(&own, &empty, true), Some(false));
        assert_eq!(expected(&empty, &empty, false), Some(false));
        assert_eq!(
            expected(&glib::StrV::from(vec![UUID; 513]), &empty, false),
            None
        );
    }
}
