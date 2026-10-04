# Distribution implementation

The Python standard-library installer/updater owns immutable version directories,
root-only transactions, and OpenSSL Ed25519 verification. Fedora 44 supplies
Python 3 and OpenSSL; these are platform prerequisites, not bundled interpreters.
Release metadata uses schema 1, monotonically increasing per-channel sequences,
UTC issuance/expiry (at most 31 days), an exact platform contract, SHA256/size,
configuration schema and bounded release notes. Stable rejects preview versions.
No production trust key is committed. Without provisioned trust, updates fail
closed. Physical installation and GNOME activation remain acceptance gates.

Signed envelopes contain `key_id`, `payload`, `signature` (base64). Signatures
cover canonical UTF-8 JSON (sorted keys, compact separators). The offline root
signs a release-keyring with an independent monotonic sequence and UTC lifetime.
Only keys in that authenticated keyring may sign channel metadata; removing a
key revokes it. Root replacement requires an explicit administrator trust action.

State writes fsync content and parent directory before proceeding. A nonblocking
flock serializes mutations on Linux. The active symlink may point only to a direct
child of the versions directory; directory/state symlinks are rejected.

Bundles contain only regular files, a bounded schema-1 `manifest.json`, and the
exact manifest file set. Extraction rejects links, traversal, duplicate names,
unexpected roots, oversized expansion and digest/size mismatches. Required four
executables prevent accepting an incomplete product bundle.

Network reads require HTTPS to GitHub release/API/asset hosts, including every
redirect. Metadata is capped at 256 KiB and payloads at the signed size (512 MiB
maximum). Connection/read timeouts and streaming SHA256 enforce download bounds.

Preflight enforces Fedora 44 x86_64, GNOME Shell 50, required platform tools and
disk space plus a recovery reserve. Known competing installed dock/tiling
extensions produce a review error. Logind Wayland/X11 user sessions block
activation regardless of active/locked state; greeters do not count.

Host integration uses an explicit fixed destination map. Links resolve through
`current` and are journaled in `owned.json`; conflicting files are never replaced.
Removal checks original link ownership and retains later user modifications.
The extension is installed system-wide but must be explicitly enabled by the
installing user's GNOME session. The helper never changes another user's settings.

`updates.json` defaults to explained automatic checking/preparation with an
opt-out and explicit stable/preview channel. Schema-1 configuration is backed up
before activation; incompatible schemas are rejected. No arbitrary migration
scripts run. Backups reject symlinks/special files and enforce 128 files/8 MiB.

Activation journals backup/prepared/switching/selected/awaiting-shell phases,
stops the daemon, selects the candidate, registers integration, restarts and
checks service health. Failures roll back the binary reference and configuration.
Interrupted nonterminal transactions recover conservatively at the next safe
logout boundary. A first-login shell health receipt completes the transaction;
missing/failed shell health causes a subsequent safe rollback.

Preparation loads only root-provisioned `trust.json`, verifies offline root
keyring then channel metadata, persists monotonic counters, downloads/hashes and
extracts into root-owned staging, and renames a verified candidate into versions.
Published version bytes are immutable: reuse with different metadata is rejected.
Normal settings never supply URLs, keys, destination paths or executable hooks.

The isolated Python helper exposes fixed verbs: `status`, `check`, `prepare`,
`install`, `activate`, `recover`, `rollback`, `automatic on|off`, `channel
stable|preview`, and systemd-only `scheduled`. All mutations require effective
root and a transaction lock. `status` reads a sanitized root-owned public JSON
snapshot; update keys, internal sessions and private logs are excluded.

Polkit restricts the fixed helper to active-session administrator authentication.
The root systemd timer runs preparation/activation checks every two minutes,
with a bounded oneshot, filesystem allowlist and no interactive authentication.
The daemon's separate service-owned `health/shell-health.json` receipt is written
only after D-Bus/logind caller validation. This authenticates the local session,
not cryptographic attestation of GNOME extension code.

Activation creates/verifies the fixed non-login `convertibled` service account
and runs candidate `convertibled --check` before selecting it. Awaiting-shell
transactions wait for the first observed graphical login; absence of a login
alone does not roll back. Missing health after that session logs out triggers
recovery, preserving normal GNOME while activation failure is investigated.

`uninstall` requires logout, validates every installed version against its owned
manifest, stops/disables only project services, removes owned links and verified
version files, and retains configuration/state by default. Added/modified files
abort removal before service shutdown. No broad `/opt` or home-directory deletion
is performed. The dedicated service account is retained for safe reinstall.

`scripts/release/bundle.py --bin-dir ... --extension-dir ... --output ...`
assembles all four ELF binaries, compiled GNOME extension schemas, Python
helpers, units/policies and desktop entry into a deterministic tar.gz with
manifest hashes and normalized ownership/modes. Version comes from Cargo's
canonical workspace version. Existing output files are never overwritten.

`metadata.py` constructs validated unsigned channel metadata with an explicit
monotonic sequence, release notes and a 14-day lifetime. `sign.py` signs canonical
payloads with an external Ed25519 private key and rejects keys inside the repo.
The same signer signs independent offline-root keyring payloads. Publication
and key custody remain maintainer operations; these scripts never publish.

Crypto tests generate ephemeral temporary Ed25519 keys and execute OpenSSL to
verify valid/tampered payloads, revoked keys, offline-root sequence rollback and
malformed signatures. These keys are test fixtures, never production trust.
