import {Emitter,Settings,main,notifications} from './native-env.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
const {WindowController} = await import('../dist/windows.js');
const {SplitController} = await import('../dist/split-controller.js');
const area={x:0,y:0,width:800,height:600};
function window(x) {
    return Object.assign(new Emitter(),{rect:{x,y:30,width:300,height:200},flags:0,failMoves:0,
        get_frame_rect(){return this.rect;},get_maximize_flags(){return this.flags;},get_monitor(){return 0;},
        get_window_type(){return 0;},get_transient_for(){return null;},is_fullscreen(){return false;},
        is_above(){return false;},is_override_redirect(){return false;},is_skip_taskbar(){return false;},
        can_maximize(){return true;},allows_resize(){return this.flags===0;},get_work_area_current_monitor(){return area;},
        maximize(){this.flags=3;this.rect={...area};},unmaximize(){this.flags=0;},
        move_resize_frame(_user,x,y,width,height){
            if(this.failMoves>0){this.failMoves--;throw new Error('Injected Mutter placement failure');}
            this.rect={x,y,width,height};
        },set_maximize_flags(flags){this.flags=flags;},
        get_min_size(){return [true,200,100];},get_client_content_rect(){return this.rect;},raise(){},
    });
}
test('tablet-maximized windows can enter split despite native interactive resize restriction', () => {
    const windows=new WindowController(),first=window(20),second=window(350);
    windows.maximize(first,0);windows.maximize(second,0);
    assert.equal(first.allows_resize(),false);
    const split=new SplitController(windows,new Settings(),()=>{});
    assert.equal(split.apply(first,second,area,0),true);
    assert.equal(first.rect.width,376);assert.equal(second.rect.x,424);
    split.clear();windows.restore();
});
test('nonresizable ordinary windows are rejected without moving either window', () => {
    const windows=new WindowController(),first=window(20),second=window(350);
    first.allows_resize=()=>false;first.can_maximize=()=>false;
    const before=[windows.snapshot(first),windows.snapshot(second)];
    const split=new SplitController(windows,new Settings(),()=>{});
    assert.equal(split.apply(first,second,area,0),false);
    assert.deepEqual([windows.snapshot(first),windows.snapshot(second)],before);
});
test('second placement failure restores both windows and existing laptop restoration ownership', () => {
    const windows=new WindowController(),first=window(20),second=window(350),changes=[];
    const original=[windows.snapshot(first),windows.snapshot(second)];
    windows.maximize(first,0);windows.maximize(second,0);
    const before=[windows.snapshot(first),windows.snapshot(second)];
    const split=new SplitController(windows,new Settings(),active=>changes.push(active));
    second.failMoves=1;
    assert.equal(split.apply(first,second,area,0),false);
    assert.deepEqual([windows.snapshot(first),windows.snapshot(second)],before);
    assert.equal(windows.owns(first),true);assert.equal(windows.owns(second),true);
    assert.deepEqual(changes,[false]);assert.equal(main.layoutManager.chrome.length,0);
    assert.match(notifications.at(-1)[1],/Previous window positions were restored/);
    windows.restore();
    assert.deepEqual([windows.snapshot(first),windows.snapshot(second)],original);
});
test('rollback failure reports incomplete restoration while still rolling back the other window', () => {
    const windows=new WindowController(),first=window(20),second=window(350),changes=[];
    windows.maximize(first,0);windows.maximize(second,0);
    const before=windows.snapshot(first);
    const split=new SplitController(windows,new Settings(),active=>changes.push(active));
    second.failMoves=2;
    assert.equal(split.apply(first,second,area,0),false);
    assert.deepEqual(windows.snapshot(first),before);
    assert.equal(windows.owns(first),true);assert.equal(windows.owns(second),false);
    assert.deepEqual(changes,[false]);assert.equal(main.layoutManager.chrome.length,0);
    assert.match(notifications.at(-1)[1],/could not be restored/);
});
