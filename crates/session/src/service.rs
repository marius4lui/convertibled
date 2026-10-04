use crate::api::Api;
use convertibled_core::{Capabilities, Observation, Status};
use std::{sync::Arc, time::Duration};
use tokio::sync::RwLock;
use zbus::{Connection, object_server::SignalEmitter};

pub(crate) async fn session_state(connection: &Connection) -> (bool, bool) {
    use convertibled_core::authorization::{SessionCandidate, select_session};
    let Ok(manager) = zbus::Proxy::new(
        connection,
        "org.freedesktop.login1",
        "/org/freedesktop/login1",
        "org.freedesktop.login1.Manager",
    )
    .await
    else {
        return (false, true);
    };
    type SessionList = Vec<(String, u32, String, String, zbus::zvariant::OwnedObjectPath)>;
    let Ok(sessions) = manager.call::<_, _, SessionList>("ListSessions", &()).await else {
        return (false, true);
    };
    // SAFETY: geteuid has no arguments or side effects.
    let uid = unsafe { libc::geteuid() };
    let mut candidates = Vec::new();
    for (_, owner, _, seat, path) in sessions {
        if owner != uid {
            continue;
        }
        let Ok(session) = zbus::Proxy::new(
            connection,
            "org.freedesktop.login1",
            path,
            "org.freedesktop.login1.Session",
        )
        .await
        else {
            continue;
        };
        candidates.push(SessionCandidate {
            active: session
                .get_property::<bool>("Active")
                .await
                .unwrap_or(false),
            remote: session.get_property::<bool>("Remote").await.unwrap_or(true),
            wayland: session
                .get_property::<String>("Type")
                .await
                .unwrap_or_default()
                == "wayland",
            locked: session
                .get_property::<bool>("LockedHint")
                .await
                .unwrap_or(true),
            seat,
        });
    }
    select_session(&candidates)
}
async fn observation(connection: &Connection) -> Observation {
    let Ok(proxy) = zbus::Proxy::new(
        connection,
        "org.convertibled.Daemon1",
        "/org/convertibled/Daemon1",
        "org.convertibled.Daemon1",
    )
    .await
    else {
        return Observation::default();
    };
    let Ok(json) = proxy.call::<_, _, String>("GetStatus", &()).await else {
        return Observation::default();
    };
    serde_json::from_str::<serde_json::Value>(&json)
        .ok()
        .and_then(|v| {
            if v.get("schema_version")?.as_u64()? != 1 {
                return None;
            }
            serde_json::from_value(v.get("observation")?.clone()).ok()
        })
        .unwrap_or_default()
}
pub async fn run() -> Result<(), Box<dyn std::error::Error>> {
    let system = Connection::system().await?;
    tokio::spawn(crate::expectation::report(system.clone()));
    let config = crate::config::load()?;
    let mut initial = Status::default();
    initial.desired.rotation_lock = config.rotation_lock.unwrap_or(false);
    initial.desired.rotation_lock_requested = config.rotation_lock.is_some();
    initial.apply_config(&config);
    let config = Arc::new(RwLock::new(config));
    let state = Arc::new(RwLock::new(initial));
    let capabilities = Arc::new(RwLock::new(Capabilities::default()));
    let report_owner = Arc::new(RwLock::new(None::<String>));
    let connection = zbus::connection::Builder::session()?
        .name("org.convertibled.Session1")?
        .serve_at(
            "/org/convertibled/Session1",
            Api {
                state: state.clone(),
                system: system.clone(),
                capabilities: capabilities.clone(),
                report_owner: report_owner.clone(),
                config: config.clone(),
            },
        )?
        .build()
        .await?;
    let emitter = SignalEmitter::new(&connection, "/org/convertibled/Session1")?;
    let mut interval = tokio::time::interval(Duration::from_millis(500));
    let mut terminate = tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())?;
    loop {
        tokio::select! { _ = tokio::signal::ctrl_c() => break, _=terminate.recv()=>break, _ = interval.tick() => {} }
        let (observed, session) = tokio::join!(
            tokio::time::timeout(Duration::from_secs(2), observation(&system)),
            tokio::time::timeout(Duration::from_secs(2), session_state(&system))
        );
        let observed = observed.unwrap_or_default();
        let (active, locked) = session.unwrap_or((false, true));
        let owner = report_owner.read().await.clone();
        let disconnected = if let Some(owner) = owner.as_deref() {
            let result = tokio::time::timeout(Duration::from_secs(2), async {
                let bus = zbus::fdo::DBusProxy::new(&connection).await?;
                let name = zbus::names::BusName::try_from(owner).map_err(zbus::Error::from)?;
                bus.name_has_owner(name).await.map_err(zbus::Error::from)
            })
            .await;
            !matches!(result, Ok(Ok(true)))
        } else {
            false
        };
        let mut status = state.write().await;
        if disconnected {
            *report_owner.write().await = None;
            status.applied = Default::default();
            *capabilities.write().await = Capabilities::default();
        }
        if disconnected
            || status.observation != observed
            || status.active != active
            || status.locked != locked
        {
            status.observation = observed;
            status.active = active;
            status.locked = locked;
            status.reconcile();
            status.apply_config(&*config.read().await);
            let json = serde_json::to_string(&*status)?;
            drop(status);
            Api::changed(&emitter, &json).await?;
        }
    }
    Ok(())
}
