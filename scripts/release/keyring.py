#!/usr/bin/env python3
"""Create an offline-root-signed keyring from explicitly selected public keys."""
import argparse
import base64
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from updater.crypto import ed25519_public, keyring
from updater.model import UpdateError, canonical, decode
from scripts.release.sign import sign


def create(keys, sequence, days, root_key, root_id, roots, now):
    if type(sequence) is not int or sequence < 1 or not 1 <= days <= 366:
        raise UpdateError("Use a positive new sequence and 1..366 validity days")
    if not isinstance(keys, dict) or not keys or root_id in keys:
        raise UpdateError("Release keys must be separate from the offline root")
    for identifier, pem in keys.items():
        if not identifier or len(identifier) > 64:
            raise UpdateError("Invalid release key identifier")
        ed25519_public(pem)
        def material(public):
            ed25519_public(public)
            return base64.b64decode(public.replace("-----BEGIN PUBLIC KEY-----", "").replace("-----END PUBLIC KEY-----", ""))
        if material(pem) in [material(root) for root in roots.values()]:
            raise UpdateError("Offline root must never be a release key")
    payload = {"schema": 1, "sequence": sequence, "issued": now.isoformat(),
               "expires": (now + dt.timedelta(days=days)).isoformat(), "keys": keys}
    signed = canonical(sign(payload, root_key, root_id))
    keyring(signed, roots, now, sequence)
    return signed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keys", type=Path, required=True, help="JSON map of release IDs to public PEM keys")
    parser.add_argument("--roots", type=Path, required=True, help="Independently authenticated JSON map of root IDs to public PEM keys")
    parser.add_argument("--root-key", type=Path, required=True)
    parser.add_argument("--root-id", required=True)
    parser.add_argument("--sequence", type=int, required=True)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = create(decode(args.keys.read_bytes()), args.sequence, args.days, args.root_key,
                 args.root_id, decode(args.roots.read_bytes()), dt.datetime.now(dt.timezone.utc))
    with args.output.open("xb") as stream:
        stream.write(raw)


if __name__ == "__main__":
    main()
