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
