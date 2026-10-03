export type Navigation = 'dock' | 'home' | 'overview';
export type TouchSample = {x: number; y: number; time: number};
export class EdgeGesture {
    private start: TouchSample | null = null;
    begin(sample: TouchSample, area: {x: number; y: number; width: number; height: number}): boolean {
        const inScreen = sample.x >= area.x && sample.x < area.x + area.width;
        this.start = inScreen && sample.y >= area.y + area.height - 24 &&
            sample.y <= area.y + area.height ? sample : null;
        return this.start !== null;
    }
    end(sample: TouchSample): Navigation | null {
        const start = this.start; this.start = null;
        if (!start) return null;
        const distance = start.y - sample.y;
        if (distance < 36 || Math.abs(sample.x - start.x) > 100) return null;
        if (sample.time - start.time >= 500) return 'overview';
        return distance >= 130 ? 'home' : 'dock';
    }
    cancel(): void { this.start = null; }
}
