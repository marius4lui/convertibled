"""Strict release contracts. Metadata is authenticated before parsing."""
import datetime as dt
import json
import re


class UpdateError(Exception):
    pass


VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-(alpha|beta)\.([1-9][0-9]*))?$")
NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.@/-]*$")


def version(value):
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise UpdateError("Invalid release version")
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise UpdateError("Duplicate JSON key")
        result[key] = value
    return result


def decode(raw, maximum=262144):
    if len(raw) > maximum:
        raise UpdateError("Metadata exceeds size limit")
    try:
        return json.loads(raw, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError) as exc:
        raise UpdateError("Invalid JSON metadata") from exc


def timestamp(value):
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset() != dt.timedelta(0):
            raise ValueError()
        return parsed
    except (ValueError, TypeError, AttributeError) as exc:
        raise UpdateError("Timestamp must be UTC ISO8601") from exc


def release(value, channel, now, sequence=0):
    required = {"schema", "version", "sequence", "channel", "platform", "issued", "expires", "artifact", "config_schema", "notes"}
    if not isinstance(value, dict) or set(value) != required or value["schema"] != 1:
        raise UpdateError("Unsupported release metadata")
    version(value["version"])
    if channel not in ("stable", "preview") or value["channel"] != channel:
        raise UpdateError("Release channel mismatch")
    if channel == "stable" and "-" in value["version"]:
        raise UpdateError("Preview version in stable channel")
    if type(value["sequence"]) is not int or value["sequence"] <= sequence:
        raise UpdateError("Release replay or downgrade")
    if not timestamp(value["issued"]) <= now < timestamp(value["expires"]):
        raise UpdateError("Release metadata is expired or not yet valid")
    if timestamp(value["expires"]) - timestamp(value["issued"]) > dt.timedelta(days=31):
        raise UpdateError("Release validity exceeds 31 days")
    if value["platform"] != {"os": "fedora", "version": "44", "architecture": "x86_64", "desktop": "GNOME", "desktop_version": "50", "session": "wayland"}:
        raise UpdateError("Unsupported release platform")
    artifact = value["artifact"]
    if not isinstance(artifact, dict) or set(artifact) != {"url", "size", "sha256"}:
        raise UpdateError("Invalid artifact contract")
    if type(artifact["size"]) is not int or not 0 < artifact["size"] <= 512 * 1024 * 1024:
        raise UpdateError("Invalid artifact size")
    if not isinstance(artifact["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]):
        raise UpdateError("Invalid artifact digest")
    if value["config_schema"] != 1 or not isinstance(value["notes"], str) or len(value["notes"]) > 16384:
        raise UpdateError("Unsupported configuration or notes")
    return value
