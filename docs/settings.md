# Native settings implementation

`crates/settings` is a Rust GTK4/libadwaita application targeting Fedora 44 and
GNOME 50. Its preferences pages use native adaptive widgets, named icons,
keyboard focus and the system appearance. The initial scaffold is not a
connected settings implementation yet; following batches wire the services.

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
clears stale values; detected posture, selected/manual profile, requested and
applied workspace, action result and error remain individually visible.

Profiles and rotation lock are explicit requests over the session API. Merely
opening settings never mutates a profile. Successful requests are described as
requested, with Overview providing confirmation of applied state. Initial
control values come from the service; automatic selection resets manual mode.

Hardware presents service capability support and its explanation independently
for the workspace, rotation, input suppression and scaling. Missing support is
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
