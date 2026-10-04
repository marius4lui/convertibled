#!/usr/bin/env bash
# Run only inside an isolated Xvfb display and temporary D-Bus session.
set -euo pipefail
mkdir -p artifacts
export GSK_RENDERER=cairo GTK_A11Y=none G_DEBUG=fatal-criticals
target/debug/convertibled-settings >artifacts/settings.log 2>&1 &
settings_pid=$!
trap 'kill "$settings_pid" 2>/dev/null || true' EXIT
sleep 6
kill -0 "$settings_pid"
import -window root artifacts/settings-overview.png
# A missing daemon/helper is an expected first-run state, but GTK criticals are not.
if grep -E 'CRITICAL|panicked at|segmentation fault' artifacts/settings.log; then
  exit 1
fi
kill "$settings_pid"
wait "$settings_pid" || test "$?" -eq 143
trap - EXIT
