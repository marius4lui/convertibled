# Configuration and CLI specification

No parser or commands exist yet. Examples below are proposed interfaces.

## Files and precedence

Proposed paths: `/etc/convertibled/config.toml` for system policy and
`~/.config/convertibled/config.toml` for user preferences.
Built-in defaults → system defaults → allowed user overrides → temporary manual
override. System security/authorization constraints cannot be weakened by user
configuration. Resolve merged configuration explicitly in diagnostics.

Use a schema version, reject invalid types/unknown keys with clear errors, and
validate the entire candidate before reload. Failed reload retains the previous
valid configuration. Migrations preserve the original and document compatibility.

## Profiles

Actions are tri-state where applicable: enabled, disabled, unchanged.
Defaults preserve desktop settings. Manual profile overrides are distinct from
observed posture and have documented persistence/reset behavior.

Illustrative schema, not a supported configuration:

```toml
schema_version = 1

[profiles.tablet]
rotation = "enabled"
osk = "unchanged"
internal_keyboard = "unchanged"
internal_touchpad = "unchanged"
scaling = "unchanged"
```

An enabled action requires backend support. Unsupported actions must be
reported and must not silently change to a different policy.

## Planned CLI

`status`, `devices`, `capabilities`, `watch`, `doctor`, `mode <profile|auto>`,
`config validate`, and `reload`. Add `--json` to diagnostic/status commands.
Define stable exit codes and versioned JSON before implementation.

Status includes observations, inferred posture/confidence, selected profile,
override origin, desired/applied actions, errors, backend, and versions.
`doctor` exports a report only on request and sanitizes private identifiers.

## Hooks

Deferred. If implemented, hooks run in user context with explicit argument
arrays, bounded execution time, documented environment, and no default shell
evaluation. A root-command escape hatch is outside initial scope.
