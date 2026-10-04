# Windows preview of the actual GNOME UI

Double-click `start.cmd`, or run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File demo/start.ps1
```

The **Mutter Development Kit** window displays the actual GNOME Shell extension.
The separate **convertibled — Demo-Steuerung** window switches scenarios and
opens the real GTK/libadwaita settings application. The previous WPF imitation
has been removed. Production UI changes are rebuilt on each fresh launch.
If the demo is already running, close its Devkit window before rebuilding.

Home, dock, app search, live overview, split view and widgets are rendered by
the same product modules and stylesheet, inside GNOME 50 on Fedora 44. The
controller and two editable sample applications are fixtures; sensor state
and Session1 service are simulated. The preview uses WSLg to appear on Windows,
with no browser or web renderer. See [native runtime details](native/README.md).

Choose Laptop, Tablet, Home, Übersicht, Geteilte Ansicht, Hochformat, Querformat,
Tastatur, Hell/Dunkel, Große/Normale Schrift, Weniger Bewegung/Animationen or
Fehler simulieren. Home/Tablet recover after failure.
The split divider changes ratios. Close the Devkit window to stop the session.
Real update installation, privileged profile configuration and diagnostics are
unavailable here; their native UI reports the missing backend.

For initial setup on Windows 11 with WSL2/WSLg and Node/npm installed, run
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File demo/setup.ps1`.
It creates only the named demo distribution and installs its Linux prerequisites.
It needs downloads and several GB of disk space. Settings can use a locally
built Linux executable or a source-verified internal CI bundle; see setup help.
Pass `-LinuxSettingsBinary <path>` for your own current Linux build, or
`-CandidateDirectory <directory>` containing `candidate.json` and its bundle.
The latter checks SHA-256 and Git source equality. Fresh starts reject a cached
candidate when Rust sources diverge; explicitly provided binaries are the
developer's responsibility to rebuild after Rust changes.
The runtime is stored in `%LOCALAPPDATA%/convertibled-demo`. The Windows default
distribution and existing Linux desktops are not used as the product session.

`demo/start.ps1 -Check` checks the running UI. The native smoke command is:

```powershell
wsl -d Convertibled-Demo -u demo -- python3 /mnt/c/src/convertibled/demo/native/smoke.py
```

Adjust the repository path if needed. The smoke exercises real virtual window
geometry and captures native screenshots. Hardware, touch, physical rotation,
display scaling, fonts and driver-dependent rendering still need target-device
acceptance. This preview demonstrates the implemented UI, not a release claim.
