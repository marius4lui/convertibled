import unittest
import io
import tarfile
import tempfile
import os
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

    @unittest.skipUnless(os.name == "posix", "Unix service-account permissions")
    def test_private_service_umask_produces_readable_durable_product_tree(self):
        from scripts.release.bundle import build
        files = {"bin/" + name: (b"executable", True) for name in
                 ("convertibled", "convertibled-session", "convertiblectl", "convertibled-settings")}
        files["share/gnome-shell/extensions/project/extension.js"] = (b"public code", False)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive, destination = root / "bundle.tar.gz", root / "candidate"
            build(files, "0.1.0", archive)
            previous = os.umask(0o077)
            try:
                extract(archive, destination, "0.1.0")
            finally:
                os.umask(previous)
            for directory in [destination] + [path for path in destination.rglob("*") if path.is_dir()]:
                self.assertEqual(directory.stat().st_mode & 0o777, 0o755)
            for name, (_, executable) in files.items():
                self.assertEqual((destination / name).stat().st_mode & 0o777, 0o755 if executable else 0o644)
            self.assertEqual((destination / "manifest.json").stat().st_mode & 0o777, 0o644)
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)
