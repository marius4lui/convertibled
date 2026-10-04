export type Status = {schema_version: number; profile: string;
    active?: boolean; locked?: boolean;
    desired: {tablet_workspace: boolean; rotation_lock: boolean; rotation_lock_requested?: boolean;
        rotation?: 'enabled' | 'disabled' | 'unchanged'; osk?: 'enabled' | 'disabled' | 'unchanged'};
    applied?: {tablet_workspace: boolean; rotation_lock: boolean; status: string; error: string | null}};
export function parseStatus(json: string): Status {
    if (json.length > 65536) throw new Error('Status exceeds limit');
    const status = JSON.parse(json) as Status;
    if (status.schema_version !== 1 || !['laptop','tablet','stand','tent'].includes(status.profile) ||
        typeof status.desired?.tablet_workspace !== 'boolean' ||
        typeof status.desired?.rotation_lock !== 'boolean') throw new Error('Unsupported session status');
    if (status.desired.rotation_lock_requested !== undefined && typeof status.desired.rotation_lock_requested !== 'boolean')
        throw new Error('Invalid rotation lock request');
    for (const action of [status.desired.rotation,status.desired.osk]) {
        if (action !== undefined && !['enabled','disabled','unchanged'].includes(action))
            throw new Error('Invalid native action request');
    }
    return status;
}
