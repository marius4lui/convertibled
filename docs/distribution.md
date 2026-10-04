# Distribution implementation

The Python standard-library installer/updater owns immutable version directories,
root-only transactions, and OpenSSL Ed25519 verification. Fedora 44 supplies
Python 3 and OpenSSL; these are platform prerequisites, not bundled interpreters.
Release metadata uses schema 1, monotonically increasing per-channel sequences,
UTC issuance/expiry (at most 31 days), an exact platform contract, SHA256/size,
configuration schema and bounded release notes. Stable rejects preview versions.
No production trust key is committed. Without provisioned trust, updates fail
closed. Physical installation and GNOME activation remain acceptance gates.

The implemented admission interlock covers the selected GNOME 50 GDM/systemd
startup contract. Real concurrent GDM login, activation and recovery acceptance
is still a public-release gate; direct/custom Shell starts are unsupported.

Signed envelopes contain `key_id`, `payload`, `signature` (base64). Signatures
cover canonical UTF-8 JSON (sorted keys, compact separators). The offline root
signs a release-keyring with an independent monotonic sequence and UTC lifetime.
Only keys in that authenticated keyring may sign channel metadata; removing a
key revokes it. Root replacement requires an explicit administrator trust action.

State writes fsync content and parent directory before proceeding. A nonblocking
flock serializes mutations on Linux. The active symlink may point only to a direct
child of the versions directory; directory/state symlinks are rejected.

Lock contention is a typed busy result. Scheduled update and deferred-install
runs leave the owner's progress untouched and retry at the next timer tick.
Interactive operations still report that another transaction is running.
Neither path writes public status without owning the transaction lock; actual
operation failures remain errors and are never classified by matching text.

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
Daemon/timer boot wants links are also manifest-owned and point to the fixed
`/usr/lib/systemd/system` unit entries. Activation and explicit queued requests
start the units without generating canonical version-pinned enable aliases.
Legacy `/etc` aliases migrate only after their exact installed unit bytes match
the version manifest; foreign or modified aliases stop activation before daemon
quiescence. Wants links are replaced atomically after ownership is journaled.
An administrator's manually removed boot link remains their choice when merely
requesting a queued operation; that operation starts the timer for this boot.

Activation and rollback synchronously reload `dbus.service` after installing or
restoring system-bus policy, before starting the daemon. Fedora's notify-reload
contract confirms policy loading; the system bus is never restarted. Removal
reloads policy after deleting the owned entry. A reload failure fails activation
and follows the existing recovery transaction.

Removal checks original link ownership and retains later user modifications.
The extension is installed system-wide. Explicit installer consent records the
authenticated installing user's UID; a GNOME autostart enables the extension
unprivileged at that user's next Wayland login and opens Settings once. A per-user
completion token preserves subsequent disabling. Declining setup revokes only
that user's pending consent. Other users opt in separately.

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

Removal also handles verified preparation before successful activation and
repeated removal. Each project unit is skipped only when a successful systemd
query proves `not-found`, `inactive`, and an empty fragment path; query errors and
failed stops of present units remain fatal. Canonical enable aliases and wants
links are removed only when they target a fixed managed unit/current path or an
exact manifest-validated installed version. Foreign links and regular files are
retained with an error, including after a failed first installation.

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

Public keys must use the exact RFC 8410 Ed25519 SubjectPublicKeyInfo encoding;
OpenSSL's algorithm-flexible interface cannot silently accept RSA/ECDSA trust.

Integration includes the daemon's system-bus policy and the session unit's
`graphical-session.target.wants` link. Conflict preflight checks system extensions
and the authenticated installing user's extension directory, without altering
other extensions or accounts.

`offline-prepare` reads only administrator-provisioned `offline/keyring.json`,
`offline/channel.json` and `offline/artifact.tar.gz` under the transaction state
directory. It uses the identical signature/freshness/replay/platform/hash/archive
pipeline. It grants no arbitrary local file-read or extraction path arguments.
`rollback` recovers a retained installed version without any network request.

Ownership intent is persisted before host links are created. Configuration backup
files and containing directories are fsynced. Interruption before selection
does not stop/restart the unchanged previous service during recovery.
Backup fsync uses a writable descriptor so the same tests run on Windows.

Configuration/state directories are root-owned and traversable (0755); private
atomic trust/state files are 0600 and backups 0700. The daemon/session can read
an administrator's public `config.toml` or obtain defaults when absent. Native
desktop entry, scalable icon and AppStream metadata are manifest-owned links.

