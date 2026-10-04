import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Shell from 'gi://Shell';
import * as Favorites from 'resource:///org/gnome/shell/ui/appFavorites.js';
import {searchApps, gridColumns, type AppInfo} from './apps.js';
import {Cleanup} from './ownership.js';
import {button, clear, scroll} from './ui.js';
import {_} from './localized.js';
export class Home {
    readonly actor = new St.BoxLayout({vertical:true,style_class:'convertibled-surface',reactive:true});
    private search = new St.Entry({hint_text:_('Search apps'),can_focus:true,accessible_name:_('Search apps')});
    private favorites = new St.BoxLayout({style_class:'convertibled-grid'});
    private grid = new St.BoxLayout({vertical:true,style_class:'convertibled-grid'});
    private cleanup = new Cleanup();
    private width = 800;
    constructor(private launch: (app: any) => void) {
        this.actor.add_child(this.search); this.actor.add_child(scroll(this.favorites));
        this.actor.add_child(scroll(this.grid));
        this.cleanup.signal(this.search.clutter_text, 'text-changed', () => this.refresh());
        this.cleanup.signal(Shell.AppSystem.get_default(), 'installed-changed', () => this.refresh());
        this.cleanup.signal(Favorites.getAppFavorites(), 'changed', () => this.refresh());
        this.refresh();
    }
    resize(width: number): void { this.width = width; this.refresh(); }
    private appButton(app: any, editable = false): any {
        const result = new St.Button({style_class:'button convertibled-app',can_focus:true,
            accessible_name:app.get_name(),reactive:true});
        const box = new St.BoxLayout({vertical:true});
        box.add_child(app.create_icon_texture(48));
        box.add_child(new St.Label({text:app.get_name(),x_align:Clutter.ActorAlign.CENTER}));
        result.set_child(box); result.connect('clicked', () => this.launch(app));
        if (!editable) return result;
        const tile = new St.BoxLayout({vertical:true}); tile.add_child(result);
        const favorite = Favorites.getAppFavorites();
        const isFavorite = favorite.isFavorite(app.get_id());
        tile.add_child(button(isFavorite ? 'Remove favorite' : 'Add favorite', () => {
            if (favorite.isFavorite(app.get_id())) favorite.removeFavorite(app.get_id());
            else favorite.addFavorite(app.get_id());
        },isFavorite ? 'starred-symbolic' : 'non-starred-symbolic'));
        return tile;
    }
    refresh(): void {
        clear(this.favorites); clear(this.grid);
        for (const app of Favorites.getAppFavorites().getFavorites()) this.favorites.add_child(this.appButton(app));
        const system = Shell.AppSystem.get_default();
        const apps: AppInfo[] = system.get_installed().filter((app: any) => app.get_app_info()?.should_show())
            .map((app: any) => ({id:app.get_id(),name:app.get_name(),
                description:app.get_description() ?? '',keywords:app.get_app_info()?.get_keywords() ?? []}));
        const filtered = searchApps(apps, this.search.get_text());
        const columns = gridColumns(this.width,176);
        let row: any;
        filtered.forEach((info, index) => {
            if (index % columns === 0) { row = new St.BoxLayout({style_class:'convertibled-grid'}); this.grid.add_child(row); }
            const app = system.lookup_app(info.id); if (app) row.add_child(this.appButton(app,true));
        });
        if (!filtered.length) this.grid.add_child(new St.Label({text:_('No matching apps')}));
    }
    focusSearch(): void { this.search.grab_key_focus(); }
    destroy(): void { this.cleanup.clear(); this.actor.destroy(); }
}
