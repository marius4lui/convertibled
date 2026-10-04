import Meta from 'gi://Meta';

type HiddenWindow = {monitor: number; workspace: any; signals: number[]};

// Standalone preferences windows can be DIALOG without being transient. Home
// hides them too, while the independent maximize policy keeps their geometry.
export function desktopEligible(window: any, monitor: number): boolean {
    const type = window.get_window_type();
    return window.get_monitor() === monitor &&
        (type === Meta.WindowType.NORMAL || type === Meta.WindowType.DIALOG) &&
        !window.get_transient_for() && !window.is_override_redirect() &&
        !window.is_skip_taskbar() && !window.is_above();
}

/** Own only minimizations made by explicit Home navigation, never by folding. */
export class DesktopController {
    private hidden = new Map<any, HiddenWindow>();

    // Callers supply the current workspace; recheck eligibility at the native boundary.
    show(windows: any[], monitor: number, workspace: any): void {
        for (const window of windows) {
            try {
                if (window.minimized || !desktopEligible(window, monitor) ||
                    window.get_workspace() !== workspace || !window.can_minimize()) continue;
                const entry: HiddenWindow = {monitor, workspace, signals: []};
                this.hidden.set(window, entry);
                entry.signals.push(window.connect('notify::minimized', () => {
                    // A later native activation relinquishes ownership permanently,
                    // even if the user minimizes the window again afterwards.
                    if (!window.minimized) this.forget(window);
                }));
                entry.signals.push(window.connect('unmanaged', () => this.forget(window)));
                entry.signals.push(window.connect('workspace-changed', () => this.forget(window)));
                entry.signals.push(window.connect('position-changed', () => {
                    if (window.get_monitor() !== entry.monitor) this.forget(window);
                }));
                window.minimize();
                // Mutter updates minimized synchronously; rejected requests own nothing.
                if (!window.minimized) this.forget(window);
            } catch (error) {
                this.forget(window);
                console.error(`convertibled Home minimization: ${String(error)}`);
            }
        }
    }

    forget(window: any): void {
        const entry = this.hidden.get(window);
        if (!entry) return;
        this.hidden.delete(window);
        for (const signal of entry.signals) {
            try { window.disconnect(signal); } catch { /* Window may be unmanaged. */ }
        }
    }

    restore(): void {
        for (const [window, entry] of this.hidden) {
            this.forget(window);
            try {
                if (window.minimized && window.get_monitor() === entry.monitor &&
                    window.get_workspace() === entry.workspace) {
                    // Unlike activate(), Mutter unminimize does not raise/focus a window.
                    window.unminimize();
                }
            } catch (error) { console.error(`convertibled Home restoration: ${String(error)}`); }
        }
    }
}
