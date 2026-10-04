"""Root exclusive admission boundary and immutable standalone guard setup."""
import contextlib
import functools
import os
import stat
import tempfile
import json
from pathlib import Path
from .storage import sync_directory
from .storage import read
from updater.model import UpdateError


STABLE = {
    "installer/admission.py": "admission.py",
    "data/systemd/convertibled-admission.service": "admission.service",
    "data/systemd/org.gnome.Shell@user.service.d/convertibled-admission.conf": "admission.conf",
}


def user_name(uid):
    import pwd
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError as exc:
        raise UpdateError("User-manager account no longer exists") from exc


def user_manager(uid, arguments):
    if type(uid) is not int or not 0 <= uid < 4294967295:
        raise UpdateError("Unexpected user-manager identity")
    name = user_name(uid)
    if not isinstance(name, str) or not name:
        raise UpdateError("Unexpected user-manager account")
    return ["/usr/bin/runuser", "-u", name, "--", "/usr/bin/env", "-i",
            "PATH=/usr/bin:/usr/sbin", f"XDG_RUNTIME_DIR=/run/user/{uid}",
            f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus",
            "/usr/bin/systemctl", "--user", *arguments]


def reload_users(run):
    result = run(["loginctl", "list-users", "--json=short", "--no-pager"])
    if result is None:  # Injectable service fake; command() always returns text.
        return
    users = json.loads(result)
    if not isinstance(users, list) or len(users) > 512:
        raise UpdateError("Unexpected user-manager inventory")
    seen = set()
    for entry in users:
        uid = entry.get("uid") if isinstance(entry, dict) else None
        if type(uid) is not int or not 0 <= uid < 4294967295:
            raise UpdateError("Unexpected user-manager identity")
        if uid in seen:
            continue
        seen.add(uid)
        if run(["systemctl", "show", f"user@{uid}.service", "-p", "ActiveState", "--value"]) == "active":
            try:
                run(user_manager(uid, ["daemon-reload"]))
            except UpdateError:
                # A manager may exit after logind enumeration. Only a confirmed
                # stopped/failed manager may be skipped; active errors stay fatal.
                if run(["systemctl", "show", f"user@{uid}.service", "-p", "ActiveState", "--value"]) not in ("inactive", "failed"):
                    raise


def guard_process(pid, uid):
    try:
        path = Path("/proc") / str(pid)
        if path.stat().st_uid != uid:
            return False
        arguments = (path / "cmdline").read_bytes().split(b"\0")
        return arguments[1:4] == [b"-I", b"/var/lib/convertibled/admission.py", b""]
    except OSError:
        return False


def waiting_at_gate(layout, session, run):
    """Only the supported manager path, never merely absence of a receipt."""
    uid = str(session.get("user", ""))
    if not uid.isascii() or not uid.isdecimal() or not 0 <= int(uid) < 4294967295:
        return False
    def properties(unit):
        text = run(user_manager(int(uid), ["show", unit,
                    "-p", "ActiveState", "-p", "SubState", "-p", "MainPID", "-p", "FragmentPath", "-p", "DropInPaths", "-p", "Job"]))
        return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
    try:
        shell = properties("org.gnome.Shell@user.service")
        guard = properties("convertibled-admission.service")
        shell_path = "/usr/lib/systemd/user/org.gnome.Shell@.service"
        guard_path = "/usr/lib/systemd/user/convertibled-admission.service"
        dropin = "/usr/lib/systemd/user/org.gnome.Shell@user.service.d/convertibled-admission.conf"
        if shell.get("FragmentPath") != shell_path or guard.get("FragmentPath") != guard_path:
            return False
        paths = shell.get("DropInPaths", "").split() + guard.get("DropInPaths", "").split()
        if paths != [dropin]:
            return False
        for name in [shell_path, guard_path] + paths:
            if not name.startswith(("/usr/lib/systemd/user/", "/etc/systemd/user/")):
                return False
            info = (layout.root / name.lstrip("/")).stat()
            if info.st_uid != os.geteuid() or info.st_mode & 0o022:
                return False
        job = shell.get("Job", "").split(" ", 1)[0]
        pid = guard.get("MainPID", "")
        return (shell.get("MainPID") == "0" and shell.get("ActiveState") in ("inactive", "activating")
                and job.isdecimal() and int(job) > 0
                and guard.get("ActiveState") == "activating" and guard.get("SubState") == "start"
                and pid.isdecimal() and 0 < int(pid) < 4294967295 and guard_process(int(pid), int(uid)))
    except (OSError, AttributeError, ValueError, UpdateError):
        return False


def provision(layout, source=None):
    source = source or layout.current
    for relative, name in STABLE.items():
        _provision_file(layout, layout.state / name, (source / relative).read_bytes())


def pending(layout, active):
    path = layout.state / "admission.pending"
    if path.is_symlink():
        raise UpdateError("Unsafe admission recovery marker")
    if active:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o644)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
                raise UpdateError("Unsafe admission recovery marker")
            os.fsync(fd)
        finally:
            os.close(fd)
    else:
        path.unlink(missing_ok=True)
    sync_directory(layout.state)


def _provision_file(layout, helper, content):
    if helper.is_symlink():
        raise UpdateError("Admission helper is not a managed regular file")
    if helper.exists():
        info = helper.stat()
        if info.st_uid != os.geteuid() or info.st_mode & 0o022 or helper.read_bytes() != content:
            raise UpdateError("Stable admission helper changed; explicit migration required")
        return
    fd, temporary = tempfile.mkstemp(dir=layout.state, prefix=".admission-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fchmod(stream.fileno(), 0o644)
            os.fsync(stream.fileno())
        os.link(temporary, helper)
        sync_directory(layout.state)
    finally:
        os.unlink(temporary)


@contextlib.contextmanager
def exclusive(layout):
    import fcntl
    if getattr(layout, "_admission_depth", 0):
        layout._admission_depth += 1
        try:
            yield
        finally:
            layout._admission_depth -= 1
        return
    layout.initialize()
    path = layout.state / "admission.lock"
    fd = os.open(path, os.O_RDONLY | os.O_CREAT | os.O_NOFOLLOW, 0o644)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise UpdateError("Unsafe admission lock")
        os.fchmod(fd, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise UpdateError("Waiting for GNOME session admission lock") from exc
        layout._admission_depth = 1
        try:
            yield
        finally:
            layout._admission_depth = 0
    finally:
        os.close(fd)


def admitted(method):
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        if method.__name__ in ("rollback", "recover"):
            value = args[0] if args else read(self.journal, {})
            if value and value.get("phase") == "quiescing" and self.layout.active() == value.get("previous"):
                return method(self, *args, **kwargs)
        with exclusive(self.layout):
            previous = getattr(self, "_admission_recovery", False)
            self._admission_recovery = method.__name__ in ("recover", "rollback")
            try:
                return method(self, *args, **kwargs)
            finally:
                self._admission_recovery = previous
    return wrapped
