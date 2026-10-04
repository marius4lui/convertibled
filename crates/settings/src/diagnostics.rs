use crate::{operations::run, strings::Strings};
use adw::prelude::*;
use gtk::{gio, glib};
use std::{cell::RefCell, rc::Rc};

pub fn page(window: &adw::PreferencesWindow, text: Strings) -> adw::PreferencesPage {
    let page = adw::PreferencesPage::builder()
        .title(text.text("Diagnostics", "Diagnose"))
        .icon_name("dialog-information-symbolic")
        .build();
    let group = adw::PreferencesGroup::builder()
        .title(text.text("Local health report", "Lokaler Zustandsbericht"))
        .description(text.text("Reports contain project state, not keystrokes or private system logs. Nothing is uploaded.",
            "Berichte enthalten den Projektzustand, keine Tastatureingaben oder privaten Systemprotokolle. Es wird nichts hochgeladen.")).build();
    let controls = gtk::Box::new(gtk::Orientation::Horizontal, 6);
    let check = gtk::Button::with_label(text.text("Run checks", "Prüfung starten"));
    let export = gtk::Button::with_label(text.text("Export…", "Exportieren…"));
    for button in [&check, &export] {
        button.set_height_request(44);
        controls.append(button);
    }
    export.set_sensitive(false);
    group.set_header_suffix(Some(&controls));
    let result = gtk::TextView::builder()
        .editable(false)
        .cursor_visible(false)
        .monospace(true)
        .wrap_mode(gtk::WrapMode::WordChar)
        .top_margin(12)
        .bottom_margin(12)
        .left_margin(12)
        .right_margin(12)
        .build();
    let scroll = gtk::ScrolledWindow::builder()
        .child(&result)
        .min_content_height(320)
        .hscrollbar_policy(gtk::PolicyType::Never)
        .build();
    group.add(&scroll);
    let notice = adw::ActionRow::builder()
        .title(text.text("Report status", "Berichtsstatus"))
        .subtitle(text.text("No report collected yet.", "Noch kein Bericht erstellt."))
        .build();
    group.add(&notice);
    page.add(&group);
    let report = Rc::new(RefCell::new(String::new()));
    let report_copy = report.clone();
    let notice_copy = notice.clone();
    let export_copy = export.clone();
    check.connect_clicked(move |button| {
        let button = button.clone();
        let result = result.clone();
        let notice = notice_copy.clone();
        let export = export_copy.clone();
        let report = report_copy.clone();
        button.set_sensitive(false);
        export.set_sensitive(false);
        glib::MainContext::default().spawn_local(async move {
            match run(&[
                "/opt/convertibled/current/bin/convertiblectl",
                "--json",
                "doctor",
            ])
            .await
            {
                Ok(raw) => match serde_json::from_str::<serde_json::Value>(&raw) {
                    Ok(value) => {
                        let formatted = serde_json::to_string_pretty(&value).unwrap_or_default();
                        result.buffer().set_text(&formatted);
                        *report.borrow_mut() = formatted;
                        export.set_sensitive(true);
                        notice.set_subtitle(
                            text.text("Report ready for review.", "Bericht zur Prüfung bereit."),
                        );
                    }
                    Err(error) => notice.set_subtitle(&error.to_string()),
                },
                Err(error) => {
                    report.borrow_mut().clear();
                    result.buffer().set_text("");
                    notice.set_subtitle(&error);
                }
            }
            button.set_sensitive(true);
        });
    });
    let weak_window = window.downgrade();
    export.connect_clicked(move |_| {
        let Some(window) = weak_window.upgrade() else {
            return;
        };
        let bytes = report.borrow().as_bytes().to_vec();
        let notice = notice.clone();
        glib::MainContext::default().spawn_local(async move {
            let dialog = gtk::FileDialog::builder()
                .title(text.text("Export diagnostic report", "Diagnosebericht exportieren"))
                .initial_name("convertibled-diagnostics.json")
                .build();
            if let Ok(file) = dialog.save_future(Some(&window)).await {
                match file
                    .replace_contents_future(bytes, None, false, gio::FileCreateFlags::PRIVATE)
                    .await
                {
                    Ok(_) => {
                        notice.set_subtitle(text.text("Report saved.", "Bericht gespeichert."))
                    }
                    Err((_, error)) => notice.set_subtitle(&error.to_string()),
                }
            }
        });
    });
    page
}
