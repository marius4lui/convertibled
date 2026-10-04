"""Refresh only the fixed shared icon index after owned integration changes."""
import os
from .platform import command
from .storage import sync_directory
from updater.model import UpdateError

TOOL = "/usr/bin/gtk-update-icon-cache"
THEME = "usr/share/icons/hicolor"


def refresh_icons(layout, run=command):
    theme = layout.root / THEME
    cache = theme / "icon-theme.cache"
    if theme.is_symlink() or cache.is_symlink() or (cache.exists() and not cache.is_file()):
        raise UpdateError("Refusing redirected icon cache")
    # The updater's 0077 umask must not create a private system-wide icon cache.
    # --force also covers rollback/current-link changes invisible to directory mtimes.
    previous = os.umask(0o022)
    try:
        run([TOOL, "--force", str(theme)])
    finally:
        os.umask(previous)
    if cache.exists():
        if cache.is_symlink() or not cache.is_file():
            raise UpdateError("Icon cache changed type during refresh")
        cache.chmod(0o644)
        sync_directory(theme)
