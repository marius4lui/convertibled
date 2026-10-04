import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Shell from 'gi://Shell';
import Pango from 'gi://Pango';
import * as Favorites from 'resource:///org/gnome/shell/ui/appFavorites.js';
import {searchApps, gridColumns, type AppInfo} from './apps.js';
import {Cleanup} from './ownership.js';
import {button, clear, scroll} from './ui.js';
import {_} from './localized.js';
export class Home {
    readonly actor = new St.BoxLayout({vertical:true,style_class:'convertibled-surface convertibled-home',reactive:true});
    private header = new St.BoxLayout({vertical:true,style_class:'convertibled-home-header',x_align:Clutter.ActorAlign.CENTER});
    private title = new St.Label({text:_('Home'),style_class:'convertibled-home-title',y_align:Clutter.ActorAlign.CENTER});
    private search = new St.Entry({hint_text:_('Search apps'),style_class:'convertibled-search',can_focus:true,accessible_name:_('Search apps'),x_expand:true});
    private favorites = new St.BoxLayout({style_class:'convertibled-app-row',y_align:Clutter.ActorAlign.START});
    private favoriteSection = new St.BoxLayout({vertical:true,style_class:'convertibled-home-section'});
    private grid = new St.BoxLayout({vertical:true,style_class:'convertibled-app-grid',y_align:Clutter.ActorAlign.START});
    private content = new St.BoxLayout({vertical:true,style_class:'convertibled-home-content',x_align:Clutter.ActorAlign.CENTER,y_align:Clutter.ActorAlign.START});
    private appHeading = new St.Label({text:_('All apps'),style_class:'convertibled-section-heading',x_expand:true,y_align:Clutter.ActorAlign.CENTER});
    private editButton: any;
    private editCaption: any;
    private heading = new St.BoxLayout({style_class:'convertibled-section-tools'});
    private favoriteScroll: any;
    private widgets: any;
    private cleanup = new Cleanup();
    private width = 736;
    private appInfos: AppInfo[] = [];
    private limit = 40;
    private editing = false;
    private compact = false;
    private textScale = 1;
    private widgetsLast = false;
    constructor(private launch: (app: any) => void) {
        this.header.add_child(this.title);
        this.header.add_child(this.search); this.actor.add_child(this.header);
        this.favoriteSection.add_child(new St.Label({text:_('Favorites'),style_class:'convertibled-section-heading'}));
        this.favoriteScroll = scroll(this.favorites); this.favoriteScroll.y_expand = false;
        this.favoriteSection.add_child(this.favoriteScroll); this.content.add_child(this.favoriteSection);
        const apps = new St.BoxLayout({vertical:true,style_class:'convertibled-home-section'});
        this.heading.add_child(this.appHeading);
        this.editButton = button('Edit favorites', () => { this.editing = !this.editing; this.refresh(); },'starred-symbolic');
        this.editCaption = this.editButton.get_children()[0].get_children().at(-1);
        this.editCaption.clutter_text.line_wrap = true;
        this.editCaption.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
        this.editButton.toggle_mode = true; this.heading.add_child(this.editButton);
        apps.add_child(this.heading); apps.add_child(this.grid); this.content.add_child(apps);
        this.actor.add_child(scroll(this.content));
        this.cleanup.signal(this.search.clutter_text, 'text-changed', () => { this.limit = 40; this.refresh(); });
        this.cleanup.signal(Shell.AppSystem.get_default(), 'installed-changed', () => { this.readApps(); this.refresh(); });
        this.cleanup.signal(Favorites.getAppFavorites(), 'changed', () => this.refresh());
        this.readApps(); this.resize(800);
    }
    addWidgets(actor: any): void {
        this.widgets = actor; this.content.insert_child_at_index(actor,this.widgetsLast ? this.content.get_n_children() : 0);
    }
    private readApps(): void {
        this.appInfos = Shell.AppSystem.get_default().get_installed().filter((info: any) => info.should_show())
            .map((info: any) => ({id:info.get_id(),name:info.get_name(),description:info.get_description() ?? '',
                keywords:info.get_keywords?.() ?? []}));
    }
    resize(width: number,height = 800,textScale = 1): void {
        const widgetsLast = width < 700 || height < 600;
        if (widgetsLast !== this.widgetsLast) {
            this.widgetsLast = widgetsLast;
            if (this.widgets) {
                this.content.remove_child(this.widgets);
                this.content.insert_child_at_index(this.widgets,widgetsLast ? this.content.get_n_children() : 0);
            }
        }
        const padding = width < 600 ? 20 : 40;
        const contentWidth = Math.min(1040,Math.max(160,width - padding * 2));
        const compact = height < 460, vertical = width < 900 * textScale, scale = Math.max(1,textScale);
        if (this.width === contentWidth && this.compact === compact &&
            this.header.vertical === vertical && this.textScale === scale) return;
        this.width = contentWidth; this.textScale = scale; this.compact = compact;
        this.actor.style = `padding: ${compact ? 12 : 24}px ${padding}px;`;
        this.title.visible = !this.compact;
        this.header.vertical = vertical;
        this.heading.vertical = contentWidth < 440 * scale;
        this.editButton.width = Math.min(contentWidth,230 * scale);
        this.editCaption.width = Math.max(80,this.editButton.width - 64);
        this.editButton.x_align = this.heading.vertical ? Clutter.ActorAlign.START : Clutter.ActorAlign.FILL;
        this.favoriteScroll.height = Math.ceil(86 + 36 * scale);
        this.header.width = this.width; this.content.width = this.width; this.refresh();
    }
    private appButton(app: any, editable = false): any {
        const columns = gridColumns(this.width + 32,152 * this.textScale);
        const tile = new St.BoxLayout({vertical:true,style_class:'convertibled-app-tile',width:Math.floor((this.width - (columns - 1) * 12) / columns)});
        const result = new St.Button({style_class:editable ? 'convertibled-app' : 'convertibled-app convertibled-favorite-app',can_focus:true,
            accessible_name:app.get_name(),reactive:true,x_expand:true});
        const box = new St.BoxLayout({vertical:true,style_class:'convertibled-app-content'});
        const icon = app.create_icon_texture(editable ? 64 : 48); icon.x_align = Clutter.ActorAlign.CENTER; box.add_child(icon);
        const label = new St.Label({text:app.get_name(),style_class:'convertibled-app-label',
            width:Math.max(60,tile.width - 24),height:Math.ceil(36 * this.textScale),x_align:Clutter.ActorAlign.CENTER});
        label.clutter_text.line_wrap = true; label.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
        label.clutter_text.ellipsize = Pango.EllipsizeMode.END;
        box.add_child(label); result.set_child(box); result.connect('clicked', () => this.launch(app)); tile.add_child(result);
        if (editable && this.editing) {
            const favorite = Favorites.getAppFavorites();
            const isFavorite = favorite.isFavorite(app.get_id());
            const toggle = new St.Button({style_class:'convertibled-favorite-toggle',can_focus:true,reactive:true,
                toggle_mode:true,checked:isFavorite,x_align:Clutter.ActorAlign.CENTER,
                accessible_name:`${_(isFavorite ? 'Remove favorite' : 'Add favorite')}: ${app.get_name()}`});
            toggle.set_child(new St.Icon({icon_name:isFavorite ? 'starred-symbolic' : 'non-starred-symbolic',icon_size:20}));
            toggle.connect('clicked', () => {
                if (favorite.isFavorite(app.get_id())) favorite.removeFavorite(app.get_id());
                else favorite.addFavorite(app.get_id());
            }); tile.add_child(toggle);
        }
        return tile;
    }
    refresh(): void {
        clear(this.favorites); clear(this.grid);
        const favorites = Favorites.getAppFavorites().getFavorites();
        for (const app of favorites) this.favorites.add_child(this.appButton(app));
        const query = this.search.get_text().trim();
        this.favoriteSection.visible = !query && !this.compact && favorites.length > 0;
        if (this.widgets) this.widgets.visible = !query && !this.compact;
        this.appHeading.text = _(query ? 'Search results' : 'All apps');
        this.editButton.checked = this.editing;
        const system = Shell.AppSystem.get_default();
        const filtered = searchApps(this.appInfos,query);
        const columns = gridColumns(this.width + 32,152 * this.textScale);
        let row: any;
        filtered.slice(0,this.limit).forEach((info, index) => {
            if (index % columns === 0) { row = new St.BoxLayout({style_class:'convertibled-app-row'}); this.grid.add_child(row); }
            const app = system.lookup_app(info.id); if (app) row.add_child(this.appButton(app,true));
        });
        if (filtered.length > this.limit) this.grid.add_child(button('Show more apps', () => { this.limit += 40; this.refresh(); }));
        if (!filtered.length) {
            const empty = new St.BoxLayout({vertical:true,style_class:'convertibled-empty-state',x_expand:true});
            empty.add_child(new St.Icon({icon_name:'system-search-symbolic',icon_size:32,x_align:Clutter.ActorAlign.CENTER}));
            const addMessage = (text: string,style: string) => {
                const label = new St.Label({text:_(text),style_class:style,width:Math.max(80,this.width - 64),x_align:Clutter.ActorAlign.CENTER});
                label.clutter_text.line_wrap = true; label.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
                empty.add_child(label);
            };
            addMessage(query ? 'No matching apps' : 'No apps available','convertibled-empty-title');
            if (query) addMessage('Try another search','convertibled-empty-detail');
            this.grid.add_child(empty);
        }
    }
    focusSearch(): void { this.search.grab_key_focus(); }
    destroy(): void { this.cleanup.clear(); this.actor.destroy(); }
}
