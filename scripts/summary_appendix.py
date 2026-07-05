#!/usr/bin/env python3
"""RadLE v2 Part E — appendix_within_provider_deltas.csv (LOCKED metrics core).

Computes within-provider deltas between the "kept" (non-excluded) arm and the
"excluded" duplicate-provider twin arm, matched on `candidate`.

Reads the master read-only. Uses `metrics()` from scripts/radle_metrics.py
without redefining any metric. Writes only appendix_within_provider_deltas.csv
into the output folder.
"""
import sys
from pathlib import Path

import pandas as pd

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from radle_metrics import metrics  # noqa: E402

OUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147"
)
MASTER = OUT_DIR / "radle_v2_final_long_master.csv"
OUT_CSV = OUT_DIR / "appendix_within_provider_deltas.csv"

PAIRS = [
    ("claude_fable_5", "claude_4_8_opus"),
    ("grok_4_3", "grok_4_20"),
    ("glm_5v_turbo", "glm_4_6v"),
]


def main():
    m = pd.read_csv(MASTER)

    rows = []
    for kept, excluded in PAIRS:
        kept_df = m[m.candidate == kept]
        excl_df = m[m.candidate == excluded]

        mk = metrics(kept_df)
        me = metrics(excl_df)

        provider_vals = kept_df["provider"].unique()
        assert len(provider_vals) == 1, (kept, provider_vals)
        provider = provider_vals[0]

        rows.append(
            {
                "provider": provider,
                "kept_model": kept,
                "excluded_model": excluded,
                "kept_accuracy": mk["accuracy"],
                "excluded_accuracy": me["accuracy"],
                "delta_accuracy": round(mk["accuracy"] - me["accuracy"], 4),
                "kept_mean_weighted": mk["mean_weighted_score"],
                "excluded_mean_weighted": me["mean_weighted_score"],
                "delta_mean_weighted": round(
                    mk["mean_weighted_score"] - me["mean_weighted_score"], 4
                ),
                "kept_n": mk["n"],
                "excluded_n": me["n"],
            }
        )

    out = pd.DataFrame(rows)

    # Asserts
    assert len(out) == 3, len(out)
    assert (out["kept_n"] == 200).all(), out["kept_n"].tolist()
    assert (out["excluded_n"] == 200).all(), out["excluded_n"].tolist()

    out.to_csv(OUT_CSV, index=False)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    print(out.to_string(index=False))
    print()
    print("Asserts passed: 3 rows, kept_n==200 all, excluded_n==200 all")
    print(f"Wrote: {OUT_CSV}")


if __name__ == "__main__":
    main()
