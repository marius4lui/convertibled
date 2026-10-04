# Contributing

The project is an experimental implementation without a public release. Start with
`README.md`, `docs/README.md`, `ROADMAP.md`, and `docs/decisions.md`.
Agents must additionally follow `AGENTS.md` in full.

## Develop locally

The selected product target is Fedora 44, GNOME 50 and Wayland on x86_64.
Use the pinned Rust toolchain and install the development prerequisites listed
in [development.md](docs/development.md#executable-development-checks).
Build the Rust workspace with `cargo build --workspace --release --locked`,
then run `npm ci` and `npm run build` in `extension/`.

Run formatting, Clippy, Rust tests, extension tests, installer/updater tests
and documentation checks using the exact commands in that guide. Linux-native
integration checks are documented in [testing.md](docs/testing.md).
The [native demo](demo/README.md) reuses production UI for visual review.
Windows model tests and virtual displays do not establish hardware acceptance.

## Submit a focused change

Discuss major desktop, privilege, updater, or UI changes before implementation.
Keep contributions focused and follow the batch, commit, and verification rules
in `docs/development.md`. Update affected documentation with behavior changes.

Report bugs with steps, environment versions, expected/actual behavior, and
sanitized evidence. Hardware support requires reproducible physical results.
Do not attach secrets, serial numbers, keystroke captures, or unrelated logs.

PRs should explain the problem, resulting behavior, validation, compatibility,
and unresolved acceptance. No signing/release credentials are needed to contribute.
No contributor license agreement is currently required; contributions are
submitted under the project's MIT license.

For device acceptance, follow the [record contract](docs/acceptance/README.md)
and identify the exact candidate bytes tested. Ordinary contributions never
need production keys, a public release, or installation on a live host.

Respect contributors and users. See `CODE_OF_CONDUCT.md` and report suspected
security vulnerabilities using `SECURITY.md` rather than a public exploit report.
