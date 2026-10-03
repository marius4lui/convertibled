//! Read switch state using EVIOCGSW only. No event streams or key data are read.
use serde::Serialize;
use std::{fs, os::fd::AsRawFd, path::Path};

#[derive(Debug, Clone, Serialize)]
pub struct Device {
    pub name: String,
    pub tablet_mode: Option<bool>,
    pub error: Option<String>,
}
fn supports_tablet_switch(path: &Path) -> bool {
    fs::read_to_string(path.join("device/capabilities/sw"))
        .ok()
        .and_then(|text| {
            text.split_whitespace()
                .last()
                .and_then(|word| u64::from_str_radix(word, 16).ok())
        })
        .is_some_and(|bits| bits & (1 << 1) != 0)
}
pub fn discover() -> Vec<Device> {
    let Ok(entries) = fs::read_dir("/sys/class/input") else {
        return vec![];
    };
    let mut devices = vec![];
    for entry in entries.flatten() {
        let event = entry.file_name();
        let event = event.to_string_lossy();
        if !event.starts_with("event") || !event[5..].chars().all(|c| c.is_ascii_digit()) {
            continue;
        }
        if !supports_tablet_switch(&entry.path()) {
            continue;
        }
        // Do not export device serials, physical paths, or identifiers.
        let name = fs::read_to_string(entry.path().join("device/name"))
            .unwrap_or_else(|_| "Tablet switch".into())
            .trim()
            .chars()
            .take(100)
            .collect();
        let result = query(&format!("/dev/input/{event}"));
        let (tablet_mode, error) = match result {
            Ok(value) => (Some(value), None),
            Err(e) => (None, Some(e.to_string())),
        };
        devices.push(Device {
            name,
            tablet_mode,
            error,
        });
    }
    devices
}
fn query(path: &str) -> std::io::Result<bool> {
    let file = fs::OpenOptions::new().read(true).open(path)?;
    let mut bits = 0u64;
    // _IOR('E', 0x1b, 8): EVIOCGSW reads current switch bitmap, not events.
    const EVIOCGSW: libc::c_ulong = 0x8008_451b;
    // SAFETY: the descriptor is live and bits provides the required writable 8 bytes.
    let rc = unsafe { libc::ioctl(file.as_raw_fd(), EVIOCGSW, &mut bits) };
    if rc < 0 {
        return Err(std::io::Error::last_os_error());
    }
    Ok(bits & (1 << 1) != 0)
}
