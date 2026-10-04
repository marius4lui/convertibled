"""Ed25519 signatures use OpenSSL, with no shell interpolation."""
import base64
import re
import subprocess
import tempfile
from pathlib import Path
from .model import UpdateError, canonical, decode, timestamp


def ed25519_public(public_pem):
    if not isinstance(public_pem, str):
        raise UpdateError("Invalid public key")
    match = re.fullmatch(r"\s*-----BEGIN PUBLIC KEY-----\s+([A-Za-z0-9+/=\s]+)-----END PUBLIC KEY-----\s*", public_pem)
    try:
        der = base64.b64decode(re.sub(r"\s", "", match.group(1)), validate=True) if match else b""
    except ValueError as exc:
        raise UpdateError("Invalid public key encoding") from exc
    # Exact RFC 8410 SubjectPublicKeyInfo: id-Ed25519 with absent parameters.
    if len(der) != 44 or not der.startswith(bytes.fromhex("302a300506032b6570032100")):
        raise UpdateError("Trust keys must be Ed25519 public keys")
    return public_pem


def verify(public_pem, payload, signature):
    ed25519_public(public_pem)
    try:
        signature = base64.b64decode(signature, validate=True)
        if len(signature) != 64 or not isinstance(public_pem, str) or "BEGIN PUBLIC KEY" not in public_pem:
            raise ValueError()
        with tempfile.TemporaryDirectory(prefix="convertibled-verify-") as directory:
            directory = Path(directory)
            (directory / "key.pem").write_text(public_pem, encoding="ascii")
            (directory / "payload").write_bytes(payload)
            (directory / "signature").write_bytes(signature)
            result = subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(directory / "key.pem"), "-rawin", "-in", str(directory / "payload"), "-sigfile", str(directory / "signature")], capture_output=True, timeout=15, check=False)
            if result.returncode:
                raise UpdateError("Invalid Ed25519 signature")
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError("Signature verification unavailable or malformed") from exc


def envelope(raw, keys):
    value = decode(raw)
    if not isinstance(value, dict) or set(value) != {"key_id", "payload", "signature"}:
        raise UpdateError("Invalid signed envelope")
    if not isinstance(value["key_id"], str) or value["key_id"] not in keys:
        raise UpdateError("Unknown or revoked signing key")
    verify(keys[value["key_id"]], canonical(value["payload"]), value["signature"])
    return value["payload"]


def keyring(raw, roots, now, minimum=0):
    value = envelope(raw, roots)
    if not isinstance(value, dict) or set(value) != {"schema", "sequence", "issued", "expires", "keys"} or value["schema"] != 1:
        raise UpdateError("Invalid root-signed keyring")
    if type(value["sequence"]) is not int or value["sequence"] < minimum:
        raise UpdateError("Keyring replay")
    if not timestamp(value["issued"]) <= now < timestamp(value["expires"]):
        raise UpdateError("Expired keyring")
    if not isinstance(value["keys"], dict) or not 1 <= len(value["keys"]) <= 16:
        raise UpdateError("Invalid release keyring")
    for key_id, pem in value["keys"].items():
        if not isinstance(key_id, str) or len(key_id) > 64 or not isinstance(pem, str) or len(pem) > 1024:
            raise UpdateError("Invalid signing key")
        ed25519_public(pem)
    return value
