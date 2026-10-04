import St from 'gi://St';
import Shell from 'gi://Shell';
import Clutter from 'gi://Clutter';
import Pango from 'gi://Pango';
import * as Favorites from 'resource:///org/gnome/shell/ui/appFavorites.js';
import {dockApps} from './apps.js';
import {Cleanup} from './ownership.js';
import {clear} from './ui.js';
import {_} from './localized.js';
export class Dock {
    readonly actor = new St.BoxLayout({style_class:'convertibled-dock',reactive:false});
    private shelf = new St.BoxLayout({style_class:'convertibled-shelf',reactive:true,
        x_align:Clutter.ActorAlign.CENTER,y_align:Clutter.ActorAlign.CENTER,x_expand:true});
    private navigation = new Map<string,any>();
    private apps = new St.BoxLayout({style_class:'convertibled-dock-apps',y_align:Clutter.ActorAlign.CENTER});
    private cleanup = new Cleanup();
    private strip: any;
    private stripContent = new St.BoxLayout({style_class:'convertibled-dock-strip'});
    private actions = new St.BoxLayout({style_class:'convertibled-dock-actions',y_align:Clutter.ActorAlign.CENTER});
    private divider = new St.Widget({style_class:'convertibled-dock-divider',y_align:Clutter.ActorAlign.CENTER});
    private width = 800;
    private textScale = 1;
    private splitAction: any;
    private touchSetup: any;
    private approveTouch: ((event: any) => boolean) | null = null;
    suspended = false;
    constructor(navigate: (surface: 'home' | 'overview') => void, private activate: (app: any) => void) {
        this.actor.add_child(this.shelf);
        const navigation = new St.BoxLayout({style_class:'convertibled-dock-navigation',y_align:Clutter.ActorAlign.CENTER});
        this.shelf.add_child(navigation);
        for (const [surface,label,icon] of [['home','Home','go-home-symbolic'],['overview','Overview','view-grid-symbolic']] as const) {
            const item = new St.Button({style_class:'convertibled-nav',can_focus:true,reactive:true,
                accessible_name:_(label),toggle_mode:true});
            const content = new St.BoxLayout({vertical:true,style_class:'convertibled-nav-content'});
            content.add_child(new St.Icon({icon_name:icon,icon_size:22,x_align:Clutter.ActorAlign.CENTER}));
            content.add_child(new St.Label({text:_(label),x_align:Clutter.ActorAlign.CENTER}));
            item.set_child(content); item.connect('clicked',() => navigate(surface as 'home' | 'overview'));
            this.navigation.set(surface,item); navigation.add_child(item);
        }
        this.strip = new St.ScrollView({x_expand:true,overlay_scrollbars:true});
        this.shelf.add_child(this.divider);
        this.stripContent.add_child(this.apps); this.stripContent.add_child(this.actions);
        this.strip.set_child(this.stripContent); this.shelf.add_child(this.strip);
        this.cleanup.signal(Favorites.getAppFavorites(), 'changed', () => this.refresh());
        this.cleanup.signal(Shell.AppSystem.get_default(), 'app-state-changed', () => this.refresh());
        this.refresh();
    }
    resize(width: number,textScale = 1): void {
        this.width = width; this.textScale = Math.max(1,textScale); this.layout();
    }
    private layout(): void {
        const appCount = this.apps.get_n_children();
        const actionCount = this.actions.get_n_children();
        this.apps.visible = appCount > 0;
        this.actions.visible = actionCount > 0;
        this.divider.visible = this.strip.visible && appCount + actionCount > 0;
        // Fit the actual content: sparse favorites must not leave an empty tail.
        const actionWidth = Math.ceil(112 * this.textScale);
        for (const action of this.actions.get_children()) action.width = actionWidth;
        const contentWidth = this.strip.visible ? appCount * 60 + actionCount * (actionWidth + 6) + 20 : 0;
        this.shelf.width = Math.min(Math.max(0,this.width - 32),Math.ceil(184 * this.textScale) + contentWidth);
    }
    select(surface: string | null): void {
        for (const [name,item] of this.navigation) item.checked = name === surface;
    }
    setSuspended(suspended: boolean): void {
        this.suspended = suspended;
        // Keep the owned strut stable while GNOME animates existing windows.
        // Hidden shelf children cannot intercept overview input.
        this.shelf.visible = !suspended; this.actor.opacity = suspended ? 0 : 255;
    }
    showApps(visible: boolean): void { this.strip.visible = visible; this.layout(); }
    setSplitAction(action: (() => void) | null): void {
        this.splitAction?.destroy(); this.splitAction = null;
        if (action) { this.splitAction = this.actionButton('End split',action,'view-restore-symbolic'); this.actions.add_child(this.splitAction); }
        this.layout();
    }
    setTouchSetup(action: ((event: any) => boolean) | null): void {
        this.approveTouch = action;
        if (!action) { this.touchSetup?.destroy(); this.touchSetup = null; this.layout(); return; }
        if (this.touchSetup) return;
        this.touchSetup = this.actionButton('Enable gestures',()=>{},'input-touchpad-symbolic');
        this.touchSetup.accessible_name = _('Touch to enable gestures');
        this.touchSetup.connect('touch-event', (_actor: any,event: any) => {
            if (event.type() === Clutter.EventType.TOUCH_BEGIN && this.approveTouch?.(event)) return Clutter.EVENT_STOP;
            return Clutter.EVENT_PROPAGATE;
        });
        this.actions.add_child(this.touchSetup); this.layout();
    }
    private actionButton(label: string, action: () => void, icon: string): any {
        const item = new St.Button({style_class:'convertibled-dock-action',can_focus:true,reactive:true,accessible_name:_(label)});
        const content = new St.BoxLayout({vertical:true,style_class:'convertibled-nav-content'});
        content.add_child(new St.Icon({icon_name:icon,icon_size:20,x_align:Clutter.ActorAlign.CENTER}));
        const caption = new St.Label({text:_(label),x_align:Clutter.ActorAlign.CENTER});
        caption.clutter_text.line_wrap = false;
        caption.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
        content.add_child(caption); item.set_child(content); item.connect('clicked',action);
        return item;
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
            const content = new St.BoxLayout({vertical:true,style_class:'convertibled-dock-app-content'});
            content.add_child(app.create_icon_texture(40));
            const indicator = new St.Widget({style_class:'convertibled-dock-running',x_align:Clutter.ActorAlign.CENTER});
            indicator.opacity = app.get_state() === Shell.AppState.RUNNING ? 255 : 0;
            content.add_child(indicator); item.set_child(content);
            item.connect('clicked', () => this.activate(app)); this.apps.add_child(item);
        }
        this.layout();
    }
    destroy(): void { this.cleanup.clear(); this.actor.destroy(); }
}
