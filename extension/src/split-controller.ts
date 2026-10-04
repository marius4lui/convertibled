import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Cleanup} from './ownership.js';
import {splitLayout, nextRatio, ratios, type Ratio, type Rect} from './split.js';
import {WindowController} from './windows.js';
import {button} from './ui.js';
import {_} from './localized.js';
export class SplitController {
    private first: any;
    private second: any;
    private area?: Rect;
    private cleanup = new Cleanup();
    private divider: any;
    constructor(private windows: WindowController, private settings: any,private activeChanged: (active: boolean) => void) {}
    apply(first: any, second: any, area: Rect, monitor: number): boolean {
        if (first === second || !this.windows.eligible(first,monitor) ||
            !this.windows.eligible(second,monitor) || !first.allows_resize() || !second.allows_resize()) {
            Main.notify('convertibled',_('Choose two resizable main windows on the internal display')); return false;
        }
        const stored = this.settings.get_string('split-ratio') as Ratio;
        const ratio = ratios.includes(stored) ? stored : 'half';
        const layout = splitLayout(area,ratio,this.windows.minimum(first),this.windows.minimum(second));
        if ('error' in layout) { Main.notify('convertibled',_(layout.error)); return false; }
        this.clear();
        const placement = this.windows.placePair(first,layout.first,second,layout.second);
        if (placement !== 'applied') {
            Main.notify('convertibled',placement === 'restored'
                ? _('Split view failed. Previous window positions were restored.')
                : _('Split view failed. Some window positions could not be restored.'));
            return false;
        }
        this.first = first; this.second = second; this.area = area;
        this.divider = new St.Button({style_class:'button convertibled-button',can_focus:true,reactive:true,
            accessible_name:_('Change split')});
        this.divider.set_child(new St.Icon({icon_name:'view-dual-symbolic',icon_size:24}));
        this.divider.connect('clicked', () => {
            this.settings.set_string('split-ratio',nextRatio(ratio));
            if (!this.apply(first,second,area,monitor)) this.settings.set_string('split-ratio',ratio);
        });
        this.divider.set_position(layout.divider.x,layout.divider.y);
        this.divider.set_size(layout.divider.width,layout.divider.height);
        Main.layoutManager.addChrome(this.divider,{affectsStruts:false,trackFullscreen:false});
        this.cleanup.add(() => { Main.layoutManager.removeChrome(this.divider); this.divider.destroy(); });
        for (const window of [first,second]) {
            this.cleanup.signal(window,'unmanaged', () => this.clear());
            this.cleanup.signal(window,'notify::fullscreen', () => this.clear());
        }
        first.raise(); second.raise(); this.activeChanged(true); return true;
    }
    resize(area: Rect, monitor: number): void {
        if (!this.first || !this.second) return;
        if (this.area && ['x','y','width','height'].every(k => this.area![k as keyof Rect] === area[k as keyof Rect])) return;
        if (!this.apply(this.first,this.second,area,monitor)) this.end(monitor);
    }
    end(monitor: number): void {
        for (const window of [this.first,this.second]) {
            if (window && this.windows.owns(window)) this.windows.maximize(window,monitor);
        }
        this.clear();
    }
    clear(): void {
        this.cleanup.clear(); this.first = null; this.second = null; this.area = undefined; this.activeChanged(false);
    }
}
