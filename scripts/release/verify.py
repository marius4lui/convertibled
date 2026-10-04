#!/usr/bin/env python3
"""Authenticate release assets before publishing or promoting a channel."""
import argparse
import datetime as dt
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from updater.crypto import envelope, keyring
from updater.model import UpdateError, decode, release, version_order


def verify(directory, roots, channel, repository, now, previous=None):
    ring = keyring((directory / "keyring.json").read_bytes(), roots, now, 1)
    signed = (directory / f"{channel}.json").read_bytes()
    current = release(envelope(signed, ring["keys"]), channel, now)
    artifact = directory / "convertibled-fedora44-x86_64.tar.gz"
    with artifact.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    expected = {"size": artifact.stat().st_size, "sha256": digest,
                "url": f"https://github.com/{repository}/releases/download/v{current['version']}/{artifact.name}"}
    if current["artifact"] != expected:
        raise UpdateError("Signed artifact identity differs from release bytes or repository")
    candidate = decode((directory / "candidate.json").read_bytes())
    if candidate.get("version") != current["version"] or candidate.get("artifact_sha256") != digest:
        raise UpdateError("Candidate provenance differs from signed release")
    if previous is not None:
        # Old channel metadata may have expired or used a now-revoked key. It is
        # read from the maintainer-controlled channel, never trusted for install.
        old = decode(previous)["payload"]
        if current["sequence"] <= old["sequence"] or version_order(current["version"]) < version_order(old["version"]):
            raise UpdateError("Channel promotion would replay or downgrade")
        if current["version"] == old["version"] and current["artifact"] != old["artifact"]:
            raise UpdateError("Published version bytes are immutable")
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--roots", type=Path, required=True)
    parser.add_argument("--channel", choices=("stable", "preview"), required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    verify(args.directory, decode(args.roots.read_bytes()), args.channel, args.repository,
           dt.datetime.now(dt.timezone.utc), args.previous.read_bytes() if args.previous else None)
    print("Release signature, trust, freshness, provenance and artifact identity verified")


if __name__ == "__main__":
    main()
