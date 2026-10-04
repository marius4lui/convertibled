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

The installer requests administrator authentication. To opt out of automatic
update checking and preparation, use `sh installer/install --no-automatic-updates`
instead. Existing host trust is preserved. Compatibility and release signatures
are checked before the version is installed. Review any reported error before
retrying. Activation requires all affected graphical users to log out; the
installer does not force logout.

## First login

Log in to GNOME Wayland and, as your normal user, enable the installed extension:

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
convertiblectl update automatic off
```

Mutating update operations request administrator authentication. Prepared is
different from installed. Activation waits for all affected graphical users to
log out; locking or switching users is insufficient. New Shell code loads at the
next login. The updater retains a previous version and recovers failed activation
at a safe logout boundary. See [troubleshooting](troubleshooting.md) for recovery.

For removal, each opted-in user should first disable the extension in their own
GNOME session:

```sh
sh /opt/convertibled/current/installer/finish-user.sh --disable
```

After all graphical users log out, run from a TTY:

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
