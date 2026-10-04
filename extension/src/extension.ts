import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import Meta from 'gi://Meta';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Cleanup} from './ownership.js';
import {SessionBridge, reportHealthOnce} from './bridge.js';
import {DisplayObserver} from './display.js';
import type {Monitor} from './monitors.js';
import type {Status} from './status.js';
import {Home} from './home.js';
import {Dock} from './dock.js';
import {WindowOverview} from './overview.js';
import {Widgets} from './widgets.js';
import {WindowController} from './windows.js';
import {SplitController} from './split-controller.js';
import {TouchNavigation} from './touch.js';
import {RotationLock} from './rotation.js';
import {NativePreference} from './native-preference.js';
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
    private splitController?: SplitController;
    private touch?: TouchNavigation;
    private rotation?: RotationLock;
    private osk?: NativePreference;
    private windowLaters = new Set<number>();
    enable(): void {
        try { this.start(); }
        catch (error) {
            const version = this.metadata['version-name'];
            this.disable();
            reportHealthOnce(version,false);
            console.error(`convertibled startup failed: ${String(error)}`);
            throw error;
        }
    }
    private start(): void {
        this.cleanup = new Cleanup(); this.settings = this.getSettings();
        this.splitController = new SplitController(this.windows,this.settings,
            active => this.dock?.setSplitAction(active ? () => this.splitController?.end(this.monitor!.index) : null));
        this.touch = new TouchNavigation(() => this.monitor,
            () => this.active && Main.modalCount === 0 && !Main.overview.visible && this.settings.get_boolean('gesture-enabled'),
            surface => this.navigate(surface));
        this.cleanup.signal(global.stage,'captured-event', (_stage: any,event: any) => this.touch?.handle(event));
        this.animations = new Gio.Settings({schema_id:'org.gnome.desktop.interface'});
        this.rotation = new RotationLock(() => this.reportApplied());
        this.osk = new NativePreference('org.gnome.desktop.a11y.applications','screen-keyboard-enabled', () => this.reportApplied());
        this.home = new Home(app => this.activateApp(app));
        this.dock = new Dock(surface => this.navigate(surface), app => this.activateApp(app));
        this.cleanup.signal(this.settings,'changed::dock-autohide', () => this.dock?.showApps(!this.settings.get_boolean('dock-autohide')));
        this.dock.showApps(!this.settings.get_boolean('dock-autohide'));
        this.overview = new WindowOverview(() => this.internalWindows(), window => this.activate(window),
            (a,b) => this.split(a,b), () => this.navigate('dock'));
        this.widgets = new Widgets(this.settings, {
            auto: () => this.bridge?.profile('auto'),
            lock: () => this.bridge?.rotationLock(!this.rotation?.locked),
            settings: () => Gio.AppInfo.create_from_commandline('convertibled-settings',null,Gio.AppInfoCreateFlags.NONE).launch([],null),
        });
        this.home.addWidgets(this.widgets.actor);
        for (const actor of [this.home.actor,this.dock.actor,this.overview.actor]) {
            actor.hide(); Main.layoutManager.addChrome(actor,{affectsStruts:false,trackFullscreen:false});
            this.cleanup.add(() => Main.layoutManager.removeChrome(actor));
        }
        Main.uiGroup.set_child_below_sibling(this.home.actor,global.window_group);
        this.cleanup.signal(global.display,'in-fullscreen-changed', () => {
            const fullscreen = this.monitor && Main.layoutManager.monitors[this.monitor.index]?.inFullscreen;
            if (fullscreen) { this.hideSurfaces(); this.dock?.actor.hide(); }
            else if (this.active) this.dock?.actor.show();
        });
        this.cleanup.signal(Main.sessionMode,'updated', () => this.reconcile());
        this.cleanup.signal(Main.layoutManager,'monitors-changed', () => this.display?.refresh());
        this.cleanup.signal(Main.layoutManager.keyboardBox,'notify::height', () => { if (this.active) this.position(); });
        this.cleanup.signal(Main.layoutManager.keyboardBox,'notify::visible', () => { if (this.active) this.position(); });
        this.cleanup.signal(global.display,'window-created', (_d: any,window: any) => {
            if (!this.active || !this.monitor) return;
            const laters = global.compositor.get_laters();
            const id = laters.add(Meta.LaterType.BEFORE_REDRAW, () => {
                this.windowLaters.delete(id);
                if (this.active && this.monitor && window.get_compositor_private()) {
                    try { this.windows.maximize(window,this.monitor.index); }
                    catch (error) { console.error(`convertibled new window: ${String(error)}`); }
                }
                return false;
            });
            this.windowLaters.add(id);
        });
        this.cleanup.add(() => {
            const laters = global.compositor.get_laters();
            for (const id of this.windowLaters) laters.remove(id); this.windowLaters.clear();
        });
        this.cleanup.signal(global.display,'notify::focus-window', () => {
            if (this.active && global.display.focus_window) {
                this.hideSurfaces(); this.dock?.showApps(!this.settings.get_boolean('dock-autohide'));
            }
        });
        this.display = new DisplayObserver(() => Main.layoutManager.monitors,
            monitor => { this.monitor = monitor; this.reconcile(); });
        this.bridge = new SessionBridge(status => {
            if (!this.status || !status) this.reported = '';
            this.status = status; this.reconcile();
        });
        this.bridge.reportHealth(this.metadata['version-name'],true);
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
            this.active = false; this.touch?.cancel(); this.splitController?.clear(); this.hideSurfaces(); this.dock?.actor.hide(); this.windows.restore();
            this.rotation?.restore();
            this.osk?.restore();
        } else if (allowed) this.position();
        if (allowed && this.status) {
            if (this.status.desired.rotation_lock_requested) this.rotation?.apply(this.status.desired.rotation_lock);
            else if (this.status.desired.rotation && this.status.desired.rotation !== 'unchanged')
                this.rotation?.apply(this.status.desired.rotation === 'disabled');
            else this.rotation?.restore();
            this.osk?.apply(this.status.desired.osk ?? 'unchanged');
        }
        this.reportApplied();
    }
    private reportApplied(): void {
        const report = {tablet_workspace:this.active,rotation_lock:this.rotation?.locked ?? false,
            status:this.active ? 'applied' : this.status?.desired.tablet_workspace ? 'unsupported' : 'applied',
            error:this.status?.desired.tablet_workspace && !this.active ? 'Internal display or unlocked GNOME session unavailable' : null,
            capabilities:{tablet_workspace:Boolean(this.monitor),rotation_lock:this.rotation?.available ?? false,
                osk:this.osk?.available ?? false,split_view:true},
            action_outcomes:{rotation:{requested:this.status?.desired.rotation ?? 'unchanged',
                applied:this.rotation?.locked ? 'disabled' : 'enabled',
                status:this.rotation?.error ? 'unsupported' : 'applied',error:this.rotation?.error ?? null},
            osk:{requested:this.status?.desired.osk ?? 'unchanged',applied:this.osk?.value ? 'enabled' : 'disabled',
                status:this.osk?.error ? 'unsupported' : 'applied',error:this.osk?.error ?? null}}};
        const json = JSON.stringify(report);
        if (this.status && this.bridge && json !== this.reported) { this.reported = json; this.bridge.report(report); }
    }
    private position(): void {
        if (!this.monitor) return;
        const area = Main.layoutManager.getWorkAreaForMonitor(this.monitor.index);
        const keyboard = Main.layoutManager.keyboardBox;
        const [kx,ky] = keyboard.get_transformed_position();
        const keyboardHere = keyboard.visible && keyboard.height > 0 &&
            kx < area.x + area.width && kx + keyboard.width > area.x && ky >= area.y;
        const usableHeight = keyboardHere ? Math.min(area.height,Math.max(0,ky - area.y)) : area.height;
        this.dock?.actor.set_position(area.x,area.y + Math.max(0,usableHeight - 88));
        this.dock?.actor.set_size(area.width,88);
        for (const actor of [this.home?.actor,this.overview?.actor]) {
            actor?.set_position(area.x,area.y); actor?.set_size(area.width,Math.max(48,usableHeight - 96));
        }
        this.home?.resize(area.width);
        this.splitController?.resize(area,this.monitor.index);
    }
    private hideSurfaces(): void {
        this.home?.actor.hide(); this.overview?.actor.hide();
        if (this.home) Main.uiGroup.set_child_below_sibling(this.home.actor,global.window_group);
    }
    private navigate(surface: 'home' | 'overview' | 'dock'): void {
        if (!this.active || Main.modalCount > 0 || Main.overview.visible) return;
        this.hideSurfaces(); this.dock?.actor.show();
        this.dock?.showApps(true);
        const actor = surface === 'home' ? this.home?.actor : surface === 'overview' ? this.overview?.actor : null;
        if (!actor) return;
        if (surface === 'home') Main.uiGroup.set_child_above_sibling(actor,global.window_group);
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
    private split(first: any, second: any): void {
        if (!this.monitor || !this.active) return;
        if (this.splitController?.apply(first,second,Main.layoutManager.getWorkAreaForMonitor(this.monitor.index),this.monitor.index))
            this.hideSurfaces();
    }
    disable(): void {
        this.active = false; this.touch?.cancel(); this.splitController?.clear(); this.windows.restore();
        this.rotation?.destroy(); this.rotation = undefined;
        this.osk?.destroy(); this.osk = undefined;
        this.bridge?.destroy(); this.display?.destroy(); this.cleanup?.clear();
        this.widgets?.destroy(); this.home?.destroy(); this.dock?.destroy(); this.overview?.destroy();
        this.bridge = undefined; this.display = undefined; this.cleanup = undefined;
        this.home = undefined; this.dock = undefined; this.overview = undefined; this.widgets = undefined;
        this.monitor = null; this.status = null; this.reported = '';
    }
}
