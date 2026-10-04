import unittest
import io
import tarfile
import tempfile
from pathlib import Path
from .archive import safe_name, manifest, extract
from .model import UpdateError


class ArchiveTests(unittest.TestCase):
    def test_paths(self):
        for name in ("../etc/passwd", "/etc/passwd", "bin//x", "bin/./x", "C:/x", "bin\\x", "bin/../../x"):
            with self.assertRaises(UpdateError, msg=name):
                safe_name(name)
        self.assertEqual(str(safe_name("bin/convertibled")), "bin/convertibled")

    def test_incomplete_product_denied(self):
        with self.assertRaises(UpdateError):
            manifest({"schema": 1, "version": "0.1.0", "files": {}})

    def hostile(self, entries):
        with tempfile.TemporaryDirectory() as root:
            archive = Path(root) / "bad.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                for entry in entries:
                    bundle.addfile(entry, io.BytesIO(b"x" * entry.size) if entry.isfile() else None)
            with self.assertRaises(UpdateError):
                extract(archive, Path(root) / "candidate", "0.1.0")
            self.assertFalse((Path(root) / "candidate").exists())

    def test_actual_link_archive_rejected(self):
        entry = tarfile.TarInfo("bin/link")
        entry.type, entry.linkname = tarfile.SYMTYPE, "/etc/passwd"
        self.hostile([entry])

    def test_duplicate_actual_entries_rejected(self):
        entry = tarfile.TarInfo("bin/file")
        entry.size = 1
        self.hostile([entry, entry])

    def test_actual_traversal_archive_rejected(self):
        self.hostile([tarfile.TarInfo("../outside")])
