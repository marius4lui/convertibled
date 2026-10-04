"""Sanitized public state snapshot; no keys, paths, session IDs or logs."""
import os
from .configuration import preferences
from .storage import atomic, read


def publish(layout, error=None):
    transaction = read(layout.state / "transaction.json", {})
    available = read(layout.state / "available.json", {})
    prepared = read(layout.state / "prepared.json", {})
    value = {"schema": 1, "installed": layout.active(), "available": available.get("version"), "prepared": prepared.get("version"), "phase": transaction.get("phase", "idle"), "preferences": preferences(layout), "error": str(error)[:512] if error else None}
    # Root-owned state is traversable for this explicitly sanitized file only.
    layout.state.chmod(0o755)
    atomic(layout.state / "status.json", value)
    (layout.state / "status.json").chmod(0o644)
    return value


def public(layout):
    return read(layout.state / "status.json", {"schema": 1, "installed": None, "phase": "not_installed", "error": None})
