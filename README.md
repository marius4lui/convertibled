# convertibled

Native-feeling tablet experiences for Linux convertibles.

convertibled is a planned open-source convertible mode manager: a hardware
daemon, desktop integration, a settings application, a diagnostic CLI, and a
project-owned installer and updater.

**Status: active implementation; no public release or physical acceptance.**
The complete product and recovery paths must pass acceptance before publication.

## Product goals

- Move naturally between laptop and folded use without interrupting work.
- Preserve focus, window placement, user preferences, and external inputs.
- Provide touch-friendly controls that belong to the target desktop.
- Explain detected hardware, requested behavior, actual behavior, and failures.
- Own installation, updates, recovery, and removal end to end.

The selected first target is Fedora 44, GNOME 50 and Wayland on ThinkPad X1
Yoga Gen 8 (x86_64). This is an acceptance target, not tested hardware support.

## Planned components

| Component | Responsibility |
| --- | --- |
| `convertibled` | Hardware discovery, observations, mode policy, authorized hardware actions |
| `convertibled-session` | Active-session coordination and desktop-specific actions |
| Settings app | Native settings, profiles, hardware diagnostics, update experience |
| `convertiblectl` | Status, manual modes, configuration validation, diagnostics |
| Installer/updater | Versioned installation, verified updates, rollback, removal |

Rust implements the daemon, session service, CLI and GTK4/libadwaita settings.
A TypeScript/GJS GNOME Shell extension adds Home, dock, application search, live
window overview, split view, local widgets and touchscreen navigation.

## Tablet experience

Tablet behavior is a core product feature. It includes large touch targets,
accessible controls, predictable rotation, on-screen keyboard coordination,
and a quick way back to automatic or laptop mode. Desktop changes require
explicit backend capabilities. convertibled cannot make every third-party
application touch-friendly.

The tablet workspace is integrated directly into GNOME without an extra
fullscreen app. GNOME retains OSK, login, locking, authentication and notifications.
External displays retain desktop behavior. Automatic scaling stays disabled.

## Detection model

Hardware observations and user profiles are separate. The initial automatic
postures are `laptop`, `folded`, and `unknown`. `tablet`, `stand`, and `tent`
are intended profiles; automatic differentiation requires validated sensor
evidence. Screen orientation alone is not sufficient.

## Installation and updates

There are no public release binaries yet.
The intended distribution is a project-owned release bundle, installer, and
updater. RPM, COPR, DEB, and distro repositories are not the planned delivery
path. Updates will verify signatures, preserve configuration, and support
recovery to a previous version. Updates automatically check and prepare by default, with an explained opt-out.
Activation waits for affected graphical sessions to log out; locking is not logout.

## Documentation

Start with [the documentation index](docs/README.md).

- [Product scope](docs/product.md)
- [Architecture](docs/architecture.md)
- [Tablet UX](docs/tablet-ux.md)
- [Hardware and desktop support](docs/support.md)
- [Configuration and CLI](docs/configuration.md)
- [Installation and updates](docs/install-updates.md)
- [Release process](docs/releases.md)
- [Verification strategy](docs/testing.md)
- [Development and batch rules](docs/development.md)
- [Decisions and open questions](docs/decisions.md)
- [Roadmap](ROADMAP.md)

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Coding agents must first read
[AGENTS.md](AGENTS.md) and its mandatory documentation. Small, reviewable
batches and truthful validation reports are required.

## Security and license

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
Licensed under [MIT](LICENSE).
