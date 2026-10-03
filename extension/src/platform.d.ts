// GI and Shell APIs are runtime-provided. Pure policy modules remain strictly typed.
declare module 'gi://*' { const api: any; export default api; }
declare module 'resource:///*' { export const Extension: any; export const gettext: (s: string) => string; }
declare const global: any;
