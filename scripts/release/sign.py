#!/usr/bin/env python3
"""Sign metadata with an externally held Ed25519 PEM key; never generate keys."""
import argparse
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from updater.model import canonical, decode, UpdateError


def sign(payload, key, key_id):
    if ROOT.resolve() in key.resolve().parents:
        raise UpdateError("Signing keys must be stored outside the repository")
    with tempfile.TemporaryDirectory(prefix="convertibled-sign-") as temporary:
        source = Path(temporary) / "payload"
        signature = Path(temporary) / "signature"
        source.write_bytes(canonical(payload))
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(key), "-rawin", "-in", str(source), "-out", str(signature)], check=True, timeout=30)
        raw = signature.read_bytes()
        if len(raw) != 64:
            raise UpdateError("Signing key must be Ed25519")
    return {"key_id": key_id, "payload": payload, "signature": base64.b64encode(raw).decode("ascii")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = sign(decode(args.input.read_bytes()), args.key, args.key_id)
    with args.output.open("xb") as stream:
        stream.write(canonical(value))


if __name__ == "__main__":
    main()
