import unittest
from unittest.mock import patch
from .platform import graphical_sessions
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
