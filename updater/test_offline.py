import io
import tempfile
import unittest
from pathlib import Path
from .offline import Offline
from .model import UpdateError


class OfflineTests(unittest.TestCase):
    def test_corruption_denied(self):
        with tempfile.TemporaryDirectory() as root:
            offline = Offline.__new__(Offline)
            offline.directory = Path(root)
            offline.mapping = {}
            (Path(root) / "artifact.tar.gz").write_bytes(b"damaged")
            with self.assertRaises(UpdateError):
                offline("https://github.com/a", target=io.BytesIO(), maximum=7, expected_size=7, expected_hash="0" * 64)

    def test_unknown_metadata_denied(self):
        offline = Offline.__new__(Offline)
        offline.mapping = {}
        with self.assertRaises(UpdateError):
            offline("https://github.com/unknown")
