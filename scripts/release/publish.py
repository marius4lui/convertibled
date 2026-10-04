#!/usr/bin/env python3
"""Publish verified draft bytes, then atomically advance a channel Git file."""
import argparse
import base64
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import sys
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.release.verify import verify
from updater.model import UpdateError, decode
from updater.transport import fetch


def gh(*arguments):
    return subprocess.check_output(["gh", *arguments], text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--channel", choices=("stable", "preview"), required=True)
    parser.add_argument("--refresh-prepared", type=Path, help="Fresh signed metadata for an already public immutable release")
    args = parser.parse_args()
    repository = os.environ["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise UpdateError("Invalid repository")
    from updater.model import version
    tag = "v" + version(args.version)
    trust = decode(Path("release/trust.json").read_bytes())
    expected_channel = f"https://raw.githubusercontent.com/{repository}/update-channels/{args.channel}.json"
    if trust["channels"][args.channel] != expected_channel:
        raise UpdateError("Trust channel does not match atomic publication branch")
    info = json.loads(gh("api", f"repos/{repository}/releases/tags/{tag}"))
    if info["prerelease"] != (args.channel == "preview"):
        raise UpdateError("Release channel differs from release visibility")
    if args.refresh_prepared and info["draft"]:
        raise UpdateError("Metadata refresh requires an already published release")
    branch = json.loads(gh("api", f"repos/{repository}/git/ref/heads/update-channels"))
    head = branch["object"]["sha"]
    tree = json.loads(gh("api", f"repos/{repository}/git/trees/{head}"))["tree"]
    existing = next((item for item in tree if item["path"] == f"{args.channel}.json"), None)
    previous = None
    if existing:
        blob = json.loads(gh("api", f"repos/{repository}/git/blobs/{existing['sha']}"))
        previous = base64.b64decode(blob["content"])
    with tempfile.TemporaryDirectory(prefix="convertibled-publish-") as temporary:
        directory = Path(temporary)
        gh("release", "download", tag, "--dir", str(directory))
        if args.refresh_prepared:
            for name in ("keyring.json", f"{args.channel}.json"):
                shutil.copyfile(args.refresh_prepared / name, directory / name)
        current = verify(directory, trust["roots"], args.channel, repository, dt.datetime.now(dt.timezone.utc), previous)
        if current["version"] != args.version:
            raise UpdateError("Requested tag differs from signed version")
        candidate = decode((directory / "candidate.json").read_bytes())
        commit = candidate["commit"]
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise UpdateError("Invalid source commit")
        actual = subprocess.check_output(["git", "rev-parse", f"refs/tags/{tag}^{{commit}}"], text=True).strip()
        if actual != commit:
            raise UpdateError("Release tag differs from accepted commit")
        subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], check=True)
        subprocess.run(["python3", "scripts/verify-acceptance.py", "--record", f"docs/acceptance/{commit}.json", "--commit", commit,
                        "--artifact", str(directory / "convertibled-fedora44-x86_64.tar.gz")], check=True)
        rebuilt = directory / "rebuilt-installer.tar.gz"
        subprocess.run(["python3", "scripts/release/bootstrap.py", "--commit", commit, "--trust", "release/trust.json", "--output", str(rebuilt)], check=True)
        if rebuilt.read_bytes() != (directory / "convertibled-installer.tar.gz").read_bytes():
            raise UpdateError("Bootstrap differs from reviewed source and trust")
        # The public root-signed keyring must already be deployed. No private
        # root or root-key rotation occurs in an online publishing job.
        deployed = fetch(trust["keyring_url"])
        if deployed != (directory / "keyring.json").read_bytes():
            raise UpdateError("Deployed keyring differs from reviewed release trust")
        if info["draft"]:
            gh("release", "edit", tag, "--draft=false", "--latest=false")
        # Independently download the now-public bundle and compare bytes before
        # moving the channel. A failure leaves the previous channel intact.
        with (directory / "public-bundle.tar.gz").open("xb") as public:
            fetch(current["artifact"]["url"], maximum=current["artifact"]["size"], target=public,
                  expected_size=current["artifact"]["size"], expected_hash=current["artifact"]["sha256"])
        verify(directory, trust["roots"], args.channel, repository, dt.datetime.now(dt.timezone.utc), previous)
        if previous == (directory / f"{args.channel}.json").read_bytes():
            print("Verified channel already selects exactly these signed bytes")
            if args.channel == "stable":
                gh("release", "edit", tag, "--latest=true")
            return
        payload = {"message": f"release({args.channel}): promote {tag}", "branch": "update-channels",
                   "content": base64.b64encode((directory / f"{args.channel}.json").read_bytes()).decode()}
        if existing:
            payload["sha"] = existing["sha"]
        request = directory / "request.json"
        request.write_text(json.dumps(payload), encoding="utf-8")
        gh("api", "--method", "PUT", f"repos/{repository}/contents/{args.channel}.json", "--input", str(request))
        if args.channel == "stable":
            gh("release", "edit", tag, "--latest=true")
    print(f"Published {tag} and atomically promoted {args.channel}")


if __name__ == "__main__":
    main()