Accepted root sequence and per-channel release metadata share one atomic state
record, avoiding a crash between advancing a counter and saving its release.
SemVer also rejects newly signed downgrades; explicit local rollback is separate.
Fresh metadata may extend a version's validity only when artifact bytes retain
the identical hash/size; immutable published bundle content never changes.

The timer checks logout/recovery every two minutes while background network
preparation is throttled to six hours; explicit check/prepare remains immediate.
Activation revalidates prepared channel, accepted release and metadata freshness.
Stale shell receipts are cleared before selecting a candidate; explicit failure
receipts trigger safe rollback even if a short first session escaped polling.

Disposable pipeline tests perform real Ed25519 verification, offline bounded
reads, deterministic archive extraction and immutable candidate preparation.
They cover idempotence, corruption, architecture/expiry rejection, signed
downgrades and replay. They do not start systemd or claim real GNOME acceptance.

POSIX lifecycle tests use real version directories, archive extraction, symlinks,
owned integration, configuration backups and removal, with simulated service
commands. They cover clean install/health/remove, failed-service rollback and
preserving added user files. Windows explicitly skips POSIX-only cases.

## Desktop recovery and removal requests

The privileged helper accepts fixed `request-recover`, `request-rollback`, and
`request-uninstall` verbs. These persist a request bound to the currently selected
version, then arm the existing update timer. `cancel-pending` cancels a waiting
or failed request; an interrupted critical transaction must recover first.
Immediate `recover`, `rollback`, and `uninstall` remain available for offline
administrator recovery after logout.

The timer processes explicit requests before automatic preparation, even when
automatic updates are disabled. Graphical sessions, including locked sessions,
block version changes and removal. A login/admission race defers safely. Failures
remain visible without retry loops; repeating the same request explicitly retries
it. Existing admission-marker crash recovery still runs without retrying the
failed requested action. A different selected version invalidates the request
and requires review.
Public status includes `pending_action` and `pending_state`; queued phases are
`waiting_for_logout` or `action_failed`, with a bounded failure explanation.
Removal consumes the request after its durable recovery journal is written,
preventing a later reinstall from inheriting an old removal request.

## Trust bootstrap and installation

The reviewed installer now requests administrator authentication when started
by a normal user. Release packaging supplies `installer/bootstrap-trust.json`
containing public trust only. Bootstrap validates it through the updater's
existing key and HTTPS URL rules, provisions only absent host trust, and never
replaces existing administrator trust. Failed release preparation leaves update
preferences unchanged. This removes manual JSON authoring from a provisioned
installer; authenticating the initial installer distribution remains required.

There is no production release key or downloadable supported release yet.
An administrator must independently authenticate the initial reviewed installer
source and the offline Ed25519 root fingerprint. A key downloaded beside an
untrusted bundle is not a trust bootstrap. Keep private keys offline/outside
the repository; only public PEM keys belong in `/etc/convertibled/trust.json`.
`installer/trust.example.json` shows the contract with intentionally invalid
placeholders. Review actual immutable artifact/channel URLs before provisioning
that root-owned 0600 file. Never use curl-pipe-to-root installation.

Run `sh installer/install` from the independently authenticated installer
distribution (or pass `--no-automatic-updates`). It requests administrator
authorization, explains the automatic default, prepares authenticated assets
and schedules activation after ordinary graphical logout or reboot. A fixed
root-owned timer executes only the verified candidate's bootstrap code. It
reauthenticates the prepared version and uses the existing admission interlock;
no session is forcibly closed. First login loads the installed session unit.
Accept the installer's workspace question or pass `--enable-workspace` to enable
the workspace automatically for your account at that login. `--no-workspace`
leaves it disabled. For later manual opt-in, use GNOME Extensions or run
`sh /opt/convertibled/current/installer/finish-user.sh`. This explicit unprivileged
onboarding verifies GNOME 50/Wayland and changes only the current user's project
extension. Other users' settings are untouched. Reference-device first-login
acceptance is still required. Before logout/removal, use the same script with
`--disable`; the root remover never edits unrelated user preferences.

The first installation waits for the consenting user's graphical login and
matching per-UID daemon health receipt. Another user's session or receipt cannot
prematurely complete or fail that acceptance. Explicitly declining first-login
workspace setup instead completes installation after the real daemon checks,
recording `shell_acceptance: not_requested`; it does not claim Shell acceptance.
An absent legacy consent record is not an explicit decline. Manual opt-in remains
available later. A matching healthy receipt can complete first-login acceptance
while the user works; it does not require a second logout.

