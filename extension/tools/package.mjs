import {copyFileSync, mkdirSync, cpSync} from 'node:fs';
mkdirSync('dist', {recursive: true});
for (const file of ['metadata.json', 'stylesheet.css']) copyFileSync(file, `dist/${file}`);
cpSync('schemas', 'dist/schemas', {recursive: true});
