from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from radle_incremental_admission import (
    RADIOLOGIST_DECISION_FIELDS,
    audit_finalized_admission,
    audit_idk0_score_lane,
    build_idk0_score_lane,
    commit_finalized_admission,
    finalize_incremental_admission,
    prepare_incremental_admission,
    read_csv_table,
    run_synthetic_dual_judge_delta,
    sha256_file,
)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the no-network pre-M7 production-shape acceptance flow")
    parser.add_argument("--fixture-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--mock-judge", action="store_true", required=True)
    parser.add_argument("--deny-network", action="store_true", required=True)
    args = parser.parse_args()
    fixture = Path(args.fixture_root)
    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"acceptance output must be absent or empty: {out}")

    network_calls = 0

    def denied_network(*_args: object, **_kwargs: object) -> None:
        nonlocal network_calls
        network_calls += 1
        raise AssertionError("network access is forbidden in pre-M7 acceptance")

    with patch("urllib.request.urlopen", denied_network):
        prepared = prepare_incremental_admission(
            parent_wide=fixture / "parent_wide.csv",
            parent_final_long_master=fixture / "parent_final_long_master.csv",
            parent_authority_manifest=fixture / "parent_authority.json",
            blind_map_path=fixture / "blind_label_map.csv",
            incoming_package=fixture / "incoming_package",
            model_key="grok_4_5",
            roster_path=fixture / "roster.json",
            variants_path=fixture / "accepted_variants.csv",
            states_path=REPO_ROOT / "config/radle_v2_terminal_states.json",
            output_root=out / "admissions",
            repo_root=REPO_ROOT,
            dry_run=False,
        )
        staging = Path(str(prepared["staging_root"]))
        judge = run_synthetic_dual_judge_delta(
            staging_root=staging,
            judges_path=REPO_ROOT / "config/radle_v2_judges.json",
            out_dir=staging / "judge_evidence",
            repo_root=REPO_ROOT,
            dry_run=False,
        )
        _, queue = read_csv_table(staging / "radiologist_queue.csv")
        decisions_path = staging / "radiologist_decisions.csv"
        write_csv(decisions_path, RADIOLOGIST_DECISION_FIELDS, [
            {
                "Master_Case_ID": row["Master_Case_ID"],
                "model_blinded": row["model_blinded"],
                "score_binary": "1",
                "reviewer_pseudonym": "pre_m7_mock_radiologist",
                "reviewed_utc": "2026-07-10T08:00:00+00:00",
                "rationale": "mocked pre-M7 acceptance decision",
            }
            for row in queue
        ])
        finalized = finalize_incremental_admission(intake_root=staging, radiologist_decisions=decisions_path)
        committed_root = Path(str(finalized["final_staging_root"]))
        commit = commit_finalized_admission(committed_root)
        committed_audit = audit_finalized_admission(committed_root, require_committed=True)

        pooled_root = out / "idk0_pooled12"
        pooled = build_idk0_score_lane(
            committed_root=committed_root,
            output_root=pooled_root,
            human_presentation="pooled12",
            states_path=REPO_ROOT / "config/radle_v2_terminal_states.json",
        )
        split_root = out / "idk0_split6x6"
        split = build_idk0_score_lane(
            committed_root=committed_root,
            output_root=split_root,
            human_presentation="split6x6",
            states_path=REPO_ROOT / "config/radle_v2_terminal_states.json",
        )

    parent = fixture / "parent_final_long_master.csv"
    final_master = committed_root / "final/radle_v2_final_long_master.csv"
    parent_bytes = parent.read_bytes()
    final_bytes = final_master.read_bytes()
    receipt = {
        "schema_version": "radle_v2_pre_m7_production_shape_acceptance.v1",
        "result": "PASS",
        "network_calls": network_calls,
        "intake_id": prepared["intake_id"],
        "finalization_id": finalized["finalization_id"],
        "parent_byte_prefix": final_bytes.startswith(parent_bytes),
        "appended_records": committed_audit["scored_delta_rows"],
        "output_row_count": committed_audit["output_row_count"],
        "source_counts": finalized["source_counts"],
        "judge_counts": {
            "results": judge["judge_result_rows"],
            "locks": judge["locked_agreement_rows"],
            "radiologist_queue": judge["radiologist_queue_rows"],
        },
        "commit": commit,
        "pooled12_counts": pooled["counts"],
        "split6x6_counts": split["counts"],
        "pooled12_audit": audit_idk0_score_lane(pooled_root),
        "split6x6_audit": audit_idk0_score_lane(split_root),
        "hashes": {
            "parent": sha256_file(parent),
            "final_master": sha256_file(final_master),
            "committed_marker": sha256_file(committed_root / "COMMITTED.json"),
        },
        "committed_root": str(committed_root.resolve()),
    }
    if network_calls or not receipt["parent_byte_prefix"] or receipt["appended_records"] != 200 or receipt["output_row_count"] != 6200:
        raise SystemExit("acceptance invariants failed")
    out.mkdir(parents=True, exist_ok=True)
    receipt_path = out / "acceptance_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print("PRE_M7_ACCEPTANCE_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
