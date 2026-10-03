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

First release platform: one explicitly selected desktop/version and a physical
reference device. Backend design may be extensible without pretending that
all desktops are supported.

Initial posture inference: laptop, folded, unknown. User profiles may be laptop,
tablet, stand, or tent. Orientation is separate from posture. Manual selection
does not create fake sensor evidence.

## Boundaries

The first product enhances the existing desktop. It does not replace its shell,
manage unrelated machine settings, or redesign third-party applications.
No telemetry by default. No network dependency for ordinary mode switching.
No arbitrary privileged command hooks. No distro-package delivery as a
substitute for the required project-owned installer/updater.

## Acceptance principles

Native appearance, accessible input, noninterrupting transitions, recoverable
settings, truthful status, and predictable updates are release requirements.
Any unsupported capability must be visible and must not silently report success.
