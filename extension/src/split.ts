export type Rect = {x: number; y: number; width: number; height: number};
export type Ratio = 'half' | 'third' | 'two-thirds';
export type Minimum = {width: number; height: number};
export const ratios: Ratio[] = ['half', 'third', 'two-thirds'];
export function nextRatio(ratio: Ratio): Ratio {
    return ratios[(ratios.indexOf(ratio) + 1) % ratios.length]!;
}
export function splitLayout(area: Rect, ratio: Ratio, first: Minimum, second: Minimum,
    gap = 48): {first: Rect; second: Rect; divider: Rect} | {error: string} {
    if (![area.width, area.height, gap, first.width, first.height, second.width,
        second.height].every(n => Number.isFinite(n) && n >= 0))
        return {error: 'Invalid window constraints'};
    const portrait = area.height > area.width;
    const length = (portrait ? area.height : area.width) - gap;
    const fraction = ratio === 'third' ? 1 / 3 : ratio === 'two-thirds' ? 2 / 3 : 1 / 2;
    const a = Math.floor(length * fraction);
    const b = length - a;
    const fits = portrait
        ? a >= first.height && b >= second.height && area.width >= Math.max(first.width, second.width)
        : a >= first.width && b >= second.width && area.height >= Math.max(first.height, second.height);
    if (!fits) return {error: 'These apps need more space for this split'};
    if (portrait) return {
        first: {...area, height: a},
        second: {...area, y: area.y + a + gap, height: b},
        divider: {...area, y: area.y + a, height: gap},
    };
    return {
        first: {...area, width: a},
        second: {...area, x: area.x + a + gap, width: b},
        divider: {...area, x: area.x + a, width: gap},
    };
}
