import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Cleanup} from './ownership.js';
import {SessionBridge} from './bridge.js';
import {DisplayObserver} from './display.js';
import type {Monitor} from './monitors.js';
import type {Status} from './status.js';
import {Home} from './home.js';
import {Dock} from './dock.js';
import {WindowOverview} from './overview.js';
import {Widgets} from './widgets.js';
import {WindowController} from './windows.js';
export default class TabletExtension extends Extension {
    private cleanup?: Cleanup;
    private bridge?: SessionBridge;
    private display?: DisplayObserver;
    private home?: Home;
    private dock?: Dock;
    private overview?: WindowOverview;
    private widgets?: Widgets;
    private monitor: Monitor | null = null;
    private status: Status | null = null;
    private active = false;
    private windows = new WindowController();
    private settings: any;
    private animations: any;
    private reported = '';
    enable(): void {
        this.cleanup = new Cleanup(); this.settings = this.getSettings();
        this.animations = new Gio.Settings({schema_id:'org.gnome.desktop.interface'});
        this.home = new Home(app => this.activateApp(app));
        this.dock = new Dock(surface => this.navigate(surface), app => this.activateApp(app));
        this.overview = new WindowOverview(() => this.internalWindows(), window => this.activate(window),
            (a,b) => this.split(a,b), () => this.navigate('dock'));
        this.widgets = new Widgets(this.settings, {
            auto: () => this.bridge?.profile('auto'),
            lock: () => this.bridge?.rotationLock(!this.status?.desired.rotation_lock),
            settings: () => Gio.AppInfo.create_from_commandline('convertibled-settings',null,Gio.AppInfoCreateFlags.NONE).launch([],null),
        });
        this.home.actor.add_child(this.widgets.actor);
        for (const actor of [this.home.actor,this.dock.actor,this.overview.actor]) {
            actor.hide(); Main.layoutManager.addChrome(actor,{affectsStruts:false,trackFullscreen:true});
            this.cleanup.add(() => Main.layoutManager.removeChrome(actor));
        }
        this.cleanup.signal(Main.sessionMode,'updated', () => this.reconcile());
        this.cleanup.signal(Main.layoutManager,'monitors-changed', () => this.display?.refresh());
        this.cleanup.signal(global.display,'window-created', (_d: any,window: any) => {
            if (this.active && this.monitor) this.windows.maximize(window,this.monitor.index);
        });
        this.cleanup.signal(global.display,'notify::focus-window', () => {
            if (this.active && global.display.focus_window) this.hideSurfaces();
        });
        this.display = new DisplayObserver(() => Main.layoutManager.monitors,
            monitor => { this.monitor = monitor; this.reconcile(); });
        this.bridge = new SessionBridge(status => { this.status = status; this.reconcile(); });
    }
    private internalWindows(): any[] {
        if (!this.monitor) return [];
        return global.get_window_actors().map((actor: any) => actor.meta_window)
            .filter((window: any) => this.windows.eligible(window,this.monitor!.index) &&
                window.located_on_workspace(global.workspace_manager.get_active_workspace()));
    }
    private reconcile(): void {
        const allowed = Main.sessionMode.currentMode === 'user' && !Main.sessionMode.isLocked &&
            Boolean(this.monitor) && this.status?.desired.tablet_workspace === true;
        if (allowed && !this.active) {
            this.active = true; this.position();
            for (const window of this.internalWindows()) this.windows.maximize(window,this.monitor!.index);
            // Do not open Home or take focus from the application during folding.
            this.dock?.actor.show();
        } else if (!allowed && this.active) {
            this.active = false; this.hideSurfaces(); this.dock?.actor.hide(); this.windows.restore();
        } else if (allowed) this.position();
        const report = {tablet_workspace:this.active,rotation_lock:false,
            status:this.active ? 'applied' : this.status?.desired.tablet_workspace ? 'unsupported' : 'applied',
            error:this.status?.desired.tablet_workspace && !this.active ? 'Internal display or unlocked GNOME session unavailable' : null,
            capabilities:{tablet_workspace:Boolean(this.monitor),rotation_lock:false,osk:true,split_view:true}};
        const json = JSON.stringify(report);
        if (json !== this.reported) { this.reported = json; this.bridge?.report(report); }
    }
    private position(): void {
        if (!this.monitor) return;
        const area = Main.layoutManager.getWorkAreaForMonitor(this.monitor.index);
        this.dock?.actor.set_position(area.x,area.y + area.height - 88);
        this.dock?.actor.set_size(area.width,88);
        for (const actor of [this.home?.actor,this.overview?.actor]) {
            actor?.set_position(area.x,area.y); actor?.set_size(area.width,Math.max(100,area.height - 96));
        }
        this.home?.resize(area.width);
    }
    private hideSurfaces(): void { this.home?.actor.hide(); this.overview?.actor.hide(); }
    private navigate(surface: 'home' | 'overview' | 'dock'): void {
        if (!this.active) return;
        this.hideSurfaces(); this.dock?.actor.show();
        const actor = surface === 'home' ? this.home?.actor : surface === 'overview' ? this.overview?.actor : null;
        if (!actor) return;
        if (surface === 'overview') this.overview?.refresh();
        actor.show(); actor.opacity = 0;
        actor.ease({opacity:255,duration:this.animations.get_boolean('enable-animations') ? 200 : 0,
            mode:Clutter.AnimationMode.EASE_OUT_QUAD});
        if (surface === 'home') this.home?.focusSearch();
    }
    private activate(window: any): void { this.hideSurfaces(); Main.activateWindow(window); }
    private activateApp(app: any): void {
        const window = app.get_windows().find((w: any) => w.get_monitor() === this.monitor?.index);
        this.hideSurfaces(); if (window) Main.activateWindow(window); else app.open_new_window(-1);
    }
    private split(_first: any, _second: any): void {
        // Implemented by the constrained split controller in the next batch.
        Main.notify('convertibled','Split controls are not available in this build');
    }
    disable(): void {
        this.active = false; this.windows.restore();
        this.bridge?.destroy(); this.display?.destroy(); this.cleanup?.clear();
        this.widgets?.destroy(); this.home?.destroy(); this.dock?.destroy(); this.overview?.destroy();
        this.bridge = undefined; this.display = undefined; this.cleanup = undefined;
        this.home = undefined; this.dock = undefined; this.overview = undefined; this.widgets = undefined;
        this.monitor = null; this.status = null; this.reported = '';
    }
}
