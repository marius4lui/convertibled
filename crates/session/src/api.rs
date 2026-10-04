use convertibled_core::{Capabilities, Status};
use std::sync::Arc;
use tokio::sync::RwLock;
use zbus::{Connection, message::Header, object_server::SignalEmitter};

pub struct Api {
    pub state: Arc<RwLock<Status>>,
    pub capabilities: Arc<RwLock<Capabilities>>,
    pub config: Arc<RwLock<convertibled_core::config::Config>>,
}
async fn authorize(connection: &Connection, header: &Header<'_>) -> zbus::fdo::Result<()> {
    let sender = header
        .sender()
        .ok_or_else(|| zbus::fdo::Error::AccessDenied("Missing caller identity".into()))?;
    let bus = zbus::fdo::DBusProxy::new(connection)
        .await
        .map_err(|e| zbus::fdo::Error::Failed(e.to_string()))?;
    let uid = bus.get_connection_unix_user(sender.clone().into()).await?;
    // SAFETY: geteuid has no arguments or side effects.
    if uid != unsafe { libc::geteuid() } {
        return Err(zbus::fdo::Error::AccessDenied(
            "Caller does not own this user session".into(),
        ));
    }
    Ok(())
}
fn failed(error: impl ToString) -> zbus::fdo::Error {
    zbus::fdo::Error::InvalidArgs(error.to_string())
}
#[zbus::interface(name = "org.convertibled.Session1")]
impl Api {
    async fn get_status(&self) -> String {
        serde_json::to_string(&*self.state.read().await).unwrap_or_default()
    }
    async fn get_capabilities(&self) -> String {
        serde_json::to_string(&*self.capabilities.read().await).unwrap_or_default()
    }
    async fn set_profile(
        &self,
        profile: &str,
        #[zbus(connection)] connection: &Connection,
        #[zbus(header)] header: Header<'_>,
        #[zbus(signal_emitter)] emitter: SignalEmitter<'_>,
    ) -> zbus::fdo::Result<()> {
        authorize(connection, &header).await?;
        let mut state = self.state.write().await;
        if !state.active || state.locked {
            return Err(zbus::fdo::Error::AccessDenied(
                "Session is inactive or locked".into(),
            ));
        }
        state.set_profile(profile).map_err(failed)?;
        state.apply_config(&*self.config.read().await);
        let json = serde_json::to_string(&*state).map_err(failed)?;
        drop(state);
        Self::changed(&emitter, &json)
            .await
            .map_err(|e| zbus::fdo::Error::Failed(e.to_string()))
    }
    async fn set_rotation_lock(
        &self,
        locked: bool,
        #[zbus(connection)] connection: &Connection,
        #[zbus(header)] header: Header<'_>,
        #[zbus(signal_emitter)] emitter: SignalEmitter<'_>,
    ) -> zbus::fdo::Result<()> {
        authorize(connection, &header).await?;
        let mut state = self.state.write().await;
        if !state.active || state.locked {
            return Err(zbus::fdo::Error::AccessDenied(
                "Session is inactive or locked".into(),
            ));
        }
        state.desired.rotation_lock = locked;
        state.desired.rotation_lock_requested = true;
        state.reconcile();
        let json = serde_json::to_string(&*state).map_err(failed)?;
        drop(state);
        Self::changed(&emitter, &json)
            .await
            .map_err(|e| zbus::fdo::Error::Failed(e.to_string()))
    }
    async fn report_applied(
        &self,
        report: &str,
        #[zbus(connection)] connection: &Connection,
        #[zbus(header)] header: Header<'_>,
        #[zbus(signal_emitter)] emitter: SignalEmitter<'_>,
    ) -> zbus::fdo::Result<()> {
        authorize(connection, &header).await?;
        if report.len() > 8192 {
            return Err(failed("Report exceeds 8192 bytes"));
        }
        let value: serde_json::Value = serde_json::from_str(report).map_err(failed)?;
        let applied = convertibled_core::report::applied_report(report).map_err(failed)?;
        let mut state = self.state.write().await;
        if applied.tablet_workspace && (!state.active || state.locked) {
            return Err(failed(
                "Workspace cannot be applied in inactive or locked session",
            ));
        }
        let changed = state.applied != applied;
        state.applied = applied;
        if let Some(report) = value.get("capabilities").and_then(|v| v.as_object()) {
            let mut caps = self.capabilities.write().await;
            let caps = &mut *caps;
            for (key, target) in [
                ("tablet_workspace", &mut caps.tablet_workspace),
                ("rotation_lock", &mut caps.rotation_lock),
                ("osk", &mut caps.osk),
                ("split_view", &mut caps.split_view),
            ] {
                if let Some(supported) = report.get(key).and_then(|v| v.as_bool()) {
                    target.supported = supported;
                    target.reason = if supported {
                        "GNOME extension reports native support"
                    } else {
                        "GNOME capability unavailable"
                    }
                    .into();
                }
            }
        }
        if changed {
            state.revision = state.revision.saturating_add(1);
            let json = serde_json::to_string(&*state).map_err(failed)?;
            drop(state);
            Self::changed(&emitter, &json)
                .await
                .map_err(|e| zbus::fdo::Error::Failed(e.to_string()))?;
        }
        Ok(())
    }
    async fn report_shell_health(
        &self,
        version: &str,
        healthy: bool,
        #[zbus(connection)] connection: &Connection,
        #[zbus(header)] header: Header<'_>,
    ) -> zbus::fdo::Result<()> {
        authorize(connection, &header).await?;
        if version != env!("CARGO_PKG_VERSION") {
            return Err(failed("Shell version differs from session service"));
        }
        let system = Connection::system()
            .await
            .map_err(|e| zbus::fdo::Error::Failed(e.to_string()))?;
        let daemon = zbus::Proxy::new(
            &system,
            "org.convertibled.Daemon1",
            "/org/convertibled/Daemon1",
            "org.convertibled.Daemon1",
        )
        .await
        .map_err(|e| zbus::fdo::Error::Failed(e.to_string()))?;
        tokio::time::timeout(
            std::time::Duration::from_secs(3),
            daemon.call::<_, _, ()>("ReportShellHealth", &(version, healthy)),
        )
        .await
        .map_err(|_| zbus::fdo::Error::Failed("Shell health report timed out".into()))?
        .map_err(|e| zbus::fdo::Error::Failed(e.to_string()))
    }
    async fn get_config(&self) -> zbus::fdo::Result<String> {
        self.config.read().await.to_toml().map_err(failed)
    }
    async fn save_config(
        &self,
        input: &str,
        #[zbus(connection)] connection: &Connection,
        #[zbus(header)] header: Header<'_>,
        #[zbus(signal_emitter)] emitter: SignalEmitter<'_>,
    ) -> zbus::fdo::Result<()> {
        authorize(connection, &header).await?;
        if input.len() > 65536 {
            return Err(failed("Configuration exceeds 64 KiB"));
        }
        let mut state = self.state.write().await;
        if !state.active || state.locked {
            return Err(zbus::fdo::Error::AccessDenied(
                "Session is inactive or locked".into(),
            ));
        }
        let input = input.to_owned();
        let candidate = tokio::task::spawn_blocking(move || crate::config::save(&input))
            .await
            .map_err(failed)?
            .map_err(failed)?;
        state.desired.rotation_lock = candidate.rotation_lock.unwrap_or(false);
        state.desired.rotation_lock_requested = candidate.rotation_lock.is_some();
        state.reconcile();
        state.apply_config(&candidate);
        *self.config.write().await = candidate;
        let json = serde_json::to_string(&*state).map_err(failed)?;
        drop(state);
        Self::changed(&emitter, &json)
            .await
            .map_err(|e| zbus::fdo::Error::Failed(e.to_string()))
    }
    async fn reload(
        &self,
        #[zbus(connection)] connection: &Connection,
        #[zbus(header)] header: Header<'_>,
        #[zbus(signal_emitter)] emitter: SignalEmitter<'_>,
    ) -> zbus::fdo::Result<()> {
        authorize(connection, &header).await?;
        let candidate = crate::config::load().map_err(failed)?;
        let mut state = self.state.write().await;
        if !state.active || state.locked {
            return Err(zbus::fdo::Error::AccessDenied(
                "Session is inactive or locked".into(),
            ));
        }
        *self.config.write().await = candidate.clone();
        state.desired.rotation_lock = candidate.rotation_lock.unwrap_or(false);
        state.desired.rotation_lock_requested = candidate.rotation_lock.is_some();
        state.reconcile();
        state.apply_config(&candidate);
        let json = serde_json::to_string(&*state).map_err(failed)?;
        drop(state);
        Self::changed(&emitter, &json)
            .await
            .map_err(|e| zbus::fdo::Error::Failed(e.to_string()))
    }
    #[zbus(signal)]
    pub async fn changed(emitter: &SignalEmitter<'_>, status: &str) -> zbus::Result<()>;
}
