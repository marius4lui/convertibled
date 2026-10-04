import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import {EdgeGesture, type Navigation} from './gesture.js';
import type {Monitor} from './monitors.js';
export class TouchNavigation {
    private gesture = new EdgeGesture();
    private sequence: any = null;
    private claimed = new Set<any>();
    private device: any;
    private timer = 0;
    private timerPoint: {x: number; y: number} | null = null;
    private navigated: Navigation | null = null;
    constructor(private area: () => Monitor | null, private enabled: () => boolean,
        private navigate: (surface: Navigation) => void) {}
    handle(event: any): any {
        const type = event.type();
        if (![Clutter.EventType.TOUCH_BEGIN,Clutter.EventType.TOUCH_UPDATE,
            Clutter.EventType.TOUCH_END,Clutter.EventType.TOUCH_CANCEL].includes(type)) return Clutter.EVENT_PROPAGATE;
        const sequence = event.get_event_sequence();
        if (!this.claimed.has(sequence) && (!this.enabled() ||
            event.get_source_device()?.get_device_type() !== Clutter.InputDeviceType.TOUCHSCREEN_DEVICE)) return Clutter.EVENT_PROPAGATE;
        const [x,y] = event.get_coords(); const sample = {x,y,time:event.get_time()};
        if (type === Clutter.EventType.TOUCH_BEGIN) {
            if (this.claimed.size && event.get_source_device() === this.device) {
                this.cancel(); this.claimed.add(sequence); return Clutter.EVENT_STOP;
            }
            const area = this.area();
            if (area && this.gesture.begin(sample,area)) {
                this.sequence = sequence; this.device = event.get_source_device(); this.claimed.add(sequence);
                this.navigated = null; return Clutter.EVENT_STOP;
            }
        }
        if (this.claimed.has(sequence)) {
            if (!this.enabled()) this.cancel();
            if (sequence === this.sequence && type === Clutter.EventType.TOUCH_UPDATE) {
                const action = this.gesture.update(sample);
                if (action && action !== this.navigated && this.navigated !== 'overview') {
                    this.navigated = action; this.navigate(action);
                }
                if (!action) this.stopTimer();
                else if (!this.timerPoint || Math.hypot(x - this.timerPoint.x,y - this.timerPoint.y) >= 8) {
                    this.stopTimer(); this.timerPoint = {x,y};
                    this.timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT,500, () => {
                        this.timer = 0;
                        if (this.enabled() && this.gesture.hold()) { this.navigated = 'overview'; this.navigate('overview'); }
                        return GLib.SOURCE_REMOVE;
                    });
                }
            }
            if (type === Clutter.EventType.TOUCH_END || type === Clutter.EventType.TOUCH_CANCEL) {
                if (sequence === this.sequence && type === Clutter.EventType.TOUCH_END) {
                    const action = this.gesture.end(sample);
                    if (action && action !== this.navigated) this.navigate(action);
                }
                this.claimed.delete(sequence); this.cancel();
                if (!this.claimed.size) this.device = null;
            }
            return Clutter.EVENT_STOP;
        }
        return Clutter.EVENT_PROPAGATE;
    }
    private stopTimer(): void {
        if (this.timer) GLib.Source.remove(this.timer); this.timer = 0; this.timerPoint = null;
    }
    cancel(): void { this.stopTimer(); this.gesture.cancel(); this.sequence = null; this.navigated = null; }
}
