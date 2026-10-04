import Gio from 'gi://Gio';
import {OwnedState, Cleanup} from './ownership.js';
export class RotationLock {
    private settings: any;
    private owned = new OwnedState<string,boolean>((a,b) => a === b);
    private cleanup = new Cleanup();
    private writing = false;
    private target: boolean | null = null;
    private userChanged = false;
    error: string | null = null;
    constructor(changed: () => void) {
        const schema = Gio.SettingsSchemaSource.get_default()?.lookup('org.gnome.settings-daemon.peripherals.touchscreen',true);
        if (!schema?.has_key('orientation-lock')) { this.error = 'Native rotation lock unavailable'; return; }
        this.settings = new Gio.Settings({settings_schema:schema});
        this.cleanup.signal(this.settings,'changed::orientation-lock', () => {
            if (!this.writing && this.target !== null) { this.userChanged = true; this.owned.forget('lock'); }
            changed();
        });
    }
    get available(): boolean { return Boolean(this.settings) && this.settings.is_writable('orientation-lock'); }
    get locked(): boolean { return this.settings?.get_boolean('orientation-lock') ?? false; }
    apply(locked: boolean): void {
        if (locked !== this.target) { this.target = locked; this.userChanged = false; }
        if (this.userChanged) { this.error = 'Rotation lock changed by user'; return; }
        if (!this.available) { this.error = 'Native rotation lock is unavailable or read-only'; return; }
        const original = this.locked;
        if (original === locked) { this.error = null; return; }
        this.owned.remember('lock',original,locked);
        this.writing = true;
        const accepted = this.settings.set_boolean('orientation-lock',locked);
        this.writing = false;
        if (!accepted) {
            this.owned.forget('lock'); this.error = 'GNOME rejected rotation lock';
        } else this.error = null;
    }
    restore(): void {
        this.target = null; this.userChanged = false; this.error = null;
        const original = this.owned.restore('lock',this.locked);
        if (original !== undefined && this.available) {
            this.writing = true; this.settings.set_boolean('orientation-lock',original); this.writing = false;
        }
    }
    destroy(): void { this.cleanup.clear(); this.restore(); this.settings = null; }
}
