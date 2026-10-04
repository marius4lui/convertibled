import test from 'node:test';
import assert from 'node:assert/strict';
import {parseStatus} from '../dist/status.js';
test('session status fails closed on incompatible or malformed data', () => {
    const status = {schema_version:1,profile:'tablet',desired:{tablet_workspace:true,rotation_lock:false}};
    assert.equal(parseStatus(JSON.stringify(status)).desired.tablet_workspace, true);
    assert.throws(() => parseStatus(JSON.stringify({...status,schema_version:2})));
    assert.throws(() => parseStatus(JSON.stringify({...status,desired:{tablet_workspace:'yes'}})));
    assert.throws(() => parseStatus(' '.repeat(65537)));
    assert.throws(() => parseStatus(JSON.stringify({...status,desired:{...status.desired,osk:'surprise'}})));
    assert.throws(() => parseStatus(JSON.stringify({...status,desired:{...status.desired,rotation_lock_requested:'yes'}})));
});
