"""Publication ordering with real signatures and isolated GitHub/network substitutes."""
import base64
import json
import os
import shutil
import subprocess
import unittest
import types
from pathlib import Path
from unittest.mock import patch
import test_release_delivery
from release import publish
from updater.model import UpdateError, canonical


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL unavailable")
class PublishTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_release_delivery.DeliveryTests("test_verified_release")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.assets = self.fixture.directory
        self.commit = "a" * 40
        candidate = json.loads((self.assets / "candidate.json").read_text())
        candidate["commit"] = self.commit
        (self.assets / "candidate.json").write_text(json.dumps(candidate))
        (self.assets / "convertibled-installer.tar.gz").write_bytes(b"reviewed bootstrap")
        self.trust = canonical({"roots": self.fixture.roots, "keyring_url": "https://raw.githubusercontent.com/owner/project/main/release/keyring.json",
                                "channels": {"stable": "https://raw.githubusercontent.com/owner/project/update-channels/stable.json"}})
        self.calls = []
        self.public_failure = self.conflict = False
        self.old = dict(self.fixture.payload, sequence=1)

    def gh(self, *args):
        self.calls.append(args)
        endpoint = args[-1]
        if args[:2] == ("release", "download"):
            destination = Path(args[-1])
            for path in self.assets.iterdir():
                if path.suffix != ".pem":
                    shutil.copyfile(path, destination / path.name)
            return ""
        if args[:2] == ("release", "edit"):
            return ""
        if "--input" in args:
            self.request = json.loads(Path(args[-1]).read_text())
            if self.conflict:
                raise subprocess.CalledProcessError(1, args)
            return "{}"
        if "/releases/tags/" in endpoint:
            return json.dumps({"prerelease": False, "draft": True})
        if "/git/ref/" in endpoint:
            return json.dumps({"object": {"sha": "branch-head"}})
        if "/git/trees/" in endpoint:
            return json.dumps({"tree": [{"path": "stable.json", "sha": "original-blob"}]})
        if "/git/blobs/" in endpoint:
            return json.dumps({"content": base64.b64encode(canonical({"payload": self.old})).decode()})
        self.fail(f"Unexpected gh operation {args}")

    def run_command(self, args, **kwargs):
        if "scripts/release/bootstrap.py" in args:
            Path(args[-1]).write_bytes(b"reviewed bootstrap")

    def fetch(self, address, **kwargs):
        self.calls.append(("fetch", address))
        if address.endswith("keyring.json"):
            return self.fixture.ring
        if self.public_failure:
            raise UpdateError("Public artifact unavailable")

    def invoke(self):
        original_read = Path.read_bytes
        trust = self.trust
        def read(path):
            return trust if path == Path("release/trust.json") else original_read(path)
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/project"}), patch("sys.argv", ["publish", "--version", "1.0.0", "--channel", "stable"]), \
             patch.object(publish, "gh", self.gh), patch.object(publish, "fetch", self.fetch), \
             patch.object(publish, "subprocess", types.SimpleNamespace(check_output=lambda *a, **k: self.commit + "\n", run=self.run_command)), \
             patch.object(Path, "read_bytes", read):
            publish.main()

    def test_public_bytes_checked_before_atomic_compare_and_swap(self):
        self.invoke()
        self.assertEqual(self.request["sha"], "original-blob")
        self.assertEqual(self.request["branch"], "update-channels")
        self.assertEqual(self.calls[-2][0], "fetch")
        self.assertIn("--input", self.calls[-1])

    def test_public_download_failure_preserves_channel(self):
        self.public_failure = True
        with self.assertRaises(UpdateError):
            self.invoke()
        self.assertFalse(any("--input" in call for call in self.calls))

    def test_concurrent_promotion_fails_without_retry(self):
        self.conflict = True
        with self.assertRaises(subprocess.CalledProcessError):
            self.invoke()
        self.assertEqual(sum("--input" in call for call in self.calls), 1)

    def test_newer_channel_blocks_publication(self):
        self.old["sequence"] = 99
        with self.assertRaises(UpdateError):
            self.invoke()
        self.assertFalse(any(call[:2] == ("release", "edit") for call in self.calls))
