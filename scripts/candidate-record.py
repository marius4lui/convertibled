#!/usr/bin/env python3
"""Record candidate bytes, source revision and an SPDX package inventory."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import tomllib

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--artifact", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
version = tomllib.loads((root / "Cargo.toml").read_text())["workspace"]["package"]["version"]
commit = subprocess.check_output(["git", "-c", f"safe.directory={root}", "rev-parse", "HEAD"], cwd=root, text=True).strip()
with args.artifact.open("rb") as stream:
    digest = hashlib.file_digest(stream, "sha256").hexdigest()
record = {"schema": 1, "version": version, "commit": commit, "artifact": args.artifact.name,
          "artifact_sha256": digest, "platform": "fedora44-gnome50-x86_64"}
args.artifact.with_name("candidate.json").write_text(json.dumps(record, indent=2) + "\n")
args.artifact.with_name("SHA256SUMS").write_text(f"{digest}  {args.artifact.name}\n")
metadata = json.loads(subprocess.check_output(["cargo", "metadata", "--format-version=1", "--locked"], cwd=root))
packages = []
for index, package in enumerate(metadata["packages"]):
    packages.append({"SPDXID": f"SPDXRef-Package-{index}", "name": package["name"],
        "versionInfo": package["version"], "downloadLocation": "NOASSERTION",
        "filesAnalyzed": False, "licenseConcluded": "NOASSERTION",
        "licenseDeclared": package.get("license") or "NOASSERTION",
        "copyrightText": "NOASSERTION"})
spdx = {"spdxVersion": "SPDX-2.3", "dataLicense": "CC0-1.0", "SPDXID": "SPDXRef-DOCUMENT",
    "name": f"convertibled-{version}", "documentNamespace": f"https://github.com/marius4lui/convertibled/spdx/{commit}/{digest}",
    "creationInfo": {"creators": ["Tool: convertibled-candidate-record"],
                     "created": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
    "packages": packages, "relationships": [{"spdxElementId": "SPDXRef-DOCUMENT",
        "relationshipType": "DESCRIBES", "relatedSpdxElement": package["SPDXID"]} for package in packages]}
args.artifact.with_name("dependencies.spdx.json").write_text(json.dumps(spdx, indent=2) + "\n")
print(f"Candidate {version} from {commit}: {digest}")
