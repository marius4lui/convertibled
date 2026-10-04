#[cfg(test)]
mod tests {
    use crate::api::Api;
    use convertibled_core::{Capabilities, Status};
    use std::sync::Arc;
    use tokio::sync::RwLock;
    #[tokio::test]
    #[ignore = "requires dbus-run-session; exercised by Linux integration CI"]
    async fn session_contract_rejects_invalid_and_inactive_mutations() {
        let state = Arc::new(RwLock::new(Status::default()));
        let name = format!("org.convertibled.Test{}", std::process::id());
        let service = zbus::connection::Builder::session()
            .unwrap()
            .name(name.as_str())
            .unwrap()
            .serve_at(
                "/org/convertibled/Session1",
                Api {
                    state: state.clone(),
                    capabilities: Arc::new(RwLock::new(Capabilities::default())),
                    config: Arc::new(RwLock::new(Default::default())),
                    report_owner: Arc::new(RwLock::new(None)),
                },
            )
            .unwrap()
            .build()
            .await
            .unwrap();
        let client = zbus::Connection::session().await.unwrap();
        let proxy = zbus::Proxy::new(
            &client,
            name.as_str(),
            "/org/convertibled/Session1",
            "org.convertibled.Session1",
        )
        .await
        .unwrap();
        let initial: String = proxy.call("GetStatus", &()).await.unwrap();
        let decoded: Status = serde_json::from_str(&initial).unwrap();
        assert_eq!(decoded.schema_version, 1);
        let denied = proxy.call::<_, _, ()>("SetProfile", &("tablet",)).await;
        assert!(denied.is_err());
        assert!(!state.read().await.desired.tablet_workspace);
        state.write().await.active = true;
        assert!(
            proxy
                .call::<_, _, ()>("SetProfile", &("invalid",))
                .await
                .is_err()
        );
        proxy
            .call::<_, _, ()>("SetProfile", &("tablet",))
            .await
            .unwrap();
        assert!(state.read().await.desired.tablet_workspace);
        assert_eq!(state.read().await.applied.status, "unavailable");
        assert!(
            proxy
                .call::<_, _, ()>("ReportApplied", &("x".repeat(8193),))
                .await
                .is_err()
        );
        assert!(
            proxy
                .call::<_, _, ()>("SaveConfig", &("schema_version=99",))
                .await
                .is_err()
        );
        assert_eq!(
            state.read().await.profile,
            convertibled_core::Profile::Tablet
        );
        state.write().await.locked = true;
        assert!(
            proxy
                .call::<_, _, ()>("SetRotationLock", &(true,))
                .await
                .is_err()
        );
        drop(service);
    }
}
