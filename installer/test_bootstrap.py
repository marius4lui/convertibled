import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from installer.bootstrap import prepare, provision_trust
from installer.storage import Layout, atomic, read
from updater.model import UpdateError


class BootstrapTrustTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.layout = Layout(self.temporary.name)
        self.layout.initialize()
        self.source = Path(self.temporary.name) / "bootstrap-trust.json"
        # Structurally valid test-only public bytes; never used as release trust.
        der = bytes.fromhex("302a300506032b6570032100") + bytes(32)
        self.value = {"schema": 1, "roots": {"test": "-----BEGIN PUBLIC KEY-----\n" + base64.b64encode(der).decode() + "\n-----END PUBLIC KEY-----\n"}, "keyring_url": "https://github.com/example/convertibled/releases/download/trust/keyring.json", "channels": {name: "https://github.com/example/convertibled/releases/download/channels/" + name + ".json" for name in ("stable", "preview")}}

    def test_absent_public_trust_fails_without_provisioning(self):
        with self.assertRaises(UpdateError):
            provision_trust(self.layout, self.source)
        self.assertFalse((self.layout.config / "trust.json").exists())

    def test_valid_trust_is_provisioned_once(self):
        atomic(self.source, self.value)
        self.assertEqual(provision_trust(self.layout, self.source), self.value)
        self.source.unlink()
        self.assertEqual(provision_trust(self.layout, self.source), self.value)

    def test_bad_shipped_key_and_url_never_written(self):
        for invalid in ({**self.value, "roots": {"test": "placeholder"}}, {**self.value, "keyring_url": "http://example.org/keyring.json"}):
            atomic(self.source, invalid)
            with self.assertRaises(UpdateError):
                provision_trust(self.layout, self.source)
            self.assertFalse((self.layout.config / "trust.json").exists())

    def test_existing_invalid_administrator_trust_is_never_replaced(self):
        atomic(self.source, self.value)
        atomic(self.layout.config / "trust.json", {"schema": 99})
        with self.assertRaises(UpdateError):
            provision_trust(self.layout, self.source)
        self.assertEqual(read(self.layout.config / "trust.json"), {"schema": 99})

    def test_failed_preparation_preserves_update_preferences(self):
        atomic(self.source, self.value)
        manager = Mock()
        manager.return_value.prepare.side_effect = UpdateError("signature refused")
        with self.assertRaises(UpdateError):
            prepare(self.layout, self.source, False, manager)
        self.assertFalse((self.layout.config / "updates.json").exists())
