# Runtime implementation

The Rust workspace separates pure policy (`convertibled-core`), the read-only
system observer, active-user session coordination, and the diagnostic CLI.
Status schema 1 keeps observation, manual selection, desired action and applied
result distinct. Unknown posture defaults to laptop; stand/tent are manual.
Inactive or locked sessions never request the tablet workspace. Input suppression
and automatic scaling remain unavailable pending their required evidence.

Host unit checks prove policy only; Linux buses, evdev and physical UX require
Linux integration and the reference-device acceptance procedure.

The system observer rediscovers tablet-switch devices and queries EVIOCGSW every
250 ms without reading event streams. Failed/conflicting switches become unknown.
SensorProxy orientation is read without competing claims; GNOME retains rotation
ownership. Linux cross compilation checks validate D-Bus and ioctl code, but do
not establish hardware access or physical detection.
