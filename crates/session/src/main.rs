#[cfg(target_os = "linux")]
mod api;
#[cfg(target_os = "linux")]
mod service;
#[cfg(target_os = "linux")]
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    service::run().await
}
#[cfg(not(target_os = "linux"))]
fn main() {
    eprintln!("convertibled-session requires Linux logind and D-Bus");
    std::process::exit(3);
}
#[cfg(target_os = "linux")]
mod config;
