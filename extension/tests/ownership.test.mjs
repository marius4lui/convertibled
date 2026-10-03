import test from 'node:test';
import assert from 'node:assert/strict';
import {OwnedState, Cleanup} from '../dist/ownership.js';
test('restores original across repeated owned changes', () => {
    const states = new OwnedState((a, b) => a === b);
    states.remember('window', 1, 2); states.remember('window', 2, 3);
    assert.equal(states.restore('window', 3), 1);
    assert.equal(states.restore('window', 3), undefined);
});
test('later user change forfeits restoration ownership', () => {
    const states = new OwnedState((a, b) => a === b);
    states.remember('window', 1, 2);
    assert.equal(states.restore('window', 9), undefined);
});
test('cleanup is LIFO and idempotent', () => {
    const log = []; const cleanup = new Cleanup();
    cleanup.add(() => log.push(1)); cleanup.add(() => log.push(2));
    cleanup.clear(); cleanup.clear(); assert.deepEqual(log, [2, 1]);
});
