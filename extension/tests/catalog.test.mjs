import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
test('packaged GNU gettext catalog contains UTF-8 German native navigation', () => {
    const bytes=readFileSync('dist/locale/de/LC_MESSAGES/convertibled.mo');
    assert.equal(bytes.readUInt32LE(0),0x950412de);
    const translations=new Map(),count=bytes.readUInt32LE(8);
    for(let index=0;index<count;index++){
        const read=(table)=>{const length=bytes.readUInt32LE(table+index*8),offset=bytes.readUInt32LE(table+index*8+4);
            return bytes.subarray(offset,offset+length).toString('utf8');};
        translations.set(read(bytes.readUInt32LE(12)),read(bytes.readUInt32LE(16)));
    }
    assert.equal(translations.get('Overview'),'Übersicht');assert.equal(translations.get('Search apps'),'Apps suchen');
    assert.equal(translations.get('End split'),'Teilung beenden');
    assert.match(translations.get(''),/charset=UTF-8/);
});
