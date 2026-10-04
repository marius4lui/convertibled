use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Action {
    Enabled,
    Disabled,
    #[default]
    Unchanged,
}
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProfileConfig {
    #[serde(default)]
    pub rotation: Action,
    #[serde(default)]
    pub osk: Action,
    #[serde(default)]
    pub internal_keyboard: Action,
    #[serde(default)]
    pub internal_touchpad: Action,
    #[serde(default)]
    pub scaling: Action,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Config {
    pub schema_version: u32,
    #[serde(default = "default_debounce")]
    pub debounce_ms: u64,
    #[serde(default)]
    pub profiles: BTreeMap<String, ProfileConfig>,
    #[serde(default)]
    pub rotation_lock: Option<bool>,
}
fn default_debounce() -> u64 {
    300
}
impl Default for Config {
    fn default() -> Self {
        Self {
            schema_version: 1,
            debounce_ms: 300,
            profiles: BTreeMap::new(),
            rotation_lock: None,
        }
    }
}
impl Config {
    pub fn parse(input: &str) -> Result<Self, String> {
        let candidate: Self = toml::from_str(input).map_err(|e| e.to_string())?;
        candidate.validate()?;
        Ok(candidate)
    }
    pub fn validate(&self) -> Result<(), String> {
        if self.schema_version != 1 {
            return Err("Unsupported configuration schema; expected 1".into());
        }
        if !(50..=5000).contains(&self.debounce_ms) {
            return Err("debounce_ms must be 50..5000".into());
        }
        for (name, profile) in &self.profiles {
            if crate::Profile::parse(name)?.is_none() {
                return Err("auto is not a profile definition".into());
            }
            if profile.internal_keyboard != Action::Unchanged
                || profile.internal_touchpad != Action::Unchanged
            {
                return Err("Input suppression has not passed physical recovery acceptance".into());
            }
            if profile.scaling != Action::Unchanged {
                return Err("Automatic scaling is unavailable".into());
            }
        }
        Ok(())
    }
}
/// Validate the whole candidate before replacing the current configuration.
pub fn reload(current: &mut Config, input: &str) -> Result<(), String> {
    let candidate = Config::parse(input)?;
    *current = candidate;
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn failed_reload_preserves_previous_config() {
        let mut current = Config::default();
        assert!(reload(&mut current, "schema_version = 7").is_err());
        assert_eq!(current.schema_version, 1);
        assert!(reload(&mut current, "schema_version = 1\nunknown = true").is_err());
    }
    #[test]
    fn refuses_unproven_input_actions() {
        assert!(
            Config::parse("schema_version = 1\n[profiles.tablet]\ninternal_keyboard = 'disabled'")
                .is_err()
        );
        assert!(
            Config::parse("schema_version = 1\n[profiles.tablet]\nrotation = 'enabled'").is_ok()
        );
    }
    #[test]
    fn absent_rotation_lock_preserves_native_preference() {
        assert_eq!(
            Config::parse("schema_version = 1").unwrap().rotation_lock,
            None
        );
        assert_eq!(
            Config::parse("schema_version = 1\nrotation_lock = false")
                .unwrap()
                .rotation_lock,
            Some(false)
        );
    }
}
