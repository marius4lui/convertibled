import {registerHooks} from 'node:module';
export class Emitter {
    signals = new Map(); sequence = 0;
    connect(name,callback){const id=++this.sequence;this.signals.set(id,{name,callback});return id;}
    disconnect(id){this.signals.delete(id);}
    emit(name,...args){for(const signal of [...this.signals.values()])if(signal.name===name)signal.callback(this,...args);}
}
export class Actor extends Emitter {
    children=[];visible=true;opacity=255;width=0;height=0;x=0;y=0;destroyed=false;
    constructor(properties={}){super();Object.assign(this,properties);this.clutter_text=new Emitter();}
    add_child(child){this.children.push(child);child.parent=this;}
    get_children(){return [...this.children];} get_n_children(){return this.children.length;}
    set_child(child){this.add_child(child);} set_size(w,h){this.width=w;this.height=h;}
    set_position(x,y){this.x=x;this.y=y;}set_scale(x,y){this.scale=[x,y];}
    get_transformed_position(){return [this.x,this.y];}
    hide(){this.visible=false;}show(){this.visible=true;}
    grab_key_focus(){globalThis.focusChanges++;} get_text(){return this.text??'';}
    add_style_pseudo_class(){}remove_style_pseudo_class(){}ease(properties){Object.assign(this,properties);}
    destroy(){this.destroyed=true;this.signals.clear();for(const child of this.children)child.destroy();this.children=[];
        if(this.parent)this.parent.children=this.parent.children.filter(c=>c!==this);}
}
export class Settings extends Emitter {
    values={'widgets':['clock','battery','actions'],'split-ratio':'half','gesture-enabled':true,'dock-autohide':false,
        'enable-animations':true,'orientation-lock':false};
    get_strv(key){return this.values[key];}get_string(key){return this.values[key];}get_boolean(key){return this.values[key];}
    set_boolean(key,value){this.values[key]=value;this.emit(`changed::${key}`);return true;}
    set_string(key,value){this.values[key]=value;this.emit(`changed::${key}`);return true;}
    is_writable(){return true;}
}
export const timers = new Map(); let timerId=0;
export const pending=[];
export const settings=new Settings();
export const main={
    layoutManager:Object.assign(new Emitter(),{monitors:[{index:0,x:0,y:0,width:800,height:600}],
        keyboardBox:Object.assign(new Actor(),{visible:false}),chrome:[],
        addChrome(actor){this.chrome.push(actor);},removeChrome(actor){this.chrome=this.chrome.filter(a=>a!==actor);},
        getWorkAreaForMonitor(){return {x:0,y:0,width:800,height:600};}}),
    sessionMode:Object.assign(new Emitter(),{currentMode:'user',isLocked:false}),
    uiGroup:{set_child_below_sibling(){},set_child_above_sibling(){}},
    activateWindow(){globalThis.focusChanges++;},notify(){},
};
const system=Object.assign(new Emitter(),{get_installed:()=>[],get_running:()=>[]});
const favorites=Object.assign(new Emitter(),{getFavorites:()=>[]});
globalThis.focusChanges=0;
globalThis.global={display:new Emitter(),stage:new Emitter(),window_group:new Actor(),
    workspace_manager:Object.assign(new Emitter(),{get_active_workspace:()=>({})}),get_window_actors:()=>[]};
globalThis.__native={
    St:{Button:Actor,BoxLayout:Actor,Label:Actor,Entry:Actor,ScrollView:Actor,Icon:Actor},
    Clutter:{Clone:Actor,ActorAlign:{CENTER:0},AnimationMode:{EASE_OUT_QUAD:0},EVENT_PROPAGATE:0,EVENT_STOP:1,
        InputDeviceType:{TOUCHSCREEN_DEVICE:1},EventType:{TOUCH_BEGIN:1,TOUCH_UPDATE:2,TOUCH_END:3,TOUCH_CANCEL:4}},
    Shell:{AppSystem:{get_default:()=>system},AppState:{RUNNING:1}},
    Meta:{WindowType:{NORMAL:0},MaximizeFlags:{BOTH:3}},
    GLib:{get_language_names:()=>['en_US'],PRIORITY_DEFAULT:0,SOURCE_CONTINUE:true,timeout_add_seconds(_p,_s,callback){timers.set(++timerId,callback);return timerId;},
        Source:{remove:id=>timers.delete(id)},DateTime:{new_now_local:()=>({format:()=> 'Sunday 12:00'})},
        Variant:class {constructor(type,values){this.type=type;this.values=values;}}},
    Gio:{Settings,SettingsSchemaSource:{get_default:()=>({lookup:()=>({has_key:()=>true})})},
        Cancellable:class {cancelled=false;cancel(){this.cancelled=true;}is_cancelled(){return this.cancelled;}},
        DBusProxy:{new_for_bus(...args){pending.push(args);}},BusType:{SESSION:0,SYSTEM:1},
        DBusProxyFlags:{NONE:0,DO_NOT_AUTO_START:1},DBusCallFlags:{NONE:0,NO_AUTO_START:1},
        DBus:{session:{call(){}}}},
};
globalThis.__main=main;globalThis.__favorites=favorites;
globalThis.__Extension=class {metadata={'version-name':'0.1.0'};getSettings(){return settings;}};
registerHooks({resolve(specifier,context,next){
    if(specifier.startsWith('gi://'))return {url:`native:${specifier.slice(5)}`,shortCircuit:true};
    if(specifier.startsWith('resource:///'))return {url:`native:resource:${specifier}`,shortCircuit:true};
    return next(specifier,context);
},load(url,context,next){
    if(url.startsWith('native:resource:')){
        let source;
        if(url.endsWith('/main.js'))source='export const {layoutManager,sessionMode,uiGroup,activateWindow,notify}=globalThis.__main;';
        else if(url.endsWith('/appFavorites.js'))source='export const getAppFavorites=()=>globalThis.__favorites;';
        else source='export const Extension=globalThis.__Extension;export const gettext=s=>s;';
        return {format:'module',source,shortCircuit:true};
    }
    if(url.startsWith('native:'))return {format:'module',source:`export default globalThis.__native[${JSON.stringify(url.slice(7))}];`,shortCircuit:true};
    return next(url,context);
}});
