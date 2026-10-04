import test from 'node:test';
import assert from 'node:assert/strict';
import {fitWindowPreview,overviewLayout} from '../dist/overview-layout.js';
import {Actor,Emitter} from './native-env.mjs';
globalThis.__native.St.Widget = Actor;
const {WindowOverview} = await import('../dist/overview.js');
function makeWindow(title='Editor',width=1200,height=800) {
    const source = new Actor({width,height});
    const window = Object.assign(new Emitter(),{get_title:()=>title,get_compositor_private:()=>source,
        get_frame_rect:()=>({width:source.width,height:source.height})});
    return {window,source};
}
function cards(overview) { return overview.content.children.flatMap(row => row.children); }
test('live window texture fits actual allocated viewport, updates with source and releases signals', () => {
    const {window,source} = makeWindow();
    let activated=null; const overview = new WindowOverview(()=>[window],value=>activated=value,()=>{},()=>{});
    overview.resize(1200); overview.refresh();
    const preview=cards(overview)[0].children[0],viewport=preview.children[0],clone=viewport.children[0];
    viewport.width=360;viewport.height=220;viewport.emit('notify::allocation');
    assert.ok(Math.abs(clone.width / clone.height - 1.5)<0.00001); assert.ok(Math.abs(clone.height - 220)<0.00001);
    assert.ok(Math.abs(clone.x - 15)<0.00001);assert.ok(Math.abs(clone.y)<0.00001);assert.equal(clone.scale,undefined);
    source.width=800;source.height=1200;source.emit('notify::allocation');
    assert.ok(Math.abs(clone.width/clone.height - 2/3)<0.00001);
    assert.ok(Math.abs(clone.height - 220)<0.00001);assert.ok(clone.x>100);
    preview.emit('clicked');assert.equal(activated,window);
    overview.refresh();assert.equal(source.signals.size,1);assert.equal(viewport.signals.size,0);
    overview.destroy();assert.equal(source.signals.size,0);assert.equal(window.signals.size,0);
});
test('split selections survive a responsive rebuild and enforce a pair', () => {
    const windows=[makeWindow('One'),makeWindow('Two'),makeWindow('Three')].map(value=>value.window);
    let applied;const overview = new WindowOverview(()=>windows,()=>{},(a,b)=>applied=[a,b],()=>{});
    overview.refresh();
    const select=index=>cards(overview)[index].children[1].children[1];
    assert.equal(select(0).accessible_name,'Select for split: One');
    select(0).emit('clicked');assert.equal(overview.splitButton.reactive,false);
    select(1).emit('clicked');select(2).emit('clicked');
    assert.equal(select(2).checked,false);assert.equal(overview.splitButton.reactive,true);
    overview.resize(550);assert.equal(overview.content.children.length,3);
    assert.equal(select(0).checked,true);assert.equal(select(1).checked,true);
    overview.splitButton.emit('clicked');assert.deepEqual(applied,windows.slice(0,2));
    select(1).emit('clicked');assert.equal(overview.splitButton.can_focus,false);
    overview.destroy();
});
test('overview explains an empty workspace and invalid source sizes cannot create NaN allocations', () => {
    const overview = new WindowOverview(()=>[],()=>{},()=>{},()=>{});overview.refresh();
    assert.equal(overview.status.text,'Your workspace is clear');assert.equal(overview.splitButton.reactive,false);
    assert.ok(overview.content.children[0].children.some(actor=>actor.text==='No windows on this display'));
    assert.deepEqual(fitWindowPreview(0,800,320,180),{width:0,height:0,x:0,y:0});
    assert.deepEqual(fitWindowPreview(Infinity,800,320,180),{width:0,height:0,x:0,y:0});overview.destroy();
});
test('overview adapts portrait and landscape card rows without oversized previews', () => {
    assert.equal(overviewLayout(550).columns,1);
    assert.equal(overviewLayout(800).columns,2);
    assert.equal(overviewLayout(1400).columns,3);
    for(const width of [320,550,800,1400]) {
        const layout=overviewLayout(width);assert.ok(layout.cardWidth*layout.columns<=width);
        assert.ok(layout.previewHeight<=270);
    }
});
