"""Version/session/boot-bound Shell expectation, separate from actual health."""
import re
from pathlib import Path
from updater.model import UpdateError, decode
from .storage import sync_directory

BOOT = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
NAME = re.compile(r"shell-(intent|health)-([0-9]{1,10})\.json")


def boot_id():
    value = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    if not BOOT.fullmatch(value):
        raise UpdateError("Kernel boot identity unavailable")
    return value


def files(layout):
    directory = layout.state / "health"
    if directory.is_symlink():
        raise UpdateError("Refusing linked health directory")
    if not directory.exists():
        return []
    result = []
    for index, path in enumerate(directory.iterdir()):
        if index >= 2048:
            raise UpdateError("Health inventory exceeds supported size")
        if NAME.fullmatch(path.name):
            if path.is_symlink() or not path.is_file():
                raise UpdateError("Invalid health receipt file")
            result.append(path)
    return result


def reset(layout):
    # Only fixed project receipt names, never unrelated diagnostics or files.
    paths = files(layout)
    for path in paths:
        path.unlink()
    if paths:
        sync_directory(layout.state / "health")


def identity(value):
    if not isinstance(value, dict):
        return None
    uid, session, boot = (value.get(key) for key in ("uid", "session", "boot_id"))
    if type(uid) is not int or not 0 <= uid < 2**32:
        return None
    if not isinstance(session, str) or not re.fullmatch(r"[A-Za-z0-9]{1,32}", session):
        return None
    if not isinstance(boot, str) or not BOOT.fullmatch(boot):
        return None
    return {"uid": uid, "session": session, "boot_id": boot}


def receipt(path, candidate):
    try:
        with path.open("rb") as stream:
            value = decode(stream.read(4097), maximum=4096)
        if type(value) is not dict:
            return None
        if type(value.get("schema")) is not int or value["schema"] != 1 or value.get("version") != candidate:
            return None
        who = identity(value)
        match = NAME.fullmatch(path.name)
        if match is None or who is None or str(who["uid"]) != match[2]:
            return None
        field = "expected" if match[1] == "intent" else "healthy"
        if set(value) != {"schema", "version", "uid", "session", "boot_id", field}:
            return None
        if field not in value or (value[field] is not None and type(value[field]) is not bool):
            return None
        return value
    except (OSError, ValueError, UpdateError):
        return None


def observe(value, sessions):
    boot = boot_id()
    observed = [identity(item) for item in value.get("observed_sessions", [])]
    if len(observed) > 512 or any(item is None for item in observed) or len(sessions) > 512:
        raise UpdateError("Invalid Shell acceptance session inventory")
    current = []
    value["unidentified_sessions"] = False
    for item in sessions:
        user = str(item.get("user", ""))
        who = identity({"uid": int(user) if user.isdecimal() and len(user) <= 10 else None,
                        "session": item.get("session"), "boot_id": boot})
        if who is None:
            value["unidentified_sessions"] = True
            continue
        current.append(who)
    # A later login for the same user supersedes their earlier trial session;
    # another user's unresolved expectation is retained independently.
    current_users = {item["uid"] for item in current}
    value["observed_sessions"] = [item for item in observed if item["uid"] not in current_users] + current
    if len(value["observed_sessions"]) > 512:
        raise UpdateError("Shell acceptance session inventory exceeds supported size")


def evaluate(layout, value):
    candidate, boot = value["candidate"], boot_id()
    receipts = [receipt(path, candidate) for path in files(layout)]
    intents = {item["uid"]: item for item in receipts if item is not None and "expected" in item}
    health = {item["uid"]: item for item in receipts if item is not None and "healthy" in item}
    observed = [identity(item) for item in value.get("observed_sessions", [])]
    if len(observed) > 512 or any(item is None for item in observed):
        raise UpdateError("Invalid Shell acceptance session inventory")
    users = {item["uid"] for item in observed}
    # A short login may finish between timer ticks. An authenticated, fresh
    # intent receipt is positive evidence of that session, never fabricated login.
    observed += [identity(item) for uid, item in intents.items() if uid not in users and item["boot_id"] == boot]
    if len(observed) > 512:
        raise UpdateError("Shell acceptance session inventory exceeds supported size")
    unknown, enabled = not observed or value.get("unidentified_sessions", False), False
    for who in observed:
        intent = intents.get(who["uid"])
        if who["boot_id"] != boot or intent is None or identity(intent) != who or intent["expected"] is None:
            unknown = True
            continue
        if intent["expected"] is False:
            continue
        enabled = True
        actual = health.get(who["uid"])
        if actual is None or identity(actual) != who or actual["healthy"] is not True:
            return "failed"
    if unknown:
        return "pending_intent"
    return "verified" if enabled else "not_requested"
