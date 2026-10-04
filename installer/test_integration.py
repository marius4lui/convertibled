import tempfile
import unittest
import os
from unittest.mock import patch
from pathlib import Path
from .integration import install, LINKS, integration_parent
from .storage import Layout
from updater.model import UpdateError


class OwnershipTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX public integration permissions")
    def test_creation_error_restores_private_umask(self):
        with tempfile.TemporaryDirectory() as root:
            previous = os.umask(0o077)
            try:
                with patch.object(Path, "mkdir", side_effect=OSError("read-only mount")):
                    with self.assertRaises(OSError):
                        integration_parent(Layout(root), Path(root) / "usr")
                probe = Path(root) / "private-probe"
                probe.mkdir()
                self.assertEqual(probe.stat().st_mode & 0o777, 0o700)
            finally:
                os.umask(previous)

    @unittest.skipUnless(os.name == "posix", "POSIX public integration permissions")
    def test_public_directories_ignore_private_umask_and_restore_it(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            previous = os.umask(0o077)
            try:
                for destination in LINKS:
                    parent = Path(root, destination).parent
                    integration_parent(layout, parent)
                    current = parent
                    while current != Path(root):
                        self.assertEqual(current.stat().st_mode & 0o777, 0o755)
                        current = current.parent
                probe = Path(root) / "private-probe"
                probe.mkdir()
                self.assertEqual(probe.stat().st_mode & 0o777, 0o700)
            finally:
                os.umask(previous)

    @unittest.skipUnless(os.name == "posix", "POSIX public integration permissions")
    def test_existing_private_parent_is_preserved_and_reported(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            parent = Path(root) / "usr"
            parent.mkdir(mode=0o700)
            with self.assertRaisesRegex(UpdateError, "review existing permissions: " + str(parent)):
                integration_parent(layout, parent / "lib/systemd/user")
            self.assertEqual(parent.stat().st_mode & 0o777, 0o700)

    @unittest.skipUnless(os.name == "posix", "POSIX public integration permissions")
    def test_existing_accessible_parent_mode_is_not_normalized(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            parent = Path(root) / "usr"
            parent.mkdir()
            parent.chmod(0o775)
            integration_parent(layout, parent / "lib")
            self.assertEqual(parent.stat().st_mode & 0o777, 0o775)

    def test_preflight_preserves_unrelated_file(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            target = Path(root) / "usr/bin/convertiblectl"
            target.parent.mkdir(parents=True)
            target.write_text("user file")
            with self.assertRaises(UpdateError):
                install(layout)
            self.assertEqual(target.read_text(), "user file")
