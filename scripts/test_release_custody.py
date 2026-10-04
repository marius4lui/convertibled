"""Ephemeral encrypted keys and isolated protected-environment provisioning."""
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from release.sign import sign, ask_passphrase
from release.setup_keys import locations, upload, main
from updater.crypto import envelope
from updater.model import UpdateError, canonical


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL unavailable")
class CustodyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_encrypted_root_signs_without_exposing_password_in_arguments(self):
        key = self.directory / "encrypted.pem"
        password = b"ephemeral test password"
        subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-aes-256-cbc", "-pass", "stdin", "-out", str(key)],
                       input=password + b"\n", check=True, capture_output=True)
        public = subprocess.check_output(["openssl", "pkey", "-in", str(key), "-passin", "stdin", "-pubout"], input=password + b"\n").decode()
        self.assertEqual(envelope(canonical(sign({"proof": 1}, key, "root", password)), {"root": public}), {"proof": 1})
        with self.assertRaises(subprocess.CalledProcessError):
            sign({"proof": 1}, key, "root", b"wrong password")
        self.assertIn(b"ENCRYPTED PRIVATE KEY", key.read_bytes())

    def test_custody_locations_cannot_overlap_or_replace(self):
        a, b, output = (self.directory / name for name in ("offline", "online", "public"))
        self.assertEqual(locations(a, b, output), (a.resolve(), b.resolve(), output.resolve()))
        for online in (a, a / "child", self.directory):
            with self.assertRaises(UpdateError):
                locations(a, online, output)
        a.mkdir()
        with self.assertRaises(UpdateError):
            locations(a, b, output)

    def test_noninteractive_prompt_fails(self):
        with patch("sys.stdin.isatty", return_value=False), self.assertRaises(UpdateError):
            ask_passphrase()

    def test_upload_requires_reviewers_and_uses_only_release_key_stdin(self):
        release = self.directory / "release.pem"
        release.write_bytes(b"temporary release secret")
        with patch("subprocess.check_output", return_value=b'{"protection_rules":[]}'), patch("subprocess.run") as run:
            with self.assertRaises(UpdateError):
                upload("owner/project", release, "release-1")
            run.assert_not_called()
        with patch("subprocess.check_output", return_value=b'{"protection_rules":[{"type":"required_reviewers","reviewers":[{}]}]}'), patch("subprocess.run") as run:
            upload("owner/project", release, "release-1")
            self.assertEqual(run.call_args_list[0].kwargs["input"], b"temporary release secret")
            self.assertNotIn("temporary release secret", str(run.call_args_list[0].args))
            self.assertEqual(run.call_count, 2)

    @unittest.skipUnless(os.name == "posix", "Custody setup enforces Linux file permissions")
    def test_interactive_setup_real_encrypted_keys_public_only_export(self):
        offline, online, output = (self.directory / name for name in ("offline", "online", "public"))
        argv = ["setup", "--repository", "owner/project", "--offline-dir", str(offline), "--release-dir", str(online), "--output", str(output)]
        terminal = io.StringIO()
        with patch("sys.argv", argv), patch("sys.stdin.isatty", return_value=True), patch("getpass.getpass", return_value="ephemeral test password"), patch("sys.stdout", terminal):
            main()
        self.assertIn(b"ENCRYPTED PRIVATE KEY", (offline / "root.pem").read_bytes())
        self.assertEqual((offline / "root.pem").stat().st_mode & 0o777, 0o600)
        self.assertEqual((online / "release.pem").stat().st_mode & 0o777, 0o600)
        self.assertEqual(offline.stat().st_mode & 0o777, 0o700)
        self.assertNotIn("ephemeral test password", terminal.getvalue())
        self.assertNotIn("PRIVATE KEY", terminal.getvalue())
