export type Monitor = {index: number; x: number; y: number; width: number; height: number};
export function integratedMonitor(state: any[], monitors: Monitor[]): Monitor | null {
    const physical = state[1] as any[];
    const logical = state[2] as any[];
    const builtIn = physical.filter(m => {
        const value = m[2]?.['is-builtin'];
        return value === true || value?.deep_unpack?.() === true;
    }).map(m => m[0][0]);
    if (builtIn.length !== 1) return null;
    const output = logical.find(m => m[5]?.some((spec: any[]) => spec[0] === builtIn[0]));
    // Mirroring combines internal and external outputs; keep GNOME's desktop.
    if (!output || output[5].length !== 1) return null;
    return monitors.find(m => m.x === output[0] && m.y === output[1]) ?? null;
}
