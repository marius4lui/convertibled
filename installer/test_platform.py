import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from .platform import graphical_sessions, preflight, conflicts
from .storage import Layout
from updater.model import UpdateError


class SessionTests(unittest.TestCase):
    def test_locked_and_inactive_count(self):
        with patch("installer.platform.command", side_effect=['[{"session":"3"}]', "Type=wayland\nClass=user\nUser=1000"]):
            self.assertEqual(len(graphical_sessions()), 1)

    def test_greeter_not_user(self):
        with patch("installer.platform.command", side_effect=['[{"session":"3"}]', "Type=wayland\nClass=greeter\nUser=42"]):
            self.assertEqual(graphical_sessions(), [])

    def test_bad_identifier_denied(self):
        with patch("installer.platform.command", return_value='[{"session":"--help"}]'):
            with self.assertRaises(UpdateError):
                graphical_sessions()

    def test_malformed_session_inventory_denied(self):
        for inventory in ("{}", "[null]", "[1]"):
            with patch("installer.platform.command", return_value=inventory):
                with self.assertRaises(UpdateError):
                    graphical_sessions()

    def test_known_conflicting_extension_is_explained(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "dash-to-dock@micxgx.gmail.com").mkdir()
            with self.assertRaisesRegex(UpdateError, "dash-to-dock"):
                conflicts([root])
            self.assertTrue((Path(root) / "dash-to-dock@micxgx.gmail.com").is_dir())

    def test_low_disk_space_rejected_before_mutation(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            with patch("installer.platform.platform.freedesktop_os_release", return_value={"ID": "fedora", "VERSION_ID": "44"}), patch("installer.platform.platform.system", return_value="Linux"), patch("installer.platform.platform.machine", return_value="x86_64"), patch("installer.platform.command", return_value="GNOME Shell 50.0"), patch("installer.platform.shutil.which", return_value="/usr/bin/tool"), patch("installer.platform.shutil.disk_usage", return_value=SimpleNamespace(free=1)):
                with self.assertRaisesRegex(UpdateError, "disk space"):
                    preflight(layout, 1024)
            self.assertEqual(list(layout.versions.iterdir()), [])
