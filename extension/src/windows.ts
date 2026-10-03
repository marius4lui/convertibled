import Meta from 'gi://Meta';
import {OwnedState} from './ownership.js';
import type {Rect} from './split.js';
type WindowState = {rect: Rect; maximized: number; monitor: number};
const equal = (a: WindowState, b: WindowState) => a.monitor === b.monitor &&
    a.maximized === b.maximized && ['x','y','width','height'].every(k =>
        a.rect[k as keyof Rect] === b.rect[k as keyof Rect]);
export class WindowController {
    private owned = new OwnedState<any, WindowState>(equal);
    snapshot(window: any): WindowState {
        const r = window.get_frame_rect();
        return {rect: {x:r.x,y:r.y,width:r.width,height:r.height},
            maximized: window.get_maximize_flags(), monitor: window.get_monitor()};
    }
    eligible(window: any, monitor: number): boolean {
        return window.get_monitor() === monitor && window.get_window_type() === Meta.WindowType.NORMAL &&
            !window.get_transient_for() && !window.is_fullscreen() && !window.is_above() &&
            !window.is_override_redirect() && !window.is_skip_taskbar();
    }
    maximize(window: any, monitor: number): void {
        if (!this.eligible(window, monitor) || !window.can_maximize()) return;
        const before = this.snapshot(window);
        window.maximize(Meta.MaximizeFlags.BOTH);
        this.owned.remember(window, before, this.snapshot(window));
    }
    place(window: any, rect: Rect): void {
        const before = this.snapshot(window);
        window.unmaximize(Meta.MaximizeFlags.BOTH);
        window.move_resize_frame(false, rect.x, rect.y, rect.width, rect.height);
        this.owned.remember(window, before, this.snapshot(window));
    }
    minimum(window: any): {width: number; height: number} {
        const size = window.get_min_size();
        return {width: size[0], height: size[1]};
    }
    restore(): void {
        for (const window of this.owned.keys()) {
            try {
                const original = this.owned.restore(window, this.snapshot(window));
                if (!original) continue;
                window.unmaximize(Meta.MaximizeFlags.BOTH);
                const r = original.rect;
                window.move_resize_frame(false, r.x, r.y, r.width, r.height);
                if (original.maximized) window.maximize(original.maximized);
            } catch (error) { console.error(`convertibled restore: ${String(error)}`); }
        }
    }
    forget(window: any): void { this.owned.forget(window); }
}
