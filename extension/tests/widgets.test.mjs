import {Settings,timers} from './native-env.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
const {Widgets}=await import('../dist/widgets.js');
test('local widgets preserve configured order and render service/battery failures', () => {
    const settings=new Settings();settings.values.widgets=['battery','clock','battery','unknown'];
    const widgets=new Widgets(settings,{auto(){},lock(){},settings(){}});
    assert.equal(widgets.actor.children.length,2);
    assert.match(widgets.actor.children[0].children[0].text,/Battery status unavailable\nSession service unavailable/);
    widgets.setSession('tablet',true,true);
    assert.match(widgets.actor.children[0].children[0].text,/Tablet mode/);
    widgets.battery={get_cached_property:key=>({deep_unpack:()=>key==='IsPresent'?true:53.5})};
    widgets.update();assert.match(widgets.actor.children[0].children[0].text,/Battery 54%/);
    settings.values.widgets=[];settings.emit('changed::widgets');assert.equal(widgets.actor.children.length,0);
    widgets.destroy();assert.equal(timers.size,0);
});
