use crate::{Capabilities, Status};
use serde_json::{Value, json};
/// Export an explicit allowlist; never include arbitrary backend errors/identifiers.
pub fn report(
    status: Option<&Status>,
    capabilities: Option<&Capabilities>,
    device_count: Option<usize>,
) -> Value {
    let state=status.map(|state|json!({
        "profile":state.profile,"manual_override":state.manual_override,
        "active":state.active,"locked":state.locked,
        "observation":{"posture":state.observation.posture,"orientation":state.observation.orientation},
        "desired":state.desired,
        "applied":{"tablet_workspace":state.applied.tablet_workspace,"rotation_lock":state.applied.rotation_lock,"status":state.applied.status,
            "actions":state.applied.action_outcomes.iter().map(|(key,value)|(key.clone(),json!({"requested":value.requested,"applied":value.applied,"status":value.status}))).collect::<serde_json::Map<String,Value>>()},
    }));
    let supported=capabilities.map(|caps|json!({"tablet_workspace":caps.tablet_workspace.supported,"rotation_lock":caps.rotation_lock.supported,"osk":caps.osk.supported,"split_view":caps.split_view.supported,"input_suppression":caps.internal_input_suppression.supported,"scaling":caps.scaling.supported}));
    json!({"schema_version":1,"version":env!("CARGO_PKG_VERSION"),"physical_acceptance":false,
        "status":state,"capabilities":supported,"tablet_switch_devices":device_count,
        "checks":{"session_service":if status.is_some(){"available"}else{"unavailable"},"hardware_service":if device_count.is_some(){"available"}else{"unavailable"}}})
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn strips_backend_errors_and_device_identifiers() {
        let mut state = Status::default();
        state.applied.error = Some("/home/private/person/key.pem serial ABC".into());
        state.observation.source = "private-device-id".into();
        let export = report(Some(&state), None, Some(1)).to_string();
        assert!(!export.contains("private"));
        assert!(!export.contains("ABC"));
        assert!(export.contains("unavailable"));
        assert!(export.contains("tablet_switch_devices"));
    }
    #[test]
    fn unavailable_service_still_produces_diagnostic_report() {
        let export = report(None, None, None);
        assert_eq!(export["physical_acceptance"], false);
        assert!(export["status"].is_null());
        assert_eq!(export["checks"]["session_service"], "unavailable");
    }
}
