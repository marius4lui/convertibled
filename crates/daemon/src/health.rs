use std::{fs, io::Write, os::unix::fs::OpenOptionsExt};
use zbus::{Connection, message::Header};
pub async fn record(
    connection: &Connection,
    header: &Header<'_>,
    version: &str,
    healthy: bool,
) -> zbus::fdo::Result<()> {
    if version != env!("CARGO_PKG_VERSION") {
        return Err(zbus::fdo::Error::InvalidArgs(
            "Shell version differs from running daemon".into(),
        ));
    }
    let sender = header
        .sender()
        .ok_or_else(|| zbus::fdo::Error::AccessDenied("Missing sender".into()))?;
    let bus = zbus::fdo::DBusProxy::new(connection)
        .await
        .map_err(failed)?;
    let uid = bus.get_connection_unix_user(sender.clone().into()).await?;
    let pid = bus
        .get_connection_unix_process_id(sender.clone().into())
        .await?;
    let manager = zbus::Proxy::new(
        connection,
        "org.freedesktop.login1",
        "/org/freedesktop/login1",
        "org.freedesktop.login1.Manager",
    )
    .await
    .map_err(failed)?;
    type Sessions = Vec<(String, u32, String, String, zbus::zvariant::OwnedObjectPath)>;
    let sessions: Sessions = manager.call("ListSessions", &()).await.map_err(failed)?;
    let mut eligible = 0;
    for (_, owner, _, seat, path) in sessions {
        if owner != uid || seat.is_empty() {
            continue;
        }
        let proxy = zbus::Proxy::new(
            connection,
            "org.freedesktop.login1",
            path,
            "org.freedesktop.login1.Session",
        )
        .await
        .map_err(failed)?;
        let active = proxy.get_property::<bool>("Active").await.unwrap_or(false);
        let remote = proxy.get_property::<bool>("Remote").await.unwrap_or(true);
        let locked = proxy
            .get_property::<bool>("LockedHint")
            .await
            .unwrap_or(true);
        let kind = proxy
            .get_property::<String>("Type")
            .await
            .unwrap_or_default();
        if active && !remote && !locked && kind == "wayland" {
            eligible += 1;
        }
    }
    if eligible != 1 {
        return Err(zbus::fdo::Error::AccessDenied(
            "Requires one unlocked active local session".into(),
        ));
    }
    // PID is retrieved from bus credentials, never supplied by the client.
    if pid == 0 {
        return Err(zbus::fdo::Error::AccessDenied(
            "Invalid caller process".into(),
        ));
    }
    let receipt = serde_json::json!({"schema":1,"version":version,"healthy":healthy});
    let directory = std::path::Path::new("/var/lib/convertibled/health");
    let temporary = directory.join(format!(".shell-health-{}.tmp", std::process::id()));
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(&temporary)
        .map_err(failed)?;
    let result = (|| -> std::io::Result<()> {
        file.write_all(receipt.to_string().as_bytes())?;
        file.sync_all()?;
        fs::rename(&temporary, directory.join("shell-health.json"))?;
        fs::File::open(directory)?.sync_all()?;
        Ok(())
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result.map_err(failed)
}
fn failed(error: impl ToString) -> zbus::fdo::Error {
    zbus::fdo::Error::Failed(error.to_string())
}
