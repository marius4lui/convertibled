"""Real ephemeral offline-root/release signing and publication preflight tests."""
import datetime as dt
import hashlib
import shutil
import subprocess
import tempfile
import tarfile
import unittest
from pathlib import Path
from release.keyring import create
from release.sign import sign
from release.verify import verify
from release.bootstrap import build
from updater.model import UpdateError, canonical


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL unavailable")
class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.now = dt.datetime.now(dt.timezone.utc)
        self.keys = {}
        for identifier in ("root", "release"):
            private = self.directory / f"{identifier}.pem"
            subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(private)], check=True, capture_output=True)
            self.keys[identifier] = subprocess.check_output(["openssl", "pkey", "-in", str(private), "-pubout"], text=True)
        self.roots = {"root": self.keys["root"]}
        self.ring = create({"release": self.keys["release"]}, 1, 90, self.directory / "root.pem", "root", self.roots, self.now)
        (self.directory / "keyring.json").write_bytes(self.ring)
        artifact = b"accepted candidate"
        (self.directory / "convertibled-fedora44-x86_64.tar.gz").write_bytes(artifact)
        digest = hashlib.sha256(artifact).hexdigest()
        self.payload = {"schema": 1, "version": "1.0.0", "sequence": 2, "channel": "stable",
                        "platform": {"os": "fedora", "version": "44", "architecture": "x86_64", "desktop": "GNOME", "desktop_version": "50", "session": "wayland"},
                        "issued": self.now.isoformat(), "expires": (self.now + dt.timedelta(days=14)).isoformat(),
                        "artifact": {"url": "https://github.com/owner/project/releases/download/v1.0.0/convertibled-fedora44-x86_64.tar.gz", "size": len(artifact), "sha256": digest}, "config_schema": 1, "notes": "accepted"}
        (self.directory / "candidate.json").write_bytes(canonical({"version": "1.0.0", "artifact_sha256": digest}))
        self.resign()

    def resign(self):
        (self.directory / "stable.json").write_bytes(canonical(sign(self.payload, self.directory / "release.pem", "release")))

    def check(self, previous=None, now=None):
        return verify(self.directory, self.roots, "stable", "owner/project", now or self.now, previous)

    def test_verified_release(self):
        self.assertEqual(self.check()["version"], "1.0.0")

    def test_wrong_key_and_expired_metadata(self):
        with self.assertRaises(UpdateError):
            create({"release": self.keys["release"]}, 1, 90, self.directory / "release.pem", "root", self.roots, self.now)
        with self.assertRaises(UpdateError):
            self.check(now=self.now + dt.timedelta(days=15))

    def test_root_release_separation(self):
        with self.assertRaises(UpdateError):
            create({"release": self.keys["root"]}, 1, 90, self.directory / "root.pem", "root", self.roots, self.now)
        with self.assertRaises(UpdateError):
            create({"release": "\n" + self.keys["root"] + "\n"}, 1, 90, self.directory / "root.pem", "root", self.roots, self.now)

    def test_bootstrap_exact_source_deterministic_no_overwrite(self):
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        trust = canonical({"schema": 1, "roots": self.roots,
                           "keyring_url": "https://github.com/owner/project/releases/download/trust/keyring.json",
                           "channels": {name: f"https://github.com/owner/project/releases/download/channels/{name}.json" for name in ("stable", "preview")}})
        first, second = self.directory / "first.tar.gz", self.directory / "second.tar.gz"
        build(commit, trust, first)
        build(commit, trust, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with tarfile.open(first) as archive:
            self.assertEqual(archive.extractfile("installer/bootstrap-trust.json").read(), trust)
            self.assertEqual(archive.extractfile("installer/install").read(), subprocess.check_output(["git", "show", f"{commit}:installer/install"]))
            self.assertFalse(any(name.endswith(".pem") for name in archive.getnames()))
        with self.assertRaises(FileExistsError):
            build(commit, trust, first)
        with self.assertRaises(UpdateError):
            build(commit, canonical({"schema": 1}), self.directory / "invalid.tar.gz")

    def test_corrupt_artifact(self):
        (self.directory / "convertibled-fedora44-x86_64.tar.gz").write_bytes(b"corrupt")
        with self.assertRaises(UpdateError):
            self.check()

    def test_wrong_repository_and_replay(self):
        with self.assertRaises(UpdateError):
            verify(self.directory, self.roots, "stable", "wrong/project", self.now)
        with self.assertRaises(UpdateError):
            self.check(canonical({"payload": self.payload}))

    def test_monotonic_promotion(self):
        old = dict(self.payload, sequence=1)
        self.assertEqual(self.check(canonical({"payload": old}))["sequence"], 2)
        old["version"] = "2.0.0"
        with self.assertRaises(UpdateError):
            self.check(canonical({"payload": old}))

    def test_identical_envelope_is_safe_noop_but_changed_payload_is_not(self):
        previous = (self.directory / "stable.json").read_bytes()
        self.assertEqual(self.check(previous)["sequence"], 2)
        self.payload["notes"] = "different content, same sequence"
        self.resign()
        with self.assertRaises(UpdateError):
            self.check(previous)
