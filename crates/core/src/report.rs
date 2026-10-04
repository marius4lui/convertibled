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
}
