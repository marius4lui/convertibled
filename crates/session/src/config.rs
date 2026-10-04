use convertibled_core::config::Config;
use std::{io::Write, os::unix::fs::OpenOptionsExt, path::PathBuf};
pub fn config_path() -> PathBuf {
    std::env::var_os("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("HOME").map(|value| PathBuf::from(value).join(".config")))
        .unwrap_or_else(|| PathBuf::from("/nonexistent"))
        .join("convertibled/config.toml")
}
fn system() -> Result<Config, String> {
    match std::fs::read_to_string("/etc/convertibled/config.toml") {
        Ok(text) => Config::parse(&text),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(Config::default()),
        Err(e) => Err(e.to_string()),
    }
}
pub fn load() -> Result<Config, String> {
    let system = system()?;
    match std::fs::read_to_string(config_path()) {
        Ok(text) => system.merge_user(Config::parse(&text)?),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(system),
        Err(e) => Err(e.to_string()),
    }
}
pub fn save(input: &str) -> Result<Config, String> {
    if input.len() > 65536 {
        return Err("Configuration exceeds 64 KiB".into());
    }
    let user = Config::parse(input)?;
    let merged = system()?.merge_user(user.clone())?;
    let path = config_path();
    let parent = path.parent().ok_or("Invalid configuration path")?;
    std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    let temporary = parent.join(format!(".config-{}.tmp", std::process::id()));
    let result = (|| -> Result<(), String> {
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(&temporary)
            .map_err(|e| e.to_string())?;
        file.write_all(user.to_toml()?.as_bytes())
            .map_err(|e| e.to_string())?;
        file.sync_all().map_err(|e| e.to_string())?;
        if path.is_file() {
            std::fs::copy(&path, parent.join("config.toml.previous")).map_err(|e| e.to_string())?;
        }
        std::fs::rename(&temporary, &path).map_err(|e| e.to_string())?;
        std::fs::File::open(parent)
            .and_then(|f| f.sync_all())
            .map_err(|e| e.to_string())?;
        Ok(())
    })();
    if result.is_err() {
        let _ = std::fs::remove_file(&temporary);
    }
    result?;
    Ok(merged)
}
