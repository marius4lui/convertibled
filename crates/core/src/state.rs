use serde::{Deserialize, Serialize};

pub const SCHEMA_VERSION: u32 = 1;
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "kebab-case")]
pub enum Posture {
    Laptop,
    Folded,
    #[default]
    Unknown,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "kebab-case")]
pub enum Orientation {
    Normal,
    LeftUp,
    RightUp,
    BottomUp,
    #[default]
    Unknown,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Profile {
    Laptop,
    Tablet,
    Stand,
    Tent,
}
impl Profile {
    pub fn parse(value: &str) -> Result<Option<Self>, String> {
        match value {
            "auto" => Ok(None),
            "laptop" => Ok(Some(Self::Laptop)),
            "tablet" => Ok(Some(Self::Tablet)),
            "stand" => Ok(Some(Self::Stand)),
            "tent" => Ok(Some(Self::Tent)),
            _ => Err("Choose auto, laptop, tablet, stand or tent".into()),
        }
    }
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Observation {
    pub posture: Posture,
    pub orientation: Orientation,
    pub source: String,
}
impl Default for Observation {
    fn default() -> Self {
        Self {
            posture: Posture::Unknown,
            orientation: Orientation::Unknown,
            source: "unavailable".into(),
        }
    }
}
#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq, Eq)]
pub struct Desired {
    pub tablet_workspace: bool,
    pub rotation_lock: bool,
    pub rotation_lock_requested: bool,
    pub rotation: crate::config::Action,
    pub osk: crate::config::Action,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct ActionOutcome {
    pub requested: crate::config::Action,
    pub applied: crate::config::Action,
    pub status: String,
    pub error: Option<String>,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Applied {
    pub tablet_workspace: bool,
    pub rotation_lock: bool,
    pub status: String,
    pub error: Option<String>,
    #[serde(default)]
    pub action_outcomes: std::collections::BTreeMap<String, ActionOutcome>,
}
impl Default for Applied {
    fn default() -> Self {
        Self {
            tablet_workspace: false,
            rotation_lock: false,
            status: "unavailable".into(),
            action_outcomes: Default::default(),
            error: Some("GNOME extension has not reported applied state".into()),
        }
    }
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Status {
    pub schema_version: u32,
    pub revision: u64,
    pub observation: Observation,
    pub profile: Profile,
    pub manual_override: Option<Profile>,
    pub desired: Desired,
    pub applied: Applied,
    pub active: bool,
    pub locked: bool,
}
impl Default for Status {
    fn default() -> Self {
        Self {
            schema_version: SCHEMA_VERSION,
            revision: 0,
            observation: Observation::default(),
            profile: Profile::Laptop,
            manual_override: None,
            desired: Desired::default(),
            applied: Applied::default(),
            active: false,
            locked: false,
        }
    }
}
impl Status {
    pub fn reconcile(&mut self) {
        self.profile = self
            .manual_override
            .unwrap_or(match self.observation.posture {
                Posture::Folded => Profile::Tablet,
                _ => Profile::Laptop,
            });
        self.desired.tablet_workspace =
            self.active && !self.locked && self.profile != Profile::Laptop;
        self.revision = self.revision.saturating_add(1);
    }
    pub fn apply_config(&mut self, config: &crate::config::Config) {
        let key = match self.profile {
            Profile::Laptop => "laptop",
            Profile::Tablet => "tablet",
            Profile::Stand => "stand",
            Profile::Tent => "tent",
        };
        let profile = config.profiles.get(key).cloned().unwrap_or_default();
        self.desired.rotation = profile.rotation;
        self.desired.osk = profile.osk;
    }
    pub fn set_profile(&mut self, profile: &str) -> Result<(), String> {
        self.manual_override = Profile::parse(profile)?;
        self.reconcile();
        Ok(())
    }
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Capability {
    pub supported: bool,
    pub reason: String,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Capabilities {
    pub schema_version: u32,
    pub tablet_workspace: Capability,
    pub rotation: Capability,
    pub rotation_lock: Capability,
    pub osk: Capability,
    pub split_view: Capability,
    pub internal_input_suppression: Capability,
    pub scaling: Capability,
}
impl Default for Capabilities {
    fn default() -> Self {
        let unavailable = |reason: &str| Capability {
            supported: false,
            reason: reason.into(),
        };
        Self {
            schema_version: 1,
            tablet_workspace: unavailable("GNOME extension not connected"),
            rotation: unavailable("GNOME owns display rotation"),
            rotation_lock: unavailable("GNOME extension not connected"),
            osk: unavailable("GNOME extension not connected"),
            split_view: unavailable("GNOME extension not connected"),
            internal_input_suppression: unavailable(
                "Requires physical assignment and crash recovery proof",
            ),
            scaling: unavailable("Automatic scaling is disabled"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn manual_profiles_do_not_invent_observations() {
        let mut state = Status {
            active: true,
            ..Status::default()
        };
        state.set_profile("tent").unwrap();
        assert_eq!(state.observation.posture, Posture::Unknown);
        assert!(state.desired.tablet_workspace);
        assert_eq!(state.applied.status, "unavailable");
    }
    #[test]
    fn locked_or_inactive_sessions_never_request_workspace() {
        let mut state = Status::default();
        state.observation.posture = Posture::Folded;
        state.reconcile();
        assert!(!state.desired.tablet_workspace);
        state.active = true;
        state.reconcile();
        assert!(state.desired.tablet_workspace);
        state.locked = true;
        state.reconcile();
        assert!(!state.desired.tablet_workspace);
    }
    #[test]
    fn unknown_sensor_retains_manual_choice() {
        let mut state = Status::default();
        state.set_profile("stand").unwrap();
        state.reconcile();
        assert_eq!(state.profile, Profile::Stand);
        state.set_profile("auto").unwrap();
        assert_eq!(state.profile, Profile::Laptop);
        assert!(state.set_profile("shell command").is_err());
    }
    #[test]
    fn selected_profile_resolves_configured_actions() {
        let config = crate::config::Config::parse(
            "schema_version=1\n[profiles.tablet]\nrotation='enabled'\nosk='disabled'",
        )
        .unwrap();
        let mut state = Status {
            active: true,
            ..Status::default()
        };
        state.set_profile("tablet").unwrap();
        state.apply_config(&config);
        assert_eq!(state.desired.rotation, crate::config::Action::Enabled);
        assert_eq!(state.desired.osk, crate::config::Action::Disabled);
        state.set_profile("laptop").unwrap();
        state.apply_config(&config);
        assert_eq!(state.desired.rotation, crate::config::Action::Unchanged);
    }
}
