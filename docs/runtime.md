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

The user session service enumerates logind sessions for its UID, requires exactly
one active local Wayland seat, and denies mutations while locked or ambiguous.
D-Bus caller credentials are checked against the service UID. Extension reports
are bounded, validated, and never inferred from desired state. Manual choices
are currently session-local and reset when the service restarts.

Session reload validates both whole configuration candidates before changing
rotation preferences. User profile entries override system defaults; debounce
and session authorization retain system ownership. Missing files use defaults;
invalid startup configurations fail explicitly instead of silently accepting them.

convertiblectl supports status/devices/capabilities, bounded watch, sanitized
explicit doctor exports, manual profiles, rotation requests, schema validation,
reload, and fixed updater commands. Updates use the installed isolated Python
helper and pkexec for mutations. Exit 0 means the request/client check completed;
applied status must still be inspected. Linux connection/backend errors exit 3.

Rotation lock has an explicit requested flag. An absent configuration property
leaves GNOME's existing lock unchanged; explicit true/false requests distinguish
locking from unlocking. Reported actual native lock remains applied state.

Services use a static convertibled identity with read-only input group access;
no devices are disabled. Only the service owns the system bus name. User services
follow graphical-session.target; installer links units into their target wants.
Hardening preserves AF_UNIX D-Bus and read-only evdev access. Receipt writes are
confined to StateDirectory=convertibled/health. Units require Linux verification.

An authenticated active local user may report matching-version shell health to
the daemon. The session relays actual extension outcomes. The daemon writes an
atomic private receipt under /var/lib/convertibled/health for recovery checking.
This authenticates session ownership, not cryptographic shell-code attestation;
version mismatch, locked/ambiguous sessions and authorization timeout fail.

convertibled --check is a bounded candidate preflight: Linux x86_64 input subsystem
and whole system configuration validation. It starts no bus name, writes no
receipt and cannot prove switch hardware or desktop acceptance.

SensorProxy accelerometer claims are limited to folded monitoring and released
when laptop/unknown returns and on orderly shutdown. Shared claims preserve GNOME
as rotation controller. Missing service, property/call failures and a two-second
timeout return unknown orientation; the next sample retries after reconnection.
