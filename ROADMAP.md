# Roadmap

Implementation and acceptance are tracked separately. Checked implementation
items mean code exists with scoped automated evidence, not verified hardware
support or permission to publish. No public version has been released.

## Selected first product

Fedora 44, GNOME 50, Wayland, x86_64, ThinkPad X1 Yoga Gen 8. Rust system/session
services and CLI, GTK4/libadwaita settings, TypeScript/GJS Shell extension and
project-owned installer/updater. See [decisions](docs/decisions.md).

## Implementation checkpoints

- [x] Product, architecture, native tablet UX and batch/commit contracts
- [x] Rust workspace, typed observations/policy and versioned D-Bus contracts
- [x] Read-only tablet-switch discovery, debounce and sensor-loss fallback
- [x] Active-session authorization, manual profiles and requested/applied state
- [x] CLI status/devices/capabilities/watch/doctor/config/profile/update commands
- [x] Native Shell Home, search, favorites, dock and live window overview
- [x] Touchscreen gesture recognition and visible navigation alternatives
- [x] Portrait-aware split ratios, minimum-size checks and owned restoration
- [x] Local clock/battery/action widgets and persistent workspace preferences
- [x] Native settings pages, German/English text and explicit diagnostic export
- [x] Validated per-profile native rotation/OSK configuration and reset
- [x] Ed25519 release metadata and independently root-signed release keyring
- [x] Bounded verified downloads/extraction and immutable version directories
- [x] Logout-safe activation, journal recovery, previous version and owned removal
- [x] Configurable automatic preparation and explicit stable/preview choice
- [x] Linux/Fedora CI, dependency review and isolated native startup checks
- [x] Internal candidate bundles and guarded manual signing/draft workflow

Implementation details and current caveats live in [runtime](docs/runtime.md),
[shell](docs/shell.md), [settings](docs/settings.md) and
[distribution](docs/distribution.md). The PR records the latest CI results.

## Integration and first public release gates

- [ ] Final aggregate checks green on the exact reviewed commit
- [ ] Clean Fedora 44 host installation, systemd/Polkit/SELinux acceptance
- [ ] Real fold/unfold, application focus and geometry restoration
- [ ] Real touchscreen gestures, native OSK and rotation/touch mapping
- [ ] Split view with varied real applications and portrait layouts
- [ ] External inputs/displays, docking, suspend, lock and sensor loss
- [ ] Extension/daemon failure and unsupported GNOME version fallback
- [ ] Large text, keyboard navigation, screenreader and reduced motion
- [ ] At least 95 percent of measured 60 Hz animation frames within budget
- [ ] Invalid signature, corrupt download, low disk and interrupted update
- [ ] Real logout/update/next-login/rollback/uninstall acceptance
- [ ] Production root/keyring custody and protected release environment configured
- [ ] Exact candidate hash and named physical acceptance recorded
- [ ] Maintainer authorization to tag, publish and promote the update channel

Use [the acceptance record contract](docs/acceptance/README.md). Nested Shell,
virtual displays and mocks cannot check off these physical gates.

## Deliberately disabled or deferred

Internal keyboard/touchpad suppression is disabled until physical assignment
and crash recovery are proved. Automatic scaling is disabled. Stand/tent remain
manual profiles. Other GNOME versions, KDE, other architectures, third-party or
network widgets and floating replacement-shell windows require separate planning.
