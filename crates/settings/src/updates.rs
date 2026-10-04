use crate::{model::field, operations::helper, strings::Strings};
use adw::prelude::*;
use gtk::glib;

pub fn page(window: &adw::PreferencesWindow, text: Strings) -> adw::PreferencesPage {
    let page = adw::PreferencesPage::builder()
        .title(text.text("Updates", "Updates"))
        .icon_name("software-update-available-symbolic")
        .build();
    crate::ui::introduction(
        &page,
        "software-update-available-symbolic",
        text.text("Software updates", "Software-Updates"),
        text.text(
            "Verified updates prepare quietly and activate after you log out.",
            "Geprüfte Updates werden im Hintergrund vorbereitet und nach deiner Abmeldung aktiviert.",
        ),
    );
    let group = adw::PreferencesGroup::builder()
        .title(text.text("Verified updates", "Geprüfte Updates"))
        .description(text.text(
            "Updates prepare automatically by default. Installation waits for logout; locking does not log out. You are never logged out automatically.",
            "Updates werden standardmäßig automatisch vorbereitet. Die Installation wartet auf die Abmeldung; Sperren reicht nicht. Du wirst niemals automatisch abgemeldet.",
        )).build();
    let rows: Vec<_> = [
        (
            "installed",
            text.text("Installed version", "Installierte Version"),
        ),
        (
            "available",
            text.text("Available version", "Verfügbare Version"),
        ),
        (
            "prepared",
            text.text("Prepared version", "Vorbereitete Version"),
        ),
        (
            "phase",
            text.text("Transaction state", "Transaktionszustand"),
        ),
        (
            "shell_acceptance",
            text.text("Desktop check", "Desktop-Prüfung"),
        ),
        (
            "pending_action",
            text.text("Scheduled action", "Geplante Aktion"),
        ),
        (
            "pending_state",
            text.text("Scheduled action status", "Status der geplanten Aktion"),
        ),
        ("error", text.text("Details", "Details")),
    ]
    .into_iter()
    .map(|(key, label)| {
        let row = adw::ActionRow::builder().title(label).subtitle("—").build();
        group.add(&row);
        (key, row)
    })
    .collect();
    let refresh = gtk::Button::with_label(text.text("Refresh", "Aktualisieren"));
    let check = gtk::Button::with_label(text.text("Check", "Prüfen"));
    let prepare = gtk::Button::with_label(text.text("Prepare", "Vorbereiten"));
    let install =
        gtk::Button::with_label(text.text("Install after logout", "Nach Abmeldung installieren"));
    prepare.add_css_class("suggested-action");
    let buttons = crate::ui::actions(&[&refresh, &check, &prepare, &install]);
    group.add(&buttons);
    for (button, command) in [
        (&refresh, "status"),
        (&check, "check"),
        (&prepare, "prepare"),
        (&install, "request-activate"),
    ] {
        let rows = rows.clone();
        let controls = buttons.downgrade();
        let window = window.downgrade();
        button.connect_clicked(move |_| {
            let rows = rows.clone();
            let Some(controls) = controls.upgrade() else {
                return;
            };
            controls.set_sensitive(false);
            let window = window.clone();
            glib::MainContext::default().spawn_local(async move {
                if command == "request-activate" {
                    let Some(window) = window.upgrade() else { controls.set_sensitive(true); return; };
                    let dialog = gtk::AlertDialog::builder()
                        .message(text.text("Install after logout", "Nach Abmeldung installieren"))
                        .detail(text.text(
                            "Install the prepared version after all graphical users log out. Nobody is logged out automatically. Automatic updates stay unchanged. You can cancel this request while it is waiting.",
                            "Die vorbereitete Version wird nach der Abmeldung aller grafischen Benutzer installiert. Niemand wird automatisch abgemeldet. Automatische Updates bleiben unverändert. Solange die Anfrage wartet, kannst du sie abbrechen.",
                        ))
                        .buttons([text.text("Go back", "Zurück"), text.text("Schedule installation", "Installation planen")])
                        .cancel_button(0).default_button(0).build();
                    if dialog.choose_future(Some(&window)).await != Ok(1) { controls.set_sensitive(true); return; }
                }
                match helper(command, None).await {
                    Ok(status) => {
                        for (key, row) in &rows {
                            row.set_subtitle(&text.value(&field(&status, &[*key])));
                        }
                    }
                    Err(error) => {
                        for (_, row) in &rows {
                            row.set_subtitle("—");
                        }
                        if let Some((_, row)) = rows.last() {
                            row.set_subtitle(&text.error(&error));
                        }
                    }
                }
                controls.set_sensitive(true);
            });
        });
    }
    page.add(&group);
    page.add(&crate::update_preferences::group(text));
    page.add(&crate::recovery::group(window, text, &refresh));
    refresh.emit_clicked();
    page
}
