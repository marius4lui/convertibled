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
export function overviewLayout(width: number): {columns: number; cardWidth: number; previewHeight: number} {
    const available = Math.max(160,width - 80);
    const columns = Math.min(3,Math.max(1,Math.floor((available + 24) / 340)));
    const cardWidth = Math.min(480,(available - (columns - 1) * 24) / columns);
    return {columns,cardWidth,previewHeight:Math.round(Math.min(270,cardWidth * 0.625))};
}
