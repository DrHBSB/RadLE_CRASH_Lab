#!/usr/bin/env python3
"""RadLE v2 shared metrics core (Part A — LOCKED).

Single source of truth for every rollup (Parts B-E). All summaries MUST import
`metrics` from here so denominators, the Wilson interval, non-answer decomposition,
and the weighted-score mean are defined exactly once.

Scoring conventions (do not change without re-locking):
  authoritative correctness column = `final_score_authoritative` (int 0/1).
  strict accuracy    = n_correct / n           (non-answers count as wrong; denom = all rows)
  attempted accuracy = n_correct / n_attempted (n_attempted = rows with score_required == True)
  Every AI/human arm has exactly 200 cases, so a single arm's strict denom is 200.
  weighted_score is signed likert (+likert if correct, -likert if wrong), blank when
  likert is non-numeric; the mean is taken over non-blank rows only.

Run this file directly to execute the self-test (hand-verified ground truth).
"""
import math

import pandas as pd

Z95 = 1.959963984540054  # two-sided 95%


def wilson(k: int, n: int, z: float = Z95):
    """Wilson score interval for a binomial proportion k/n. Returns (lo, hi)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (center - half, center + half)


def metrics(df: pd.DataFrame, rnd: int = 4) -> dict:
    """Compute the locked metric block for a group of long-format rows.

    Expects columns: final_score_authoritative (0/1), score_required (bool),
    abstained (bool), technical_failure (bool), weighted_score (numeric-or-blank).
    """
    n = int(len(df))
    n_correct = int((df["final_score_authoritative"] == 1).sum())
    n_attempted = int((df["score_required"] == True).sum())  # noqa: E712
    w = pd.to_numeric(df["weighted_score"], errors="coerce")

    acc = n_correct / n if n else float("nan")
    acc_lo, acc_hi = wilson(n_correct, n)
    att = n_correct / n_attempted if n_attempted else float("nan")
    att_lo, att_hi = wilson(n_correct, n_attempted)

    def r(x):
        return round(x, rnd) if x == x else x  # keep NaN as NaN

    return {
        "n": n,
        "n_correct": n_correct,
        "accuracy": r(acc),
        "acc_ci_lo": r(acc_lo),
        "acc_ci_hi": r(acc_hi),
        "n_attempted": n_attempted,
        "attempted_accuracy": r(att),
        "att_ci_lo": r(att_lo),
        "att_ci_hi": r(att_hi),
        "n_abstained": int((df["abstained"] == True).sum()),  # noqa: E712
        "n_technical_failure": int((df["technical_failure"] == True).sum()),  # noqa: E712
        "mean_weighted_score": r(float(w.mean())) if w.notna().any() else float("nan"),
        "n_weighted": int(w.notna().sum()),
    }


# --------------------------------------------------------------------------- #
# Self-test: hand-verified ground truth from the authoritative master.
# --------------------------------------------------------------------------- #
def _selftest():
    from pathlib import Path

    master = (
        Path(__file__).resolve().parents[1]
        / "outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147"
        / "radle_v2_final_long_master.csv"
    )
    m = pd.read_csv(master)

    # whole-dataset invariants
    assert len(m) == 6000, len(m)
    assert int((m.final_score_authoritative == 1).sum()) == 1255

    gpt = metrics(m[m.candidate == "gpt_5_5"])
    assert gpt["n"] == 200 and gpt["n_correct"] == 56, gpt
    assert gpt["accuracy"] == 0.28, gpt
    assert abs(gpt["acc_ci_lo"] - 0.2224) < 1e-3 and abs(gpt["acc_ci_hi"] - 0.3459) < 1e-3, gpt
    assert gpt["n_attempted"] == 200 and gpt["attempted_accuracy"] == 0.28, gpt

    raj = metrics(m[m.provider == "Rajesh Vanagundi"])  # radiologist, 85 abstentions
    assert raj["n"] == 200 and raj["n_correct"] == 62, raj
    assert raj["accuracy"] == 0.31, raj
    assert raj["n_attempted"] == 115 and raj["n_abstained"] == 85, raj
    assert raj["attempted_accuracy"] == round(62 / 115, 4), raj
    assert raj["n_weighted"] == 115, raj

    # Sum of per-arm n_correct across all 30 arms must equal the global 1255.
    # candidate is NOT unique for humans (it's a role label), so group by identity.
    tot_id = sum(
        metrics(g)["n_correct"]
        for _, g in m.groupby(["candidate", "provider"], dropna=False)
    )
    assert tot_id == 1255, tot_id

    print("radle_metrics self-test PASSED")
    print("  gpt_5_5:", gpt)
    print("  Rajesh :", raj)
    print("  sum n_correct over 30 arms:", tot_id)


if __name__ == "__main__":
    _selftest()
