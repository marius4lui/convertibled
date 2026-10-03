import test from 'node:test';
import assert from 'node:assert/strict';
import {splitLayout, nextRatio} from '../dist/split.js';
const min = {width: 200, height: 100};
test('landscape split partitions work area without overlap', () => {
    const result = splitLayout({x: 100, y: 20, width: 1000, height: 600}, 'third', min, min);
    assert.equal(result.first.width + result.second.width + result.divider.width, 1000);
    assert.equal(result.second.x, result.divider.x + result.divider.width);
});
test('portrait splits vertically and refuses incompatible minimums', () => {
    const area = {x: 0, y: 0, width: 600, height: 1000};
    assert.equal(splitLayout(area, 'half', min, min).first.height, 476);
    assert.ok(splitLayout(area, 'half', {width: 700, height: 10}, min).error);
    assert.equal(nextRatio(nextRatio(nextRatio('half'))), 'half');
});
