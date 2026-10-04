#!/bin/sh
# Explicit first-login onboarding in the installing user's GNOME session.
set -eu
if [ "$(id -u)" -eq 0 ]; then
    printf '%s\n' 'Run onboarding as your normal GNOME user, never as root.' >&2
    exit 1
fi
case "${1-}" in
    '') operation=enable ;;
    --disable) operation=disable ;;
    *) printf '%s\n' 'Usage: finish-user.sh [--disable]' >&2; exit 2 ;;
esac
if [ "$#" -gt 1 ]; then exit 2; fi
if [ "${XDG_SESSION_TYPE-}" != wayland ]; then
    printf '%s\n' 'Onboarding requires your GNOME Wayland session.' >&2
    exit 1
fi
case "$(gnome-shell --version)" in
    'GNOME Shell 50'*) ;;
    *) printf '%s\n' 'GNOME Shell 50 is required.' >&2; exit 1 ;;
esac
uuid=convertibled@convertibled.org
if ! gnome-extensions info "$uuid" >/dev/null 2>&1; then
    printf '%s\n' 'Log out and back in so GNOME discovers the installed extension.' >&2
    exit 1
fi
printf '%s\n' 'GNOME retains lock/login/OSK ownership. Input suppression and scaling stay off.' >&2
exec gnome-extensions "$operation" "$uuid"
