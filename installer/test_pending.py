import tempfile
import unittest
from unittest.mock import Mock
from installer.pending import cancel, process, request, requested
from installer.status import publish
from installer.storage import Layout, atomic
from updater.model import UpdateError


class PendingActionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.layout = Layout(self.temporary.name)
        self.layout.initialize()
        self.layout.active = Mock(return_value="0.1.0")
        self.run = Mock()
        self.transaction = Mock()
        self.remove = Mock()

    def tick(self, sessions=None):
        return process(self.layout, lambda: sessions or [], self.transaction, self.remove)

    def test_locked_or_inactive_graphical_session_still_blocks_mutation(self):
        for action in ("uninstall", "rollback", "recover"):
            request(self.layout, action, self.run)
            self.assertTrue(self.tick([{"user": "1000", "locked": True, "active": False}]))
            self.transaction.return_value.assert_not_called()
            self.assertEqual(self.transaction.return_value.method_calls, [])
            self.remove.assert_not_called()
            self.assertEqual(publish(self.layout)["pending_action"], action)
            self.assertEqual(publish(self.layout)["phase"], "waiting_for_logout")
            cancel(self.layout)

    def test_logout_runs_only_requested_action_and_consumes_intent(self):
        for action in ("uninstall", "rollback", "recover"):
            self.transaction.reset_mock()
            self.remove.reset_mock()
            request(self.layout, action, self.run)
            self.assertTrue(self.tick())
            if action == "uninstall":
                self.remove.assert_called_once_with(self.layout)
            else:
                getattr(self.transaction.return_value, action).assert_called_once_with()
            self.assertIsNone(requested(self.layout))

    def test_failure_persists_without_automatic_retry_and_explicit_retry_works(self):
        request(self.layout, "rollback", self.run)
        self.transaction.return_value.rollback.side_effect = UpdateError("previous version unavailable")
        self.tick()
        self.tick()
        self.transaction.return_value.rollback.assert_called_once_with()
        self.assertEqual(publish(self.layout)["phase"], "action_failed")
        self.assertIn("previous version", publish(self.layout)["error"])
        self.transaction.return_value.rollback.side_effect = None
        request(self.layout, "rollback", self.run)
        self.tick()
        self.assertEqual(self.transaction.return_value.rollback.call_count, 2)

    def test_changed_version_rejects_stale_request_before_any_recovery(self):
        request(self.layout, "uninstall", self.run)
        self.layout.active.return_value = "0.2.0"
        (self.layout.state / "admission.pending").touch()
        self.tick()
        self.remove.assert_not_called()
        self.assertEqual(self.transaction.return_value.method_calls, [])
        self.assertEqual(requested(self.layout)["state"], "failed")

    def test_login_race_defers_without_failure(self):
        request(self.layout, "rollback", self.run)
        self.transaction.return_value.rollback.side_effect = UpdateError("Waiting for graphical logout; locking does not count")
        self.tick()
        self.assertEqual(requested(self.layout)["state"], "waiting")
        self.assertIsNone(publish(self.layout)["error"])

    def test_conflicting_action_requires_cancel(self):
        request(self.layout, "rollback", self.run)
        with self.assertRaises(UpdateError):
            request(self.layout, "uninstall", self.run)
        cancel(self.layout)
        request(self.layout, "uninstall", self.run)
        self.assertEqual(requested(self.layout)["action"], "uninstall")

    def test_cancellation_cannot_discard_interrupted_critical_transaction(self):
        request(self.layout, "uninstall", self.run)
        value = requested(self.layout)
        value["state"] = "running"
        atomic(self.layout.state / "pending-action.json", value)
        atomic(self.layout.state / "transaction.json", {"phase": "removing"})
        with self.assertRaises(UpdateError):
            cancel(self.layout)
        self.assertIsNotNone(requested(self.layout))

    def test_interrupted_completed_rollback_does_not_rollback_twice(self):
        request(self.layout, "rollback", self.run)
        value = requested(self.layout)
        value["state"] = "running"
        atomic(self.layout.state / "pending-action.json", value)
        atomic(self.layout.state / "transaction.json", {"phase": "rolled_back", "candidate": "0.1.0", "previous": "0.0.9"})
        self.layout.active.return_value = "0.0.9"
        self.tick()
        self.assertEqual(self.transaction.return_value.method_calls, [])
        self.assertIsNone(requested(self.layout))

    def test_timer_failure_is_actionable_and_failed(self):
        self.run.side_effect = UpdateError("systemctl unavailable")
        with self.assertRaises(UpdateError):
            request(self.layout, "recover", self.run)
        self.assertEqual(requested(self.layout)["state"], "failed")

    def test_failed_action_still_allows_journal_recovery_without_retry(self):
        request(self.layout, "rollback", self.run)
        self.transaction.return_value.rollback.side_effect = UpdateError("service restart failed")
        self.tick()
        (self.layout.state / "admission.pending").touch()
        self.tick()
        self.transaction.return_value.rollback.assert_called_once_with()
        self.transaction.return_value.recover.assert_called_once_with()
        self.assertEqual(requested(self.layout)["state"], "failed")
