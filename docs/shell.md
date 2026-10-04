# GNOME tablet workspace

Work-area conversion reads native rectangle fields explicitly. GI boxed geometry
can expose prototype accessors that disappear when spread into a plain object;
the regression uses non-enumerable accessors matching that native boundary.

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

All mutation responses are finished even when no result callback is needed,
so D-Bus failures are observed. Reconnecting a restarted session service sends
fresh capabilities and applied state. Disable sends a bounded unavailable
report independent of ordinary canceled operations.

Window ownership now compares against requested geometry rather than an
immediate snapshot before a Wayland client acknowledges resizing. Adapter tests
simulate asynchronous maximize acknowledgement, later user moves, external
outputs and dialog exclusion. They remain mocks, not compositor acceptance.

Rotation lock uses GNOME Settings Daemon's native touchscreen `orientation-lock`
preference. An absent request preserves the user's native lock; the versioned
desired state carries `rotation_lock_requested` to distinguish this from an
explicit unlock. Owned temporary changes restore on exit, while later native
user changes retain ownership. Actual lock and read-only/absent failures are
reported separately from requests. GNOME remains the rotation/touch mapper.

Hidden surfaces opt out of LayoutManager's automatic fullscreen visibility
tracking, which otherwise overrides an actor's hidden state. Home rests below
the application group and is raised only on explicit navigation. Fullscreen
entry hides navigation; leaving fullscreen restores it only in active tablet mode.

Installed-app tiles provide explicit touch-sized add/remove favorite controls.
These use GNOME's existing AppFavorites owner so Home, the tablet dock and the
desktop favorites share one preference instead of maintaining divergent lists.

Optional `dock-autohide` hides the application strip when app focus returns,
while leaving labeled Home/Overview navigation visible. Bottom-edge navigation
reveals the full app strip, and changing the preference updates it immediately.

Surface allocation observes the native keyboard box and reserves its occupied
internal-output height. Navigation moves above the OSK and Home stays scrollable;
the extension never opens/closes the keyboard directly. GNOME owns editable
focus, authentication, keyboard lifetime and third-party app occlusion handling.

The extension reports explicit startup health with its bundle `version-name`
through `Session1.ReportShellHealth(version, healthy)`. A completed UI/resource
setup is healthy even in laptop mode; a setup exception cleans resources and
reports failure. This receipt is distinct from tablet applied state, allowing
the update helper to evaluate the candidate at the next real login.

Native-boundary mocks exercise complete extension enable/fold/lock/disable,
focus preservation, timer/signal/chrome cleanup, reduced motion and keyboard
allocation. Tests import the built entrypoint, rather than mirroring controller
logic. Their native surfaces are test doubles and cannot prove GNOME rendering.

`extension/tools/smoke-shell.sh extension/dist` launches GNOME 50 with a headless
Wayland virtual monitor, an isolated user D-Bus and temporary XDG directories.
It compiles schemas and requires enable/disable/re-enable extension states.
Software rendering and the virtual output prove startup/lifecycle only, never
physical tablet behavior. The script was prepared from GNOME 50 CLI/extension
contracts on Windows; its first Linux execution remains a CI requirement.

Profile `rotation` and `osk` tri-state actions update native preferences only
when configured. Explicit rotation lock takes precedence over profile rotation.
OSK coordination uses `org.gnome.desktop.a11y.applications.screen-keyboard-enabled`
and restores only owned values; it does not repeatedly show or dismiss keyboards.

A later native user preference edit relinquishes ownership and blocks repeated
reconciliation of the same request. Changing the requested action or leaving
the mode resets that block. Adapter tests verify that D-Bus feedback cannot
silently reapply a preference after a user has deliberately changed it.

Applied reports include independent `rotation` and `osk` action outcomes:
requested action, actual native preference, status and error. Missing native
preferences never turn successful workspace activation into an action success.
Optional action fields are validated before any desktop preference is touched.
Delayed notifications matching the owned write retain ownership.

Built-in interaction text is available in German and English according to
GLib's language preferences. Installed application names remain their native
localized names and diagnostics retain stable English descriptions.

GNOME 50 AppSystem's installed list contains Gio AppInfo records, not ShellApp
objects. Home resolves each ID through `lookup_app` for icons/launching. A native
adapter test covers that distinction with realistic nonempty app metadata.

Smoke checks use the versioned extension D-Bus numeric state (ACTIVE=1,
INACTIVE=2), avoiding translated CLI labels and renamed GNOME 50 states.

Home keeps search outside one scrollable body containing favorites, widgets and
the app grid. Narrow displays, large fonts and the OSK therefore cannot make
the bottom widgets unreachable through fixed-height content accumulation.

The headless smoke owns a second isolated D-Bus transport for system proxies;
it never connects to the CI host's system bus. Fedora container startup required
that transport for GNOME LoginManager/TimeLimits initialization. Absent actual
logind/UPower services remain explicit container limitations.

Surfaces inherit GNOME popup theme colors instead of hard-coded backgrounds,
including light/dark and text contrast. Split selections expose native checked
button state, and the split action becomes focusable/reactive only after two
windows are selected. Physical screen-reader and large-text review remains open.

The divider uses an accessible icon so its allocation fits the reserved 48-pixel
strip. A labeled dock action ends split and maximizes only windows whose split
geometry is still owned. Rejected ratio changes retain the previous ratio;
rotation into an incompatible layout ends split rather than keeping stale bounds.