Updates obtain current per-user enablement from the independent native session
observer, not from old onboarding consent. A bounded, strictly typed intent
receipt must match the candidate version, UID, logind session and kernel boot ID.
Enabled intent requires actual matching healthy Shell evidence; missing or failed
health triggers recovery only after graphical logout. Explicitly disabled intent
completes service-only acceptance with `shell_acceptance: not_requested`; no
healthy receipt is fabricated. Unknown, stale or legacy unbound intent stays
pending. All observed users are evaluated, so one disabled user cannot hide
another user's enabled failure. Later sessions supersede the same user's earlier
trial; other users' unresolved trials remain. Successful journal-only acceptance
can complete online, while rollback and binary changes always require logout.

The temporary `convertibled-install`
service/timer are journaled before creation and removed only while their contents
still match project ownership. Logout or
admission contention keeps the timer waiting; actual activation errors publish
status and stop retries. An explicit installer rerun can authorize one retry of
a previously rolled-back candidate. `bootstrap.py --cancel-install`, run with
administrator privileges, cancels owned scheduling and retains verified files
and configuration. Uninstall also removes owned pending bootstrap scheduling.

Subsequent fixed helper commands use
`pkexec /opt/convertibled/current/installer/cli.py COMMAND`. Status is unprivileged:
`python3 -I /opt/convertibled/current/installer/cli.py status`. A root TTY can run
the same helper using `python3 -I` for offline prepare/activate/recover/rollback.
Do not manually edit `current` or transaction journals during recovery.

Archive metadata is bounded during enumeration, before reading a later entry.
Payload extraction follows physical archive order to avoid repeated gzip
rewinds. Tests construct actual symlink, duplicate and traversal tar entries and
verify rejection before the candidate directory is created.

JSON rejects non-finite numbers and boolean schema impostors. Root keyring
validity is capped at 366 days and an accepted sequence binds the exact keyring
payload; changed keys/expiry require a new root sequence, preventing same-sequence
keyring swaps after revocation.

A rolled-back candidate is quarantined from automatic retry, preventing a
logout/update/failure loop. A newer version or an explicit administrator
`activate` can retry. Service sandbox write paths include only the complete fixed
integration destinations. SELinux enforcing installation/activation must still
be verified on Fedora 44; no SELinux protections are disabled by the installer.

Malformed/deep JSON, oversized logind inventories and corrupt tar streams produce
bounded actionable errors rather than escaping the transaction/error-status path.

Bootstrap conflict checks recognize both authenticated `PKEXEC_UID` and sudo's
`SUDO_UID`, so the TTY install also inspects the installing user's extensions.
Low-space and competing-extension tests verify refusal preserves existing files.

Authenticated offline-root keyring advancements are persisted before requesting
channel metadata. A revoked/unavailable channel cannot undo a learned revocation
or permit replay of a previously fresh older keyring. Root trust and per-channel
availability are independent atomic state transitions.

Activation reauthenticates retained channel envelopes using the latest retained
root-signed keyring, including root freshness and administrator-provisioned root
trust. Learning a revocation through another channel invalidates a cached prepared
release signed by that key. The installed candidate's artifact identity must also
match the authenticated metadata; equal version strings alone do not bind bytes.

Quiescing is journaled before stopping the daemon, so an interruption there
restarts the unchanged previous version during recovery. Logout is rechecked
after the potentially slow candidate preflight and again after daemon stop.
These observations run inside the exclusive admission lease. No display manager
is stopped, sessions forced out, or global nologin file imposed. Normal GNOME
Shell startup waits at a separate service until the updater releases its lease.

Bundle assembly qualifies the Polkit helper annotation with the canonical
version-directory path, matching upstream pkexec's realpath-based lookup.
Activation and rollback atomically replace the owned host policy-directory entry
to trigger Polkit reload; changing the external `current` symlink alone would
not update its watched actions directory. Signed manifest hashes cover the exact
version-qualified policy bytes. Tests verify program identity and policy refresh.

If login arrives after daemon stop while phase remains quiescing and `current`
still selects the unchanged previous version, recovery directly resumes that
daemon even with the session present. It does not select a version, restore
configuration or edit integration. Recovery after selection still requires logout.

