import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from installer.onboarding import onboarding, decline
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

    def test_declining_again_revokes_pending_setup_only_for_that_user(self):
        decline(self.layout, "1001")
        self.assertIn("1000", read(self.layout.state / "onboarding.json")["users"])
        self.assertEqual(read(self.layout.state / "onboarding.json")["pending_uid"], 1000)
        decline(self.layout, "1000")
        self.assertNotIn("pending_uid", read(self.layout.state / "onboarding.json"))
        self.assertFalse(onboarding(self.layout, self.state, 1000, {"XDG_SESSION_TYPE": "wayland"}, self.run))
        self.run.assert_not_called()
