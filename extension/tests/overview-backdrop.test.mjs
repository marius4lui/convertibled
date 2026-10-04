import {Emitter, main} from './native-env.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
globalThis.__native.Cogl={Color:{from_string:value=>[true,value]}};
globalThis.__native.GDesktopEnums={BackgroundShading:{VERTICAL:1}};
globalThis.__native.Meta.Background=class {
    constructor(properties){Object.assign(this,properties);}
    set_gradient(...args){this.gradient=args;}
};
const {OverviewBackdrop}=await import('../dist/overview-backdrop.js');
function content(){return {background:{native:true},rounded_clip_radius:30,brightness:0.6,
    set(properties){Object.assign(this,properties);}};}
function workspace(monitorIndex=0){
    const manager=Object.assign(new Emitter(),{backgroundActor:{content:content()}});
    return {monitorIndex,_background:{_bgManager:manager}};
}
function install(views){main.overview._overview={controls:{_workspacesDisplay:{_workspacesViews:views}}};}

test('internal native content keeps clipping and dimming; external output remains native',()=>{
    const internal=workspace(),external=workspace(1),a=internal._background._bgManager,b=external._background._bgManager;
    const original=a.backgroundActor.content.background,externalOriginal=b.backgroundActor.content.background;
    install([{_workspaces:[internal]},{_workspaces:[external]}]);
    const backdrop=new OverviewBackdrop();backdrop.show(0,false);
    assert.deepEqual(a.backgroundActor.content.background.gradient,[1,'#222d40','#151c29']);
    assert.equal(a.backgroundActor.content.rounded_clip_radius,30);
    assert.equal(a.backgroundActor.content.brightness,0.6);
    assert.equal(b.backgroundActor.content.background,externalOriginal);assert.equal(b.signals.size,0);
    backdrop.hide();backdrop.hide();assert.equal(a.backgroundActor.content.background,original);assert.equal(a.signals.size,0);
});
test('secondary internal output, replacement content and palette refresh are owned and restored',()=>{
    const ws=workspace(1),manager=ws._background._bgManager,first=manager.backgroundActor.content;
    const original=first.background;install([{}, {_workspacesView:{_workspace:ws}}]);
    const backdrop=new OverviewBackdrop();backdrop.show(1,false);
    const next=content(),nextOriginal=next.background;manager.backgroundActor.content=next;manager.emit('changed');
    assert.deepEqual(next.background.gradient,[1,'#222d40','#151c29']);
    backdrop.show(1,true);assert.equal(first.background,original);assert.equal(manager.signals.size,1);
    assert.deepEqual(next.background.gradient,[1,'#f5f7fc','#e7edf7']);
    backdrop.hide();assert.equal(next.background,nextOriginal);assert.equal(manager.signals.size,0);
});
test('later background owner wins; unavailable paths and disposed contents clean safely',()=>{
    const ws=workspace(),manager=ws._background._bgManager;install([{_workspaces:[ws]}]);
    const backdrop=new OverviewBackdrop();backdrop.show(0,false);
    const replacement={user:true};manager.backgroundActor.content.background=replacement;
    backdrop.hide();assert.equal(manager.backgroundActor.content.background,replacement);
    backdrop.show(0,true);manager.backgroundActor.content.set=()=>{throw Error('disposed');};
    assert.doesNotThrow(()=>backdrop.hide());assert.equal(manager.signals.size,0);
    delete main.overview._overview;assert.doesNotThrow(()=>backdrop.show(0,false));backdrop.hide();
});
