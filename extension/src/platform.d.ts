// GI and Shell APIs are runtime-provided. Pure policy modules remain strictly typed.
declare module 'gi://*' { const api: any; export default api; }
declare module 'resource:///*' {
    export const Extension: any; export const gettext: (s: string) => string;
    export const layoutManager: any; export const sessionMode: any; export const overview: any;
    export const wm: any; export const keyboard: any; export const uiGroup: any;
    export const getAppFavorites: any; export const activateWindow: any;
    export const notify: any; export const panel: any;
}
declare const global: any;
