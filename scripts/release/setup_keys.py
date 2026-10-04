#!/usr/bin/env python3
"""Interactive Linux key custody setup; never run unattended or inside CI."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.release.provision import provision
from updater.model import UpdateError


def locations(offline, online, output):
    offline, online, output = offline.resolve(), online.resolve(), output.resolve()
    for directory in (offline, online):
        if directory == ROOT or ROOT in directory.parents or directory in ROOT.parents:
            raise UpdateError("Private key directories must be outside the repository")
        if directory.exists() or not directory.parent.is_dir():
            raise UpdateError("Use new private directories under existing storage mounts")
    if offline == online or offline in online.parents or online in offline.parents:
        raise UpdateError("Root and release key directories must be separate, not nested")
    if output.exists() or any(directory == output or directory in output.parents or output in directory.parents for directory in (offline, online)):
        raise UpdateError("Public export must be new and separate from private key storage")
    return offline, online, output


def openssl(*arguments, password=None):
    return subprocess.check_output(["openssl", *arguments], input=(password or b"") + b"\n", stderr=subprocess.PIPE, timeout=30)


def protected(repository):
    raw = subprocess.check_output(["gh", "api", f"repos/{repository}/environments/release"], timeout=30)
    if not any(rule.get("type") == "required_reviewers" and rule.get("reviewers") for rule in json.loads(raw).get("protection_rules", [])):
        raise UpdateError("Release environment must have configured required reviewers")


def upload(repository, release_key, release_id):
    protected(repository)
    subprocess.run(["gh", "secret", "set", "RELEASE_SIGNING_KEY", "--repo", repository, "--env", "release"],
                   input=release_key.read_bytes(), capture_output=True, check=True, timeout=30)
    subprocess.run(["gh", "variable", "set", "RELEASE_KEY_ID", "--repo", repository, "--env", "release", "--body", release_id],
                   capture_output=True, check=True, timeout=30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--offline-dir", type=Path, required=True)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--upload-release-key", action="store_true")
    args = parser.parse_args()
    if os.name != "posix" or not sys.stdin.isatty():
        raise UpdateError("Run this setup in an interactive Linux terminal")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        raise UpdateError("Expected GitHub OWNER/REPOSITORY")
    offline, online, output = locations(args.offline_dir, args.release_dir, args.output)
    if args.upload_release_key:
        protected(args.repository)
    print("Use removable/offline storage for --offline-dir and disconnect it after setup.")
    print("Encryption alone does not make a key offline on this connected machine.")
    password = getpass.getpass("New offline root passphrase (hidden, at least 12 characters): ")
    if len(password) < 12 or any(value in password for value in ("\n", "\r", "\0")):
        raise UpdateError("Use at least 12 characters without line breaks or NUL")
    if password != getpass.getpass("Repeat offline root passphrase (hidden): "):
        raise UpdateError("Passphrases do not match")
    secret = password.encode("utf-8")
    prior_umask = os.umask(0o077)
    try:
        offline.mkdir(mode=0o700)
        online.mkdir(mode=0o700)
        for directory in (offline, online):
            if directory.stat().st_mode & 0o777 != 0o700 or directory.stat().st_uid != os.getuid():
                raise UpdateError("Private storage must enforce owner-only Linux directory permissions")
        root_key, release_key = offline / "root.pem", online / "release.pem"
        openssl("genpkey", "-algorithm", "ED25519", "-aes-256-cbc", "-pass", "stdin", "-out", str(root_key), password=secret)
        openssl("genpkey", "-algorithm", "ED25519", "-out", str(release_key))
        root_public = openssl("pkey", "-in", str(root_key), "-passin", "stdin", "-pubout", password=secret)
        release_public = openssl("pkey", "-in", str(release_key), "-pubout")
        (offline / "root-public.pem").write_bytes(root_public)
        (online / "release-public.pem").write_bytes(release_public)
        provision(args.repository, "offline-root-1", root_public.decode(), root_key,
                  "release-1", release_public.decode(), 1, 90, output, secret)
        public_der = openssl("pkey", "-pubin", "-inform", "PEM", "-in", str(offline / "root-public.pem"), "-outform", "DER")
        if args.upload_release_key:
            upload(args.repository, release_key, "release-1")
    finally:
        os.umask(prior_umask)
    print(f"Offline root public SHA-256: {hashlib.sha256(public_der).hexdigest()}")
    print(f"Review public files in {output}; independently record the fingerprint and disconnect root storage.")


if __name__ == "__main__":
    main()
