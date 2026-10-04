"""Offline ordering analysis; these fixtures do not run GNOME or accept GDM."""
import os
import shutil
import subprocess
import tempfile
import unittest
import configparser
from pathlib import Path


class SandboxTests(unittest.TestCase):
    def test_update_namespace_covers_every_owned_integration_destination(self):
        from .integration import LINKS
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(Path(__file__).resolve().parent.parent / "data/systemd/convertibled-update.service")
        writable = parser["Service"]["ReadWritePaths"].split()
        for destination in LINKS:
            path = "/" + destination
            self.assertTrue(any(path == root or path.startswith(root + "/") for root in writable), path)


@unittest.skipUnless(os.name == "posix" and shutil.which("systemd-analyze"), "Linux systemd unit analyzer")
class UnitGraphTests(unittest.TestCase):
    def test_supported_gnome_start_order_has_no_cycle(self):
        # Relevant GNOME 50 ordering from upstream data/org.gnome.Shell@.service.in
        # and gnome-session's session-manager/initialized/session targets. Exec
        # uses true solely so verification needs no installed GNOME executable.
        units = {
            "org.gnome.Shell@.service": "[Unit]\nAfter=gnome-session-manager.target\nRequisite=gnome-session-initialized.target\nPartOf=gnome-session-initialized.target\nBefore=gnome-session-initialized.target\n[Service]\nType=notify\nExecStart=/usr/bin/true\n",
            "gnome-session-manager.target": "[Unit]\nDefaultDependencies=no\nAfter=gnome-session-pre.target\nBefore=gnome-session-initialized.target\n",
            "gnome-session-pre.target": "[Unit]\nDefaultDependencies=no\nBefore=gnome-session-initialized.target\n",
            "gnome-session-initialized.target": "[Unit]\nDefaultDependencies=no\nRequires=gnome-session-pre.target\nAfter=gnome-session-pre.target\nBefore=gnome-session.target\n",
            "gnome-session.target": "[Unit]\nDefaultDependencies=no\nRequires=gnome-session-initialized.target\nAfter=gnome-session-initialized.target\nBefore=graphical-session.target\n",
            "graphical-session.target": "[Unit]\nDefaultDependencies=no\n",
        }
        repository = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in units.items():
                (root / name).write_text(content)
            (root / "org.gnome.Shell@user.service").symlink_to("org.gnome.Shell@.service")
            shutil.copyfile(repository / "data/systemd/convertibled-admission.service", root / "convertibled-admission.service")
            dropin = root / "org.gnome.Shell@user.service.d"
            dropin.mkdir()
            shutil.copyfile(repository / "data/systemd/org.gnome.Shell@user.service.d/convertibled-admission.conf", dropin / "convertibled-admission.conf")
            runtime = root / "runtime"
            runtime.mkdir(mode=0o700)
            environment = dict(os.environ, SYSTEMD_UNIT_PATH=str(root) + ":", XDG_RUNTIME_DIR=str(runtime))
            result = subprocess.run(["systemd-analyze", "--user", "verify", "--man=no", str(root / "org.gnome.Shell@user.service"), str(root / "convertibled-admission.service")], env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
