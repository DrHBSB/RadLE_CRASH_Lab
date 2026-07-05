#!/usr/bin/env python3
"""RadLE v2 finalization — Part F: write final_scoring_audit.json.

Records input+output SHA256s, the authoritative score distribution/source mix,
the master role-fix summary, and the radiologist flip audit (how many needs_review
rows were filled and how many suggested_reviews flipped vs the prior lock).

Read-only w.r.t. all data files; only writes final_scoring_audit.json.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:/Users/thehb/Documents/RadLE v2")
STATS = ROOT / "outputs/radle_v2_stats"
OUT = STATS / "final_scoring_radiologist_20260706_001147"
MASTER = OUT / "radle_v2_final_long_master.csv"
WORKBOOK = STATS / "radle_v2_dual_judge_scored_combined_with_codex_v2.xlsx"
RADIOLOGIST = Path(r"C:/Users/thehb/Downloads/Radiologist Review.xlsx")
PRE_FIX = Path(
    r"C:/Users/thehb/AppData/Local/Temp/claude/"
    r"C--Users-thehb-Documents-RadLE-v2/5ad141d4-072f-4c1e-8a58-f0f572281fa9/scratchpad"
    r"/radle_v2_final_long_master.step1_pre.csv"
)

SUMMARY_FILES = [
    "model_summary.csv",
    "provider_summary.csv",
    "access_summary.csv",
    "domain_summary.csv",
    "human_role_summary.csv",
    "seniority_summary.csv",
    "appendix_within_provider_deltas.csv",
    "SUMMARY_SPEC.md",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    m = pd.read_csv(MASTER)
    assert len(m) == 6000 and int((m.final_score_authoritative == 1).sum()) == 1255

    # --- radiologist flip audit (score is identity-independent of the role fix) ---
    sc = pd.read_excel(WORKBOOK, sheet_name="scored")[
        ["Master_Case_ID", "model_blinded", "review_status", "final_resolved"]
    ]
    mm = m.merge(sc, on=["Master_Case_ID", "model_blinded"], how="left", validate="1:1")
    rad = mm[mm.final_score_source == "radiologist"]
    nr = rad[rad.review_status == "NEEDS_REVIEW"]
    sg = rad[rad.review_status != "NEEDS_REVIEW"]
    flipped = sg[sg.final_score_authoritative != sg.final_resolved]

    hum = m[m.domain == "human"]
    audit = {
        "generated": ts,
        "generator": "scripts/write_audit.py",
        "authoritative_score_column": "final_score_authoritative",
        "row_count": int(len(m)),
        "duplicate_keys": int(m.duplicated(["Master_Case_ID", "model_blinded"]).sum()),
        "final_score_distribution": {
            str(k): int(v) for k, v in m.final_score_authoritative.value_counts().sort_index().items()
        },
        "final_score_source_mix": {
            k: int(v) for k, v in m.final_score_source.value_counts().items()
        },
        "weighted_score_blanks": int(pd.to_numeric(m.weighted_score, errors="coerce").isna().sum()),
        "radiologist_flip_audit": {
            "radiologist_rows": int(len(rad)),
            "needs_review_filled": int(len(nr)),
            "needs_review_all_prior_nan": bool(nr.final_resolved.isna().all()),
            "suggested_rows": int(len(sg)),
            "suggested_flipped": int(len(flipped)),
            "suggested_unchanged": int(len(sg) - len(flipped)),
            "flip_0_to_1": int(((sg.final_resolved == 0) & (sg.final_score_authoritative == 1)).sum()),
            "flip_1_to_0": int(((sg.final_resolved == 1) & (sg.final_score_authoritative == 0)).sum()),
        },
        "master_role_fix": {
            "candidate_changes": {
                "Nishtha Mahajan": "Radiologist -> Trainee",
                "Devyani Singh": "Radiologist -> Trainee",
            },
            "role_people_counts": {
                r: int(hum[hum.candidate == r].provider.nunique()) for r in ("Radiologist", "Trainee")
            },
            "seniority_columns_added": ["rater_seniority", "rater_seniority_rank"],
        },
        "input_sha256": {
            "workbook_scored_with_codex_v2": sha256(WORKBOOK),
            "radiologist_review_xlsx": sha256(RADIOLOGIST) if RADIOLOGIST.exists() else None,
            "master_pre_role_fix": sha256(PRE_FIX) if PRE_FIX.exists() else None,
        },
        "output_sha256": {
            "radle_v2_final_long_master.csv": sha256(MASTER),
            **{f: sha256(OUT / f) for f in SUMMARY_FILES},
        },
    }
    (OUT / "final_scoring_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    fa = audit["radiologist_flip_audit"]
    print("wrote final_scoring_audit.json")
    print("  final_score_distribution:", audit["final_score_distribution"])
    print("  source_mix:", audit["final_score_source_mix"])
    print("  flip audit:", json.dumps(fa))
    print("  role people:", audit["master_role_fix"]["role_people_counts"])
    print("  radiologist input sha present:", audit["input_sha256"]["radiologist_review_xlsx"] is not None)
    print("  output files hashed:", 1 + len(SUMMARY_FILES))


if __name__ == "__main__":
    main()
