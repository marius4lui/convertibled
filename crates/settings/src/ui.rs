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
    let text = crate::strings::Strings::detect();
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
    window.add(&crate::overview::page(&window, text));
    window.add(&crate::profiles::page(&window, text));
    window.add(&crate::hardware::page(text));
    window.add(&crate::tablet::page(text));
    window.add(&crate::updates::page(text));
    window.add(&crate::diagnostics::page(&window, text));
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
