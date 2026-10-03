import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
test('window adapter uses GNOME 50 maximize flags API', () => {
    const source = readFileSync('src/windows.ts','utf8');
    assert.ok(source.includes('get_maximize_flags()'));
    assert.ok(!source.includes('get_maximized()'));
});
