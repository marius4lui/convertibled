export type Status = {schema_version: number; profile: string;
    desired: {tablet_workspace: boolean; rotation_lock: boolean; rotation_lock_requested?: boolean};
    applied?: {tablet_workspace: boolean; rotation_lock: boolean; status: string; error: string | null}};
export function parseStatus(json: string): Status {
    if (json.length > 65536) throw new Error('Status exceeds limit');
    const status = JSON.parse(json) as Status;
    if (status.schema_version !== 1 || !['laptop','tablet','stand','tent'].includes(status.profile) ||
        typeof status.desired?.tablet_workspace !== 'boolean' ||
        typeof status.desired?.rotation_lock !== 'boolean') throw new Error('Unsupported session status');
    return status;
}
