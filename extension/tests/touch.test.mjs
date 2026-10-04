import {timers} from './native-env.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
const {TouchNavigation}=await import('../dist/touch.js');
const device={get_device_type:()=>1};
const event=(type,sequence,x=200,y=890)=>({type:()=>type,get_event_sequence:()=>sequence,get_source_device:()=>device,
    get_coords:()=>[x,y],get_time:()=>100});
test('claims begin/update/end and opens held overview before finger release', () => {
    const actions=[],touch=new TouchNavigation(()=>({x:100,y:0,width:600,height:900}),()=>true,a=>actions.push(a));
    assert.equal(touch.handle(event(1,'one')),1);assert.equal(touch.handle(event(2,'one',200,850)),1);
    assert.deepEqual(actions,['dock']);const [id,callback]=[...timers.entries()][0];timers.delete(id);callback();
    assert.deepEqual(actions,['dock','overview']);assert.equal(touch.handle(event(3,'one',200,850)),1);
    assert.equal(timers.size,0);
});
test('canceled candidates stay consumed through end and outside edge sequences propagate', () => {
    const actions=[],touch=new TouchNavigation(()=>({x:100,y:0,width:600,height:900}),()=>true,a=>actions.push(a));
    assert.equal(touch.handle(event(1,'outside',200,200)),0);
    assert.equal(touch.handle(event(1,'one')),1);assert.equal(touch.handle(event(2,'one',400,800)),1);
    assert.equal(touch.handle(event(3,'one',400,800)),1);assert.deepEqual(actions,[]);assert.equal(timers.size,0);
});
