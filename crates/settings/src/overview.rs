use crate::{client::Client, model::field, strings::Strings};
use adw::prelude::*;
use gtk::glib;

pub fn page(window: &adw::PreferencesWindow, text: Strings) -> adw::PreferencesPage {
    let page = adw::PreferencesPage::builder()
        .title(text.text("Overview", "Übersicht"))
        .icon_name("computer-symbolic")
        .build();
    let group = adw::PreferencesGroup::builder()
        .title(text.text("Current state", "Aktueller Zustand"))
        .description(text.text(
            "Requested actions and confirmed results are shown separately.",
            "Gewünschte Aktionen und bestätigte Ergebnisse werden getrennt angezeigt.",
        ))
        .build();
    let definitions = [
        (
            text.text("Detected posture", "Erkannte Haltung"),
            vec!["observation", "posture"],
        ),
        (
            text.text("Orientation", "Ausrichtung"),
            vec!["observation", "orientation"],
        ),
        (
            text.text("Selected profile", "Gewähltes Profil"),
            vec!["profile"],
        ),
        (
            text.text("Manual override", "Manuelle Auswahl"),
            vec!["manual_override"],
        ),
        (
            text.text("Requested workspace", "Gewünschte Arbeitsfläche"),
            vec!["desired", "tablet_workspace"],
        ),
        (
            text.text("Applied workspace", "Angewendete Arbeitsfläche"),
            vec!["applied", "tablet_workspace"],
        ),
        (
            text.text("Action result", "Aktionsergebnis"),
            vec!["applied", "status"],
        ),
        (
            text.text("Action details", "Aktionsdetails"),
            vec!["applied", "error"],
        ),
        (
            text.text("Requested rotation", "Gewünschte Drehung"),
            vec!["desired", "rotation"],
        ),
        (
            text.text("Rotation result", "Drehungsergebnis"),
            vec!["applied", "action_outcomes", "rotation", "status"],
        ),
        (
            text.text("Rotation details", "Drehungsdetails"),
            vec!["applied", "action_outcomes", "rotation", "error"],
        ),
        (
            text.text("Requested screen keyboard", "Gewünschte Bildschirmtastatur"),
            vec!["desired", "osk"],
        ),
        (
            text.text("Screen keyboard result", "Bildschirmtastatur-Ergebnis"),
            vec!["applied", "action_outcomes", "osk", "status"],
        ),
        (
            text.text("Screen keyboard details", "Bildschirmtastatur-Details"),
            vec!["applied", "action_outcomes", "osk", "error"],
        ),
    ];
    let rows: Vec<_> = definitions
        .into_iter()
        .map(|(title, path)| {
            let row = adw::ActionRow::builder().title(title).subtitle("—").build();
            row.set_subtitle_selectable(true);
            group.add(&row);
            (row, path)
        })
        .collect();
    let refresh = gtk::Button::with_label(text.text("Refresh", "Aktualisieren"));
    refresh.set_height_request(44);
    group.set_header_suffix(Some(&refresh));
    let health = adw::ActionRow::builder()
        .title(text.text("Connection", "Verbindung"))
        .subtitle(text.text("Connecting…", "Verbindung wird hergestellt…"))
        .build();
    group.add(&health);
    page.add(&group);
    let weak_window = window.downgrade();
    refresh.connect_clicked(move |button| {
        let rows = rows.clone();
        let health = health.clone();
        let weak_window = weak_window.clone();
        let button = button.clone();
        button.set_sensitive(false);
        glib::MainContext::default().spawn_local(async move {
            let result = async { Client::connect().await?.status().await }.await;
            if weak_window.upgrade().is_none() {
                return;
            }
            match result {
                Ok(status) => {
                    for (row, path) in &rows {
                        row.set_subtitle(&text.value(&field(&status, path)));
                    }
                    health.set_subtitle(text.text("Connected", "Verbunden"));
                }
                Err(error) => {
                    // Remove stale values instead of presenting them as current state.
                    for (row, _) in &rows {
                        row.set_subtitle("—");
                    }
                    health.set_subtitle(&format!(
                        "{}: {}",
                        text.text("Service unavailable", "Dienst nicht verfügbar"),
                        text.error(&error)
                    ));
                }
            }
            button.set_sensitive(true);
        });
    });
    refresh.emit_clicked();
    let weak_refresh = refresh.downgrade();
    let weak_window = window.downgrade();
    glib::timeout_add_local(std::time::Duration::from_secs(2), move || {
        let (Some(window), Some(refresh)) = (weak_window.upgrade(), weak_refresh.upgrade()) else {
            return glib::ControlFlow::Break;
        };
        if window.is_active() && refresh.is_sensitive() {
            refresh.emit_clicked();
        }
        glib::ControlFlow::Continue
    });
    page
}
