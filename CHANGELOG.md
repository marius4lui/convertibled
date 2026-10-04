# Changelog

Changes are grouped by release. Planned work belongs in `ROADMAP.md`.

## Unreleased

### Added

- Product specification, architecture, native tablet UX requirements, and roadmap.
- Project-owned installation, update, release, support, and verification plans.
- Mandatory agent documentation reading, batch boundaries, and commit rules.
- Contribution, security, conduct, issue, and pull request guidance.

### Experimental implementation

- Authenticated shell installer with one bootstrap authorization, verified
  preparation and automatic completion after ordinary graphical logout.
- Per-user first-login consent enables the workspace and opens native Settings
  once. Explicitly declined setup preserves service-only installation; later
  disabling and other users' preferences are respected.
- Native Settings and CLI schedule manual activation, recovery, previous-version
  restoration and removal after logout, including when automatic updates are off.
  Requests bind their targets, expose waiting/running/failed states and support
  cancellation before critical work begins.
- Independent native GNOME preference observation separates disabled workspace
  intent from actual Shell health, with version/UID/session/boot-bound receipts.
  Successful acceptance can complete online; recovery still waits for logout.
- Stable owned systemd boot links, synchronous system-bus policy reload and
  traversable installation directories support first login and version changes.
  Busy timers preserve the owning transaction's status and retry normally.
- Guarded release draft, publication, atomic channel promotion and metadata
  renewal workflows preserve accepted bytes. Interactive key-setup tooling keeps
  the offline root separate from the release key; production custody is not
  provisioned by the repository.

- Home now prioritizes apps over widgets at every size, with bounded search and
  quieter editing controls. The dock fits its content and separates navigation,
  running apps and contextual actions. Standalone settings are nonmodal so Home
  can minimize them alongside other applications.

- Refined shared native UI: centered Home with deliberate favorite editing,
  compact local widgets and navigation shelf, proportional live previews, and
  coordinated light/dark styling. Search remains reachable above the native OSK.
- Settings now group selected, requested and applied state with adaptive actions;
  demo checks cover larger text, reduced motion and keyboard geometry.

- Windows WSLg preview runs the actual GNOME extension and GTK settings with
  isolated scenario controls, virtual monitor resizing and native smoke captures.
- Native boxed geometry and maximized-window split eligibility fixes found by
  exercising the real compositor; the separate WPF imitation was removed.

- Fedora 44 / GNOME 50 / Wayland reference-platform contract.
- Rust observation/policy, session authorization, versioned D-Bus and CLI.
- Native Shell Home/search/favorites, dock, live overview, split view, local
  widgets, touchscreen navigation and ownership-aware restoration.
- Rust GTK4/libadwaita settings with German/English text, profile editing,
  capabilities, verified-update controls and explicit local diagnostic export.
- Project-owned bundles, Ed25519 metadata/root keyring verification, bounded
  downloads/extraction, logout-safe transactions, recovery and owned removal.
- Linux/Fedora builds, portable and private-D-Bus tests, isolated native startup,
  dependency checks and an exact-artifact physical acceptance release gate.

No public version has been released. Live reference-device touch, rotation,
accessibility, performance and full installation/update acceptance are pending.
Production trust and protected release-environment configuration are not supplied
by the repository and must not be confused with passing synthetic tests.
