import Gio from 'gi://Gio';
import {OwnedState, Cleanup} from './ownership.js';
export type Action = 'enabled' | 'disabled' | 'unchanged';
export class NativePreference {
    private settings: any;
    private owned = new OwnedState<string,boolean>((a,b) => a === b);
    private cleanup = new Cleanup();
    private writing = false;
    private target: Action = 'unchanged';
    private userChanged = false;
    error: string | null = null;
    constructor(schemaId: string,private key: string,changed: () => void) {
        const schema = Gio.SettingsSchemaSource.get_default()?.lookup(schemaId,true);
        if (!schema?.has_key(key)) { this.error = 'Native preference unavailable'; return; }
        this.settings = new Gio.Settings({settings_schema:schema});
        this.cleanup.signal(this.settings,`changed::${key}`, () => {
            if (!this.writing && this.target !== 'unchanged') { this.userChanged = true; this.owned.forget(this.key); }
            changed();
        });
    }
    get value(): boolean { return this.settings?.get_boolean(this.key) ?? false; }
    get available(): boolean { return Boolean(this.settings) && this.settings.is_writable(this.key); }
    apply(action: Action): void {
        if (action === 'unchanged') { this.restore(); return; }
        if (action !== this.target) { this.target = action; this.userChanged = false; }
        if (this.userChanged) { this.error = 'Native preference changed by user'; return; }
        if (!this.available) { this.error = 'Native preference unavailable or read-only'; return; }
        const target = action === 'enabled';
        if (target === this.value) { this.error = null; return; }
        this.owned.remember(this.key,this.value,target);
        this.writing = true;
        const accepted = this.settings.set_boolean(this.key,target);
        this.writing = false;
        if (!accepted) {
            this.owned.forget(this.key); this.error = 'GNOME rejected native preference';
        } else this.error = null;
    }
    restore(): void {
        this.target = 'unchanged'; this.userChanged = false; this.error = null;
        const original = this.owned.restore(this.key,this.value);
        if (original !== undefined && this.available) {
            this.writing = true; this.settings.set_boolean(this.key,original); this.writing = false;
        }
    }
    destroy(): void { this.cleanup.clear(); this.restore(); }
}
