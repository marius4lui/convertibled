#!/usr/bin/env python3
"""Fail closed unless physical acceptance names these exact candidate bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import re

REQUIRED = {
    "fold_focus_restore", "touch_gestures", "osk", "rotation_touch_mapping",
    "split_view", "external_inputs_displays", "suspend_lock_sensor_loss",
    "extension_daemon_failure", "portrait_large_text_screenreader_keyboard",
    "reduced_motion", "clean_install", "invalid_signature_corrupt_download",
    "low_disk_interrupted_update", "logout_next_login", "rollback_uninstall",
}


def validate(record, commit, artifact_hash):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Expected full reviewed commit SHA")
    if record.get("schema") != 1 or record.get("commit") != commit:
        raise ValueError("Acceptance schema or commit mismatch")
    if record.get("artifact_sha256") != artifact_hash:
        raise ValueError("Acceptance describes different artifact bytes")
    if record.get("platform") != {
        "os": "Fedora 44", "desktop": "GNOME 50", "session": "Wayland",
        "device": "ThinkPad X1 Yoga Gen 8", "architecture": "x86_64",
    }:
        raise ValueError("Reference-platform acceptance is required")
    if not isinstance(record.get("reviewer"), str) or not record["reviewer"].strip():
        raise ValueError("Named human acceptance reviewer required")
    if not isinstance(record.get("date"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["date"]):
        raise ValueError("Acceptance date required")
    checks = record.get("checks", {})
    if not isinstance(checks, dict) or set(checks) != REQUIRED:
        raise ValueError("Complete physical and recovery checklist required")
    if any(value != "passed" for value in checks.values()):
        raise ValueError("Every required acceptance check must have passed")
    frames = record.get("animation", {})
    if frames.get("refresh_hz") != 60 or frames.get("recurring_stalls") is not False:
        raise ValueError("60 Hz measurement without recurring stalls required")
    total, within = frames.get("frames"), frames.get("within_budget")
    if type(total) is not int or type(within) is not int or total < 120 or not 0 <= within <= total:
        raise ValueError("At least 120 valid measured animation frames required")
    if within / total < 0.95:
        raise ValueError("Fewer than 95 percent of frames met the frame budget")
    if record.get("limitations") != []:
        raise ValueError("Unresolved acceptance limitations block public release")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    args = parser.parse_args()
    record = json.loads(args.record.read_text(encoding="utf-8"))
    with args.artifact.open("rb") as artifact:
        digest = hashlib.file_digest(artifact, "sha256").hexdigest()
    validate(record, args.commit, digest)
    print("Acceptance record matches candidate commit and artifact bytes")


if __name__ == "__main__":
    main()
