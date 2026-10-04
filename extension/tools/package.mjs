import {copyFileSync, mkdirSync, cpSync} from 'node:fs';
import {compileMo} from './compile-mo.mjs';
mkdirSync('dist', {recursive: true});
for (const file of ['metadata.json', 'stylesheet.css']) copyFileSync(file, `dist/${file}`);
cpSync('schemas', 'dist/schemas', {recursive: true});
compileMo('po/de.po','dist/locale/de/LC_MESSAGES/convertibled.mo');
