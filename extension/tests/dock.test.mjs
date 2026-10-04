import test from 'node:test';
import assert from 'node:assert/strict';
import {Actor,system,favorites} from './native-env.mjs';
const {Dock}=await import('../dist/dock.js');

test('dock fits sparse content, bounds portrait width and preserves navigation when apps hide', () => {
    const app={get_id:()=> 'files',get_name:()=> 'Files',get_state:()=>1,create_icon_texture:()=>new Actor()};
    favorites.getFavorites=()=>[app]; system.get_running=()=>[app];system.lookup_app=()=>app;
    const dock=new Dock(()=>{},()=>{});
    dock.resize(1280); const sparseWidth=dock.shelf.width;
    dock.setTouchSetup(()=>true);
    assert.ok(dock.shelf.width>sparseWidth);
    dock.resize(320);assert.ok(dock.shelf.width<=288);
    dock.showApps(false);assert.equal(dock.shelf.width,184);assert.equal(dock.divider.visible,false);
    assert.equal(dock.navigation.size,2);
    dock.showApps(true);assert.equal(dock.divider.visible,true);
    const setup=dock.touchSetup;dock.refresh();assert.equal(dock.touchSetup,setup);
    assert.equal(setup.destroyed,false);assert.equal(setup.accessible_name,'Touch to enable gestures');
    dock.setSuspended(true);assert.equal(dock.actor.opacity,0);assert.equal(dock.shelf.visible,false);
    dock.setSuspended(false);assert.equal(dock.shelf.visible,true);
    dock.destroy();
});

test('running app marker does not confuse pressed and running state', () => {
    let running=0;
    const app={get_id:()=> 'files',get_name:()=> 'Files',get_state:()=>running,create_icon_texture:()=>new Actor()};
    favorites.getFavorites=()=>[app];system.lookup_app=()=>app;system.get_running=()=>[];
    const dock=new Dock(()=>{},()=>{});
    const marker=()=>dock.apps.get_children()[0].get_children()[0].get_children()[1];
    assert.equal(marker().opacity,0);running=1;dock.refresh();assert.equal(marker().opacity,255);
    dock.destroy();
});
