#!/usr/bin/env python3
"""Validate downloaded artifact metadata before using values in release tooling."""
import json
from pathlib import Path
import re
import sys

candidate = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
run = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
if candidate.get("schema") != 1 or candidate.get("platform") != "fedora44-gnome50-x86_64":
    raise ValueError("Unexpected candidate schema/platform")
if not re.fullmatch(r"[0-9a-f]{40}", candidate.get("commit", "")) or candidate["commit"] != run.get("head_sha"):
    raise ValueError("Candidate provenance does not match successful run")
if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-(?:alpha|beta)\.[0-9]+)?", candidate.get("version", "")):
    raise ValueError("Invalid release version")
if candidate.get("artifact") != "convertibled-fedora44-x86_64.tar.gz":
    raise ValueError("Unexpected artifact name")
print("Candidate identity matches successful main build")
