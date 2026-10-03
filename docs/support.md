# Hardware and desktop support

No platform has been physically validated. Fedora 44, GNOME 50, Wayland and
x86_64 ThinkPad X1 Yoga Gen 8 are the selected acceptance target. Other desktops
and versions are deferred; selection is not a verified support matrix.

## Evidence labels

- **Planned:** design intent without acceptance evidence.
- **Experimental:** implemented, with explicit limitations and partial checks.
- **Reported:** user report with reproducible details, not maintainer acceptance.
- **Verified:** recorded physical acceptance on a named configuration/version.

Record device model, firmware where relevant, kernel, distro, desktop/version,
project version, sensor availability, action capabilities, and test evidence.
Avoid publishing serial numbers or unnecessary identifying information.

## Discovery

Use stable udev/device characteristics rather than fixed event numbers. Separate
internal keyboard/touchpad from external devices and composite devices. Never
assume brand/model names alone prove capability. Missing/conflicting observations
yield unknown or a documented fallback. Hardware quirks require evidence and a
narrow match with a generic fallback.

## Capability matrix

Evaluate detection, rotation, touch mapping, OSK, internal keyboard/touchpad
control, scaling, quick controls, session lifecycle, and restoration separately.
A supported sensor does not imply supported desktop actions.

## Hardware report

Include sanitized `doctor` output when available, environment versions, steps,
expected/actual behavior, manual recovery, and observations before/after resume.
Do not request raw keystroke streams or full private system logs.
