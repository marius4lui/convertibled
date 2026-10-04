"""Bounded configuration backup with no executable migration hooks."""
import shutil
import os
from pathlib import Path
from updater.model import UpdateError
from .storage import atomic, read, sync_directory

DEFAULTS = {"schema": 1, "automatic_updates": True, "channel": "stable"}


def preferences(layout):
    value = read(layout.config / "updates.json", DEFAULTS.copy())
    if set(value) != set(DEFAULTS) or value["schema"] != 1 or type(value["automatic_updates"]) is not bool or value["channel"] not in ("stable", "preview"):
        raise UpdateError("Invalid update preferences")
    return value


def set_preferences(layout, automatic=None, channel=None):
    value = preferences(layout)
    if automatic is not None:
        if type(automatic) is not bool:
            raise UpdateError("Automatic update preference must be boolean")
        value["automatic_updates"] = automatic
    if channel is not None:
        if channel not in ("stable", "preview"):
            raise UpdateError("Unknown update channel")
        value["channel"] = channel
    atomic(layout.config / "updates.json", value)
    return value


def files(directory):
    directory = Path(directory)
    result = []
    total = 0
    if not directory.exists():
        return result
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise UpdateError("Configuration symlinks cannot be migrated")
        if path.is_dir():
            continue
        if not path.is_file():
            raise UpdateError("Configuration special files cannot be migrated")
        total += path.stat().st_size
        result.append(path)
        if len(result) > 128 or total > 8 * 1024 * 1024:
            raise UpdateError("Configuration backup exceeds limits")
    return result


def backup(layout):
    source_files = files(layout.config)
    target = layout.state / "config-backup"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(mode=0o700)
    for source in source_files:
        destination = target / source.relative_to(layout.config)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        with destination.open("r+b") as stream:
            os.fsync(stream.fileno())
        sync_directory(destination.parent)
    sync_directory(target)


def restore(layout):
    source = layout.state / "config-backup"
    if not source.is_dir() or source.is_symlink():
        raise UpdateError("Configuration backup missing")
    saved = files(source)
    files(layout.config)
    # No schema-changing migration exists: restoring replaces only the backed-up
    # schema-1 files. New files are retained rather than deleting user content.
    for path in saved:
        target = layout.config / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        with target.open("r+b") as stream:
            os.fsync(stream.fileno())
        sync_directory(target.parent)
    sync_directory(layout.config)
