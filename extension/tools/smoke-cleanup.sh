#!/usr/bin/env bash
# Sourced only by the disposable compositor harness and its regression tests.
cleanup_smoke_root() {
    local root=$1 original_status=$2 attempt
    # Restrict deletion to the canonical mktemp root created by this harness.
    if [[ "$root" != /* || ! "${root##*/}" =~ ^convertibled-shell-smoke\.[[:alnum:]]{8}$ ]]; then
        printf '%s\n' 'Refusing unexpected compositor smoke cleanup path' >&2
        if (( original_status != 0 )); then return "$original_status"; fi
        return 1
    fi
    # Bus shutdown can leave short-lived helpers writing their final cache files.
    # Repeated deletion is bounded, and persistent errors still fail the smoke.
    for ((attempt=1; attempt<=20; attempt++)); do
        if rm -rf -- "$root"; then return "$original_status"; fi
        if (( attempt < 20 )); then sleep 0.25; fi
    done
    printf '%s\n' "Failed to clean compositor smoke root: $root" >&2
    if (( original_status != 0 )); then return "$original_status"; fi
    return 1
}
