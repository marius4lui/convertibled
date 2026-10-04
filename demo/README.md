# Windows scenario demo

Run `powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File demo/start.ps1`
from the repository root. This opens an interactive WPF window using built-in
Windows components, without a browser, server, installation or administrator rights.

This is an illustrative simulator, not the GTK application or GNOME extension.
It approximates layout and demonstrates selected product journeys. It does not
validate native GNOME appearance, live previews, gestures, hardware, accessibility,
performance or update acceptance. No system settings, devices or services change.
All displayed sensor, battery, clock, application and update data are fixtures.

Choose one of thirteen scenarios. Open Home, search demo apps, switch apps,
change split ratios, rotate the display, toggle light/dark appearance, type in
the sample note, or simulate update/logout/recovery. Notes remain in memory until
the window closes. The keyboard drawing is illustrative and does not send keys.
The desktop preview scales to the window; target sizes in the preview are not
physical touch measurements. Simulated update actions are illustrative controls,
not the production transaction engine or a substitute for its state validation.

For local rendering verification, use `-SnapshotDirectory .tools/demo-smoke`.
This opens a temporary demo window, renders each fixture, checks sample actions,
then closes. Generated images belong outside version control.
