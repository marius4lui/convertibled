"""Verified preparation across real mounts and safe failure/collision cleanup."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import test_pipeline
from .model import UpdateError
from installer.storage import read


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL unavailable")
class PreparationStorageTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_pipeline.PipelineTests("test_real_signed_bundle_prepare_and_idempotence")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.setup_release()
        self.layout = self.fixture.layout

    def test_preparation_publishes_from_versions_filesystem_and_preserves_foreign_staging(self):
        staging = self.layout.state / "staging"
        staging.mkdir()
        foreign = staging / "candidate"
        foreign.mkdir()
        (foreign / "keep").write_text("foreign")
        original = os.replace
        publications = []
        def replace(source, target):
            if Path(target) == self.layout.versions / "0.1.0":
                publications.append(Path(source))
                self.assertEqual(Path(source).parent.parent, self.layout.versions)
            return original(source, target)
        with patch("updater.manager.os.replace", side_effect=replace):
            self.fixture.manager.prepare()
        self.assertEqual(len(publications), 1)
        self.assertEqual((foreign / "keep").read_text(), "foreign")
        self.assertEqual([p.name for p in self.layout.versions.iterdir()], ["0.1.0"])
        self.assertEqual(list(staging.iterdir()), [foreign])

    @unittest.skipUnless(os.name == "posix" and Path("/dev/shm").is_dir(), "Requires POSIX tmpfs")
    def test_real_cross_filesystem_state_and_versions(self):
        with tempfile.TemporaryDirectory(prefix="convertibled-crossfs-", dir="/dev/shm") as temporary:
            versions = Path(temporary) / "versions"
            versions.mkdir()
            if versions.stat().st_dev == self.layout.state.stat().st_dev:
                self.skipTest("State and tmpfs share a device")
            self.layout.versions = versions
            self.fixture.manager.prepare()
            self.assertTrue((versions / "0.1.0/bin/convertibled").is_file())
            self.assertEqual(read(self.layout.state / "prepared.json")["version"], "0.1.0")
            self.assertEqual([p.name for p in versions.iterdir()], ["0.1.0"])

    @unittest.skipUnless(os.name == "posix", "Requires symlink support")
    def test_failure_preserves_active_version_and_cleans_only_own_temporary_files(self):
        previous = self.layout.versions / "0.0.9"
        previous.mkdir()
        (previous / "keep").write_text("active bytes")
        self.layout.select("0.0.9")
        (self.fixture.incoming / "artifact.tar.gz").write_bytes(b"corrupt")
        with self.assertRaises(UpdateError):
            self.fixture.manager.prepare()
        self.assertEqual(self.layout.active(), "0.0.9")
        self.assertEqual((previous / "keep").read_text(), "active bytes")
        self.assertEqual(list(self.layout.versions.iterdir()), [previous])
        self.assertEqual(list((self.layout.state / "staging").iterdir()), [])

    @unittest.skipUnless(os.name == "posix", "Requires symlink support")
    def test_symlink_and_late_collision_are_not_replaced(self):
        destination = self.layout.versions / "0.1.0"
        destination.symlink_to(self.fixture.directory / "absent", target_is_directory=True)
        with self.assertRaises(UpdateError):
            self.fixture.manager.prepare()
        self.assertTrue(destination.is_symlink())
        destination.unlink()
        from .archive import extract
        def competing_extract(*args):
            result = extract(*args)
            destination.mkdir()
            (destination / "foreign").write_text("retain")
            return result
        with patch("updater.manager.extract", side_effect=competing_extract), self.assertRaises(UpdateError):
            self.fixture.manager.prepare()
        self.assertEqual((destination / "foreign").read_text(), "retain")
        self.assertEqual(list(self.layout.versions.iterdir()), [destination])

    @unittest.skipUnless(os.name == "posix", "Requires POSIX permissions")
    def test_writable_version_storage_is_rejected_before_extraction(self):
        self.layout.versions.chmod(0o777)
        with self.assertRaisesRegex(UpdateError, "publicly writable"):
            self.fixture.manager.prepare()
        self.assertEqual(list(self.layout.versions.iterdir()), [])
