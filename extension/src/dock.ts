import St from 'gi://St';
import Shell from 'gi://Shell';
import Clutter from 'gi://Clutter';
import * as Favorites from 'resource:///org/gnome/shell/ui/appFavorites.js';
import {dockApps} from './apps.js';
import {Cleanup} from './ownership.js';
import {button, clear} from './ui.js';
import {_} from './localized.js';
export class Dock {
    readonly actor = new St.BoxLayout({style_class:'convertibled-dock',reactive:false});
    private shelf = new St.BoxLayout({style_class:'convertibled-shelf',reactive:true,
        x_align:Clutter.ActorAlign.CENTER,y_align:Clutter.ActorAlign.CENTER,x_expand:true});
    private navigation = new Map<string,any>();
    private apps = new St.BoxLayout({style_class:'convertibled-grid'});
    private cleanup = new Cleanup();
    private strip: any;
    private stripContent = new St.BoxLayout({style_class:'convertibled-grid'});
    private splitAction: any;
    private touchSetup: any;
    private approveTouch: ((event: any) => boolean) | null = null;
    constructor(navigate: (surface: 'home' | 'overview') => void, private activate: (app: any) => void) {
        this.actor.add_child(this.shelf);
        for (const [surface,label,icon] of [['home','Home','go-home-symbolic'],['overview','Overview','view-grid-symbolic']] as const) {
            const item = new St.Button({style_class:'convertibled-nav',can_focus:true,reactive:true,
                accessible_name:_(label),toggle_mode:true});
            const content = new St.BoxLayout({vertical:true,style_class:'convertibled-nav-content'});
            content.add_child(new St.Icon({icon_name:icon,icon_size:22,x_align:Clutter.ActorAlign.CENTER}));
            content.add_child(new St.Label({text:_(label),x_align:Clutter.ActorAlign.CENTER}));
            item.set_child(content); item.connect('clicked',() => navigate(surface as 'home' | 'overview'));
            this.navigation.set(surface,item); this.shelf.add_child(item);
        }
        this.strip = new St.ScrollView({x_expand:true,overlay_scrollbars:true});
        this.stripContent.add_child(this.apps); this.strip.set_child(this.stripContent); this.shelf.add_child(this.strip);
        this.cleanup.signal(Favorites.getAppFavorites(), 'changed', () => this.refresh());
        this.cleanup.signal(Shell.AppSystem.get_default(), 'app-state-changed', () => this.refresh());
        this.refresh();
    }
    resize(width: number): void { this.shelf.width = Math.max(240,Math.min(760,width - 32)); }
    select(surface: string | null): void {
        for (const [name,item] of this.navigation) item.checked = name === surface;
    }
    showApps(visible: boolean): void { this.strip.visible = visible; }
    setSplitAction(action: (() => void) | null): void {
        this.splitAction?.destroy(); this.splitAction = null;
        if (action) { this.splitAction = button('End split',action,'view-restore-symbolic'); this.stripContent.add_child(this.splitAction); }
    }
    setTouchSetup(action: ((event: any) => boolean) | null): void {
        this.approveTouch = action;
        if (!action) { this.touchSetup?.destroy(); this.touchSetup = null; return; }
        if (this.touchSetup) return;
        this.touchSetup = button('Enable gestures',()=>{},'input-touchpad-symbolic');
        this.touchSetup.accessible_name = _('Touch to enable gestures');
        this.touchSetup.style_class = 'convertibled-button convertibled-setup';
        this.touchSetup.connect('touch-event', (_actor: any,event: any) => {
            if (event.type() === Clutter.EventType.TOUCH_BEGIN && this.approveTouch?.(event)) return Clutter.EVENT_STOP;
            return Clutter.EVENT_PROPAGATE;
        });
        this.stripContent.add_child(this.touchSetup);
    }
    refresh(): void {
        clear(this.apps);
        const system = Shell.AppSystem.get_default();
        const ids = dockApps(Favorites.getAppFavorites().getFavorites().map((app: any) => app.get_id()),
            system.get_running().map((app: any) => app.get_id()));
        for (const id of ids) {
            const app = system.lookup_app(id); if (!app) continue;
            const item = new St.Button({style_class:'convertibled-dock-app',can_focus:true,
                accessible_name:app.get_name(),reactive:true});
            item.set_child(app.create_icon_texture(40));
            if (app.get_state() === Shell.AppState.RUNNING) item.add_style_pseudo_class('active');
            item.connect('clicked', () => this.activate(app)); this.apps.add_child(item);
        }
    }
    destroy(): void { this.cleanup.clear(); this.actor.destroy(); }
}
