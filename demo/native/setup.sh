#!/usr/bin/env bash
set -euo pipefail
test "${WSL_DISTRO_NAME:-}" = Convertibled-Demo
test -f /etc/convertibled-demo-runtime
source /etc/os-release
test "$ID" = fedora && test "$VERSION_ID" = 44
dnf install -y gnome-shell gnome-session gnome-settings-daemon dbus-daemon dbus-x11 \
    mesa-dri-drivers python3-gobject gtk4 libadwaita gnome-text-editor nautilus \
    glibc-langpack-de mutter-devkit pipewire wireplumber xdotool
id demo >/dev/null 2>&1 || useradd -m demo
gnome-shell --version | grep -E 'GNOME Shell 50([. ]|$)'
