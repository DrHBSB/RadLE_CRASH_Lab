#!/usr/bin/env python3
"""RadLE v2 Part C rollups: provider_summary.csv, access_summary.csv, domain_summary.csv.

Non-excluded universe only (access != 'excluded'). Uses the LOCKED metrics core
from radle_metrics.py — do not redefine any metric here.
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

METRIC_COLS = [
    "n",
    "n_correct",
    "accuracy",
    "acc_ci_lo",
    "acc_ci_hi",
    "n_attempted",
    "attempted_accuracy",
    "att_ci_lo",
    "att_ci_hi",
    "n_abstained",
    "n_technical_failure",
    "mean_weighted_score",
    "n_weighted",
]


def build_summary(m: pd.DataFrame, group_col: str, sort_accuracy_desc: bool) -> pd.DataFrame:
    rows = []
    for key, g in m.groupby(group_col, dropna=False):
        row = {group_col: key}
        row.update(metrics(g))
        rows.append(row)
    df = pd.DataFrame(rows, columns=[group_col] + METRIC_COLS)
    if sort_accuracy_desc:
        df = df.sort_values("accuracy", ascending=False).reset_index(drop=True)
    return df


def main():
    m_all = pd.read_csv(MASTER)
    m = m_all[m_all["access"] != "excluded"].copy()

    assert len(m) == 5400, f"universe rows expected 5400, got {len(m)}"

    provider_summary = build_summary(m, "provider", sort_accuracy_desc=True)
    access_summary = build_summary(m, "access", sort_accuracy_desc=False)
    domain_summary = build_summary(m, "domain", sort_accuracy_desc=False)

    # Sigma checks for each output file.
    for name, df in [
        ("provider_summary", provider_summary),
        ("access_summary", access_summary),
        ("domain_summary", domain_summary),
    ]:
        sn = int(df["n"].sum())
        snc = int(df["n_correct"].sum())
        assert sn == 5400, f"{name}: Sigma n expected 5400, got {sn}"
        assert snc == 1224, f"{name}: Sigma n_correct expected 1224, got {snc}"

    # access-level tripwires
    access_lookup = access_summary.set_index("access")
    exp_access = {
        "closed": (1200, 245),
        "open": (1800, 55),
        "human": (2400, 924),
    }
    for k, (exp_n, exp_c) in exp_access.items():
        row = access_lookup.loc[k]
        assert int(row["n"]) == exp_n, f"access={k}: n expected {exp_n}, got {row['n']}"
        assert int(row["n_correct"]) == exp_c, (
            f"access={k}: n_correct expected {exp_c}, got {row['n_correct']}"
        )

    # domain-level tripwires
    domain_lookup = domain_summary.set_index("domain")
    exp_domain = {
        "general": (2400, 290),
        "medical": (600, 10),
        "human": (2400, 924),
    }
    for k, (exp_n, exp_c) in exp_domain.items():
        row = domain_lookup.loc[k]
        assert int(row["n"]) == exp_n, f"domain={k}: n expected {exp_n}, got {row['n']}"
        assert int(row["n_correct"]) == exp_c, (
            f"domain={k}: n_correct expected {exp_c}, got {row['n_correct']}"
        )

    provider_summary.to_csv(OUT_DIR / "provider_summary.csv", index=False)
    access_summary.to_csv(OUT_DIR / "access_summary.csv", index=False)
    domain_summary.to_csv(OUT_DIR / "domain_summary.csv", index=False)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)

    print("=== provider_summary.csv ===")
    print(provider_summary.to_string(index=False))
    print()
    print("=== access_summary.csv ===")
    print(access_summary.to_string(index=False))
    print()
    print("=== domain_summary.csv ===")
    print(domain_summary.to_string(index=False))
    print()
    print("ALL ASSERTS PASSED")


if __name__ == "__main__":
    main()
