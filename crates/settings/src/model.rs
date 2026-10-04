//! Presentation rules are independent from GTK so they can be tested anywhere.
use serde_json::Value;

pub const PROFILES: [&str; 5] = ["auto", "laptop", "tablet", "stand", "tent"];

pub fn field(status: &Value, path: &[&str]) -> String {
    let mut value = status;
    for key in path {
        value = &value[*key];
    }
    match value {
        Value::String(s) => s.clone(),
        Value::Null => "—".into(),
        other => other.to_string(),
    }
}

pub fn parse_status(raw: &str) -> Result<Value, String> {
    if raw.len() > 1024 * 1024 {
        return Err("Status exceeds the supported size".into());
    }
    let value: Value = serde_json::from_str(raw).map_err(|e| e.to_string())?;
    if !value.is_object() {
        return Err("Status must be an object".into());
    }
    for key in ["schema", "schema_version"] {
        if let Some(schema) = value.get(key) {
            if schema.as_u64() != Some(1) {
                return Err("Unsupported service response version".into());
            }
        }
    }
    Ok(value)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn missing_applied_state_is_not_requested_state() {
        let v = parse_status(r#"{"desired":{"tablet":true}}"#).unwrap();
        assert_eq!(field(&v, &["desired", "tablet"]), "true");
        assert_eq!(field(&v, &["applied", "tablet"]), "—");
    }

    #[test]
    fn rejects_unstructured_status() {
        assert!(parse_status("[]").is_err());
        assert!(parse_status("null").is_err());
        assert!(parse_status(&"x".repeat(1024 * 1024 + 1)).is_err());
    }

    #[test]
    fn rejects_incompatible_and_malformed_schema() {
        assert!(parse_status(r#"{"schema_version":2}"#).is_err());
        assert!(parse_status(r#"{"schema":"1"}"#).is_err());
        assert!(parse_status(r#"{"schema":1,"installed":null}"#).is_ok());
        assert!(parse_status(r#"{"schema_version":1,"applied":null}"#).is_ok());
    }
}
