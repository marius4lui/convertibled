use crate::{operations::helper, strings::Strings};
use adw::prelude::*;
use gtk::glib;

pub fn group(text: Strings) -> adw::PreferencesGroup {
    let group = adw::PreferencesGroup::builder()
        .title(text.text("Update preferences", "Update-Einstellungen"))
        .description(text.text("Preview is optional. Changing these system preferences requires authorization.",
            "Preview ist optional. Änderungen an diesen Systemeinstellungen erfordern eine Autorisierung.")).build();
    let automatic = adw::SwitchRow::builder()
        .title(text.text(
            "Automatically check and prepare",
            "Automatisch prüfen und vorbereiten",
        ))
        .build();
    let channel = adw::ComboRow::builder()
        .title(text.text("Channel", "Kanal"))
        .model(&gtk::StringList::new(&["Stable", "Preview"]))
        .build();
    let save = gtk::Button::with_label(text.text("Save", "Speichern"));
    save.set_height_request(44);
    save.set_sensitive(false);
    group.set_header_suffix(Some(&save));
    let status = adw::ActionRow::builder()
        .title(text.text("Preferences status", "Einstellungsstatus"))
        .subtitle(text.text("Loading…", "Wird geladen…"))
        .build();
    group.add(&automatic);
    group.add(&channel);
    group.add(&status);
    let automatic_copy = automatic.clone();
    let channel_copy = channel.clone();
    let status_copy = status.clone();
    save.connect_clicked(move |button| {
        let button = button.clone();
        let automatic = automatic_copy.clone();
        let channel = channel_copy.clone();
        let status = status_copy.clone();
        button.set_sensitive(false);
        automatic.set_sensitive(false);
        channel.set_sensitive(false);
        glib::MainContext::default().spawn_local(async move {
            let desired_auto = automatic.is_active();
            let desired_channel = if channel.selected() == 1 {
                "preview"
            } else {
                "stable"
            };
            let result: Result<(), String> = async {
                let current = helper("status", None).await?;
                if current["preferences"]["automatic_updates"].as_bool() != Some(desired_auto) {
                    helper("automatic", Some(if desired_auto { "on" } else { "off" })).await?;
                }
                if current["preferences"]["channel"].as_str() != Some(desired_channel) {
                    helper("channel", Some(desired_channel)).await?;
                }
                Ok(())
            }
            .await;
            status.set_subtitle(&match result {
                Ok(()) => text
                    .text("Preferences saved.", "Einstellungen gespeichert.")
                    .into(),
                Err(error) => error,
            });
            // Re-read after partial failure as one preference may have succeeded.
            if let Ok(current) = helper("status", None).await {
                automatic.set_active(
                    current["preferences"]["automatic_updates"]
                        .as_bool()
                        .unwrap_or(false),
                );
                channel.set_selected(u32::from(current["preferences"]["channel"] == "preview"));
            }
            automatic.set_sensitive(true);
            channel.set_sensitive(true);
            button.set_sensitive(true);
        });
    });
    glib::MainContext::default().spawn_local(async move {
        match helper("status", None).await {
            Ok(current) if current["preferences"].is_object() => {
                automatic.set_active(
                    current["preferences"]["automatic_updates"]
                        .as_bool()
                        .unwrap_or(false),
                );
                channel.set_selected(u32::from(current["preferences"]["channel"] == "preview"));
                save.set_sensitive(true);
                status.set_subtitle(text.text("Loaded", "Geladen"));
            }
            Ok(_) => status.set_subtitle(text.text(
                "Install the product before changing update preferences.",
                "Installiere das Produkt, bevor du Update-Einstellungen änderst.",
            )),
            Err(error) => status.set_subtitle(&error),
        }
    });
    group
}
