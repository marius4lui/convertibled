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
        if (before.maximized === Meta.MaximizeFlags.BOTH) return;
        window.maximize();
        const r = window.get_work_area_current_monitor();
        this.owned.remember(window, before, {rect:{x:r.x,y:r.y,width:r.width,height:r.height},
            maximized:Meta.MaximizeFlags.BOTH,monitor});
    }
    place(window: any, rect: Rect): void {
        const before = this.snapshot(window);
        window.unmaximize();
        window.move_resize_frame(false, rect.x, rect.y, rect.width, rect.height);
        this.owned.remember(window, before, {rect:{...rect},maximized:0,monitor:before.monitor});
    }
    placePair(first: any, firstRect: Rect, second: any, secondRect: Rect): 'applied' | 'restored' | 'failed' {
        const checkpoints = [first,second].map(window => ({window,before:this.snapshot(window),
            restoreOwnership:this.owned.checkpoint(window)}));
        let attempted = 0;
        try {
            for (const [index,rect] of [firstRect,secondRect].entries()) {
                // Include a window whose unmaximize succeeds but placement throws.
                attempted = index + 1;
                this.place(checkpoints[index]!.window,rect);
            }
            return 'applied';
        } catch (error) {
            console.error(`convertibled split placement: ${String(error)}`);
            let restored = true;
            // No await: roll back this synchronous operation before another UI action.
            for (const checkpoint of checkpoints.slice(0,attempted).reverse()) {
                const {window,before,restoreOwnership} = checkpoint;
                try {
                    if (window.get_monitor() !== before.monitor) throw new Error('Window changed monitor');
                    window.unmaximize();
                    const r = before.rect;
                    window.move_resize_frame(false,r.x,r.y,r.width,r.height);
                    if (before.maximized) window.set_maximize_flags(before.maximized);
                    restoreOwnership();
                } catch (rollbackError) {
                    // Do not retain a successful ownership claim for a failed rollback.
                    this.owned.forget(window); restored = false;
                    console.error(`convertibled split rollback: ${String(rollbackError)}`);
                }
            }
            return restored ? 'restored' : 'failed';
        }
    }
    minimum(window: any): {width: number; height: number} {
        const [known,width,height] = window.get_min_size();
        if (!known) return {width:0,height:0};
        const frame = window.get_frame_rect(); const client = window.get_client_content_rect();
        return {width:width + Math.max(0,frame.width - client.width),
            height:height + Math.max(0,frame.height - client.height)};
    }
    restore(): void {
        for (const window of this.owned.keys()) {
            try {
                const original = this.owned.restore(window, this.snapshot(window));
                if (!original) continue;
                window.unmaximize();
                const r = original.rect;
                window.move_resize_frame(false, r.x, r.y, r.width, r.height);
                if (original.maximized) window.set_maximize_flags(original.maximized);
            } catch (error) { console.error(`convertibled restore: ${String(error)}`); }
        }
    }
    forget(window: any): void { this.owned.forget(window); }
    owns(window: any): boolean { return this.owned.matches(window,this.snapshot(window)); }
    reconcileWorkArea(monitor: number): void {
        for (const window of this.owned.keys()) {
            const applied = this.owned.applied(window);
            if (!applied || applied.maximized !== Meta.MaximizeFlags.BOTH ||
                window.get_monitor() !== monitor || window.get_maximize_flags() !== Meta.MaximizeFlags.BOTH) continue;
            const r = window.get_work_area_current_monitor();
            this.owned.remember(window,this.snapshot(window),{...applied,
                rect:{x:r.x,y:r.y,width:r.width,height:r.height}});
        }
    }
}
