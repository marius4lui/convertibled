import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Pango from 'gi://Pango';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {Cleanup} from './ownership.js';
import {clear} from './ui.js';
import {_} from './localized.js';
export const widgetIds = ['clock','battery','actions'];
export function validWidgets(ids: string[]): string[] { return [...new Set(ids.filter(id => widgetIds.includes(id)))]; }
export class Widgets {
    readonly actor = new St.BoxLayout({vertical:true,style_class:'convertibled-widgets',y_align:Clutter.ActorAlign.START,x_expand:true});
    private cleanup = new Cleanup();
    private battery: any;
    private cancel = new Gio.Cancellable();
    private labels = new Map<string,any>();
    private session: {profile: string | null; workspace: boolean; locked: boolean} = {profile:null,workspace:false,locked:false};
    private lockButton: any;
    private width = 720;
    private textScale = 1;
    private actionWidth = 72;
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
    resize(width: number,textScale = 1): void {
        const scale = Math.max(1,textScale);
        if (this.width === width && this.textScale === scale) return;
        this.width = Math.max(160,width); this.textScale = scale; this.refresh();
    }
    private label(card: any,key: string,style: string): void {
        const label = new St.Label({text:'',style_class:style,width:Math.max(80,card.width - 40)});
        label.clutter_text.line_wrap = true; label.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
        this.labels.set(key,label); card.add_child(label);
    }
    private action(label: string,icon: string,action: () => void): any {
        const control = new St.Button({style_class:'convertibled-widget-action',can_focus:true,reactive:true,
            width:this.actionWidth,accessible_name:_(label)});
        const content = new St.BoxLayout({vertical:true,style_class:'convertibled-widget-action-content'});
        content.add_child(new St.Icon({icon_name:icon,icon_size:24,x_align:Clutter.ActorAlign.CENTER}));
        const caption = new St.Label({text:_(label),style_class:'convertibled-widget-action-label',
            width:Math.max(32,this.actionWidth - 16),x_align:Clutter.ActorAlign.CENTER});
        caption.clutter_text.line_wrap = true; caption.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
        content.add_child(caption);
        control.set_child(content); control.connect('clicked',action); return control;
    }
    refresh(): void {
        clear(this.actor); this.labels.clear(); this.lockButton = null;
        const ids = validWidgets(this.settings.get_strv('widgets'));
        const columns = this.width >= 880 * this.textScale ? 3 : this.width >= 380 * this.textScale ? 2 : 1;
        const groups: string[][] = [];
        for (const id of ids) {
            const last = groups.at(-1);
            if (!last || last.length >= columns || (columns < 3 && (id === 'actions' || last.includes('actions')))) groups.push([id]);
            else last.push(id);
        }
        for (const group of groups) {
            const row = new St.BoxLayout({style_class:'convertibled-widget-row',x_expand:true}); this.actor.add_child(row);
            const cardWidth = Math.floor((this.width - (group.length - 1) * 16) / group.length);
            this.actionWidth = Math.max(44,Math.min(Math.ceil(112 * this.textScale),Math.floor((cardWidth - 40 - 16) / 3)));
            for (const id of group) {
            const card = new St.BoxLayout({vertical:true,style_class:`convertibled-widget convertibled-widget-${id}`,
                width:cardWidth,y_align:Clutter.ActorAlign.FILL});
            if (id === 'clock') {
                this.label(card,'clock-time','convertibled-widget-value convertibled-clock-time');
                this.label(card,'clock-date','convertibled-widget-detail');
            } else if (id === 'battery') {
                const heading = new St.BoxLayout({style_class:'convertibled-widget-heading'});
                heading.add_child(new St.Icon({icon_name:'battery-good-symbolic',icon_size:20}));
                heading.add_child(new St.Label({text:_('Battery'),style_class:'convertibled-widget-title'})); card.add_child(heading);
                this.label(card,'battery-charge','convertibled-widget-value');
                this.label(card,'battery-status','convertibled-widget-detail');
                this.label(card,'battery-mode','convertibled-widget-detail');
            } else {
                const inline = cardWidth >= 600 * this.textScale;
                card.vertical = !inline;
                card.add_child(new St.Label({text:_('Quick actions'),style_class:'convertibled-widget-title',
                    x_expand:inline,y_align:Clutter.ActorAlign.CENTER}));
                const controls = new St.BoxLayout({style_class:'convertibled-widget-actions'});
                controls.add_child(this.action('Automatic mode','view-refresh-symbolic',this.actions.auto));
                this.lockButton = this.action('Rotation lock','rotation-locked-symbolic',this.actions.lock);
                this.lockButton.toggle_mode = true; controls.add_child(this.lockButton);
                controls.add_child(this.action('Settings','emblem-system-symbolic',this.actions.settings)); card.add_child(controls);
            }
            row.add_child(card);
            }
        }
        this.update();
    }
    setSession(profile: string | null,workspace: boolean,locked: boolean): void {
        this.session = {profile,workspace,locked}; this.update();
    }
    update(): void {
        const now = GLib.DateTime.new_now_local();
        const clock = this.labels.get('clock-time'); if (clock) clock.text = now.format('%H:%M');
        const date = this.labels.get('clock-date'); if (date) date.text = now.format('%A, %e %B');
        if (this.lockButton) this.lockButton.checked = this.session.locked;
        const battery = this.labels.get('battery-charge');
        if (battery) {
            const present = this.battery?.get_cached_property('IsPresent')?.deep_unpack();
            const percentage = this.battery?.get_cached_property('Percentage')?.deep_unpack();
            const available = present && Number.isFinite(percentage);
            battery.text = available ? `${Math.round(Math.max(0,Math.min(100,percentage)))}%` : '—';
            const status = this.labels.get('battery-status');
            status.text = available ? '' : _('Battery status unavailable'); status.visible = !available;
            const profileLabels: Record<string,string> = {laptop:'Laptop mode',tablet:'Tablet mode',stand:'Stand mode',tent:'Tent mode'};
            this.labels.get('battery-mode').text = this.session.profile
                ? _(profileLabels[this.session.profile] ?? 'Tablet mode') : _('Session service unavailable');
        }
    }
    destroy(): void { this.cancel.cancel(); this.cleanup.clear(); this.actor.destroy(); }
}
