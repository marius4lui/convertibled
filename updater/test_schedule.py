import datetime as dt
import tempfile
import unittest
from .schedule import due
from installer.storage import Layout


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
