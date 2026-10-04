# Decisions and acceptance boundaries

## Agreed decisions

| ID | Decision | Rationale |
| --- | --- | --- |
| D001 | Project `convertibled`, CLI `convertiblectl`, MIT license | Existing project identity |
| D002 | Own versioned installer, updater and bundles; no RPM/COPR/DEB delivery | Explicit product requirement |
| D003 | Native tablet UX and accessibility are release requirements | Folding should preserve work |
| D004 | Fedora 44, GNOME 50, Wayland, x86_64; ThinkPad X1 Yoga Gen 8 reference target | User-selected platform, not proven support |
| D005 | TypeScript to GJS Shell extension with St/Clutter/Mutter | Native Home/dock/windows without another fullscreen app |
| D006 | Rust daemon/session/CLI and GTK4/libadwaita settings | Native GNOME settings and separated system responsibilities |
| D007 | Separate observation, policy, requested action and applied result | Truthful diagnostics and recovery |
| D008 | Laptop/folded/unknown automatic posture; stand/tent manual | Orientation does not establish posture |
| D009 | No input suppression or automatic scaling initially | Physical recovery and device mapping remain unproved |
| D010 | Browser control requires explicit current permission | User workspace instruction |
| D011 | Home/search/favorites, dock, live overview, split view, local widgets and gestures in first release | User's complete product mandate |
| D012 | Preserve GNOME login/lock/authentication/notifications/OSK and external desktop outputs | Avoid competing controllers |
| D013 | Version directories under /opt/convertibled; config /etc/convertibled; state /var/lib/convertibled | Atomic reference and recoverable transactions |
| D014 | Ed25519 release signatures, separate offline root for release-keyring rotation | Root trust does not live in online release jobs |
| D015 | Automatic checking/preparation by default with explained opt-out; activate after graphical logout | No forced logout or replacing live Shell code |
| D016 | First public release requires the entire product plus physical/update/recovery acceptance | Internal increments are experimental |
| D017 | Rust 1.99 pinned toolchain and Linux x86_64 build target | Matches selected dependency MSRVs and checked toolchain |
| D018 | Serialize update activation with the normal GNOME 50 GDM/systemd Shell startup path | A pre-Shell shared lease and exclusive updater lease close the login/check race; direct unmanaged Shell starts are unsupported |

The October 2026 user mandate supersedes the original candidate GNOME/KDE,
GTK/Qt and reference-device questions. The tablet workspace enhances GNOME
within its Shell; a separate replacement desktop is outside this decision.

## Technical consequences

The October 4 design refinement permits a project-owned Shell palette and
surface styling while retaining native St/Clutter and GTK/libadwaita controls.
The goal is consistent visual and interaction quality across the real product
and its Windows-hosted native demo, without a second UI implementation.

The Windows preview runs the actual GNOME Shell extension in an isolated Fedora
44 / GNOME 50 WSLg session. A demo-only wrapper supplies a virtual internal
monitor and scenario controls; production UI modules and stylesheet are reused
unchanged. This replaces the illustrative WPF replica. Virtual input, sensors,
session state and device performance remain separate from physical acceptance.
Demo wrappers are never included in production release bundles.

Split view supports 50/50, 1/3-2/3 and 2/3-1/3, vertically stacked in portrait
with minimum sizes enforced. Home is opened by navigation, never forced by
folding. Normal primary windows maximize while dialogs/floating windows keep
their role. Owned settings and window geometry restore only while ownership
still matches; later user changes win. Touchpad gestures stay with GNOME.

Shell work must avoid blocking IO. Animations use approximately 200 ms opacity
or transform transitions and respect reduced motion. On the reference device,
at least 95 percent of measured 60 Hz frames must meet the frame budget.

## Remaining release decisions and evidence

No physical reference-device result, production trust key, protected release
environment, or published supported version is provided by this repository.
Maintainers must establish key custody/revocation operations and record actual
Fedora system integration, touch/accessibility, performance, update and recovery
acceptance. SSH/CLI results alone cannot establish touch usability. Other
platforms or behavior need a new decision with rationale and evidence.

The startup admission contract uses GNOME's actual `org.gnome.Shell@user.service`
instance. The separate admission service must signal readiness only after taking
its shared lease; it must not depend on the later graphical-session target.
The updater holds an exclusive lease across its final logout check and version
selection/restart. Existing graphical sessions still block activation. No
display manager is stopped and no user session is forcibly terminated. The
stable lock inode must survive version replacement and recovery. Real GDM
startup, competing login and logout/update acceptance remain release gates.
