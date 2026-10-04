#!/usr/bin/env python3
"""Package reviewed installer source and public trust without private key material."""
import argparse
import gzip
import io
import subprocess
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from updater.crypto import ed25519_public
from updater.model import UpdateError, decode
from updater.transport import url


def build(commit, trust_raw, output):
    trust = decode(trust_raw)
    if set(trust) != {"schema", "roots", "keyring_url", "channels"} or trust["schema"] != 1:
        raise UpdateError("Invalid bootstrap trust contract")
    if not isinstance(trust["roots"], dict) or not trust["roots"]:
        raise UpdateError("Independently authenticated public roots are required")
    for pem in trust["roots"].values():
        ed25519_public(pem)
    url(trust["keyring_url"])
    if set(trust["channels"]) != {"stable", "preview"}:
        raise UpdateError("Both channel endpoints are required")
    for endpoint in trust["channels"].values():
        url(endpoint)
    source = subprocess.check_output(["git", "-c", "core.autocrlf=false", "archive", "--format=tar", commit, "installer", "updater", "LICENSE"])
    with output.open("xb") as destination, gzip.GzipFile(fileobj=destination, mode="wb", mtime=0, filename="") as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive, tarfile.open(fileobj=io.BytesIO(source)) as original:
            for member in original:
                if member.name == "installer/bootstrap-trust.json":
                    continue
                if not (member.isdir() or member.isfile()):
                    raise UpdateError("Unexpected installer source link")
                member.uid = member.gid = member.mtime = 0
                member.uname = member.gname = ""
                archive.addfile(member, original.extractfile(member) if member.isfile() else None)
            member = tarfile.TarInfo("installer/bootstrap-trust.json")
            member.size, member.mode = len(trust_raw), 0o644
            archive.addfile(member, io.BytesIO(trust_raw))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--trust", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.commit, args.trust.read_bytes(), args.output)
