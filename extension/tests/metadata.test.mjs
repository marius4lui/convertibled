import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {workspaceVersion} from '../tools/version.mjs';
test('bundle targets only agreed GNOME version', () => {
  const metadata = JSON.parse(readFileSync('dist/metadata.json'));
  assert.deepEqual(metadata['shell-version'], ['50']);
  assert.equal(metadata.uuid, 'convertibled@convertibled.org');
  assert.equal(metadata['version-name'],workspaceVersion(readFileSync('../Cargo.toml','utf8')));
});
test('canonical version parser never falls back to unrelated package versions',()=>{
  assert.equal(workspaceVersion('[package]\nversion="9.0.0"\n[workspace.package]\nversion="1.2.3-preview.1"'), '1.2.3-preview.1');
  assert.throws(()=>workspaceVersion('[package]\nversion="9.0.0"'));
});
