import test from 'node:test';
import assert from 'node:assert/strict';
import {beforeDock} from '../dist/work-area.js';
test('native boxed rectangle accessors survive conversion to a plain work area', () => {
    const area=Object.create(Object.defineProperties({}, {
        x:{get:()=>0},y:{get:()=>32},width:{get:()=>1280},height:{get:()=>768},
    }));
    assert.deepEqual({...area},{});
    assert.deepEqual(beforeDock(area,{x:0,y:0,width:0,height:0},false,
        {x:0,y:0,width:1280,height:800}),{x:0,y:32,width:1280,height:768});
});
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
