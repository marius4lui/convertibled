use convertibled_core::config::Config;
use std::path::PathBuf;
pub fn config_path() -> PathBuf {
    std::env::var_os("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("HOME").map(|value| PathBuf::from(value).join(".config")))
        .unwrap_or_else(|| PathBuf::from("/nonexistent"))
        .join("convertibled/config.toml")
}
pub fn load() -> Result<Config, String> {
    let system = match std::fs::read_to_string("/etc/convertibled/config.toml") {
        Ok(text) => Config::parse(&text)?,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Config::default(),
        Err(e) => return Err(e.to_string()),
    };
    match std::fs::read_to_string(config_path()) {
        Ok(text) => {
            let user = Config::parse(&text)?;
            let mut merged = system;
            merged.rotation_lock = user.rotation_lock;
            merged.profiles.extend(user.profiles);
            // System debounce and authorization are not weakened by user settings.
            merged.validate()?;
            Ok(merged)
        }
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(system),
        Err(e) => Err(e.to_string()),
    }
}
