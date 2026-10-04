use crate::{client::Client, strings::Strings};
use adw::prelude::*;
use gtk::glib;

pub fn page(text: Strings) -> adw::PreferencesPage {
    let page = adw::PreferencesPage::builder()
        .title(text.text("Hardware", "Hardware"))
        .icon_name("input-tablet-symbolic")
        .build();
    let group = adw::PreferencesGroup::builder()
        .title(text.text("Available capabilities", "Verfügbare Fähigkeiten"))
        .description(text.text(
            "A sensor does not imply support for every desktop action.",
            "Ein Sensor bedeutet nicht, dass jede Desktop-Aktion unterstützt wird.",
        ))
        .build();
    let refresh = gtk::Button::with_label(text.text("Refresh", "Aktualisieren"));
    refresh.set_height_request(44);
    group.set_header_suffix(Some(&refresh));
    let rows: Vec<_> = [
        (
            "tablet_workspace",
            text.text("Tablet workspace", "Tablet-Arbeitsfläche"),
        ),
        ("rotation", text.text("Rotation", "Drehung")),
        ("rotation_lock", text.text("Rotation lock", "Drehsperre")),
        (
            "osk",
            text.text("Native on-screen keyboard", "Native Bildschirmtastatur"),
        ),
        ("split_view", text.text("Split view", "Geteilte Ansicht")),
        (
            "touchscreen_gestures",
            text.text("Touchscreen gestures", "Touchscreen-Gesten"),
        ),
        (
            "internal_input_suppression",
            text.text(
                "Internal input suppression",
                "Interne Eingaben deaktivieren",
            ),
        ),
        (
            "scaling",
            text.text("Automatic scaling", "Automatische Skalierung"),
        ),
    ]
    .into_iter()
    .map(|(key, title)| {
        let row = adw::ActionRow::builder().title(title).subtitle("—").build();
        group.add(&row);
        (key, row)
    })
    .collect();
    refresh.connect_clicked(move |button| {
        let button = button.clone();
        let rows = rows.clone();
        button.set_sensitive(false);
        glib::MainContext::default().spawn_local(async move {
            let result = async { Client::connect().await?.capabilities().await }.await;
            for (key, row) in &rows {
                match &result {
                    Ok(value) => {
                        let supported = value[*key]["supported"].as_bool().unwrap_or(false);
                        let state = if supported {
                            text.text("Available", "Verfügbar")
                        } else {
                            text.text("Unavailable", "Nicht verfügbar")
                        };
                        let reason = value[*key]["reason"].as_str().unwrap_or("—");
                        row.set_subtitle(&format!("{state}: {reason}"));
                    }
                    Err(error) => row.set_subtitle(&format!(
                        "{}: {}",
                        text.text("Service unavailable", "Dienst nicht verfügbar"),
                        text.error(error)
                    )),
                }
            }
            button.set_sensitive(true);
        });
    });
    refresh.emit_clicked();
    page.add(&group);
    page
}
