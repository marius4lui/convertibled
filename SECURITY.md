# Security policy

No software release exists yet. There are no supported release versions to list.
This policy will gain a maintained-version table when releases begin.

## Reporting

Do not disclose exploitable vulnerabilities in public issues. Use GitHub private
vulnerability reporting if enabled for this repository. If it is unavailable,
open an issue asking the maintainer for a private reporting channel without
including exploit details, credentials, or sensitive logs. A dedicated contact
and response expectations must be established before the first release.

Include affected version/commit, impact, prerequisites, and a minimal sanitized
reproduction through the private channel. No response-time guarantee is currently
published.

## Security requirements

Privilege separation, authorized session mutations, safe internal-input recovery,
signature-verified updates, bounded archive extraction, migration recovery,
and minimal data collection are implementation/release requirements. See
`docs/architecture.md` and `docs/install-updates.md`.

Never commit signing keys or credentials. No telemetry or keystroke collection
is planned. Diagnostics exports must be explicit and sanitized.
