"""Fixed destination ownership; never accept an arbitrary install path."""
from .storage import atomic, read
from updater.model import UpdateError

UUID = "convertibled@convertibled.org"
LINKS = {
    "usr/bin/convertiblectl": "bin/convertiblectl",
    "usr/bin/convertibled-settings": "bin/convertibled-settings",
    "usr/share/gnome-shell/extensions/" + UUID: "share/gnome-shell/extensions/" + UUID,
    "usr/lib/systemd/system/convertibled.service": "data/systemd/convertibled.service",
    "usr/lib/systemd/user/convertibled-session.service": "data/systemd/convertibled-session.service",
    "usr/lib/systemd/user/graphical-session.target.wants/convertibled-session.service": "data/systemd/convertibled-session.service",
    "usr/share/dbus-1/system.d/org.convertibled.Daemon1.conf": "data/dbus/org.convertibled.Daemon1.conf",
    "usr/lib/systemd/system/convertibled-update.service": "data/systemd/convertibled-update.service",
    "usr/lib/systemd/system/convertibled-update.timer": "data/systemd/convertibled-update.timer",
    "usr/share/polkit-1/actions/org.convertibled.installer.policy": "data/polkit/org.convertibled.installer.policy",
    "usr/share/applications/org.convertibled.Settings.desktop": "share/applications/org.convertibled.Settings.desktop",
    "usr/share/icons/hicolor/scalable/apps/org.convertibled.Settings.svg": "share/icons/hicolor/scalable/apps/org.convertibled.Settings.svg",
    "usr/share/metainfo/org.convertibled.Settings.metainfo.xml": "share/metainfo/org.convertibled.Settings.metainfo.xml",
}


def expected(layout, source):
    # Absolute on the installed host, portable inside disposable test roots.
    return layout.current / source


def install(layout):
    owned = read(layout.state / "owned.json", {"schema": 1, "links": {}})
    if owned.get("schema") != 1:
        raise UpdateError("Unsupported ownership manifest")
    for destination, source in LINKS.items():
        target = layout.root / destination
        if target.exists() or target.is_symlink():
            if not target.is_symlink() or str(target.readlink()) != str(expected(layout, source)):
                raise UpdateError("Refusing to overwrite unrelated integration: " + destination)
        if not (layout.current / source).exists():
            raise UpdateError("Bundle lacks required integration: " + source)
    # Journal ownership intent before creating links, so a power loss between
    # link creation and journaling cannot leave an untracked project link.
    owned["links"].update(LINKS)
    atomic(layout.state / "owned.json", owned)
    for destination, source in LINKS.items():
        target = layout.root / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_symlink():
            target.symlink_to(expected(layout, source), target_is_directory=destination.endswith(UUID))


def remove(layout):
    owned = read(layout.state / "owned.json", {"schema": 1, "links": {}})
    retained = []
    for destination, source in owned.get("links", {}).items():
        if LINKS.get(destination) != source:
            raise UpdateError("Invalid ownership manifest")
        target = layout.root / destination
        if target.is_symlink() and str(target.readlink()) == str(expected(layout, source)):
            target.unlink()
        elif target.exists() or target.is_symlink():
            retained.append(destination)
    if retained:
        raise UpdateError("User-modified integration retained: " + ", ".join(retained))
    atomic(layout.state / "owned.json", {"schema": 1, "links": {}})
