import Gio from 'gi://Gio';
import {OwnedState, Cleanup} from './ownership.js';
export type Action = 'enabled' | 'disabled' | 'unchanged';
export class NativePreference {
    private settings: any;
    private owned = new OwnedState<string,boolean>((a,b) => a === b);
    private cleanup = new Cleanup();
    error: string | null = null;
    constructor(schemaId: string,private key: string,changed: () => void) {
        const schema = Gio.SettingsSchemaSource.get_default()?.lookup(schemaId,true);
        if (!schema?.has_key(key)) { this.error = 'Native preference unavailable'; return; }
        this.settings = new Gio.Settings({settings_schema:schema});
        this.cleanup.signal(this.settings,`changed::${key}`,changed);
    }
    get value(): boolean { return this.settings?.get_boolean(this.key) ?? false; }
    get available(): boolean { return Boolean(this.settings) && this.settings.is_writable(this.key); }
    apply(action: Action): void {
        if (action === 'unchanged') { this.restore(); return; }
        if (!this.available) { this.error = 'Native preference unavailable or read-only'; return; }
        const target = action === 'enabled';
        if (target === this.value) { this.error = null; return; }
        this.owned.remember(this.key,this.value,target);
        if (!this.settings.set_boolean(this.key,target)) {
            this.owned.forget(this.key); this.error = 'GNOME rejected native preference';
        } else this.error = null;
    }
    restore(): void {
        const original = this.owned.restore(this.key,this.value);
        if (original !== undefined && this.available) this.settings.set_boolean(this.key,original);
    }
    destroy(): void { this.cleanup.clear(); this.restore(); }
}
