# Physical acceptance records

No physical acceptance record exists yet. Never create a passing record from
unit tests, a nested compositor, screenshots, or intended behavior.

After testing actual candidate bytes, a maintainer records `<full-commit>.json`
with schema 1, full commit, artifact_sha256, named reviewer and ISO date. The
platform must name Fedora 44, GNOME 50, Wayland, x86_64 and ThinkPad X1 Yoga Gen 8.
`checks` must include every key in `scripts/verify-acceptance.py`, each with the
observed result. Include `animation` with refresh_hz=60, measured frame count,
within_budget count and recurring_stalls. Record unresolved `limitations`.
Keep private identifiers and raw system logs outside public records.

`concurrent_gdm_login_update` must exercise a real GDM login competing with
activation, including the pre-Shell admission lease, update interruption and
subsequent recovery. A locked or inactive existing session must still prevent
activation. No session may be forcibly terminated. POSIX lock tests alone do
not establish this complete GNOME/systemd integration result.

The release gate requires all checks passed, no unresolved limitations, at least
120 measured frames and 95 percent within 16.67 ms without recurring stalls.
It hashes the artifact and rejects reports for different bytes or commits.
This validates report completeness; it cannot substitute for the human testing.
