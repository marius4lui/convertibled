import './mock-gi.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
const {WindowController} = await import('../dist/windows.js');
function window() {
    return {rect:{x:20,y:30,width:300,height:200},flags:0,monitor:0,requests:[],
        get_frame_rect(){return this.rect;},get_maximize_flags(){return this.flags;},get_monitor(){return this.monitor;},
        get_window_type(){return 0;},get_transient_for(){return null;},is_fullscreen(){return false;},
        is_above(){return false;},is_override_redirect(){return false;},is_skip_taskbar(){return false;},
        can_maximize(){return true;},get_work_area_current_monitor(){return {x:0,y:0,width:800,height:600};},
        maximize(){this.requests.push('maximize');},unmaximize(){this.flags=0;this.requests.push('unmaximize');},
        move_resize_frame(_user,x,y,width,height){this.rect={x,y,width,height};},set_maximize_flags(flags){this.flags=flags;},
        get_min_size(){return [true,200,100];},get_client_content_rect(){return {width:280,height:180};}};
}
test('restores acknowledged asynchronous maximize without overwriting user move', () => {
    const controller = new WindowController(), w = window(); controller.maximize(w,0);
    w.rect={x:0,y:0,width:800,height:600};w.flags=3;controller.restore();
    assert.deepEqual(w.rect,{x:20,y:30,width:300,height:200});
    controller.maximize(w,0);w.rect={x:1,y:0,width:800,height:600};w.flags=3;
    controller.restore();assert.equal(w.rect.x,1);
});
test('never maximizes external or transient windows and includes decorations in minimums', () => {
    const controller=new WindowController(),w=window();controller.maximize(w,1);assert.equal(w.requests.length,0);
    assert.deepEqual(controller.minimum(w),{width:220,height:120});
    w.get_transient_for=()=>({});controller.maximize(w,0);assert.equal(w.requests.length,0);
});
