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
        self.identical = self.refresh = False
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
            return json.dumps({"prerelease": False, "draft": not self.refresh})
        if "/git/ref/" in endpoint:
            return json.dumps({"object": {"sha": "branch-head"}})
        if "/git/trees/" in endpoint:
            return json.dumps({"tree": [{"path": "stable.json", "sha": "original-blob"}]})
        if "/git/blobs/" in endpoint:
            content = (self.assets / "stable.json").read_bytes() if self.identical else canonical({"payload": self.old})
            return json.dumps({"content": base64.b64encode(content).decode()})
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
        argv = ["publish", "--version", "1.0.0", "--channel", "stable"]
        if self.refresh:
            argv += ["--refresh-prepared", str(self.assets)]
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/project"}), patch("sys.argv", argv), \
             patch.object(publish, "gh", self.gh), patch.object(publish, "fetch", self.fetch), \
             patch.object(publish, "subprocess", types.SimpleNamespace(check_output=lambda *a, **k: self.commit + "\n", run=self.run_command)), \
             patch.object(Path, "read_bytes", read):
            publish.main()

    def test_public_bytes_checked_before_atomic_compare_and_swap(self):
        self.invoke()
        self.assertEqual(self.request["sha"], "original-blob")
        self.assertEqual(self.request["branch"], "update-channels")
        self.assertEqual(self.calls[-3][0], "fetch")
        self.assertIn("--input", self.calls[-2])
        self.assertEqual(self.calls[-1], ("release", "edit", "v1.0.0", "--latest=true"))

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

    def test_identical_channel_is_verified_noop(self):
        self.identical = True
        self.invoke()
        self.assertFalse(any("--input" in call for call in self.calls))
        self.assertTrue(any(call[0] == "fetch" and call[1].endswith(".tar.gz") for call in self.calls))

    def test_metadata_refresh_does_not_modify_release_assets(self):
        self.refresh = True
        self.invoke()
        self.assertFalse(any(call[:2] == ("release", "upload") for call in self.calls))
        self.assertFalse(any("--draft=false" in call for call in self.calls))

    def test_refresh_rejects_signature_from_revoked_key(self):
        self.refresh = True
        from release.keyring import create
        ring = create({"next-release": self.fixture.keys["release"]}, 2, 90,
                      self.assets / "root.pem", "root", self.fixture.roots, self.fixture.now)
        (self.assets / "keyring.json").write_bytes(ring)
        with self.assertRaises(UpdateError):
            self.invoke()
        self.assertFalse(any("--input" in call for call in self.calls))
