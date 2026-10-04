import unittest
from .transport import url
from .model import UpdateError


class TransportTests(unittest.TestCase):
    def test_denied_urls(self):
        for value in ("http://github.com/a", "file:///etc/passwd", "https://github.com.evil/a", "https://u:p@github.com/a", "https://github.com:8443/a", "https://127.0.0.1/a"):
            with self.assertRaises(UpdateError, msg=value):
                url(value)

    def test_release_host(self):
        self.assertEqual(url("https://github.com/a/b/releases/download/v1/a.tar.gz"), "https://github.com/a/b/releases/download/v1/a.tar.gz")
