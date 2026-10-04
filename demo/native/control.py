#!/usr/bin/env python3
"""Disposable native demo controls and simulated Session1 transport, never hardware."""
import argparse
import json
import os
import sys

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

NAME = "org.convertibled.Session1"
DEMO_STATE = "org.convertibled.DemoState"
PATH = "/org/convertibled/Session1"
XML = """<node><interface name="org.convertibled.Session1">
<method name="GetStatus"><arg type="s" direction="out"/></method>
<method name="GetCapabilities"><arg type="s" direction="out"/></method>
<method name="SetProfile"><arg type="s" direction="in"/></method>
<method name="SetRotationLock"><arg type="b" direction="in"/></method>
<method name="ReportApplied"><arg type="s" direction="in"/></method>
<method name="ReportShellHealth"><arg type="s" direction="in"/><arg type="b" direction="in"/></method>
<method name="InjectScenario"><arg type="s" direction="in"/></method>
<signal name="Changed"><arg type="s"/></signal>
</interface></node>"""


class SessionMock:
    def __init__(self, connection):
        self.connection = connection
        self.failed = False
        self.health = None
        self.status = {
            "schema_version": 1, "revision": 0, "version": os.environ["CONVERTIBLED_DEMO_VERSION"],
            "backend": "gnome50-wayland-demo", "override_origin": "automatic",
            "observation": {"posture": "unknown", "orientation": "unknown",
                            "source": "demo-simulated", "confidence": "none"},
            "profile": "laptop", "manual_override": None,
            "desired": {"tablet_workspace": False, "rotation_lock": False,
                        "rotation_lock_requested": False, "rotation": "unchanged",
                        "osk": "unchanged"},
            "applied": {"tablet_workspace": False, "rotation_lock": False,
                        "status": "unavailable", "error": "Waiting for actual demo Shell report",
                        "action_outcomes": {}}, "active": True, "locked": False,
        }
        keys = ("tablet_workspace", "rotation", "rotation_lock", "osk", "split_view",
                "touchscreen_gestures", "internal_input_suppression", "scaling")
        self.capabilities = {key: {"supported": False,
                            "reason": "Unavailable in simulated hardware demo"} for key in keys}
        self.capabilities["schema_version"] = 1
        info = Gio.DBusNodeInfo.new_for_xml(XML).interfaces[0]
        self.registration = connection.register_object(PATH, info, self.call, None, None)
        self.owner = Gio.bus_own_name_on_connection(connection, NAME,
            Gio.BusNameOwnerFlags.NONE, None, None)
        self.demo_owner = Gio.bus_own_name_on_connection(connection, DEMO_STATE,
            Gio.BusNameOwnerFlags.NONE, None, None)

    def changed(self):
        self.status["revision"] += 1
        self.connection.emit_signal(None, PATH, NAME, "Changed",
                                    GLib.Variant("(s)", (json.dumps(self.status),)))

    def reconcile(self):
        state = self.status
        state["profile"] = state["manual_override"] or (
            "tablet" if state["observation"]["posture"] == "folded" else "laptop")
        state["override_origin"] = "session-manual" if state["manual_override"] else "automatic"
        state["desired"]["tablet_workspace"] = state["profile"] != "laptop" and not self.failed

    def inject(self, scenario):
        if scenario not in ("laptop", "tablet", "portrait", "landscape", "failure"):
            raise ValueError("Unknown sensor scenario")
        self.failed = scenario == "failure"
        if self.failed and self.owner:
            Gio.bus_unown_name(self.owner)
            self.owner = 0
        elif not self.failed and not self.owner:
            self.owner = Gio.bus_own_name_on_connection(self.connection, NAME,
                Gio.BusNameOwnerFlags.NONE, None, None)
        if scenario in ("laptop", "tablet"):
            self.status["manual_override"] = None
            self.status["observation"]["posture"] = "folded" if scenario == "tablet" else "laptop"
        elif scenario in ("portrait", "landscape"):
            self.status["observation"]["orientation"] = "left-up" if scenario == "portrait" else "normal"
        if self.failed:
            self.status["observation"]["posture"] = "unknown"
        self.reconcile()
        self.changed()

    def call(self, connection, sender, path, interface, method, parameters, invocation):
        try:
            args = parameters.unpack()
            if method == "GetStatus":
                invocation.return_value(GLib.Variant("(s)", (json.dumps(self.status),)))
                return
            if method == "GetCapabilities":
                invocation.return_value(GLib.Variant("(s)", (json.dumps(self.capabilities),)))
                return
            if method == "SetProfile":
                profile = args[0]
                if profile not in ("auto", "laptop", "tablet", "stand", "tent"):
                    raise ValueError("Choose auto, laptop, tablet, stand or tent")
                self.failed = False
                self.status["manual_override"] = None if profile == "auto" else profile
                self.reconcile()
                self.changed()
            elif method == "SetRotationLock":
                self.status["desired"].update(rotation_lock=args[0], rotation_lock_requested=True)
                self.changed()
            elif method == "InjectScenario":
                self.inject(args[0])
            elif method == "ReportShellHealth":
                self.health = args
            elif method == "ReportApplied":
                if len(args[0].encode()) > 8192:
                    raise ValueError("Report exceeds 8192 bytes")
                report = json.loads(args[0])
                if not isinstance(report, dict) or report.get("status") not in (
                        "applied", "failed", "unsupported", "unavailable"):
                    raise ValueError("Invalid applied report")
                for key in ("tablet_workspace", "rotation_lock"):
                    if type(report.get(key)) is not bool:
                        raise ValueError("Invalid applied field: " + key)
                applied = {key: report.get(key) for key in (
                    "tablet_workspace", "rotation_lock", "status", "error")}
                applied["action_outcomes"] = report.get("action_outcomes", {})
                caps = report.get("capabilities", {})
                for key, value in caps.items():
                    if key in self.capabilities and type(value) is bool:
                        self.capabilities[key] = {"supported": value,
                            "reason": "Actual demo Shell report; physical acceptance unverified"}
                self.capabilities["rotation"] = self.capabilities["rotation_lock"].copy()
                if "gesture_reason" in caps:
                    self.capabilities["touchscreen_gestures"]["reason"] = caps["gesture_reason"]
                if applied != self.status["applied"]:
                    self.status["applied"] = applied
                    self.changed()
            else:
                raise ValueError("Unsupported demo method")
            invocation.return_value(GLib.Variant("()", ()))
        except (ValueError, TypeError, KeyError) as error:
            invocation.return_dbus_error("org.freedesktop.DBus.Error.InvalidArgs", str(error))


