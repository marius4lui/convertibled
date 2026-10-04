import './native-env.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
const {NativePreference}=await import('../dist/native-preference.js');
const {RotationLock}=await import('../dist/rotation.js');
test('native user edits survive reconciliation and mode exit', () => {
    const preference=new NativePreference('test','orientation-lock',()=>{});
    preference.apply('enabled');assert.equal(preference.value,true);
    preference.settings.set_boolean('orientation-lock',false);
    preference.apply('enabled');assert.equal(preference.value,false);assert.match(preference.error,/user/);
    preference.restore();assert.equal(preference.value,false);preference.destroy();
});
test('rotation restores own values but relinquishes later user edits', () => {
    const rotation=new RotationLock(()=>{});
    rotation.apply(true);rotation.restore();assert.equal(rotation.locked,false);
    rotation.apply(true);rotation.settings.set_boolean('orientation-lock',false);
    rotation.apply(true);assert.equal(rotation.locked,false);rotation.restore();assert.equal(rotation.locked,false);
    rotation.destroy();
});
