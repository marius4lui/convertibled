# GNOME tablet workspace

The extension targets GNOME Shell 50 and is compiled from TypeScript to GJS
ES modules. `cd extension && npm ci && npm test` builds a distributable `dist`
directory. The project installer owns deployment; development never installs
the extension on this Windows host.

GI/Shell bindings are runtime boundaries; portable policy is checked strictly.
GNOME runtime and physical touch acceptance are not established by Node tests.
API references: [GNOME 50 migration](https://gjs.guide/extensions/upgrading/gnome-shell-50.html)
and [Mutter Window](https://gnome.pages.gitlab.gnome.org/mutter/meta/class.Window.html).

Split layout supports half, third and two-thirds, choosing a vertical arrangement
in portrait. A 48 logical-pixel divider is reserved before checking each app's
minimum dimensions. Incompatible pairs produce an explanation without moving
either window. Portable tests cover geometry partitioning and rejection.

Restoration records the original and most recently applied value. Later user
changes forfeit ownership, so leaving tablet mode does not overwrite them.
Resource cleanup runs in reverse order, continues after errors and is idempotent.

App search uses installed application names, descriptions and keywords with
accent-insensitive token matching. Dock order preserves GNOME favorites and
adds running apps once. Grid columns adapt to the integrated display width.

Only touchscreen sequences starting in the integrated display's bottom 24
pixels are candidates. A short upward swipe reveals the dock, a longer swipe
opens Home, and a swipe held for 500 ms opens the app overview. Cancellation and
diagonal gestures do nothing; touchpad gesture handling remains with GNOME.
