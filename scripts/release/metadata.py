#!/usr/bin/env python3
"""Construct validated unsigned metadata; release signing is a separate step."""
import argparse
import datetime as dt
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from updater.model import canonical, release
from updater.transport import url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--sequence", type=int, required=True)
    parser.add_argument("--channel", choices=("stable", "preview"), required=True)
    parser.add_argument("--notes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    value = {"schema": 1, "version": args.version, "sequence": args.sequence, "channel": args.channel, "platform": {"os": "fedora", "version": "44", "architecture": "x86_64", "desktop": "GNOME", "desktop_version": "50", "session": "wayland"}, "issued": now.isoformat(), "expires": (now + dt.timedelta(days=14)).isoformat(), "artifact": {"url": url(args.url), "size": args.artifact.stat().st_size, "sha256": hashlib.sha256(args.artifact.read_bytes()).hexdigest()}, "config_schema": 1, "notes": args.notes.read_text(encoding="utf-8")}
    release(value, args.channel, now)
    with args.output.open("xb") as stream:
        stream.write(canonical(value))


if __name__ == "__main__":
    main()
