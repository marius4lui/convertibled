"""Full real-signature preparation in disposable directories, no host changes."""
import datetime as dt
import hashlib
import shutil
import unittest
from pathlib import Path
from . import test_crypto
from .manager import Manager
from .offline import Offline
from .model import canonical, UpdateError
from installer.storage import Layout, atomic, read
from scripts.release.bundle import build


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL unavailable")
class PipelineTests(unittest.TestCase):
    setUp = test_crypto.CryptoTests.setUp
    tearDown = test_crypto.CryptoTests.tearDown
    signed = test_crypto.CryptoTests.signed
    def setup_release(self, version="0.1.0", sequence=1):
        self.layout = Layout(self.directory / "host")
        self.layout.initialize()
        self.incoming = self.layout.state / "offline"
        self.incoming.mkdir(exist_ok=True)
        files = {"bin/" + name: (b"\x7fELFtest", True) for name in ("convertibled", "convertibled-session", "convertiblectl", "convertibled-settings")}
        artifact = self.incoming / "artifact.tar.gz"
        artifact.unlink(missing_ok=True)
        build(files, version, artifact)
        now = dt.datetime.now(dt.timezone.utc)
        self.metadata = {"schema": 1, "version": version, "sequence": sequence, "channel": "stable", "platform": {"os": "fedora", "version": "44", "architecture": "x86_64", "desktop": "GNOME", "desktop_version": "50", "session": "wayland"}, "issued": (now - dt.timedelta(minutes=1)).isoformat(), "expires": (now + dt.timedelta(days=1)).isoformat(), "artifact": {"url": "https://github.com/project/releases/artifact", "size": artifact.stat().st_size, "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}, "config_schema": 1, "notes": "Fixture only"}
        ring = {"schema": 1, "sequence": 1, "issued": self.metadata["issued"], "expires": self.metadata["expires"], "keys": {"release": self.public}}
        atomic(self.layout.config / "trust.json", {"schema": 1, "roots": {"root": self.public}, "keyring_url": "https://github.com/project/keyring", "channels": {"stable": "https://github.com/project/stable", "preview": "https://github.com/project/preview"}})
        (self.incoming / "keyring.json").write_bytes(canonical(self.signed(ring, "root")))
        self.write_metadata()
        self.manager = Manager(self.layout, network=Offline(self.layout), platform_check=lambda *_: None)

    def write_metadata(self):
        (self.incoming / "channel.json").write_bytes(canonical(self.signed(self.metadata)))

    def test_real_signed_bundle_prepare_and_idempotence(self):
        self.setup_release()
        self.manager.prepare()
        self.assertTrue((self.layout.versions / "0.1.0/bin/convertibled").exists())
        self.assertEqual(self.manager.activation_ready(), "0.1.0")
        self.manager.prepare()
        self.assertEqual(read(self.layout.state / "accepted.json")["channels"]["stable"]["sequence"], 1)

    def test_corrupted_artifact_never_installed(self):
        self.setup_release()
        (self.incoming / "artifact.tar.gz").write_bytes(b"corrupt")
        with self.assertRaises(UpdateError):
            self.manager.prepare()
        self.assertFalse((self.layout.versions / "0.1.0").exists())

    def test_newly_signed_downgrade_denied(self):
        self.setup_release("0.2.0", 1)
        self.manager.check()
        self.metadata.update(version="0.1.0", sequence=2)
        self.write_metadata()
        with self.assertRaises(UpdateError):
            self.manager.check()

    def test_wrong_architecture_and_expiry_denied(self):
        self.setup_release()
        self.metadata["platform"]["architecture"] = "aarch64"
        self.write_metadata()
        with self.assertRaises(UpdateError):
            self.manager.check()
        self.metadata["platform"]["architecture"] = "x86_64"
        self.metadata["expires"] = self.metadata["issued"]
        self.write_metadata()
        with self.assertRaises(UpdateError):
            self.manager.check()

    def test_replay_rejected_after_accepting_later_sequence(self):
        self.setup_release()
        self.manager.check()
        old = (self.incoming / "channel.json").read_bytes()
        self.metadata["sequence"] = 2
        self.write_metadata()
        self.manager.check()
        (self.incoming / "channel.json").write_bytes(old)
        with self.assertRaises(UpdateError):
            self.manager.check()
