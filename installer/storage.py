"""Crash-durable root-owned state, serial operations, immutable paths."""
import contextlib
import json
import os
import tempfile
from pathlib import Path
from updater.model import UpdateError, decode


def sync_directory(path):
    if os.name == "posix":
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise UpdateError("Refusing symlink state")
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".write-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(json.dumps(value, sort_keys=True).encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read(path, default=None):
    path = Path(path)
    if path.is_symlink():
        raise UpdateError("Refusing symlink state")
    return decode(path.read_bytes()) if path.exists() else default


class Layout:
    def __init__(self, root=Path("/")):
        self.root = Path(root)
        self.base = self.root / "opt/convertibled"
        self.versions = self.base / "versions"
        self.current = self.base / "current"
        self.config = self.root / "etc/convertibled"
        self.state = self.root / "var/lib/convertibled"

    def initialize(self):
        for path in (self.base, self.versions, self.config, self.state):
            if path.is_symlink():
                raise UpdateError("Installation directory is a symlink")
            path.mkdir(parents=True, exist_ok=True, mode=0o755)
            # The unprivileged daemon/session must traverse config even when
            # config.toml is absent. Individual trust/state files remain private.
            path.chmod(0o755)

    @contextlib.contextmanager
    def lock(self):
        import fcntl
        self.initialize()
        with (self.state / "lock").open("a+b") as stream:
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise UpdateError("Another installation transaction is running") from exc
            yield

    def active(self):
        if not self.current.exists() and not self.current.is_symlink():
            return None
        if not self.current.is_symlink():
            raise UpdateError("Active reference is not a managed symlink")
        target = self.current.resolve()
        if target.parent != self.versions.resolve() or not target.is_dir():
            raise UpdateError("Active reference escapes installation")
        return target.name

    def select(self, version):
        from updater.model import version as validate
        validate(version)
        if not (self.versions / version).is_dir():
            raise UpdateError("Version is not installed")
        temporary = self.base / ".current-next"
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(Path("versions") / version, target_is_directory=True)
        os.replace(temporary, self.current)
        sync_directory(self.base)
