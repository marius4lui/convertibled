# Verification strategy

Tests prove specific behavior. Local mocks do not establish desktop/device
acceptance. Run checks appropriate to the batch; avoid repeated broad checks
after unchanged passing results.

## Automated layers

Private D-Bus integration checks exercise actual versioned session calls and
SensorProxy claims/release/reconnection against disposable bus services. Run
each ignored daemon/session test under `timeout 90s dbus-run-session`; these
tests do not connect to the host's system bus or establish hardware acceptance.

- State engine: conflicting/unknown observations, debounce, manual overrides,
  ordering, reconnect, and resume reconciliation.
- Configuration: validation, precedence, atomic reload, migration compatibility.
- Backends: idempotence, timeouts, failures, supported/unsupported actions,
  desired versus applied status, restoration ownership.
- IPC: input validation, API versions, denied mutations, session/seat changes.
- Installer/updater: clean install, idempotence, unsafe archives, wrong signature,
  corrupted artifact, replay, wrong architecture, low disk space, concurrent runs,
  interrupted staging/activation, migration failure, rollback, and uninstall.

Use disposable Linux environments for integration. Avoid live host mutation
as a substitute for an isolated test. Rust host checks on Windows do not prove
Linux device and desktop behavior.

Archive permission tests use the update service's actual private `0077` umask.
The verified candidate has traversable 0755 directories, executable 0755 binaries
and readable 0644 assets/manifest while its outer staging directory stays private.
File content, modes and directory entries are synced before atomic publication.

Icon integration tests rebuild a disposable hicolor cache with the actual GTK
utility under the updater's private umask, retaining unrelated icons and public
cache readability. Where PyGObject/GTK4 are available, fresh headless icon-theme
lookups reproduce the stale-cache miss and verify discovery after refresh.
These tests do not modify the host icon cache or replace rendered desktop review.

## Physical acceptance checklist

- [ ] Laptop → folded → laptop; desired/applied state agrees
- [ ] External keyboard/mouse remain usable
- [ ] Built-in input recovery on stop, crash, restart, and sensor loss
- [ ] Rotation lock, portrait/landscape, touch mapping, external displays
- [ ] Text focus, OSK appearance and occlusion, no repeated toggling
- [ ] Touch targets, screen reader, large text, keyboard navigation, reduced motion
- [ ] Lock/unlock, logout/login, session switch, suspend/resume, docking
- [ ] User changes preserved; owned changes restored
- [ ] Clean installation, previous-version update, interruption, rollback, removal
- [ ] GDM login racing with update activation, admission interruption and recovery

For each record: project commit/version, OS/kernel, desktop/version, device,
procedure, actual result, and unresolved limitations. Never tick a checklist
based only on intended behavior.

## Headless settings check

Linux CI starts the real GTK/libadwaita application under disposable Xvfb and
D-Bus, checks it remains alive without GTK criticals and captures its initial
missing-service view. The screenshot/log artifact aids review of native layout.
This X11 software-rendered smoke check does not validate Wayland, touch, OSK,
screenreader behavior or GNOME Shell integration; those remain physical gates.

Reference-platform CI builds on Fedora 44 and starts a nested GNOME 50 Shell
with software rendering to exercise extension enable/disable lifecycle. A
virtual monitor deliberately does not impersonate the integrated touchscreen;
this cannot mark physical gestures, display assignment or performance accepted.

## Documentation checks

Resolve relative Markdown links, check mandatory reading targets, inspect UTF-8,
run `git diff --check`, and review planned/current wording. Do not introduce
application tests before implementation exists solely to mirror documentation.
