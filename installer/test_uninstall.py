import tempfile
import unittest
from pathlib import Path
from .uninstall import owned_version, uninstall
from .storage import Layout
from updater.model import UpdateError


class UninstallTests(unittest.TestCase):
    def test_session_blocks_before_service_stop(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            calls = []
            with self.assertRaises(UpdateError):
                uninstall(layout, run=calls.append, sessions=lambda: [{"type": "wayland"}])
            self.assertEqual(calls, [])

    def test_unowned_directory_retained(self):
        with tempfile.TemporaryDirectory() as root:
            candidate = Path(root) / "0.1.0"
            candidate.mkdir()
            (candidate / "user.txt").write_text("retain")
            with self.assertRaises(UpdateError):
                owned_version(candidate)
            self.assertTrue((candidate / "user.txt").exists())
