import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
test('bundle targets only agreed GNOME version', () => {
  const metadata = JSON.parse(readFileSync('dist/metadata.json'));
  assert.deepEqual(metadata['shell-version'], ['50']);
  assert.equal(metadata.uuid, 'convertibled@convertibled.org');
});
