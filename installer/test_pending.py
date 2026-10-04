import tempfile
import unittest
from unittest.mock import Mock
from installer.pending import cancel, process, request, requested
from installer.status import publish
from installer.storage import Layout, atomic
from installer.configuration import preferences, set_preferences
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
        self.manager = Mock()
        self.manager.return_value.activation_ready.return_value = "0.2.0"

    def tick(self, sessions=None):
        return process(self.layout, lambda: sessions or [], self.transaction, self.remove, self.manager)

    def queue_activation(self):
        atomic(self.layout.state / "prepared.json", {"schema": 1, "version": "0.2.0", "channel": "stable"})
        request(self.layout, "activate", self.run, self.manager)

    def running_activation(self, phase, active):
        self.queue_activation()
        value = requested(self.layout)
        value["state"] = "running"
        atomic(self.layout.state / "pending-action.json", value)
        atomic(self.layout.state / "transaction.json", {"phase": phase, "candidate": "0.2.0", "previous": "0.1.0"})
        self.layout.active.return_value = active

    def test_manual_activation_preserves_opt_out_and_waits_for_every_graphical_session(self):
        set_preferences(self.layout, automatic=False)
        self.queue_activation()
        self.assertEqual(publish(self.layout)["pending_action"], "activate")
        self.manager.return_value.activation_ready.assert_called_once_with()
        self.tick([{"locked": True, "active": False}])
        self.transaction.return_value.activate.assert_not_called()
        self.assertEqual(self.manager.return_value.activation_ready.call_count, 1)
        self.tick()
        self.transaction.return_value.activate.assert_called_once_with("0.2.0")
        self.assertEqual(self.manager.return_value.activation_ready.call_count, 2)
        self.assertFalse(preferences(self.layout)["automatic_updates"])
        self.assertIsNone(requested(self.layout))

    def test_changed_candidate_or_channel_requires_explicit_review(self):
        for changed in ({"version": "0.3.0", "channel": "stable"}, {"version": "0.2.0", "channel": "preview"}):
            self.queue_activation()
            atomic(self.layout.state / "prepared.json", changed)
            self.tick()
            self.assertEqual(requested(self.layout)["state"], "failed")
            self.transaction.return_value.activate.assert_not_called()
            cancel(self.layout)

    def test_activation_reauthenticates_and_rejects_expired_or_revoked_release(self):
        self.queue_activation()
        self.manager.return_value.activation_ready.side_effect = UpdateError("Release expired or key revoked")
        self.tick()
        self.assertEqual(requested(self.layout)["state"], "failed")
        self.transaction.return_value.activate.assert_not_called()
        cancel(self.layout)
        with self.assertRaises(UpdateError):
            request(self.layout, "activate", self.run, self.manager)
        self.assertIsNone(requested(self.layout))

    def test_successful_activation_crash_never_reapplies_candidate(self):
        for phase in ("awaiting_shell", "complete"):
            self.layout.active.return_value = "0.1.0"
            self.running_activation(phase, "0.2.0")
            self.tick([{"active": True}])
            self.assertIsNone(requested(self.layout))
            self.assertEqual(self.transaction.return_value.method_calls, [])

    def test_rolled_back_activation_does_not_loop(self):
        self.running_activation("rolled_back", "0.1.0")
        self.tick()
        self.tick()
        self.assertEqual(requested(self.layout)["state"], "failed")
        self.transaction.return_value.activate.assert_not_called()

    def test_selected_interruption_recovers_without_reapplying(self):
        self.running_activation("selected", "0.2.0")
        def recover():
            atomic(self.layout.state / "transaction.json", {"phase": "rolled_back", "candidate": "0.2.0", "previous": "0.1.0"})
            self.layout.active.return_value = "0.1.0"
        self.transaction.return_value.recover.side_effect = recover
        self.tick()
        self.transaction.return_value.recover.assert_called_once_with()
        self.transaction.return_value.activate.assert_not_called()
        self.assertEqual(requested(self.layout)["state"], "failed")

    def test_running_activation_cannot_be_replaced_before_recovery(self):
        self.running_activation("quiescing", "0.1.0")
        with self.assertRaises(UpdateError):
            request(self.layout, "activate", self.run, self.manager)
        self.assertEqual(requested(self.layout)["state"], "running")

    def test_recovery_wait_retains_running_transaction_identity(self):
        self.running_activation("selected", "0.2.0")
        self.transaction.return_value.recover.side_effect = UpdateError("Waiting for graphical logout; locking does not count")
        self.tick([{"active": True}])
        self.assertEqual(requested(self.layout)["state"], "running")
        self.transaction.return_value.activate.assert_not_called()

    def test_authenticated_candidate_change_cannot_activate_another_version(self):
        self.queue_activation()
        self.manager.return_value.activation_ready.return_value = "0.3.0"
        self.tick()
        self.assertEqual(requested(self.layout)["state"], "failed")
        self.transaction.return_value.activate.assert_not_called()

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

    def test_failed_request_does_not_starve_online_health_or_logout_recovery(self):
        self.queue_activation()
        value = requested(self.layout)
        value.update(state="failed", error="Candidate changed")
        atomic(self.layout.state / "pending-action.json", value)
        atomic(self.layout.state / "transaction.json", {"phase": "awaiting_shell"})
        self.tick([{"user": "1000"}])
        self.transaction.return_value.observe_login.assert_called_once_with()
        self.transaction.return_value.recover.assert_not_called()
        self.tick()
        self.transaction.return_value.recover.assert_called_once_with()
        self.transaction.return_value.activate.assert_not_called()
        self.assertEqual(requested(self.layout)["state"], "failed")

    def test_waiting_action_allows_journal_only_acceptance_online(self):
        request(self.layout, "uninstall", self.run)
        atomic(self.layout.state / "transaction.json", {"phase": "awaiting_shell"})
        self.tick([{"user": "1000"}])
        self.transaction.return_value.observe_login.assert_called_once_with()
        self.transaction.return_value.recover.assert_not_called()
        self.remove.assert_not_called()

    def test_next_activation_cannot_skip_failed_previous_trial(self):
        self.queue_activation()
        atomic(self.layout.state / "transaction.json", {"phase": "awaiting_shell"})
        self.transaction.return_value.recover.side_effect = lambda: setattr(self.layout.active, "return_value", "0.0.9")
        self.tick()
        self.transaction.return_value.recover.assert_called_once_with()
        self.transaction.return_value.activate.assert_not_called()
        self.assertEqual(requested(self.layout)["state"], "failed")
