"""Offline verified assets use a fixed root-owned incoming directory."""
import hashlib
from .model import UpdateError
from .manager import trust
from installer.configuration import preferences


class Offline:
    def __init__(self, layout):
        self.directory = layout.state / "offline"
        endpoints = trust(layout)
        self.mapping = {endpoints["keyring_url"]: "keyring.json", endpoints["channels"][preferences(layout)["channel"]]: "channel.json"}

    def __call__(self, address, maximum=262144, target=None, expected_hash=None, expected_size=None):
        name = self.mapping.get(address) if target is None else "artifact.tar.gz"
        if not name or self.directory.is_symlink():
            raise UpdateError("Unknown offline asset")
        path = self.directory / name
        if path.is_symlink() or not path.is_file():
            raise UpdateError("Required root-provisioned offline asset missing")
        if path.stat().st_size > maximum:
            raise UpdateError("Offline asset exceeds size limit")
        digest = hashlib.sha256()
        count = 0
        content = []
        with path.open("rb") as source:
            while chunk := source.read(65536):
                count += len(chunk)
                if count > maximum:
                    raise UpdateError("Offline asset exceeds size limit")
                digest.update(chunk)
                if target is None:
                    content.append(chunk)
                else:
                    target.write(chunk)
        if expected_size is not None and count != expected_size or expected_hash is not None and digest.hexdigest() != expected_hash:
            raise UpdateError("Offline asset verification failed")
        return b"".join(content) if target is None else count
