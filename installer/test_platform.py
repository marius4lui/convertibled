import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from .platform import graphical_sessions, preflight, conflicts, command, SessionGone
from .storage import Layout
from updater.model import UpdateError


class SessionTests(unittest.TestCase):
    def test_vanished_session_restarts_inventory_and_finds_new_login(self):
        with patch("installer.platform.command", side_effect=['[{"session":"3"}]', SessionGone("gone"), '[{"session":"4"}]', "Type=wayland\nClass=user\nUser=1001"]) as run:
            self.assertEqual(graphical_sessions(), [{"session": "4", "user": "1001", "type": "wayland"}])
            self.assertEqual(sum(call.args[0][1] == "list-sessions" for call in run.call_args_list), 2)

    def test_repeated_session_churn_is_bounded_and_blocks_mutation(self):
        with patch("installer.platform.command", side_effect=['[{"session":"3"}]', SessionGone("gone")] * 3) as run:
            sessions = graphical_sessions()
            self.assertTrue(sessions)
            self.assertEqual(sessions[0]["type"], "unknown")
            self.assertEqual(run.call_count, 6)

    def test_arbitrary_login_failure_is_not_treated_as_logout(self):
        with patch("installer.platform.command", side_effect=['[{"session":"3"}]', UpdateError("permission denied")]) as run:
            with self.assertRaisesRegex(UpdateError, "permission denied"):
                graphical_sessions()
            self.assertEqual(run.call_count, 2)

    def test_only_exact_vanished_session_error_is_retryable(self):
        args = ["loginctl", "show-session", "3", "-p", "Type"]
        gone = "Failed to get path for session '3': No session '3' known"
        for message in (gone, "Failed to connect to bus: Access denied", gone + "\nAnother error"):
            with patch("installer.platform.subprocess.run", return_value=SimpleNamespace(returncode=1, stdout="", stderr=message)) as run:
                with self.assertRaises(UpdateError) as raised:
                    command(args)
                self.assertEqual(isinstance(raised.exception, SessionGone), message == gone)
                self.assertEqual(run.call_args.kwargs["env"]["LC_ALL"], "C")

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
