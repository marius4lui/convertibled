"""POSIX disposable lifecycle with real file mutations and simulated services."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from .integration import LINKS
from .storage import Layout, atomic, read
from .transaction import Transaction
from .uninstall import uninstall
from updater.archive import extract
from updater.model import UpdateError
from scripts.release.bundle import build


@unittest.skipUnless(os.name == "posix", "Linux/POSIX lifecycle test")
class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.layout = Layout(self.temporary.name)
        self.layout.initialize()
        self.calls = []
        self.transaction = Transaction(self.layout, sessions=lambda: [], run=lambda args: self.calls.append(args))

    def tearDown(self):
        self.temporary.cleanup()

    def candidate(self, version):
        files = {"bin/" + name: (b"\x7fELFfixture", True) for name in ("convertibled", "convertibled-session", "convertiblectl", "convertibled-settings")}
        for source in LINKS.values():
            if source.startswith("share/gnome-shell/extensions/"):
                source += "/extension.js"
            files.setdefault(source, (b"fixture", source.endswith(".py")))
        archive = Path(self.temporary.name) / (version + ".tar.gz")
        build(files, version, archive)
        path = self.layout.versions / version
        extract(archive, path, version)
        atomic(path / "release.json", {"version": version})

    @patch("installer.identity.ensure")
    def test_clean_install_health_and_uninstall(self, identity):
        self.candidate("0.1.0")
        self.assertEqual(self.transaction.activate("0.1.0")["phase"], "awaiting_shell")
        self.assertEqual(self.layout.active(), "0.1.0")
        atomic(self.layout.state / "health/shell-health.json", {"version": "0.1.0", "healthy": True})
        self.assertEqual(self.transaction.recover()["phase"], "complete")
        uninstall(self.layout, run=lambda args: self.calls.append(args), sessions=lambda: [])
        self.assertIsNone(self.layout.active())
        self.assertEqual(list(self.layout.versions.iterdir()), [])
        self.assertTrue(self.layout.config.exists())

    @patch("installer.identity.ensure")
    def test_failed_new_service_restores_previous(self, identity):
        self.candidate("0.1.0")
        self.transaction.activate("0.1.0")
        atomic(self.layout.state / "health/shell-health.json", {"version": "0.1.0", "healthy": True})
        self.transaction.recover()
        self.candidate("0.2.0")
        count = [0]
        def run(args):
            if args[:2] == ["systemctl", "is-active"]:
                count[0] += 1
                if count[0] == 1:
                    raise UpdateError("candidate health failed")
            self.calls.append(args)
        self.transaction.run = run
        with self.assertRaises(UpdateError):
            self.transaction.activate("0.2.0")
        self.assertEqual(self.layout.active(), "0.1.0")
        self.assertEqual(read(self.transaction.journal)["phase"], "rolled_back")

    @patch("installer.identity.ensure")
    def test_modified_user_file_blocks_uninstall_before_services(self, identity):
        self.candidate("0.1.0")
        self.transaction.activate("0.1.0")
        (self.layout.versions / "0.1.0/user-content").write_text("retain")
        self.calls.clear()
        with self.assertRaises(UpdateError):
            uninstall(self.layout, run=lambda args: self.calls.append(args), sessions=lambda: [])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.layout.active(), "0.1.0")
