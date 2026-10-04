import St from 'gi://St';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {Cleanup} from './ownership.js';
import {button, clear} from './ui.js';
import {_} from './localized.js';
export const widgetIds = ['clock','battery','actions'];
export function validWidgets(ids: string[]): string[] { return [...new Set(ids.filter(id => widgetIds.includes(id)))]; }
export class Widgets {
    readonly actor = new St.BoxLayout({vertical:true,style_class:'convertibled-grid'});
    private cleanup = new Cleanup();
    private battery: any;
    private cancel = new Gio.Cancellable();
    private labels = new Map<string,any>();
    private session: {profile: string | null; workspace: boolean; locked: boolean} = {profile:null,workspace:false,locked:false};
    private lockButton: any;
    constructor(private settings: any, private actions: {auto: () => void; lock: () => void; settings: () => void}) {
        this.cleanup.signal(settings,'changed::widgets', () => this.refresh());
        const timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT,30, () => { this.update(); return GLib.SOURCE_CONTINUE; });
        this.cleanup.add(() => GLib.Source.remove(timer));
        Gio.DBusProxy.new_for_bus(Gio.BusType.SYSTEM,Gio.DBusProxyFlags.NONE,null,
            'org.freedesktop.UPower','/org/freedesktop/UPower/devices/DisplayDevice',
            'org.freedesktop.UPower.Device',this.cancel,(_s: any,result: any) => {
                if (this.cancel.is_cancelled()) return;
                try {
                    this.battery = Gio.DBusProxy.new_for_bus_finish(result);
                    this.cleanup.signal(this.battery,'g-properties-changed', () => this.update());
                    this.update();
                } catch (error) { console.error(String(error)); }
            });
        this.refresh();
    }
    refresh(): void {
        clear(this.actor); this.labels.clear();
        for (const id of validWidgets(this.settings.get_strv('widgets'))) {
            const card = new St.BoxLayout({vertical:true,style_class:'convertibled-widget'});
            if (id === 'actions') {
                card.add_child(button('Automatic mode',this.actions.auto,'view-refresh-symbolic'));
                this.lockButton = button('Rotation lock',this.actions.lock,'rotation-locked-symbolic');
                this.lockButton.toggle_mode = true; card.add_child(this.lockButton);
                card.add_child(button('Settings',this.actions.settings,'emblem-system-symbolic'));
            } else { const label = new St.Label({text:''}); this.labels.set(id,label); card.add_child(label); }
            this.actor.add_child(card);
        }
        this.update();
    }
    setSession(profile: string | null,workspace: boolean,locked: boolean): void {
        this.session = {profile,workspace,locked}; this.update();
    }
    update(): void {
        const clock = this.labels.get('clock');
        if (clock) clock.text = GLib.DateTime.new_now_local().format('%A, %x\n%H:%M');
        if (this.lockButton) this.lockButton.checked = this.session.locked;
        const battery = this.labels.get('battery');
        if (battery) {
            const present = this.battery?.get_cached_property('IsPresent')?.deep_unpack();
            const percentage = this.battery?.get_cached_property('Percentage')?.deep_unpack();
            const charge = present && Number.isFinite(percentage)
                ? `${_('Battery')} ${Math.round(Math.max(0,Math.min(100,percentage)))}%` : _('Battery status unavailable');
            const profileLabels: Record<string,string> = {laptop:'Laptop mode',tablet:'Tablet mode',stand:'Stand mode',tent:'Tent mode'};
            const mode = this.session.profile ? _(profileLabels[this.session.profile] ?? 'Tablet mode') : _('Session service unavailable');
            battery.text = `${charge}\n${mode}`;
        }
    }
    destroy(): void { this.cancel.cancel(); this.cleanup.clear(); this.actor.destroy(); }
}
