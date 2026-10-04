"""Explicit, fixed installation/maintenance requests serviced after logout."""
from .platform import command, graphical_sessions
from .storage import atomic, read, sync_directory
from .transaction import Transaction
from updater.manager import Manager
from updater.model import UpdateError, version

ACTIONS = ("uninstall", "rollback", "recover", "activate")
WAITING = ("Waiting for graphical logout; locking does not count", "Waiting for GNOME session admission lock", "Log out graphical sessions before removal", "Graphical login appeared during removal preflight")


def requested(layout):
    value = read(layout.state / "pending-action.json")
    if value is None:
        return None
    if not isinstance(value, dict) or value.get("schema") != 1 or value.get("action") not in ACTIONS or value.get("state") not in ("waiting", "running", "failed"):
        raise UpdateError("Invalid pending system action")
    version(value.get("version"))
    if value["action"] == "activate":
        version(value.get("candidate"))
        if value.get("channel") not in ("stable", "preview"):
            raise UpdateError("Invalid pending activation channel")
    return value


def request(layout, action, run=command, manager_type=Manager):
    if action not in ACTIONS:
        raise UpdateError("Unknown system action")
    active = layout.active()
    if active is None:
        raise UpdateError("Use the trusted offline recovery helper when no version is active")
    previous = requested(layout)
    if previous and previous["action"] != action:
        raise UpdateError("Cancel the pending action before requesting another")
    journal = read(layout.state / "transaction.json", {})
    if previous and previous["state"] in ("running", "failed") and journal.get("phase") in ("removing", "rolling_back", "quiescing", "switching", "selected", "backup", "prepared"):
        raise UpdateError("Recover the interrupted transaction before requesting another action")
    value = {"schema": 1, "action": action, "version": active, "state": "waiting"}
    if action == "activate":
        candidate = manager_type(layout).activation_ready()
        if candidate == active:
            raise UpdateError("Prepared version is already installed")
        value.update(candidate=candidate, channel=read(layout.state / "prepared.json", {}).get("channel"))
    atomic(layout.state / "pending-action.json", value)
    # Managed boot links already exist. Start the timer without systemctl enable,
    # which canonicalizes our versioned source into a stale /etc unit alias.
    try:
        run(["systemctl", "start", "convertibled-update.timer"])
    except (UpdateError, OSError, ValueError) as exc:
        value.update(state="failed", error=str(exc)[:512])
        atomic(layout.state / "pending-action.json", value)
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


def activation_finished(layout, value, journal):
    if value["action"] != "activate" or value["state"] != "running":
        return False
    if journal.get("candidate") != value["candidate"] or journal.get("previous") != value["version"]:
        return False
    if journal.get("phase") in ("awaiting_shell", "complete") and layout.active() == value["candidate"]:
        clear(layout)
        return True
    if journal.get("phase") == "rolled_back":
        raise UpdateError("Requested activation was rolled back; review before retrying")
    return False


def process(layout, sessions=graphical_sessions, transaction_type=Transaction, uninstall_fn=None, manager_type=Manager):
    value = requested(layout)
    if value is None:
        return False
    transaction = transaction_type(layout)
    if value["state"] == "failed":
        # A failed requested action must not suppress the existing crash-recovery
        # path or leave the admission gate closed. Never retry the action itself.
        journal = read(layout.state / "transaction.json", {})
        if (layout.state / "admission.pending").exists() or journal.get("phase") == "awaiting_shell":
            try:
                if not (layout.state / "admission.pending").exists() and sessions():
                    transaction.observe_login()
                else:
                    transaction.recover()
            except (UpdateError, OSError, ValueError) as exc:
                if not isinstance(exc, UpdateError) or str(exc) not in WAITING:
                    value["error"] = "Interrupted transaction needs recovery: " + str(exc)[:450]
                    atomic(layout.state / "pending-action.json", value)
        return True
    try:
        journal = read(layout.state / "transaction.json", {})
        if activation_finished(layout, value, journal):
            return True
        # A successful rollback may have been interrupted before clearing the
        # request. A second rollback must not run against the new active version.
        if value["state"] == "running" and value["action"] == "rollback" and journal.get("phase") == "rolled_back" and journal.get("candidate") == value["version"] and layout.active() == journal.get("previous"):
            clear(layout)
            return True
        own_activation = value["action"] == "activate" and value["state"] == "running" and journal.get("candidate") == value["candidate"] and journal.get("previous") == value["version"]
        if layout.active() != value["version"] and not (own_activation and layout.active() == value["candidate"]):
            raise UpdateError("Installed version changed; cancel and review the system action again")
        if (layout.state / "admission.pending").exists() or (value["action"] == "activate" and value["state"] == "running"):
            transaction.recover()
            journal = read(layout.state / "transaction.json", {})
            if activation_finished(layout, value, journal):
                return True
            if value["action"] == "recover" and journal.get("phase") in ("complete", "rolled_back", "removed"):
                clear(layout)
                return True
            if requested(layout) is None:
                return True
        if layout.active() != value["version"]:
            raise UpdateError("Installed version changed; cancel and review the system action again")
        if sessions():
            if journal.get("phase") == "awaiting_shell":
                transaction.observe_login()
            return True
        if value["action"] == "activate":
            if journal.get("phase") == "awaiting_shell":
                transaction.recover()
                if layout.active() != value["version"]:
                    raise UpdateError("Installed version recovered; cancel and review activation again")
            prepared = read(layout.state / "prepared.json", {})
            if prepared.get("version") != value["candidate"] or prepared.get("channel") != value["channel"]:
                raise UpdateError("Prepared version or channel changed; cancel and review activation again")
            if manager_type(layout).activation_ready() != value["candidate"]:
                raise UpdateError("Authenticated candidate changed; review activation again")
        value["state"] = "running"
        atomic(layout.state / "pending-action.json", value)
        if value["action"] == "uninstall":
            if uninstall_fn is None:
                from .uninstall import uninstall as uninstall_fn
            uninstall_fn(layout)
        elif value["action"] == "rollback":
            transaction.rollback()
        elif value["action"] == "activate":
            transaction.activate(value["candidate"])
        else:
            transaction.recover()
        clear(layout)
        return True
    except (UpdateError, OSError, ValueError) as exc:
        if isinstance(exc, UpdateError) and str(exc) in WAITING:
            # Preserve the transaction identity across a login/recovery wait.
            journal = read(layout.state / "transaction.json", {})
            interrupted = value["action"] == "activate" and value["state"] == "running" and journal.get("candidate") == value["candidate"] and journal.get("previous") == value["version"] and journal.get("phase") not in (None, "complete", "rolled_back")
            value["state"] = "running" if interrupted else "waiting"
        else:
            value["state"] = "failed"
            value["error"] = str(exc)[:512]
        atomic(layout.state / "pending-action.json", value)
        return True
