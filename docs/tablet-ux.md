# Native tablet UX

## Design direction

Use the selected desktop's typography, icons, spacing, navigation, dialogs,
colors, dark mode, and accessibility conventions. Choose GTK/libadwaita for a
GNOME-first app or Qt/Kirigami for a KDE-first app only after platform selection.
No toolkit choice has been made. A replacement tablet shell is deferred.

## Planned surfaces

| Surface | Contents |
| --- | --- |
| Overview | Current profile, auto/manual, detected posture, action outcomes |
| Profiles | Supported behavior per profile, reset to defaults |
| Hardware | Detected sensors/inputs and readable capability explanations |
| Updates | Installed/available version, channel, release notes, progress, recovery |
| Diagnostics | Health checks and explicit export of a sanitized report |
| Native quick controls | Auto/manual profile, rotation lock, open settings |

Exact shell placement requires the target desktop's supported integration.
A generic tray icon is not automatically an acceptable native experience.

## Touch and accessibility

- Start with at least 44 × 44 logical-pixel touch targets; reconcile with toolkit
  guidance and test physically. Leave spacing to avoid accidental activation.
- Support keyboard navigation, screen readers, visible focus, contrast, text
  scaling, portrait/landscape, and reduced motion.
- Do not rely on hover, tiny icon-only controls, or color alone.
- Use adaptive layouts: single-column navigation on narrow displays and a
  split layout when space permits; prevent clipped labels and unreachable controls.
- Keep destructive/recovery actions explicit and understandable.

## Transitions

Folding should preserve focused app, windows, running tasks, and text entry.
Only supported, enabled actions run. Debounce posture changes. Notifications
are reserved for actionable failures; routine mode changes stay unobtrusive.

Rotation lock persists predictably across posture changes. Rotate the integrated
display by default; external displays require explicit configuration. Coordinate
touch mapping with output rotation where the backend requires it.

OSK follows editable focus through the native desktop facility. Do not launch
or dismiss it repeatedly during a transition, and ensure focused fields remain
reachable. Unsupported OSK coordination is reported honestly.

Scaling is opt-in, per-display, and deferred until restoration and failure
handling are demonstrated. Show a preview/revert path before persistent changes.

## First-run and failure experience

First run explains detected support and requests enabling supported behaviors.
Absent sensors retain manual profiles. Failed actions show a concise explanation
and a recovery action; detailed implementation logs belong in diagnostics.
An emergency path must restore laptop input without requiring the disabled
built-in keyboard. Do not advertise this until physically verified.

## Required design review before UI implementation

Review overview, profile editor, quick controls, update screen, unsupported
hardware, failure/recovery, portrait, dark mode, and large-text layouts.
Record target desktop and toolkit in `decisions.md` before coding the shell.

## Acceptance

Physically verify touch targets, text entry, OSK occlusion, rotation/touch mapping,
focus, fold/unfold, docking, lock/unlock, suspend/resume, and reduced motion.
Screenshots prove appearance only, not the complete interaction.
