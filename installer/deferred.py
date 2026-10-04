"""Owned first-install scheduler; callers hold the installation lock."""
import os
import tempfile
from .platform import command, graphical_sessions
from .storage import atomic, read, sync_directory
from .status import publish
from .transaction import Transaction
from updater.manager import Manager
from updater.model import UpdateError, version

NAMES = ("convertibled-install.service", "convertibled-install.timer")


def units(candidate):
    version(candidate)
    return {
        NAMES[0]: "[Unit]\nDescription=Finish verified convertibled installation after logout\nAfter=systemd-logind.service\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 -I /opt/convertibled/versions/" + candidate + "/installer/bootstrap.py --finish-install\nTimeoutStartSec=5min\nUMask=0077\n",
        NAMES[1]: "[Unit]\nDescription=Wait for safe convertibled installation\n[Timer]\nOnBootSec=20s\nOnUnitActiveSec=20s\nAccuracySec=2s\nUnit=convertibled-install.service\n[Install]\nWantedBy=timers.target\n",
    }


def path_for(layout, name):
    return layout.root / "etc/systemd/system" / name


def check_owned(layout, record):
    expected = units(record["version"])
    for name, content in expected.items():
        target = path_for(layout, name)
        if target.is_symlink() or (target.exists() and (not target.is_file() or target.read_text() != content)):
            raise UpdateError("User-modified bootstrap unit retained: " + name)
    return expected


def write_unit(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".convertibled-")
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def schedule(layout, candidate, run=command):
    version(candidate)
    record = read(layout.state / "bootstrap-install.json")
    if record:
        if record.get("version") != candidate:
            raise UpdateError("Cancel the pending installation before selecting another candidate")
        check_owned(layout, record)
    else:
        for name in NAMES:
            target = path_for(layout, name)
            if target.exists() or target.is_symlink():
                raise UpdateError("Unowned bootstrap unit retained: " + name)
    if not (layout.versions / candidate / "installer/bootstrap.py").is_file():
        raise UpdateError("Verified candidate lacks the installation scheduler")
    # Persist ownership intent before writing any host integration.
    journal = read(layout.state / "transaction.json", {})
    record = {"schema": 1, "version": candidate, "retry_rolled_back": journal.get("phase") == "rolled_back" and journal.get("candidate") == candidate}
    atomic(layout.state / "bootstrap-install.json", record)
    for name, content in units(candidate).items():
        write_unit(path_for(layout, name), content)
    run(["systemctl", "daemon-reload"])
    run(["systemctl", "enable", "--now", NAMES[1]])
    publish(layout)


def remove(layout, run=command):
    record = read(layout.state / "bootstrap-install.json")
    if not record:
        return
    check_owned(layout, record)
    if path_for(layout, NAMES[1]).exists():
        run(["systemctl", "disable", "--now", NAMES[1]])
    for name in NAMES:
        path_for(layout, name).unlink(missing_ok=True)
    sync_directory(path_for(layout, NAMES[0]).parent)
    run(["systemctl", "daemon-reload"])
    (layout.state / "bootstrap-install.json").unlink()
    sync_directory(layout.state)


def finish(layout, run=command, sessions=graphical_sessions, manager_type=Manager, transaction_type=Transaction):
    record = read(layout.state / "bootstrap-install.json")
    if not record:
        return
    transaction = transaction_type(layout)
    activating = False
    try:
        check_owned(layout, record)
        if (layout.state / "admission.pending").exists():
            transaction.recover()
        if layout.active() == record["version"]:
            remove(layout, run)
            publish(layout)
            return
        if sessions():
            publish(layout)
            return
        transaction.recover()
        journal = read(layout.state / "transaction.json", {})
        if journal.get("candidate") == record["version"] and journal.get("phase") == "rolled_back" and not record.get("retry_rolled_back", False):
            raise UpdateError("Installation recovered to the previous version; inspect Updates before retrying")
        candidate = manager_type(layout).activation_ready()
        if candidate != record["version"]:
            raise UpdateError("Prepared candidate changed; rerun the authenticated installer")
        # Consume explicit retry before mutation, so a second crash/rollback does
        # not authorize another automatic retry of a failing candidate.
        record["retry_rolled_back"] = False
        atomic(layout.state / "bootstrap-install.json", record)
        activating = True
        transaction.activate(candidate)
        remove(layout, run)
        publish(layout)
    except (UpdateError, OSError, ValueError) as exc:
        if isinstance(exc, UpdateError) and str(exc) in ("Waiting for graphical logout; locking does not count", "Waiting for GNOME session admission lock"):
            if activating:
                # Admission/login races are safe deferrals, not bad candidates.
                # Recovery of their preselection journal may mark rolled_back.
                record["retry_rolled_back"] = True
                atomic(layout.state / "bootstrap-install.json", record)
            publish(layout)
            return
        publish(layout, exc)
        # Preserve owned units for explicit retry/removal; do not loop failures.
        timer = path_for(layout, NAMES[1])
        if timer.is_file() and not timer.is_symlink() and timer.read_text() == units(record["version"])[NAMES[1]]:
            run(["systemctl", "disable", "--now", NAMES[1]])
        raise
