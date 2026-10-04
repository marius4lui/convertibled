# Troubleshooting

Start with **Settings → Overview** and **Hardware**. Check detected posture,
requested profile, applied workspace and the explanation for each capability.
An unavailable capability or service is not a successful action.

## The tablet workspace does not appear

Verify that the session uses GNOME 50 and Wayland and that your user enabled
`convertibled@convertibled.org`. After installation, log out and back in before
running the [first-login step](getting-started.md#first-login). Other users do
not inherit your opt-in.

```sh
convertiblectl status
convertiblectl capabilities
convertiblectl doctor
```

If the sensor is absent or unknown, automatic behavior conservatively falls back
to laptop. In your active, unlocked graphical session, try a manual request:

```sh
convertiblectl mode tablet
convertiblectl status
```

Return with `convertiblectl mode auto` or `convertiblectl mode laptop`.
Manual selection does not create sensor evidence. A locked, remote or ambiguous
session may deny changes. Do not run the desktop UI as root.

## Gestures or rotation are unavailable

Use the visible Home/Overview controls while touchscreen gestures are unavailable.
Gesture source approval requires touching the setup target on the integrated
display after login or device reconnect. Enabling a preference alone cannot prove
which physical device is the built-in touchscreen.

GNOME owns display rotation, touch mapping and the on-screen keyboard. Inspect
the per-action outcomes in Settings; successful workspace activation does not
prove native rotation or OSK support. External displays retain desktop behavior.
Input suppression and automatic scaling are deliberately disabled.

## An update is waiting or fails

Check **Settings → Updates** or `convertiblectl update status`. Preparation may
download and verify a version while you work. Activation waits for all affected
graphical users to log out. A locked session still blocks it.

Signature, expired metadata, revoked key, platform or archive errors must be
resolved with authenticated assets. Do not bypass verification, manually change
`/opt/convertibled/current`, or edit transaction journals. No configured production
trust means updates cannot authenticate a release.

If the desktop is available, **Settings → Updates → Recovery and removal**
can schedule recovery or restoration of the retained previous version. The
equivalent `convertiblectl update recover` and `convertiblectl update rollback`
requests wait until all graphical users log out, even with automatic updates
disabled. Review the scheduled action, status and details before logging out.
Waiting is not completion. A failed request stays visible and does not retry
silently; repeat the reviewed request to retry or use
`convertiblectl update cancel-pending` to cancel it. Cancellation cannot interrupt
a running critical operation. A changed installed version requires a fresh
reviewed request rather than applying maintenance to an unexpected version.

For a blocked subsequent login, use a TTY and the retained installed helper
after graphical users have logged out. These direct helper verbs perform
immediate offline recovery rather than queueing a desktop request:

```sh
sudo python3 -I /opt/convertibled/current/installer/cli.py recover
```

To explicitly request the retained previous version:

```sh
sudo python3 -I /opt/convertibled/current/installer/cli.py rollback
```

Recovery still checks transaction state and session safety. Rollback requires an
available compatible retained version; it is not arbitrary downgrade support.
If no installed helper is available, use independently authenticated installer
source and follow the [distribution recovery contract](distribution.md).

## Report a problem

In **Settings → Diagnostics**, collect and review the report before explicitly
exporting it. Nothing uploads automatically. CLI collection is also available:

```sh
convertiblectl --json doctor
convertiblectl doctor --export diagnostics.json
```

Include the project version/commit, Fedora and GNOME versions, device model,
reproduction steps, expected behavior, actual behavior and sanitized diagnostics.
Do not include serial numbers, credentials, private logs or keystroke captures.
Use [the security policy](../SECURITY.md) for vulnerabilities and
[contribution guidance](../CONTRIBUTING.md) for ordinary bug reports.
