# CI and releases

The Product checks workflow builds/tests Linux services, GTK settings and the
Shell extension, and validates documentation links. Checks use read-only token
permissions and commit-pinned Actions. Passing Ubuntu compilation is not Fedora
or physical-device acceptance. Public publishing remains separately gated.

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
7. Promote update-channel metadata only after artifacts are available and verified.

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

## Maintenance

Dependency update PRs use normal checks. Security fixes receive explicit impact
and upgrade guidance. Establish a support window before v1.0; do not imply older
versions are maintained without a policy. Protect publishing credentials and
review key rotation/revocation procedures.
