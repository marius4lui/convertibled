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
                self.recovery = true;
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
