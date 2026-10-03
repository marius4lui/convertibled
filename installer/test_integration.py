import tempfile
import unittest
from pathlib import Path
from .integration import install, LINKS
from .storage import Layout
from updater.model import UpdateError


class OwnershipTests(unittest.TestCase):
    def test_preflight_preserves_unrelated_file(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            target = Path(root) / "usr/bin/convertiblectl"
            target.parent.mkdir(parents=True)
            target.write_text("user file")
            with self.assertRaises(UpdateError):
                install(layout)
            self.assertEqual(target.read_text(), "user file")
