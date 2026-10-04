import datetime as dt
import tempfile
import unittest
from .schedule import due, quarantined
from installer.storage import Layout, atomic


class ScheduleTests(unittest.TestCase):
    def test_logout_checks_do_not_download_every_two_minutes(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            now = dt.datetime.now(dt.timezone.utc)
            self.assertTrue(due(layout, now))
            self.assertFalse(due(layout, now + dt.timedelta(minutes=2)))
            self.assertFalse(due(layout, now - dt.timedelta(hours=1)))
            self.assertTrue(due(layout, now + dt.timedelta(hours=6)))

    def test_failed_candidate_is_not_automatically_retried(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            atomic(layout.state / "transaction.json", {"phase": "rolled_back", "candidate": "0.2.0"})
            self.assertTrue(quarantined(layout, "0.2.0"))
            self.assertFalse(quarantined(layout, "0.2.1"))
