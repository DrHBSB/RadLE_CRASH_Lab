from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from radle_incremental_admission import (  # noqa: E402
    FINAL_LONG_MASTER_FIELDS,
    KEY_COLUMNS,
    audit_finalized_admission,
    audit_judge_evidence,
    audit_prepared_staging,
    canonical_json_sha256,
    canonical_text_bytes,
    canonical_text_sha256,
    compute_intake_id,
    content_only_json_sha256,
    detect_line_terminator,
    model_result_columns,
    read_csv_table,
    read_json,
    serialize_csv_table,
    sha256_bytes,
    sha256_file,
    write_json,
    write_csv_table,
)


def _index_by_case(rows: list[dict[str, str]], label: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        case_id = row.get("Master_Case_ID", "")
        if not case_id:
            raise ValueError(f"{label} row missing Master_Case_ID")
        if case_id in out:
            raise ValueError(f"{label} duplicate Master_Case_ID: {case_id}")
        out[case_id] = row
    return out


def _build_combined_wide(
    *,
    parent_wide: Path,
    one_model_wide: Path,
    model_key: str,
    out_path: Path,
) -> None:
    parent_fields, parent_rows = read_csv_table(parent_wide)
    one_fields, one_rows = read_csv_table(one_model_wide)
    for field in KEY_COLUMNS:
        if field not in parent_fields or field not in one_fields:
            raise ValueError(f"missing key field {field} in parent or one-model wide")
    model_columns = model_result_columns(model_key)
    for field in model_columns:
        if field not in one_fields:
            raise ValueError(f"one-model wide missing {field}")
    parent_by_case = _index_by_case(parent_rows, "parent wide")
    one_by_case = _index_by_case(one_rows, "one-model wide")
    if set(parent_by_case) != set(one_by_case):
        raise ValueError("parent wide and one-model wide case sets differ")
    combined_fields = parent_fields + [field for field in model_columns if field not in parent_fields]
    combined_rows: list[dict[str, str]] = []
    for case_id in sorted(parent_by_case, key=lambda value: int(value) if value.isdigit() else value):
        parent_row = parent_by_case[case_id]
        one_row = one_by_case[case_id]
        for field in KEY_COLUMNS:
            if str(parent_row.get(field, "")) != str(one_row.get(field, "")):
                raise ValueError(f"case metadata mismatch for case {case_id} field {field}")
        combined = dict(parent_row)
        for field in model_columns:
            combined[field] = one_row.get(field, "")
        combined_rows.append(combined)
    write_csv_table(out_path, combined_fields, combined_rows)


def build_carry_forward_root(
    *,
    source_final_root: Path,
    parent_committed_root: Path,
    output_root: Path,
    carry_forward_note: str,
) -> dict[str, Any]:
    source_audit = audit_finalized_admission(source_final_root)
    source_manifest = read_json(source_final_root / "append_manifest.json")
    snapshot_root = source_final_root / "intake_snapshot"
    snapshot_manifest = read_json(snapshot_root / "append_input_manifest.json")
    model_key = str(snapshot_manifest.get("model_key", "")).strip()
    if not model_key:
        raise ValueError("source intake snapshot is missing model_key")

    parent_committed = read_json(parent_committed_root / "COMMITTED.json")
    parent_manifest = read_json(parent_committed_root / "append_manifest.json")
    parent_chain_id = str(parent_committed.get("finalization_id", "")).strip()
    if not parent_chain_id:
        raise ValueError("parent COMMITTED.json missing finalization_id")
    parent_master = parent_committed_root / str(parent_manifest["outputs"]["final_long_master"])
    parent_wide = parent_committed_root / str(parent_manifest["outputs"]["combined_wide"])
    parent_fields, parent_rows = read_csv_table(parent_master)
    if parent_fields != FINAL_LONG_MASTER_FIELDS:
        raise ValueError("committed parent final master schema mismatch")

    scored_delta = source_final_root / "scored_append_delta.csv"
    scored_fields, scored_rows = read_csv_table(scored_delta)
    if scored_fields != FINAL_LONG_MASTER_FIELDS:
        raise ValueError("source scored delta schema mismatch")
    if len(scored_rows) != int(source_manifest.get("case_count", -1)):
        raise ValueError("source scored delta count mismatch")

    finalizer_code_sha = canonical_text_sha256(Path(__file__))
    decisions_path = source_final_root / "radiologist_decisions.csv"
    paid_auth = snapshot_root / "judge_evidence" / "paid_judge_authorization.json"
    judge_index = read_json(snapshot_root / "judge_evidence" / "judge_evidence_index.json")
    authorization_identity: object = judge_index.get("authorization", "MISSING")
    if paid_auth.is_file():
        authorization_identity = {
            "sha256": sha256_file(paid_auth),
            "content_sha256": content_only_json_sha256(paid_auth),
        }

    evidence_hashes = {
        "adjudication_state": sha256_file(snapshot_root / "adjudication_state.csv"),
        "judge_worklist": sha256_file(snapshot_root / "judge_worklist.csv"),
        "judge_config": canonical_json_sha256(snapshot_root / "judge_evidence" / "judge_config.json"),
        "judge_prompt": canonical_text_sha256(snapshot_root / "judge_evidence" / "judge_prompt.txt"),
        "judge_results": sha256_file(snapshot_root / "judge_evidence" / "judge_results.jsonl"),
        "judge_index": sha256_file(snapshot_root / "judge_evidence" / "judge_evidence_index.json"),
        "agreement_locks": sha256_file(snapshot_root / "judge_evidence" / "agreement_locks.csv"),
        "radiologist_queue": sha256_file(snapshot_root / "radiologist_queue.csv"),
        "radiologist_decisions": sha256_file(decisions_path),
        "scored_append_delta": sha256_file(scored_delta),
        "roster": canonical_json_sha256(source_final_root / "roster" / "model_roster.json"),
        "blind_map": sha256_file(source_final_root / "roster" / "blind_label_map.csv"),
        "finalizer_code": finalizer_code_sha,
    }
    finalization_payload = {
        "schema_version": "radle_v2_finalization_identity.v2",
        "intake_id": source_manifest.get("intake_id"),
        "parent_chain_id": parent_chain_id,
        "parent_master_sha256": sha256_file(parent_master),
        "evidence_hashes": evidence_hashes,
        "authorization": authorization_identity,
        "source_counts": source_manifest.get("source_counts"),
    }
    finalization_id = compute_intake_id(finalization_payload)
    final_root = output_root / model_key / "finalized" / finalization_id
    if final_root.exists():
        audit = audit_finalized_admission(final_root, require_committed=(final_root / "COMMITTED.json").exists())
        return {
            "already_exists": True,
            "finalization_id": finalization_id,
            "final_root": str(final_root.resolve()),
            "audit": audit,
        }

    final_root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(scored_delta, final_root / "scored_append_delta.csv")
    shutil.copyfile(decisions_path, final_root / "radiologist_decisions.csv")
    shutil.copytree(snapshot_root, final_root / "intake_snapshot")

    finalizer_source = final_root / "provenance" / "finalizer_source.py"
    finalizer_source.parent.mkdir(parents=True, exist_ok=True)
    finalizer_source.write_bytes(canonical_text_bytes(Path(__file__)))

    roster_out = final_root / "roster"
    roster_out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_final_root / "roster" / "model_roster.json", roster_out / "model_roster.json")
    shutil.copyfile(source_final_root / "roster" / "blind_label_map.csv", roster_out / "blind_label_map.csv")

    parent_out = final_root / "parent" / "parent_final_long_master.csv"
    parent_out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(parent_master, parent_out)

    combined_out = final_root / "combined_wide" / "RadLE_v2_results_final.csv"
    _build_combined_wide(
        parent_wide=parent_wide,
        one_model_wide=snapshot_root / "one_model_final_wide.csv",
        model_key=model_key,
        out_path=combined_out,
    )

    parent_bytes = parent_master.read_bytes()
    line_terminator = detect_line_terminator(parent_bytes)
    delta_bytes = serialize_csv_table(
        FINAL_LONG_MASTER_FIELDS,
        scored_rows,
        lineterminator=line_terminator,
        include_header=False,
    )
    final_master = final_root / "final" / "radle_v2_final_long_master.csv"
    final_master.parent.mkdir(parents=True, exist_ok=True)
    needs_break = parent_bytes and not parent_bytes.endswith((b"\n", b"\r"))
    final_master.write_bytes(parent_bytes + (line_terminator.encode("utf-8") if needs_break else b"") + delta_bytes)

    parent_semantic_hash = sha256_bytes(json.dumps(parent_rows, sort_keys=True).encode("utf-8"))
    append_manifest = {
        "schema_version": "radle_v2_append_manifest.v2",
        "intake_id": source_manifest.get("intake_id"),
        "finalization_id": finalization_id,
        "transaction_state": "PRECOMMIT_VALIDATED",
        "case_count": len(scored_rows),
        "parent_row_count": len(parent_rows),
        "output_row_count": len(parent_rows) + len(scored_rows),
        "parent_chain_id": parent_chain_id,
        "parent_master_path": "parent/parent_final_long_master.csv",
        "parent_master_sha256": sha256_file(parent_master),
        "parent_semantic_sha256": parent_semantic_hash,
        "scored_append_delta_sha256": sha256_file(final_root / "scored_append_delta.csv"),
        "output_master_sha256": sha256_file(final_master),
        "judge_evidence_index_sha256": sha256_file(snapshot_root / "judge_evidence" / "judge_evidence_index.json"),
        "radiologist_decisions_sha256": sha256_file(final_root / "radiologist_decisions.csv"),
        "roster_sha256": sha256_file(roster_out / "model_roster.json"),
        "source_counts": source_manifest.get("source_counts"),
        "finalization_identity": finalization_payload,
        "line_terminator": "\\r\\n" if line_terminator == "\r\n" else "\\n",
        "checksum_exclusions": ["SHA256SUMS", "COMMITTED.json"],
        "outputs": {
            "scored_append_delta": "scored_append_delta.csv",
            "final_long_master": "final/radle_v2_final_long_master.csv",
            "combined_wide": "combined_wide/RadLE_v2_results_final.csv",
            "blind_label_map": "roster/blind_label_map.csv",
            "model_roster": "roster/model_roster.json",
            "intake_snapshot": "intake_snapshot",
        },
        "output_hashes": {
            "scored_append_delta": sha256_file(final_root / "scored_append_delta.csv"),
            "final_long_master": sha256_file(final_master),
            "combined_wide": sha256_file(combined_out),
            "blind_label_map": sha256_file(roster_out / "blind_label_map.csv"),
            "model_roster": sha256_file(roster_out / "model_roster.json"),
            "parent_final_long_master": sha256_file(parent_out),
            "finalizer_source": sha256_file(finalizer_source),
        },
        "prepared_audit": audit_prepared_staging(snapshot_root),
        "judge_audit": audit_judge_evidence(snapshot_root),
        "evidence_carry_forward": {
            "schema_version": "radle_v2_evidence_carry_forward.v1",
            "source_final_root": str(source_final_root.resolve()),
            "source_finalization_id": source_manifest.get("finalization_id"),
            "source_parent_chain_id": source_manifest.get("parent_chain_id"),
            "carried_forward_to_parent_chain_id": parent_chain_id,
            "parent_committed_root": str(parent_committed_root.resolve()),
            "note": carry_forward_note,
        },
    }
    write_json(final_root / "append_manifest.json", append_manifest)
    audit = audit_finalized_admission(final_root)
    return {
        "already_exists": False,
        "source_audit": source_audit,
        "finalization_id": finalization_id,
        "final_root": str(final_root.resolve()),
        "audit": audit,
        "output_row_count": append_manifest["output_row_count"],
        "output_master_sha256": append_manifest["output_master_sha256"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Carry forward audited Muse evidence onto a committed GPT parent.")
    parser.add_argument("--source-final-root", required=True)
    parser.add_argument("--parent-committed-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--carry-forward-note", required=True)
    args = parser.parse_args(argv)
    receipt = build_carry_forward_root(
        source_final_root=Path(args.source_final_root),
        parent_committed_root=Path(args.parent_committed_root),
        output_root=Path(args.output_root),
        carry_forward_note=args.carry_forward_note,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print(f"CARRY_FORWARD_ROOT={receipt['final_root']}")
    print("CARRY_FORWARD_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
