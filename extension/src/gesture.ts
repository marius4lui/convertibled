export type Navigation = 'dock' | 'home' | 'overview';
export type TouchSample = {x: number; y: number; time: number};
export class EdgeGesture {
    private start: TouchSample | null = null;
    private latest: TouchSample | null = null;
    private held = false;
    begin(sample: TouchSample, area: {x: number; y: number; width: number; height: number}): boolean {
        this.latest = null; this.held = false;
        const inScreen = sample.x >= area.x && sample.x < area.x + area.width;
        this.start = inScreen && sample.y >= area.y + area.height - 24 &&
            sample.y <= area.y + area.height ? sample : null;
        return this.start !== null;
    }
    update(sample: TouchSample): Navigation | null {
        const start = this.start;
        if (!start) return null;
        this.latest = sample;
        const distance = start.y - sample.y;
        if (Math.abs(sample.x - start.x) > 100) { this.cancel(); return null; }
        if (distance < 36) return null;
        return distance >= 130 ? 'home' : 'dock';
    }
    hold(): Navigation | null {
        if (!this.latest || !this.update(this.latest)) return null;
        this.held = true; return 'overview';
    }
    end(sample: TouchSample): Navigation | null {
        const result = this.held ? null : this.update(sample); this.cancel(); return result;
    }
    cancel(): void { this.start = null; this.latest = null; this.held = false; }
}
