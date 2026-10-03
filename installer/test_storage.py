import tempfile
import unittest
from pathlib import Path
from .storage import Layout, atomic, read
from updater.model import UpdateError


class StorageTests(unittest.TestCase):
    def test_atomic_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "state.json"
            atomic(path, {"phase": "verified"})
            self.assertEqual(read(path), {"phase": "verified"})
            self.assertEqual(len(list(Path(root).iterdir())), 1)

    @unittest.skipIf(__import__('os').name != 'posix', "Symlinks require POSIX test host")
    def test_active_cannot_escape(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            layout.current.symlink_to(Path(root))
            with self.assertRaises(UpdateError):
                layout.active()
