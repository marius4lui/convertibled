import {system,Actor} from './native-env.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
const {Home}=await import('../dist/home.js');
test('Home consumes Gio AppInfo records and resolves native ShellApp icons', () => {
    const info={get_id:()=> 'org.test.desktop',get_name:()=> 'Test app',get_description:()=> 'Editor',
        get_keywords:()=> ['text'],should_show:()=>true};
    const app={get_id:info.get_id,get_name:info.get_name,create_icon_texture:()=>new Actor()};
    system.get_installed=()=>[info];system.lookup_app=()=>app;
    let launched=null;const home=new Home(value=>launched=value);
    const tile=home.grid.children[0].children[0];tile.children[0].emit('clicked');
    assert.equal(launched,app);
    home.search.text='nonexistent';home.refresh();assert.equal(home.grid.children[0].text,'No matching apps');
    home.destroy();system.get_installed=()=>[];
});
