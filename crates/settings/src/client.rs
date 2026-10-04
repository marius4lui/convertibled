use gio::prelude::*;
use glib::variant::ToVariant;
use gtk::{gio, glib};

const NAME: &str = "org.convertibled.Session1";
const PATH: &str = "/org/convertibled/Session1";

#[derive(Clone)]
pub struct Client(gio::DBusProxy);

impl Client {
    pub async fn connect() -> Result<Self, String> {
        gio::DBusProxy::for_bus_future(
            gio::BusType::Session,
            gio::DBusProxyFlags::DO_NOT_AUTO_START,
            None,
            NAME,
            PATH,
            NAME,
        )
        .await
        .map(Self)
        .map_err(|e| e.to_string())
    }

    async fn call(&self, method: &str, args: glib::Variant) -> Result<glib::Variant, String> {
        self.0
            .call_future(method, Some(&args), gio::DBusCallFlags::NONE, 5000)
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn status(&self) -> Result<serde_json::Value, String> {
        let result = self.call("GetStatus", ().to_variant()).await?;
        let (json,) = result.get::<(String,)>().ok_or("Invalid status reply")?;
        crate::model::parse_status(&json)
    }

    pub async fn profile(&self, profile: &str) -> Result<(), String> {
        if !crate::model::PROFILES.contains(&profile) {
            return Err("Unknown profile".into());
        }
        self.call("SetProfile", (profile,).to_variant()).await?;
        Ok(())
    }

    pub async fn rotation_lock(&self, locked: bool) -> Result<(), String> {
        self.call("SetRotationLock", (locked,).to_variant()).await?;
        Ok(())
    }

    pub async fn capabilities(&self) -> Result<serde_json::Value, String> {
        let result = self.call("GetCapabilities", ().to_variant()).await?;
        let (json,) = result
            .get::<(String,)>()
            .ok_or("Invalid capabilities reply")?;
        crate::model::parse_status(&json)
    }

    pub async fn config(&self) -> Result<convertibled_core::config::Config, String> {
        let result = self.call("GetConfig", ().to_variant()).await?;
        let (toml,) = result
            .get::<(String,)>()
            .ok_or("Invalid configuration reply")?;
        if toml.len() > 65536 {
            return Err("Configuration exceeds supported size".into());
        }
        convertibled_core::config::Config::parse(&toml)
    }

    pub async fn save_config(
        &self,
        config: &convertibled_core::config::Config,
    ) -> Result<(), String> {
        config.validate()?;
        self.call("SaveConfig", (config.to_toml()?,).to_variant())
            .await?;
        Ok(())
    }
}
