import test from 'node:test';
import assert from 'node:assert/strict';
import {beforeDock} from '../dist/work-area.js';
test('owned bottom strut reconstruction prevents repeated dock inset feedback', () => {
    const monitor={x:0,y:0,width:800,height:600},dock={x:0,y:512,width:800,height:88};
    const reserved={x:0,y:32,width:800,height:480};
    const base=beforeDock(reserved,dock,true,monitor);
    assert.equal(base.height,568);assert.equal(base.y+base.height-88,dock.y);
    assert.deepEqual(beforeDock(reserved,dock,false,monitor),reserved);
});
test('OSK-middle and external dock geometry cannot claim bottom strut', () => {
    const monitor={x:0,y:0,width:800,height:600},area={x:0,y:32,width:800,height:568};
    assert.deepEqual(beforeDock(area,{x:800,y:512,width:800,height:88},true,monitor),area);
    assert.deepEqual(beforeDock(area,{x:0,y:262,width:800,height:88},true,monitor),area);
});
