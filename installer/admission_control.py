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
            run(["systemctl", "--user", f"--machine={uid}@.host", "daemon-reload"])


def provision(layout, source=None):
    source = source or layout.current
    for relative, name in STABLE.items():
        _provision_file(layout, layout.state / name, (source / relative).read_bytes())


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
            return method(self, *args, **kwargs)
    return wrapped
