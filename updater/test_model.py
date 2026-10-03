import datetime as dt
import unittest
from .model import UpdateError, canonical, decode, release, timestamp, version


class MetadataTests(unittest.TestCase):
    def test_canonical_stable(self):
        self.assertEqual(canonical({"b": 1, "a": 2}), b'{"a":2,"b":1}')

    def test_duplicate_keys_denied(self):
        with self.assertRaises(UpdateError):
            decode(b'{"a":1,"a":2}')

    def test_unsafe_versions_denied(self):
        for value in ("../1", "01.0.0", "1.2", "1.0.0;id", "1.0.0-beta.0"):
            with self.assertRaises(UpdateError):
                version(value)

    def test_utc_required(self):
        with self.assertRaises(UpdateError):
            timestamp("2026-10-03T00:00:00")

    def test_invalid_contract(self):
        with self.assertRaises(UpdateError):
            release({}, "stable", dt.datetime.now(dt.timezone.utc))


if __name__ == "__main__":
    unittest.main()
