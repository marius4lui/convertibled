# Native GNOME preview runtime

The Windows preview uses Fedora 44 / GNOME Shell 50.5 in the dedicated
`Convertibled-Demo` WSL2 distribution, displayed by WSLg. It does not use a web
renderer. `run.sh` requires that distribution and a non-root user, creates
private XDG directories and separate session/system D-Bus transports, and runs
Mutter Devkit with software rendering. No product services are installed.

Build `extension/dist` with `npm --prefix extension run build`, then run:

```powershell
wsl -d Convertibled-Demo -u demo -- bash /mnt/c/src/convertibled/demo/native/run.sh
```

`extension.js` is only a development entrypoint: it imports the byte-identical
built production entrypoint as `product.js`. The launcher compares every built
JavaScript module and stylesheet with the source build before startup. All
Home, dock, overview, widgets, split layout and window management use production
classes and native St/Clutter/Mutter rendering. The wrapper supplies the virtual
internal monitor identity and invokes product navigation for scenario controls.
The separate GTK controller and example text apps are demo fixtures.

Settings uses the real Linux application binary. Its optional cached CI binary
must have a verified bundle hash and unchanged Rust sources/lockfile relative
to its recorded source commit. It is not a separately designed settings screen.
Missing privileged updater/configuration/diagnostic services remain unavailable.

Hochformat changes the Devkit viewer size to 800x1280; Querformat uses 1280x800.
`resize.py` binds the X11 viewer to the private session bus and verifies actual
Mutter dimensions. Compositor transforms crashed this software-rendered Devkit
path, so this is a viewport change, not sensor-driven physical rotation.
Sensor state is simulated; service failure removes the mock's Session1 name.
The mock retains its separate demo-control name for recovery.

Run `smoke.py` inside the distribution to exercise the running UI and capture
native PNGs in its private run directory. This tests UI rendering and virtual
window geometry, not physical input, gestures, performance or release acceptance.
Closing Mutter Devkit stops the demo session. Logs and temporary screenshots
remain under `~/.local/state/convertibled-native-demo`; no private desktop profile
or live host system bus is used. Demo code is outside release bundle inputs.

The native smoke also checks both appearances, 125-percent text, reduced motion
and keyboard occlusion. Inspect exposes only the demo surface allocations and
preferences needed for these assertions. The controller changes these settings
only in its private session; system accessibility preferences are untouched.

Additional scenarios exercise the persistent desktop, native GNOME window/app
overviews, manual app minimization, 480x720 and 640x480 viewports. Native Overview
assertions require tablet chrome to be hidden; laptop assertions require the
owned dock strut to be removed. Home is never counted as an application window.
