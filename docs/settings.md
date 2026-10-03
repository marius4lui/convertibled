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
