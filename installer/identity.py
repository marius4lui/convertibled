"""Create only the fixed non-login hardware service identity."""
import grp
import pwd
from .platform import command
from updater.model import UpdateError


def ensure(run=command):
    try:
        account = pwd.getpwnam("convertibled")
    except KeyError:
        run(["useradd", "--system", "--user-group", "--no-create-home", "--home-dir", "/nonexistent", "--shell", "/usr/sbin/nologin", "convertibled"])
        account = pwd.getpwnam("convertibled")
    if account.pw_uid == 0 or account.pw_shell not in ("/usr/sbin/nologin", "/sbin/nologin") or account.pw_dir != "/nonexistent":
        raise UpdateError("Existing convertibled identity is not a dedicated service account")
    if grp.getgrnam("convertibled").gr_gid != account.pw_gid:
        raise UpdateError("Unexpected service primary group")
    return account.pw_uid
