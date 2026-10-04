#!/usr/bin/python3 -I
"""Bootstrap only from an independently authenticated installer distribution."""
import argparse
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.dont_write_bytecode = True
from installer.configuration import set_preferences
from installer.storage import Layout, atomic
from updater.manager import Manager, trust
from updater.model import UpdateError


def provision_trust(layout, source):
    """Never replace administrator trust, even on repeated installation."""
    target = layout.config / "trust.json"
    if target.exists() or target.is_symlink():
        return trust(layout)
    source = Path(source)
    if not source.is_file() or source.is_symlink() or source.stat().st_size > 65536:
        raise UpdateError("This installer has no authenticated public trust configuration; no public release is available")
    # Reuse the updater's complete key/URL validation without persisting bad data.
    class SourceConfig:
        def __truediv__(self, name):
            return source
    value = trust(SimpleNamespace(config=SourceConfig()))
    atomic(target, value)
    return value


def prepare(layout, source, automatic, manager_type=Manager):
    provision_trust(layout, source)
    metadata = manager_type(layout).prepare()
    # No preference changes until an authenticated candidate is available.
    set_preferences(layout, automatic=automatic)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("automatic", choices=("on", "off"))
    args = parser.parse_args()
    try:
        if os.name != "posix" or os.geteuid() != 0:
            raise UpdateError("Use installer/install to authorize installation")
        layout = Layout()
        with layout.lock():
            metadata = prepare(layout, Path(__file__).with_name("bootstrap-trust.json"), args.automatic == "on")
            from installer.transaction import Transaction
            Transaction(layout).activate(metadata["version"])
        print("convertibled installed. Log in to complete your personal setup.")
        return 0
    except (UpdateError, OSError, ValueError) as exc:
        print(str(exc)[:512], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
