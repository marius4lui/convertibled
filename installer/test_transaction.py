import tempfile
import unittest
import os
from unittest.mock import patch
from .transaction import Transaction
from .storage import Layout, atomic, read
from updater.model import UpdateError


@unittest.skipUnless(os.name == "posix", "POSIX admission boundary")
class TransactionTests(unittest.TestCase):
    @patch("installer.transaction.install")
    @patch("installer.identity.ensure")
    def test_first_install_decline_completes_services_only_and_survives_logout(self, identity, integration):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            atomic(layout.versions / "0.2.0/manifest.json", {})
            atomic(layout.state / "onboarding.json", {"schema": 1, "users": {}, "shell_acceptance": "not_requested"})
            calls = []
            transaction = Transaction(layout, sessions=lambda: [], run=calls.append)
            result = transaction.activate("0.2.0")
            self.assertEqual(result["phase"], "complete")
            self.assertEqual(result["shell_acceptance"], "not_requested")
            self.assertIn([str(layout.versions / "0.2.0/bin/convertibled"), "--check"], calls)
            self.assertIn(["systemctl", "is-active", "--quiet", "convertibled.service"], calls)
            self.assertFalse((layout.state / "health/shell-health.json").exists())
            transaction.sessions = lambda: [{"user": "1000"}]
            transaction.observe_login()
            transaction.sessions = lambda: []
            self.assertEqual(transaction.recover()["phase"], "complete")
            self.assertEqual(layout.active(), "0.2.0")

    @patch("installer.transaction.install")
    @patch("installer.identity.ensure")
    def test_no_decline_inference_and_consent_still_requires_shell(self, identity, integration):
        for onboarding in ({}, {"pending_uid": 1000}, {"pending_uid": 1000, "shell_acceptance": "not_requested"}):
            with self.subTest(onboarding=onboarding), tempfile.TemporaryDirectory() as root:
                layout = Layout(root)
                layout.initialize()
                atomic(layout.versions / "0.2.0/manifest.json", {})
                if onboarding:
                    atomic(layout.state / "onboarding.json", onboarding)
                transaction = Transaction(layout, sessions=lambda: [], run=lambda args: None)
                result = transaction.activate("0.2.0")
                self.assertEqual(result["phase"], "awaiting_shell")
                self.assertNotIn("shell_acceptance", result)
                if "pending_uid" in onboarding:
                    self.assertEqual(result["expected_uid"], 1000)

    @patch("installer.transaction.install")
    @patch("installer.identity.ensure")
    def test_declined_shell_never_bypasses_failed_daemon_health(self, identity, integration):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            atomic(layout.versions / "0.2.0/manifest.json", {})
            atomic(layout.state / "onboarding.json", {"shell_acceptance": "not_requested"})
            def run(args):
                if args[:2] == ["systemctl", "is-active"]:
                    raise UpdateError("daemon unhealthy")
            transaction = Transaction(layout, sessions=lambda: [], run=run)
            with patch.object(transaction, "rollback") as rollback:
                with self.assertRaisesRegex(UpdateError, "daemon unhealthy"):
                    transaction.activate("0.2.0")
                rollback.assert_called_once()
            self.assertNotEqual(read(transaction.journal)["phase"], "complete")

    @patch("installer.transaction.install")
    @patch("installer.identity.ensure")
    def test_initial_decline_is_not_reused_as_update_intent(self, identity, integration):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            atomic(layout.versions / "0.1.0/manifest.json", {})
            atomic(layout.versions / "0.2.0/manifest.json", {})
            layout.select("0.1.0")
            atomic(layout.state / "onboarding.json", {"shell_acceptance": "not_requested"})
            transaction = Transaction(layout, sessions=lambda: [], run=lambda args: None)
            result = transaction.activate("0.2.0")
            self.assertEqual(result["phase"], "awaiting_shell")
            self.assertNotIn("shell_acceptance", result)

    def test_no_activation_while_locked_session_exists(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            transaction = Transaction(layout, sessions=lambda: [{"locked": True}])
            with self.assertRaises(UpdateError):
                transaction.activate("0.1.0")
            self.assertFalse(transaction.journal.exists())

    def test_backup_interruption_retains_active_version(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            transaction = Transaction(layout, sessions=lambda: [])
            atomic(transaction.journal, {"schema": 1, "candidate": "0.2.0", "previous": "0.1.0", "phase": "backup"})
            self.assertEqual(transaction.recover()["phase"], "rolled_back")

    def test_successful_shell_receipt_completes(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            transaction = Transaction(layout, sessions=lambda: [])
            atomic(transaction.journal, {"schema": 1, "candidate": "0.2.0", "previous": "0.1.0", "phase": "awaiting_shell"})
            atomic(layout.state / "health/shell-health.json", {"version": "0.2.0", "healthy": True})
            self.assertEqual(transaction.recover()["phase"], "complete")

    def test_first_login_not_yet_observed_waits(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            transaction = Transaction(layout, sessions=lambda: [])
            atomic(transaction.journal, {"schema": 1, "candidate": "0.2.0", "previous": "0.1.0", "phase": "awaiting_shell"})
            self.assertEqual(transaction.recover()["phase"], "awaiting_shell")

    def test_unrelated_user_neither_starts_acceptance_nor_supplies_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            transaction = Transaction(layout, sessions=lambda: [{"user": "1001"}])
            atomic(transaction.journal, {"schema": 1, "candidate": "0.2.0", "previous": None, "phase": "awaiting_shell", "expected_uid": 1000})
            transaction.observe_login()
            self.assertNotIn("first_session_seen", read(transaction.journal))
            transaction.sessions = lambda: []
            atomic(layout.state / "health/shell-health.json", {"version": "0.2.0", "healthy": True, "uid": 1001})
            self.assertEqual(transaction.recover()["phase"], "awaiting_shell")
            atomic(layout.state / "health/shell-health-1000.json", {"version": "0.2.0", "healthy": True, "uid": 1000})
            self.assertEqual(transaction.recover()["phase"], "complete")

    def test_consented_user_starts_first_login_acceptance(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            transaction = Transaction(layout, sessions=lambda: [{"user": "1000"}])
            atomic(transaction.journal, {"schema": 1, "candidate": "0.2.0", "phase": "awaiting_shell", "expected_uid": 1000})
            transaction.observe_login()
            self.assertTrue(read(transaction.journal)["first_session_seen"])

    def test_prepared_interruption_never_stops_existing_service(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            calls = []
            transaction = Transaction(layout, sessions=lambda: [], run=calls.append)
            atomic(transaction.journal, {"schema": 1, "candidate": "0.2.0", "previous": "0.1.0", "phase": "prepared"})
            self.assertEqual(transaction.recover()["phase"], "rolled_back")
            self.assertEqual(calls, [])
