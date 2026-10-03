import St from 'gi://St';
import Clutter from 'gi://Clutter';
import {gettext as _} from 'resource:///org/gnome/shell/extensions/extension.js';
export function button(label: string, action: () => void, icon?: string): any {
    const result = new St.Button({style_class: 'button convertibled-button',
        can_focus: true, reactive: true, accessible_name: _(label)});
    const row = new St.BoxLayout({style_class: 'convertibled-grid'});
    if (icon) row.add_child(new St.Icon({icon_name:icon,icon_size:24}));
    row.add_child(new St.Label({text:_(label),y_align:Clutter.ActorAlign.CENTER}));
    result.set_child(row); result.connect('clicked', action);
    return result;
}
export function clear(actor: any): void { for (const child of actor.get_children()) child.destroy(); }
export function scroll(child: any): any {
    const view = new St.ScrollView({x_expand:true,y_expand:true,overlay_scrollbars:true});
    view.set_child(child); return view;
}
