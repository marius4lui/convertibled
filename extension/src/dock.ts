import St from 'gi://St';
import Shell from 'gi://Shell';
import * as Favorites from 'resource:///org/gnome/shell/ui/appFavorites.js';
import {dockApps} from './apps.js';
import {Cleanup} from './ownership.js';
import {button, clear} from './ui.js';
export class Dock {
    readonly actor = new St.BoxLayout({style_class:'convertibled-surface',reactive:true});
    private apps = new St.BoxLayout({style_class:'convertibled-grid'});
    private cleanup = new Cleanup();
    constructor(navigate: (surface: 'home' | 'overview') => void, private activate: (app: any) => void) {
        this.actor.add_child(button('Home', () => navigate('home'), 'go-home-symbolic'));
        this.actor.add_child(button('Overview', () => navigate('overview'), 'view-grid-symbolic'));
        const scroll = new St.ScrollView({x_expand:true,overlay_scrollbars:true});
        scroll.set_child(this.apps); this.actor.add_child(scroll);
        this.cleanup.signal(Favorites.getAppFavorites(), 'changed', () => this.refresh());
        this.cleanup.signal(Shell.AppSystem.get_default(), 'app-state-changed', () => this.refresh());
        this.refresh();
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
