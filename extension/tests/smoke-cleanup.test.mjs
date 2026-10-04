import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const windowsBash=`${process.env.ProgramFiles??'C:/Program Files'}/Git/bin/bash.exe`;
const bash=process.platform==='win32' ? (existsSync(windowsBash) ? windowsBash : null) : 'bash';
const helper=fileURLToPath(new URL('../tools/smoke-cleanup.sh',import.meta.url)).replaceAll('\\','/');
function run(failures,original,invalid=false) {
    return execFileSync(bash,['--noprofile','--norc','-c',`
        set -euo pipefail
        source "$1"
        root=$(mktemp -d /tmp/convertibled-shell-smoke.XXXXXXXX)
        calls=0
        failures=$2
        rm() {
            calls=$((calls+1))
            if (( calls <= failures )); then return 1; fi
            command rm "$@"
        }
        sleep() { :; }
        candidate=$root
        if [[ "$4" == true ]]; then candidate=/; fi
        result=0
        cleanup_smoke_root "$candidate" "$3" || result=$?
        printf '%s %s\\n' "$result" "$calls"
        command rm -rf -- "$root"
    `,'cleanup-test',helper,String(failures),String(original),String(invalid)],
    {encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim();
}
test('native smoke cleanup retries late writers and preserves the original test status', {skip:!bash}, () => {
    assert.equal(run(2,0),'0 3');
    assert.equal(run(2,7),'7 3');
});
test('persistent native smoke cleanup errors fail successful tests without masking existing failures', {skip:!bash}, () => {
    assert.equal(run(30,0),'1 20');
    assert.equal(run(30,7),'7 20');
});
test('native smoke cleanup never deletes an unexpected root', {skip:!bash}, () => {
    assert.equal(run(0,0,true),'1 0');
});
