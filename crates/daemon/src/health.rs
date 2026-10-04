use std::{fs, io::Write, os::unix::fs::OpenOptionsExt};
use zbus::{Connection, message::Header};
pub async fn record(
    connection: &Connection,
    header: &Header<'_>,
    version: &str,
    healthy: bool,
) -> zbus::fdo::Result<()> {
    let (uid, session, boot_id) = authorize(connection, header, version).await?;
    let receipt = serde_json::json!({"schema":1,"version":version,"healthy":healthy,"uid":uid,"session":session,"boot_id":boot_id});
    let directory = std::path::Path::new("/var/lib/convertibled/health");
    write_receipt(directory, &format!("shell-health-{uid}.json"), &receipt).map_err(failed)?;
    write_receipt(directory, "shell-health.json", &receipt).map_err(failed)
}

pub async fn expectation(
    connection: &Connection,
    header: &Header<'_>,
    version: &str,
    known: bool,
    enabled: bool,
) -> zbus::fdo::Result<()> {
    let (uid, session, boot_id) = authorize(connection, header, version).await?;
    let expected = known.then_some(enabled);
    let receipt = serde_json::json!({"schema":1,"version":version,"expected":expected,"uid":uid,"session":session,"boot_id":boot_id});
    write_receipt(
        std::path::Path::new("/var/lib/convertibled/health"),
        &format!("shell-intent-{uid}.json"),
        &receipt,
    )
    .map_err(failed)
}

async fn authorize(
    connection: &Connection,
    header: &Header<'_>,
    version: &str,
) -> zbus::fdo::Result<(u32, String, String)> {
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
    if sessions.len() > 512 {
        return Err(failed("Session inventory exceeds supported size"));
    }
    let mut eligible = Vec::new();
    for (id, owner, _, seat, path) in sessions {
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
            if id.is_empty() || id.len() > 32 || !id.bytes().all(|c| c.is_ascii_alphanumeric()) {
                return Err(failed("Invalid session identifier"));
            }
            eligible.push(id);
        }
    }
    if eligible.len() != 1 {
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
    let boot_id = fs::read_to_string("/proc/sys/kernel/random/boot_id").map_err(failed)?;
    let boot_id = boot_id.trim();
    if !valid_boot_id(boot_id) {
        return Err(failed("Invalid kernel boot identity"));
    }
    Ok((uid, eligible.remove(0), boot_id.to_owned()))
}
fn valid_boot_id(value: &str) -> bool {
    value.len() == 36
        && value.bytes().enumerate().all(|(index, c)| {
            if [8, 13, 18, 23].contains(&index) {
                c == b'-'
            } else {
                c.is_ascii_hexdigit()
            }
        })
}
fn write_receipt(
    directory: &std::path::Path,
    name: &str,
    receipt: &serde_json::Value,
) -> std::io::Result<()> {
    let temporary = directory.join(format!(".{name}-{}.tmp", std::process::id()));
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(&temporary)?;
    let result = (|| -> std::io::Result<()> {
        file.write_all(receipt.to_string().as_bytes())?;
        file.sync_all()?;
        fs::rename(&temporary, directory.join(name))?;
        fs::File::open(directory)?.sync_all()?;
        Ok(())
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result
}
fn failed(error: impl ToString) -> zbus::fdo::Error {
    zbus::fdo::Error::Failed(error.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn boot_identity_must_be_a_kernel_uuid() {
        assert!(valid_boot_id("2d2a6a12-c8ae-4f66-8132-f0aa50031c0e"));
        for value in [
            "",
            "../other",
            "2d2a6a12_c8ae-4f66-8132-f0aa50031c0e",
            "2d2a6a12-c8ae-4f66-8132-f0aa50031c0g",
        ] {
            assert!(!valid_boot_id(value));
        }
    }
}
