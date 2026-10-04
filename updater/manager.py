"""Root-controlled trust, channel state and verified preparation."""
import datetime as dt
import os
import shutil
import tarfile
from pathlib import Path
from .archive import extract
from .crypto import ed25519_public, envelope, keyring
from .model import UpdateError, canonical, decode, release, version_order
from .transport import fetch, url
from installer.configuration import preferences
from installer.platform import preflight
from installer.storage import atomic, read, sync_directory


def trust(layout):
    value = read(layout.config / "trust.json")
    if not isinstance(value, dict) or set(value) != {"schema", "roots", "keyring_url", "channels"} or value["schema"] != 1:
        raise UpdateError("Administrator must provision trusted offline root and channel URLs")
    if not isinstance(value["roots"], dict) or not 1 <= len(value["roots"]) <= 4:
        raise UpdateError("Invalid offline root set")
    for identifier, pem in value["roots"].items():
        if not isinstance(identifier, str) or not 1 <= len(identifier) <= 64:
            raise UpdateError("Invalid root identifier")
        ed25519_public(pem)
    if set(value["channels"]) != {"stable", "preview"}:
        raise UpdateError("Both channel endpoints must be explicit")
    for address in [value["keyring_url"], *value["channels"].values()]:
        url(address)
    return value


class Manager:
    def __init__(self, layout, network=fetch, platform_check=preflight):
        self.layout, self.network, self.platform_check = layout, network, platform_check

    def check(self):
        channel = preferences(self.layout)["channel"]
        trusted = trust(self.layout)
        accepted = read(self.layout.state / "accepted.json", {"schema": 1, "root_sequence": 0, "channels": {}})
        now = dt.datetime.now(dt.timezone.utc)
        signed_ring = self.network(trusted["keyring_url"])
        ring = keyring(signed_ring, trusted["roots"], now, accepted["root_sequence"])
        if ring["sequence"] == accepted["root_sequence"] and accepted.get("keyring") not in (None, ring):
            raise UpdateError("Immutable keyring sequence changed")
        # Root trust advances independently of channel availability/signatures.
        # Once learned, a revocation must survive a failed downstream request.
        accepted["root_sequence"] = ring["sequence"]
        accepted["keyring"] = ring
        accepted["keyring_envelope"] = decode(signed_ring)
        atomic(self.layout.state / "accepted.json", accepted)
        signed = self.network(trusted["channels"][channel])
        metadata = envelope(signed, ring["keys"])
        # Re-checking the same authenticated version is idempotent, while older
        # sequences are rejected. Accepted metadata bytes are retained for audit.
        prior = accepted["channels"].get(channel, {})
        sequence = prior.get("sequence", 0)
        if metadata == prior and metadata.get("sequence") == sequence:
            sequence -= 1
        metadata = release(metadata, channel, now, sequence)
        active = self.layout.active()
        installed = read(self.layout.versions / active / "release.json", {}) if active else {}
        for old in (prior, installed):
            if old.get("version") and version_order(metadata["version"]) < version_order(old["version"]):
                raise UpdateError("Signed version downgrade requires explicit local rollback")
        accepted["channels"][channel] = metadata
        accepted.setdefault("channel_envelopes", {})[channel] = decode(signed)
        atomic(self.layout.state / "accepted.json", accepted)
        atomic(self.layout.state / "available.json", metadata)
        return metadata

    def prepare(self):
        metadata = self.check()
        artifact = metadata["artifact"]
        self.platform_check(self.layout, artifact["size"] * 3 + 1024 * 1024 * 1024)
        installed = self.layout.versions / metadata["version"]
        if installed.exists():
            old = read(installed / "release.json", {})
            if old.get("version") != metadata["version"] or old.get("artifact", {}).get("sha256") != artifact["sha256"] or old.get("artifact", {}).get("size") != artifact["size"]:
                raise UpdateError("Immutable installed version disagrees with release")
            atomic(self.layout.state / "prepared.json", {"schema": 1, "version": metadata["version"], "channel": metadata["channel"]})
            return metadata
        staging = self.layout.state / "staging"
        if staging.is_symlink():
            raise UpdateError("Staging path is a symlink")
        staging.mkdir(exist_ok=True, mode=0o700)
        archive = staging / "artifact.tar.gz"
        candidate = staging / "candidate"
        if candidate.exists():
            shutil.rmtree(candidate)
        try:
            with archive.open("wb") as stream:
                self.network(artifact["url"], maximum=artifact["size"], target=stream, expected_hash=artifact["sha256"], expected_size=artifact["size"])
                stream.flush()
                os.fsync(stream.fileno())
            try:
                extract(archive, candidate, metadata["version"])
            except (tarfile.TarError, EOFError) as exc:
                raise UpdateError("Release bundle archive is corrupt") from exc
            atomic(candidate / "release.json", metadata)
            os.replace(candidate, installed)
            sync_directory(self.layout.versions)
            atomic(self.layout.state / "prepared.json", {"schema": 1, "version": metadata["version"], "channel": metadata["channel"]})
            return metadata
        finally:
            archive.unlink(missing_ok=True)
            if candidate.exists():
                shutil.rmtree(candidate)

    def activation_ready(self):
        prepared = read(self.layout.state / "prepared.json", {})
        channel = preferences(self.layout)["channel"]
        if prepared.get("channel") != channel:
            raise UpdateError("Prepared release is from another channel")
        accepted = read(self.layout.state / "accepted.json", {})
        now = dt.datetime.now(dt.timezone.utc)
        trusted = trust(self.layout)
        ring = keyring(canonical(accepted.get("keyring_envelope", {})), trusted["roots"], now, accepted.get("root_sequence", 0))
        metadata = envelope(canonical(accepted.get("channel_envelopes", {}).get(channel, {})), ring["keys"])
        if metadata != accepted.get("channels", {}).get(channel):
            raise UpdateError("Cached release metadata differs from authenticated envelope")
        if not metadata or metadata["version"] != prepared.get("version"):
            raise UpdateError("Prepared release no longer matches accepted metadata")
        release(metadata, channel, now, metadata["sequence"] - 1)
        installed = read(self.layout.versions / metadata["version"] / "release.json", {})
        if installed.get("artifact", {}).get("sha256") != metadata["artifact"]["sha256"] or installed.get("artifact", {}).get("size") != metadata["artifact"]["size"]:
            raise UpdateError("Prepared bundle bytes differ from authenticated release")
        return metadata["version"]
