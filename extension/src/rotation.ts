import Gio from 'gi://Gio';
import {OwnedState, Cleanup} from './ownership.js';
export class RotationLock {
    private settings: any;
    private owned = new OwnedState<string,boolean>((a,b) => a === b);
    private cleanup = new Cleanup();
    error: string | null = null;
    constructor(changed: () => void) {
        const schema = Gio.SettingsSchemaSource.get_default()?.lookup('org.gnome.settings-daemon.peripherals.touchscreen',true);
        if (!schema?.has_key('orientation-lock')) { this.error = 'Native rotation lock unavailable'; return; }
        this.settings = new Gio.Settings({settings_schema:schema});
        this.cleanup.signal(this.settings,'changed::orientation-lock',changed);
    }
    get available(): boolean { return Boolean(this.settings) && this.settings.is_writable('orientation-lock'); }
    get locked(): boolean { return this.settings?.get_boolean('orientation-lock') ?? false; }
    apply(locked: boolean): void {
        if (!this.available) { this.error = 'Native rotation lock is unavailable or read-only'; return; }
        const original = this.locked;
        if (original === locked) { this.error = null; return; }
        this.owned.remember('lock',original,locked);
        if (!this.settings.set_boolean('orientation-lock',locked)) {
            this.owned.forget('lock'); this.error = 'GNOME rejected rotation lock';
        } else this.error = null;
    }
    restore(): void {
        const original = this.owned.restore('lock',this.locked);
        if (original !== undefined && this.available) this.settings.set_boolean('orientation-lock',original);
    }
    destroy(): void { this.cleanup.clear(); this.restore(); this.settings = null; }
}
