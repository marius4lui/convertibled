# Rust runtime and wire contract

The workspace uses Rust 1.99 and pinned dependencies. `convertibled-core` is pure
policy/configuration/report code; `convertibled` observes hardware;
`convertibled-session` owns user-session coordination; `convertiblectl` is a client.
Rust services use the Tokio executor for D-Bus dispatch, timers and blocking work.
GTK settings and the GJS extension remain separate unprivileged clients.

## Status and policy

Schema 1 keeps observation, selected profile, desired actions and applied outcomes
separate. Observations contain posture (`laptop`, `folded`, `unknown`), orientation,
source and confidence. A debounced direct switch is direct-switch confidence;
manual tablet/stand/tent selection never manufactures sensor evidence. Unknown
posture automatically falls back to laptop. Manual overrides are session-local
and reset on session-service restart; profile configuration persists on disk.

Status includes revision, component version/backend, override origin, active and
locked flags. Desired workspace requires an active unlocked local session. Native
rotation and OSK actions are tri-state (`enabled`, `disabled`, `unchanged`) and
resolved from the selected profile. Inactive/locked sessions request unchanged
native actions. Explicit rotation lock has a requested flag: absent means retain
the existing GNOME preference; explicit false is an unlock request.

Applied reports contain actual workspace/lock values, status/error and optional
per-action rotation/OSK outcomes. Workspace success can coexist with an unsupported
native preference. Reports are limited to 8192 bytes and 2048-byte errors; unknown
actions/status values fail validation. Reporter-owner disconnect resets applied
state/capabilities to unavailable. Extension disable reports explicit cleanup.

## Hardware and lifecycle

The system daemon discovers tablet switches through `/sys/class/input` and queries
`EVIOCGSW` every 250 ms. It never reads event streams or key data, disables no input
device and exports no serials/physical identifiers. Fresh discovery covers startup,
hotplug and reconnect. Debounce is configurable (50..5000 ms); missing, failed or
conflicting switches become unknown immediately.

SensorProxy accelerometer claims exist only during folded monitoring. Laptop,
unknown, suspend and orderly shutdown release claims. GNOME retains rotation/touch
mapping ownership. Each sensor operation has a two-second deadline. Service-owner
changes trigger a new claim; canceled/failed claims are released before retry.
No sensor/service failure creates valid orientation evidence.

logind PrepareForSleep invalidates posture and pauses sampling until wake, then
fresh samples must debounce again. A closed signal stream fails for systemd restart.
SIGTERM and Ctrl-C perform orderly shutdown. The static convertibled service identity
uses read-only input-group access; hardened units retain AF_UNIX for D-Bus and allow
writes only to the private health StateDirectory. Units are owned by the installer.

## Buses and authorization

System service: `org.convertibled.Daemon1`, `/org/convertibled/Daemon1`.
User service: `org.convertibled.Session1`, `/org/convertibled/Session1`.
The matching versioned interfaces and signals are in `../data/dbus/`.

Session coordination requires exactly one active local Wayland seat for the user
service UID. Locked, remote, absent and ambiguous sessions are conservative fallbacks.
Hardware/logind polling runs concurrently with two-second deadlines; timeout replaces
cached observation with unknown or cached authorization with inactive/locked.
Profile, rotation and configuration mutations validate the actual bus sender UID
and re-query authoritative logind ownership with a bounded deadline.

GetStatus/GetCapabilities/GetConfig expose snapshots. SetProfile, SetRotationLock,
SaveConfig and Reload are authorized mutations; ReportApplied supplies actual outcomes.
ReportShellHealth separately relays explicit matching-version extension startup health
to the daemon. The daemon revalidates active local ownership and atomically writes
`/var/lib/convertibled/health/shell-health.json` and `shell-health-UID.json` for
update recovery and the consenting user's first-login acceptance. This authenticates
session ownership and matching version, not cryptographic shell-code attestation.

