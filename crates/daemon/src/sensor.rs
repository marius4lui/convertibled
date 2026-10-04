use convertibled_core::Orientation;
use std::time::Duration;
use zbus::Connection;
#[derive(Default)]
pub struct Sensor {
    claimed: bool,
    recovery: bool,
    owner: Option<String>,
}
impl Sensor {
    pub async fn sample(&mut self, connection: &Connection, needed: bool) -> Orientation {
        let result =
            tokio::time::timeout(Duration::from_secs(2), self.inner(connection, needed)).await;
        match result {
            Ok(Ok(orientation)) => orientation,
            _ => {
                self.recovery = true;
                Orientation::Unknown
            }
        }
    }
    async fn inner(&mut self, connection: &Connection, needed: bool) -> zbus::Result<Orientation> {
        let proxy = zbus::Proxy::new(
            connection,
            "net.hadess.SensorProxy",
            "/net/hadess/SensorProxy",
            "net.hadess.SensorProxy",
        )
        .await?;
        let bus = zbus::fdo::DBusProxy::new(connection).await?;
        let owner = bus
            .get_name_owner(zbus::names::BusName::try_from("net.hadess.SensorProxy")?)
            .await?
            .as_str()
            .to_owned();
        if self.owner.as_deref() != Some(&owner) {
            self.claimed = false;
            self.recovery = false;
            self.owner = Some(owner);
        }
        if self.recovery {
            // A canceled claim may have reached the service: release before retry.
            let _ = proxy.call::<_, _, ()>("ReleaseAccelerometer", &()).await;
            self.claimed = false;
            self.recovery = false;
        }
        let available = proxy
            .get_property::<bool>("HasAccelerometer")
            .await
            .unwrap_or(false);
        if !needed || !available {
            if self.claimed {
                proxy.call::<_, _, ()>("ReleaseAccelerometer", &()).await?;
                self.claimed = false;
            }
            return Ok(Orientation::Unknown);
        }
        if !self.claimed {
            self.claimed = true;
            proxy.call::<_, _, ()>("ClaimAccelerometer", &()).await?;
        }
        let value = proxy
            .get_property::<String>("AccelerometerOrientation")
            .await?;
        Ok(match value.as_str() {
            "normal" => Orientation::Normal,
            "left-up" => Orientation::LeftUp,
            "right-up" => Orientation::RightUp,
            "bottom-up" => Orientation::BottomUp,
            _ => Orientation::Unknown,
        })
    }
    pub async fn release(&mut self, connection: &Connection) {
        let _ = self.sample(connection, false).await;
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{
        Arc,
        atomic::{AtomicU32, Ordering},
    };
    struct Proxy {
        claims: Arc<AtomicU32>,
        releases: Arc<AtomicU32>,
    }
    #[zbus::interface(name = "net.hadess.SensorProxy")]
    impl Proxy {
        fn claim_accelerometer(&self) {
            self.claims.fetch_add(1, Ordering::SeqCst);
        }
        fn release_accelerometer(&self) {
            self.releases.fetch_add(1, Ordering::SeqCst);
        }
        #[zbus(property)]
        fn has_accelerometer(&self) -> bool {
            true
        }
        #[zbus(property)]
        fn accelerometer_orientation(&self) -> String {
            "left-up".into()
        }
    }
    async fn proxy(claims: Arc<AtomicU32>, releases: Arc<AtomicU32>) -> Connection {
        zbus::connection::Builder::session()
            .unwrap()
            .name("net.hadess.SensorProxy")
            .unwrap()
            .serve_at("/net/hadess/SensorProxy", Proxy { claims, releases })
            .unwrap()
            .build()
            .await
            .unwrap()
    }
    #[tokio::test]
    #[ignore = "requires dbus-run-session; no physical sensor"]
    async fn claims_release_and_reconnect_follow_actual_bus_owner() {
        tokio::time::timeout(Duration::from_secs(15), async {
            let claims = Arc::new(AtomicU32::new(0));
            let releases = Arc::new(AtomicU32::new(0));
            let service = proxy(claims.clone(), releases.clone()).await;
            let client = Connection::session().await.unwrap();
            let mut sensor = Sensor::default();
            assert_eq!(sensor.sample(&client, true).await, Orientation::LeftUp);
            assert_eq!(sensor.sample(&client, true).await, Orientation::LeftUp);
            assert_eq!(claims.load(Ordering::SeqCst), 1);
            assert_eq!(sensor.sample(&client, false).await, Orientation::Unknown);
            assert_eq!(releases.load(Ordering::SeqCst), 1);
            assert_eq!(sensor.sample(&client, true).await, Orientation::LeftUp);
            assert_eq!(claims.load(Ordering::SeqCst), 2);
            service.close().await.unwrap();
            assert_eq!(sensor.sample(&client, true).await, Orientation::Unknown);
            let replacement = proxy(claims.clone(), releases.clone()).await;
            assert_eq!(sensor.sample(&client, true).await, Orientation::LeftUp);
            assert_eq!(claims.load(Ordering::SeqCst), 3);
            sensor.release(&client).await;
            assert_eq!(releases.load(Ordering::SeqCst), 2);
            replacement.close().await.unwrap();
        })
        .await
        .expect("Sensor private-bus integration exceeded 15 seconds");
    }
}
