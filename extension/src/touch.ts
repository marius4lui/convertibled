import Clutter from 'gi://Clutter';
import {EdgeGesture, type Navigation} from './gesture.js';
import type {Monitor} from './monitors.js';
export class TouchNavigation {
    private gesture = new EdgeGesture();
    private sequence: any = null;
    constructor(private area: () => Monitor | null, private enabled: () => boolean,
        private navigate: (surface: Navigation) => void) {}
    handle(event: any): any {
        if (!this.enabled() || event.get_source_device()?.get_device_type() !== Clutter.InputDeviceType.TOUCHSCREEN_DEVICE)
            return Clutter.EVENT_PROPAGATE;
        const type = event.type();
        if (![Clutter.EventType.TOUCH_BEGIN,Clutter.EventType.TOUCH_UPDATE,
            Clutter.EventType.TOUCH_END,Clutter.EventType.TOUCH_CANCEL].includes(type)) return Clutter.EVENT_PROPAGATE;
        const sequence = event.get_event_sequence();
        const [x,y] = event.get_coords(); const sample = {x,y,time:event.get_time()};
        if (type === Clutter.EventType.TOUCH_BEGIN) {
            if (this.sequence) { this.cancel(); return Clutter.EVENT_PROPAGATE; }
            const area = this.area();
            if (area && this.gesture.begin(sample,area)) this.sequence = sequence;
        } else if (sequence === this.sequence) {
            if (type === Clutter.EventType.TOUCH_CANCEL) this.cancel();
            else if (type === Clutter.EventType.TOUCH_END) {
                this.sequence = null; const action = this.gesture.end(sample);
                if (action) { this.navigate(action); return Clutter.EVENT_STOP; }
            }
        }
        return Clutter.EVENT_PROPAGATE;
    }
    cancel(): void { this.gesture.cancel(); this.sequence = null; }
}
