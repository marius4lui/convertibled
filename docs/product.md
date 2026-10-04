# Product specification

## Purpose

Make Linux convertible use feel intentional and native: users fold the device
and continue their work without managing a collection of scripts.

The product includes hardware policy, desktop integration, a settings app,
diagnostic CLI, and its own installation/update lifecycle. Tablet interface
quality is part of functionality, not a final cosmetic pass.

## Primary user journeys

1. Install, inspect capabilities, and enable supported behavior.
2. Fold the device; retain application focus and receive appropriate touch
   behavior without a blocking dialog.
3. Lock rotation or choose a manual profile through native quick controls.
4. Return to laptop use; restore only preferences the project actually changed.
5. Understand a missing sensor or failed action in plain language.
6. Review, install, and recover from an update.
7. Disable or uninstall the project without residual input restrictions.

## Scope

First release target: Fedora 44, GNOME 50, Wayland, x86_64 and ThinkPad X1 Yoga
Gen 8. This identifies the acceptance target, not verified support. Native
GTK4/libadwaita settings and a TypeScript/GJS Shell extension are selected.
The first public release includes the complete workspace, services, CLI, own
installer, signed updates and recovery; internal increments are experimental.

Initial posture inference: laptop, folded, unknown. User profiles may be laptop,
tablet, stand, or tent. Orientation is separate from posture. Manual selection
does not create fake sensor evidence.

## Boundaries

The first product provides Home/search/favorites, dock, live window overview,
portrait-aware split view (50/50, 1/3-2/3, 2/3-1/3), and local clock/battery/action
widgets within GNOME Shell. It does not create another fullscreen app,
manage unrelated machine settings, or redesign third-party applications.
No telemetry by default. No network dependency for ordinary mode switching.
No arbitrary privileged command hooks. No distro-package delivery as a
substitute for the required project-owned installer/updater.

## Acceptance principles

Native appearance, accessible input, noninterrupting transitions, recoverable
settings, truthful status, and predictable updates are release requirements.
Any unsupported capability must be visible and must not silently report success.
