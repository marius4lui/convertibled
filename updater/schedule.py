"""Frequent logout checks, infrequent bounded background network work."""
import datetime as dt
from installer.storage import atomic, read
from .model import timestamp, UpdateError


def due(layout, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    previous = read(layout.state / "schedule.json", {})
    if previous.get("checked"):
        last = timestamp(previous["checked"])
        # Clock rollback never bypasses signed metadata freshness, but must not
        # create a network storm. A later restored clock resumes normal checks.
        if now - last < dt.timedelta(hours=6):
            return False
    atomic(layout.state / "schedule.json", {"schema": 1, "checked": now.isoformat()})
    return True


def quarantined(layout, candidate):
    previous = read(layout.state / "transaction.json", {})
    return previous.get("phase") == "rolled_back" and previous.get("candidate") == candidate
