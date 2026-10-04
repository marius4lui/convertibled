"""Standalone stable login guard; deliberately imports no versioned code."""
import os
import signal
import socket
import stat


def checked_descriptor(path, create=False):
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if create:
        flags |= os.O_CREAT
    fd = os.open(path, flags, 0o644)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        os.close(fd)
        raise RuntimeError("Admission lock must be a root-owned regular file")
    return fd


def guard():
    import fcntl
    fd = checked_descriptor("/var/lib/convertibled/admission.lock")
    try:
        fcntl.flock(fd, fcntl.LOCK_SH)
        address = os.environ.get("NOTIFY_SOCKET")
        if not address or address[0] not in ("/", "@"):
            raise RuntimeError("Admission requires systemd notify startup")
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as notify:
            notify.connect("\0" + address[1:] if address.startswith("@") else address)
            notify.sendall(b"READY=1")
        # systemd's default SIGTERM ends this process and releases the lock.
        while True:
            signal.pause()
    finally:
        os.close(fd)


if __name__ == "__main__":
    guard()
