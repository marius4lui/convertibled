use crate::Applied;
/// Parse bounded extension reports independently of transport credentials.
pub fn applied_report(report: &str) -> Result<Applied, String> {
    if report.len() > 8192 {
        return Err("Report exceeds 8192 bytes".into());
    }
    let applied: Applied = serde_json::from_str(report).map_err(|e| e.to_string())?;
    if !matches!(
        applied.status.as_str(),
        "applied" | "failed" | "unsupported" | "unavailable"
    ) {
        return Err("Invalid applied status".into());
    }
    if applied.error.as_ref().is_some_and(|text| text.len() > 2048) {
        return Err("Error exceeds 2048 bytes".into());
    }
    for (key, outcome) in &applied.action_outcomes {
        if !matches!(key.as_str(), "rotation" | "osk") {
            return Err("Unknown action outcome".into());
        }
        if !matches!(
            outcome.status.as_str(),
            "applied" | "failed" | "unsupported" | "unavailable"
        ) {
            return Err("Invalid action outcome status".into());
        }
        if outcome.error.as_ref().is_some_and(|text| text.len() > 2048) {
            return Err("Action error exceeds 2048 bytes".into());
        }
    }
    Ok(applied)
}
/// Normalize the Shell's partial capability report without inventing support.
/// Rotation profile actions and rotation lock use the same native preference.
pub fn capabilities_report(
    report: &serde_json::Value,
    previous: &crate::Capabilities,
) -> Result<crate::Capabilities, String> {
    let mut candidate = previous.clone();
    if let Some(value) = report.get("capabilities") {
        let values = value.as_object().ok_or("Capabilities must be an object")?;
        for (key, value) in values {
            if key == "gesture_reason" {
                let reason = value.as_str().ok_or("Gesture reason must be a string")?;
                if reason.len() > 2048 {
                    return Err("Gesture reason exceeds 2048 bytes".into());
                }
                continue;
            }
            let target = match key.as_str() {
                "tablet_workspace" => &mut candidate.tablet_workspace,
                "rotation_lock" => &mut candidate.rotation_lock,
                "osk" => &mut candidate.osk,
                "split_view" => &mut candidate.split_view,
                "touchscreen_gestures" => &mut candidate.touchscreen_gestures,
                _ => return Err("Unknown reported capability".into()),
            };
            target.supported = value
                .as_bool()
                .ok_or("Capability support must be boolean")?;
            target.reason = if target.supported {
                "GNOME extension reports native support"
            } else {
                "GNOME capability unavailable"
            }
            .into();
        }
        if values.contains_key("rotation_lock") {
            candidate.rotation = candidate.rotation_lock.clone();
            if candidate.rotation.supported {
                candidate.rotation.reason="Native rotation preference available; GNOME owns orientation and touch mapping".into();
            }
        }
        if let Some(reason) = values.get("gesture_reason").and_then(|v| v.as_str()) {
            candidate.touchscreen_gestures.reason = reason.into();
        }
    }
    if report.get("status").and_then(|v| v.as_str()) == Some("unavailable") {
        candidate = crate::Capabilities::default();
    }
    Ok(candidate)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn accepts_action_outcomes_without_assuming_all_succeeded() {
        let report = r#"{"tablet_workspace":true,"rotation_lock":false,"status":"applied","error":null,"action_outcomes":{"osk":{"requested":"enabled","applied":"disabled","status":"unsupported","error":"missing preference"}}}"#;
        let result = applied_report(report).unwrap();
        assert!(result.tablet_workspace);
        assert_eq!(result.action_outcomes["osk"].status, "unsupported");
    }
    #[test]
    fn rejects_unbounded_or_unknown_outcomes() {
        assert!(applied_report(&"x".repeat(8193)).is_err());
        assert!(applied_report(r#"{"tablet_workspace":true,"rotation_lock":false,"status":"invented","error":null}"#).is_err());
    }
    #[test]
    fn native_capabilities_match_profile_actions_and_cleanup() {
        let report = serde_json::json!({"status":"applied","capabilities":{"tablet_workspace":true,"rotation_lock":true,"osk":true,"split_view":true,"touchscreen_gestures":false,"gesture_reason":"No approved integrated touchscreen"}});
        let connected = capabilities_report(&report, &crate::Capabilities::default()).unwrap();
        assert!(connected.rotation.supported);
        assert!(connected.rotation_lock.supported);
        assert!(connected.osk.supported);
        assert!(!connected.touchscreen_gestures.supported);
        assert_eq!(
            connected.touchscreen_gestures.reason,
            "No approved integrated touchscreen"
        );
        let disabled = capabilities_report(
            &serde_json::json!({"status":"unavailable","capabilities":{"tablet_workspace":false}}),
            &connected,
        )
        .unwrap();
        assert_eq!(disabled, crate::Capabilities::default());
    }
    #[test]
    fn malformed_capability_types_and_reasons_are_rejected() {
        let previous = crate::Capabilities::default();
        assert!(
            capabilities_report(
                &serde_json::json!({"capabilities":{"osk":"true"}}),
                &previous
            )
            .is_err()
        );
        assert!(
            capabilities_report(
                &serde_json::json!({"capabilities":{"gesture_reason":"x".repeat(2049)}}),
                &previous
            )
            .is_err()
        );
        assert!(
            capabilities_report(
                &serde_json::json!({"capabilities":{"input_suppression":true}}),
                &previous
            )
            .is_err()
        );
        assert!(!previous.osk.supported);
    }
}
