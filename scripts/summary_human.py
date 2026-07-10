#!/usr/bin/env python3
"""RadLE v2 Part D — human role + seniority rollups.

Produces:
  human_role_summary.csv
  seniority_summary.csv

Reads the master read-only; writes only the two CSVs above into the same
output folder. Uses the LOCKED metrics() core from scripts/radle_metrics.py —
no metric is redefined here.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from radle_metrics import metrics  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147"
MASTER = OUT_DIR / "radle_v2_final_long_master.csv"

METRIC_COLS = [
    "n", "n_correct", "accuracy", "acc_ci_lo", "acc_ci_hi",
    "n_attempted", "attempted_accuracy", "att_ci_lo", "att_ci_hi",
    "n_abstained", "n_technical_failure", "mean_weighted_score", "n_weighted",
]


def main():
    m = pd.read_csv(MASTER)
    hum = m[m.domain == "human"].copy()
    assert len(hum) == 2400, f"expected 2400 human rows, got {len(hum)}"
    assert hum["provider"].nunique() == 12, f"expected 12 people, got {hum['provider'].nunique()}"

    # ---------------------------------------------------------------- #
    # human_role_summary.csv
    # ---------------------------------------------------------------- #
    role_rows = []
    for role in ["Radiologist", "Trainee"]:
        g = hum[hum.candidate == role]
        row = {"group": role, "n_raters": int(g["provider"].nunique())}
        row.update(metrics(g))
        role_rows.append(row)

    all_human_row = {"group": "All-Human", "n_raters": int(hum["provider"].nunique())}
    all_human_row.update(metrics(hum))
    role_rows.append(all_human_row)

    role_df = pd.DataFrame(role_rows, columns=["group", "n_raters"] + METRIC_COLS)

    # ---------------------------------------------------------------- #
    # seniority_summary.csv
    # ---------------------------------------------------------------- #
    sen_rows = []
    for rank, g in hum.groupby("rater_seniority_rank", dropna=False):
        rank_int = int(rank)
        tier = g["rater_seniority"].iloc[0]
        role = "Radiologist" if rank_int >= 3 else "Trainee"
        row = {
            "rater_seniority_rank": rank_int,
            "tier": tier,
            "role": role,
            "n_raters": int(g["provider"].nunique()),
        }
        row.update(metrics(g))
        sen_rows.append(row)

    sen_df = pd.DataFrame(
        sen_rows,
        columns=["rater_seniority_rank", "tier", "role", "n_raters"] + METRIC_COLS,
    ).sort_values("rater_seniority_rank").reset_index(drop=True)

    # ---------------------------------------------------------------- #
    # Asserts
    # ---------------------------------------------------------------- #
    rad = role_df[role_df.group == "Radiologist"].iloc[0]
    tra = role_df[role_df.group == "Trainee"].iloc[0]
    allh = role_df[role_df.group == "All-Human"].iloc[0]

    assert rad["n"] == 1200 and rad["n_raters"] == 6, f"Radiologist mismatch: {rad.to_dict()}"
    assert tra["n"] == 1200 and tra["n_raters"] == 6, f"Trainee mismatch: {tra.to_dict()}"
    assert allh["n"] == 2400 and allh["n_raters"] == 12, f"All-Human mismatch: {allh.to_dict()}"

    assert rad["n_correct"] + tra["n_correct"] == allh["n_correct"] == 924, (
        f"n_correct mismatch: rad={rad['n_correct']} tra={tra['n_correct']} "
        f"sum={rad['n_correct'] + tra['n_correct']} all_human={allh['n_correct']}"
    )

    assert len(sen_df) == 7, f"expected 7 seniority rows, got {len(sen_df)}"
    assert sen_df["n"].sum() == 2400, f"seniority n sum mismatch: {sen_df['n'].sum()}"
    assert sen_df["n_correct"].sum() == 924, f"seniority n_correct sum mismatch: {sen_df['n_correct'].sum()}"

    # ---------------------------------------------------------------- #
    # Write outputs
    # ---------------------------------------------------------------- #
    role_out = OUT_DIR / "human_role_summary.csv"
    sen_out = OUT_DIR / "seniority_summary.csv"
    role_df.to_csv(role_out, index=False)
    sen_df.to_csv(sen_out, index=False)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    print("=== human_role_summary.csv ===")
    print(role_df.to_string(index=False))
    print()
    print("=== seniority_summary.csv ===")
    print(sen_df.to_string(index=False))
    print()
    print("ALL ASSERTS PASSED")
    print(f"Wrote: {role_out}")
    print(f"Wrote: {sen_out}")


if __name__ == "__main__":
    main()
