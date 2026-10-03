import test from 'node:test';
import assert from 'node:assert/strict';
import {EdgeGesture} from '../dist/gesture.js';
const area = {x:100,y:0,width:600,height:900};
test('edge gestures expose dock, home and hold overview', () => {
    for (const [y,time,expected] of [[850,200,'dock'],[700,200,'home'],[850,600,'overview']]) {
        const gesture = new EdgeGesture(); gesture.begin({x:200,y:890,time:0},area);
        assert.equal(gesture.end({x:200,y,time}),expected);
    }
});
test('outside integrated screen, diagonal and canceled gestures do nothing', () => {
    const gesture = new EdgeGesture();
    assert.equal(gesture.begin({x:20,y:890,time:0},area),false);
    gesture.begin({x:200,y:890,time:0},area);
    assert.equal(gesture.end({x:400,y:700,time:200}),null);
    gesture.begin({x:200,y:890,time:0},area); gesture.cancel();
    assert.equal(gesture.end({x:200,y:700,time:200}),null);
});
