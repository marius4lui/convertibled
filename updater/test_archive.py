import unittest
from .archive import safe_name, manifest
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
