"""One-time legacy lock retirement after externally verified runtime shutdown.

This is deliberately not automatic stale-PID detection. The caller must supply
the recorded shutdown authorization for this exact run, in a committed release.
"""
import hashlib
import json
import os
from pathlib import Path

RUN = "openrouter_16_32k_20261008"
AUTHORIZATION = "20261010-user-approved-colab-sessions-terminated-v1"


def retire_legacy_locks(output_csv, *, run_label, authorization):
    output_csv = Path(output_csv)
    if run_label != RUN or authorization != AUTHORIZATION or output_csv.parent.parent.name != RUN:
        raise RuntimeError("Lock recovery authorization does not match this run")
    folder = Path(str(output_csv) + ".concurrent")
    receipt = folder / "legacy_lock_retirement_v1.json"
    locks = [folder / "writer.lock", folder / "queue" / "writer.lock"]
    if receipt.exists():
        if any(lock.exists() for lock in locks):
            raise RuntimeError("One-time lock recovery consumed; new lock requires owner review")
        return json.loads(receipt.read_text())
    snapshots = []
    for lock in locks:
        if not lock.exists():
            continue
        data = lock.read_bytes()
        # Legacy files contain only a decimal PID. Modern/unknown locks stay held.
        if not data or not data.isdigit() or len(data) > 20:
            raise RuntimeError("Unknown lock format; preserve for owner review")
        snapshots.append((lock, data))
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    for lock, data in snapshots:
        digest = hashlib.sha256(data).hexdigest()
        archive = lock.with_name("writer.retired." + digest + ".lock")
        if archive.exists():
            if archive.read_bytes() != data:
                raise RuntimeError("Retired lock archive mismatch")
        else:
            with archive.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        records.append({"path": str(lock), "sha256": digest, "archive": str(archive)})
    for lock, data in snapshots:
        if lock.read_bytes() != data:
            raise RuntimeError("Lock changed during retirement; stop")
    result = {"authorization": authorization, "run_label": run_label,
              "basis": "User approved shutdown; Colab Manage sessions verified no active sessions before release publication",
              "locks": records}
    # Consume permission BEFORE unlink: an interrupted retirement needs review,
    # rather than treating a subsequently created live lock as another stale one.
    with receipt.open("x") as handle:
        json.dump(result, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    for lock, data in snapshots:
        if lock.read_bytes() != data:
            raise RuntimeError("Lock changed after receipt; stop")
        lock.unlink()
    print("LOCK RECOVERY: archived", len(records), "legacy locks; one-time authorization consumed")
    return result
