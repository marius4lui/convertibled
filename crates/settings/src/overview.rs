use crate::{client::Client, model::field, strings::Strings};
use adw::prelude::*;
use gtk::glib;

pub fn page(window: &adw::PreferencesWindow, text: Strings) -> adw::PreferencesPage {
    let page = adw::PreferencesPage::builder()
        .title(text.text("Overview", "Übersicht"))
        .icon_name("computer-symbolic")
        .build();
    let hero = gtk::Box::new(gtk::Orientation::Vertical, 12);
    hero.set_margin_top(12);
    hero.set_margin_bottom(12);
    let icon = gtk::Image::from_icon_name("computer-symbolic");
    icon.set_pixel_size(64);
    icon.add_css_class("accent");
    let heading = gtk::Label::new(Some(text.text("Your convertible", "Dein Convertible")));
    heading.add_css_class("title-1");
    heading.set_wrap(true);
    heading.set_justify(gtk::Justification::Center);
    let summary = gtk::Label::new(Some(text.text(
        "Connecting to your session…",
        "Verbindung mit deiner Sitzung wird hergestellt…",
    )));
    summary.set_wrap(true);
    summary.set_justify(gtk::Justification::Center);
    summary.add_css_class("dim-label");
    hero.append(&icon);
    hero.append(&heading);
    hero.append(&summary);
    let introduction = adw::PreferencesGroup::new();
    introduction.add(&hero);
    page.add(&introduction);
    let group = adw::PreferencesGroup::new();
    let health = adw::ActionRow::builder()
        .title(text.text("Connection", "Verbindung"))
        .subtitle(text.text("Connecting…", "Verbindung wird hergestellt…"))
        .build();
    group.add(&health);
    page.add(&group);
    let detected = adw::PreferencesGroup::builder()
        .title(text.text("Device & profile", "Gerät und Profil"))
        .build();
    let workspace = adw::PreferencesGroup::builder()
        .title(text.text("Workspace", "Arbeitsfläche"))
        .description(text.text(
            "What was requested, and what your desktop confirmed.",
            "Was angefordert wurde und was dein Desktop bestätigt hat.",
        ))
        .build();
    let native = adw::PreferencesGroup::builder()
        .title(text.text("Desktop preferences", "Desktop-Einstellungen"))
        .build();
    let rotation = adw::ExpanderRow::builder()
        .title(text.text("Automatic rotation", "Automatische Drehung"))
        .subtitle(text.text("Request and result", "Anforderung und Ergebnis"))
        .build();
    let keyboard = adw::ExpanderRow::builder()
        .title(text.text("Screen keyboard", "Bildschirmtastatur"))
        .subtitle(text.text("Request and result", "Anforderung und Ergebnis"))
        .build();
    native.add(&rotation);
    native.add(&keyboard);
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
        .enumerate()
        .map(|(index, (title, path))| {
            let row = adw::ActionRow::builder().title(title).subtitle("—").build();
            row.set_subtitle_selectable(true);
            if index < 4 {
                detected.add(&row);
            } else if index < 8 {
                workspace.add(&row);
            } else if index < 11 {
                rotation.add_row(&row);
            } else {
                keyboard.add_row(&row);
            }
            (row, path)
        })
        .collect();
    let refresh = gtk::Button::with_label(text.text("Refresh", "Aktualisieren"));
    refresh.set_height_request(44);
    refresh.set_valign(gtk::Align::Center);
    health.add_suffix(&refresh);
    page.add(&detected);
    page.add(&workspace);
    page.add(&native);
    for group in [&detected, &workspace, &native] {
        group.set_visible(false);
    }
    let weak_window = window.downgrade();
    refresh.connect_clicked(move |button| {
        let rows = rows.clone();
        let health = health.clone();
        let heading = heading.clone();
        let summary = summary.clone();
        let icon = icon.clone();
        let rotation = rotation.clone();
        let keyboard = keyboard.clone();
        let groups = [detected.clone(), workspace.clone(), native.clone()];
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
                    for group in &groups {
                        group.set_visible(true);
                    }
                    for (row, path) in &rows {
                        let value = field(&status, path);
                        row.set_subtitle(&text.value(&value));
                        if path.last() == Some(&"error") {
                            row.set_visible(value != "—" && !value.is_empty());
                        }
                    }
                    let profile = field(&status, &["profile"]);
                    heading.set_label(&format!(
                        "{} · {}",
                        text.profile(&profile),
                        text.text("selected", "ausgewählt")
                    ));
                    icon.set_icon_name(Some(if profile == "tablet" {
                        "input-tablet-symbolic"
                    } else {
                        "computer-symbolic"
                    }));
                    summary.set_label(&format!(
                        "{}: {} · {}: {}",
                        text.text("Detected", "Erkannt"),
                        text.value(&field(&status, &["observation", "posture"])),
                        text.text("Workspace applied", "Arbeitsfläche angewendet"),
                        text.value(&field(&status, &["applied", "tablet_workspace"]))
                    ));
                    rotation.set_subtitle(&text.value(&field(
                        &status,
                        &["applied", "action_outcomes", "rotation", "status"],
                    )));
                    keyboard.set_subtitle(&text.value(&field(
                        &status,
                        &["applied", "action_outcomes", "osk", "status"],
                    )));
                    health.set_subtitle(text.text("Connected", "Verbunden"));
                }
                Err(error) => {
                    for group in &groups {
                        group.set_visible(false);
                    }
                    // Remove stale values instead of presenting them as current state.
                    for (row, _) in &rows {
                        row.set_subtitle("—");
                    }
                    heading.set_label(text.text("Let's connect", "Verbindung herstellen"));
                    icon.set_icon_name(Some("network-offline-symbolic"));
                    summary.set_label(text.text(
                        "Your session is unavailable. Refresh to try again.",
                        "Deine Sitzung ist nicht erreichbar. Aktualisiere, um es erneut zu versuchen.",
                    ));
                    rotation.set_subtitle("—");
                    keyboard.set_subtitle("—");
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
