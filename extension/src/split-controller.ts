import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Cleanup} from './ownership.js';
import {splitLayout, nextRatio, ratios, type Ratio, type Rect} from './split.js';
import {WindowController} from './windows.js';
import {button} from './ui.js';
export class SplitController {
    private first: any;
    private second: any;
    private area?: Rect;
    private cleanup = new Cleanup();
    private divider: any;
    constructor(private windows: WindowController, private settings: any) {}
    apply(first: any, second: any, area: Rect, monitor: number): boolean {
        if (first === second || !this.windows.eligible(first,monitor) ||
            !this.windows.eligible(second,monitor) || !first.allows_resize() || !second.allows_resize()) {
            Main.notify('convertibled','Choose two resizable main windows on the internal display'); return false;
        }
        const stored = this.settings.get_string('split-ratio') as Ratio;
        const ratio = ratios.includes(stored) ? stored : 'half';
        const layout = splitLayout(area,ratio,this.windows.minimum(first),this.windows.minimum(second));
        if ('error' in layout) { Main.notify('convertibled',layout.error); return false; }
        this.clear(); this.first = first; this.second = second; this.area = area;
        this.windows.place(first,layout.first); this.windows.place(second,layout.second);
        this.divider = button('Change split', () => {
            this.settings.set_string('split-ratio',nextRatio(ratio));
            this.apply(first,second,area,monitor);
        },'view-dual-symbolic');
        this.divider.set_position(layout.divider.x,layout.divider.y);
        this.divider.set_size(layout.divider.width,layout.divider.height);
        Main.layoutManager.addChrome(this.divider,{affectsStruts:false,trackFullscreen:false});
        this.cleanup.add(() => { Main.layoutManager.removeChrome(this.divider); this.divider.destroy(); });
        for (const window of [first,second]) {
            this.cleanup.signal(window,'unmanaged', () => this.clear());
            this.cleanup.signal(window,'notify::fullscreen', () => this.clear());
        }
        first.raise(); second.raise(); return true;
    }
    resize(area: Rect, monitor: number): void {
        if (!this.first || !this.second) return;
        if (this.area && ['x','y','width','height'].every(k => this.area![k as keyof Rect] === area[k as keyof Rect])) return;
        this.apply(this.first,this.second,area,monitor);
    }
    clear(): void { this.cleanup.clear(); this.first = null; this.second = null; this.area = undefined; }
}
