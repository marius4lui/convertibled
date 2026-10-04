use convertibled_core::{Applied, Capabilities, Status};
use std::sync::Arc;
use tokio::sync::RwLock;
use zbus::{Connection, message::Header, object_server::SignalEmitter};

pub struct Api {
    pub state: Arc<RwLock<Status>>,
    pub capabilities: Arc<RwLock<Capabilities>>,
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
        let applied: Applied = serde_json::from_value(value.clone()).map_err(failed)?;
        if !matches!(
            applied.status.as_str(),
            "applied" | "failed" | "unsupported" | "unavailable"
        ) {
            return Err(failed("Invalid applied status"));
        }
        if applied.error.as_ref().is_some_and(|text| text.len() > 2048) {
            return Err(failed("Error exceeds 2048 bytes"));
        }
        let mut state = self.state.write().await;
        if applied.tablet_workspace && (!state.active || state.locked) {
            return Err(failed(
                "Workspace cannot be applied in inactive or locked session",
            ));
        }
        let changed = state.applied != applied;
        state.applied = applied;
        if let Some(workspace) = value
            .pointer("/capabilities/tablet_workspace")
            .and_then(|v| v.as_bool())
        {
            let mut caps = self.capabilities.write().await;
            caps.tablet_workspace.supported = workspace;
            caps.tablet_workspace.reason = if workspace {
                "GNOME extension connected"
            } else {
                "GNOME extension unavailable"
            }
            .into();
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
        state.desired.rotation_lock = candidate.rotation_lock.unwrap_or(false);
        state.desired.rotation_lock_requested = candidate.rotation_lock.is_some();
        state.reconcile();
        let json = serde_json::to_string(&*state).map_err(failed)?;
        drop(state);
        Self::changed(&emitter, &json)
            .await
            .map_err(|e| zbus::fdo::Error::Failed(e.to_string()))
    }
    #[zbus(signal)]
    pub async fn changed(emitter: &SignalEmitter<'_>, status: &str) -> zbus::Result<()>;
}
