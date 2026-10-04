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
