use crate::{client::Client, strings::Strings};
use adw::prelude::*;
use convertibled_core::config::{Action, ProfileConfig};
use gtk::glib;

const ACTIONS: [Action; 3] = [Action::Unchanged, Action::Enabled, Action::Disabled];
const NAMES: [&str; 4] = ["laptop", "tablet", "stand", "tent"];

pub fn group(text: Strings) -> adw::PreferencesGroup {
    let group = adw::PreferencesGroup::builder()
        .title(text.text("Customize a profile", "Profil anpassen"))
        .description(text.text("Unchanged preserves GNOME preferences. Input suppression and scaling stay unavailable.",
            "Unverändert erhält die GNOME-Einstellungen. Eingabesperre und Skalierung bleiben nicht verfügbar.")).build();
    let names: Vec<_> = NAMES.iter().map(|name| text.profile(name)).collect();
    let profile = adw::ComboRow::builder()
        .title(text.text("Edit profile", "Profil bearbeiten"))
        .model(&gtk::StringList::new(&names))
        .build();
    let labels = [
        text.text("Unchanged", "Unverändert"),
        text.text("Enabled", "Aktiviert"),
        text.text("Disabled", "Deaktiviert"),
    ];
    let rotation = adw::ComboRow::builder()
        .title(text.text("Automatic rotation", "Automatische Drehung"))
        .model(&gtk::StringList::new(&labels))
        .build();
    let osk = adw::ComboRow::builder()
        .title(text.text("Native screen keyboard", "Native Bildschirmtastatur"))
        .model(&gtk::StringList::new(&labels))
        .build();
    let result = adw::ActionRow::builder()
        .title(text.text("Configuration status", "Konfigurationsstatus"))
        .subtitle(text.text("Loading…", "Wird geladen…"))
        .build();
    let save = gtk::Button::with_label(text.text("Save profile", "Profil speichern"));
    let reset = gtk::Button::with_label(text.text("Reset profile", "Profil zurücksetzen"));
    let controls = gtk::Box::new(gtk::Orientation::Horizontal, 6);
    for button in [&save, &reset] {
        button.set_height_request(44);
        controls.append(button);
    }
    group.set_header_suffix(Some(&controls));
    for row in [&profile, &rotation, &osk] {
        group.add(row);
    }
    group.add(&result);

    let rotation_copy = rotation.clone();
    let osk_copy = osk.clone();
    let result_copy = result.clone();
    let controls_weak = controls.downgrade();
    profile.connect_selected_notify(move |profile| {
        let Some(controls) = controls_weak.upgrade() else {
            return;
        };
        let name = NAMES[profile.selected() as usize];
        let rotation = rotation_copy.clone();
        let osk = osk_copy.clone();
        let result = result_copy.clone();
        let profile_weak = profile.downgrade();
        controls.set_sensitive(false);
        glib::MainContext::default().spawn_local(async move {
            let response = async { Client::connect().await?.config().await }.await;
            let Some(profile) = profile_weak.upgrade() else {
                return;
            };
            if NAMES[profile.selected() as usize] != name {
                return;
            }
            match response {
                Ok(config) => {
                    let value = config.profiles.get(name).cloned().unwrap_or_default();
                    rotation.set_selected(
                        ACTIONS
                            .iter()
                            .position(|a| *a == value.rotation)
                            .unwrap_or(0) as u32,
                    );
                    osk.set_selected(
                        ACTIONS.iter().position(|a| *a == value.osk).unwrap_or(0) as u32
                    );
                    result.set_subtitle(text.text("Loaded", "Geladen"));
                    controls.set_sensitive(true);
                }
                Err(error) => result.set_subtitle(&text.error(&error)),
            }
        });
    });
    for (button, reset_profile) in [(&save, false), (&reset, true)] {
        let profile_weak = profile.downgrade();
        let controls_weak = controls.downgrade();
        let rotation = rotation.clone();
        let osk = osk.clone();
        let result = result.clone();
        button.connect_clicked(move |_| {
            let (Some(profile), Some(controls)) = (profile_weak.upgrade(), controls_weak.upgrade())
            else {
                return;
            };
            let name = NAMES[profile.selected() as usize];
            let value = if reset_profile {
                ProfileConfig::default()
            } else {
                ProfileConfig {
                    rotation: ACTIONS[rotation.selected() as usize],
                    osk: ACTIONS[osk.selected() as usize],
                    ..ProfileConfig::default()
                }
            };
            let result = result.clone();
            controls.set_sensitive(false);
            profile.set_sensitive(false);
            glib::MainContext::default().spawn_local(async move {
                let outcome: Result<(), String> = async {
                    let client = Client::connect().await?;
                    let mut config = client.config().await?;
                    config.profiles.insert(name.to_owned(), value);
                    client.save_config(&config).await
                }
                .await;
                result.set_subtitle(&match outcome {
                    Ok(()) => text
                        .text(
                            "Profile saved. Applied results are shown in Overview.",
                            "Profil gespeichert. Angewendete Ergebnisse stehen in der Übersicht.",
                        )
                        .into(),
                    Err(error) => text.error(&error),
                });
                profile.set_sensitive(true);
                controls.set_sensitive(true);
                if reset_profile {
                    profile.notify("selected");
                }
            });
        });
    }
    profile.notify("selected");
    group
}
