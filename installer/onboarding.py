#!/usr/bin/python3 -I
"""Explicitly consented, per-user first-login workspace setup."""
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.dont_write_bytecode = True
from installer.storage import Layout, atomic, read
from updater.model import UpdateError

UUID = "convertibled@convertibled.org"


def consent(layout, user):
    if not isinstance(user, str) or not user.isdecimal() or not 0 < int(user) < 2**32:
        raise UpdateError("Workspace consent requires the authenticated installing user")
    import pwd
    try:
        pwd.getpwuid(int(user))
    except KeyError as exc:
        raise UpdateError("Installing user does not exist") from exc
    record = read(layout.state / "onboarding.json", {"schema": 1, "users": {}})
    record["users"][str(int(user))] = secrets.token_hex(16)
    record["pending_uid"] = int(user)
    record.pop("shell_acceptance", None)
    target = layout.state / "onboarding.json"
    atomic(target, record)
    target.chmod(0o644)


def decline(layout, user):
    target = layout.state / "onboarding.json"
    record = read(target, {"schema": 1, "users": {}})
    if user.isdecimal():
        if record.get("pending_uid") == int(user):
            record.pop("pending_uid", None)
        record.get("users", {}).pop(str(int(user)), None)
    if "pending_uid" not in record:
        record["shell_acceptance"] = "not_requested"
    atomic(target, record)
    target.chmod(0o644)


def wait_for_extension(run, pause):
    # XDG autostart has no obsolete GNOME phase ordering. Wait for Shell's
    # extension registry, not a guessed fixed startup delay. Never enable or
    # consume consent when the registry remains unavailable.
    for attempt in range(15):
        try:
            run(["gnome-extensions", "info", UUID], capture_output=True, timeout=2, check=True)
            return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            if attempt == 14:
                raise UpdateError("GNOME extension registry did not become ready; retry setup after login") from exc
            pause(1)


def onboarding(layout, user_state, uid, environment, run=subprocess.run, pause=time.sleep):
    if uid == 0 or environment.get("XDG_SESSION_TYPE") != "wayland":
        return False
    record = read(layout.state / "onboarding.json", {})
    token = record.get("users", {}).get(str(uid))
    if not token or read(user_state, {}).get("consent") == token:
        return False
    shell = run(["gnome-shell", "--version"], capture_output=True, text=True, timeout=15, check=True)
    if not shell.stdout.strip().startswith("GNOME Shell 50"):
        raise UpdateError("First-login setup requires GNOME Shell 50")
    wait_for_extension(run, pause)
    run(["gnome-extensions", "enable", UUID], capture_output=True, timeout=15, check=True)
    atomic(user_state, {"schema": 1, "consent": token})
    return True


def main():
    try:
        state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
        if not state.is_absolute():
            raise UpdateError("User state directory must be absolute")
        if onboarding(Layout(), state / "convertibled/onboarding.json", os.getuid(), os.environ):
            subprocess.Popen(["/usr/bin/convertibled-settings"], start_new_session=True)
        return 0
    except (UpdateError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print("convertibled first-login setup failed; open Settings or run finish-user.sh: " + str(exc)[:256], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
