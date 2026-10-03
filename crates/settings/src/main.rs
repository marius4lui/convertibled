mod model;

#[cfg(target_os = "linux")]
mod ui;

#[cfg(target_os = "linux")]
fn main() -> gtk::glib::ExitCode {
    ui::run()
}

#[cfg(not(target_os = "linux"))]
fn main() {
    eprintln!("convertibled-settings requires GNOME 50 on Fedora 44/Wayland");
    std::process::exit(2);
}
