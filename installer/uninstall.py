"""Remove only verified owned files; retain configuration by default."""
import hashlib
import os
from pathlib import Path
from .integration import remove
from .platform import command, graphical_sessions
from .storage import read, atomic, sync_directory
from updater.archive import manifest
from updater.model import UpdateError, version
from .admission_control import exclusive, reload_users, pending
from .desktop_cache import refresh_icons

UNITS = {
    "convertibled-update.timer": "timers.target.wants",
    "convertibled.service": "multi-user.target.wants",
}


def enable_links(layout, verified_versions=()):
    owned = []
    for name, directory in UNITS.items():
        allowed = {layout.root / "usr/lib/systemd/system" / name,
                   layout.current / "data/systemd" / name}
        for installed in verified_versions:
            allowed.add(layout.versions / version(installed) / "data/systemd" / name)
        # systemctl --root emits host-absolute targets in disposable roots.
        allowed |= {Path("/") / path.relative_to(layout.root) for path in allowed}
        for relative in (Path(name), Path(directory) / name):
            link = layout.root / "etc/systemd/system" / relative
            if not link.exists() and not link.is_symlink():
                continue
            if not link.is_symlink():
                raise UpdateError("Unrelated project enable entry retained: " + name)
            target = Path(os.path.normpath(str(link.parent / link.readlink())))
            if target not in allowed:
                raise UpdateError("User-modified project enable link retained: " + name)
            owned.append(link)
    return owned


def stop_units(layout, run, verified_versions=()):
    links = enable_links(layout, verified_versions)
    for name in UNITS:
        result = run(["systemctl", "show", name, "-p", "LoadState", "-p", "ActiveState", "-p", "FragmentPath"])
        # Injectable service fake only; command() always returns text. Real
        # failures are never ignored, and absence requires all three properties.
        if result is not None:
            state = dict(line.split("=", 1) for line in result.splitlines() if "=" in line)
            if state == {"LoadState": "not-found", "ActiveState": "inactive", "FragmentPath": ""}:
                continue
            if not {"LoadState", "ActiveState", "FragmentPath"} <= state.keys():
                raise UpdateError("Ambiguous project service state: " + name)
        run(["systemctl", "stop", name])
    # systemctl may already remove these. Recheck ownership before clearing
    # dangling links belonging to absent units (e.g. failed first activation).
    enable_links(layout, verified_versions)
    for link in links:
        if link.is_symlink():
            link.unlink()
            sync_directory(link.parent)


def owned_version(path, interrupted=False):
    version(path.name)
    if interrupted and not (path / "manifest.json").exists():
        if any(item.is_file() or item.is_symlink() for item in path.rglob("*")):
            raise UpdateError("Interrupted removal contains unowned files")
        return set()
    contract = manifest(read(path / "manifest.json"))
    if contract["version"] != path.name:
        raise UpdateError("Version ownership mismatch")
    expected = set(contract["files"]) | {"manifest.json", "release.json"}
    actual = set()
    for item in path.rglob("*"):
        if item.is_symlink():
            raise UpdateError("Modified installed version retained")
        if item.is_file():
            actual.add(item.relative_to(path).as_posix())
    if actual != expected and not (interrupted and actual <= expected):
        raise UpdateError("Unowned content in version directory retained")
    for name, info in contract["files"].items():
        item = path / name
        if interrupted and not item.exists():
            continue
        if item.stat().st_size != info["size"] or hashlib.sha256(item.read_bytes()).hexdigest() != info["sha256"]:
            raise UpdateError("Modified installed file retained: " + name)
    return actual


def uninstall(layout, run=command, sessions=graphical_sessions):
    if sessions():
        raise UpdateError("Log out graphical sessions before removal")
    with exclusive(layout):
        return _uninstall(layout, run, sessions)


def _uninstall(layout, run, sessions):
    if sessions():
        raise UpdateError("Log out graphical sessions before removal")
    from updater.preparation import cleanup as cleanup_preparation
    cleanup_preparation(layout)
    versions = []
    journal = read(layout.state / "transaction.json", {})
    removing = journal.get("phase") == "removing"
    recorded = journal.get("versions", []) if removing else []
    if not isinstance(recorded, list) or any(not isinstance(name, str) for name in recorded):
        raise UpdateError("Invalid interrupted removal journal")
    for path in layout.versions.iterdir():
        if not path.is_dir() or path.is_symlink():
            raise UpdateError("Unowned version entry retained")
        if removing and path.name not in recorded:
            raise UpdateError("Unjournaled version retained during interrupted removal")
        versions.append((path, owned_version(path, interrupted=removing)))
    if sessions():
        raise UpdateError("Graphical login appeared during removal preflight")
    verified_versions = [path.name for path, names in versions] + recorded
    enable_links(layout, verified_versions)
    from .deferred import remove as remove_bootstrap
    remove_bootstrap(layout, run)
    pending(layout, True)
    atomic(layout.state / "transaction.json", {"schema": 1, "phase": "removing", "versions": [path.name for path, names in versions]})
    # The durable removal journal now owns recovery. Consume any queued intent
    # before deleting code so a later reinstall cannot inherit an old removal.
    from .pending import clear as clear_pending
    clear_pending(layout)
    stop_units(layout, run, verified_versions)
    remove(layout, preserve_admission=True)
    refresh_icons(layout, run)
    run(["systemctl", "reload", "dbus.service"])
    reload_users(run)
    layout.current.unlink(missing_ok=True)
    for path, names in versions:
        # Keep ownership metadata until all other files have been removed.
        for name in sorted(names, key=lambda name: name == "manifest.json"):
            (path / name).unlink()
        for child in sorted(path.rglob("*"), key=lambda value: len(value.parts), reverse=True):
            if child.is_dir():
                child.rmdir()
        path.rmdir()
    run(["systemctl", "daemon-reload"])
    atomic(layout.state / "transaction.json", {"schema": 1, "phase": "removed"})
    pending(layout, False)
    remove(layout)
    reload_users(run)
    return {"removed": True, "configuration_retained": True}
