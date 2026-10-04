export function workspaceVersion(toml) {
    let inPackage=false;let version=null;
    for(const line of toml.split(/\r?\n/)) {
        if(/^\[/.test(line.trim()))inPackage=line.trim()==='[workspace.package]';
        if(!inPackage)continue;
        const match=/^\s*version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)"\s*(?:#.*)?$/.exec(line);
        if(match){if(version!==null)throw new Error('Duplicate canonical version');version=match[1];}
    }
    if(version===null)throw new Error('Missing canonical Cargo workspace version');return version;
}
