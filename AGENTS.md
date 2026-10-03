# Agent instructions

These instructions apply to every agent and every directory in this repository.
Explicit current user instructions take precedence. Do not interpret a roadmap
item as authorization to publish, install on a live host, or change a desktop.

## Mandatory reading before work

Every agent, including delegated agents, must read:

1. `README.md`
2. `docs/README.md`
3. `docs/product.md`
4. `docs/architecture.md`
5. `docs/tablet-ux.md`
6. `docs/development.md`
7. `docs/decisions.md`
8. `ROADMAP.md`

Then read the task-specific documents listed in `docs/README.md`. In the first
progress update, briefly identify the task scope and applicable documents.
Do not start implementation before this reading. Re-read documents changed
during the task if the changes affect your work.

## Browser restriction

Never use browser control, browser automation, or a browser as a working
interface for OPNsense or any other task unless Marius explicitly requests
browser use in the current request. A URL, open session, browser login, or
convenience does not grant permission. If a task cannot reasonably be done
without browser control, stop and ask. This does not prohibit noninteractive
HTTP/API research or CLI operations.

## Product constraints

- Project-owned installer and updater; do not substitute RPM/COPR/DEB delivery.
- Native tablet UX is a primary acceptance criterion.
- Target desktop, UI toolkit, hardware support, and release readiness must
  not be invented. Consult `docs/decisions.md`.
- Never claim physical device acceptance from simulated tests.
- Keep requested and applied states separate and report unsupported actions.
- Do not disable external input devices or collect keystrokes for diagnostics.

## Batches, checks, and commits

Follow `docs/development.md` exactly: one coherent outcome per batch, normally
3–8 manually authored files, at most 12 and roughly 500 changed lines. Split
larger work before implementation; exceptions and initial documentation
bootstrap are documented there. Never pad a batch to meet a file count.

At each boundary: inspect the diff, run relevant checks, update affected docs,
and report the outcome and remaining limitations. Commit completed batches
when implementation/commit work is authorized; a documentation-only request
does not authorize a commit. Do not push, tag, publish, or release without
authorization. Use the commit format and selective staging rules in
`docs/development.md`.

## Coordination and workspace safety

- Inspect Git status before edits; preserve unrelated changes.
- Do not spawn agents unless the user or applicable instructions explicitly
  authorize delegation. This file does not request delegation.
- If delegation is authorized, give every agent the mandatory reading list,
  explicit ownership, acceptance criteria, and a prohibition on committing
  shared changes independently unless agreed.
- Do not store credentials, machine-specific private logs, or signing keys.
- Leave documentation consistent with actual implemented behavior.
