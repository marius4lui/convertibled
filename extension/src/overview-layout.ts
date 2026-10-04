export interface PreviewFit {width: number; height: number; x: number; y: number}
/** Fit the source texture into its allocated viewport without distorting it. */
export function fitWindowPreview(sourceWidth: number, sourceHeight: number,
    viewportWidth: number, viewportHeight: number): PreviewFit {
    if (![sourceWidth,sourceHeight,viewportWidth,viewportHeight].every(value => Number.isFinite(value) && value > 0))
        return {width:0,height:0,x:0,y:0};
    const scale = Math.min(viewportWidth / sourceWidth,viewportHeight / sourceHeight);
    const width = sourceWidth * scale, height = sourceHeight * scale;
    return {width,height,x:(viewportWidth - width) / 2,y:(viewportHeight - height) / 2};
}
export function overviewLayout(width: number,count = 3,scale = 1,allocatedWidth?: number):
    {columns: number; cardWidth: number; previewHeight: number; available: number; stackedToolbar: boolean; compact: boolean} {
    const compact = width < 600;
    const fallback = Math.max(1,width - (compact ? 32 : 80));
    const available = Math.max(1,Math.min(fallback,allocatedWidth && allocatedWidth > 0 ? allocatedWidth : fallback));
    const gap = 24, minimumCard = 300 * Math.max(1,scale);
    const columns = Math.min(3,Math.max(1,count),Math.max(1,Math.floor((available + gap) / (minimumCard + gap))));
    const cardWidth = Math.min(640,(available - (columns - 1) * gap) / columns);
    return {columns,cardWidth,previewHeight:Math.round(Math.min(340,(cardWidth - 34) * 0.72)),available,
        stackedToolbar:available < 540 * Math.max(1,scale),compact};
}
