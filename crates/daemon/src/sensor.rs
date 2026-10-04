use convertibled_core::Orientation;
use std::time::Duration;
use zbus::Connection;
#[derive(Default)]
pub struct Sensor {
    claimed: bool,
}
impl Sensor {
    pub async fn sample(&mut self, connection: &Connection, needed: bool) -> Orientation {
        let result =
            tokio::time::timeout(Duration::from_secs(2), self.inner(connection, needed)).await;
        match result {
            Ok(Ok(orientation)) => orientation,
            _ => {
                self.claimed = false;
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
            proxy.call::<_, _, ()>("ClaimAccelerometer", &()).await?;
            self.claimed = true;
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
