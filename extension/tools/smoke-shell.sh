#!/usr/bin/env bash
# Disposable GNOME 50 compositor smoke; never installs in the caller's desktop.
set -euo pipefail
bundle=${1:-"$(cd "$(dirname "$0")/.." && pwd)/dist"}
test -f "$bundle/extension.js"
test -f "$bundle/metadata.json"
for command in gnome-shell gnome-extensions gsettings gdbus glib-compile-schemas dbus-run-session dbus-daemon; do
    command -v "$command" >/dev/null
done
gnome-shell --version | grep -E 'GNOME Shell 50([. ]|$)'
task_root=$(mktemp -d "${TMPDIR:-/tmp}/convertibled-shell-smoke.XXXXXXXX")
task_system_pid=''
trap 'if test -n "$task_system_pid"; then kill "$task_system_pid" 2>/dev/null || true; fi; rm -rf -- "$task_root"' EXIT
export XDG_DATA_HOME="$task_root/data" XDG_CONFIG_HOME="$task_root/config"
export XDG_CACHE_HOME="$task_root/cache" XDG_RUNTIME_DIR="$task_root/runtime"
export GSETTINGS_BACKEND=keyfile LIBGL_ALWAYS_SOFTWARE=1
mkdir -p "$XDG_DATA_HOME/gnome-shell/extensions" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
# A container has no logind/system bus. Provide an isolated transport rather
# than exposing or mutating the host's actual system bus.
mapfile -t task_bus < <(dbus-daemon --session --fork --print-address=1 --print-pid=1)
export DBUS_SYSTEM_BUS_ADDRESS="${task_bus[0]}"
task_system_pid="${task_bus[1]}"
uuid=convertibled@convertibled.org
cp -a "$bundle" "$XDG_DATA_HOME/gnome-shell/extensions/$uuid"
glib-compile-schemas --strict "$XDG_DATA_HOME/gnome-shell/extensions/$uuid/schemas"
export CONVERTIBLED_SMOKE_LOG="$task_root/shell.log"
dbus-run-session -- bash -eu -o pipefail <<'SESSION'
uuid=convertibled@convertibled.org
gsettings set org.gnome.shell disable-user-extensions false
gsettings set org.gnome.shell enabled-extensions "['$uuid']"
gnome-shell --headless --wayland --virtual-monitor=1280x800 >"$CONVERTIBLED_SMOKE_LOG" 2>&1 &
shell_pid=$!
trap 'kill "$shell_pid" 2>/dev/null || true; wait "$shell_pid" 2>/dev/null || true' EXIT
wait_state() {
    local wanted=$1
    for attempt in $(seq 1 40); do
        if ! kill -0 "$shell_pid" 2>/dev/null; then cat "$CONVERTIBLED_SMOKE_LOG"; return 1; fi
        if gdbus call --session --timeout 1 --dest org.gnome.Shell.Extensions \
            --object-path /org/gnome/Shell/Extensions \
            --method org.gnome.Shell.Extensions.GetExtensionInfo "$uuid" 2>/dev/null \
            | grep -Eq "'state': <$wanted([.]0)?>"; then return 0; fi
        sleep 0.5
    done
    LC_ALL=C gnome-extensions info "$uuid" || true
    cat "$CONVERTIBLED_SMOKE_LOG"
    return 1
}
wait_state 1 # GNOME 50 ExtensionState.ACTIVE
gnome-extensions disable "$uuid"
wait_state 2 # GNOME 50 ExtensionState.INACTIVE
gnome-extensions enable "$uuid"
wait_state 1
if grep -Eq 'JS ERROR.*convertibled|Failed to (load|enable) extension.*convertibled' "$CONVERTIBLED_SMOKE_LOG"; then
    cat "$CONVERTIBLED_SMOKE_LOG"; exit 1
fi
printf '%s\n' 'GNOME 50 extension enable/disable/re-enable smoke passed'
SESSION
