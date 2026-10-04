import Meta from 'gi://Meta';
import Cogl from 'gi://Cogl';
import GDesktopEnums from 'gi://GDesktopEnums';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

/** GNOME 50 adapter: retain native rounding, dimming and workspace actors. */
export class OverviewBackdrop {
    private owned = new Map<any, {original: any; applied: any}>();
    private signals: Array<{manager: any; id: number}> = [];

    show(monitorIndex: number, light: boolean): void {
        this.hide();
        const display = (Main.overview as any)._overview?.controls?._workspacesDisplay;
        const outer = display?._workspacesViews?.[monitorIndex];
        const view = outer?._workspacesView ?? outer;
        const workspaces = view?._workspaces ?? (view?._workspace ? [view._workspace] : []);
        const colors = light ? ['#f5f7fc','#e7edf7'] : ['#222d40','#151c29'];
        let background: any;
        try {
            const [firstValid,first] = Cogl.Color.from_string(colors[0]);
            const [secondValid,second] = Cogl.Color.from_string(colors[1]);
            if (!firstValid || !secondValid) return;
            background = new Meta.Background({meta_display:global.display});
            background.set_gradient(GDesktopEnums.BackgroundShading.VERTICAL,first,second);
        } catch { return; }
        for (const workspace of workspaces) {
            if (workspace.monitorIndex !== monitorIndex) continue;
            const manager = workspace._background?._bgManager;
            if (!manager) continue;
            const apply = () => {
                try {
                    const content = manager.backgroundActor?.content;
                    if (!content || this.owned.has(content)) return;
                    const original = content.background;
                    content.set({background});
                    this.owned.set(content,{original,applied:background});
                } catch { /* Workspace teardown may race a queued background change. */ }
            };
            try {
                const id = manager.connect('changed',apply);
                this.signals.push({manager,id});
                apply();
            } catch { /* Missing private API leaves the native background untouched. */ }
        }
    }

    hide(): void {
        for (const {manager,id} of this.signals) {
            try { manager.disconnect(id); } catch { /* Already destroyed. */ }
        }
        this.signals = [];
        for (const [content,{original,applied}] of this.owned) {
            try {
                if (content.background === applied) content.set({background:original});
            } catch { /* Already disposed with its native workspace. */ }
        }
        this.owned.clear();
    }
}
