"""Remove only verified owned files; retain configuration by default."""
import hashlib
from pathlib import Path
from .integration import remove
from .platform import command, graphical_sessions
from .storage import read, atomic
from updater.archive import manifest
from updater.model import UpdateError, version
from .admission_control import exclusive, reload_users, pending


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
    pending(layout, True)
    atomic(layout.state / "transaction.json", {"schema": 1, "phase": "removing", "versions": [path.name for path, names in versions]})
    run(["systemctl", "disable", "--now", "convertibled-update.timer", "convertibled.service"])
    remove(layout, preserve_admission=True)
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
