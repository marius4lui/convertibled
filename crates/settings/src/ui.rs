use adw::prelude::*;
use gtk::{gio, glib};

pub fn run() -> glib::ExitCode {
    let app = adw::Application::builder()
        .application_id("org.convertibled.Settings")
        .build();
    app.connect_activate(build_window);
    app.run()
}

fn build_window(app: &adw::Application) {
    if let Some(window) = app.active_window() {
        window.present();
        return;
    }
    let window = adw::PreferencesWindow::builder()
        .application(app)
        .title("convertibled")
        .default_width(760)
        .default_height(720)
        .search_enabled(true)
        .build();
    for (title, icon) in [
        ("Overview", "computer-symbolic"),
        ("Profiles", "preferences-system-symbolic"),
        ("Hardware", "input-tablet-symbolic"),
        ("Tablet", "view-grid-symbolic"),
        ("Updates", "software-update-available-symbolic"),
        ("Diagnostics", "dialog-information-symbolic"),
    ] {
        let page = adw::PreferencesPage::builder()
            .title(title)
            .icon_name(icon)
            .build();
        let group = adw::PreferencesGroup::builder().title(title).build();
        let row = adw::ActionRow::builder()
            .title("Service connection")
            .subtitle("Connecting to the session service…")
            .build();
        group.add(&row);
        page.add(&group);
        window.add(&page);
    }
    let quit = gio::SimpleAction::new("quit", None);
    let weak = app.downgrade();
    quit.connect_activate(move |_, _| {
        if let Some(app) = weak.upgrade() {
            app.quit();
        }
    });
    app.add_action(&quit);
    app.set_accels_for_action("app.quit", &["<primary>q"]);
    window.present();
}
