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
import {beforeDock} from './work-area.js';
import {TouchSource} from './touch-source.js';
import {DesktopController, desktopEligible} from './desktop.js';
import {OverviewBackdrop} from './overview-backdrop.js';
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
    private touchSource?: TouchSource;
    private desktop = new DesktopController();
    private dockStrut = false;
    private backdrop = new OverviewBackdrop();
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
        this.touchSource = new TouchSource(global.stage.context.get_backend().get_default_seat(),this.settings, () => {
            this.touch?.cancel(); this.reportApplied();
        });
        this.touch = new TouchNavigation(() => this.monitor,
            () => this.active && Main.modalCount === 0 && !Main.overview.visible && this.settings.get_boolean('gesture-enabled'),
            surface => this.navigate(surface),device => this.touchSource?.allows(device) ?? false);
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
        this.cleanup.signal(this.animations,'changed::color-scheme', () => this.appearance());
        this.cleanup.signal(this.animations,'changed::text-scaling-factor', () => this.position());
        this.appearance();
        const homeActor = this.home.actor;
        homeActor.hide(); global.window_group.add_child(homeActor);
        global.window_group.set_child_above_sibling(homeActor,Main.layoutManager._backgroundGroup);
        Main.layoutManager.trackChrome(homeActor,{affectsStruts:false,trackFullscreen:false});
        this.cleanup.add(() => {
            Main.layoutManager.untrackChrome(homeActor);
            global.window_group.remove_child(homeActor);
        });
        for (const actor of [this.dock.actor,this.overview.actor]) {
            actor.hide(); Main.layoutManager.addChrome(actor,{affectsStruts:false,trackFullscreen:false});
            this.cleanup.add(() => Main.layoutManager.removeChrome(actor));
        }
        for (const actor of [this.home.actor,this.overview.actor]) {
            actor.can_focus = true;
            this.cleanup.signal(actor,'key-press-event', (_actor: any,event: any) => {
                if (event.get_key_symbol() !== Clutter.KEY_Escape) return Clutter.EVENT_PROPAGATE;
                this.overview?.actor.hide(); this.showDesktop(); return Clutter.EVENT_STOP;
            });
        }
        this.cleanup.signal(global.display,'in-fullscreen-changed', () => {
            const fullscreen = this.monitor && Main.layoutManager.monitors[this.monitor.index]?.inFullscreen;
            if (fullscreen) { this.hideSurfaces(); this.dock?.actor.hide(); }
            else if (this.active) {
                this.dock?.setSuspended(Main.overview.visible); this.dock?.actor.show(); this.showDesktop();
            }
        });
        this.cleanup.signal(Main.sessionMode,'updated', () => this.reconcile());
        this.cleanup.signal(Main.overview,'showing', () => {
            this.touch?.cancel(); this.hideSurfaces(); this.dock?.setSuspended(true);
            this.splitController?.setVisible(false);
            if (this.active && this.monitor) this.backdrop.show(this.monitor.index,
                this.animations.get_string('color-scheme') === 'prefer-light');
        });
        this.cleanup.signal(Main.overview,'hidden', () => {
            this.backdrop.hide();
            const fullscreen = this.monitor && Main.layoutManager.monitors[this.monitor.index]?.inFullscreen;
            this.dock?.setSuspended(false);
            if (this.active && !fullscreen) {
                this.position(); this.dock?.actor.show(); this.showDesktop();
            }
        });
        this.cleanup.signal(Main.layoutManager,'monitors-changed', () => this.display?.refresh());
        this.cleanup.signal(global.display,'workareas-changed', () => {
            if (this.active && this.monitor) { this.position(); this.windows.reconcileWorkArea(this.monitor.index); }
        });
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
            if (this.active) {
                this.overview?.actor.hide(); this.showDesktop();
                this.dock?.showApps(!this.settings.get_boolean('dock-autohide'));
            }
        });
        this.cleanup.signal(global.workspace_manager,'active-workspace-changed', () => {
            this.overview?.actor.hide(); this.showDesktop();
        });
        this.cleanup.signal(global.workspace_manager,'notify::n-workspaces', () => {
            if (this.active && this.monitor && Main.overview.visible)
                this.backdrop.show(this.monitor.index,this.animations.get_string('color-scheme') === 'prefer-light');
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
    private desktopWindows(): any[] {
        if (!this.monitor) return [];
        return global.get_window_actors().map((actor: any) => actor.meta_window)
            .filter((window: any) => desktopEligible(window,this.monitor!.index) &&
                window.located_on_workspace(global.workspace_manager.get_active_workspace()));
    }
    private appearance(): void {
        const light = this.animations.get_string('color-scheme') === 'prefer-light';
        for (const actor of [this.home?.actor,this.overview?.actor,this.dock?.actor]) {
            if (!actor) continue;
            const base = actor.style_class.replace(/\s*convertibled-light/g,'');
            actor.style_class = base + (light ? ' convertibled-light' : '');
        }
        if (this.active && this.monitor && Main.overview.visible) this.backdrop.show(this.monitor.index,light);
    }
    private setDockStrut(enabled: boolean): void {
        if (!this.dock || this.dockStrut === enabled) return;
        Main.layoutManager.untrackChrome(this.dock.actor);
        Main.layoutManager.trackChrome(this.dock.actor,{affectsStruts:enabled,trackFullscreen:false});
        this.dockStrut = enabled;
    }
    private showDesktop(): void {
        const fullscreen = this.monitor && Main.layoutManager.monitors[this.monitor.index]?.inFullscreen;
        if (!this.active || Main.overview.visible || fullscreen) { this.home?.actor.hide(); return; }
        this.home?.actor.show();
        const desktopVisible = this.desktopWindows().every(window => window.minimized);
        this.dock?.select(desktopVisible ? 'home' : null);
        this.splitController?.setVisible(!desktopVisible && !this.overview?.actor.visible);
    }
    private reconcile(): void {
        const allowed = Main.sessionMode.currentMode === 'user' && !Main.sessionMode.isLocked &&
            Boolean(this.monitor) && this.status?.desired.tablet_workspace === true;
        if (allowed && !this.active) {
            this.active = true; this.position();
            this.setDockStrut(true);
            for (const window of this.internalWindows()) this.windows.maximize(window,this.monitor!.index);
            // Do not open Home or take focus from the application during folding.
            this.dock?.setSuspended(Main.overview.visible); this.dock?.actor.show(); this.showDesktop();
        } else if (!allowed && this.active) {
            this.backdrop.hide();
            this.active = false; this.touch?.cancel(); this.splitController?.clear(); this.hideSurfaces();
            this.dock?.actor.hide(); this.setDockStrut(false); this.desktop.restore(); this.windows.restore();
        } else if (allowed) this.position();
        const nativeAllowed = Main.sessionMode.currentMode === 'user' && !Main.sessionMode.isLocked &&
            this.status?.active === true && this.status.locked === false;
        if (nativeAllowed && this.status) {
            if (this.status.desired.rotation_lock_requested) this.rotation?.apply(this.status.desired.rotation_lock);
            else if (this.status.desired.rotation && this.status.desired.rotation !== 'unchanged')
                this.rotation?.apply(this.status.desired.rotation === 'disabled');
            else this.rotation?.restore();
            this.osk?.apply(this.status.desired.osk ?? 'unchanged');
        } else { this.rotation?.restore(); this.osk?.restore(); }
        this.reportApplied();
    }
    private reportApplied(): void {
        this.widgets?.setSession(this.status?.profile ?? null,this.active,this.rotation?.locked ?? false);
        this.dock?.setTouchSetup(this.touchSource?.available ? null : event => {
            const device = event.get_source_device(); const [x,y] = event.get_coords(); const area = this.monitor;
            if (!this.active || !area || x < area.x || x >= area.x + area.width || y < area.y || y >= area.y + area.height)
                return false;
            return this.touchSource?.approveDevice(device) ?? false;
        });
        const rotationRequest = this.status?.desired.rotation_lock_requested
            ? this.status.desired.rotation_lock ? 'disabled' : 'enabled' : this.status?.desired.rotation ?? 'unchanged';
        const rotationActual = this.rotation?.locked ? 'disabled' : 'enabled';
        const oskRequest = this.status?.desired.osk ?? 'unchanged';
        const oskActual = this.osk?.value ? 'enabled' : 'disabled';
        const rotationError = this.rotation?.error ??
            (rotationRequest !== 'unchanged' && rotationRequest !== rotationActual ? 'Native rotation request is not applied' : null);
        const oskError = this.osk?.error ??
            (oskRequest !== 'unchanged' && oskRequest !== oskActual ? 'Native keyboard request is not applied' : null);
        const report = {tablet_workspace:this.active,rotation_lock:this.rotation?.locked ?? false,
            status:this.active ? 'applied' : this.status?.desired.tablet_workspace ? 'unsupported' : 'applied',
            error:this.status?.desired.tablet_workspace && !this.active ? 'Internal display or unlocked GNOME session unavailable' : null,
            capabilities:{tablet_workspace:Boolean(this.monitor),rotation_lock:this.rotation?.available ?? false,
                osk:this.osk?.available ?? false,split_view:true,
                touchscreen_gestures:Boolean(this.monitor && this.touchSource?.available),
                gesture_reason:this.touchSource?.reason ?? 'No approved touchscreen'},
            action_outcomes:{rotation:{requested:rotationRequest,applied:rotationActual,
                status:rotationError ? 'unsupported' : 'applied',error:rotationError},
            osk:{requested:oskRequest,applied:oskActual,status:oskError ? 'unsupported' : 'applied',error:oskError}}};
        const json = JSON.stringify(report);
        if (this.status && this.bridge && json !== this.reported) { this.reported = json; this.bridge.report(report); }
    }
    private position(): void {
        if (!this.monitor) return;
        const workArea = Main.layoutManager.getWorkAreaForMonitor(this.monitor.index);
        const dock = this.dock!.actor;
        const area = beforeDock(workArea,{x:dock.x,y:dock.y,width:dock.width,height:dock.height},this.dockStrut,this.monitor);
        const keyboard = Main.layoutManager.keyboardBox;
        const [kx,boxY] = keyboard.get_transformed_position();
        // GNOME 50 anchors keyboardBox at the monitor bottom and translates its
        // child upwards. Reserve its final height as soon as it becomes visible.
        const monitorBottom = this.monitor.y + this.monitor.height;
        const ky = Math.min(boxY,monitorBottom - keyboard.height);
        const keyboardHere = keyboard.visible && keyboard.height > 0 &&
            kx < area.x + area.width && kx + keyboard.width > area.x &&
            boxY >= this.monitor.y && boxY <= monitorBottom && ky >= area.y;
        const usableHeight = keyboardHere ? Math.min(area.height,Math.max(0,ky - area.y)) : area.height;
        this.dock?.actor.set_position(area.x,area.y + Math.max(0,usableHeight - 88));
        this.dock?.actor.set_size(area.width,88);
        this.dock?.resize(area.width);
        for (const actor of [this.home?.actor,this.overview?.actor]) {
            actor?.set_position(area.x,area.y); actor?.set_size(area.width,Math.max(48,usableHeight - 88));
        }
        this.home?.resize(area.width,usableHeight - 88,this.animations.get_double('text-scaling-factor'));
        this.widgets?.resize(Math.min(1040,area.width - (area.width < 600 ? 40 : 80)),this.animations.get_double('text-scaling-factor'));
        this.overview?.resize(area.width,usableHeight - 88,this.animations.get_double('text-scaling-factor'));
        this.splitController?.resize({...area,height:Math.max(0,usableHeight - 88)},this.monitor.index);
    }
    private hideSurfaces(): void {
        this.dock?.select(null);
        this.home?.actor.hide(); this.overview?.actor.hide();
        const fullscreen = this.monitor && Main.layoutManager.monitors[this.monitor.index]?.inFullscreen;
        this.splitController?.setVisible(this.active && !Main.overview.visible && !fullscreen);
    }
    private navigate(surface: 'home' | 'overview' | 'dock'): void {
        if (!this.active || Main.modalCount > 0 || Main.overview.visible) return;
        this.overview?.actor.hide(); this.dock?.actor.show();
        this.dock?.showApps(true);
        if (surface === 'home') {
            this.desktop.show(this.desktopWindows(),this.monitor!.index,global.workspace_manager.get_active_workspace());
            this.showDesktop(); this.home?.actor.grab_key_focus(); return;
        }
        const actor = surface === 'overview' ? this.overview?.actor : null;
        if (!actor) { this.showDesktop(); return; }
        this.splitController?.setVisible(false);
        this.dock?.select(surface);
        this.home?.actor.hide();
        if (surface === 'overview') this.overview?.refresh();
        actor.show(); actor.opacity = 0;
        actor.ease({opacity:255,duration:this.animations.get_boolean('enable-animations') ? 200 : 0,
            mode:Clutter.AnimationMode.EASE_OUT_QUAD});
        // Navigation itself is not a text-entry request. In particular, opening
        // Home must not summon the native OSK until the user chooses search.
        actor.grab_key_focus();
    }
    private activate(window: any): void {
        this.desktop.forget(window); this.overview?.actor.hide(); Main.activateWindow(window); this.showDesktop();
    }
    private activateApp(app: any): void {
        const window = app.get_windows().find((w: any) => w.get_monitor() === this.monitor?.index);
        this.overview?.actor.hide();
        if (window) { this.desktop.forget(window); Main.activateWindow(window); } else app.open_new_window(-1);
        this.showDesktop();
    }
    private split(first: any, second: any): void {
        if (!this.monitor || !this.active) return;
        if (this.splitController?.apply(first,second,Main.layoutManager.getWorkAreaForMonitor(this.monitor.index),this.monitor.index)) {
            this.desktop.forget(first); this.desktop.forget(second);
            first.unminimize(); second.unminimize();
            this.overview?.actor.hide(); Main.activateWindow(second); this.showDesktop();
        }
    }
    disable(): void {
        this.backdrop.hide();
        this.active = false; this.touch?.cancel(); this.splitController?.clear(); this.desktop.restore(); this.windows.restore();
        this.rotation?.destroy(); this.rotation = undefined;
        this.osk?.destroy(); this.osk = undefined;
        this.touchSource?.destroy(); this.touchSource = undefined;
        this.bridge?.destroy(); this.display?.destroy(); this.cleanup?.clear();
        this.widgets?.destroy(); this.home?.destroy(); this.dock?.destroy(); this.overview?.destroy();
        this.bridge = undefined; this.display = undefined; this.cleanup = undefined;
        this.home = undefined; this.dock = undefined; this.overview = undefined; this.widgets = undefined;
        this.monitor = null; this.status = null; this.reported = '';
        this.dockStrut = false;
    }
}
