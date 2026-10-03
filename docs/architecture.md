# Architecture

Planned implementation: Rust daemon/CLI with independently selected native UI.
Directory/module names are provisional until the workspace exists.

## Data flow

Hardware observations → normalized state → policy → desired actions → backend
execution → applied-state reconciliation → CLI/UI.

Keep observations, inferred posture, selected profile, desired state, and
applied state distinct. Record reasons and per-action errors. Never infer
successful execution from a requested transition.

## Process responsibilities

- `convertibled`: device discovery, observation lifetime, policy, tightly scoped
  hardware actions, system D-Bus API. Prefer restricted service identity;
  privilege requirements must be proved in M0.
- `convertibled-session`: coordinates desktop actions for the authorized active
  local session. Handle logout, lock, inactive sessions, and seat ownership.
- Settings app: native presentation; no root desktop UI.
- `convertiblectl`: authenticated API client with human and JSON output.
- Installer/update helper: separately authorized installation operations;
  never accepts arbitrary paths or commands from an untrusted client.

## Backends

Hardware: evdev tablet switch, udev discovery, iio-sensor-proxy orientation.
Read initial switch state and reconcile after suspend and reconnect. Do not
record key events. Release sensor claims when monitoring is unnecessary.

Desktop: capability-based adapter for the chosen desktop. Native controllers
should retain ownership where suitable. Avoid competing rotation/OSK policies.
GNOME/KDE-specific APIs and extension requirements are feasibility decisions,
not assumptions that a generic Wayland client can control the whole desktop.

## State and recovery

- Debounce unstable observations; unknown is a legitimate state.
- Reconcile idempotently after restart and reconnect.
- Remember originals only for settings the project changes.
- Restore with ownership checks so later user changes are not overwritten.
- Define a conservative fallback per action; uncertainty must not lock out input.
- Input suppression needs an independently demonstrated release-on-failure path.
- Bound retries, queue sizes, and backend timeouts.

## API and authorization

Use versioned D-Bus interfaces with typed status, capabilities, changes, manual
overrides, and action outcomes. Read access and mutation authorization are
separate. Validate session/seat ownership for desktop-affecting mutations.
Plan policy-based authorization for privileged operations; implementation and
packaging must document concrete rules.

## Service lifecycle

systemd manages foreground processes, restart limits, logs, and shutdown.
Hardening is derived from actual device/API access, tested rather than copied.
No shell command strings for routine backend actions. Persistent state uses
atomic writes and documented schema versions.
