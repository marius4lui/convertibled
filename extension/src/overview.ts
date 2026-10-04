import St from 'gi://St';
import Clutter from 'gi://Clutter';
import {Cleanup} from './ownership.js';
import {button, clear, scroll} from './ui.js';
import {_} from './localized.js';
export class WindowOverview {
    readonly actor = new St.BoxLayout({vertical:true,style_class:'convertibled-surface',reactive:true});
    private content = new St.BoxLayout({vertical:true,style_class:'convertibled-grid'});
    private cleanup = new Cleanup();
    private windowCleanup = new Cleanup();
    private selection: any[] = [];
    constructor(private windows: () => any[], private activate: (window: any) => void,
        private split: (a: any, b: any) => void, private close: () => void) {
        const header = new St.BoxLayout({style_class:'convertibled-grid'});
        header.add_child(button('Back', close, 'go-previous-symbolic'));
        header.add_child(button('Split selected apps', () => {
            if (this.selection.length === 2) split(this.selection[0],this.selection[1]);
        },'view-dual-symbolic'));
        this.actor.add_child(header); this.actor.add_child(scroll(this.content));
        this.cleanup.signal(global.display, 'window-created', () => this.refresh());
        this.cleanup.signal(global.workspace_manager, 'active-workspace-changed', () => this.refresh());
    }
    refresh(): void {
        this.windowCleanup.clear(); clear(this.content); this.selection = [];
        for (const window of this.windows()) {
            const source = window.get_compositor_private(); if (!source) continue;
            const card = new St.BoxLayout({vertical:true,style_class:'convertibled-widget'});
            const preview = new St.Button({can_focus:true,reactive:true,accessible_name:window.get_title()});
            const clone = new Clutter.Clone({source,reactive:false});
            const rect = window.get_frame_rect();
            const factor = Math.min(320 / Math.max(rect.width,1), 180 / Math.max(rect.height,1));
            clone.set_size(rect.width,rect.height); clone.set_scale(factor,factor);
            preview.set_size(320,180); preview.set_child(clone);
            preview.connect('clicked', () => this.activate(window));
            card.add_child(preview);
            const title = new St.Label({text:window.get_title() ?? _('Application')}); card.add_child(title);
            const select = button('Select for split', () => {
                if (this.selection.includes(window)) { this.selection = this.selection.filter(w => w !== window); select.remove_style_pseudo_class('checked'); }
                else if (this.selection.length < 2) { this.selection.push(window); select.add_style_pseudo_class('checked'); }
            });
            card.add_child(select); this.content.add_child(card);
            this.windowCleanup.signal(window, 'unmanaged', () => this.refresh());
            this.windowCleanup.signal(window, 'notify::title', () => { title.text = window.get_title() ?? _('Application'); });
        }
        if (!this.content.get_n_children()) this.content.add_child(new St.Label({text:_('No windows on this display')}));
    }
    destroy(): void { this.windowCleanup.clear(); this.cleanup.clear(); this.actor.destroy(); }
}
