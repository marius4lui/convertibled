#[cfg(target_os = "linux")]
mod hardware;
#[cfg(target_os = "linux")]
mod service;
#[cfg(target_os = "linux")]
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    if std::env::args().any(|arg| arg == "--check") {
        return service::check();
    }
    service::run().await
}
#[cfg(not(target_os = "linux"))]
fn main() {
    eprintln!("convertibled requires Linux evdev and system D-Bus");
    std::process::exit(3);
}
#[cfg(target_os = "linux")]
mod health;
#[cfg(target_os = "linux")]
mod sensor;
