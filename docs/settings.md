# Native settings implementation

`crates/settings` is a Rust GTK4/libadwaita application targeting Fedora 44 and
GNOME 50. Its preferences pages use native adaptive widgets, named icons,
keyboard focus and the system appearance. All six pages connect to actual
session APIs, installed helper commands or extension-owned preferences. Missing
components produce explicit unavailable states; there are no simulated results.

The presentation model explicitly keeps missing applied state distinct from
requested state. Windows can test the model but cannot validate GTK rendering.
Run `cargo test -p convertibled-settings` and build on Linux with GTK4 and
libadwaita development libraries. Actual accessibility and portrait rendering
require a GNOME session and remain unverified until recorded acceptance.

German/English text is selected from LC_ALL, LC_MESSAGES, then LANG, using the
first nonempty locale. Unsupported locales use English. Version metadata is
inherited from the Rust workspace; settings must not report an independent release.

The async session client uses `org.convertibled.Session1`, five-second call
timeouts, typed replies, bounded JSON and explicit profile validation. It never
blocks GTK on service IO or starts a missing daemon as a side effect of reading.

Overview loads actual session status and offers retry. A connection failure
is visible before the state rows and clears stale values; detected posture,
selected/manual profile, requested and applied workspace, action result and error
remain individually visible.

Profiles and rotation lock are explicit requests over the session API. Merely
opening settings never mutates a profile. Successful requests are described as
requested, with Overview providing confirmation of applied state. Initial
control values come from the service; automatic selection resets manual mode.

Hardware presents service capability support and its explanation independently
for the workspace, rotation, rotation lock, native OSK, split view, input
suppression and scaling. Missing support is
never promoted to available merely because an input sensor was discovered.

Tablet preferences use the extension's GSettings schema, loaded from the
installed bundle if not registered globally. Gestures, dock visibility, split
ratio and ordered local widgets are configurable. Hidden widgets stay hidden
when their reorder button is pressed. The application never changes GNOME's
global theme or external-input preferences.

Updates reads the helper's public status without privileges. Check and prepare
invoke the fixed installed helper through Polkit asynchronously. The UI does
not claim a prepared version is installed and does not force logout or terminate
critical helper operations when the settings window closes.

Diagnostics collects a bounded `convertiblectl --json doctor` response only
when requested. Users can inspect it before an explicit native save dialog
exports a private-permission file using asynchronous Gio IO. Nothing is uploaded.

Update opt-out and stable/preview selection require an explicit save. Existing
system values load before saving is enabled; partial save failures re-read the
actual preferences rather than pretending the entire change was applied.

Recovery and previous-version requests use native confirmation dialogs with
Cancel as the default. The helper still enforces logout requirements; an error
is displayed instead of forcing the user's current graphical session to stop.

Desktop launch metadata and a project-owned scalable icon live under `data/`.
The installer owns their installation/removal; settings does not register itself
in the user's desktop by writing files when launched.

Unsupported status schema versions are rejected. Common state values are
translated for German users while detailed service errors retain their original
diagnostic text, so the UI cannot misrepresent a failure as successful.

The profile editor uses validated core configuration types. It edits native
rotation and OSK tri-state preferences for a single profile, loading the latest
configuration before saving so unrelated profiles are retained. Reset explicitly
sets that profile's actions to unchanged. Configuration saves are authorized by
the active unlocked session service and use its atomic persistence path.

While the settings window has focus, Overview refreshes every two seconds.
Only one request runs at a time; the timer holds weak widget references and
stops when the window is destroyed. Inactive windows do not poll the service.

Rotation and native OSK requests expose separate outcome/error rows in Overview;
a successfully shown workspace cannot conceal a failed native preference change.
