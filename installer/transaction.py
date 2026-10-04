"""Recoverable activation. Callers hold Layout.lock before every mutation."""
from .storage import atomic, read
from .configuration import backup, restore
from .integration import install, remove
from .platform import command, graphical_sessions
from updater.model import UpdateError, version


class Transaction:
    def __init__(self, layout, sessions=graphical_sessions, run=command):
        self.layout, self.sessions, self.run = layout, sessions, run
        self.journal = layout.state / "transaction.json"

    def record(self, value, phase):
        value["phase"] = phase
        atomic(self.journal, value)

    def require_logout(self):
        if self.sessions():
            raise UpdateError("Waiting for graphical logout; locking does not count")

    def activate(self, candidate):
        version(candidate)
        self.require_logout()
        previous = self.layout.active()
        if previous == candidate:
            return {"phase": "complete", "version": candidate}
        if read(self.journal, {}).get("phase") not in (None, "complete", "rolled_back"):
            raise UpdateError("Recover the pending transaction first")
        if not (self.layout.versions / candidate / "manifest.json").is_file():
            raise UpdateError("Candidate is not verified")
        value = {"schema": 1, "candidate": candidate, "previous": previous, "phase": "backup"}
        self.record(value, "backup")
        backup(self.layout)
        self.record(value, "prepared")
        self.require_logout()
        try:
            from .identity import ensure
            ensure(self.run)
            self.run([str(self.layout.versions / candidate / "bin/convertibled"), "--check"])
            if previous:
                self.run(["systemctl", "stop", "convertibled.service"])
            self.record(value, "switching")
            self.layout.select(candidate)
            self.record(value, "selected")
            install(self.layout)
            self.run(["systemctl", "daemon-reload"])
            self.run(["systemctl", "enable", "--now", "convertibled.service", "convertibled-update.timer"])
            self.run(["systemctl", "is-active", "--quiet", "convertibled.service"])
            self.record(value, "awaiting_shell")
            return value
        except Exception:
            self.rollback(value)
            raise

    def rollback(self, value=None):
        self.require_logout()
        value = value or read(self.journal, {})
        previous = value.get("previous")
        if value.get("phase") in ("backup", "prepared"):
            self.record(value, "rolled_back")
            return value
        if not value.get("candidate") or value.get("phase") in (None, "rolled_back", "removed"):
            raise UpdateError("No recoverable previous transaction")
        self.record(value, "rolling_back")
        if (self.layout.root / "usr/lib/systemd/system/convertibled.service").exists():
            self.run(["systemctl", "stop", "convertibled.service"])
        if previous:
            version(previous)
            self.layout.select(previous)
            restore(self.layout)
            install(self.layout)
            self.run(["systemctl", "daemon-reload"])
            self.run(["systemctl", "start", "convertibled.service"])
            self.run(["systemctl", "is-active", "--quiet", "convertibled.service"])
        else:
            remove(self.layout)
            self.layout.current.unlink(missing_ok=True)
            self.run(["systemctl", "daemon-reload"])
        self.record(value, "rolled_back")
        return value

    def recover(self):
        value = read(self.journal, {})
        phase = value.get("phase")
        if phase in (None, "complete", "rolled_back"):
            return value
        self.require_logout()
        if phase == "backup":
            self.record(value, "rolled_back")
            return value
        if phase == "awaiting_shell":
            receipt = read(self.layout.state / "health/shell-health.json", {})
            if receipt.get("version") == value["candidate"] and receipt.get("healthy") is True:
                self.record(value, "complete")
                return value
            if not value.get("first_session_seen"):
                return value
        return self.rollback(value)

    def observe_login(self):
        value = read(self.journal, {})
        if value.get("phase") == "awaiting_shell" and self.sessions():
            value["first_session_seen"] = True
            self.record(value, "awaiting_shell")
