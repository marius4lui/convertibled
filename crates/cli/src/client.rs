use crate::args::{Args, Command, ConfigCommand, UpdateCommand};
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
    if let Command::Update { command } = &args.command {
        return update(command).await;
    }
    if let Command::Doctor { export } = &args.command {
        return doctor(export.as_deref(), args.json).await;
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
        Command::Config {
            command: ConfigCommand::Show,
        } => {
            let text: String = proxy
                .call("GetConfig", &())
                .await
                .map_err(|e| e.to_string())?;
            if args.json {
                Ok(serde_json::json!({"schema_version":1,"toml":text}).to_string())
            } else {
                Ok(text)
            }
        }
        Command::Config {
            command: ConfigCommand::Save { path },
        } => {
            let text = std::fs::read_to_string(path).map_err(|e| e.to_string())?;
            convertibled_core::config::Config::parse(&text)?;
            proxy
                .call::<_, _, ()>("SaveConfig", &(text,))
                .await
                .map_err(|e| e.to_string())?;
            Ok("Configuration saved and reloaded".into())
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
async fn update(action: &UpdateCommand) -> Result<String, String> {
    let mut command = if matches!(action, UpdateCommand::Status) {
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
        .args(action.arguments())
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

async fn doctor(export: Option<&std::path::Path>, json: bool) -> Result<String, String> {
    let mut status = None;
    let mut capabilities = None;
    let mut device_count = None;
    if let Ok(connection) = Connection::session().await
        && let Ok(proxy) = session(&connection).await
    {
        if let Ok(raw) = proxy.call::<_, _, String>("GetStatus", &()).await {
            status = serde_json::from_str::<convertibled_core::Status>(&raw).ok();
        }
        if let Ok(raw) = proxy.call::<_, _, String>("GetCapabilities", &()).await {
            capabilities = serde_json::from_str::<convertibled_core::Capabilities>(&raw).ok();
        }
    }
    if let Ok(connection) = Connection::system().await
        && let Ok(proxy) = daemon(&connection).await
        && let Ok(raw) = proxy.call::<_, _, String>("GetDevices", &()).await
    {
        device_count = serde_json::from_str::<Vec<serde_json::Value>>(&raw)
            .ok()
            .map(|v| v.len());
    }
    let report = convertibled_core::diagnostics::report(
        status.as_ref(),
        capabilities.as_ref(),
        device_count,
    )
    .to_string();
    if let Some(path) = export {
        use std::io::Write;
        use std::os::unix::fs::OpenOptionsExt;
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .mode(0o600)
            .open(path)
            .map_err(|e| e.to_string())?;
        file.write_all(report.as_bytes())
            .and_then(|_| file.sync_all())
            .map_err(|e| e.to_string())?;
    }
    render(report, json)
}
