#[cfg(test)]
mod tests {
    use crate::api::Api;
    use convertibled_core::{Capabilities, Status};
    use std::sync::Arc;
    use tokio::sync::RwLock;
    struct Manager;
    #[zbus::interface(name = "org.freedesktop.login1.Manager")]
    impl Manager {
        fn list_sessions(
            &self,
        ) -> Vec<(String, u32, String, String, zbus::zvariant::OwnedObjectPath)> {
            // SAFETY: geteuid has no arguments or side effects.
            vec![(
                "test".into(),
                unsafe { libc::geteuid() },
                "test".into(),
                "seat0".into(),
                zbus::zvariant::OwnedObjectPath::try_from("/org/freedesktop/login1/session/test")
                    .unwrap(),
            )]
        }
    }
    struct Session(Arc<RwLock<Status>>);
    #[zbus::interface(name = "org.freedesktop.login1.Session")]
    impl Session {
        #[zbus(property)]
        async fn active(&self) -> bool {
            self.0.read().await.active
        }
        #[zbus(property)]
        async fn locked_hint(&self) -> bool {
            self.0.read().await.locked
        }
        #[zbus(property)]
        fn remote(&self) -> bool {
            false
        }
        #[zbus(property, name = "Type")]
        fn kind(&self) -> String {
            "wayland".into()
        }
    }
    #[tokio::test]
    #[ignore = "requires dbus-run-session; exercised by Linux integration CI"]
    async fn session_contract_rejects_invalid_and_inactive_mutations() {
        tokio::time::timeout(std::time::Duration::from_secs(15), async {
            let state = Arc::new(RwLock::new(Status::default()));
            let authoritative = Arc::new(RwLock::new(Status::default()));
            let system = zbus::connection::Builder::session()
                .unwrap()
                .name("org.freedesktop.login1")
                .unwrap()
                .serve_at("/org/freedesktop/login1", Manager)
                .unwrap()
                .serve_at(
                    "/org/freedesktop/login1/session/test",
                    Session(authoritative.clone()),
                )
                .unwrap()
                .build()
                .await
                .unwrap();
            let name = format!("org.convertibled.Test{}", std::process::id());
            let service = zbus::connection::Builder::session()
                .unwrap()
                .name(name.as_str())
                .unwrap()
                .serve_at(
                    "/org/convertibled/Session1",
                    Api {
                        state: state.clone(),
                        system: system.clone(),
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
                    .call::<_, _, ()>("SetProfile", &("tablet",))
                    .await
                    .is_err()
            );
            authoritative.write().await.active = true;
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
            let connected=serde_json::json!({"tablet_workspace":true,"rotation_lock":false,"status":"applied","error":null,
                "capabilities":{"tablet_workspace":true,"rotation_lock":true,"osk":true,"split_view":true}}).to_string();
            proxy.call::<_,_,()>("ReportApplied",&(connected,)).await.unwrap();
            let raw:String=proxy.call("GetCapabilities",&()).await.unwrap();
            let caps:Capabilities=serde_json::from_str(&raw).unwrap();
            assert!(caps.rotation.supported);assert!(caps.osk.supported);
            let revision=state.read().await.revision;
            let malformed=serde_json::json!({"tablet_workspace":false,"rotation_lock":false,"status":"applied","error":null,"capabilities":{"osk":"true"}}).to_string();
            assert!(proxy.call::<_,_,()>("ReportApplied",&(malformed,)).await.is_err());
            assert!(state.read().await.applied.tablet_workspace);assert_eq!(state.read().await.revision,revision);
            let cleanup=serde_json::json!({"tablet_workspace":false,"rotation_lock":false,"status":"unavailable","error":"GNOME extension disabled","capabilities":{"tablet_workspace":false}}).to_string();
            proxy.call::<_,_,()>("ReportApplied",&(cleanup,)).await.unwrap();
            let raw:String=proxy.call("GetCapabilities",&()).await.unwrap();
            assert_eq!(serde_json::from_str::<Capabilities>(&raw).unwrap(),Capabilities::default());
            authoritative.write().await.locked = true;
            assert!(
                proxy
                    .call::<_, _, ()>("SetRotationLock", &(true,))
                    .await
                    .is_err()
            );
            drop(service);
        })
        .await
        .expect("Private-bus contract test exceeded 15 seconds");
    }
}
