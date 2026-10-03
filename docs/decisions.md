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
