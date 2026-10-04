# Documentation index

This folder contains the project specification. Unless explicitly described
as implemented with evidence, behavior is planned. `ROADMAP.md` records
milestone progress; `CHANGELOG.md` records actual project changes.

## Reading order

Read product → architecture → tablet UX → development → decisions → roadmap.
Agents must follow the complete mandatory list in `../AGENTS.md`.

| Task | Additional required reading |
| --- | --- |
| Hardware or daemon | `support.md`, `configuration.md`, `testing.md` |
| UI or desktop integration | `support.md`, `configuration.md`, `testing.md` |
| Installer or updater | `install-updates.md`, `releases.md`, `testing.md`, `../SECURITY.md` |
| CI or releases | `releases.md`, `testing.md`, `install-updates.md` |
| Contribution/process | `../CONTRIBUTING.md`, `development.md` |

## Documents

- [Product](product.md): scope and user outcomes
- [Architecture](architecture.md): processes, ownership, trust boundaries
- [Tablet UX](tablet-ux.md): interaction and acceptance requirements
- [Support](support.md): hardware and desktop capability evidence
- [Configuration](configuration.md): profiles, precedence, planned CLI
- [Install and updates](install-updates.md): project-owned distribution
- [Releases](releases.md): CI, artifacts, publication gates
- [Testing](testing.md): automated and physical acceptance
- [Development](development.md): batches, commits, review rules
- [Decisions](decisions.md): agreed constraints and unresolved choices

Update the relevant specification in the same batch as behavior changes.
Document new decisions before dependent implementation. Avoid duplicating
the same detailed policy across documents; link to its owner instead.

## Implemented components (experimental)

Read these with the task-specific specifications above:

- [Runtime](runtime.md): Rust services, versioned D-Bus, CLI and configuration
- [Shell](shell.md): native tablet actors, gestures, windows and lifecycle
- [Settings](settings.md): GTK/libadwaita profiles, updates and diagnostics
- [Distribution](distribution.md): signatures, transactions and installer usage
- [Acceptance](acceptance/README.md): exact-artifact physical release gate
