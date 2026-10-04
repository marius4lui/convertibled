import tempfile
import unittest
import os
from unittest.mock import patch
from .transaction import Transaction
from .storage import Layout, atomic, read
from updater.model import UpdateError


@unittest.skipUnless(os.name == "posix", "POSIX admission boundary")
class TransactionTests(unittest.TestCase):
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
