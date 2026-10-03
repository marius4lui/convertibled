# Decisions and open questions

## Agreed constraints

| ID | Decision | Rationale |
| --- | --- | --- |
| D001 | Public project named `convertibled`; CLI `convertiblectl` | Hardware-neutral identity |
| D002 | Keep existing MIT license | Repository already uses MIT |
| D003 | Own installer, updater, and release bundles | Explicit product requirement |
| D004 | Native tablet UX is a primary requirement | Product must feel integrated |
| D005 | Enhance existing desktop first | Replacement shell is a separate scope |
| D006 | Separate system and session responsibilities | Desktop/session ownership and least privilege |
| D007 | Observation, policy, and applied state remain separate | Truthful diagnostics and recovery |
| D008 | Orientation alone cannot classify stand/tent/tablet | Avoid unsupported inference |
| D009 | No automatic scaling in initial foundation | Preserve preferences and validate recovery first |
| D010 | Browser control requires explicit current permission | User's workspace instruction |

## Open decisions blocking dependent implementation

## October 2026 product mandate (supersedes candidate choices below)

The user selected Fedora 44, GNOME 50, Wayland, and ThinkPad X1 Yoga Gen 8
as the first release target. This is a target, not physical acceptance.
D005 now means a native tablet workspace inside GNOME Shell, with no additional
fullscreen application. O001/O002/O003/O005 are resolved: TypeScript compiled
to GJS with St/Clutter/Mutter, and a separate Rust GTK4/libadwaita settings app.
Rust system/session services and versioned D-Bus retain hardware/policy ownership.
Home, dock, live window overview, split view, local widgets, touchscreen gestures,
visible navigation, and ownership-aware restoration are first-release scope.
GNOME continues to own lock/login, notifications, authentication, and OSK.
External displays retain desktop behavior. Stand/tent remain manual profiles.

O006 layout is `/opt/convertibled/versions`, with an atomic active reference,
`/etc/convertibled` configuration and `/var/lib/convertibled` transaction state.
Installation requires an authorized helper; normal settings run unprivileged.
O007 uses Ed25519 release metadata and independent offline-root-signed key
rotation. No production keys are available or generated in this repository.
Automatic update checking/preparation is the explained, opt-out default;
activation waits for affected graphical sessions to log out (locking is not
logout). Retain a journal, configuration backup and prior version for recovery.
GitHub Releases is the artifact host; publishing requires separate authorization.
O008 initially targets x86_64 with Fedora 44 as the Linux build baseline.
O004 remains gated: input suppression is disabled pending physical proof of
device assignment and failure recovery. Automatic scaling remains disabled.

The public release gate requires the whole product, signed-update recovery,
accessibility, and recorded physical acceptance. Internal increments do not
constitute a supported release. Other desktops/versions/network widgets defer.
Animations target 200 ms and respect reduced motion; reference-device testing
must measure at least 95 percent of 60 Hz animation frames within budget.

The older open-question table below is retained as historical context; resolved
entries above take precedence. CLI/SSH diagnostics do not establish touch UX.

| ID | Question | Blocks |
| --- | --- | --- |
| O001 | First desktop and supported version: GNOME or KDE? | UI toolkit and session backend |
| O002 | Reference device, distro/version, and access method? | Hardware and physical acceptance |
| O003 | GTK/libadwaita or Qt/Kirigami for initial UI? | UI implementation; depends on O001 |
| O004 | Supported privilege and internal-input control mechanism? | Input suppression |
| O005 | Native quick-control integration/API or extension? | Shell integration |
| O006 | Installation layout, helper authorization, service identity? | Installer implementation |
| O007 | Signing mechanism, key custody, rotation, metadata freshness? | Production updater/release |
| O008 | Initial architecture and libc compatibility baseline? | Release target matrix |

Do useful independent work while decisions are open. Ask for missing user
preferences when needed; do not silently choose a desktop. Technical decisions
require a short rationale, alternatives, consequences, and evidence in this file
or a linked ADR under `docs/adr/`. Supersede old decisions explicitly.
