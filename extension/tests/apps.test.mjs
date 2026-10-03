import test from 'node:test';
import assert from 'node:assert/strict';
import {searchApps, dockApps, gridColumns} from '../dist/apps.js';
const apps = [{id:'a',name:'Éditeur',description:'Text',keywords:['write']},
    {id:'b',name:'Files',description:'Folders',keywords:[]}];
test('accent-insensitive search matches all tokens and native metadata', () => {
    assert.equal(searchApps(apps, 'editeur write')[0].id, 'a');
    assert.equal(searchApps(apps, 'editeur folders').length, 0);
});
test('dock keeps favorite order and deduplicates running apps', () => {
    assert.deepEqual(dockApps(['a','b'], ['b','c']), ['a','b','c']);
    assert.equal(gridColumns(20), 1); assert.equal(gridColumns(10000), 10);
});
