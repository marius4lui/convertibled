"""Root-controlled trust, channel state and verified preparation."""
import datetime as dt
import os
import shutil
from pathlib import Path
from .archive import extract
from .crypto import envelope, keyring
from .model import UpdateError, release
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
        counters = read(self.layout.state / "counters.json", {"root": 0, "stable": 0, "preview": 0})
        now = dt.datetime.now(dt.timezone.utc)
        ring = keyring(self.network(trusted["keyring_url"]), trusted["roots"], now, counters["root"])
        signed = self.network(trusted["channels"][channel])
        metadata = envelope(signed, ring["keys"])
        # Re-checking the same authenticated version is idempotent, while older
        # sequences are rejected. Accepted metadata bytes are retained for audit.
        prior = read(self.layout.state / "available.json", {})
        sequence = counters[channel]
        if metadata == prior and metadata.get("sequence") == sequence:
            sequence -= 1
        metadata = release(metadata, channel, now, sequence)
        counters["root"] = ring["sequence"]
        counters[channel] = metadata["sequence"]
        atomic(self.layout.state / "counters.json", counters)
        atomic(self.layout.state / "available.json", metadata)
        return metadata

    def prepare(self):
        metadata = self.check()
        artifact = metadata["artifact"]
        self.platform_check(self.layout, artifact["size"] * 3 + 1024 * 1024 * 1024)
        installed = self.layout.versions / metadata["version"]
        if installed.exists():
            if read(installed / "release.json") != metadata:
                raise UpdateError("Immutable installed version disagrees with release")
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
            extract(archive, candidate, metadata["version"])
            atomic(candidate / "release.json", metadata)
            os.replace(candidate, installed)
            sync_directory(self.layout.versions)
            atomic(self.layout.state / "prepared.json", {"schema": 1, "version": metadata["version"], "channel": metadata["channel"]})
            return metadata
        finally:
            archive.unlink(missing_ok=True)
            if candidate.exists():
                shutil.rmtree(candidate)
