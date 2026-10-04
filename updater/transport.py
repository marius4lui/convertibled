"""HTTPS-only bounded downloads restricted to the release artifact host."""
import hashlib
import urllib.parse
import urllib.request
from .model import UpdateError

HOSTS = {"github.com", "api.github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}


def url(value):
    if not isinstance(value, str) or len(value) > 4096:
        raise UpdateError("Invalid release URL")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.fragment:
        raise UpdateError("Release URL is outside trusted HTTPS hosts")
    return value


class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        url(newurl)
        return super().redirect_request(request, fp, code, message, headers, newurl)


def fetch(address, maximum=262144, target=None, expected_hash=None, expected_size=None):
    url(address)
    digest = hashlib.sha256()
    count = 0
    pieces = []
    try:
        with urllib.request.build_opener(Redirects).open(address, timeout=30) as response:
            url(response.url)
            while chunk := response.read(65536):
                count += len(chunk)
                if count > maximum:
                    raise UpdateError("Download exceeds declared limit")
                digest.update(chunk)
                if target is None:
                    pieces.append(chunk)
                else:
                    target.write(chunk)
        if expected_size is not None and count != expected_size:
            raise UpdateError("Download size mismatch")
        if expected_hash is not None and digest.hexdigest() != expected_hash:
            raise UpdateError("Download hash mismatch")
        return b"".join(pieces) if target is None else count
    except (OSError, ValueError) as exc:
        raise UpdateError("Release download failed") from exc
