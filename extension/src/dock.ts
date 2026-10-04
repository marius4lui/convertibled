import St from 'gi://St';
import Shell from 'gi://Shell';
import Clutter from 'gi://Clutter';
import * as Favorites from 'resource:///org/gnome/shell/ui/appFavorites.js';
import {dockApps} from './apps.js';
import {Cleanup} from './ownership.js';
import {button, clear} from './ui.js';
export class Dock {
    readonly actor = new St.BoxLayout({style_class:'popup-menu-content convertibled-surface convertibled-dock',reactive:true});
    private apps = new St.BoxLayout({style_class:'convertibled-grid'});
    private cleanup = new Cleanup();
    private strip: any;
    private splitAction: any;
    private touchSetup: any;
    private approveTouch: ((event: any) => boolean) | null = null;
    constructor(navigate: (surface: 'home' | 'overview') => void, private activate: (app: any) => void) {
        this.actor.add_child(button('Home', () => navigate('home'), 'go-home-symbolic'));
        this.actor.add_child(button('Overview', () => navigate('overview'), 'view-grid-symbolic'));
        this.strip = new St.ScrollView({x_expand:true,overlay_scrollbars:true});
        this.strip.set_child(this.apps); this.actor.add_child(this.strip);
        this.cleanup.signal(Favorites.getAppFavorites(), 'changed', () => this.refresh());
        this.cleanup.signal(Shell.AppSystem.get_default(), 'app-state-changed', () => this.refresh());
        this.refresh();
    }
    showApps(visible: boolean): void { this.strip.visible = visible; }
    setSplitAction(action: (() => void) | null): void {
        this.splitAction?.destroy(); this.splitAction = null;
        if (action) { this.splitAction = button('End split',action,'view-restore-symbolic'); this.actor.add_child(this.splitAction); }
    }
    setTouchSetup(action: ((event: any) => boolean) | null): void {
        this.approveTouch = action;
        if (!action) { this.touchSetup?.destroy(); this.touchSetup = null; return; }
        if (this.touchSetup) return;
        this.touchSetup = button('Touch to enable gestures',()=>{},'input-touchpad-symbolic');
        this.touchSetup.connect('touch-event', (_actor: any,event: any) => {
            if (event.type() === Clutter.EventType.TOUCH_BEGIN && this.approveTouch?.(event)) return Clutter.EVENT_STOP;
            return Clutter.EVENT_PROPAGATE;
        });
        this.actor.add_child(this.touchSetup);
    }
    refresh(): void {
        clear(this.apps);
        const system = Shell.AppSystem.get_default();
        const ids = dockApps(Favorites.getAppFavorites().getFavorites().map((app: any) => app.get_id()),
            system.get_running().map((app: any) => app.get_id()));
        for (const id of ids) {
            const app = system.lookup_app(id); if (!app) continue;
            const item = new St.Button({style_class:'button convertibled-button',can_focus:true,
                accessible_name:app.get_name(),reactive:true});
            item.set_child(app.create_icon_texture(32));
            if (app.get_state() === Shell.AppState.RUNNING) item.add_style_pseudo_class('active');
            item.connect('clicked', () => this.activate(app)); this.apps.add_child(item);
        }
    }
    destroy(): void { this.cleanup.clear(); this.actor.destroy(); }
}
