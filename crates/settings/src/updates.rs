use crate::{model::field, operations::helper, strings::Strings};
use adw::prelude::*;
use gtk::glib;

pub fn page(text: Strings) -> adw::PreferencesPage {
    let page = adw::PreferencesPage::builder()
        .title(text.text("Updates", "Updates"))
        .icon_name("software-update-available-symbolic")
        .build();
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
        ("error", text.text("Details", "Details")),
    ]
    .into_iter()
    .map(|(key, label)| {
        let row = adw::ActionRow::builder().title(label).subtitle("—").build();
        group.add(&row);
        (key, row)
    })
    .collect();
    let buttons = gtk::Box::new(gtk::Orientation::Horizontal, 6);
    let refresh = gtk::Button::with_label(text.text("Refresh", "Aktualisieren"));
    let check = gtk::Button::with_label(text.text("Check", "Prüfen"));
    let prepare = gtk::Button::with_label(text.text("Prepare", "Vorbereiten"));
    for button in [&refresh, &check, &prepare] {
        button.set_height_request(44);
        buttons.append(button);
    }
    group.set_header_suffix(Some(&buttons));
    for (button, command) in [
        (&refresh, "status"),
        (&check, "check"),
        (&prepare, "prepare"),
    ] {
        let rows = rows.clone();
        let controls = buttons.clone();
        button.connect_clicked(move |_| {
            let rows = rows.clone();
            let controls = controls.clone();
            controls.set_sensitive(false);
            glib::MainContext::default().spawn_local(async move {
                match helper(command, None).await {
                    Ok(status) => {
                        for (key, row) in &rows {
                            row.set_subtitle(&field(&status, &[*key]));
                        }
                    }
                    Err(error) => {
                        for (_, row) in &rows {
                            row.set_subtitle("—");
                        }
                        if let Some((_, row)) = rows.last() {
                            row.set_subtitle(&error);
                        }
                    }
                }
                controls.set_sensitive(true);
            });
        });
    }
    page.add(&group);
    page.add(&crate::update_preferences::group(text));
    refresh.emit_clicked();
    page
}
