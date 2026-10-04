"""Explicit, fixed recovery/removal requests serviced after graphical logout."""
from .platform import command, graphical_sessions
from .storage import atomic, read, sync_directory
from .transaction import Transaction
from updater.model import UpdateError, version

ACTIONS = ("uninstall", "rollback", "recover")
WAITING = ("Waiting for graphical logout; locking does not count", "Waiting for GNOME session admission lock", "Log out graphical sessions before removal", "Graphical login appeared during removal preflight")


def requested(layout):
    value = read(layout.state / "pending-action.json")
    if value is None:
        return None
    if not isinstance(value, dict) or value.get("schema") != 1 or value.get("action") not in ACTIONS or value.get("state") not in ("waiting", "running", "failed"):
        raise UpdateError("Invalid pending system action")
    version(value.get("version"))
    return value


def request(layout, action, run=command):
    if action not in ACTIONS:
        raise UpdateError("Unknown system action")
    active = layout.active()
    if active is None:
        raise UpdateError("Use the trusted offline recovery helper when no version is active")
    previous = requested(layout)
    if previous and previous["action"] != action:
        raise UpdateError("Cancel the pending action before requesting another")
    atomic(layout.state / "pending-action.json", {"schema": 1, "action": action, "version": active, "state": "waiting"})
    # Managed boot links already exist. Start the timer without systemctl enable,
    # which canonicalizes our versioned source into a stale /etc unit alias.
    try:
        run(["systemctl", "start", "convertibled-update.timer"])
    except (UpdateError, OSError, ValueError) as exc:
        atomic(layout.state / "pending-action.json", {"schema": 1, "action": action, "version": active, "state": "failed", "error": str(exc)[:512]})
        raise


def clear(layout):
    (layout.state / "pending-action.json").unlink(missing_ok=True)
    sync_directory(layout.state)


def cancel(layout):
    value = requested(layout)
    if not value:
        return
    journal = read(layout.state / "transaction.json", {})
    if value["state"] in ("running", "failed") and journal.get("phase") in ("removing", "rolling_back", "quiescing", "switching", "selected", "backup", "prepared"):
        raise UpdateError("Recover the interrupted transaction before cancelling its request")
    clear(layout)


def process(layout, sessions=graphical_sessions, transaction_type=Transaction, uninstall_fn=None):
    value = requested(layout)
    if value is None:
        return False
    transaction = transaction_type(layout)
    if value["state"] == "failed":
        # A failed requested action must not suppress the existing crash-recovery
        # path or leave the admission gate closed. Never retry the action itself.
        if (layout.state / "admission.pending").exists():
            try:
                transaction.recover()
            except (UpdateError, OSError, ValueError) as exc:
                if not isinstance(exc, UpdateError) or str(exc) not in WAITING:
                    value["error"] = "Interrupted transaction needs recovery: " + str(exc)[:450]
                    atomic(layout.state / "pending-action.json", value)
        return True
    try:
        journal = read(layout.state / "transaction.json", {})
        # A successful rollback may have been interrupted before clearing the
        # request. A second rollback must not run against the new active version.
        if value["state"] == "running" and value["action"] == "rollback" and journal.get("phase") == "rolled_back" and journal.get("candidate") == value["version"] and layout.active() == journal.get("previous"):
            clear(layout)
            return True
        if layout.active() != value["version"]:
            raise UpdateError("Installed version changed; cancel and review the system action again")
        if (layout.state / "admission.pending").exists():
            transaction.recover()
            journal = read(layout.state / "transaction.json", {})
            if value["action"] == "recover" and journal.get("phase") in ("complete", "rolled_back", "removed"):
                clear(layout)
                return True
            if requested(layout) is None:
                return True
        if layout.active() != value["version"]:
            raise UpdateError("Installed version changed; cancel and review the system action again")
        if sessions():
            return True
        value["state"] = "running"
        atomic(layout.state / "pending-action.json", value)
        if value["action"] == "uninstall":
            if uninstall_fn is None:
                from .uninstall import uninstall as uninstall_fn
            uninstall_fn(layout)
        elif value["action"] == "rollback":
            transaction.rollback()
        else:
            transaction.recover()
        clear(layout)
        return True
    except (UpdateError, OSError, ValueError) as exc:
        if isinstance(exc, UpdateError) and str(exc) in WAITING:
            value["state"] = "waiting"
        else:
            value["state"] = "failed"
            value["error"] = str(exc)[:512]
        atomic(layout.state / "pending-action.json", value)
        return True
