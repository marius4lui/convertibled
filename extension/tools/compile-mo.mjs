import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {dirname} from 'node:path';
export function compileMo(source,destination) {
    const entries=[];let current=null;let field=null;
    for(const line of readFileSync(source,'utf8').split(/\r?\n/)) {
        if(!line.trim()||line.startsWith('#'))continue;
        const match=/^(msgid|msgstr) (".*")$/.exec(line);
        if(match){
            if(match[1]==='msgid'){current={msgid:'',msgstr:''};entries.push(current);}
            if(!current)throw new Error('Translation before msgid');
            field=match[1];current[field]=JSON.parse(match[2]);
        } else if(line.startsWith('"')&&current&&field)current[field]+=JSON.parse(line);
        else throw new Error(`Unsupported PO syntax: ${line}`);
    }
    entries.sort((a,b)=>Buffer.compare(Buffer.from(a.msgid),Buffer.from(b.msgid)));
    if(new Set(entries.map(e=>e.msgid)).size!==entries.length)throw new Error('Duplicate PO msgid');
    const count=entries.length,tableEnd=28+count*16;
    const header=Buffer.alloc(tableEnd);header.writeUInt32LE(0x950412de,0);
    header.writeUInt32LE(count,8);header.writeUInt32LE(28,12);header.writeUInt32LE(28+count*8,16);
    const data=[];let offset=tableEnd;
    for(const [field,table] of [['msgid',28],['msgstr',28+count*8]]) {
        entries.forEach((entry,index)=>{
            const bytes=Buffer.from(entry[field],'utf8');
            header.writeUInt32LE(bytes.length,table+index*8);header.writeUInt32LE(offset,table+index*8+4);
            data.push(bytes,Buffer.from([0]));offset+=bytes.length+1;
        });
    }
    mkdirSync(dirname(destination),{recursive:true});writeFileSync(destination,Buffer.concat([header,...data]));
}