New application windows are handled once before redraw, after their compositor
actor exists, rather than maximizing during early `window-created` setup.
Pending compositor callbacks are canceled on disable and per-window errors stay
bounded. Input focus and application text are never sampled for diagnostics.

Gesture recognition and explicit navigation defer while GNOME holds a modal
grab or its native global Overview is open. Authentication/system dialogs keep
their existing input ownership; the extension creates no modal authentication
surface and never replaces the lock/login workflow.

Native profile actions are reconciled independently of tablet workspace:
explicit laptop rotation/OSK actions also apply in an active, unlocked user
session. Inactive/locked states restore owned preferences. Action reports compare
the actual preference with the request and never claim success on a mismatch.

The visible dock reserves a bottom strut only on the internal output, keeping
maximized application controls above navigation. Position calculations remove
only that owned inset to avoid repeated self-shrinking work areas. Native work
area changes refresh maximize ownership; split allocations exclude the dock.
Portable regression tests cover inset feedback, OSK placement and external bounds.

The battery/system widget includes the selected native mode and an explicit
session-service-unavailable state. Rotation quick action exposes actual native
checked state. Widget adapter tests cover ordered visibility, unavailable/live
battery updates and clock timer cleanup. Split space also excludes visible OSK.

GNOME's extension gettext domain `convertibled` now owns translations. The
bundle contains `locale/de/LC_MESSAGES/convertibled.mo` compiled from `po/de.po`
with a deterministic Node compiler; the English source strings are the fallback.
Catalog tests inspect real GNU MO tables and UTF-8 translations. Linux CI can
independently validate the PO using `msgfmt --check -o /dev/null extension/po/de.po`.

Home caches installed metadata until AppSystem changes and initially constructs
at most 40 app tiles per query. An explicit Show more action keeps every match
reachable without building hundreds of actors on each edit. Live window clones
update scale when source geometry changes; hidden overview ignores unrelated
new-window/workspace refreshes. Frame-budget acceptance still requires hardware.

The bottom 24-pixel strip owns candidate touch sequences from BEGIN through END
or CANCEL, so underlying apps/buttons never receive a partial sequence. Canceled
candidates remain consumed until their end. A stationary 500 ms hold beyond the
swipe threshold opens Overview while the finger is still down; timers cancel on
diagonal/multitouch/disable. Source filtering currently proves touchscreen type
and internal-output coordinates. Physical provenance is not inferred from those
properties: gesture support remains unavailable until explicit current-login
approval binds a connected native Clutter device object.

Bundle metadata reads `workspace.package.version` from canonical Cargo.toml
during every build. Startup health therefore uses the installed product version,
including future upgrades. Build cleanup removes only the resolved extension
`dist` directory and prevents deleted source modules surviving in release bundles.

`touchscreen-device-node` is an explicit current-login grant for the physically
confirmed integrated touchscreen. Startup and device removal clear it; event
number reuse cannot grant another device because checks compare the actual
native device object. Wrong/absent nodes remain unsupported and visible
navigation works throughout. Reference-device setup must physically confirm the
chosen source, and reconnect/login requires fresh approval. No input device is
disabled and no keystrokes or raw event streams are recorded.

Normal setup uses the visible internal-output dock target **Touch to enable
gestures**. Only a real touchscreen TOUCH_BEGIN from a currently connected
native device can approve it; mouse/keyboard activation does nothing. The node
key is an internal optional handoff, not the ordinary setup interface. This
explicit physical confirmation grants the actual device object until removal or
disable and does not infer physical internal identity from vendor/name strings.

Touch setup and End split live in the dock's horizontally scrollable strip,
keeping Home/Overview reachable in portrait and large-text layouts. App refresh
does not destroy the separate setup/action controls.

Split placement snapshots both window states and their existing restoration
ownership. A synchronous Mutter exception, including after the second window
has already been unmaximized, rolls back every attempted window before returning
failure. The divider and successful split state are created only after both
placements succeed. A notification distinguishes successful rollback from an
incomplete rollback; failed rollback drops that window's ownership rather than
claiming restoration succeeded. A Node native-boundary regression injects the
second placement exception and checks both positions, maximization and later
laptop restoration. Actual asynchronous client geometry remains a device test.

The touchscreen gate obtains the Clutter seat through
`global.stage.context.get_backend().get_default_seat()`, matching
[GNOME Shell 50.5 keyboard.js](https://github.com/GNOME/gnome-shell/blob/50.5/js/ui/keyboard.js).
`global.backend` is a Meta.Backend and does not expose that seat method. The
native-boundary mock deliberately preserves this distinction so the incorrect
access fails startup tests. Clutter 50.5
[seat declarations](https://github.com/GNOME/mutter/blob/50.5/clutter/clutter/clutter-seat.h),
[seat signals](https://github.com/GNOME/mutter/blob/50.5/clutter/clutter/clutter-seat.c)
and [input device declarations](https://github.com/GNOME/mutter/blob/50.5/clutter/clutter/clutter-input-device.h)
confirm `list_devices`, `device-removed`, `get_device_type` and `get_device_node`.
The regression exercises seat discovery, approval and removal through extension
startup; physical touchscreen acceptance remains separate.

The disposable native smoke canonicalizes and freezes its own mktemp root.
After compositor/bus shutdown, cleanup retries deletion up to 20 times with a
quarter-second drain between attempts, covering short-lived cache writers.
The original failing test status is retained; persistent cleanup failure also
fails an otherwise successful test. Cleanup refuses unexpected root names.
