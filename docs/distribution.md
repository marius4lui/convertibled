# Distribution implementation

The Python standard-library installer/updater owns immutable version directories,
root-only transactions, and OpenSSL Ed25519 verification. Fedora 44 supplies
Python 3 and OpenSSL; these are platform prerequisites, not bundled interpreters.
Release metadata uses schema 1, monotonically increasing per-channel sequences,
UTC issuance/expiry (at most 31 days), an exact platform contract, SHA256/size,
configuration schema and bounded release notes. Stable rejects preview versions.
No production trust key is committed. Without provisioned trust, updates fail
closed. Physical installation and GNOME activation remain acceptance gates.
