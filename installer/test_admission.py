import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from .admission_control import exclusive, reload_users, provision, STABLE
from .storage import Layout
from updater.model import UpdateError


def reader(path, notify, started):
    from . import admission
    admission.checked_descriptor = lambda ignored: os.open(path, os.O_RDONLY)
    os.environ["NOTIFY_SOCKET"] = notify
    started.set()
    admission.guard()


@unittest.skipUnless(os.name == "posix", "POSIX flock/notify admission")
class AdmissionTests(unittest.TestCase):
    def test_login_ready_waits_for_update_and_blocks_next_update(self):
        import multiprocessing
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            address = str(Path(root) / "notify")
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as notify:
                notify.bind(address)
                notify.settimeout(0.2)
                with exclusive(layout):
                    inode = (layout.state / "admission.lock").stat().st_ino
                    context = multiprocessing.get_context("spawn")
                    started = context.Event()
                    child = context.Process(target=reader, args=(str(layout.state / "admission.lock"), address, started))
                    child.start()
                    try:
                        self.assertTrue(started.wait(5), "Admission process did not start")
                        with self.assertRaises(socket.timeout):
                            notify.recv(100)
                    except BaseException:
                        child.terminate()
                        child.join(5)
                        raise
                try:
                    notify.settimeout(5)
                    self.assertEqual(notify.recv(100), b"READY=1")
                    with self.assertRaises(UpdateError):
                        with exclusive(layout):
                            self.fail("Update admitted during shared login lease")
                finally:
                    child.terminate()
                    child.join(5)
                with exclusive(layout):
                    self.assertEqual((layout.state / "admission.lock").stat().st_ino, inode)

    def test_symlink_lock_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            (layout.state / "admission.lock").symlink_to(Path(root) / "unrelated")
            with self.assertRaises(OSError):
                with exclusive(layout):
                    self.fail("Symlink lock admitted")

    def test_nested_recovery_keeps_exclusive_lease(self):
        import fcntl
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            with exclusive(layout), exclusive(layout):
                with (layout.state / "admission.lock").open("rb") as reader_fd:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(reader_fd.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)

    def test_stable_helper_not_replaced_and_changes_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            source = Path(root) / "source"
            for relative in STABLE:
                path = source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"trusted fixture")
            provision(layout, source)
            inode = (layout.state / "admission.py").stat().st_ino
            provision(layout, source)
            self.assertEqual((layout.state / "admission.py").stat().st_ino, inode)
            (source / "installer/admission.py").write_bytes(b"changed")
            with self.assertRaises(UpdateError):
                provision(layout, source)


class UserReloadTests(unittest.TestCase):
    def test_only_existing_validated_managers_reload(self):
        calls = []
        def run(args):
            calls.append(args)
            if args[0] == "loginctl":
                return '[{"uid":1000},{"uid":1001},{"uid":1000}]'
            return "active" if "user@1000.service" in args else "inactive"
        reload_users(run)
        self.assertIn(["systemctl", "--user", "--machine=1000@.host", "daemon-reload"], calls)
        self.assertEqual(sum("daemon-reload" in call for call in calls), 1)

    def test_argument_injection_rejected(self):
        with self.assertRaises(UpdateError):
            reload_users(lambda args: '[{"uid":"1000 --host=evil"}]')
