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

The session bus bridge subscribes to `org.convertibled.Session1.Changed` and
reads `GetStatus` asynchronously with a three-second timeout. Service loss or
invalid versioned status exits tablet mode. Calls are canceled on disable.
`ReportApplied` reports observed outcomes, never treats a request as success.

The internal display is identified from Mutter DisplayConfig `is-builtin`
metadata rather than assuming the primary monitor is internal. Mirrored outputs,
missing identity or ambiguous internal outputs retain normal GNOME behavior.
Display changes are observed asynchronously and stale replies are discarded.

Normal main windows on the internal output are maximized on tablet entry.
Dialogs, always-above, fullscreen, skipped-taskbar and external windows are
excluded. Window geometry and maximize flags are restored only while their
last applied state still matches. GNOME runtime must verify Wayland clients'
asynchronous geometry acknowledgements before release acceptance.

Home is a native St surface with editable app search, GNOME favorites and an
adaptive installed-app grid. AppSystem/favorite changes refresh it live; GNOME
application icons and keyboard-focusable buttons provide native app launching.
Search uses GNOME's text widget so the native OSK follows editable focus.

The native dock includes visible labeled Home and Overview alternatives,
favorites and running apps with an active indicator. Favorites and app-state
signals keep it current. Horizontal scrolling prevents clipping on narrow
portrait outputs and touch targets are at least 48 logical pixels.

Overview uses live Clutter clones of internal-output application windows,
with accessible title labels, window activation and two-app split selection.
It observes new windows, workspace switches, window removal and title changes.
It does not activate GNOME's global overview on external displays.

Local widgets show system-local clock/date, UPower display-battery state and
quick actions. Ordered `widgets` GSettings controls visibility and order; unknown
identifiers and duplicates are ignored. UPower uses asynchronous local D-Bus,
with an explicit unavailable label. There are no accounts or network widgets.

The extension entrypoint wires surfaces, service/display observers and window
management. Folding reveals navigation without opening Home or changing app
focus. Lock/inactive shell modes, daemon loss and disable restore owned windows
and hide surfaces. Home/Overview open only through explicit navigation; app
activation closes them. Reduced-motion preferences disable 200 ms opacity easing.
Split selection places two compatible resizable windows and creates a visible
divider to cycle ratios. Display changes recalculate the portrait-aware layout;
window closure removes the divider. Incompatible minimums leave both windows
untouched and produce a concise explanation.

Touch navigation listens only to touchscreen events and coordinates on the
identified internal output. Other input event types propagate immediately;
no keystrokes are stored. Multitouch/cancel stops recognition. The
`gesture-enabled` setting disables it while keeping visible Home/Overview.

GNOME 50 method signatures were checked against its tagged Mutter header:
`maximize()`/`unmaximize()` take no flags; partial restoration uses
`set_maximize_flags()`. GJS minimum-size results contain a boolean followed by
width/height, and frame decoration extents are added before split fit checks.
