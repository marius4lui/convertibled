import test from 'node:test';
import assert from 'node:assert/strict';
import {integratedMonitor} from '../dist/monitors.js';
const monitor = {index:1,x:1000,y:0,width:800,height:600};
const physical = [[['eDP-1'],[],{'is-builtin':true}], [['DP-1'],[],{'is-builtin':false}]];
test('internal display identity does not assume primary monitor', () => {
    assert.equal(integratedMonitor([1,physical,[[1000,0,1,0,false,[['eDP-1']],{}]]],[monitor]),monitor);
});
test('mirroring and ambiguous internal identities fail closed', () => {
    assert.equal(integratedMonitor([1,physical,[[1000,0,1,0,true,[['eDP-1'],['DP-1']],{}]]],[monitor]),null);
    assert.equal(integratedMonitor([1,[],[]],[monitor]),null);
});
