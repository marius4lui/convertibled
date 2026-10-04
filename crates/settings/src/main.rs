#[cfg_attr(not(target_os = "linux"), allow(dead_code))]
mod model;
#[cfg_attr(not(target_os = "linux"), allow(dead_code))]
mod strings;

#[cfg(target_os = "linux")]
mod client;
#[cfg(target_os = "linux")]
mod hardware;
#[cfg(target_os = "linux")]
mod operations;
#[cfg(target_os = "linux")]
mod overview;
#[cfg(target_os = "linux")]
mod profiles;
#[cfg(target_os = "linux")]
mod tablet;
#[cfg(target_os = "linux")]
mod ui;
#[cfg(target_os = "linux")]
mod updates;

#[cfg(target_os = "linux")]
fn main() -> gtk::glib::ExitCode {
    ui::run()
}

#[cfg(not(target_os = "linux"))]
fn main() {
    eprintln!("convertibled-settings requires GNOME 50 on Fedora 44/Wayland");
    std::process::exit(2);
}
