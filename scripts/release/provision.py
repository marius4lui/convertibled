#!/usr/bin/env python3
"""Export public production trust using existing externally held Ed25519 keys."""
import argparse
import datetime as dt
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.release.keyring import create
from updater.crypto import ed25519_public
from updater.model import UpdateError, canonical
from scripts.release.sign import ask_passphrase


def provision(repository, root_id, root_public, root_private, release_id, release_public,
              sequence, days, output, passphrase=None):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise UpdateError("Expected GitHub OWNER/REPOSITORY")
    for identifier in (root_id, release_id):
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", identifier):
            raise UpdateError("Invalid public key identifier")
    roots = {root_id: ed25519_public(root_public)}
    ring = create({release_id: ed25519_public(release_public)}, sequence, days,
                  root_private, root_id, roots, dt.datetime.now(dt.timezone.utc), passphrase)
    base = f"https://raw.githubusercontent.com/{repository}"
    trust = {"schema": 1, "roots": roots, "keyring_url": f"{base}/main/release/keyring.json",
             "channels": {channel: f"{base}/update-channels/{channel}.json" for channel in ("stable", "preview")}}
    output.mkdir(parents=True, exist_ok=False)
    (output / "trust.json").write_bytes(canonical(trust))
    (output / "keyring.json").write_bytes(ring)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--root-id", default="offline-root-1")
    parser.add_argument("--root-public", type=Path, required=True)
    parser.add_argument("--root-key", type=Path, required=True)
    parser.add_argument("--release-id", default="release-1")
    parser.add_argument("--release-public", type=Path, required=True)
    parser.add_argument("--sequence", type=int, required=True)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ask-passphrase", action="store_true")
    args = parser.parse_args()
    provision(args.repository, args.root_id, args.root_public.read_text(encoding="ascii"),
              args.root_key, args.release_id, args.release_public.read_text(encoding="ascii"),
              args.sequence, args.days, args.output, ask_passphrase() if args.ask_passphrase else None)
    print("Exported public trust.json and verified root-signed keyring.json; no private keys copied")
