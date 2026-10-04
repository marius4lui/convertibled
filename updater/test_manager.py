import tempfile
import unittest
from .manager import trust
from installer.storage import Layout, atomic
from .model import UpdateError


class TrustTests(unittest.TestCase):
    def test_bootstrap_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(UpdateError):
                trust(Layout(root))

    def test_localhost_trust_endpoint_denied(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            atomic(layout.config / "trust.json", {"schema": 1, "roots": {"offline": "pem"}, "keyring_url": "https://localhost/key", "channels": {"stable": "https://github.com/s", "preview": "https://github.com/p"}})
            with self.assertRaises(UpdateError):
                trust(layout)
