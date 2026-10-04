import tempfile
import unittest
from unittest.mock import Mock
from installer.deferred import NAMES, finish, path_for, remove, schedule
from installer.storage import Layout, atomic, read
from updater.model import UpdateError


class DeferredInstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.layout = Layout(self.temporary.name)
        self.layout.initialize()
        candidate = self.layout.versions / "0.1.0/installer"
        candidate.mkdir(parents=True)
        (candidate / "bootstrap.py").write_text("verified fixture")
        self.run = Mock()
        self.manager = Mock()
        self.manager.return_value.activation_ready.return_value = "0.1.0"
        self.transaction = Mock()

    def tick(self, sessions=None):
        return finish(self.layout, self.run, lambda: sessions or [], self.manager, self.transaction)

    def test_logged_in_prepares_owned_timer_without_activation(self):
        schedule(self.layout, "0.1.0", self.run)
        self.tick([{"user": "1000"}])
        self.transaction.return_value.activate.assert_not_called()
        self.manager.return_value.activation_ready.assert_not_called()
        content = path_for(self.layout, NAMES[0]).read_text()
        self.assertIn("/versions/0.1.0/installer/bootstrap.py --finish-install", content)

    def test_logout_activates_authenticated_version_then_removes_units(self):
        schedule(self.layout, "0.1.0", self.run)
        self.tick()
        self.transaction.return_value.activate.assert_called_once_with("0.1.0")
        self.assertFalse((self.layout.state / "bootstrap-install.json").exists())
        self.assertTrue(all(not path_for(self.layout, name).exists() for name in NAMES))

    def test_modified_unit_blocks_removal_and_is_retained(self):
        schedule(self.layout, "0.1.0", self.run)
        path_for(self.layout, NAMES[0]).write_text("user content")
        with self.assertRaises(UpdateError):
            remove(self.layout, self.run)
        self.assertEqual(path_for(self.layout, NAMES[0]).read_text(), "user content")

    def test_foreign_unit_is_never_claimed(self):
        path = path_for(self.layout, NAMES[0])
        path.parent.mkdir(parents=True)
        path.write_text("foreign")
        with self.assertRaises(UpdateError):
            schedule(self.layout, "0.1.0", self.run)
        self.assertFalse((self.layout.state / "bootstrap-install.json").exists())

    def test_changed_prepared_version_fails_and_exposes_error(self):
        schedule(self.layout, "0.1.0", self.run)
        self.manager.return_value.activation_ready.return_value = "0.2.0"
        with self.assertRaises(UpdateError):
            self.tick()
        self.transaction.return_value.activate.assert_not_called()
        self.assertIn("candidate changed", read(self.layout.state / "status.json")["error"])
        self.run.assert_called_with(["systemctl", "disable", "--now", NAMES[1]])

    def test_interrupted_unit_creation_and_removal_are_resumable(self):
        atomic(self.layout.state / "bootstrap-install.json", {"schema": 1, "version": "0.1.0"})
        schedule(self.layout, "0.1.0", self.run)
        for name in NAMES:
            path_for(self.layout, name).unlink()
        remove(self.layout, self.run)
        self.assertFalse((self.layout.state / "bootstrap-install.json").exists())

    def test_recovered_failure_does_not_automatically_retry(self):
        schedule(self.layout, "0.1.0", self.run)
        self.transaction.return_value.recover.side_effect = lambda: atomic(self.layout.state / "transaction.json", {"candidate": "0.1.0", "phase": "rolled_back"})
        with self.assertRaises(UpdateError):
            self.tick()
        self.transaction.return_value.activate.assert_not_called()

    def test_explicit_reinstall_consumes_one_rollback_retry(self):
        atomic(self.layout.state / "transaction.json", {"candidate": "0.1.0", "phase": "rolled_back"})
        schedule(self.layout, "0.1.0", self.run)
        self.transaction.return_value.activate.side_effect = UpdateError("failed again")
        with self.assertRaises(UpdateError):
            self.tick()
        self.assertFalse(read(self.layout.state / "bootstrap-install.json")["retry_rolled_back"])
        self.transaction.return_value.activate.reset_mock()
        with self.assertRaises(UpdateError):
            self.tick()
        self.transaction.return_value.activate.assert_not_called()

    def test_login_race_keeps_timer_armed_for_safe_retry(self):
        schedule(self.layout, "0.1.0", self.run)
        self.run.reset_mock()
        self.transaction.return_value.activate.side_effect = UpdateError("Waiting for graphical logout; locking does not count")
        self.tick()
        self.run.assert_not_called()
        self.assertTrue(read(self.layout.state / "bootstrap-install.json")["retry_rolled_back"])
        self.assertIsNone(read(self.layout.state / "status.json")["error"])

    def test_admission_contention_keeps_timer_armed(self):
        schedule(self.layout, "0.1.0", self.run)
        self.run.reset_mock()
        self.transaction.return_value.recover.side_effect = UpdateError("Waiting for GNOME session admission lock")
        self.tick()
        self.run.assert_not_called()
        self.transaction.return_value.activate.assert_not_called()
