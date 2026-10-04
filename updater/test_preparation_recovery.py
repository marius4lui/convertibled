"""Real SIGKILL leaves staging for journal-owned recovery, never foreign deletion."""
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from . import test_pipeline
from .preparation import cleanup, Workspace
from .model import UpdateError
from installer.storage import atomic, read


@unittest.skipUnless(os.name == "posix" and shutil.which("openssl"), "Requires POSIX SIGKILL and OpenSSL")
class PreparationRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_pipeline.PipelineTests("test_real_signed_bundle_prepare_and_idempotence")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.setup_release()
        self.layout = self.fixture.layout

    def interrupt(self, published=False, downloading=False):
        script = '''
import os, signal, sys
from pathlib import Path
from unittest.mock import patch
from installer.storage import Layout
from updater.manager import Manager
from updater.offline import Offline
from updater.archive import extract
layout = Layout(Path(sys.argv[1]))
original_replace = os.replace
offline = Offline(layout)
def killed_download(address, **kwargs):
    if kwargs.get("target") is not None:
        kwargs["target"].write(b"partial network bytes")
        kwargs["target"].flush()
        os.fsync(kwargs["target"].fileno())
        os.kill(os.getpid(), signal.SIGKILL)
    return offline(address, **kwargs)
def killed_extract(*args):
    result = extract(*args)
    path = Path(args[1]) / "bin/convertibled"
    with path.open("r+b") as stream:
        stream.truncate(3)
        stream.flush()
        os.fsync(stream.fileno())
    os.kill(os.getpid(), signal.SIGKILL)
def killed_publish(source, target):
    result = original_replace(source, target)
    if Path(target) == layout.versions / "0.1.0":
        os.kill(os.getpid(), signal.SIGKILL)
    return result
target = "updater.manager.os.replace" if sys.argv[2] == "published" else "updater.manager.extract"
with patch(target, side_effect=killed_publish if sys.argv[2] == "published" else killed_extract):
    Manager(layout, network=killed_download if sys.argv[2] == "download" else offline, platform_check=lambda *_: None).prepare()
'''
        result = subprocess.run([sys.executable, "-c", script, str(self.layout.root), "download" if downloading else "published" if published else "partial"], capture_output=True, timeout=30)
        self.assertEqual(result.returncode, -9, result.stderr.decode())
        self.journal = read(self.layout.state / "preparation.json")
        token = self.journal["token"]
        self.preparation = self.layout.versions / (".prepare-" + token)
        self.download = self.layout.state / "staging" / (".download-" + token)
        self.candidate = self.preparation / "candidate"

    def test_next_prepare_recovers_sigkill_partial_extraction(self):
        self.interrupt()
        self.assertEqual((self.candidate / "bin/convertibled").stat().st_size, 3)
        self.fixture.manager.prepare()
        self.assertEqual((self.layout.versions / "0.1.0/bin/convertibled").read_bytes(), b"\x7fELFtest")
        self.assertFalse((self.layout.state / "preparation.json").exists())
        self.assertFalse(self.download.exists())
        self.assertFalse(self.preparation.exists())

    def test_sigkill_after_publish_keeps_installed_bytes_and_cleans_journal(self):
        self.interrupt(published=True)
        self.fixture.manager.prepare()
        self.assertTrue((self.layout.versions / "0.1.0/bin/convertibled").is_file())
        self.assertFalse(self.preparation.exists())
        self.assertFalse((self.layout.state / "preparation.json").exists())

    def test_partial_download_sigkill_recovers_without_candidate(self):
        self.interrupt(downloading=True)
        self.assertFalse(self.candidate.exists())
        self.fixture.manager.prepare()
        self.assertFalse(self.download.exists())
        self.assertFalse(self.preparation.exists())
        self.assertTrue((self.layout.versions / "0.1.0").is_dir())

    def test_cleanup_precedes_low_space_preflight(self):
        self.interrupt()
        def no_space(*_):
            self.assertFalse(self.preparation.exists())
            self.assertFalse(self.download.exists())
            raise UpdateError("Insufficient disk space")
        self.fixture.manager.platform_check = no_space
        with self.assertRaisesRegex(UpdateError, "Insufficient disk"):
            self.fixture.manager.prepare()
        self.assertFalse((self.layout.state / "preparation.json").exists())

    def test_cleanup_does_not_require_available_channel(self):
        self.interrupt()
        def unavailable(*_, **__):
            self.assertFalse(self.preparation.exists())
            self.assertFalse(self.download.exists())
            raise UpdateError("Channel unavailable")
        self.fixture.manager.network = unavailable
        with self.assertRaisesRegex(UpdateError, "Channel unavailable"):
            self.fixture.manager.prepare()

    def test_foreign_file_prevents_all_cleanup(self):
        self.interrupt()
        foreign = self.candidate / "foreign.txt"
        foreign.write_text("retain this file")
        with self.assertRaisesRegex(UpdateError, "Unowned"):
            cleanup(self.layout)
        self.assertEqual(foreign.read_text(), "retain this file")
        self.assertTrue((self.download / "artifact.tar.gz").exists())
        self.assertTrue((self.layout.state / "preparation.json").exists())

    def test_modified_partial_file_and_corrupt_archive_are_retained(self):
        self.interrupt()
        binary = self.candidate / "bin/convertibled"
        binary.write_bytes(b"bad")
        with self.assertRaisesRegex(UpdateError, "Modified"):
            cleanup(self.layout)
        binary.write_bytes(b"\x7fEL")
        (self.download / "artifact.tar.gz").write_bytes(b"corrupt")
        with self.assertRaisesRegex(UpdateError, "authenticated"):
            cleanup(self.layout)
        self.assertTrue(binary.exists())

    def test_replaced_directory_identity_is_retained(self):
        self.interrupt()
        self.preparation.rename(self.preparation.with_name("retained-original"))
        self.preparation.mkdir(mode=0o700)
        with self.assertRaisesRegex(UpdateError, "identity"):
            cleanup(self.layout)
        self.assertTrue(self.preparation.exists())

    def test_creation_gap_cleans_only_empty_unregistered_directory(self):
        self.fixture.manager.check()
        (self.layout.state / "staging").mkdir()
        workspace = Workspace(self.layout, self.fixture.metadata)
        workspace.__enter__()
        journal = read(self.layout.state / "preparation.json")
        del journal["preparation"]
        atomic(self.layout.state / "preparation.json", journal)
        foreign = workspace.preparation / "foreign"
        foreign.write_text("retain")
        with self.assertRaisesRegex(UpdateError, "Unregistered nonempty"):
            cleanup(self.layout)
        foreign.unlink()
        cleanup(self.layout)
        self.assertFalse(workspace.preparation.exists())
