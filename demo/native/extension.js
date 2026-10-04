// Demo-only entrypoint. product.js is the byte-identical built extension.js.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import TabletExtension from './product.js';

const xml = `<node><interface name="org.convertibled.Demo">
  <method name="Scenario"><arg type="s" direction="in"/><arg type="s" direction="out"/></method>
  <method name="Inspect"><arg type="s" direction="out"/></method>
  <method name="Capture"><arg type="s" direction="out"/></method>
</interface></node>`;

export default class DemoExtension extends TabletExtension {
    enable() {
        if (GLib.getenv('CONVERTIBLED_DEMO_PRIVATE_BUS') !== '1' ||
            !GLib.getenv('XDG_DATA_HOME')?.includes('/convertibled-native-demo/'))
            throw new Error('Demo requires its isolated launcher');
        this.failed = false;
        super.enable();
        this.demoObject = Gio.DBusExportedObject.wrapJSObject(xml, this);
        this.demoObject.export(Gio.DBus.session, '/org/convertibled/Demo');
        this.demoOwner = Gio.bus_own_name_on_connection(Gio.DBus.session,
            'org.convertibled.Demo', Gio.BusNameOwnerFlags.NONE, null, null);
    }
    reconcile() {
        // WSLg has no physical integrated output. Substitute only its identity;
        // all actors, layout, window management, CSS and events remain production.
        this.monitor = Main.layoutManager.monitors[0] ?? null;
        if (this.failed) this.status = null;
        super.reconcile();
    }
    Scenario(name) {
        this.lastScenario = name;
        const allowed = ['laptop','tablet','home','overview','split','portrait','landscape',
            'keyboard','dark','light','failure','large-text','normal-text','reduced-motion','normal-motion'];
        if (!allowed.includes(name)) throw new Error('Unknown demo scenario');
        this.failed = name === 'failure';
        const appearance = new Gio.Settings({schema_id:'org.gnome.desktop.interface'});
        if (name === 'large-text' || name === 'normal-text') {
            appearance.set_double('text-scaling-factor', name === 'large-text' ? 1.25 : 1);
            return this.Inspect();
        }
        if (name === 'reduced-motion' || name === 'normal-motion') {
            appearance.set_boolean('enable-animations', name === 'normal-motion');
            return this.Inspect();
        }
        if (name === 'dark' || name === 'light') {
            new Gio.Settings({schema_id:'org.gnome.desktop.interface'})
                .set_string('color-scheme', name === 'dark' ? 'prefer-dark' : 'prefer-light');
            return this.Inspect();
        }
        const profile = this.failed ? 'failure' : name === 'laptop' ? 'laptop' : 'tablet';
        this.demoCall('InjectScenario', new GLib.Variant('(s)', [profile]), () => {
            this.demoCall('GetStatus', null, response => {
                this.status = JSON.parse(response[0]); this.reconcile();
                Main.overview.hide();
                if (this.demoTimer) GLib.source_remove(this.demoTimer);
                this.demoTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 350, () => {
                    this.demoTimer = 0;
                    if (name === 'home' || name === 'overview') this.navigate(name);
                    if (name === 'tablet') this.navigate('dock');
                    if (name === 'split') {
                        const windows = this.internalWindows().filter(w =>
                            !w.get_title().includes('Demo-Steuerung'));
                        this.splitCandidates = windows.length;
                        if (windows.length >= 2) this.split(windows[0], windows[1]);
                    }
                    if (name === 'keyboard') {
                        const accessibility = new Gio.Settings({schema_id:'org.gnome.desktop.a11y.applications'});
                        accessibility.set_boolean('screen-keyboard-enabled',
                            !accessibility.get_boolean('screen-keyboard-enabled'));
                        this.navigate('home');
                        this.home.focusSearch();
                    }
                    return GLib.SOURCE_REMOVE;
                });
            });
        });
        // Monitor dimensions are controlled by the nested compositor window,
        // never faked in the product's geometry calculations.
        if (name === 'portrait' || name === 'landscape') {
            const process = Gio.Subprocess.new(['python3', GLib.getenv('CONVERTIBLED_DEMO_RESIZE'), name],
                Gio.SubprocessFlags.NONE);
            process.wait_check_async(null, (source, result) => {
                try { source.wait_check_finish(result); Main.overview.hide(); this.reconcile(); }
                catch (error) { Main.notify('convertibled Demo', String(error)); }
            });
        }
        return JSON.stringify({requested:name});
    }
    demoCall(method, args, done) {
        Gio.DBus.session.call('org.convertibled.DemoState', '/org/convertibled/Session1',
            'org.convertibled.Session1', method, args, null, Gio.DBusCallFlags.NO_AUTO_START,
            3000, null, (source, result) => {
                try { done(source.call_finish(result).deep_unpack()); }
                catch (error) { Main.notify('convertibled Demo', String(error)); }
            });
    }
    Inspect() {
        const appearance = new Gio.Settings({schema_id:'org.gnome.desktop.interface'});
        const keyboard = Main.layoutManager.keyboardBox;
        return JSON.stringify({active:this.active, monitor:this.monitor,
            home:this.home?.actor.visible, overview:this.overview?.actor.visible,
            dock:this.dock?.actor.visible, windows:this.internalWindows().length,
            failure:this.failed, nativeOverview:Main.overview.visible,
            appearance:appearance.get_string('color-scheme'),
            textScale:appearance.get_double('text-scaling-factor'),
            animations:appearance.get_boolean('enable-animations'),
            keyboard:{visible:keyboard.visible,height:keyboard.height},
            layout:{homeBottom:this.home.actor.y + this.home.actor.height,
                dockTop:this.dock.actor.y,dockBottom:this.dock.actor.y + this.dock.actor.height,
                compact:this.home.compact},
            scenario:this.lastScenario, splitCandidates:this.splitCandidates,
            frames:this.internalWindows().map(w => {
                const r = w.get_frame_rect();
                return {title:w.get_title(),x:r.x,y:r.y,width:r.width,height:r.height,
                    minimum:this.windows.minimum(w)};
            })});
    }
    async CaptureAsync(_params, invocation) {
        const path = `${GLib.getenv('CONVERTIBLED_DEMO_ROOT')}/capture.png`;
        let stream;
        try {
            stream = Gio.File.new_for_path(path).replace(null, false, Gio.FileCreateFlags.NONE, null);
            await new Shell.Screenshot().screenshot(false, stream);
            stream.close(null);
            invocation.return_value(new GLib.Variant('(s)', [path]));
        } catch (error) {
            stream?.close(null);
            invocation.return_dbus_error('org.convertibled.Demo.CaptureFailed', String(error));
        }
    }
    disable() {
        if (this.demoTimer) GLib.source_remove(this.demoTimer);
        this.demoTimer = 0;
        this.demoObject?.unexport(); this.demoObject = null;
        if (this.demoOwner) Gio.bus_unown_name(this.demoOwner);
        this.demoOwner = 0;
        super.disable();
    }
}
