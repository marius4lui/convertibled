import {Settings,timers} from './native-env.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
const {Widgets}=await import('../dist/widgets.js');
test('local widgets preserve configured order and render service/battery failures', () => {
    const settings=new Settings();settings.values.widgets=['battery','clock','battery','unknown'];
    const widgets=new Widgets(settings,{auto(){},lock(){},settings(){}});
    assert.equal(widgets.actor.children.length,2);
    assert.equal(widgets.labels.get('battery-charge').text,'—');
    assert.equal(widgets.labels.get('battery-status').text,'Battery status unavailable');
    assert.equal(widgets.labels.get('battery-mode').text,'Session service unavailable');
    widgets.setSession('tablet',true,true);assert.equal(widgets.labels.get('battery-mode').text,'Tablet mode');
    widgets.battery={get_cached_property:key=>({deep_unpack:()=>key==='IsPresent'?true:53.5})};
    widgets.update();assert.equal(widgets.labels.get('battery-charge').text,'54%');
    widgets.resize(500);assert.equal(widgets.actor.vertical,true);widgets.resize(1000);assert.equal(widgets.actor.vertical,false);
    settings.values.widgets=[];settings.emit('changed::widgets');assert.equal(widgets.actor.children.length,0);
    widgets.destroy();assert.equal(timers.size,0);
});
test('quick actions keep actual rotation state and stop updating a hidden action', () => {
    const settings=new Settings();let locked=0;
    const widgets=new Widgets(settings,{auto(){},lock(){locked++;},settings(){}});
    widgets.setSession('tablet',true,true);assert.equal(widgets.lockButton.checked,true);
    widgets.lockButton.emit('clicked');assert.equal(locked,1);
    settings.values.widgets=['clock'];settings.emit('changed::widgets');assert.equal(widgets.lockButton,null);
    widgets.setSession(null,false,false);widgets.destroy();assert.equal(timers.size,0);
});
