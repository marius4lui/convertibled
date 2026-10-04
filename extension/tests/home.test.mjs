import {system,Actor,favorites} from './native-env.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
const {Home}=await import('../dist/home.js');
const info=(id,name)=>({get_id:()=>id,get_name:()=>name,get_description:()=> 'Editor',get_keywords:()=> ['text'],should_show:()=>true});
const app=info=>({get_id:info.get_id,get_name:info.get_name,create_icon_texture:size=>new Actor({icon_size:size})});
test('Home resolves native icons, launches apps and gives search a clear empty state', () => {
    const record=info('org.test.desktop','Test app'); const native=app(record);
    system.get_installed=()=>[record];system.lookup_app=()=>native;
    let launched=null;const home=new Home(value=>launched=value);
    const tile=home.grid.children[0].children[0];tile.children[0].emit('clicked');
    assert.equal(launched,native);assert.equal(tile.children.length,1);
    assert.equal(tile.children[0].children[0].children[0].icon_size,64);
    const widgets=new Actor();home.addWidgets(widgets);
    home.search.text='nonexistent';home.refresh();
    assert.equal(home.appHeading.text,'Search results');assert.equal(widgets.visible,false);
    assert.equal(home.grid.children[0].children[1].text,'No matching apps');
    assert.equal(home.grid.children[0].children[2].text,'Try another search');
    home.destroy();system.get_installed=()=>[];
});
test('favorite editing is explicit and shares the GNOME owner', () => {
    const record=info('org.favorite.desktop','Favorite');const native=app(record);
    system.get_installed=()=>[record];system.lookup_app=()=>native;
    let saved=false;favorites.isFavorite=()=>saved;favorites.getFavorites=()=>saved?[native]:[];
    favorites.addFavorite=id=>{assert.equal(id,record.get_id());saved=true;favorites.emit('changed');};
    favorites.removeFavorite=()=>{saved=false;favorites.emit('changed');};
    const home=new Home(()=>{});home.editButton.emit('clicked');
    let toggle=home.grid.children[0].children[0].children[1];
    assert.equal(toggle.accessible_name,'Add favorite: Favorite');toggle.emit('clicked');
    assert.equal(home.favoriteSection.visible,true);
    toggle=home.grid.children[0].children[0].children[1];
    assert.equal(toggle.checked,true);toggle.emit('clicked');assert.equal(saved,false);
    home.editButton.emit('clicked');assert.equal(home.grid.children[0].children[0].children.length,1);
    home.destroy();system.get_installed=()=>[];favorites.getFavorites=()=>[];favorites.isFavorite=()=>false;
});
test('Home caps wide content, adapts narrow app rows and keeps pagination reachable', () => {
    const records=Array.from({length:65},(_,index)=>info(`${index}.desktop`,String(index).padStart(2,'0')));
    system.get_installed=()=>records;system.lookup_app=id=>app(records.find(record=>record.get_id()===id));
    const home=new Home(()=>{});home.resize(1800);
    assert.equal(home.content.width,1040);assert.equal(home.header.width,1040);
    const count=()=>home.grid.children.filter(child=>child.style_class==='convertibled-app-row').reduce((sum,row)=>sum+row.children.length,0);
    assert.equal(count(),40);home.grid.children.at(-1).emit('clicked');assert.equal(count(),65);
    const normalColumns=home.grid.children[0].children.length;
    home.resize(1800,800,1.25);assert.ok(home.grid.children[0].children.length<normalColumns);
    home.resize(360);assert.equal(home.content.width,320);assert.equal(home.grid.children[0].children.length,2);
    home.search.text='01';home.search.clutter_text.emit('text-changed');assert.equal(home.limit,40);
    assert.equal(count(),1);home.destroy();system.get_installed=()=>[];
});

test('Home bounds translated controls and long captions across narrow and large-text allocations', () => {
    const records=Array.from({length:12},(_,index)=>info(`${index}.desktop`,'An exceptionally long installed application name'));
    system.get_installed=()=>records;system.lookup_app=id=>app(records.find(record=>record.get_id()===id));
    const home=new Home(()=>{});
    for (const scale of [1,1.25,1.5]) for (const width of [320,360,480,600,800,1024]) {
        home.resize(width,800,scale);
        assert.ok(home.header.width<=width);assert.ok(home.editButton.width<=home.content.width);
        if (home.content.width<440*scale) assert.equal(home.heading.vertical,true);
        for (const row of home.grid.children) {
            const occupied=row.children.reduce((total,tile)=>total+tile.width,0)+(row.children.length-1)*12;
            assert.ok(occupied<=home.content.width);
            for (const tile of row.children) {
                const launch=tile.children[0],label=launch.children[0].children[1];
                assert.ok(label.width<tile.width);assert.equal(label.clutter_text.line_wrap,true);
                assert.equal(launch.accessible_name,'An exceptionally long installed application name');
            }
        }
    }
    home.destroy();system.get_installed=()=>[];
});

test('keyboard-height Home preserves search and apps while removing ancillary sections', () => {
    const home=new Home(()=>{});const widgets=new Actor();home.addWidgets(widgets);
    home.resize(1280,300);assert.equal(home.title.visible,false);assert.equal(widgets.visible,false);
    assert.equal(home.favoriteSection.visible,false);assert.equal(home.search.visible,true);
    home.resize(1280,700);assert.equal(home.title.visible,true);assert.equal(widgets.visible,true);
    const child=home.grid.children[0];home.resize(1280,700);assert.equal(home.grid.children[0],child);
    home.destroy();
});
