import tempfile
import unittest
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch
from installer.onboarding import onboarding, decline, consent
from installer.storage import Layout, atomic, read
from updater.model import UpdateError


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.layout = Layout(self.temporary.name)
        self.layout.initialize()
        atomic(self.layout.state / "onboarding.json", {"schema": 1, "users": {"1000": "consent-token"}, "pending_uid": 1000})
        self.state = Path(self.temporary.name) / "user/onboarding.json"
        self.run = Mock(return_value=Mock(stdout="GNOME Shell 50.0"))

    def test_only_consented_wayland_user_is_enabled_once(self):
        self.assertFalse(onboarding(self.layout, self.state, 1001, {"XDG_SESSION_TYPE": "wayland"}, self.run))
        self.assertFalse(onboarding(self.layout, self.state, 0, {"XDG_SESSION_TYPE": "wayland"}, self.run))
        self.assertFalse(onboarding(self.layout, self.state, 1000, {"XDG_SESSION_TYPE": "x11"}, self.run))
        self.run.assert_not_called()
        self.assertTrue(onboarding(self.layout, self.state, 1000, {"XDG_SESSION_TYPE": "wayland"}, self.run))
        self.assertEqual(read(self.state)["consent"], "consent-token")
        self.run.reset_mock()
        self.assertFalse(onboarding(self.layout, self.state, 1000, {"XDG_SESSION_TYPE": "wayland"}, self.run))
        self.run.assert_not_called()

    def test_failure_never_records_success(self):
        self.run.return_value.stdout = "GNOME Shell 49.0"
        with self.assertRaises(UpdateError):
            onboarding(self.layout, self.state, 1000, {"XDG_SESSION_TYPE": "wayland"}, self.run)
        self.assertFalse(self.state.exists())

    def test_new_explicit_consent_permits_onboarding_again(self):
        atomic(self.state, {"schema": 1, "consent": "previous-consent"})
        self.assertTrue(onboarding(self.layout, self.state, 1000, {"XDG_SESSION_TYPE": "wayland"}, self.run))

    def test_registry_readiness_retries_before_enabling_and_consuming_consent(self):
        pause = Mock()
        self.run.side_effect = [Mock(stdout="GNOME Shell 50.0"),
            subprocess.CalledProcessError(1, "gnome-extensions"),
            subprocess.TimeoutExpired("gnome-extensions", 2), Mock(), Mock()]
        self.assertTrue(onboarding(self.layout, self.state, 1000, {"XDG_SESSION_TYPE": "wayland"}, self.run, pause))
        self.assertEqual(pause.call_count, 2)
        commands = [call.args[0][1] for call in self.run.call_args_list]
        self.assertEqual(commands, ["--version", "info", "info", "info", "enable"])
        self.assertEqual(read(self.state)["consent"], "consent-token")

    def test_unready_registry_is_bounded_and_preserves_consent_for_later_login(self):
        pause = Mock()
        def unready(command, **kwargs):
            if command[0] == "gnome-shell":
                return Mock(stdout="GNOME Shell 50.0")
            self.assertEqual(command[1], "info")
            self.assertEqual(kwargs["timeout"], 2)
            raise subprocess.CalledProcessError(1, command)
        self.run.side_effect = unready
        with self.assertRaisesRegex(UpdateError, "did not become ready"):
            onboarding(self.layout, self.state, 1000, {"XDG_SESSION_TYPE": "wayland"}, self.run, pause)
        self.assertEqual(pause.call_count, 14)
        self.assertEqual(self.run.call_count, 16)
        self.assertFalse(self.state.exists())

    def test_enable_failure_never_consumes_consent(self):
        self.run.side_effect = [Mock(stdout="GNOME Shell 50.0"), Mock(),
            subprocess.CalledProcessError(1, "gnome-extensions enable")]
        with self.assertRaises(subprocess.CalledProcessError):
            onboarding(self.layout, self.state, 1000, {"XDG_SESSION_TYPE": "wayland"}, self.run, Mock())
        self.assertFalse(self.state.exists())

    def test_declining_again_revokes_pending_setup_only_for_that_user(self):
        decline(self.layout, "1001")
        self.assertIn("1000", read(self.layout.state / "onboarding.json")["users"])
        self.assertEqual(read(self.layout.state / "onboarding.json")["pending_uid"], 1000)
        self.assertNotIn("shell_acceptance", read(self.layout.state / "onboarding.json"))
        decline(self.layout, "1000")
        self.assertNotIn("pending_uid", read(self.layout.state / "onboarding.json"))
        self.assertFalse(onboarding(self.layout, self.state, 1000, {"XDG_SESSION_TYPE": "wayland"}, self.run))
        self.run.assert_not_called()

    def test_first_explicit_decline_is_recorded_without_existing_consent(self):
        (self.layout.state / "onboarding.json").unlink()
        decline(self.layout, "1000")
        self.assertEqual(read(self.layout.state / "onboarding.json")["shell_acceptance"], "not_requested")
        self.assertFalse(onboarding(self.layout, self.state, 1000, {"XDG_SESSION_TYPE": "wayland"}, self.run))
        self.run.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "POSIX account lookup")
    def test_later_consent_replaces_explicit_decline(self):
        decline(self.layout, "1000")
        with patch("pwd.getpwuid"):
            consent(self.layout, "1000")
        record = read(self.layout.state / "onboarding.json")
        self.assertNotIn("shell_acceptance", record)
        self.assertEqual(record["pending_uid"], 1000)
