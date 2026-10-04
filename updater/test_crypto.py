"""Real temporary Ed25519 key tests; no key material survives the test."""
import base64
import datetime as dt
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from .crypto import envelope, keyring, verify
from .model import canonical, UpdateError


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL not available")
class CryptoTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.key = self.directory / "key.pem"
        subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(self.key)], check=True, capture_output=True)
        self.public = subprocess.check_output(["openssl", "pkey", "-in", str(self.key), "-pubout"], text=True)

    def tearDown(self):
        self.temporary.cleanup()

    def signed(self, value, identifier="release"):
        source = self.directory / "payload"
        source.write_bytes(canonical(value))
        signature = subprocess.check_output(["openssl", "pkeyutl", "-sign", "-inkey", str(self.key), "-rawin", "-in", str(source)])
        return {"key_id": identifier, "payload": value, "signature": base64.b64encode(signature).decode()}

    def test_valid_and_tampered_signature(self):
        signed = self.signed({"sequence": 1})
        self.assertEqual(envelope(canonical(signed), {"release": self.public}), {"sequence": 1})
        signed["payload"]["sequence"] = 2
        with self.assertRaises(UpdateError):
            envelope(canonical(signed), {"release": self.public})

    def test_revoked_key(self):
        with self.assertRaises(UpdateError):
            envelope(canonical(self.signed({"sequence": 1})), {"new-release": self.public})

    def test_root_rotation_sequence(self):
        now = dt.datetime.now(dt.timezone.utc)
        value = {"schema": 1, "sequence": 3, "issued": (now - dt.timedelta(hours=1)).isoformat(), "expires": (now + dt.timedelta(days=1)).isoformat(), "keys": {"next": self.public}}
        signed = canonical(self.signed(value, "root"))
        self.assertEqual(keyring(signed, {"root": self.public}, now, 3)["keys"], {"next": self.public})
        with self.assertRaises(UpdateError):
            keyring(signed, {"root": self.public}, now, 4)

    def test_wrong_signature_length(self):
        with self.assertRaises(UpdateError):
            verify(self.public, b"payload", "YQ==")
