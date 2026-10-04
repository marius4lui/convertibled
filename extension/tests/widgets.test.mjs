import {Settings,timers} from './native-env.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
const {Widgets}=await import('../dist/widgets.js');
test('local widgets preserve configured order and render service/battery failures', () => {
    const settings=new Settings();settings.values.widgets=['battery','clock','battery','unknown'];
    const widgets=new Widgets(settings,{auto(){},lock(){},settings(){}});
    assert.equal(widgets.actor.children[0].children.length,2);
    assert.ok(widgets.actor.children[0].children[0].style_class.endsWith('battery'));
    assert.equal(widgets.labels.get('battery-charge').text,'—');
    assert.equal(widgets.labels.get('battery-status').text,'Battery status unavailable');
    assert.equal(widgets.labels.get('battery-mode').text,'Session service unavailable');
    widgets.setSession('tablet',true,true);assert.equal(widgets.labels.get('battery-mode').text,'Tablet mode');
    widgets.battery={get_cached_property:key=>({deep_unpack:()=>key==='IsPresent'?true:53.5})};
    widgets.update();assert.equal(widgets.labels.get('battery-charge').text,'54%');
    widgets.resize(320);assert.equal(widgets.actor.children.length,2);
    widgets.resize(1000);assert.equal(widgets.actor.children.length,1);
    settings.values.widgets=[];settings.emit('changed::widgets');assert.equal(widgets.actor.children.length,0);
    widgets.destroy();assert.equal(timers.size,0);
});

test('widget cards and action captions fit narrow and scaled layouts with configured order intact', () => {
    const settings=new Settings();const widgets=new Widgets(settings,{auto(){},lock(){},settings(){}});
    for (const scale of [1,1.25,1.5]) for (const width of [280,320,440,600,720,1040]) {
        widgets.resize(width,scale);
        const cards=widgets.actor.children.flatMap(row=>row.children);
        assert.deepEqual(cards.map(card=>card.style_class.split(' ').at(-1)),
            ['convertibled-widget-clock','convertibled-widget-battery','convertibled-widget-actions']);
        for (const row of widgets.actor.children) {
            const occupied=row.children.reduce((total,card)=>total+card.width,0)+(row.children.length-1)*16;
            assert.ok(occupied<=width);
        }
        const actions=cards.at(-1).children[1];
        assert.ok(actions.children.reduce((total,control)=>total+control.width,0)+16<=cards.at(-1).width-40);
        for (const control of actions.children) {
            const caption=control.children[0].children[1];
            assert.ok(caption.width<control.width);assert.equal(caption.clutter_text.line_wrap,true);
        }
    }
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
