use crate::hardware::{self, Device};
use convertibled_core::{Capabilities, Observation, Orientation, debounce::Debouncer};
use std::{
    sync::Arc,
    time::{Duration, Instant},
};
use tokio::sync::RwLock;
use zbus::{Connection, object_server::SignalEmitter};

#[derive(Default)]
struct Data {
    observation: Observation,
    devices: Vec<Device>,
    revision: u64,
}
struct Api(Arc<RwLock<Data>>);
#[zbus::interface(name = "org.convertibled.Daemon1")]
impl Api {
    async fn get_status(&self) -> String {
        let data = self.0.read().await;
        serde_json::json!({"schema_version":1,"revision":data.revision,"observation":data.observation}).to_string()
    }
    async fn get_devices(&self) -> String {
        serde_json::to_string(&self.0.read().await.devices).unwrap_or_else(|_| "[]".into())
    }
    fn get_capabilities(&self) -> String {
        serde_json::to_string(&Capabilities::default()).unwrap_or_default()
    }
    async fn report_shell_health(
        &self,
        version: &str,
        healthy: bool,
        #[zbus(connection)] connection: &Connection,
        #[zbus(header)] header: zbus::message::Header<'_>,
    ) -> zbus::fdo::Result<()> {
        tokio::time::timeout(
            Duration::from_secs(3),
            crate::health::record(connection, &header, version, healthy),
        )
        .await
        .map_err(|_| zbus::fdo::Error::Failed("Authorization timed out".into()))?
    }
    #[zbus(signal)]
    async fn changed(emitter: &SignalEmitter<'_>, status: &str) -> zbus::Result<()>;
}
async fn orientation(connection: &Connection) -> Orientation {
    let Ok(proxy) = zbus::Proxy::new(
        connection,
        "net.hadess.SensorProxy",
        "/net/hadess/SensorProxy",
        "net.hadess.SensorProxy",
    )
    .await
    else {
        return Orientation::Unknown;
    };
    match proxy
        .get_property::<String>("AccelerometerOrientation")
        .await
        .as_deref()
    {
        Ok("normal") => Orientation::Normal,
        Ok("left-up") => Orientation::LeftUp,
        Ok("right-up") => Orientation::RightUp,
        Ok("bottom-up") => Orientation::BottomUp,
        _ => Orientation::Unknown,
    }
}
pub async fn run() -> Result<(), Box<dyn std::error::Error>> {
    let config = match std::fs::read_to_string("/etc/convertibled/config.toml") {
        Ok(text) => convertibled_core::config::Config::parse(&text)?,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Default::default(),
        Err(error) => return Err(error.into()),
    };
    let data = Arc::new(RwLock::new(Data::default()));
    let connection = zbus::connection::Builder::system()?
        .name("org.convertibled.Daemon1")?
        .serve_at("/org/convertibled/Daemon1", Api(data.clone()))?
        .build()
        .await?;
    // SensorProxy owns hardware and GNOME owns claim lifecycle. Read available
    // orientation without competing accelerometer claims or rotation actions.
    let emitter = SignalEmitter::new(&connection, "/org/convertibled/Daemon1")?;
    let start = Instant::now();
    let mut debouncer = Debouncer::new(Duration::from_millis(config.debounce_ms));
    let mut interval = tokio::time::interval(Duration::from_millis(250));
    loop {
        tokio::select! { _ = tokio::signal::ctrl_c() => break, _ = interval.tick() => {} }
        // Rediscovery + fresh ioctl every tick covers initial, reconnect and resume.
        let devices = tokio::task::spawn_blocking(hardware::discover).await?;
        let available: Vec<bool> = devices
            .iter()
            .filter_map(|device| device.tablet_mode)
            .collect();
        // Failed observations must not leave a previous folded state authoritative.
        let samples = if devices.iter().any(|device| device.error.is_some()) {
            &[][..]
        } else {
            &available[..]
        };
        let posture = debouncer.sample(samples, start.elapsed());
        let current = Observation {
            posture,
            orientation: orientation(&connection).await,
            source: if samples.is_empty() {
                "unavailable"
            } else {
                "evdev-switch"
            }
            .into(),
        };
        let mut state = data.write().await;
        state.devices = devices;
        if state.observation != current {
            state.observation = current;
            state.revision = state.revision.saturating_add(1);
            let json = serde_json::json!({"schema_version":1,"revision":state.revision,"observation":state.observation}).to_string();
            drop(state);
            Api::changed(&emitter, &json).await?;
        }
    }
    Ok(())
}

pub fn check() -> Result<(), Box<dyn std::error::Error>> {
    if std::env::consts::ARCH != "x86_64" {
        return Err("Release supports x86_64 only".into());
    }
    if !std::path::Path::new("/sys/class/input").is_dir() {
        return Err("Linux input subsystem unavailable".into());
    }
    let config = match std::fs::read_to_string("/etc/convertibled/config.toml") {
        Ok(text) => convertibled_core::config::Config::parse(&text)?,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Default::default(),
        Err(error) => return Err(error.into()),
    };
    config.validate()?;
    println!(
        "{}",
        serde_json::json!({"schema_version":1,"version":env!("CARGO_PKG_VERSION"),"platform":"linux-x86_64","configuration":"valid","physical_acceptance":false})
    );
    Ok(())
}
