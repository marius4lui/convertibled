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

Startup shell health now uses explicit Session1.ReportShellHealth(version,healthy),
separate from action reports: normal laptop mode does not imply failed startup
or prove a successful startup. Extension-provided matching metadata version is
validated before the bounded relay to the system daemon.

Selected profile TOML actions now resolve to desired rotation/osk tri-state fields.
Defaults remain unchanged; switching profiles recomputes actions and never infers
applied success. Unsupported input/scaling directives still fail validation.

GetConfig exposes the merged TOML; authorized SaveConfig validates up to 64 KiB,
backs up the previous user file and writes atomically with private permissions.
System debounce is retained during merge. Reset a profile to unchanged actions
explicitly to override system defaults; failed saves leave state unchanged.

Applied action_outcomes retain separate rotation and OSK request/result/status/error
records. Bounded report parsing rejects unknown actions/status values and oversized
errors. A supported workspace can coexist with a failed native preference action;
diagnostics must show the per-action outcome rather than assuming all succeeded.

logind PrepareForSleep invalidates posture before sleep and on wake, releasing
accelerometer claims before fresh switch sampling. Both services handle SIGTERM
for systemd orderly stop in addition to Ctrl-C; the daemon releases sensor claims.
Suspend/reconnect behavior remains subject to Linux and device integration checks.

A private-bus integration test exercises the actual Session1 wire contract,
inactive/locked denials, invalid profile/config rejection and bounded reports.
Run dbus-run-session -- cargo test -p convertibled-session -- --ignored on Linux;
Windows cross checks compile this test but cannot execute its D-Bus assertions.

Capabilities separately expose native rotation lock, focus-owned OSK preference
and split view. Validated extension reports update each capability independently;
sensor support is not mistaken for a supported display action.

The session records the unique D-Bus sender of applied reports and checks that
owner's lifetime. Disconnect resets applied state and capabilities to unavailable,
then emits a new status; an old successful report cannot survive a dead reporter.
Extension disable separately submits an explicit unavailable cleanup report.

Doctor now collects services independently so missing session/hardware services
still produce a versioned report. Export uses a typed allowlist, omitting device
identifiers, source strings and arbitrary backend errors while retaining action
status and supported booleans. File export is explicit and created privately.

CLI configuration show/save use GetConfig/SaveConfig; profiles and validation have
versioned JSON output. Mode names and positive watch counts are validated before
connecting. Update recover/automatic/channel commands use fixed argument arrays.
Exit codes: 0 completed request, 2 usage/configuration error, 3 unavailable runtime,
4 denied authorization, 5 failed updater operation. Desired is never applied.

Hardware and logind reconciliation run concurrently with two-second deadlines.
Timeouts immediately substitute unknown observation or inactive/locked session,
so a stalled backend cannot retain cached authorization. Applied owner queries
are bounded too. Profile actions become unchanged for inactive/locked sessions.

All Rust bus services explicitly use zbus's Tokio executor, matching their timers
and blocking workers. The private-bus contract test is internally bounded to
15 seconds so an absent reply fails rather than hanging the integration job.

Sensor claim recovery tracks the actual SensorProxy bus owner. Restarted owners
are reclaimed; canceled/failed claims are released before retry because the remote
service may already have received the request. Loss never creates valid orientation.

Switch sampling pauses throughout PrepareForSleep(true)..false; stale folded state
cannot return during suspend preparation. A closed logind stream fails for systemd
restart rather than spinning. Successful sensor release clears local claim state.
