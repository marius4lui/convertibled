import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Pango from 'gi://Pango';
import {Cleanup} from './ownership.js';
import {button, clear, scroll} from './ui.js';
import {fitWindowPreview, overviewLayout} from './overview-layout.js';
import {_} from './localized.js';
export class WindowOverview {
    readonly actor = new St.BoxLayout({vertical:true,style_class:'popup-menu-content convertibled-surface convertibled-overview',reactive:true});
    private content = new St.BoxLayout({vertical:true,style_class:'convertibled-overview-grid',x_expand:true,y_align:Clutter.ActorAlign.START});
    private toolbar = new St.BoxLayout({style_class:'convertibled-overview-toolbar',x_expand:true});
    private heading: any;
    private view: any;
    private scale = 1;
    private allocatedWidth?: number;
    private cleanup = new Cleanup();
    private windowCleanup = new Cleanup();
    private selection: any[] = [];
    private selectionButtons = new Map<any,any>();
    private splitButton: any;
    private status: any;
    private width = 800;
    constructor(private windows: () => any[], private activate: (window: any) => void,
        private split: (a: any, b: any) => void, private close: () => void) {
        const header = new St.BoxLayout({vertical:true,style_class:'convertibled-overview-header'});
        const back = button('Back',close,'go-previous-symbolic');
        this.toolbar.add_child(back);
        const heading = new St.BoxLayout({vertical:true,x_expand:true});
        this.heading = new St.Label({text:_('Open windows'),style_class:'convertibled-overview-title',x_expand:true});
        this.heading.clutter_text.line_wrap = true; this.heading.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
        heading.add_child(this.heading);
        this.status = new St.Label({text:_('Select two apps for split'),style_class:'convertibled-overview-status'});
        this.status.clutter_text.line_wrap = true; this.status.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
        heading.add_child(this.status); header.add_child(heading);
        this.splitButton = button('Split selected apps', () => {
            if (this.selection.length === 2) split(this.selection[0],this.selection[1]);
        },'view-dual-symbolic');
        for (const control of [back,this.splitButton]) {
            control.x_expand = true;
            const row = control.get_children()[0]; row.x_expand = true;
            const children = row.get_children(); const label = children[children.length - 1];
            label.x_expand = true; label.clutter_text.line_wrap = true; label.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
        }
        this.toolbar.add_child(this.splitButton); header.add_child(this.toolbar);
        const page = new St.BoxLayout({vertical:true,style_class:'convertibled-overview-page',x_expand:true,y_align:Clutter.ActorAlign.START});
        page.add_child(header); page.add_child(this.content);
        this.view = scroll(page); this.actor.add_child(this.view);
        this.cleanup.signal(this.view,'notify::allocation', () => {
            if (this.view.width > 0 && Math.abs(this.view.width - (this.allocatedWidth ?? 0)) > 1) {
                this.allocatedWidth = this.view.width;
                if (this.actor.visible) this.refresh();
            }
        });
        this.updateSelection();
        this.cleanup.signal(global.display, 'window-created', () => { if (this.actor.visible) this.refresh(); });
        this.cleanup.signal(global.workspace_manager, 'active-workspace-changed', () => { if (this.actor.visible) this.refresh(); });
    }
    resize(width: number,_height = 800,scale = 1): void {
        if (this.width === width && this.scale === scale) return;
        this.width = width; this.scale = scale; this.allocatedWidth = undefined;
        if (this.actor.visible) this.refresh();
    }
    private updateSelection(): void {
        const ready = this.selection.length === 2;
        this.splitButton.reactive = ready; this.splitButton.can_focus = ready;
        if (ready) this.splitButton.remove_style_pseudo_class('disabled');
        else this.splitButton.add_style_pseudo_class('disabled');
        this.status.text = this.selection.length === 0 ? _('Tap a window to continue. Select two for split.')
            : this.selection.length === 1 ? _('Choose a second window') : _('Ready to split');
        for (const [window,select] of this.selectionButtons) {
            select.checked = this.selection.includes(window);
            if (select.checked) select.add_style_pseudo_class('checked');
            else select.remove_style_pseudo_class('checked');
        }
    }
    refresh(): void {
        this.windowCleanup.clear(); clear(this.content); this.selectionButtons.clear();
        const windows = this.windows().filter(window => window.get_compositor_private());
        this.selection = this.selection.filter(window => windows.includes(window));
        const layout = overviewLayout(this.width,windows.length,this.scale,this.allocatedWidth);
        const base = this.actor.style_class.replace(/\s*convertibled-overview-compact/g,'');
        this.actor.style_class = base + (layout.compact ? ' convertibled-overview-compact' : '');
        this.toolbar.vertical = layout.stackedToolbar;
        this.content.width = layout.available;
        let row: any;
        windows.forEach((window,index) => {
            if (index % layout.columns === 0) {
                row = new St.BoxLayout({style_class:'convertibled-overview-grid-row',x_align:Clutter.ActorAlign.CENTER,y_align:Clutter.ActorAlign.START});
                this.content.add_child(row);
            }
            const source = window.get_compositor_private();
            const card = new St.BoxLayout({vertical:true,style_class:'convertibled-overview-card',width:layout.cardWidth});
            const preview = new St.Button({can_focus:true,reactive:true,style_class:'convertibled-overview-preview',
                accessible_name:window.get_title() ?? _('Application'),x_expand:true});
            // A fixed-layout viewport owns the clone allocation. Scaling a full-size
            // clone inside a Button lets St allocate it again and distorts the texture.
            const previewWidth = Math.max(1,layout.cardWidth - 34);
            const rect = window.get_frame_rect();
            const sourceAspect = (source.width || rect.width) / Math.max(1,source.height || rect.height);
            const previewHeight = Math.round(Math.min(420,Math.max(layout.previewHeight,previewWidth / Math.max(0.1,sourceAspect))));
            const viewport = new St.Widget({width:previewWidth,height:previewHeight,clip_to_allocation:true});
            const clone = new Clutter.Clone({source,reactive:false}); viewport.add_child(clone);
            const updatePreview = () => {
                const rect = window.get_frame_rect();
                const fitted = fitWindowPreview(source.width || rect.width,source.height || rect.height,
                    viewport.width,viewport.height);
                clone.set_size(fitted.width,fitted.height); clone.set_position(fitted.x,fitted.y);
            };
            updatePreview();
            this.windowCleanup.signal(viewport,'notify::allocation',updatePreview);
            this.windowCleanup.signal(source,'notify::allocation',updatePreview);
            this.windowCleanup.signal(window,'size-changed',updatePreview);
            preview.set_child(viewport); preview.connect('clicked', () => this.activate(window));
            card.add_child(preview);
            const footer = new St.BoxLayout({style_class:'convertibled-overview-card-footer'});
            const title = new St.Label({text:window.get_title() ?? _('Application'),
                style_class:'convertibled-overview-window-title',x_expand:true,y_align:Clutter.ActorAlign.CENTER});
            title.clutter_text.ellipsize = Pango.EllipsizeMode.END;
            footer.add_child(title);
            const select = new St.Button({can_focus:true,reactive:true,toggle_mode:true,
                accessible_name:`${_('Select for split')}: ${window.get_title() ?? _('Application')}`,
                style_class:'button convertibled-overview-select'});
            select.set_child(new St.Icon({icon_name:'view-dual-symbolic',icon_size:20}));
            select.connect('clicked', () => {
                if (this.selection.includes(window)) this.selection = this.selection.filter(value => value !== window);
                else if (this.selection.length < 2) this.selection.push(window);
                this.updateSelection();
            });
            this.selectionButtons.set(window,select);
            footer.add_child(select); card.add_child(footer); row.add_child(card);
            this.windowCleanup.signal(window,'unmanaged', () => this.refresh());
            this.windowCleanup.signal(window,'notify::title', () => {
                title.text = window.get_title() ?? _('Application'); preview.accessible_name = title.text;
                select.accessible_name = `${_('Select for split')}: ${title.text}`;
            });
        });
        if (!windows.length) {
            const empty = new St.BoxLayout({vertical:true,style_class:'convertibled-overview-empty',x_expand:true,
                x_align:Clutter.ActorAlign.CENTER});
            empty.add_child(new St.Icon({icon_name:'view-grid-symbolic',icon_size:56}));
            for (const [text,style] of [[_('No windows on this display'),'convertibled-overview-title'],
                [_('Open an app from Home to get started.'),'convertibled-overview-status']]) {
                const label = new St.Label({text,style_class:style,x_expand:true});
                label.clutter_text.line_wrap = true; label.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
                empty.add_child(label);
            }
            this.content.add_child(empty);
        }
        this.updateSelection();
        if (!windows.length) this.status.text = _('Your workspace is clear');
    }
    destroy(): void { this.windowCleanup.clear(); this.cleanup.clear(); this.actor.destroy(); }
}
