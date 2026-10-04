"""Real cache/GTK lookup regression in disposable theme directories only."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock
from .desktop_cache import refresh_icons, TOOL, THEME
from .storage import Layout
from updater.model import UpdateError

ROOT = Path(__file__).resolve().parents[1]
INDEX = Path("/usr/share/icons/hicolor/index.theme")


def gtk4_available():
    if os.name != "posix" or not Path(TOOL).is_file() or not INDEX.is_file():
        return False
    try:
        result = subprocess.run(
            ["python3", "-c", "import gi;gi.require_version('Gtk','4.0');from gi.repository import Gtk"],
            capture_output=True, timeout=15, check=False)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


class DesktopCacheTests(unittest.TestCase):
    def test_command_is_fixed_and_private_umask_is_restored_on_failure(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            seen = []
            def fail(args):
                seen.append(args)
                mask = os.umask(0o022)
                self.assertEqual(mask, 0o022)
                raise UpdateError("cache tool failed")
            original = os.umask(0o077)
            try:
                with self.assertRaisesRegex(UpdateError, "cache tool failed"):
                    refresh_icons(layout, fail)
                self.assertEqual(os.umask(0o077), 0o077)
            finally:
                os.umask(original)
            self.assertEqual(seen, [[TOOL, "--force", str(Path(root) / THEME)]])

    @unittest.skipUnless(os.name == "posix", "POSIX symlink refusal")
    def test_linked_cache_cannot_redirect_shared_index_write(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            theme = layout.root / THEME
            theme.mkdir(parents=True)
            foreign = Path(root) / "foreign"
            foreign.write_text("keep")
            (theme / "icon-theme.cache").symlink_to(foreign)
            run = Mock()
            with self.assertRaises(UpdateError):
                refresh_icons(layout, run)
            run.assert_not_called()
            self.assertEqual(foreign.read_text(), "keep")

    @unittest.skipUnless(os.name == "posix" and Path(TOOL).is_file() and INDEX.is_file(), "Linux GTK icon cache utility and hicolor index")
    def test_real_cache_install_rollback_and_remove_preserve_other_icons(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            theme = layout.root / THEME
            icons = theme / "scalable/apps"
            icons.mkdir(parents=True)
            shutil.copyfile(INDEX, theme / "index.theme")
            source = ROOT / "data/icons/org.convertibled.Settings.svg"
            foreign = icons / "unrelated-application.svg"
            shutil.copyfile(source, foreign)
            refresh_icons(layout)
            own = icons / "org.convertibled.Settings.svg"
            shutil.copyfile(source, own)
            cache = theme / "icon-theme.cache"
            self.assertNotIn(b"org.convertibled.Settings", cache.read_bytes())
            original = os.umask(0o077)
            try:
                refresh_icons(layout)
                self.assertEqual(os.umask(0o077), 0o077)
            finally:
                os.umask(original)
            self.assertIn(b"org.convertibled.Settings", cache.read_bytes())
            self.assertEqual(cache.stat().st_mode & 0o777, 0o644)
            # Force also handles retained icon paths whose selected bytes change.
            own.write_text(source.read_text().replace("#3584e4", "#ffffff"))
            refresh_icons(layout)
            self.assertIn(b"unrelated-application", cache.read_bytes())
            own.unlink()
            refresh_icons(layout)
            self.assertNotIn(b"org.convertibled.Settings", cache.read_bytes())
            self.assertIn(b"unrelated-application", cache.read_bytes())
            self.assertEqual(foreign.read_bytes(), source.read_bytes())

    @unittest.skipUnless(gtk4_available(), "Linux GTK4 typelib/PyGObject, cache utility and hicolor index")
    def test_stale_index_hides_existing_svg_until_forced_refresh(self):
        with tempfile.TemporaryDirectory() as root:
            layout = Layout(root)
            theme = layout.root / THEME
            icons = theme / "scalable/apps"
            icons.mkdir(parents=True)
            shutil.copyfile(INDEX, theme / "index.theme")
            source = ROOT / "data/icons/org.convertibled.Settings.svg"
            shutil.copyfile(source, icons / "unrelated-application.svg")
            refresh_icons(layout)
            shutil.copyfile(source, icons / "org.convertibled.Settings.svg")
            # Deep additions do not invalidate the theme-root timestamp.
            os.utime(theme, (1, 1))
            probe = "import gi,sys;gi.require_version('Gtk','4.0');from gi.repository import Gtk;t=Gtk.IconTheme.new();t.set_search_path([sys.argv[1]]);t.set_theme_name('hicolor');print(t.has_icon('org.convertibled.Settings'))"
            def available():
                return subprocess.run(["python3", "-c", probe, str(theme.parent)], capture_output=True, text=True, timeout=15, check=True).stdout.strip()
            self.assertEqual(available(), "False")
            refresh_icons(layout)
            self.assertEqual(available(), "True")
