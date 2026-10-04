# Native tablet UX

## Design direction

The October 4 refinement uses a quiet, carefully proportioned workspace: a
centered Home canvas, spacious app icons, compact information cards, and a
floating navigation shelf. Content has a clear title/detail/action hierarchy;
secondary controls do not compete with application launch targets. Window
previews preserve aspect ratio and split selection remains explicit.
Light and dark palettes share geometry, with restrained accent color, visible
focus and readable muted text. Native toolkit behavior and accessible targets
remain requirements. This supersedes the initial unstyled popup presentation.
Review covers Home, overview, settings, failures, portrait and keyboard
occlusion in the actual shared native demo; physical acceptance remains separate.

Use GNOME typography, symbolic icons, system colors, dialogs and dark mode.
Settings use GTK4/libadwaita; the tablet workspace uses native Shell actors.
Home is the persistent desktop behind applications in tablet mode. Navigation
returns to it by minimizing eligible windows on the internal current workspace.
It is never raised as an application-like overlay. Folding keeps the active app
focused. Eligible main windows maximize; dialogs do not. Native Overview hides
tablet chrome during its zoom transition and never lists Home as an app.

## Planned surfaces

| Surface | Contents |
| --- | --- |
| Overview | Current profile, auto/manual, detected posture, action outcomes |
| Profiles | Supported behavior per profile, reset to defaults |
| Hardware | Detected sensors/inputs and readable capability explanations |
| Updates | Installed/available version, channel, release notes, progress, recovery |
| Diagnostics | Health checks and explicit export of a sanitized report |
| Native quick controls | Auto/manual profile, rotation lock, open settings |

A short bottom-edge touchscreen swipe reveals the dock, a longer swipe opens
Home, and swipe-and-hold opens live overview. Visible Home/Overview controls
provide equivalent actions. Preserve touchpad gestures and external displays.
Split view supports half/third/two-thirds with vertical stacking in portrait;
minimum sizes produce an explanation instead of forced geometry. Local widgets
(clock/date, battery/status, quick actions) can be hidden and reordered.

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

Automatic scaling stays disabled and is deferred until restoration and failure
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

## Initial settings design review

The implementation plan uses a libadwaita PreferencesWindow with six named
pages: overview, profiles, hardware, tablet, updates and diagnostics. Native
preferences groups adapt to narrow widths; all controls retain labels and
keyboard focus. Status rows distinguish detected, requested and applied state.
Unavailable services show an explanation and retry, never invented success.
Profiles offer automatic plus four manual choices and native rotation lock.
Tablet settings expose only extension-owned preferences. Update preparation
and logout-safe activation have separate labels; recovery needs explicit action.
Diagnostics remain local until the user explicitly chooses an export path.
System appearance follows libadwaita, with no forced font sizes or custom theme.
This is the structural design review before coding; rendered portrait, dark,
large-text and assistive-technology review remain acceptance tasks.

Animation duration is approximately 200 ms using transforms/opacity; reduced
motion disables decorative transitions. At 60 Hz at least 95 percent of
reference-device animation frames must meet budget, without recurring stalls.
