use std::sync::{
    Arc,
    atomic::{AtomicU32, Ordering},
};
use tokio::sync::RwLock;
use zbus::Connection;

struct Manager(Arc<AtomicU32>);
#[zbus::interface(name = "org.freedesktop.login1.Manager")]
impl Manager {
    fn list_sessions(&self) -> Vec<(String, u32, String, String, zbus::zvariant::OwnedObjectPath)> {
        vec![(
            "c1".into(),
            self.0.load(Ordering::Relaxed),
            "test".into(),
            "seat0".into(),
            zbus::zvariant::OwnedObjectPath::try_from("/org/freedesktop/login1/session/test")
                .unwrap(),
        )]
    }
}
struct Session(Arc<RwLock<Option<String>>>);
#[zbus::interface(name = "org.freedesktop.login1.Session")]
impl Session {
    #[zbus(property)]
    fn active(&self) -> bool {
        true
    }
    #[zbus(property)]
    fn remote(&self) -> bool {
        false
    }
    #[zbus(property)]
    fn locked_hint(&self) -> bool {
        false
    }
    #[zbus(property, name = "Type")]
    fn kind(&self) -> &str {
        "wayland"
    }
    #[zbus(property)]
    async fn class(&self) -> zbus::fdo::Result<String> {
        self.0
            .read()
            .await
            .clone()
            .ok_or_else(|| zbus::fdo::Error::UnknownProperty("Class".into()))
    }
}
// Use the real authorization boundary and bus-supplied credentials without
// writing any receipt to the developer/CI machine's system state directory.
struct Gate;
#[zbus::interface(name = "org.convertibled.TestHealth")]
impl Gate {
    async fn authorize(
        &self,
        version: &str,
        #[zbus(connection)] connection: &Connection,
        #[zbus(header)] header: zbus::message::Header<'_>,
    ) -> zbus::fdo::Result<(u32, String, String)> {
        super::authorize(connection, &header, version).await
    }
}

#[tokio::test]
#[ignore = "requires dbus-run-session; exercised by Linux integration CI"]
async fn health_authorization_rejects_nonuser_classes_and_foreign_owner() {
    tokio::time::timeout(std::time::Duration::from_secs(15), async {
        // SAFETY: geteuid takes no arguments and has no side effects.
        let uid = unsafe { libc::geteuid() };
        let owner = Arc::new(AtomicU32::new(uid));
        let class = Arc::new(RwLock::new(Some("user".to_owned())));
        let _login = zbus::connection::Builder::session()
            .unwrap()
            .name("org.freedesktop.login1")
            .unwrap()
            .serve_at("/org/freedesktop/login1", Manager(owner.clone()))
            .unwrap()
            .serve_at(
                "/org/freedesktop/login1/session/test",
                Session(class.clone()),
            )
            .unwrap()
            .build()
            .await
            .unwrap();
        let _service = zbus::connection::Builder::session()
            .unwrap()
            .name("org.convertibled.TestHealth")
            .unwrap()
            .serve_at("/org/convertibled/TestHealth", Gate)
            .unwrap()
            .build()
            .await
            .unwrap();
        let client = Connection::session().await.unwrap();
        let proxy = zbus::Proxy::new(
            &client,
            "org.convertibled.TestHealth",
            "/org/convertibled/TestHealth",
            "org.convertibled.TestHealth",
        )
        .await
        .unwrap();
        for excluded in [
            Some("greeter"),
            Some("manager"),
            Some("background"),
            Some("user-early"),
            Some(""),
            None,
        ] {
            *class.write().await = excluded.map(str::to_owned);
            let result = proxy
                .call::<_, _, (u32, String, String)>("Authorize", &(env!("CARGO_PKG_VERSION"),))
                .await;
            assert!(
                result.is_err(),
                "Non-user class must not authorize a receipt: {excluded:?}"
            );
        }
        *class.write().await = Some("user".to_owned());
        let (actual_uid, session, boot) = proxy
            .call::<_, _, (u32, String, String)>("Authorize", &(env!("CARGO_PKG_VERSION"),))
            .await
            .unwrap();
        assert_eq!(actual_uid, uid);
        assert_eq!(session, "c1");
        assert!(super::valid_boot_id(&boot));
        owner.store(uid.wrapping_add(1), Ordering::Relaxed);
        assert!(
            proxy
                .call::<_, _, (u32, String, String)>("Authorize", &(env!("CARGO_PKG_VERSION"),))
                .await
                .is_err()
        );
        owner.store(uid, Ordering::Relaxed);
        assert!(
            proxy
                .call::<_, _, (u32, String, String)>("Authorize", &("99.0.0",))
                .await
                .is_err()
        );
    })
    .await
    .expect("Private-bus health authorization test exceeded 15 seconds");
}
