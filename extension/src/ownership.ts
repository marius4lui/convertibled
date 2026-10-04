export class OwnedState<K, T> {
    private records = new Map<K, {original: T; applied: T}>();
    constructor(private equal: (a: T, b: T) => boolean) {}
    remember(key: K, original: T, applied: T): void {
        const old = this.records.get(key);
        this.records.set(key, {original: old?.original ?? original, applied});
    }
    restore(key: K, current: T): T | undefined {
        const record = this.records.get(key);
        this.records.delete(key);
        return record && this.equal(record.applied, current) ? record.original : undefined;
    }
    forget(key: K): void { this.records.delete(key); }
    matches(key: K,current: T): boolean {
        const record = this.records.get(key); return Boolean(record && this.equal(record.applied,current));
    }
    keys(): K[] { return [...this.records.keys()]; }
}
export class Cleanup {
    private callbacks: (() => void)[] = [];
    add(callback: () => void): void { this.callbacks.push(callback); }
    signal(object: any, name: string, callback: (...args: any[]) => unknown): number {
        const id = object.connect(name, callback);
        this.add(() => object.disconnect(id));
        return id;
    }
    clear(): void {
        const errors: unknown[] = [];
        for (const callback of this.callbacks.splice(0).reverse()) {
            try { callback(); } catch (error) { errors.push(error); }
        }
        if (errors.length) console.error(`convertibled cleanup: ${errors.length} resource errors`);
    }
}
