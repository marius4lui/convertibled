use adw::prelude::*;
use gtk::{gio, glib};

/// A quiet introduction using the desktop's typography and symbolic artwork.
pub fn introduction(page: &adw::PreferencesPage, icon: &str, title: &str, description: &str) {
    let group = adw::PreferencesGroup::new();
    let content = gtk::Box::new(gtk::Orientation::Vertical, 12);
    content.set_margin_top(12);
    content.set_margin_bottom(12);
    let image = gtk::Image::from_icon_name(icon);
    image.set_pixel_size(48);
    image.add_css_class("accent");
    content.append(&image);
    let heading = gtk::Label::new(Some(title));
    heading.add_css_class("title-1");
    heading.set_wrap(true);
    heading.set_justify(gtk::Justification::Center);
    content.append(&heading);
    let subtitle = gtk::Label::new(Some(description));
    subtitle.set_wrap(true);
    subtitle.set_justify(gtk::Justification::Center);
    subtitle.add_css_class("dim-label");
    content.append(&subtitle);
    group.add(&content);
    page.add(&group);
}

/// Full-width wrapping action area: labels remain reachable in portrait.
pub fn actions(buttons: &[&gtk::Button]) -> gtk::FlowBox {
    let controls = gtk::FlowBox::builder()
        .selection_mode(gtk::SelectionMode::None)
        .homogeneous(true)
        .column_spacing(12)
        .row_spacing(12)
        .min_children_per_line(1)
        .max_children_per_line(buttons.len() as u32)
        .build();
    for button in buttons {
        button.set_height_request(44);
        button.set_hexpand(true);
        controls.insert(*button, -1);
    }
    controls
}

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
    window.add(&crate::updates::page(&window, text));
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
