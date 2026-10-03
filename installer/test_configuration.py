import tempfile
import unittest
from pathlib import Path
from .configuration import preferences, set_preferences, backup, restore
from .storage import Layout
from updater.model import UpdateError


class ConfigurationTests(unittest.TestCase):
    def test_opt_out_and_channel(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            self.assertTrue(preferences(layout)["automatic_updates"])
            set_preferences(layout, automatic=False, channel="preview")
            self.assertEqual(preferences(layout)["channel"], "preview")
            self.assertFalse(preferences(layout)["automatic_updates"])

    def test_backup_restore(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            set_preferences(layout)
            backup(layout)
            set_preferences(layout, automatic=False)
            restore(layout)
            self.assertTrue(preferences(layout)["automatic_updates"])

    def test_unknown_channel(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            with self.assertRaises(UpdateError):
                set_preferences(layout, channel="experimental")
