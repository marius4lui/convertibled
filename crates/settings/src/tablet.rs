use crate::strings::Strings;
use adw::prelude::*;
use gtk::gio;

fn preferences() -> Result<gio::Settings, String> {
    let parent = gio::SettingsSchemaSource::default();
    let id = "org.gnome.shell.extensions.convertibled";
    let schema = parent.as_ref().and_then(|source| source.lookup(id, true));
    let schema = match schema {
        Some(schema) => schema,
        None => gio::SettingsSchemaSource::from_directory(
            "/opt/convertibled/current/share/gnome-shell/extensions/convertibled@convertibled.org/schemas",
            parent.as_ref(), false,
        ).map_err(|e| e.to_string())?.lookup(id, false).ok_or("Extension schema unavailable")?,
    };
    Ok(gio::Settings::new_full(
        &schema,
        None::<&gio::SettingsBackend>,
        None,
    ))
}

pub fn page(text: Strings) -> adw::PreferencesPage {
    let page = adw::PreferencesPage::builder()
        .title(text.text("Tablet", "Tablet"))
        .icon_name("view-grid-symbolic")
        .build();
    crate::ui::introduction(
        &page,
        "view-grid-symbolic",
        text.text("A workspace for touch", "Deine Tablet-Arbeitsfläche"),
        text.text(
            "Shape your dock, gestures and the essentials on Home.",
            "Gestalte dein Dock, die Gesten und das Wesentliche auf Start.",
        ),
    );
    let group = adw::PreferencesGroup::builder()
        .title(text.text("Workspace preferences", "Arbeitsfläche anpassen"))
        .description(text.text(
            "To enable gestures, touch the setup target on the built-in display after login. Reconnects require confirmation again. Home and Overview remain available without gestures.",
            "Berühre nach der Anmeldung das Einrichtungsfeld am eingebauten Bildschirm, um Gesten freizugeben. Nach erneutem Anschließen ist die Bestätigung wieder nötig. Start und Übersicht bleiben ohne Gesten verfügbar.",
        ))
        .build();
    page.add(&group);
    let settings = match preferences() {
        Ok(settings) => settings,
        Err(error) => {
            group.add(
                &adw::ActionRow::builder()
                    .title(text.text("Extension unavailable", "Erweiterung nicht verfügbar"))
                    .subtitle(text.error(&error))
                    .build(),
            );
            return page;
        }
    };
    for (key, title) in [
        (
            "gesture-enabled",
            text.text("Touchscreen edge gestures", "Randgesten am Touchscreen"),
        ),
        (
            "dock-autohide",
            text.text("Hide dock automatically", "Dock automatisch ausblenden"),
        ),
    ] {
        let row = adw::SwitchRow::builder().title(title).build();
        if key == "gesture-enabled" {
            row.set_subtitle(text.text(
                "Approve the built-in touchscreen using the setup target first.",
                "Gib zuerst den eingebauten Touchscreen über das Einrichtungsfeld frei.",
            ));
        }
        settings.bind(key, &row, "active").build();
        group.add(&row);
    }
    let ratios = gtk::StringList::new(&["50 / 50", "1/3 – 2/3", "2/3 – 1/3"]);
    let split = adw::ComboRow::builder()
        .title(text.text("Split view", "Geteilte Ansicht"))
        .subtitle(text.text(
            "Side by side in landscape. Stacked in portrait.",
            "Nebeneinander im Querformat. Untereinander im Hochformat.",
        ))
        .model(&ratios)
        .build();
    let values = ["half", "third", "two-thirds"];
    split.set_selected(
        values
            .iter()
            .position(|v| *v == settings.string("split-ratio"))
            .unwrap_or(0) as u32,
    );
    let preferences = settings.clone();
    split.connect_selected_notify(move |row| {
        if let Some(value) = values.get(row.selected() as usize) {
            let _ = preferences.set_string("split-ratio", value);
        }
    });
    group.add(&split);
    let widgets = adw::PreferencesGroup::builder()
        .title(text.text("Local widgets", "Lokale Widgets"))
        .description(text.text(
            "Enable widgets and choose their order. No account or network is needed.",
            "Widgets aktivieren und anordnen. Konto und Netzwerk sind nicht erforderlich.",
        ))
        .build();
    let message = adw::ActionRow::builder()
        .title(text.text("Widget order", "Widget-Reihenfolge"))
        .subtitle(settings.strv("widgets").join(Some(" → ")))
        .build();
    for (key, title) in [
        ("clock", text.text("Clock and date", "Uhr und Datum")),
        (
            "battery",
            text.text("Battery and system status", "Akku und Systemstatus"),
        ),
        ("actions", text.text("Quick actions", "Schnellaktionen")),
    ] {
        let row = adw::ActionRow::builder().title(title).build();
        let enabled = gtk::Switch::builder().valign(gtk::Align::Center).build();
        enabled.set_active(settings.strv("widgets").iter().any(|v| v == key));
        enabled.set_tooltip_text(Some(title));
        let first = gtk::Button::with_label(text.text("Move first", "Nach vorne"));
        first.set_height_request(44);
        first.set_valign(gtk::Align::Center);
        first.set_tooltip_text(Some(&format!(
            "{title}: {}",
            text.text("move first", "nach vorne")
        )));
        row.add_suffix(&first);
        row.add_suffix(&enabled);
        row.set_activatable_widget(Some(&enabled));
        let prefs = settings.clone();
        let message_copy = message.clone();
        enabled.connect_active_notify(move |control| {
            let mut current: Vec<String> = prefs
                .strv("widgets")
                .iter()
                .map(|v| v.to_string())
                .collect();
            current.retain(|v| v != key);
            if control.is_active() {
                current.push(key.to_owned());
            }
            if let Err(error) = prefs.set_strv("widgets", current.as_slice()) {
                message_copy.set_subtitle(&error.to_string());
            }
        });
        let prefs = settings.clone();
        let enabled_copy = enabled.clone();
        first.connect_clicked(move |_| {
            // Reordering a hidden widget does not silently enable it.
            if !enabled_copy.is_active() {
                return;
            }
            let mut current: Vec<String> = prefs
                .strv("widgets")
                .iter()
                .map(|v| v.to_string())
                .collect();
            current.retain(|v| v != key);
            current.insert(0, key.to_owned());
            let _ = prefs.set_strv("widgets", current.as_slice());
        });
        widgets.add(&row);
    }
    let message_copy = message.clone();
    settings.connect_changed(Some("widgets"), move |prefs, _| {
        message_copy.set_subtitle(&prefs.strv("widgets").join(Some(" → ")));
    });
    widgets.add(&message);
    page.add(&widgets);
    page
}
