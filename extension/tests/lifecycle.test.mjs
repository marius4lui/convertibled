import {main,timers,seat,settings} from './native-env.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
const {default:Extension}=await import('../dist/extension.js');
test('startup uses the GNOME 50 Clutter seat and releases touch approval on removal', () => {
    assert.equal(global.backend.get_default_seat,undefined);
    const device={get_device_type:()=>1,get_device_node:()=>'/dev/input/event42'};
    seat.devices=[device];
    const extension=new Extension();extension.enable();
    assert.equal(extension.touchSource.seat,seat);
    assert.equal(extension.touchSource.approveDevice(device),true);
    assert.equal(extension.touchSource.allows(device),true);
    settings.set_string('touchscreen-device-node','/dev/input/event42');
    assert.equal(extension.touchSource.allows(device),true);
    seat.devices=[];seat.emit('device-removed',device);
    assert.equal(extension.touchSource.available,false);
    assert.equal(settings.get_string('touchscreen-device-node'),'');
    extension.disable();assert.equal(seat.signals.size,0);
});
test('startup, fold, lock and disable preserve focus and release resources', () => {
    const extension=new Extension();extension.enable();
    assert.equal(main.layoutManager.chrome.length,3);
    assert.ok(main.layoutManager.chrome.every(a=>!a.visible));
    extension.monitor=main.layoutManager.monitors[0];
    extension.status={schema_version:1,profile:'tablet',desired:{tablet_workspace:true,rotation_lock:false}};
    extension.reconcile();
    assert.equal(globalThis.focusChanges,0);assert.equal(extension.dock.actor.visible,true);
    assert.equal(extension.home.actor.visible,false);
    main.sessionMode.isLocked=true;extension.reconcile();
    assert.ok(main.layoutManager.chrome.every(a=>!a.visible));
    extension.disable();extension.disable();
    assert.equal(main.layoutManager.chrome.length,0);assert.equal(timers.size,0);
    assert.equal(global.display.signals.size,0);assert.equal(global.stage.signals.size,0);
    main.sessionMode.isLocked=false;
});
test('explicit Home navigation honors reduced motion and OSK allocation', () => {
    const extension=new Extension();extension.enable();extension.monitor=main.layoutManager.monitors[0];
    extension.status={schema_version:1,profile:'tablet',desired:{tablet_workspace:true,rotation_lock:false}};
    extension.reconcile();extension.animations.values['enable-animations']=false;extension.navigate('home');
    assert.equal(extension.home.actor.duration,0);
    main.layoutManager.keyboardBox.visible=true;main.layoutManager.keyboardBox.set_position(0,350);
    main.layoutManager.keyboardBox.set_size(800,250);extension.position();
    assert.equal(extension.home.actor.height,254);assert.equal(extension.dock.actor.y,262);
    extension.disable();main.layoutManager.keyboardBox.visible=false;
});
test('explicit laptop native actions apply only in the active unlocked session', () => {
    const extension=new Extension();extension.enable();
    extension.status={schema_version:1,profile:'laptop',active:true,locked:false,
        desired:{tablet_workspace:false,rotation_lock:false,rotation:'disabled',osk:'enabled'}};
    extension.reconcile();assert.equal(extension.active,false);assert.equal(extension.rotation.locked,true);
    assert.equal(extension.osk.value,true);
    extension.status.active=false;extension.reconcile();
    assert.equal(extension.rotation.locked,false);assert.equal(extension.osk.value,false);
    extension.disable();
});
