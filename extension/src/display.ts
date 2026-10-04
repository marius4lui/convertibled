import Gio from 'gi://Gio';
import {Cleanup} from './ownership.js';
import {integratedMonitor, type Monitor} from './monitors.js';
export class DisplayObserver {
    private cancel = new Gio.Cancellable();
    private cleanup = new Cleanup();
    private proxy: any;
    private serial = 0;
    constructor(private monitors: () => Monitor[], private changed: (monitor: Monitor | null) => void) {
        Gio.DBusProxy.new_for_bus(Gio.BusType.SESSION, Gio.DBusProxyFlags.NONE, null,
            'org.gnome.Mutter.DisplayConfig', '/org/gnome/Mutter/DisplayConfig',
            'org.gnome.Mutter.DisplayConfig', this.cancel, (_source: any, result: any) => {
                if (this.cancel.is_cancelled()) return;
                try {
                    this.proxy = Gio.DBusProxy.new_for_bus_finish(result);
                    this.cleanup.signal(this.proxy, 'g-signal', (_p: any, _s: any, name: string) => {
                        if (name === 'MonitorsChanged') this.refresh();
                    });
                    this.refresh();
                } catch (error) { this.changed(null); console.error(String(error)); }
            });
    }
    refresh(): void {
        if (!this.proxy) return;
        const serial = ++this.serial;
        this.proxy.call('GetCurrentState', null, Gio.DBusCallFlags.NONE, 3000, this.cancel,
            (source: any, result: any) => {
                if (this.cancel.is_cancelled() || serial !== this.serial) return;
                try { this.changed(integratedMonitor(source.call_finish(result).deep_unpack(), this.monitors())); }
                catch (error) { this.changed(null); console.error(String(error)); }
            });
    }
    destroy(): void { this.cancel.cancel(); this.cleanup.clear(); }
}
