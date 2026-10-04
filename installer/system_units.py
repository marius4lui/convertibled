"""Stable system-unit enable links and bounded legacy alias migration."""
import hashlib
import os
from pathlib import Path
from .storage import read, sync_directory
from updater.archive import manifest
from updater.model import UpdateError, version

WANTS = {
    "etc/systemd/system/multi-user.target.wants/convertibled.service": "usr/lib/systemd/system/convertibled.service",
    "etc/systemd/system/timers.target.wants/convertibled-update.timer": "usr/lib/systemd/system/convertibled-update.timer",
}


def legacy_aliases(layout):
    """Validate every alias before the caller mutates any of them."""
    result = {}
    for destination, unit in WANTS.items():
        name = Path(unit).name
        for relative in (destination, "etc/systemd/system/" + name):
            path = layout.root / relative
            if not path.exists() and not path.is_symlink():
                continue
            if not path.is_symlink():
                raise UpdateError("Unrelated system-unit entry retained: " + relative)
            target = path.readlink()
            normalized = Path(os.path.normpath(str(path.parent / target)))
            if relative == destination and normalized == layout.root / unit:
                continue
            # Map host-absolute targets emitted by systemctl --root into the
            # disposable root; normal installation uses root=/.
            if not normalized.is_relative_to(layout.root):
                normalized = layout.root / str(normalized).lstrip("/")
            resolved = normalized.resolve()
            try:
                parts = resolved.relative_to(layout.versions.resolve()).parts
            except ValueError as exc:
                raise UpdateError("Foreign system-unit alias retained: " + relative) from exc
            if len(parts) != 4 or parts[1:] != ("data", "systemd", name):
                raise UpdateError("Foreign system-unit alias retained: " + relative)
            installed = version(parts[0])
            directory = layout.versions / installed
            if directory.is_symlink():
                raise UpdateError("Unsafe legacy version directory")
            index = manifest(read(directory / "manifest.json"))
            info = index["files"].get("data/systemd/" + name)
            if index["version"] != installed or info is None or not resolved.is_file():
                raise UpdateError("Unverified legacy system-unit alias")
            content = resolved.read_bytes()
            if len(content) != info["size"] or hashlib.sha256(content).hexdigest() != info["sha256"]:
                raise UpdateError("Modified legacy system-unit file retained")
            result[path] = target
    return result


def remove_direct_aliases(aliases):
    for path, target in aliases.items():
        if path.parent.name != "system":
            continue
        if not path.is_symlink() or path.readlink() != target:
            raise UpdateError("System-unit alias changed during migration")
        path.unlink()
        sync_directory(path.parent)
