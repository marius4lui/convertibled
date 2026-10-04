import './mock-gi.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
const {DesktopController} = await import('../dist/desktop.js');
const workspace = {};
function window(overrides = {}) {
    let next = 0;
    return {minimized:false,monitor:0,workspace,requests:[],signals:new Map(),
        get_monitor(){return this.monitor;},get_workspace(){return this.workspace;},
        get_window_type(){return 0;},get_transient_for(){return null;},
        is_fullscreen(){return false;},is_above(){return false;},
        is_override_redirect(){return false;},is_skip_taskbar(){return false;},
        can_minimize(){return true;},
        connect(name,callback){this.signals.set(++next,{name,callback});return next;},
        disconnect(id){this.signals.delete(id);},
        emit(name){for(const signal of [...this.signals.values()]) if(signal.name===name) signal.callback();},
        minimize(){this.requests.push('minimize');this.minimized=true;this.emit('notify::minimized');},
        unminimize(){this.requests.push('unminimize');this.minimized=false;this.emit('notify::minimized');},
        ...overrides};
}
test('only explicit Home hides apps, repeated navigation restores once without activation', () => {
    const desktop=new DesktopController(),app=window();
    assert.deepEqual(app.requests,[]);
    desktop.show([app],0,workspace);desktop.show([app],0,workspace);
    assert.deepEqual(app.requests,['minimize']);
    desktop.restore();desktop.restore();
    assert.deepEqual(app.requests,['minimize','unminimize']);assert.equal(app.signals.size,0);
});
test('Home preserves preexisting minimization and excludes external, transient and special windows', () => {
    const desktop=new DesktopController();
    const excluded=[{minimized:true},{monitor:1},{workspace:{}},
        {get_transient_for:()=>({})},{get_window_type:()=>2},
        {is_above:()=>true},{is_override_redirect:()=>true},{is_skip_taskbar:()=>true},
        {can_minimize:()=>false}].map(overrides=>window(overrides));
    desktop.show(excluded,0,workspace);desktop.restore();
    for(const app of excluded){assert.deepEqual(app.requests,[]);assert.equal(app.signals.size,0);}
});
test('Home hides standalone dialog apps and fullscreen apps without changing their geometry', () => {
    const desktop=new DesktopController();
    const apps=[window({get_window_type:()=>1}),window({is_fullscreen:()=>true})];
    desktop.show(apps,0,workspace);
    for(const app of apps) assert.equal(app.minimized,true);
    desktop.restore();
    for(const app of apps) assert.deepEqual(app.requests,['minimize','unminimize']);
});
test('native reopening drops ownership even if user minimizes again', () => {
    const desktop=new DesktopController(),app=window();desktop.show([app],0,workspace);
    app.unminimize();assert.equal(app.signals.size,0);app.minimize();desktop.restore();
    assert.equal(app.minimized,true);assert.deepEqual(app.requests,['minimize','unminimize','minimize']);
});
test('window destruction, workspace changes and explicit relinquishment clean signals', () => {
    for(const action of [app=>app.emit('unmanaged'),app=>app.emit('workspace-changed'),
        (app,desktop)=>desktop.forget(app)]) {
        const desktop=new DesktopController(),app=window();desktop.show([app],0,workspace);
        action(app,desktop);desktop.restore();
        assert.equal(app.signals.size,0);assert.deepEqual(app.requests,['minimize']);
    }
});
test('moving a hidden window to another monitor does not restore over the user change', () => {
    const desktop=new DesktopController(),app=window();desktop.show([app],0,workspace);
    app.monitor=1;desktop.restore();assert.equal(app.minimized,true);assert.equal(app.signals.size,0);
});
test('moving a hidden window out and back permanently relinquishes restoration', () => {
    const desktop=new DesktopController(),app=window();desktop.show([app],0,workspace);
    app.monitor=1;app.emit('position-changed');assert.equal(app.signals.size,0);
    app.monitor=0;app.emit('position-changed');desktop.restore();
    assert.equal(app.minimized,true);assert.deepEqual(app.requests,['minimize']);
});
test('rejected minimization owns nothing and another app still hides', () => {
    const desktop=new DesktopController(),refused=window({minimize(){}}),app=window();
    desktop.show([refused,app],0,workspace);assert.equal(refused.signals.size,0);
    desktop.restore();assert.deepEqual(refused.requests,[]);assert.equal(app.minimized,false);
});
