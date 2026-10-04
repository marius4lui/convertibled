"""Exercise the real XDG generator without writing the host's autostart state."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

GENERATOR = Path("/usr/lib/systemd/user-generators/systemd-xdg-autostart-generator")
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "posix" and GENERATOR.is_file(), "Linux XDG autostart generator required")
class AutostartTests(unittest.TestCase):
    def test_onboarding_generates_an_actual_graphical_session_service(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config"
            (config / "autostart").mkdir(parents=True)
            shutil.copyfile(ROOT / "data/autostart/org.convertibled.Onboarding.desktop",
                            config / "autostart/org.convertibled.Onboarding.desktop")
            outputs = [root / name for name in ("normal", "early", "late")]
            for output in outputs:
                output.mkdir()
            environment = dict(os.environ, HOME=str(root), XDG_CONFIG_HOME=str(config),
                               XDG_CONFIG_DIRS=str(root / "no-system-config"),
                               XDG_DATA_HOME=str(root / "data"), XDG_DATA_DIRS=str(root / "no-system-data"))
            subprocess.run([str(GENERATOR), *map(str, outputs)], env=environment,
                           capture_output=True, text=True, timeout=15, check=True)
            services = [p for output in outputs for p in output.glob("*convertibled*.service")]
            self.assertEqual(len(services), 1, "Onboarding must not be silently skipped by XDG generation")
            content = services[0].read_text()
            self.assertIn("/opt/convertibled/current/installer/onboarding.py", content)
            self.assertIn("graphical-session.target", content)
