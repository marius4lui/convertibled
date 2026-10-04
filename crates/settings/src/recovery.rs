use crate::{operations::helper, strings::Strings};
use adw::prelude::*;
use gtk::glib;

pub fn group(
    window: &adw::PreferencesWindow,
    text: Strings,
    refresh: &gtk::Button,
) -> adw::PreferencesGroup {
    let group = adw::PreferencesGroup::builder()
        .title(text.text("Recovery and removal", "Wiederherstellung und Entfernung"))
        .description(text.text(
            "Schedule an action for after all graphical users log out. Nothing closes your session. Configuration and personal data are retained when removing convertibled.",
            "Plane eine Aktion für die Abmeldung aller grafischen Benutzer. Deine Sitzung wird nicht beendet. Beim Entfernen bleiben Konfiguration und persönliche Daten erhalten.",
        )).build();
    let result = adw::ActionRow::builder()
        .title(text.text("Request result", "Ergebnis der Anfrage"))
        .subtitle("—")
        .build();
    for (command, title, detail, confirm) in [
        (
            "request-recover",
            text.text(
                "Recover interrupted transaction",
                "Unterbrochene Transaktion wiederherstellen",
            ),
            text.text("Repair an interrupted installation after all graphical users log out. The installed helper checks what can safely be recovered. Automatic updates may remain off.", "Eine unterbrochene Installation wird nach der Abmeldung aller grafischen Benutzer repariert. Der installierte Helfer prüft, was sicher wiederhergestellt werden kann. Automatische Updates dürfen ausgeschaltet bleiben."),
            text.text("Schedule recovery", "Wiederherstellung planen"),
        ),
        (
            "request-rollback",
            text.text(
                "Restore previous version",
                "Vorherige Version wiederherstellen",
            ),
            text.text("Restore the retained previous version after all graphical users log out. The helper checks that a compatible previous version exists. Your session stays open until you log out yourself.", "Die aufbewahrte vorherige Version wird nach der Abmeldung aller grafischen Benutzer wiederhergestellt. Der Helfer prüft, ob eine kompatible Version vorhanden ist. Deine Sitzung bleibt bis zu deiner eigenen Abmeldung geöffnet."),
            text.text("Schedule rollback", "Rückkehr planen"),
        ),
        (
            "request-uninstall",
            text.text("Remove convertibled", "convertibled entfernen"),
            text.text("After all graphical users log out, remove convertibled and its tablet workspace from this computer. Configuration and personal data are retained. Modified or unowned files are not removed. You can cancel while this request is waiting. No one is logged out automatically.", "Nach der Abmeldung aller grafischen Benutzer werden convertibled und seine Tablet-Oberfläche von diesem Computer entfernt. Konfiguration und persönliche Daten bleiben erhalten. Veränderte oder fremde Dateien werden nicht entfernt. Solange die Anfrage wartet, kannst du sie abbrechen. Niemand wird automatisch abgemeldet."),
            text.text("Schedule removal", "Entfernung planen"),
        ),
        (
            "cancel-pending",
            text.text("Cancel scheduled action", "Geplante Aktion abbrechen"),
            text.text("Cancel a waiting or failed recovery or removal request. An action already being applied cannot be interrupted. Automatic update preferences are unchanged.", "Eine wartende oder fehlgeschlagene Wiederherstellung oder Entfernung wird abgebrochen. Eine bereits laufende Aktion kann nicht unterbrochen werden. Die Einstellung für automatische Updates bleibt unverändert."),
            text.text("Cancel scheduled action", "Geplante Aktion abbrechen"),
        ),
    ] {
        let row = adw::ActionRow::builder().title(title).build();
        let button = gtk::Button::with_label(text.text("Review…", "Prüfen…"));
        button.set_height_request(44);
        button.set_valign(gtk::Align::Center);
        if command == "request-uninstall" {
            button.add_css_class("destructive-action");
        }
        row.add_suffix(&button);
        let weak = window.downgrade();
        let result = result.clone();
        let refresh = refresh.downgrade();
        button.connect_clicked(move |button| {
            let Some(window) = weak.upgrade() else { return; };
            let button = button.clone();
            let result = result.clone();
            let refresh = refresh.clone();
            glib::MainContext::default().spawn_local(async move {
                let dialog = gtk::AlertDialog::builder().message(title)
                    .detail(detail)
                    .buttons([text.text("Go back", "Zurück"), confirm])
                    .cancel_button(0).default_button(0).build();
                if dialog.choose_future(Some(&window)).await != Ok(1) { return; }
                button.set_sensitive(false);
                match helper(command, None).await {
                    Ok(value) => result.set_subtitle(&text.value(&crate::model::field(&value, &["phase"]))),
                    Err(error) => result.set_subtitle(&text.error(&error)),
                }
                button.set_sensitive(true);
                if let Some(refresh) = refresh.upgrade() { refresh.emit_clicked(); }
            });
        });
        group.add(&row);
    }
    group.add(&result);
    group
}
