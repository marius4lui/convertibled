"""Remove only verified owned files; retain configuration by default."""
import hashlib
from pathlib import Path
from .integration import remove
from .platform import command, graphical_sessions
from .storage import read, atomic
from updater.archive import manifest
from updater.model import UpdateError, version


def owned_version(path):
    version(path.name)
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
    if actual != expected:
        raise UpdateError("Unowned content in version directory retained")
    for name, info in contract["files"].items():
        item = path / name
        if item.stat().st_size != info["size"] or hashlib.sha256(item.read_bytes()).hexdigest() != info["sha256"]:
            raise UpdateError("Modified installed file retained: " + name)
    return actual


def uninstall(layout, run=command, sessions=graphical_sessions):
    if sessions():
        raise UpdateError("Log out graphical sessions before removal")
    versions = []
    for path in layout.versions.iterdir():
        if not path.is_dir() or path.is_symlink():
            raise UpdateError("Unowned version entry retained")
        versions.append((path, owned_version(path)))
    run(["systemctl", "disable", "--now", "convertibled-update.timer", "convertibled.service"])
    remove(layout)
    layout.current.unlink(missing_ok=True)
    for path, names in versions:
        for name in sorted(names):
            (path / name).unlink()
        for child in sorted(path.rglob("*"), key=lambda value: len(value.parts), reverse=True):
            if child.is_dir():
                child.rmdir()
        path.rmdir()
    run(["systemctl", "daemon-reload"])
    atomic(layout.state / "transaction.json", {"schema": 1, "phase": "removed"})
    return {"removed": True, "configuration_retained": True}
