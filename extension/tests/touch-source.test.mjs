import {Emitter,Settings} from './native-env.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
const {TouchSource}=await import('../dist/touch-source.js');
test('explicit device approval never grants a reused event node or external device', () => {
    const internal={get_device_type:()=>1,get_device_node:()=>'/dev/input/event5'};
    const external={get_device_type:()=>1,get_device_node:()=>'/dev/input/event6'};
    const seat=Object.assign(new Emitter(),{list_devices:()=>[internal,external]});
    const settings=new Settings();settings.values['touchscreen-device-node']='/dev/input/event5';
    const source=new TouchSource(seat,settings,()=>{});assert.equal(source.available,false);
    settings.set_string('touchscreen-device-node','/dev/input/event5');
    assert.equal(source.allows(internal),true);assert.equal(source.allows(external),false);
    seat.emit('device-removed',internal);assert.equal(source.available,false);
    const reused={get_device_type:()=>1,get_device_node:()=>'/dev/input/event5'};
    assert.equal(source.allows(reused),false);assert.equal(settings.get_string('touchscreen-device-node'),'');
    source.destroy();assert.equal(seat.signals.size,0);
});
test('visible touch confirmation grants only a currently connected real touchscreen object', () => {
    const mouse={get_device_type:()=>0},touch={get_device_type:()=>1,get_device_node:()=>'/dev/input/event9'};
    const seat=Object.assign(new Emitter(),{list_devices:()=>[mouse,touch]});
    const source=new TouchSource(seat,new Settings(),()=>{});
    assert.equal(source.approveDevice(mouse),false);assert.equal(source.approveDevice({...touch}),false);
    assert.equal(source.approveDevice(touch),true);assert.equal(source.allows(touch),true);
    source.destroy();
});
