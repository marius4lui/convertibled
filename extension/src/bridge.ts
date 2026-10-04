import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {Cleanup} from './ownership.js';
import {parseStatus, type Status} from './status.js';
const name = 'org.convertibled.Session1';
const path = '/org/convertibled/Session1';
export function reportHealthOnce(version: string, healthy: boolean): void {
    Gio.DBus.session.call(name,path,name,'ReportShellHealth',new GLib.Variant('(sb)',[version,healthy]),
        null,Gio.DBusCallFlags.NO_AUTO_START,3000,null,(source: any,result: any) => {
            try { source.call_finish(result); } catch (error) { console.error(String(error)); }
        });
}
export class SessionBridge {
    private proxy: any;
    private cancel = new Gio.Cancellable();
    private cleanup = new Cleanup();
    private health: {version: string; healthy: boolean} | null = null;
    constructor(private changed: (status: Status | null, error?: string) => void) {
        Gio.DBusProxy.new_for_bus(Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_AUTO_START,
            null, name, path, name, this.cancel, (_source: any, result: any) => {
                if (this.cancel.is_cancelled()) return;
                try {
                    this.proxy = Gio.DBusProxy.new_for_bus_finish(result);
                    this.cleanup.signal(this.proxy, 'g-signal', (_p: any, _sender: string, signal: string, args: any) => {
                        if (signal === 'Changed') this.receive(args.deep_unpack()[0]);
                    });
                    this.cleanup.signal(this.proxy, 'notify::g-name-owner', () => this.refresh());
                    this.refresh();
                } catch (error) { changed(null, String(error)); }
            });
    }
    private receive(json: string): void {
        try { this.changed(parseStatus(json)); }
        catch (error) { this.changed(null, String(error)); }
    }
    private refresh(): void {
        if (!this.proxy?.get_name_owner()) { this.changed(null, 'Session service unavailable'); return; }
        if (this.health) this.call('ReportShellHealth',new GLib.Variant('(sb)',[this.health.version,this.health.healthy]));
        this.call('GetStatus', null, response => this.receive(response[0]));
    }
    call(method: string, parameters: any, done?: (response: any[]) => void): void {
        if (!this.proxy?.get_name_owner()) return;
        this.proxy.call(method, parameters, Gio.DBusCallFlags.NONE, 3000, this.cancel,
            (source: any, result: any) => {
                if (this.cancel.is_cancelled()) return;
                try { const response = source.call_finish(result).deep_unpack(); done?.(response); }
                catch (error) { console.error(`convertibled ${method}: ${String(error)}`); }
            });
    }
    profile(profile: string): void { this.call('SetProfile', new GLib.Variant('(s)', [profile])); }
    rotationLock(locked: boolean): void { this.call('SetRotationLock', new GLib.Variant('(b)', [locked])); }
    reportHealth(version: string, healthy: boolean): void {
        this.health = {version,healthy};
        this.call('ReportShellHealth',new GLib.Variant('(sb)',[version,healthy]));
    }
    report(value: object): void { this.call('ReportApplied', new GLib.Variant('(s)', [JSON.stringify(value)])); }
    destroy(): void {
        if (this.proxy?.get_name_owner()) {
            const report = {tablet_workspace:false,rotation_lock:false,status:'unavailable',
                error:'GNOME extension disabled',capabilities:{tablet_workspace:false}};
            // This final bounded call must outlive cancellation of normal extension work.
            this.proxy.call('ReportApplied',new GLib.Variant('(s)',[JSON.stringify(report)]),
                Gio.DBusCallFlags.NONE,1000,null,(source: any,result: any) => {
                    try { source.call_finish(result); } catch (error) { console.error(String(error)); }
                });
        }
        this.cancel.cancel(); this.cleanup.clear(); this.proxy = null;
    }
}
