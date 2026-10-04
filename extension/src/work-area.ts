import type {Rect} from './split.js';
export function beforeDock(area: Rect,dock: Rect,visible: boolean,monitor: Rect): Rect {
    const ownsBottom = visible && dock.x <= monitor.x && dock.x + dock.width >= monitor.x + monitor.width &&
        Math.abs(dock.y + dock.height - (monitor.y + monitor.height)) <= 1 &&
        Math.abs(area.y + area.height - dock.y) <= 1;
    // GI boxed rectangle fields are prototype accessors, not enumerable keys.
    return {x:area.x,y:area.y,width:area.width,
        height:ownsBottom ? Math.min(monitor.y + monitor.height - area.y,area.height + dock.height) : area.height};
}
