#!/usr/bin/env python3
"""RadLE v2 Part B — model_summary.csv (all 30 arms).

Reads the master (read-only), groups by ['candidate','provider','access','domain'],
and writes model_summary.csv using the locked metrics() core. Does not redefine
any metric and does not modify the master.
"""
import sys
from pathlib import Path

import pandas as pd

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from radle_metrics import metrics  # noqa: E402

OUT_DIR = (
    SCRIPTS_DIR.parent
    / "outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147"
)
MASTER = OUT_DIR / "radle_v2_final_long_master.csv"
OUT_CSV = OUT_DIR / "model_summary.csv"

SRC_COLS = {
    "radiologist": "src_radiologist",
    "ai_judges": "src_ai_judges",
    "human_prior": "src_human_prior",
    "auto_score_not_required": "src_auto_score_not_required",
}


def build_row(candidate, provider, access, domain, g):
    row = {
        "candidate": candidate,
        "provider": provider,
        "access": access,
        "domain": domain,
        "is_excluded": bool(access == "excluded"),
    }
    row.update(metrics(g))

    src_counts = g["final_score_source"].value_counts()
    for src_key, col_name in SRC_COLS.items():
        row[col_name] = int(src_counts.get(src_key, 0))

    return row


def main():
    m = pd.read_csv(MASTER)

    rows = []
    for (candidate, provider, access, domain), g in m.groupby(
        ["candidate", "provider", "access", "domain"], dropna=False
    ):
        rows.append(build_row(candidate, provider, access, domain, g))

    out = pd.DataFrame(rows)
    out = out.sort_values(
        by=["is_excluded", "accuracy"], ascending=[True, False]
    ).reset_index(drop=True)

    # -------------------- asserts (tripwires) --------------------
    assert len(out) == 30, f"expected 30 rows, got {len(out)}"

    sum_n = int(out["n"].sum())
    assert sum_n == 6000, f"expected sum(n)==6000, got {sum_n}"

    sum_correct = int(out["n_correct"].sum())
    assert sum_correct == 1255, f"expected sum(n_correct)==1255, got {sum_correct}"

    excl_count = int(out["is_excluded"].sum())
    assert excl_count == 3, f"expected is_excluded.sum()==3, got {excl_count}"

    src_cols = list(SRC_COLS.values())
    src_sum = out[src_cols].sum(axis=1)
    mismatches = out.loc[src_sum != out["n"], ["candidate", "provider", "n"]]
    assert mismatches.empty, f"src_* sum mismatch for rows:\n{mismatches}"

    out.to_csv(OUT_CSV, index=False)

    print(f"Wrote {OUT_CSV} ({len(out)} rows)")
    print(f"Sum n = {sum_n}")
    print(f"Sum n_correct = {sum_correct}")
    print(f"is_excluded count = {excl_count}")
    print("All asserts PASSED")
    print()
    with pd.option_context(
        "display.max_rows", None, "display.max_columns", None, "display.width", 220
    ):
        print(out)


if __name__ == "__main__":
    main()