def launch_controls(connection, samples_only=False, controls_only=False):
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    class Controls(Gtk.Application):
        def __init__(self):
            super().__init__(application_id="org.convertibled.DemoControls",
                             flags=Gio.ApplicationFlags.NON_UNIQUE)
            self.samples = []

        def scenario(self, value):
            self.message.set_text("Szenario angefordert: " + value)
            def finished(source, result):
                try:
                    reply = source.call_finish(result).unpack()[0]
                    self.message.set_text("Szenario angefordert: " + value)
                except GLib.Error as error:
                    self.message.set_text("Demo-Shell nicht erreichbar: " + error.message)
            connection.call("org.convertibled.Demo", "/org/convertibled/Demo",
                "org.convertibled.Demo", "Scenario", GLib.Variant("(s)", (value,)),
                GLib.VariantType.new("(s)"), Gio.DBusCallFlags.NO_AUTO_START,
                4000, None, finished)

        def settings(self, _button):
            executable = GLib.find_program_in_path("convertibled-settings")
            if not executable:
                self.message.set_text("Einstellungen wurden noch nicht gebaut.")
                return
            launcher = Gio.SubprocessLauncher.new(Gio.SubprocessFlags.NONE)
            display = os.environ.get("CONVERTIBLED_DEMO_WAYLAND_DISPLAY")
            if display:
                launcher.setenv("WAYLAND_DISPLAY", display, True)
            try:
                launcher.spawnv([executable])
                self.message.set_text("Native Produkteinstellungen geöffnet.")
            except GLib.Error as error:
                self.message.set_text(error.message)

        def sample(self, title):
            window = Gtk.ApplicationWindow(application=self, title=title,
                                           default_width=600, default_height=450)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            for side in ("top", "bottom", "start", "end"):
                getattr(box, "set_margin_" + side)(20)
            box.append(Gtk.Label(label="Native GTK-Anwendung • editierbarer Text",
                                 xalign=0, wrap=True))
            entry = Gtk.Entry(placeholder_text="Hier schreiben und die native GNOME-Tastatur testen")
            box.append(entry)
            text = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
            text.get_buffer().set_text(
                "Dein Text bleibt beim Wechsel zwischen Laptop, Tablet, Übersicht und Split erhalten.\n\n"
                "Dieses echte GTK-Fenster wird vom laufenden GNOME-Compositor verwaltet.")
            scroll = Gtk.ScrolledWindow(vexpand=True, child=text)
            box.append(scroll)
            window.set_child(box)
            self.samples.append(window)
            window.present()

        def do_activate(self):
            if samples_only:
                self.sample("Demo notes A")
                self.sample("Demo notes B")
                return
            window = Gtk.ApplicationWindow(application=self, title="convertibled — Demo-Steuerung",
                                           default_width=520, default_height=590)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            for side in ("top", "bottom", "start", "end"):
                getattr(box, "set_margin_" + side)(18)
            box.append(Gtk.Label(label="Echte GNOME-Oberfläche • simulierte Sensoren", wrap=True, xalign=0))
            box.append(Gtk.Label(label="Die Demo verwendet die Erweiterung des Produkts. "
                "Diese Steuerung schaltet Szenarien in einer isolierten Sitzung. "
                "Touch-Gesten und echte Hardware sind damit noch nicht geprüft.", wrap=True, xalign=0))
            grid = Gtk.Grid(column_spacing=10, row_spacing=10, column_homogeneous=True)
            scenarios = (("Laptop", "laptop"), ("Tablet", "tablet"), ("Home", "home"),
                ("Übersicht", "overview"), ("Geteilte Ansicht", "split"), ("Hochformat", "portrait"),
                ("Querformat", "landscape"), ("Tastatur", "keyboard"), ("Dunkel", "dark"),
                ("Hell", "light"), ("Fehler simulieren", "failure"),
                ("Große Schrift", "large-text"), ("Normale Schrift", "normal-text"),
                ("Weniger Bewegung", "reduced-motion"), ("Animationen", "normal-motion"))
            for index, (label, value) in enumerate(scenarios):
                button = Gtk.Button(label=label, height_request=44)
                button.connect("clicked", lambda _button, action=value: self.scenario(action))
                grid.attach(button, index % 2, index // 2, 1, 1)
            box.append(grid)
            if not controls_only:
                add = Gtk.Button(label="Weitere Text-Anwendung öffnen", height_request=44)
                add.connect("clicked", lambda _button: self.sample("Demo notes " + str(len(self.samples) + 1)))
                box.append(add)
            settings = Gtk.Button(label="Native Einstellungen öffnen", height_request=44)
            settings.connect("clicked", self.settings)
            box.append(settings)
            self.message = Gtk.Label(label="Bereit. Wähle ein Szenario.", wrap=True, xalign=0)
            box.append(self.message)
            window.set_child(box)
            window.present()
            if not controls_only:
                self.sample("Demo notes A")
                self.sample("Demo notes B")

    return Controls().run([])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--service-only", action="store_true")
    mode.add_argument("--controls-only", action="store_true")
    mode.add_argument("--samples-only", action="store_true")
    args = parser.parse_args()
    if (os.environ.get("CONVERTIBLED_DEMO_PRIVATE_BUS") != "1"
            or not os.environ.get("DBUS_SESSION_BUS_ADDRESS")):
        parser.error("Start through demo/native/run.sh with its isolated private D-Bus")
    connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    service = None if args.controls_only or args.samples_only else SessionMock(connection)
    if args.service_only:
        GLib.MainLoop().run()
        return 0
    return launch_controls(connection, args.samples_only, args.controls_only)


if __name__ == "__main__":
    sys.exit(main())
