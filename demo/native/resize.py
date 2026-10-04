#!/usr/bin/env python3
"""Resize only the private demo's X11 Devkit viewer and verify real monitor size.

Mutter 50.5 mdk/mdk-monitor.c routes viewer allocation through mdk_stream_resize.
Compositor transforms are unsafe for this software-rendered PipeWire setup.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("orientation", choices=("portrait", "landscape", "compact", "small"))
    args = parser.parse_args()
    root = Path(os.environ.get("CONVERTIBLED_DEMO_ROOT", "/invalid")).resolve()
    address = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
    if (os.environ.get("CONVERTIBLED_DEMO_PRIVATE_BUS") != "1"
            or root.parent.name != "convertibled-native-demo"
            or not root.name.startswith("run.")
            or not address or (root / "bus-address").read_text().strip() != address):
        parser.error("Requires the running isolated native demo bus")
    connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)

    def dimensions():
        state = connection.call_sync("org.gnome.Mutter.DisplayConfig",
            "/org/gnome/Mutter/DisplayConfig", "org.gnome.Mutter.DisplayConfig",
            "GetCurrentState", None, None, Gio.DBusCallFlags.NO_AUTO_START,
            3000, None).unpack()
        monitors = state[1]
        if len(monitors) != 1 or monitors[0][0][1:3] != ("MetaVendor", "Virtual remote monitor"):
            raise ValueError("Requires exactly one Devkit virtual monitor")
        current = next((mode for mode in monitors[0][1] if mode[-1].get("is-current")), None)
        if current is None:
            raise ValueError("Nested monitor has no active mode")
        return current[1:3]

    def xdo(*command):
        return subprocess.check_output(["xdotool", *map(str, command)],
            text=True, timeout=4, env=dict(os.environ, DISPLAY=":0")).strip()

    # Bind the viewer to the private bus, not an unrelated desktop's same title.
    pids = []
    for process in Path("/proc").iterdir():
        if not process.name.isdigit():
            continue
        try:
            cmd = (process / "cmdline").read_bytes().split(b"\0")[0]
            env = (process / "environ").read_bytes().split(b"\0")
            if (cmd.endswith(b"/mutter-devkit")
                    and ("DBUS_SESSION_BUS_ADDRESS=" + address).encode() in env):
                pids.append(process.name)
        except OSError:
            continue
    if len(pids) != 1:
        raise ValueError("Could not identify the private demo's unique Devkit viewer")
    windows = xdo("search", "--onlyvisible", "--pid", pids[0]).splitlines()
    candidates = [window for window in windows if "Mutter" in xdo("getwindowname", window)]
    if len(candidates) != 1:
        raise ValueError("Could not identify the private demo's unique X11 viewer window")
    window = candidates[0]
    geometry = dict(line.split("=", 1) for line in xdo("getwindowgeometry", "--shell", window).splitlines())
    old_width, old_height = dimensions()
    target_width, target_height = {"portrait": (800, 1280), "landscape": (1280, 800),
                                   "compact": (480, 720), "small": (640, 480)}[args.orientation]
    # Preserve the viewer's native header/decorations while changing content size.
    width = target_width + int(geometry["WIDTH"]) - old_width
    height = target_height + int(geometry["HEIGHT"]) - old_height
    xdo("windowsize", window, width, height)
    for _attempt in range(60):
        actual = dimensions()
        if actual == (target_width, target_height):
            print(json.dumps({"orientation": args.orientation,
                              "width": actual[0], "height": actual[1]}))
            return 0
        time.sleep(0.05)
    raise ValueError("Viewer resized, but compositor did not acknowledge requested dimensions")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (GLib.Error, ValueError, OSError, subprocess.SubprocessError) as error:
        print("Demo orientation unavailable: " + str(error), file=sys.stderr)
        sys.exit(1)
