import {registerHooks} from 'node:module';
registerHooks({
    resolve(specifier, context, next) {
        if (specifier === 'gi://Meta') return {url:'mock:Meta',shortCircuit:true};
        return next(specifier,context);
    },
    load(url, context, next) {
        if (url === 'mock:Meta') return {format:'module',source:'export default {WindowType:{NORMAL:0,DIALOG:1},MaximizeFlags:{BOTH:3}};',shortCircuit:true};
        return next(url,context);
    },
});