The session service independently observes native `org.gnome.shell` settings
(`enabled-extensions`, `disabled-extensions`, `disable-user-extensions`) on a
dedicated GLib thread. It reports user intent using the separate daemon method
`ReportShellExpectation(version, known, enabled)`, with bounded asynchronous
retries. Missing settings or an oversized list report unknown, never disabled.
The daemon validates the same active, unlocked local session credentials, derives
the UID and unique logind session ID, and records the kernel boot ID. Intent is
written to `shell-intent-UID.json`; health and intent are separate receipts.
Both now carry version, UID, session and boot identity. This producer contract
does not by itself turn disabled intent into a successful Shell health receipt.

Update acceptance retires prior-boot observations, so another user's old login
cannot indefinitely block a later boot. Prior-boot positive health never counts
as current evidence. An explicit matching failed trial remains a failure across
reboot until that user supplies fresh intent; recovery still waits for logout.
For current-boot logins, the consumer snapshots existing intent identity when it
first observes each session. A mismatched receipt already present then cannot
satisfy that login. A subsequently replaced authenticated identity may establish
a short later login missed between timer ticks, while other users' unresolved
observations continue to block completion. Missing prior-boot health cannot prove
a failure: fresh evidence is required rather than inferring success or rollback.

## Configuration and CLI

Built-in defaults merge `/etc/convertibled/config.toml`, then allowed user preferences
in `$XDG_CONFIG_HOME/convertibled/config.toml` (otherwise `~/.config/convertibled`).
Unknown keys, unsupported schemas and invalid types fail. User preferences cannot
replace system debounce or session authorization. Input suppression and automatic
scaling directives must remain unchanged until their required acceptance gates.

GetConfig returns merged schema-1 TOML. SaveConfig validates up to 64 KiB before
writing a private atomic user file with `config.toml.previous` backup. Failed saves
retain prior applied configuration. Explicit unchanged profile actions reset user
behavior even where system defaults exist. Reload validates complete candidates
before replacing state.

CLI: status, devices, capabilities, watch (`--count` positive), doctor, mode,
rotation-lock, profiles, config validate/show/save, reload and update controls.
Diagnostic commands support JSON. Doctor collects services independently and uses
a typed export allowlist, omitting identifiers/source strings/arbitrary backend
errors. Export is explicit. Update check/prepare/status/activate/recover/rollback,
uninstall/cancel-pending, automatic on/off and channel stable/preview use fixed arguments to the isolated
installed helper; mutations request pkexec authorization. Exit codes: 0 completed
request, 2 usage/configuration error, 3 unavailable runtime, 4 denied authorization,
5 updater failure. Request completion never proves desktop action success.

The CLI's recover, rollback and uninstall commands queue fixed `request-*` verbs
for graphical logout. Those explicit aliases are accepted too. `cancel-pending`
cancels waiting or failed maintenance. The installed Python helper retains
immediate recover/rollback/uninstall verbs for an administrator's offline TTY.

`convertibled --check` validates Linux x86_64, the input subsystem and system config
without claiming a bus name, modifying hardware or creating health receipts.

## Evidence and acceptance

Pure policy/configuration/report and CLI parser tests run on Windows. Linux cross
Clippy validates Linux source/types; it does not execute hardware or bus behavior.
Private-bus tests use real transport with fake peers, each internally bounded to
15 seconds:

```sh
cargo fmt --all --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --locked
dbus-run-session -- cargo test -p convertibled-session -- --ignored
dbus-run-session -- cargo test -p convertibled -- --ignored
```

The session test covers active/locked authoritative ownership, denied mutations,
invalid configuration/profile/report and desired/applied separation. The sensor
test covers idempotent claim, release, loss and service-owner replacement. These
checks do not establish physical ThinkPad fold, rotation/touch mapping, input
recovery, focus, GNOME interaction quality or installer acceptance. Input suppression
and automatic scaling remain disabled; production signing keys are not in this repo.

Capability normalization maps Shell rotation_lock support to the same native
rotation preference used by profile actions; it does not claim direct control of
orientation/touch mapping. Unavailable cleanup clears every extension capability
even while GNOME's shared bus sender survives. Malformed capability types are
rejected atomically; capability-only changes also increment revision and signal.
Touchscreen gesture support is separate and false until an integrated source is
approved; its bounded explanation is retained without promoting other input support.
