"""Fail-closed Fedora/GNOME preflight and logind session inspection."""
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from updater.model import UpdateError


class SessionGone(UpdateError):
    """A listed logind session vanished before its properties were read."""


def command(args, timeout=15):
    session_query = len(args) >= 3 and args[:2] == ["loginctl", "show-session"]
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False,
                                env={**os.environ, "LC_ALL": "C"} if session_query else None)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError("Required platform command unavailable") from exc
    if result.returncode:
        if session_query and result.stderr.strip() == f"Failed to get path for session '{args[2]}': No session '{args[2]}' known":
            raise SessionGone("Logind session vanished during observation")
        raise UpdateError("Platform operation failed: " + args[0])
    return result.stdout.strip()


def _session_snapshot():
    # Locked and inactive graphical sessions still load the installed extension.
    sessions = json.loads(command(["loginctl", "list-sessions", "--json=short", "--no-pager"]))
    if not isinstance(sessions, list) or len(sessions) > 512 or any(not isinstance(entry, dict) for entry in sessions):
        raise UpdateError("Unexpected or oversized logind session inventory")
    affected = []
    for entry in sessions:
        identifier = str(entry.get("session", ""))
        if not identifier.isalnum() or len(identifier) > 32:
            raise UpdateError("Unexpected logind session identifier")
        properties = command(["loginctl", "show-session", identifier, "-p", "Type", "-p", "Class", "-p", "User", "--no-pager"])
        values = dict(line.split("=", 1) for line in properties.splitlines() if "=" in line)
        if values.get("Type") in ("wayland", "x11") and values.get("Class") not in ("greeter", "manager"):
            affected.append({"session": identifier, "user": values.get("User"), "type": values["Type"]})
    return affected


def graphical_sessions():
    for _ in range(3):
        try:
            return _session_snapshot()
        except SessionGone:
            # Restart the complete observation: a new login can appear while
            # the old session disappears. Never infer logout from one failure.
            continue
    return [{"session": "unknown", "user": None, "type": "unknown"}]


def preflight(layout, required_space):
    os_release = platform.freedesktop_os_release()
    if platform.system() != "Linux" or platform.machine() != "x86_64" or os_release.get("ID") != "fedora" or os_release.get("VERSION_ID") != "44":
        raise UpdateError("Requires Fedora 44 x86_64")
    if not command(["gnome-shell", "--version"]).startswith("GNOME Shell 50"):
        raise UpdateError("Requires GNOME Shell 50")
    for tool in ("python3", "openssl", "systemctl", "loginctl", "pkexec", "glib-compile-schemas", "/usr/bin/runuser", "/usr/bin/env", "/usr/bin/systemctl"):
        if shutil.which(tool) is None:
            raise UpdateError("Missing prerequisite: " + tool)
    if shutil.disk_usage(layout.versions).free < required_space + 128 * 1024 * 1024:
        raise UpdateError("Insufficient disk space (including recovery reserve)")
    directories = [layout.root / "usr/share/gnome-shell/extensions"]
    caller = os.environ.get("PKEXEC_UID") or os.environ.get("SUDO_UID", "")
    if caller.isdecimal():
        import pwd
        try:
            home = Path(pwd.getpwuid(int(caller)).pw_dir)
        except KeyError as exc:
            raise UpdateError("Installing user does not exist") from exc
        directories.append(home / ".local/share/gnome-shell/extensions")
    conflicts(directories)


def conflicts(extension_directories, own_uuid="convertibled@convertibled.org"):
    # Conflicts are explained; nothing is disabled automatically.
    known = {"dash-to-dock@micxgx.gmail.com", "dash-to-panel@jderose9.github.com", "pop-shell@system76.com", "paperwm@paperwm.github.com"}
    found = set()
    for directory in extension_directories:
        path = Path(directory)
        if path.exists():
            found.update(child.name for child in path.iterdir() if child.name in known and child.name != own_uuid)
    if found:
        raise UpdateError("Review conflicting installed GNOME extensions: " + ", ".join(sorted(found)))
