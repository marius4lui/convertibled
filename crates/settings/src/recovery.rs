use crate::{operations::helper, strings::Strings};
use adw::prelude::*;
use gtk::glib;

pub fn group(window: &adw::PreferencesWindow, text: Strings) -> adw::PreferencesGroup {
    let group = adw::PreferencesGroup::builder()
        .title(text.text("Recovery", "Wiederherstellung"))
        .description(text.text(
            "Recovery respects active graphical sessions. If logout is required, use the installed command-line helper after logging out.",
            "Die Wiederherstellung berücksichtigt aktive grafische Sitzungen. Falls eine Abmeldung erforderlich ist, nutze anschließend den installierten Kommandozeilenhelfer.",
        )).build();
    let result = adw::ActionRow::builder()
        .title(text.text("Recovery result", "Wiederherstellungsergebnis"))
        .subtitle("—")
        .build();
    for (command, title) in [
        (
            "recover",
            text.text(
                "Recover interrupted transaction",
                "Unterbrochene Transaktion wiederherstellen",
            ),
        ),
        (
            "rollback",
            text.text(
                "Restore previous version",
                "Vorherige Version wiederherstellen",
            ),
        ),
    ] {
        let row = adw::ActionRow::builder().title(title).build();
        let button = gtk::Button::with_label(text.text("Review…", "Prüfen…"));
        button.set_height_request(44);
        button.set_valign(gtk::Align::Center);
        row.add_suffix(&button);
        let weak = window.downgrade();
        let result = result.clone();
        button.connect_clicked(move |button| {
            let Some(window) = weak.upgrade() else { return; };
            let button = button.clone();
            let result = result.clone();
            glib::MainContext::default().spawn_local(async move {
                let dialog = gtk::AlertDialog::builder().message(title)
                    .detail(text.text("This requests an authorized system recovery. Current sessions are never forcibly closed.",
                        "Dies fordert eine autorisierte Systemwiederherstellung an. Aktuelle Sitzungen werden niemals erzwungen beendet."))
                    .buttons([text.text("Cancel", "Abbrechen"), text.text("Request recovery", "Wiederherstellung anfordern")])
                    .cancel_button(0).default_button(0).build();
                if dialog.choose_future(Some(&window)).await != Ok(1) { return; }
                button.set_sensitive(false);
                match helper(command, None).await {
                    Ok(value) => result.set_subtitle(&crate::model::field(&value, &["phase"])),
                    Err(error) => result.set_subtitle(&error),
                }
                button.set_sensitive(true);
            });
        });
        group.add(&row);
    }
    group.add(&result);
    group
}
