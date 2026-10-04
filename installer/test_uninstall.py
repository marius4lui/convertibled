import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import Mock
from .uninstall import owned_version, uninstall, stop_units
from .storage import Layout
from updater.model import UpdateError


class UninstallTests(unittest.TestCase):
    def test_absent_units_require_complete_inactive_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            run = Mock(return_value="LoadState=not-found\nActiveState=inactive\nFragmentPath=")
            stop_units(layout, run)
            self.assertEqual(run.call_count, 2)
            self.assertTrue(all(call.args[0][1] == "show" for call in run.call_args_list))
            with self.assertRaisesRegex(UpdateError, "bus unavailable"):
                stop_units(layout, Mock(side_effect=UpdateError("bus unavailable")))

    def test_ambiguous_or_present_failed_stop_remains_fatal(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            with self.assertRaisesRegex(UpdateError, "Ambiguous"):
                stop_units(layout, Mock(return_value="LoadState=not-found"))
            for state in ("LoadState=loaded\nActiveState=active\nFragmentPath=/usr/lib/systemd/system/convertibled-update.timer", "LoadState=not-found\nActiveState=active\nFragmentPath="):
                with self.assertRaisesRegex(UpdateError, "stop failed"):
                    stop_units(layout, Mock(side_effect=[state, UpdateError("stop failed")]))

    @unittest.skipUnless(os.name == "posix", "POSIX enable symlinks")
    def test_owned_aliases_removed_and_foreign_enable_link_retained(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            directory = layout.root / "etc/systemd/system"
            alias = directory / "convertibled.service"
            enable = directory / "multi-user.target.wants/convertibled.service"
            enable.parent.mkdir(parents=True)
            target = layout.versions / "0.1.0/data/systemd/convertibled.service"
            alias.symlink_to(target)
            enable.symlink_to(target)
            run = Mock(return_value="LoadState=not-found\nActiveState=inactive\nFragmentPath=")
            stop_units(layout, run, ["0.1.0"])
            self.assertFalse(alias.is_symlink())
            self.assertFalse(enable.is_symlink())
            enable.symlink_to("/user/changed.service")
            run.reset_mock()
            with self.assertRaisesRegex(UpdateError, "User-modified"):
                stop_units(layout, run, ["0.1.0"])
            self.assertTrue(enable.is_symlink())
            run.assert_not_called()

    def test_session_blocks_before_service_stop(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            calls = []
            with self.assertRaises(UpdateError):
                uninstall(layout, run=calls.append, sessions=lambda: [{"type": "wayland"}])
            self.assertEqual(calls, [])

    def test_unowned_directory_retained(self):
        with tempfile.TemporaryDirectory() as root:
            candidate = Path(root) / "0.1.0"
            candidate.mkdir()
            (candidate / "user.txt").write_text("retain")
            with self.assertRaises(UpdateError):
                owned_version(candidate)
            self.assertTrue((candidate / "user.txt").exists())
