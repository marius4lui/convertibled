"""Public trust export never copies private key material or replaces prior output."""
import json
import shutil
import unittest
import test_release_delivery
from release.provision import provision
from updater.crypto import keyring
from updater.model import UpdateError


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL unavailable")
class ProvisionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_release_delivery.DeliveryTests("test_verified_release")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def export(self, output, repository="owner/project"):
        f = self.fixture
        provision(repository, "root", f.keys["root"], f.directory / "root.pem", "release",
                  f.keys["release"], 1, 90, output)

    def test_verified_public_only_export_and_no_overwrite(self):
        output = self.fixture.directory / "export"
        self.export(output)
        self.assertEqual({p.name for p in output.iterdir()}, {"trust.json", "keyring.json"})
        trust = json.loads((output / "trust.json").read_bytes())
        self.assertEqual(trust["channels"]["stable"], "https://raw.githubusercontent.com/owner/project/update-channels/stable.json")
        import datetime as dt
        self.assertEqual(keyring((output / "keyring.json").read_bytes(), trust["roots"], dt.datetime.now(dt.timezone.utc))["sequence"], 1)
        self.assertNotIn(b"PRIVATE KEY", (output / "trust.json").read_bytes() + (output / "keyring.json").read_bytes())
        with self.assertRaises(FileExistsError):
            self.export(output)

    def test_invalid_repository_leaves_no_output(self):
        output = self.fixture.directory / "invalid"
        with self.assertRaises(UpdateError):
            self.export(output, "../other/repository")
        self.assertFalse(output.exists())
