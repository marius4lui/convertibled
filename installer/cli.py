#!/usr/bin/python3 -I
"""Fixed privileged verbs; no caller-supplied paths, URLs or commands."""
import argparse
import json
import os
import sys
from pathlib import Path

# Isolated mode ignores user site/PYTHONPATH. Only this root-owned bundle is used.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.dont_write_bytecode = True
from installer.configuration import preferences, set_preferences
from installer.platform import graphical_sessions
from installer.status import public, publish
from installer.storage import Layout, read
from installer.transaction import Transaction
from updater.manager import Manager
from updater.model import UpdateError


def parser():
    result = argparse.ArgumentParser(description="convertibled installation and verified updates")
    result.add_argument("command", choices=("status", "check", "prepare", "offline-prepare", "install", "activate", "recover", "rollback", "uninstall", "automatic", "channel", "scheduled"))
    result.add_argument("value", nargs="?", choices=("on", "off", "stable", "preview"))
    return result


def execute(args, layout):
    if args.command == "status":
        return public(layout)
    if os.name != "posix" or os.geteuid() != 0:
        raise UpdateError("Use the authorized pkexec installation helper")
    if (args.command in ("automatic", "channel")) != (args.value is not None):
        raise UpdateError("This operation requires exactly its fixed preference value")
    with layout.lock():
        manager = Manager(layout)
        transaction = Transaction(layout)
        if args.command == "automatic":
            if args.value not in ("on", "off"):
                raise UpdateError("Automatic updates accept on/off")
            set_preferences(layout, automatic=args.value == "on")
        elif args.command == "channel":
            if args.value not in ("stable", "preview"):
                raise UpdateError("Channel accepts stable/preview")
            set_preferences(layout, channel=args.value)
        elif args.command == "check":
            manager.check()
        elif args.command == "prepare":
            manager.prepare()
        elif args.command == "offline-prepare":
            from updater.offline import Offline
            Manager(layout, network=Offline(layout)).prepare()
        elif args.command == "install":
            metadata = manager.prepare()
            transaction.activate(metadata["version"])
        elif args.command == "activate":
            transaction.activate(manager.activation_ready())
        elif args.command == "recover":
            transaction.recover()
        elif args.command == "rollback":
            transaction.rollback()
        elif args.command == "uninstall":
            from installer.uninstall import uninstall
            uninstall(layout)
        elif args.command == "scheduled":
            from updater.schedule import due, quarantined
            if graphical_sessions():
                transaction.observe_login()
                if preferences(layout)["automatic_updates"] and due(layout):
                    manager.prepare()
            else:
                transaction.recover()
                if preferences(layout)["automatic_updates"]:
                    if due(layout):
                        manager.prepare()
                    if read(layout.state / "prepared.json"):
                        candidate = manager.activation_ready()
                        if not quarantined(layout, candidate):
                            transaction.activate(candidate)
        return publish(layout)


def main():
    args = parser().parse_args()
    layout = Layout()
    try:
        print(json.dumps(execute(args, layout), sort_keys=True))
        return 0
    except (UpdateError, OSError, ValueError) as exc:
        if os.name == "posix" and os.geteuid() == 0:
            try:
                publish(layout, exc)
            except (UpdateError, OSError):
                pass
        print(json.dumps({"error": str(exc)[:512]}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
