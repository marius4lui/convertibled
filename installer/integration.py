"""Fixed destination ownership; never accept an arbitrary install path."""
import os
from .storage import atomic, read, sync_directory
from updater.model import UpdateError

UUID = "convertibled@convertibled.org"
LINKS = {
    "etc/xdg/autostart/org.convertibled.Onboarding.desktop": "data/autostart/org.convertibled.Onboarding.desktop",
    "usr/bin/convertiblectl": "bin/convertiblectl",
    "usr/bin/convertibled-settings": "bin/convertibled-settings",
    "usr/share/gnome-shell/extensions/" + UUID: "share/gnome-shell/extensions/" + UUID,
    "usr/lib/systemd/system/convertibled.service": "data/systemd/convertibled.service",
    "usr/lib/systemd/user/convertibled-session.service": "data/systemd/convertibled-session.service",
    "usr/lib/systemd/user/convertibled-admission.service": "data/systemd/convertibled-admission.service",
    "usr/lib/systemd/user/org.gnome.Shell@user.service.d/convertibled-admission.conf": "data/systemd/org.gnome.Shell@user.service.d/convertibled-admission.conf",
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
    from .admission_control import STABLE
    if source in STABLE:
        return layout.state / STABLE[source]
    # Absolute on the installed host, portable inside disposable test roots.
    return layout.current / source


def refresh_policy(layout, target, source):
    temporary = target.with_name(".convertibled-next-" + target.name)
    if temporary.exists() or temporary.is_symlink():
        if not temporary.is_symlink() or str(temporary.readlink()) != str(expected(layout, source)):
            raise UpdateError("Unrelated policy staging entry retained")
        temporary.unlink()
    temporary.symlink_to(expected(layout, source))
    os.replace(temporary, target)
    sync_directory(target.parent)


def install(layout, admission_only=False, candidate=None):
    from .admission_control import provision
    from .admission_control import STABLE
    links = {destination: source for destination, source in LINKS.items() if not admission_only or source in STABLE}
    owned = read(layout.state / "owned.json", {"schema": 1, "links": {}})
    if owned.get("schema") != 1:
        raise UpdateError("Unsupported ownership manifest")
    for destination, source in links.items():
        target = layout.root / destination
        if target.exists() or target.is_symlink():
            if not target.is_symlink() or str(target.readlink()) != str(expected(layout, source)):
                raise UpdateError("Refusing to overwrite unrelated integration: " + destination)
    provision(layout, layout.versions / candidate if candidate else None)
    for destination, source in links.items():
        if not expected(layout, source).exists():
            raise UpdateError("Bundle lacks required integration: " + source)
    # Journal ownership intent before creating links, so a power loss between
    # link creation and journaling cannot leave an untracked project link.
    owned["links"].update(links)
    atomic(layout.state / "owned.json", owned)
    for destination, source in links.items():
        target = layout.root / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        if destination == "usr/share/polkit-1/actions/org.convertibled.installer.policy":
            # A changed `current` symlink is outside Polkit's watched actions
            # directory. Refresh its entry atomically to trigger policy reload.
            refresh_policy(layout, target, source)
        elif not target.is_symlink():
            target.symlink_to(expected(layout, source), target_is_directory=destination.endswith(UUID))


def remove(layout, preserve_admission=False):
    from .admission_control import STABLE
    owned = read(layout.state / "owned.json", {"schema": 1, "links": {}})
    retained = []
    preserved = {}
    entries = owned.get("links", {}).items()
    for destination, source in sorted(entries, key=lambda item: item[0].endswith("convertibled-admission.service")):
        if LINKS.get(destination) != source:
            raise UpdateError("Invalid ownership manifest")
        if preserve_admission and source in STABLE:
            preserved[destination] = source
            continue
        target = layout.root / destination
        if destination == "usr/share/polkit-1/actions/org.convertibled.installer.policy":
            temporary = target.with_name(".convertibled-next-" + target.name)
            if temporary.is_symlink() and str(temporary.readlink()) == str(expected(layout, source)):
                temporary.unlink()
            elif temporary.exists() or temporary.is_symlink():
                retained.append(str(temporary.relative_to(layout.root)))
        if target.is_symlink() and str(target.readlink()) == str(expected(layout, source)):
            target.unlink()
        elif target.exists() or target.is_symlink():
            retained.append(destination)
    if retained:
        raise UpdateError("User-modified integration retained: " + ", ".join(retained))
    atomic(layout.state / "owned.json", {"schema": 1, "links": preserved})
