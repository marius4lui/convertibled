# Project-owned installation and updates

No installer exists yet. These requirements define the intended implementation.
Distribution uses our own versioned release bundle, installer, and updater;
RPM/COPR/DEB or distro repositories do not replace this path.

## Installation

Select and document exact layout before implementation. Prefer immutable
version directories with one active-version reference. Keep configuration,
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

Signing credentials stay outside the repository. Key custody and CI signing
mechanism are open decisions. Do not treat CI provenance as a substitute for
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
stable. Default: user-reviewed updates. No network is required for mode switching.
Background checking, if added, is configurable and does not run inside the
hardware event loop. Display downloaded, verified, applying, complete, failed,
and recovered states accurately. Never offer cancellation mid-critical switch
unless that operation has a defined safe cancellation path.

## Recovery and removal

Keep a known-good previous version. Document offline/manual recovery using
trusted local assets. Rollback checks configuration compatibility; do not promise
arbitrary historical downgrades. Uninstall stops processes, restores owned
settings, and removes only manifest-owned integration. Ask whether to retain
configuration/user data; default to retention. Repeat install/remove safely.
