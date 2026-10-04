import {rmSync} from 'node:fs';
import {resolve,dirname,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
const extensionRoot=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const output=resolve(extensionRoot,'dist');
if(!output.startsWith(extensionRoot+sep))throw new Error('Build output escaped extension workspace');
rmSync(output,{recursive:true,force:true});