The admission ordering follows GNOME 50's
[Shell service template](https://github.com/GNOME/gnome-shell/blob/50.0/data/org.gnome.Shell%40.service.in)
and [GNOME session definition](https://github.com/GNOME/gnome-session/blob/50.0/data/gnome.session.conf).
The actual Shell instance is `org.gnome.Shell@user.service`; `user` is its mode,
not its display protocol. Its project drop-in Requires/After a separate
`convertibled-admission.service`. The admission service has Type=notify and
signals READY only after acquiring the shared flock. It holds that lease until
the initialized session target stops it. The existing project session service
continues to start from graphical-session.target without an ordering cycle.

The root-owned `/var/lib/convertibled/admission.lock` inode is never replaced or
deleted, including on uninstall. Activation, rollback, recovery and removal hold
the same inode exclusively, nonblocking, before their final logind observations
and through mutation/restart. Stable standalone helper/unit/drop-in copies in
the state directory are readable0644 under the existing traversable0755 parent;
private journals/trust remain0600. They import no versioned project code. Changed
stable guard bytes require an explicit future migration; updates cannot silently
replace the admission contract. First installation establishes the gate before
selection. Active, numerically validated user managers receive daemon-reload.
Local user-manager calls resolve each validated UID through the account database
and use `runuser` with a fixed, cleared environment and that UID's runtime D-Bus
socket. No user shell runs, including for the greeter's non-login account. A
failed reload is ignored only after systemd confirms that manager is stopped or
failed; errors from a still-active or ambiguous manager remain failures.

Logind snapshots restart at most three times when the exact C-locale error proves
a listed session vanished before property lookup. Every retry re-enumerates the
whole inventory, so a concurrent new login is retained. Repeated churn produces
a conservative blocking observation and the next scheduled check retries;
unrelated command failures never count as logout.

A persistent root-owned admission.pending marker survives updater interruption.
The guard releases SH and retries while this marker exists, so recovery can take
EX. Only pending recovery/rollback may tolerate a registered GDM session whose
canonical systemd units prove a waiting Shell startjob with MainPID=0 and a live
activating admission process. Foreign overrides, ambiguous unit state and every
running Shell still block. Scheduled recovery runs before the graphical-session
branch, avoiding a pending-marker/login deadlock. Interrupted removal journals
version names, hashes all remaining files, retains manifests until last deletion,
and resumes only owned deletion; added files remain protected. Recovery clears
the marker after a healthy selection, completed rollback or completed removal.

POSIX tests exercise real competing locks, notify readiness, updater-crash marker
recovery and inode retention using disposable roots. Offline systemd-analyze
checks a GNOME50 ordering fixture with the real project units; it does not run
GDM or prove the distribution's physical session lifecycle. Guard failure or an
unrecovered marker intentionally prevents a new supported Shell start; recovery
from a TTY remains available. Direct GNOME Shell processes, custom user units and
other startup paths can bypass this gate and are outside the supported contract.

## Preparation across filesystem boundaries

Verified archives download into exclusive temporary storage beneath the state
directory. Extraction uses a separate exclusive temporary directory directly
under `versions`, so the final candidate rename stays on the destination
filesystem even when Fedora places `/var` and `/opt` on different mounts or
btrfs subvolumes. Preparation never changes the active version reference.
Normal success/failure removes only this invocation's temporary directories;
unrelated staging entries, symlink destinations and late version collisions are
preserved or rejected. A real POSIX test prepares a signed bundle with state and
versions on different device IDs, alongside corruption and collision cases.

Preparation journals creation intent and each temporary directory's device/inode
identity before extraction. A following preparation or removal first validates
and cleans that exact workspace. A retained archive must match the authenticated
release hash before partial extracted files can be compared with its exact byte
prefixes. Unknown entries, symlinks, hard links, modified bytes, changed ownership
or replaced directories cause refusal without deleting retained evidence. Only
empty directories at the journaled creation gap can be removed without a recorded
inode. Tests kill a real subprocess during extraction and immediately after
publication, then verify successful recovery and preservation of foreign files.

## Public integration directory permissions

The privileged updater keeps its private state umask. Missing host integration
directories are created as `0755` under a narrowly scoped umask `022`, restored even
when creation fails. Existing directory modes remain unchanged. An existing
parent without public read/traversal permission causes an actionable error with
its exact path instead of silently installing unreadable user units. Review that
directory's ownership and intended permissions; do not recursively chmod system
directories. Previously created directories have no recorded ownership proof,
so the installer does not automatically widen their permissions.
