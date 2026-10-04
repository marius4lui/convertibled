# Project-owned installation and updates

These requirements define the installer/updater implementation and acceptance.
Distribution uses our own versioned release bundle, installer, and updater;
RPM/COPR/DEB or distro repositories do not replace this path.

## Installation

Use immutable `/opt/convertibled/versions/<version>` directories and an atomic
`/opt/convertibled/current` reference, `/etc/convertibled` configuration and
`/var/lib/convertibled` transaction state. Keep configuration,
mutable state, user data, and binaries separate. Installer performs preflight
for OS/architecture/libc, available space, desktop compatibility, and permissions.

Install only required binaries, units, authorization rules, desktop integration,
and defaults. Maintain a manifest of owned files. Never overwrite unrelated
files or enable unverified input suppression by default. Privileged changes use
a bounded authorized helper; the UI remains unprivileged.

## Update trust

Use signed release metadata rooted in a shipped trust configuration and verify
artifact hashes after signature validation. A checksum alone is not authenticity.
Metadata includes schema/version, channel, architecture, compatibility bounds,
artifact size/hash, and migration requirements. Prevent replay/downgrade unless
the user explicitly requests a supported recovery version. Specify freshness,
key rotation/revocation, and trust-bootstrap behavior before production use.

Signing credentials stay outside the repository. Ed25519 release keys are separate from an offline trust-root key used for key
rotation. Production public trust material and protected CI credentials must be
provisioned by maintainers before a public release. Do not treat CI provenance as a substitute for
an updater's implemented trust verification.

## Activation transaction

1. Check metadata and compatibility; show release notes and required consent.
2. Download to staging with bounded resource use; verify before extraction.
3. Reject path traversal, unsafe links, oversized archives, and unexpected files.
4. Validate config migration with backup and preflight.
5. Quiesce relevant processes and restore owned input restrictions.
6. Atomically select the new version, start services, run bounded health checks.
7. If checks fail, restore previous binaries and compatible configuration.

Binary activation, config migration, and service restart form a recoverable
transaction with a journal. Startup repairs interrupted transactions. "Atomic"
activation does not mean migrations and all services change simultaneously.

## UX and channels

Stable and preview are explicit channels. Preview does not silently replace
stable. Default: automatic checking and preparation, explained during installation with
an opt-out. No network is required for mode switching. Background work stays
outside the hardware event loop. Activation waits until no affected graphical
session remains; a locked session is still active for this purpose. Never force
logout. New Shell code loads at the next login. Failed Shell activation keeps
normal GNOME usable and queues previous-version recovery at a safe transaction. Display downloaded, verified, applying, complete, failed,
and recovered states accurately. Never offer cancellation mid-critical switch
unless that operation has a defined safe cancellation path.

## Recovery and removal

Keep a known-good previous version. Document offline/manual recovery using
trusted local assets. Rollback checks configuration compatibility; do not promise
arbitrary historical downgrades. Uninstall stops processes, restores owned
settings, and removes only manifest-owned integration. Ask whether to retain
configuration/user data; default to retention. Repeat install/remove safely.
