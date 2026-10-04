#!/usr/bin/env python3
"""Build a deterministic project-owned bundle from existing Linux artifacts."""
import argparse
import gzip
import hashlib
import io
import json
import sys
import tarfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from updater.archive import manifest
from updater.model import canonical, UpdateError


def collect(binary_directory, extension_directory):
    result = {}
    for name in ("convertibled", "convertibled-session", "convertiblectl", "convertibled-settings"):
        path = binary_directory / name
        if not path.is_file() or path.read_bytes()[:4] != b"\x7fELF":
            raise UpdateError("Missing Linux ELF executable: " + name)
        result["bin/" + name] = (path.read_bytes(), True)
    for component in ("installer", "updater"):
        for path in sorted((ROOT / component).glob("*.py")):
            if not path.name.startswith("test_"):
                result[component + "/" + path.name] = (path.read_bytes().replace(b"\r\n", b"\n"), path.name == "cli.py")
    for path in sorted((ROOT / "data").rglob("*")):
        if path.is_file() and not path.is_symlink():
            result[path.relative_to(ROOT).as_posix()] = (path.read_bytes().replace(b"\r\n", b"\n"), False)
    for path in sorted(extension_directory.rglob("*")):
        if path.is_file() and not path.is_symlink():
            result["share/gnome-shell/extensions/convertibled@convertibled.org/" + path.relative_to(extension_directory).as_posix()] = (path.read_bytes(), False)
    if not any(name.endswith("/gschemas.compiled") for name in result):
        raise UpdateError("Compile extension GSettings schemas before bundling")
    desktop = ROOT / "crates/settings/data/org.convertibled.Settings.desktop"
    if not desktop.is_file():
        desktop = ROOT / "data/org.convertibled.Settings.desktop"
    if not desktop.is_file():
        raise UpdateError("Missing native settings desktop entry")
    result["share/applications/org.convertibled.Settings.desktop"] = (desktop.read_bytes(), False)
    return result


def build(files, version, output):
    index = {"schema": 1, "version": version, "files": {name: {"size": len(content), "sha256": hashlib.sha256(content).hexdigest(), "executable": executable} for name, (content, executable) in files.items()}}
    manifest(index)
    files = {**files, "manifest.json": (canonical(index), False)}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream, gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0) as compressed, tarfile.open(fileobj=compressed, mode="w") as archive:
        for name, (content, executable) in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(content), 0o755 if executable else 0o644, 0
            info.uid = info.gid = 0
            archive.addfile(info, io.BytesIO(content))
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin-dir", type=Path, required=True)
    parser.add_argument("--extension-dir", type=Path, default=ROOT / "extension/dist")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    version = tomllib.loads((ROOT / "Cargo.toml").read_text())["workspace"]["package"]["version"]
    build(collect(args.bin_dir, args.extension_dir), version, args.output)
    print(json.dumps({"version": version, "size": args.output.stat().st_size, "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
