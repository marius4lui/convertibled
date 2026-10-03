# Roadmap

All items below are planned. Dates are intentionally omitted. Versions are
milestone targets, not commitments or evidence of working software.

## D0 — Documentation foundation

- [x] Product, architecture, tablet UX, distribution, and release plans
- [x] Mandatory agent reading and batch/commit rules
- [x] Contribution, security, issue, and PR guidance
- [ ] Confirm first desktop, Linux version, and physical reference device

Exit: unresolved platform decisions are explicit and implementation can be
broken into reviewable batches.

## M0 — Feasibility and interaction design

- [ ] Capture sanitized hardware capabilities on the reference device
- [ ] Identify native desktop behavior and avoid competing controllers
- [ ] Prove sensor access and session authorization paths
- [ ] Evaluate safe internal-input control and crash recovery
- [ ] Choose native UI toolkit and desktop integration mechanism
- [ ] Review laptop, tablet, transition, failure, and update screen designs

Exit: documented capabilities and physical evidence; UI/backend decisions
recorded; unsupported behavior has an explicit fallback.

## M1 — v0.1.0 preview: observable foundation

- [ ] Rust workspace, Linux CI, version policy, dependency checks
- [ ] Read-only daemon with discovery, hotplug, suspend reconciliation
- [ ] State engine and versioned D-Bus contract
- [ ] CLI status, devices, capabilities, watch, doctor, config validation
- [ ] systemd lifecycle and initial settings app
- [ ] Versioned installer, uninstall, and initial verified update path
- [ ] Preview release bundle with signatures and documented recovery

Exit: install/start/stop/update/remove verified on a clean reference system;
physical detection verified; no unproven automatic input suppression.

## M2 — v0.2.0 preview: native tablet experience

- [ ] First desktop backend and native quick controls
- [ ] Automatic/manual profiles and stable transitions
- [ ] Rotation lock and on-screen keyboard coordination
- [ ] Safe, explicitly scoped internal keyboard/touchpad behavior if feasible
- [ ] Preference restoration, focus preservation, accessibility testing
- [ ] Update interruption and rollback tests

Exit: complete laptop → folded → laptop physical acceptance, including
suspend, dock, session lock, restart, and failure recovery.

## M3 — v0.3.0: broader reliability

- [ ] Additional hardware validated through reproducible reports
- [ ] Stable and preview channel lifecycle
- [ ] Optional scaling with per-display restoration and emergency recovery
- [ ] Config migrations and documented downgrade compatibility
- [ ] Second desktop feasibility evaluation; implement only after decision

Exit: repeatable support matrix and verified upgrade paths from prior previews.

## M4 — v1.0.0: stable contract

- [ ] Stable configuration and documented D-Bus compatibility policy
- [ ] Fully tested installer/updater/uninstaller and recovery documentation
- [ ] Accessible native UX and published desktop/version support matrix
- [ ] Security review, release provenance, and maintenance procedures

Exit: every advertised feature has implementation and acceptance evidence.

## Deferred

Replacement desktop shell; automatic stand/tent classification without
sufficient sensors; arbitrary root hooks; distro packaging; untested aarch64
support. These require a new decision rather than implicit expansion.
