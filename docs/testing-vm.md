# Fedora 44 virtual-machine lifecycle evidence

This is integration evidence, not physical convertible acceptance or authorization
to publish a release. See [testing](testing.md) and the separate
[physical acceptance contract](acceptance/README.md).

## Environment and artifact identity

The 2026-10-04 test used a disposable KVM/QEMU virtual machine booting the
signature- and checksum-verified Fedora Cloud Base 44-1.7 x86_64 image. GNOME Shell
50.5, GDM 50.3 and systemd 259.5 ran with SELinux enforcing on kernel
`6.19.10-300.fc44.x86_64`, GTK 4.22.5 and libadwaita 1.9.4. The VM used a virtual
display with software rendering and a disposable, non-root graphical account.

The tested installer and all four Linux executables were built from immutable
Git exports. Private fixture versions changed the workspace/package versions and
rebuilt the binaries and extension together; version numbers were not substituted
over older binaries. The successful initial lifecycle used source commit
`91fec9b855a427e8e05196bdf784ad8d30748c3f`:

| Private fixture | SHA-256 of the complete bundle |
| --- | --- |
| 0.1.0 | `96d43db0663d7d5ec65149a47a24d1a1ac9da7030c5d0f28f20e8cb38ad747a4` |
| 0.1.1 | `a7e38e689d0163298ce5f5ecfdfecde6a42bfecfa62e8cad523a5619bcc29549` |

The final icon-cache and retained-state reinstall fixes were checked from commit
`577802bc88be40b3a247c3e0809fa35cefd75714`. Fixture 0.1.2 was a normal rebuild;
0.1.3 deliberately threw an exception at extension-module loading to test failure
recovery while keeping the archive and its signatures valid:

| Private fixture | SHA-256 of the complete bundle |
| --- | --- |
| 0.1.2 | `95e46ab8543b06eac5683556da8059581c3ba4520bf6822fa324bb8ff2da4d2f` |
| 0.1.3, deliberately broken Shell | `3be5af0b7870925d4a9cdd95fa0a6cbe6b2883d4e80af4a1d8a841f972efa8c8` |

The final public-status correction was built from
`890a2b910fd3ef20696fecc328e0adfb63266781` as private fixture 0.1.4, SHA-256
`cc6bc012d3a4845cffd43b7f59a455d5dfc9d9e177dea32078742daa27ae4a59`.
It exercised retained-state reinstall with both workspace setup and automatic
updates explicitly declined.

A private HTTPS fixture served root-signed keyring and release-signed metadata.
Ephemeral trust and URL routing existed only inside the disposable VM. TLS,
Ed25519 verification, freshness, replay checks and artifact hashing were active.
These artifacts and signing keys were never production releases or repository
secrets. Administrative helper calls used the disposable account's sudo policy;
this does not prove the physical desktop's authentication-dialog interaction.

## Observed results

| Scenario | Result |
| --- | --- |
| Run trusted shell installer during an active GNOME session | Verified preparation succeeds; no active version is selected until logout. |
| Ordinary logout, deferred first installation, next login | Root timer activates the version; consenting user gets extension enablement and native Settings; genuine version/UID/session/boot-bound health completes acceptance. |
| Explicit activation with automatic updates off | Prepared 0.1.1 waits while 0.1.0 remains in use; logout installs it; next login verifies actual 0.1.1 health. Automatic updates remain off. |
| Cancel a waiting activation | Request disappears; selected version remains unchanged; a later explicit request works. |
| Request previous-version restoration | It waits for logout, restores 0.1.0 and consumes the request. |
| Disable the extension, then reinstall prepared 0.1.1 | Next login retains the disabled extension; authenticated disabled intent completes service-only acceptance. No healthy receipt is fabricated. |
| Tamper with signed channel payload | Verification rejects it and leaves the selected version unchanged. |
| Owned removal from the administrator helper | Project integration and verified versions are removed; configuration/state are retained as documented. |
| Full VM reboot | Installed services and timer restart through stable unit links; automatic-update opt-out and disabled extension remain intact. |
| Add an unowned file beneath an installed version | Removal refuses before stopping the daemon; file and selected version are retained. |
| Queue removal through the installed service | Request is consumed, verified versions and owned integration are removed, retained configuration/state remain. |
| Reinstall 0.1.2 with retained removal journal | Verified preparation, logout activation, next-login onboarding and genuine health succeed without deleting state. |
| Native application icon | First-login Settings and GNOME's dock render the project SVG instead of the previous missing-image placeholder. |
| Install deliberately broken, signed 0.1.3 | GNOME reports extension `ERROR` but remains usable; native intent says enabled, no healthy receipt exists, and the running session is preserved. |
| Log out after broken 0.1.3 trial | Real update service rolls back to 0.1.2; next login produces genuine matching 0.1.2 health. |
| Reinstall 0.1.4 with workspace setup declined | Installation completes after actual daemon checks; next login leaves extension disabled and reports service-only acceptance with no fabricated healthy receipt. |

The installed systemd unit paths resolve through stable `/usr/lib` entries;
boot links do not pin an old version. No SELinux AVC was recorded for the checked
installation/update operations. Upstream software-rendered GNOME logout crashes
were also observed on the unmodified VM before installation; VM results do not
establish compositor stability on hardware.

## Reproducing the relevant boundaries

Use a disposable Fedora 44 GNOME 50 Wayland VM. Build both versions from exact
source exports using the documented release bundler, with separately generated
test-only root and release keys. Serve the normal signed metadata contract over
HTTPS trusted only by that VM. Keep private keys and VM logs outside the repo.

1. Log in graphically and run the reviewed installer with explicit workspace
   consent. Check public status and the absence of `current` before logout.
2. Log out normally. Wait for the real deferred timer, then log in again. Check
   actual extension state, session and system services, and the daemon's receipt.
3. Disable automatic updates, prepare the second signed version and queue
   activation. Check that an open graphical session prevents selection changes.
4. Log out, let the installed update service activate, then log in and verify the
   receipt's version and session. Old receipts are insufficient evidence.
5. Repeat with explicit rollback, disabled extension, cancellation and removal.
   Inspect the actual unit namespace and SELinux result, not only mocked calls.

The VM exposed and drove fixes for cross-filesystem preparation, restrictive
umasks, real user-manager transport, D-Bus policy reload ordering, GNOME 50 XDG
autostart, implicit user namespaces, greeter authorization and hidden runtime
bus sockets. The automated regression suites cover the corresponding boundaries.

## Remaining physical gates

Real fold sensors, integrated display assignment, touchscreen gestures, native
OSK/touch mapping, rotation, external input/display restoration, suspend and
measured frame timing remain physical acceptance requirements. A virtual display
must not be presented as an accepted integrated touchscreen. Production signing
key custody and exact-artifact release acceptance remain separate requirements.
