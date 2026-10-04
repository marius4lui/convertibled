import contextlib
import tempfile
import unittest
from argparse import Namespace
from unittest.mock import patch, Mock
from .storage import Layout
from . import cli


class SchedulerRecoveryTests(unittest.TestCase):
    def test_pending_recovery_precedes_graphical_session_branch(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            layout.initialize()
            (layout.state / "admission.pending").touch()
            transaction = Mock()
            transaction.recover.return_value = {"phase": "rolled_back"}
            with patch.object(layout, "lock", return_value=contextlib.nullcontext()), patch("installer.cli.os.name", "posix"), patch("installer.cli.os.geteuid", return_value=0, create=True), patch("installer.cli.Manager"), patch("installer.cli.Transaction", return_value=transaction), patch("installer.cli.graphical_sessions", return_value=[{"user": "1000"}]), patch("installer.cli.preferences", return_value={"automatic_updates": False}), patch("installer.cli.publish", return_value={}):
                cli.execute(Namespace(command="scheduled", value=None), layout)
            self.assertEqual(transaction.method_calls[:2], [("recover", (), {}), ("observe_login", (), {})])
