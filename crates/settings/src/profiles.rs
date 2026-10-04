use crate::{client::Client, model::PROFILES, strings::Strings};
use adw::prelude::*;
use gtk::glib;

pub fn page(window: &adw::PreferencesWindow, text: Strings) -> adw::PreferencesPage {
    let page = adw::PreferencesPage::builder()
        .title(text.text("Profiles", "Profile"))
        .icon_name("preferences-system-symbolic")
        .build();
    crate::ui::introduction(
        &page,
        "preferences-system-symbolic",
        text.text("Profiles & rotation", "Profile und Drehung"),
        text.text(
            "Switch automatically with device posture, or select a profile.",
            "Automatisch nach Gerätehaltung wechseln oder ein Profil auswählen.",
        ),
    );
    let group = adw::PreferencesGroup::builder()
        .title(text.text("Choose behavior", "Verhalten wählen"))
        .description(text.text(
            "Automatic follows the tablet switch. Stand and tent are manual profiles.",
            "Automatik folgt dem Tablet-Sensor. Stand und Zelt sind manuelle Profile.",
        ))
        .build();
    let labels: Vec<_> = PROFILES.iter().map(|p| text.profile(p)).collect();
    let selection = adw::ComboRow::builder()
        .title(text.text("Profile", "Profil"))
        .model(&gtk::StringList::new(&labels))
        .build();
    let apply = gtk::Button::with_label(text.text("Apply profile", "Profil anwenden"));
    apply.set_height_request(44);
    apply.add_css_class("suggested-action");
    let result = adw::ActionRow::builder()
        .title(text.text("Result", "Ergebnis"))
        .subtitle(text.text(
            "Choose a profile to request a change.",
            "Wähle ein Profil für eine Änderung.",
        ))
        .build();
    let weak_window = window.downgrade();
    let result_copy = result.clone();
    let selection_copy = selection.downgrade();
    apply.connect_clicked(move |button| {
        let Some(selection) = selection_copy.upgrade() else {
            return;
        };
        let Some(profile) = PROFILES.get(selection.selected() as usize) else {
            return;
        };
        let profile = *profile;
        let result = result_copy.clone();
        let button = button.clone();
        let weak = weak_window.clone();
        button.set_sensitive(false);
        glib::MainContext::default().spawn_local(async move {
            let outcome = async { Client::connect().await?.profile(profile).await }.await;
            if weak.upgrade().is_none() {
                return;
            }
            match outcome {
                Ok(()) => result.set_subtitle(text.text(
                    "Profile requested. Check Overview for the applied result.",
                    "Profil angefordert. Das angewendete Ergebnis steht in der Übersicht.",
                )),
                Err(error) => result.set_subtitle(&text.error(&error)),
            }
            button.set_sensitive(true);
        });
    });
    group.add(&selection);
    group.add(&result);
    group.add(&crate::ui::actions(&[&apply]));
    page.add(&group);

    let rotation = adw::PreferencesGroup::builder()
        .title(text.text("Native rotation", "Native Drehung"))
        .description(text.text(
            "GNOME remains responsible for display rotation and touch mapping.",
            "GNOME bleibt für Bildschirmdrehung und Touch-Zuordnung zuständig.",
        ))
        .build();
    let lock = adw::SwitchRow::builder()
        .title(text.text("Lock rotation", "Drehung sperren"))
        .build();
    let save = gtk::Button::with_label(text.text("Apply rotation lock", "Drehsperre anwenden"));
    save.set_height_request(44);
    let lock_copy = lock.clone();
    let result_copy = result.clone();
    save.connect_clicked(move |button| {
        let desired = lock_copy.is_active();
        let result = result_copy.clone();
        let button = button.clone();
        button.set_sensitive(false);
        glib::MainContext::default().spawn_local(async move {
            let outcome = async { Client::connect().await?.rotation_lock(desired).await }.await;
            result.set_subtitle(&match outcome {
                Ok(()) => text
                    .text(
                        "Rotation lock requested; see applied result in Overview.",
                        "Drehsperre angefordert; Ergebnis siehe Übersicht.",
                    )
                    .to_owned(),
                Err(error) => text.error(&error),
            });
            button.set_sensitive(true);
        });
    });
    rotation.add(&lock);
    rotation.add(&crate::ui::actions(&[&save]));
    page.add(&rotation);
    // Initialize controls from service state without causing writes.
    selection.set_sensitive(false);
    lock.set_sensitive(false);
    apply.set_sensitive(false);
    save.set_sensitive(false);
    glib::MainContext::default().spawn_local(async move {
        if let Ok(client) = Client::connect().await
            && let Ok(status) = client.status().await
        {
            let profile = status["manual_override"].as_str().unwrap_or("auto");
            selection.set_selected(PROFILES.iter().position(|p| *p == profile).unwrap_or(0) as u32);
            let state = if status["desired"]["rotation_lock_requested"] == true {
                &status["desired"]
            } else {
                &status["applied"]
            };
            lock.set_active(state["rotation_lock"].as_bool().unwrap_or(false));
        }
        selection.set_sensitive(true);
        lock.set_sensitive(true);
        apply.set_sensitive(true);
        save.set_sensitive(true);
    });
    page.add(&crate::profile_editor::group(text));
    page
}
