#!/usr/bin/env bash
set -euo pipefail
test "${CONVERTIBLED_DEMO_PRIVATE_BUS:-}" = 1
root=$CONVERTIBLED_DEMO_ROOT
repo=$CONVERTIBLED_DEMO_REPO
printf '%s\n' "$DBUS_SESSION_BUS_ADDRESS" > "$root/bus-address"
gsettings set org.gnome.shell disable-user-extensions false
gsettings set org.gnome.shell enabled-extensions "['convertibled@convertibled.org']"
gsettings set org.gnome.shell welcome-dialog-last-shown-version '50.5'
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.desktop.screensaver lock-enabled false
gsettings set org.gnome.desktop.notifications show-banners false
gsettings set org.gnome.desktop.interface color-scheme prefer-dark
gsettings set org.gnome.desktop.interface enable-animations true
pids=()
cleanup() { for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done; wait || true; }
trap cleanup EXIT
pipewire >"$root/pipewire.log" 2>&1 & pids+=("$!")
wireplumber >"$root/wireplumber.log" 2>&1 & pids+=("$!")
python3 "$repo/demo/native/control.py" --service-only >"$root/service.log" 2>&1 & pids+=("$!")
gnome-shell --devkit --wayland --no-x11 --wayland-display=convertibled-demo >"$root/shell.log" 2>&1 &
shell_pid=$!; pids+=("$shell_pid")
ready=false
for attempt in $(seq 1 80); do
    kill -0 "$shell_pid" 2>/dev/null || { cat "$root/shell.log"; exit 1; }
    if gdbus call --session --timeout 1 --dest org.convertibled.Demo --object-path /org/convertibled/Demo \
        --method org.convertibled.Demo.Inspect >"$root/state.json" 2>/dev/null; then ready=true; break; fi
    sleep 0.5
done
$ready || { cat "$root/shell.log"; exit 1; }
for attempt in $(seq 1 30); do
    if python3 "$repo/demo/native/resize.py" landscape >"$root/resize.log" 2>&1; then break; fi
    sleep 0.3
done
export CONVERTIBLED_DEMO_WAYLAND_DISPLAY=convertibled-demo
python3 "$repo/demo/native/control.py" --controls-only >"$root/controls.log" 2>&1 & pids+=("$!")
WAYLAND_DISPLAY=convertibled-demo GDK_BACKEND=wayland python3 "$repo/demo/native/control.py" --samples-only >"$root/samples.log" 2>&1 & pids+=("$!")
sleep 2
gdbus call --session --dest org.convertibled.Demo --object-path /org/convertibled/Demo \
    --method org.convertibled.Demo.Scenario home
echo "Native demo ready. Logs: $root"
wait "$shell_pid"
