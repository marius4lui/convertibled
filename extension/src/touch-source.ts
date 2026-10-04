import Clutter from 'gi://Clutter';
import {Cleanup} from './ownership.js';
export class TouchSource {
    private approved: any = null;
    private cleanup = new Cleanup();
    reason = 'Approve the integrated touchscreen for this login before enabling gestures';
    constructor(private seat: any,private settings: any,private changed: () => void) {
        // Event numbers can be reused. Never carry numeric-node approvals across login.
        settings.set_string('touchscreen-device-node','');
        this.cleanup.signal(settings,'changed::touchscreen-device-node', () => this.approve());
        if (seat) this.cleanup.signal(seat,'device-removed', (_seat: any,device: any) => {
            if (device === this.approved) {
                this.approved = null; settings.set_string('touchscreen-device-node','');
                this.reason = 'Touchscreen disconnected; approve the current device again'; this.changed();
            }
        });
    }
    private approve(): void {
        this.approved = null;
        const node = this.settings.get_string('touchscreen-device-node');
        if (/^\/dev\/input\/event[0-9]+$/.test(node)) {
            this.approved = this.seat?.list_devices().find((device: any) =>
                device.get_device_type() === Clutter.InputDeviceType.TOUCHSCREEN_DEVICE && device.get_device_node() === node) ?? null;
        }
        this.reason = this.approved ? 'Explicit current-login touchscreen approval'
            : 'No approved currently connected touchscreen; visible navigation remains available';
        this.changed();
    }
    approveDevice(device: any): boolean {
        if (!this.seat?.list_devices().includes(device) ||
            device.get_device_type() !== Clutter.InputDeviceType.TOUCHSCREEN_DEVICE) return false;
        this.approved = device; this.reason = 'Explicit physical touch confirmation for this login';
        this.changed(); return true;
    }
    allows(device: any): boolean { return Boolean(this.approved && device === this.approved); }
    get available(): boolean { return this.approved !== null; }
    destroy(): void { this.cleanup.clear(); this.approved = null; this.settings.set_string('touchscreen-device-node',''); }
}
