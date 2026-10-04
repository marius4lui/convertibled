#!/usr/bin/env bash
# Run only inside the dedicated WSL distribution, never a login desktop.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
test "${WSL_DISTRO_NAME:-}" = Convertibled-Demo
test "$(id -u)" != 0
gnome-shell --version | grep -E 'GNOME Shell 50([. ]|$)'
test -f "$repo/extension/dist/extension.js"
base="$HOME/.local/state/convertibled-native-demo"
mkdir -p "$base"
export PATH="$base/bin:$PATH"
exec 9>"$base/run.lock"
flock -n 9 || { echo 'The native demo is already running.'; exit 1; }
root=$(mktemp -d "$base/run.XXXXXXXX")
export CONVERTIBLED_DEMO_ROOT="$root" CONVERTIBLED_DEMO_PRIVATE_BUS=1
export CONVERTIBLED_DEMO_REPO="$repo"
export CONVERTIBLED_DEMO_WAYLAND_DISPLAY=convertibled-demo
export CONVERTIBLED_DEMO_SETTINGS_BINARY="$base/bin/convertibled-settings"
export CONVERTIBLED_DEMO_VERSION=$(python3 -c 'import sys,tomllib; print(tomllib.load(open(sys.argv[1],"rb"))["workspace"]["package"]["version"])' "$repo/Cargo.toml")
export XDG_DATA_HOME="$root/data" XDG_CONFIG_HOME="$root/config"
export XDG_CACHE_HOME="$root/cache" XDG_RUNTIME_DIR="$root/runtime"
export GSETTINGS_BACKEND=keyfile LIBGL_ALWAYS_SOFTWARE=1 LANG=de_DE.UTF-8 GSK_RENDERER=cairo GDK_BACKEND=x11
mkdir -p "$XDG_DATA_HOME/gnome-shell/extensions" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_RUNTIME_DIR"
mkdir -p "$XDG_DATA_HOME/applications" "$XDG_DATA_HOME/icons/hicolor/scalable/apps"
cp "$repo/data/applications/org.convertibled.Settings.desktop" "$XDG_DATA_HOME/applications/"
cp "$repo/data/icons/org.convertibled.Settings.svg" "$XDG_DATA_HOME/icons/hicolor/scalable/apps/"
chmod 700 "$root" "$XDG_RUNTIME_DIR"
mkdir -p "$root/bin"
cat > "$root/bin/convertibled-settings" <<'LAUNCH'
#!/bin/sh
exec env GDK_BACKEND=wayland WAYLAND_DISPLAY="$CONVERTIBLED_DEMO_WAYLAND_DISPLAY" "$CONVERTIBLED_DEMO_SETTINGS_BINARY"
LAUNCH
chmod +x "$root/bin/convertibled-settings"
export PATH="$root/bin:$PATH"
ln -s /mnt/wslg/runtime-dir/wayland-0 "$XDG_RUNTIME_DIR/wayland-0"
uuid=convertibled@convertibled.org
bundle="$XDG_DATA_HOME/gnome-shell/extensions/$uuid"
cp -a "$repo/extension/dist" "$bundle"
mv "$bundle/extension.js" "$bundle/product.js"
cp "$repo/demo/native/extension.js" "$bundle/extension.js"
cmp "$bundle/product.js" "$repo/extension/dist/extension.js"
for file in "$repo"/extension/dist/*.js; do
    test "$(basename "$file")" = extension.js || cmp "$file" "$bundle/$(basename "$file")"
done
cmp "$repo/extension/dist/stylesheet.css" "$bundle/stylesheet.css"
glib-compile-schemas --strict "$bundle/schemas"
export GSETTINGS_SCHEMA_DIR="$bundle/schemas"
export CONVERTIBLED_DEMO_RESIZE="$repo/demo/native/resize.py"
mapfile -t bus < <(dbus-daemon --session --fork --print-address=1 --print-pid=1)
export DBUS_SYSTEM_BUS_ADDRESS="${bus[0]}"
trap 'kill "${bus[1]}" 2>/dev/null || true' EXIT
printf '%s\n' "$root" > "$base/latest"
dbus-run-session -- bash "$repo/demo/native/session.sh"
