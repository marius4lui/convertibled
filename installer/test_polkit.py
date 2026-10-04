import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.release.bundle import qualify_policy
from .integration import refresh_policy
from .storage import Layout
from updater.model import UpdateError


class PolkitTests(unittest.TestCase):
    def test_signed_policy_names_canonical_versioned_program(self):
        template = (Path(__file__).resolve().parent.parent / "data/polkit/org.convertibled.installer.policy").read_bytes()
        policy = ET.fromstring(qualify_policy(template, "0.2.0-beta.1"))
        annotation = policy.find(".//annotate[@key='org.freedesktop.policykit.exec.path']")
        self.assertEqual(annotation.text, "/opt/convertibled/versions/0.2.0-beta.1/installer/cli.py")
        self.assertEqual(policy.find(".//allow_inactive").text, "no")

    def test_policy_cannot_encode_unsafe_version_or_arbitrary_helper(self):
        with self.assertRaises(UpdateError):
            qualify_policy(b"/opt/convertibled/current/installer/cli.py", "../unsafe")
        with self.assertRaises(UpdateError):
            qualify_policy(b"/usr/bin/python3", "0.1.0")

    @unittest.skipUnless(os.name == "posix", "POSIX inode/symlink refresh")
    def test_refresh_replaces_watched_policy_entry(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            target = Path(root) / "policy"
            target.symlink_to(layout.current / "data/polkit/policy")
            # Hold old inode open so the replacement cannot recycle its number.
            original = target.lstat().st_ino
            refresh_policy(layout, target, "data/polkit/policy")
            self.assertNotEqual(target.lstat().st_ino, original)
            self.assertEqual(target.readlink(), layout.current / "data/polkit/policy")
            self.assertFalse(target.with_name(".convertibled-next-policy").is_symlink())
