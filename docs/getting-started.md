# Getting started

convertibled is experimental. There is no supported public release or production
trust configuration yet. The instructions below describe the installer workflow
for authenticated release assets; they are not a download announcement.

## Requirements

The installer targets Fedora 44, x86_64, GNOME Shell 50 and Wayland. The reference
acceptance device is ThinkPad X1 Yoga Gen 8; physical support is still unverified.
Installation needs administrator authorization, Python 3, OpenSSL and the
platform tools checked by preflight. Competing dock/tiling extensions may block
installation until their compatibility has been reviewed.

Ordinary mode switching works without a network connection. Network installation
and update preparation need access to the authenticated release locations.

## Install from authenticated assets

The release installer asset is named `convertibled-installer.tar.gz`. Before
running it, independently authenticate its origin and the project's published
trust-root fingerprint. A checksum downloaded alongside an untrusted archive
alone does not establish authenticity. See [trust bootstrap](distribution.md#trust-bootstrap-and-installation).

The release archive includes its public trust configuration; normal installation
does not require editing trust JSON. Maintainers must provision production trust
before publishing this asset. Private signing keys never belong in the archive.

Extract the authenticated archive into an empty directory and run from that
extracted directory:

```sh
sh installer/install
```

The installer asks whether to enable the tablet workspace for your account,
then requests administrator authentication. Use `--enable-workspace` to record
that choice explicitly or `--no-workspace` to leave it disabled. To opt out of automatic
update checking and preparation, use `sh installer/install --no-automatic-updates`
instead. Existing host trust is preserved. Compatibility and release signatures
are checked before the version is installed. Review any reported error before
retrying. Activation requires all affected graphical users to log out; the
installer does not force logout.

## First login

If you accepted workspace setup, your next GNOME Wayland login enables the
extension for your account and opens Settings once. Later disabling the
extension is respected. Other accounts are not opted in automatically.

If you declined setup, enable it later as your normal user:

```sh
sh /opt/convertibled/current/installer/finish-user.sh
```

This changes only your own extension preference. Each additional user must opt
in separately. Open **convertibled Settings** and review **Overview** and
**Hardware**. Detected posture, requested profile and applied workspace are
distinct; a successful request does not by itself prove a desktop change.

Choose **Automatic** for sensor-driven behavior, or a manual profile when the
device has no usable tablet switch. Folding keeps the current application
focused. Use Home to return to the tablet desktop. The dock and Overview expose
navigation without gestures. To use touchscreen gestures, touch the setup target
on the integrated display when prompted; reconnecting the device requires renewed
source approval. Touchpad gestures remain GNOME's responsibility.

## Updates and removal

Open **Settings → Updates** to check or prepare an update, choose stable/preview,
or opt out of automatic preparation. The equivalent CLI commands are:

```sh
convertiblectl update status
convertiblectl update check
convertiblectl update prepare
convertiblectl update activate
convertiblectl update automatic off
```

With automatic updates off, **Install after logout** explicitly schedules the
prepared version without enabling automatic updates. Review its confirmation,
then log out when ready; nobody is logged out automatically. The equivalent
`convertiblectl update activate` (alias `request-activate`) also queues the
operation. The request binds the installed version, prepared candidate and
channel; a changed candidate requires review. Signatures and freshness are
checked again before activation. **Cancel scheduled action** also cancels this
request while it is waiting.

Mutating update operations request administrator authentication. Prepared is
different from installed. Activation waits for all affected graphical users to
log out; locking or switching users is insufficient. New Shell code loads at the
next login. The updater retains a previous version and recovers failed activation
at a safe logout boundary. See [troubleshooting](troubleshooting.md) for recovery.

For recovery or removal, open **Settings → Updates → Recovery and removal**.
Review the action and confirm it, then authorize the administrator request.
Removal is scheduled; it does not remove the running workspace immediately.
The status shows the scheduled action and whether it is waiting, running or
failed. Save your work and log out normally when ready. All graphical users
must log out; these explicit requests also run when automatic updates are off.

Equivalent CLI requests are:

```sh
convertiblectl update recover
convertiblectl update rollback
convertiblectl update uninstall
convertiblectl update cancel-pending
```

The `request-recover`, `request-rollback` and `request-uninstall` aliases have
the same queued behavior. **Cancel scheduled action** cancels a waiting or
failed request. An action already running cannot be interrupted. A failed
request remains visible for review; explicitly request it again to retry, or
cancel before choosing another action. Requests bind the selected installed
version so an intervening installation cannot silently change their target.

Before removal, each opted-in user can disable the extension in their own
GNOME session to restore their workspace preferences:

```sh
sh /opt/convertibled/current/installer/finish-user.sh --disable
```

If Settings is unavailable, immediate offline removal remains available from
a TTY after all graphical users log out:

```sh
sudo python3 -I /opt/convertibled/current/installer/cli.py uninstall
```

Removal retains configuration/state by default and removes only verified owned
files. Added or changed files stop removal for review. The dedicated service
account is retained for safe reinstall. See [distribution](distribution.md)
for ownership, retained data and offline operations.

## Development preview

The [native demo](../demo/README.md) runs the real extension in an isolated
Fedora/GNOME session on Windows via WSLg. It is useful for visual review without
installing the product into a real desktop. It simulates hardware and cannot
validate physical touch, folding, input recovery or reference-device performance.
