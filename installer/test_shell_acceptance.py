import os
import tempfile
import unittest
from unittest.mock import patch
from .storage import Layout, atomic, read
from .transaction import Transaction
from .shell_acceptance import evaluate, observe, reset, receipt

BOOT = "11111111-1111-1111-1111-111111111111"
OTHER_BOOT = "22222222-2222-2222-2222-222222222222"


@unittest.skipUnless(os.name == "posix", "POSIX transaction boundary")
class ShellAcceptanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.layout = Layout(temporary.name)
        self.layout.initialize()
        patcher = patch("installer.shell_acceptance.boot_id", return_value=BOOT)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.value = {"schema": 1, "phase": "awaiting_shell", "candidate": "0.2.0", "previous": "0.1.0",
                      "shell_acceptance": "pending_intent", "observed_sessions": []}

    def write(self, field, state, uid=1000, session="c1", **changes):
        kind = "intent" if field == "expected" else "health"
        value = {"schema": 1, "version": "0.2.0", "uid": uid, "session": session, "boot_id": BOOT, field: state}
        value.update(changes)
        path = self.layout.state / f"health/shell-{kind}-{uid}.json"
        atomic(path, value)
        return path

    def seen(self, uid=1000, session="c1"):
        observe(self.value, [{"user": str(uid), "session": session}])

    def test_no_receipt_or_unknown_intent_never_means_disabled(self):
        self.assertEqual(evaluate(self.layout, self.value), "pending_intent")
        self.write("healthy", True)
        self.assertEqual(evaluate(self.layout, self.value), "pending_intent")
        self.write("expected", None)
        self.assertEqual(evaluate(self.layout, self.value), "pending_intent")

    def test_disabled_is_service_only_even_after_explicit_health_failure(self):
        self.seen()
        self.write("expected", False)
        self.write("healthy", False)
        self.assertEqual(evaluate(self.layout, self.value), "not_requested")

    def test_enabled_requires_actual_matching_health(self):
        self.seen()
        self.write("expected", True)
        self.assertEqual(evaluate(self.layout, self.value), "failed")
        self.write("healthy", False)
        self.assertEqual(evaluate(self.layout, self.value), "failed")
        self.write("healthy", True, session="foreign")
        self.assertEqual(evaluate(self.layout, self.value), "failed")
        self.write("healthy", True, boot_id=OTHER_BOOT)
        self.assertEqual(evaluate(self.layout, self.value), "failed")
        self.write("healthy", True)
        self.assertEqual(evaluate(self.layout, self.value), "verified")

    def test_other_user_cannot_mask_enabled_failure_or_unknown_intent(self):
        self.seen()
        self.seen(1001, "c2")
        self.write("expected", False, 1001, "c2")
        self.assertEqual(evaluate(self.layout, self.value), "pending_intent")
        self.write("expected", True)
        self.assertEqual(evaluate(self.layout, self.value), "failed")
        self.write("healthy", True, 1001, "c2")
        self.assertEqual(evaluate(self.layout, self.value), "failed")
        self.write("healthy", True)
        self.assertEqual(evaluate(self.layout, self.value), "verified")

    def test_stale_or_foreign_intent_does_not_complete(self):
        self.seen()
        for changes in ({"boot_id": OTHER_BOOT}, {"session": "c2"}, {"version": "0.1.0"}):
            with self.subTest(changes=changes):
                self.write("expected", False, **changes)
                self.assertEqual(evaluate(self.layout, self.value), "pending_intent")

    def test_short_login_receipt_is_evidence_but_prior_boot_is_not(self):
        self.write("expected", False, boot_id=OTHER_BOOT)
        self.assertEqual(evaluate(self.layout, self.value), "pending_intent")
        self.write("expected", False)
        self.assertEqual(evaluate(self.layout, self.value), "not_requested")

    def test_new_session_supersedes_same_user_only(self):
        self.seen()
        self.seen(1001, "c2")
        self.seen(1000, "c3")
        self.assertEqual({(item["uid"], item["session"]) for item in self.value["observed_sessions"]}, {(1000, "c3"), (1001, "c2")})

    def test_unidentified_current_session_cannot_be_hidden_by_disabled_user(self):
        self.write("expected", False)
        observe(self.value, [{"session": "unknown", "user": None}])
        self.assertEqual(evaluate(self.layout, self.value), "pending_intent")

    def test_invalid_receipts_are_unknown_including_legacy_and_oversized(self):
        path = self.write("expected", False)
        for value in ({"schema": True}, {"uid": True}, {"expected": "false"}, {"boot_id": ""}, {"extra": 1}):
            self.write("expected", False, **value)
            self.assertIsNone(receipt(path, "0.2.0"))
        atomic(path, {"version": "0.2.0", "uid": 1000, "healthy": True})
        self.assertIsNone(receipt(path, "0.2.0"))
        path.write_text(" " * 4097)
        self.assertIsNone(receipt(path, "0.2.0"))
        path.write_text('{"schema":1,"schema":1}')
        self.assertIsNone(receipt(path, "0.2.0"))

    def test_reset_removes_only_fixed_receipt_names(self):
        intent = self.write("expected", True)
        health = self.write("healthy", True)
        retained = self.layout.state / "health/private-note.txt"
        retained.write_text("keep")
        reset(self.layout)
        self.assertFalse(intent.exists())
        self.assertFalse(health.exists())
        self.assertTrue(retained.exists())

    def test_online_success_settles_without_services_or_second_logout(self):
        for field in ("expected", "healthy"):
            self.write(field, True)
        atomic(self.layout.state / "transaction.json", self.value)
        calls = []
        transaction = Transaction(self.layout, sessions=lambda: [{"user": "1000", "session": "c1"}], run=calls.append)
        transaction.observe_login()
        self.assertEqual(read(transaction.journal)["phase"], "complete")
        self.assertEqual(calls, [])

    def test_public_acceptance_is_a_fixed_label_without_session_identifiers(self):
        from .status import publish
        self.seen()
        for acceptance in ("pending_intent", "verified", "not_requested", "private/unexpected"):
            self.value["shell_acceptance"] = acceptance
            atomic(self.layout.state / "transaction.json", self.value)
            result = publish(self.layout)
            self.assertEqual(result["shell_acceptance"], None if acceptance == "private/unexpected" else acceptance)
            self.assertNotIn("observed_sessions", result)
            self.assertNotIn("boot_id", result)
            self.assertNotIn("uid", result)
    def test_online_failure_waits_for_logout_before_rollback(self):
        self.write("expected", True)
        self.write("healthy", False)
        atomic(self.layout.state / "transaction.json", self.value)
        transaction = Transaction(self.layout, sessions=lambda: [{"user": "1000", "session": "c1"}])
        with patch.object(transaction, "rollback") as rollback:
            transaction.observe_login()
            rollback.assert_not_called()
            self.assertEqual(read(transaction.journal)["phase"], "awaiting_shell")
            transaction.sessions = lambda: []
            transaction.recover()
            rollback.assert_called_once()

    def test_first_consented_login_settles_with_matching_receipt_online(self):
        self.value.pop("shell_acceptance")
        self.value["expected_uid"] = 1000
        self.write("healthy", True)
        atomic(self.layout.state / "transaction.json", self.value)
        transaction = Transaction(self.layout, sessions=lambda: [{"user": "1000", "session": "c1"}], run=lambda args: self.fail("Unexpected host mutation"))
        transaction.observe_login()
        self.assertEqual(read(transaction.journal)["phase"], "complete")

    def test_unknown_remains_pending_and_disabled_completes_after_logout(self):
        atomic(self.layout.state / "transaction.json", self.value)
        transaction = Transaction(self.layout, sessions=lambda: [])
        with patch.object(transaction, "rollback") as rollback:
            self.assertEqual(transaction.recover()["phase"], "awaiting_shell")
            self.write("expected", False)
            result = transaction.recover()
            self.assertEqual(result["phase"], "complete")
            self.assertEqual(result["shell_acceptance"], "not_requested")
            rollback.assert_not_called()
