use crate::hardware::{self, Device};
use convertibled_core::{Capabilities, Confidence, Observation, Posture, debounce::Debouncer};
use futures_lite::StreamExt;
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
        serde_json::json!({"schema_version":1,"version":env!("CARGO_PKG_VERSION"),"backend":"evdev-sensor-proxy","revision":data.revision,"observation":data.observation}).to_string()
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
    async fn report_shell_expectation(
        &self,
        version: &str,
        known: bool,
        enabled: bool,
        #[zbus(connection)] connection: &Connection,
        #[zbus(header)] header: zbus::message::Header<'_>,
    ) -> zbus::fdo::Result<()> {
        tokio::time::timeout(
            Duration::from_secs(3),
            crate::health::expectation(connection, &header, version, known, enabled),
        )
        .await
        .map_err(|_| zbus::fdo::Error::Failed("Authorization timed out".into()))?
    }
    #[zbus(signal)]
    async fn changed(emitter: &SignalEmitter<'_>, status: &str) -> zbus::Result<()>;
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
    let logind = zbus::Proxy::new(
        &connection,
        "org.freedesktop.login1",
        "/org/freedesktop/login1",
        "org.freedesktop.login1.Manager",
    )
    .await?;
    let mut sleep_events = logind.receive_signal("PrepareForSleep").await?;
    let mut terminate = tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())?;
    let mut interval = tokio::time::interval(Duration::from_millis(250));
    let mut sensor = crate::sensor::Sensor::default();
    let mut suspended = false;
    loop {
        tokio::select! {
            _=tokio::signal::ctrl_c()=>break,
            _=terminate.recv()=>break,
            signal=sleep_events.next()=>{
                let Some(signal)=signal else{return Err("logind signal stream closed".into());};
                if let Ok((sleeping,))=signal.body().deserialize::<(bool,)>() {
                        suspended=sleeping;
                        debouncer.invalidate();sensor.release(&connection).await;
                        let mut state=data.write().await;state.observation=Observation::default();state.revision=state.revision.saturating_add(1);
                        let json=serde_json::json!({"schema_version":1,"revision":state.revision,"observation":state.observation}).to_string();drop(state);
                        Api::changed(&emitter,&json).await?;
                }
                continue;
            },
            _=interval.tick()=>{}
        }
        if suspended {
            continue;
        }
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
            confidence: if posture == Posture::Unknown {
                Confidence::None
            } else {
                Confidence::DirectSwitch
            },
            orientation: sensor.sample(&connection, posture == Posture::Folded).await,
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
    sensor.release(&connection).await;
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
