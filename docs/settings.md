# Native settings implementation

The standalone PreferencesWindow is explicitly nonmodal, so GNOME treats it as
a regular application and Home can minimize it. Confirmation dialogs retain
their native modal behavior.

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
When no explicit lock request exists, the rotation control reflects the reported
native lock state rather than treating the default desired value as a request.

Hardware presents service capability support and its explanation independently
for the workspace, rotation, rotation lock, native OSK, split view, input
suppression, explicitly approved touchscreen gestures and scaling. Missing support is
never promoted to available merely because an input sensor was discovered.

Tablet preferences use the extension's GSettings schema, loaded from the
installed bundle if not registered globally. Gestures, dock visibility, split
ratio and ordered local widgets are configurable. Hidden widgets stay hidden
when their reorder button is pressed. The application never changes GNOME's
global theme or external-input preferences.
Touchscreen gestures require physically touching the Shell setup target on the
built-in display after login or device reconnect. Settings explains this source
approval; no raw input-node path is required for normal setup. Visible navigation
remains available without approval, and software does not infer physical identity.

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

Recovery, previous-version restoration and removal use native confirmation
dialogs with Cancel as the default. The helper queues the confirmed action for
all graphical users' logout, even when automatic updates are off. Settings shows
the pending action and distinguishes waiting from failure; a waiting or failed
request can be cancelled before a critical transaction starts. Removal retains
configuration and personal data. No action forcibly closes a session.

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

All six pages now use compact icon-and-heading introductions and wrapping action areas.
Overview places the selected profile and confirmed workspace summary first,
then groups device observations, workspace state and expandable rotation/OSK
outcomes. Unavailable sessions hide stale detail groups and retain retry.
Actions use native suggested-action styling and at least 44-pixel height.

Updates includes **Install after logout**, with a native confirmation and fixed
`request-activate` helper verb. It explicitly schedules the authenticated prepared
version even when automatic updates are off, without changing that preference.
All graphical users must log out themselves. The public scheduled action is
translated separately from the transaction result; changed candidates/channels,
expired metadata and failed activation require review rather than silent retry.
The separate **Desktop check** row distinguishes a pending desktop check,
actual enabled-workspace health, and a workspace that was not
requested. A services-only success never claims Shell health.

A waiting or failed maintenance request does not suspend the installed version's
desktop acceptance check. Successful health can settle while a user is logged in;
failed health can recover after logout. The failed requested action itself is
never retried automatically. A recovery that changes the installed version makes
an older activation request require review again.
