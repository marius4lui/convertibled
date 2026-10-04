use crate::args::{Args, Command};
use zbus::{Connection, Proxy};
async fn session(connection: &Connection) -> Result<Proxy<'_>, String> {
    Proxy::new(
        connection,
        "org.convertibled.Session1",
        "/org/convertibled/Session1",
        "org.convertibled.Session1",
    )
    .await
    .map_err(|e| e.to_string())
}
async fn daemon(connection: &Connection) -> Result<Proxy<'_>, String> {
    Proxy::new(
        connection,
        "org.convertibled.Daemon1",
        "/org/convertibled/Daemon1",
        "org.convertibled.Daemon1",
    )
    .await
    .map_err(|e| e.to_string())
}
fn render(raw: String, json: bool) -> Result<String, String> {
    let value: serde_json::Value = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
    if json {
        Ok(raw)
    } else {
        serde_json::to_string_pretty(&value).map_err(|e| e.to_string())
    }
}
pub async fn run(args: &Args) -> Result<String, String> {
    if let Command::Update { action } = &args.command {
        return update(action).await;
    }
    let user = Connection::session()
        .await
        .map_err(|e| format!("Session bus unavailable: {e}"))?;
    let proxy = session(&user).await?;
    match &args.command {
        Command::Status => render(
            proxy
                .call("GetStatus", &())
                .await
                .map_err(|e| e.to_string())?,
            args.json,
        ),
        Command::Capabilities => render(
            proxy
                .call("GetCapabilities", &())
                .await
                .map_err(|e| e.to_string())?,
            args.json,
        ),
        Command::Devices => {
            let system = Connection::system().await.map_err(|e| e.to_string())?;
            render(
                daemon(&system)
                    .await?
                    .call("GetDevices", &())
                    .await
                    .map_err(|e| e.to_string())?,
                args.json,
            )
        }
        Command::Mode { profile } => {
            convertibled_core::Profile::parse(profile)?;
            proxy
                .call::<_, _, ()>("SetProfile", &(profile,))
                .await
                .map_err(|e| e.to_string())?;
            Ok("Profile requested; inspect status for applied result".into())
        }
        Command::RotationLock { value } => {
            proxy
                .call::<_, _, ()>("SetRotationLock", &(value == "on",))
                .await
                .map_err(|e| e.to_string())?;
            Ok("Rotation lock requested; inspect status for applied result".into())
        }
        Command::Watch { count } => {
            let mut previous = String::new();
            let mut emitted = 0;
            loop {
                let raw: String = proxy
                    .call("GetStatus", &())
                    .await
                    .map_err(|e| e.to_string())?;
                if raw != previous {
                    println!("{}", render(raw.clone(), args.json)?);
                    previous = raw;
                    emitted += 1;
                }
                if count.is_some_and(|limit| emitted >= limit) {
                    break;
                }
                tokio::select! {_=tokio::signal::ctrl_c()=>break,_=tokio::time::sleep(std::time::Duration::from_millis(500))=>{}}
            }
            Ok(String::new())
        }
        Command::Doctor { export } => {
            let raw: String = proxy
                .call("GetStatus", &())
                .await
                .map_err(|e| e.to_string())?;
            let mut value: serde_json::Value =
                serde_json::from_str(&raw).map_err(|e| e.to_string())?;
            // Keep known status fields only, excluding arbitrary backend diagnostics.
            if let Some(object) = value.as_object_mut() {
                object.retain(|key, _| {
                    [
                        "schema_version",
                        "revision",
                        "profile",
                        "manual_override",
                        "active",
                        "locked",
                        "desired",
                        "observation",
                    ]
                    .contains(&key.as_str())
                });
            }
            let report=serde_json::json!({"schema_version":1,"version":env!("CARGO_PKG_VERSION"),"physical_acceptance":false,"status":value,"checks":{"session_bus":"available","input_suppression":"disabled","scaling":"disabled"}}).to_string();
            if let Some(path) = export {
                std::fs::write(path, &report).map_err(|e| e.to_string())?;
            }
            render(report, args.json)
        }
        Command::Reload => {
            proxy
                .call::<_, _, ()>("Reload", &())
                .await
                .map_err(|e| e.to_string())?;
            Ok("Configuration reloaded".into())
        }
        _ => Err("Command unavailable".into()),
    }
}
async fn update(action: &str) -> Result<String, String> {
    let mut command = if action == "status" {
        let mut command = tokio::process::Command::new("/usr/bin/python3");
        command
            .arg("-I")
            .arg("/opt/convertibled/current/installer/cli.py");
        command
    } else {
        let mut command = tokio::process::Command::new("/usr/bin/pkexec");
        command.arg("/opt/convertibled/current/installer/cli.py");
        command
    };
    let status = command
        .arg(action)
        .status()
        .await
        .map_err(|e| format!("Updater unavailable: {e}"))?;
    if status.success() {
        Ok(String::new())
    } else {
        Err(format!(
            "Updater exited with {}",
            status.code().unwrap_or(3)
        ))
    }
}
