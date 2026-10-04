"""Recoverable activation. Callers hold Layout.lock before every mutation."""
from .storage import atomic, read
from .configuration import backup, restore
from .integration import install, remove
from .platform import command, graphical_sessions
from updater.model import UpdateError, version
from .admission_control import admitted, reload_users, pending, waiting_at_gate


class Transaction:
    def __init__(self, layout, sessions=graphical_sessions, run=command):
        self.layout, self.sessions, self.run = layout, sessions, run
        self.journal = layout.state / "transaction.json"

    def record(self, value, phase):
        value["phase"] = phase
        atomic(self.journal, value)

    def require_logout(self):
        sessions = self.sessions()
        if getattr(self, "_admission_recovery", False) and (self.layout.state / "admission.pending").exists():
            sessions = [session for session in sessions if not waiting_at_gate(self.layout, session, self.run)]
        if sessions:
            raise UpdateError("Waiting for graphical logout; locking does not count")

    @admitted
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
        if previous is None:
            onboarding = read(self.layout.state / "onboarding.json", {})
            if type(onboarding.get("pending_uid")) is int:
                value["expected_uid"] = onboarding["pending_uid"]
        self.record(value, "backup")
        backup(self.layout)
        self.record(value, "prepared")
        self.require_logout()
        try:
            from .identity import ensure
            ensure(self.run)
            install(self.layout, admission_only=True, candidate=candidate)
            reload_users(self.run)
            self.run([str(self.layout.versions / candidate / "bin/convertibled"), "--check"])
            # Preflight may be slow. Recheck immediately before quiescing.
            self.require_logout()
            pending(self.layout, True)
            self.record(value, "quiescing")
            if previous:
                self.run(["systemctl", "stop", "convertibled.service"])
            self.require_logout()
            self.record(value, "switching")
            (self.layout.state / "health/shell-health.json").unlink(missing_ok=True)
            if "expected_uid" in value:
                (self.layout.state / f"health/shell-health-{value['expected_uid']}.json").unlink(missing_ok=True)
            self.layout.select(candidate)
            self.record(value, "selected")
            install(self.layout)
            self.run(["systemctl", "daemon-reload"])
            reload_users(self.run)
            self.run(["systemctl", "enable", "--now", "convertibled.service", "convertibled-update.timer"])
            self.run(["systemctl", "is-active", "--quiet", "convertibled.service"])
            self.record(value, "awaiting_shell")
            pending(self.layout, False)
            return value
        except Exception:
            self.rollback(value)
            raise

    @admitted
    def rollback(self, value=None):
        value = value or read(self.journal, {})
        previous = value.get("previous")
        if value.get("phase") == "quiescing" and self.layout.active() == previous:
            # Selection/config/integration are unchanged. Resuming the previous
            # observer is safe even if login arrived while systemctl stopped it.
            if previous:
                self.run(["systemctl", "start", "convertibled.service"])
                self.run(["systemctl", "is-active", "--quiet", "convertibled.service"])
            self.record(value, "rolled_back")
            pending(self.layout, False)
            return value
        self.require_logout()
        if value.get("phase") in ("backup", "prepared"):
            self.record(value, "rolled_back")
            pending(self.layout, False)
            return value
        if not value.get("candidate") or value.get("phase") in (None, "rolled_back", "removed"):
            raise UpdateError("No recoverable previous transaction")
        pending(self.layout, True)
        self.record(value, "rolling_back")
        if (self.layout.root / "usr/lib/systemd/system/convertibled.service").exists():
            self.run(["systemctl", "stop", "convertibled.service"])
        if previous:
            version(previous)
            self.layout.select(previous)
            restore(self.layout)
            install(self.layout)
            self.run(["systemctl", "daemon-reload"])
            reload_users(self.run)
            self.run(["systemctl", "start", "convertibled.service"])
            self.run(["systemctl", "is-active", "--quiet", "convertibled.service"])
        else:
            remove(self.layout, preserve_admission=True)
            self.layout.current.unlink(missing_ok=True)
            self.run(["systemctl", "daemon-reload"])
            reload_users(self.run)
        self.record(value, "rolled_back")
        pending(self.layout, False)
        if not previous:
            remove(self.layout)
            reload_users(self.run)
        return value

    @admitted
    def recover(self):
        value = read(self.journal, {})
        phase = value.get("phase")
        if phase == "removing":
            self.require_logout()
            from .uninstall import _uninstall
            _uninstall(self.layout, self.run, lambda: self.require_logout() or [])
            return read(self.journal, {})
        if phase in (None, "complete", "rolled_back", "removed"):
            pending(self.layout, False)
            return value
        if phase == "quiescing" and self.layout.active() == value.get("previous"):
            return self.rollback(value)
        self.require_logout()
        if phase == "backup":
            self.record(value, "rolled_back")
            pending(self.layout, False)
            return value
        if phase == "awaiting_shell":
            receipt = read(self.layout.state / "health/shell-health.json", {})
            if "expected_uid" in value:
                receipt = read(self.layout.state / f"health/shell-health-{value['expected_uid']}.json", {})
            if "expected_uid" in value and receipt.get("uid") != value["expected_uid"]:
                receipt = {}
            if receipt.get("version") == value["candidate"] and receipt.get("healthy") is True:
                self.record(value, "complete")
                pending(self.layout, False)
                return value
            if not value.get("first_session_seen") and not (receipt.get("version") == value["candidate"] and receipt.get("healthy") is False):
                pending(self.layout, False)
                return value
        return self.rollback(value)

    def observe_login(self):
        value = read(self.journal, {})
        sessions = self.sessions()
        if "expected_uid" in value:
            sessions = [item for item in sessions if str(item.get("user")) == str(value["expected_uid"])]
        if value.get("phase") == "awaiting_shell" and sessions:
            value["first_session_seen"] = True
            self.record(value, "awaiting_shell")
