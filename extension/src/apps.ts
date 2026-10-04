export type AppInfo = {id: string; name: string; description: string; keywords: string[]};
const normalize = (text: string) => text.normalize('NFKD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase();
export function searchApps(apps: AppInfo[], query: string): AppInfo[] {
    const words = normalize(query).trim().split(/\s+/).filter(Boolean);
    return apps.filter(app => words.every(word => normalize(
        [app.name, app.description, ...app.keywords].join(' ')).includes(word)))
        .sort((a, b) => a.name.localeCompare(b.name));
}
export function dockApps(favorites: string[], running: string[]): string[] {
    return [...new Set([...favorites, ...running])];
}
export function gridColumns(width: number, target = 104): number {
    return Math.max(1, Math.min(10, Math.floor((width - 32) / target)));
}
