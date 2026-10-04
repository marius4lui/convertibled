# CI and releases

The Product checks workflow builds/tests Linux services, GTK settings and the
Shell extension, and validates documentation links. Checks use read-only token
permissions and commit-pinned Actions. Passing Ubuntu compilation is not Fedora
or physical-device acceptance. Public publishing remains separately gated.
Distribution CI exercises signature failures, archive rejection, installation
transactions and recovery in isolated temporary directories. Pull requests run
once per update; branch pushes do not duplicate the same checks.
Dependency gates check RustSec advisories, declared licenses and registry sources
with a pinned cargo-deny version, plus npm's high-severity audit. These gates do
not replace review of privileged code or a production signing-key procedure.

Successful Fedora CI creates an internal candidate bundle with SHA256SUMS,
source/version provenance and an SPDX 2.3 Rust dependency inventory. The current
candidate uses an optimized release build; it is not a public production release.
The inventory declares package licenses without file-level analysis or operating
system components. Public release must use the exact accepted bytes and the
record described in [physical acceptance](acceptance/README.md).

`Prepare accepted release draft` is manual and runs only from main. It refuses
environments without required reviewers, unsuccessful/non-main candidate runs,
missing matching version tags, different artifact bytes, missing physical
acceptance or an existing release. Configure the `release` environment with
required reviewers, `RELEASE_SIGNING_KEY` and public `RELEASE_KEY_ID` only after
key custody is established. The offline trust root never enters CI. API access
to environment protection must be available; inability to verify it fails closed.
The workflow signs accepted bytes, verifies the signer against the reviewed
root-signed keyring, packages the bootstrap installer and creates a draft only.
It never rebuilds or overwrites the accepted product bundle.

`Publish accepted release and promote channel` is a separate manual main-only
workflow behind the same reviewed environment. It rechecks signatures, freshness,
tag/commit identity, physical acceptance and exact bootstrap source/trust bytes.
It requires the deployed root-signed keyring to match the release. After making
the release public it downloads and verifies the public bundle before atomically
writing the selected channel file on `update-channels`. GitHub's required prior
blob SHA prevents overwriting a competing promotion; a conflict fails without
retry. Both workflows share a concurrency group. Failures before promotion leave
the prior channel unchanged; a release already made public remains public and
the job may be rerun while metadata is fresh.

Maintainers provision reviewed public `release/trust.json` and the offline-signed
`release/keyring.json` on main, plus the `update-channels` branch before dispatch.
Trust URLs use `https://raw.githubusercontent.com/OWNER/REPO/main/release/keyring.json`
and `https://raw.githubusercontent.com/OWNER/REPO/update-channels/stable.json`
(or `preview.json`). Neither workflow fabricates missing production trust.
The bootstrap asset is `convertibled-installer.tar.gz`; authenticating its source
before executing `sh installer/install` remains the initial trust boundary.

## Version policy

Use SemVer with `vX.Y.Z` tags; previews may use `-alpha.N` or `-beta.N`.
One canonical application version must feed binaries, bundles, UI, and metadata.
Config and D-Bus schema versions are independent and documented. Before 1.0,
breaking changes still require explicit notes and migration guidance.

## Pull request CI

Formatting, Clippy with warnings denied, meaningful tests, Linux build,
documentation checks, dependency/license review, and installer/update integration
tests as implemented. Pin third-party Actions to reviewed commit SHAs and grant
minimal permissions. Untrusted PRs do not receive signing/publishing secrets.
Define Rust MSRV and release platform baseline before adding a build matrix.

## Release sequence

1. Release PR updates canonical version, changelog, compatibility, and migrations.
2. Required CI and named physical acceptance pass for advertised behavior.
3. Authorized maintainer creates a protected version tag on the reviewed commit.
4. Build from that exact commit; verify tag/version consistency and artifact content.
5. Create draft release with tested bundles, signed metadata, checksums, SBOM,
   provenance, installation/recovery instructions, and limitations.
6. Publish only with authorization and all required artifacts present.
7. Dispatch the protected publisher to verify public bytes and atomically promote
   the selected channel. A channel conflict requires fresh inspection, not force.

Never rebuild different bytes under the same published version. Prefer immutable
published releases. Failed release jobs leave channel pointers unchanged. Retry
must preserve traceability and not overwrite already published artifacts.

## Required release contents

Architecture/platform-qualified bundle, installer entry point, uninstall/recovery
instructions, signed update metadata, checksum manifest, SBOM/provenance where
implemented, and release notes listing new behavior, fixes, known issues,
compatibility, migrations, and physical evidence.

## Acceptance record

Record commit, artifact hashes, CI run, clean-install test, upgrade/rollback tests,
desktop/device versions, and physical UX results. Missing device acceptance
blocks claims requiring it. Never describe unavailable CI as passing.

## Offline trust tooling

`scripts/release/keyring.py` accepts a JSON map of release IDs to public PEM
keys, an independently authenticated root map, an external offline private root
key, a new positive sequence and a validity of 1–366 days. It signs and verifies
the result before creating its output; existing files are never replaced. Root
and release public keys must differ. Removing a release key and advancing the
keyring sequence revokes it. Preserve the previous sequence in the maintainer's
offline records; production private keys are never generated by these tools.

`scripts/release/verify.py` authenticates keyring and channel signatures, expiry,
candidate hash/version, bundle size/hash and immutable GitHub artifact URL.
Promotion additionally checks the prior channel sequence, version and immutable
same-version bytes. Real ephemeral Ed25519 tests cover corruption, incorrect
trust, expiry, replay, downgrade and root/release separation.

`scripts/release/bootstrap.py` packages installer/updater source from the exact
accepted Git commit plus reviewed public trust as `installer/bootstrap-trust.json`.
The archive is deterministic and contains no private keys. Maintainers must
provide real authenticated public trust; placeholders cannot produce an installer.
Executing this bootstrap still requires authenticating its source independently.

## Maintenance

Dependency update PRs use normal checks. Security fixes receive explicit impact
and upgrade guidance. Establish a support window before v1.0; do not imply older
versions are maintained without a policy. Protect publishing credentials and
review key rotation/revocation procedures.
