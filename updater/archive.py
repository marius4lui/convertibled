"""Bounded extraction; release manifest is the only allowed file set."""
import hashlib
import os
import tarfile
from pathlib import Path, PurePosixPath
from .model import UpdateError, decode, version

MAX_EXPANDED = 1024 * 1024 * 1024
MAX_FILES = 4096


def safe_name(name):
    path = PurePosixPath(name)
    if not name or "\\" in name or path.is_absolute() or any(part in ("..", ".", "") for part in name.split("/")):
        raise UpdateError("Unsafe archive path")
    if len(name) > 240 or ":" in name:
        raise UpdateError("Invalid archive path")
    return path


def manifest(value):
    if not isinstance(value, dict) or set(value) != {"schema", "version", "files"} or type(value["schema"]) is not int or value["schema"] != 1:
        raise UpdateError("Unsupported bundle manifest")
    version(value["version"])
    files = value["files"]
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise UpdateError("Invalid bundle file count")
    total = 0
    for name, info in files.items():
        safe_name(name)
        if not name.startswith(("bin/", "installer/", "updater/", "share/", "data/")):
            raise UpdateError("Bundle path is outside component roots")
        if not isinstance(info, dict) or set(info) != {"size", "sha256", "executable"}:
            raise UpdateError("Invalid file contract")
        if type(info["size"]) is not int or info["size"] < 0 or type(info["executable"]) is not bool:
            raise UpdateError("Invalid file size or permissions")
        if not isinstance(info["sha256"], str) or len(info["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in info["sha256"]):
            raise UpdateError("Invalid file hash")
        total += info["size"]
    if total > MAX_EXPANDED:
        raise UpdateError("Expanded bundle exceeds limit")
    for binary in ("convertibled", "convertibled-session", "convertiblectl", "convertibled-settings"):
        if f"bin/{binary}" not in files or not files[f"bin/{binary}"]["executable"]:
            raise UpdateError("Bundle is missing a required executable")
    return value


def extract(archive, destination, expected_version):
    destination = Path(destination)
    if destination.exists():
        raise UpdateError("Extraction destination already exists")
    with tarfile.open(archive, "r:gz") as bundle:
        entries = []
        names = set()
        total = 0
        for entry in bundle:
            entries.append(entry)
            if len(entries) > MAX_FILES + 1:
                raise UpdateError("Archive has too many entries")
            safe_name(entry.name)
            if not entry.isfile() or entry.name in names or entry.size < 0:
                raise UpdateError("Links, directories and duplicate entries are forbidden")
            names.add(entry.name)
            total += entry.size
            if total > MAX_EXPANDED + 262144:
                raise UpdateError("Archive expansion exceeds limit")
        index = bundle.getmember("manifest.json") if "manifest.json" in names else None
        if index is None or index.size > 262144:
            raise UpdateError("Missing bounded bundle manifest")
        contract = manifest(decode(bundle.extractfile(index).read()))
        if contract["version"] != expected_version or names != set(contract["files"]) | {"manifest.json"}:
            raise UpdateError("Bundle and signed release disagree")
        destination.mkdir(mode=0o755, parents=True)
        # Read payloads in archive order to avoid repeated gzip rewind/expansion.
        for entry in entries:
            name = entry.name
            if name == "manifest.json":
                continue
            info = contract["files"][name]
            if entry.size != info["size"]:
                raise UpdateError("Bundle size mismatch")
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            with bundle.extractfile(entry) as source, path.open("xb") as target:
                while block := source.read(65536):
                    digest.update(block)
                    target.write(block)
                if digest.hexdigest() != info["sha256"]:
                    raise UpdateError("Bundle file hash mismatch")
                path.chmod(0o755 if info["executable"] else 0o644)
                target.flush()
                os.fsync(target.fileno())
        index_path = destination / "manifest.json"
        with index_path.open("xb") as target:
            target.write(__import__('json').dumps(contract).encode())
            index_path.chmod(0o644)
            target.flush()
            os.fsync(target.fileno())
        # systemd prepares updates with UMask=0077. Published code must still
        # be traversable by the service account and GNOME users. Keep the outer
        # private staging directory private until Manager publishes this tree.
        from installer.storage import sync_directory
        directories = [destination] + [path for path in destination.rglob("*") if path.is_dir()]
        for directory in sorted(directories, key=lambda path: len(path.parts), reverse=True):
            directory.chmod(0o755)
            sync_directory(directory)
        return contract
