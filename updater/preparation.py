"""Journal-owned staging and conservative cleanup after interrupted preparation."""
import hashlib
import json
import os
import re
import shutil
import stat
import tarfile
import uuid
from pathlib import Path
from .archive import MAX_FILES, MAX_EXPANDED, manifest, safe_name
from .model import UpdateError, decode
from installer.storage import atomic, read, sync_directory


def identity(path):
    info = path.lstat()
    return {"device": info.st_dev, "inode": info.st_ino}


def private_directory(path, expected=None):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or path.is_symlink():
        raise UpdateError("Preparation directory is not a real directory")
    if os.name == "posix" and (info.st_uid != os.geteuid() or info.st_mode & 0o777 != 0o700):
        raise UpdateError("Preparation directory ownership or permissions changed")
    if expected is not None and identity(path) != expected:
        raise UpdateError("Preparation directory identity changed")


def matches_prefix(path, expected):
    if path.stat().st_size > len(expected):
        return False
    with path.open("rb") as stream:
        position = 0
        while chunk := stream.read(65536):
            if chunk != expected[position:position + len(chunk)]:
                return False
            position += len(chunk)
    return True


def inspect_candidate(candidate, archive, metadata):
    artifact = metadata["artifact"]
    with archive.open("rb") as stream:
        if archive.stat().st_size != artifact["size"] or hashlib.file_digest(stream, "sha256").hexdigest() != artifact["sha256"]:
            raise UpdateError("Retained preparation archive no longer matches authenticated bytes")
    with tarfile.open(archive, "r:gz") as bundle:
        entries = {}
        expanded = 0
        for member in bundle:
            safe_name(member.name)
            expanded += member.size
            if not member.isfile() or member.size < 0 or member.name in entries or len(entries) >= MAX_FILES + 1 or expanded > MAX_EXPANDED + 262144:
                raise UpdateError("Retained preparation archive is unsafe")
            entries[member.name] = member
        index = entries.get("manifest.json")
        if index is None or index.size > 262144:
            raise UpdateError("Retained preparation manifest is missing")
        contract = manifest(decode(bundle.extractfile(index).read()))
        if contract["version"] != metadata["version"] or set(entries) != set(contract["files"]) | {"manifest.json"}:
            raise UpdateError("Retained preparation archive differs from release")
        metadata_files = {"manifest.json": json.dumps(contract).encode(),
                          "release.json": json.dumps(metadata, sort_keys=True).encode()}
        allowed_files = set(contract["files"]) | set(metadata_files)
        allowed_dirs = {parent.as_posix() for name in allowed_files for parent in Path(name).parents if parent.as_posix() != "."}
        actual_files = {}
        for item in candidate.rglob("*"):
            name = item.relative_to(candidate).as_posix()
            info = item.lstat()
            if os.name == "posix" and info.st_uid != os.geteuid():
                raise UpdateError("Preparation file ownership changed")
            if stat.S_ISDIR(info.st_mode) and name in allowed_dirs:
                continue
            if not stat.S_ISREG(info.st_mode) or name not in allowed_files or info.st_nlink != 1:
                raise UpdateError("Unowned preparation content retained")
            actual_files[name] = item
        # Verify in physical archive order to avoid repeated gzip rewinds.
        for name in [*entries, "release.json"]:
            item = actual_files.get(name)
            if item is None:
                continue
            if name in metadata_files:
                matched = matches_prefix(item, metadata_files[name])
            else:
                expected = entries[name]
                if item.stat().st_size > expected.size:
                    raise UpdateError("Modified preparation file retained")
                matched = True
                with item.open("rb") as actual, bundle.extractfile(expected) as original:
                    while block := actual.read(65536):
                        if block != original.read(len(block)):
                            matched = False
                            break
            if not matched:
                raise UpdateError("Modified preparation file retained")


def cleanup(layout):
    journal_path = layout.state / "preparation.json"
    journal = read(journal_path)
    if journal is None:
        return
    if not isinstance(journal, dict) or type(journal.get("schema")) is not int or journal["schema"] != 1 or not isinstance(journal.get("token"), str) or not re.fullmatch(r"[0-9a-f]{32}", journal["token"]):
        raise UpdateError("Invalid preparation ownership journal")
    if layout.versions.is_symlink() or (layout.state / "staging").is_symlink():
        raise UpdateError("Preparation parent directory is a symlink")
    token = journal["token"]
    download = layout.state / "staging" / (".download-" + token)
    preparation = layout.versions / (".prepare-" + token)
    # Validate everything before removing anything; unknown data survives.
    for label, path in (("download", download), ("preparation", preparation)):
        if not path.exists() and not path.is_symlink():
            continue
        private_directory(path, journal.get(label))
        if label not in journal and any(path.iterdir()):
            raise UpdateError("Unregistered nonempty preparation directory retained")
    if download.exists():
        if set(p.name for p in download.iterdir()) - {"artifact.tar.gz"}:
            raise UpdateError("Unowned download content retained")
    archive = download / "artifact.tar.gz"
    if archive.exists() or archive.is_symlink():
        info = archive.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or (os.name == "posix" and info.st_uid != os.geteuid()):
            raise UpdateError("Download file identity changed")
        if "archive" not in journal:
            if info.st_size != 0:
                raise UpdateError("Unregistered nonempty download retained")
        elif identity(archive) != journal["archive"]:
            raise UpdateError("Download file identity changed")
    if preparation.exists():
        if set(p.name for p in preparation.iterdir()) - {"candidate"}:
            raise UpdateError("Unowned preparation content retained")
        candidate = preparation / "candidate"
        if candidate.exists() or candidate.is_symlink():
            if candidate.is_symlink() or not candidate.is_dir():
                raise UpdateError("Candidate directory changed")
            if not archive.exists():
                raise UpdateError("Retained candidate has no authenticated archive")
            inspect_candidate(candidate, archive, journal["metadata"])
    for path in (preparation, download):
        if path.exists():
            shutil.rmtree(path)
            sync_directory(path.parent)
    journal_path.unlink()
    sync_directory(layout.state)


class Workspace:
    def __init__(self, layout, metadata):
        self.layout = layout
        self.journal = {"schema": 1, "token": uuid.uuid4().hex, "metadata": metadata}
        self.download = layout.state / "staging" / (".download-" + self.journal["token"])
        self.preparation = layout.versions / (".prepare-" + self.journal["token"])
        self.archive = self.download / "artifact.tar.gz"
        self.candidate = self.preparation / "candidate"

    def save(self):
        atomic(self.layout.state / "preparation.json", self.journal)

    def __enter__(self):
        cleanup(self.layout)
        self.save()  # Creation intent precedes both mkdir calls.
        for label, path in (("download", self.download), ("preparation", self.preparation)):
            path.mkdir(mode=0o700)
            sync_directory(path.parent)
            private_directory(path)
            self.journal[label] = identity(path)
            self.save()
        with self.archive.open("xb"):
            pass
        self.journal["archive"] = identity(self.archive)
        self.save()
        return self

    def write_release(self):
        with (self.candidate / "release.json").open("xb") as stream:
            stream.write(json.dumps(self.journal["metadata"], sort_keys=True).encode())
            stream.flush()
            os.fsync(stream.fileno())

    def __exit__(self, *_):
        cleanup(self.layout)
