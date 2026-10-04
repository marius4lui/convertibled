"""Real flock contention must never overwrite the owner's public progress."""
import contextlib
import io
import os
import tempfile
import unittest
from unittest.mock import patch
from . import bootstrap, cli
from .storage import BusyError, Layout, atomic
from updater.model import UpdateError


@unittest.skipUnless(os.name == "posix", "POSIX flock")
class BusyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.layout = Layout(temporary.name)
        self.layout.initialize()
        self.status = self.layout.state / "status.json"
        atomic(self.status, {"schema": 1, "phase": "switching", "error": None})
        self.before = self.status.read_bytes()

    def invoke(self, module, args):
        output, error = io.StringIO(), io.StringIO()
        with patch.object(module, "Layout", return_value=self.layout), patch("sys.argv", [module.__name__, *args]), patch("os.geteuid", return_value=0), contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            result = module.main()
        return result, output.getvalue(), error.getvalue()

    def test_lock_raises_typed_busy_without_entering_transaction(self):
        with self.layout.lock(), self.assertRaises(BusyError):
            with self.layout.lock():
                self.fail("Entered an already-owned transaction")

    def test_scheduled_update_contention_is_quiet_and_preserves_progress(self):
        with self.layout.lock(), patch.object(cli, "publish") as publish:
            self.assertEqual(self.invoke(cli, ["scheduled"]), (0, "", ""))
            publish.assert_not_called()
        self.assertEqual(self.status.read_bytes(), self.before)

    def test_deferred_install_contention_is_quiet_and_preserves_progress(self):
        with self.layout.lock():
            self.assertEqual(self.invoke(bootstrap, ["--finish-install"]), (0, "", ""))
        self.assertEqual(self.status.read_bytes(), self.before)

    def test_interactive_mutations_still_report_busy_without_status_writes(self):
        with self.layout.lock(), patch.object(cli, "publish") as publish:
            for arguments in (["prepare"], ["request-activate"], ["cancel-pending"], ["automatic", "off"]):
                with self.subTest(arguments=arguments):
                    code, output, error = self.invoke(cli, arguments)
                    self.assertEqual((code, output), (1, ""))
                    self.assertIn("Another installation transaction", error)
            publish.assert_not_called()
            for arguments in (["off"], ["--cancel-install"]):
                code, output, error = self.invoke(bootstrap, arguments)
                self.assertEqual((code, output), (1, ""))
                self.assertIn("Another installation transaction", error)
        self.assertEqual(self.status.read_bytes(), self.before)

    def test_matching_error_text_is_not_mistaken_for_benign_contention(self):
        with patch.object(cli, "execute", side_effect=UpdateError("Another installation transaction is running")):
            code, _, error = self.invoke(cli, ["scheduled"])
        self.assertEqual(code, 1)
        self.assertIn("Another installation transaction", error)
        self.assertNotEqual(self.status.read_bytes(), self.before)

    def test_real_error_publication_reacquires_transaction_lock(self):
        def check_locked(layout, error):
            with self.assertRaises(BusyError):
                with layout.lock():
                    self.fail("Error status was written outside the transaction lock")
        with patch.object(cli, "execute", side_effect=UpdateError("Actual failure")), patch.object(cli, "publish", side_effect=check_locked) as publish:
            self.assertEqual(self.invoke(cli, ["scheduled"])[0], 1)
            publish.assert_called_once()

    def test_error_cannot_overwrite_status_if_next_transaction_has_started(self):
        with self.layout.lock(), patch.object(cli, "execute", side_effect=UpdateError("Earlier failure")), patch.object(cli, "publish") as publish:
            self.assertEqual(self.invoke(cli, ["scheduled"])[0], 1)
            publish.assert_not_called()
        self.assertEqual(self.status.read_bytes(), self.before)
