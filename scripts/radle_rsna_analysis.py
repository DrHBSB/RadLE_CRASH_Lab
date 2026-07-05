"""
RadLE-RSNA Confidence-Aware Benchmark — Analysis Script
========================================================

Inputs (paths configurable below or via CLI args):
  1. Scored diagnosis file (radiologist-graded)  — wide format, 200 rows × 25 cols
                                                   columns: Master_Case_ID, Ground_Truth_Diagnosis,
                                                            Diagnosis_Model_{A..J},
                                                            Score_Model_{A..J} (binary 0/1),
                                                            Reviewer_Notes
  2. Likert review file                          — wide format, 200 rows × 25 cols
                                                   columns: Master_Case_ID, Diagnosis_Model_{A..J},
                                                            Likert_Model_{A..J}

Outputs (written to ./outputs/):
  - results_table.csv             : full per-model results with all metrics
  - abstract_placeholders.txt     : the X/Y/Z/W values that fill the abstract draft
  - analysis_log.txt              : data-quality flags and validation summary

Locked decisions (per Hakikat + Suvrankar consensus):
  - Likert scale: 0–4 (verified empirically)
  - Primary accuracy denominator = 200; abstentions and technical failures count as 0
  - Calibration denominator = diagnosis-given + valid Likert only
  - Headline safety metric = very-high-confidence error rate (Likert=4)
  - Secondary safety metric = high-confidence error rate (Likert≥3)
  - Calibration metrics = Ordinal ECE (Likert/4 mapping) + Spearman ρ
  - 95% Wilson CIs on all proportions
  - Empty Likert bins excluded from ECE weighted mean
  - Table ordering = very-high-confidence error rate ascending; ties → accuracy desc, ECE asc
"""

import argparse
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Configuration: locked per consensus
# ---------------------------------------------------------------------------

MODEL_LETTERS = list("ABCDEFGHIJ")

UNBLIND_MAP = {
    "A": "GPT-5.5",
    "B": "Claude Opus 4.7",
    "C": "Gemini 3.1 Pro",
    "D": "Grok 4.20",
    "E": "Qwen VL Max",
    "F": "Gemma 4 31B",
    "G": "Llama 4 Maverick",
    "H": "Pixtral Large",
    "I": "GLM 4.6V",
    "J": "Nemotron 3 Omni",
}

LIKERT_TO_PROB = {0: 0.00, 1: 0.25, 2: 0.50, 3: 0.75, 4: 1.00}

ABSTENTION_PATTERN = r"don'?t\s*know|i\s*dont\s*know"
TECH_FAIL_PATTERN = r"PARSE_FAILED|API_ERROR|provider\s*block|^ERROR$"


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """95% Wilson score CI for a proportion. Returns (lo, hi) on [0,1]."""
    if n == 0:
        return (float("nan"), float("nan"))
    z = stats.norm.ppf(1 - alpha / 2)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    halfw = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    return (max(0.0, centre - halfw), min(1.0, centre + halfw))


def fmt_pct_ci(k: int, n: int) -> str:
    if n == 0:
        return "NA"
    p = 100 * k / n
    lo, hi = wilson_ci(k, n)
    return f"{p:.1f}% [{100*lo:.1f}–{100*hi:.1f}]"


def matches_pattern(value, pattern: str) -> bool:
    """Case-insensitive regex match for non-empty scalar cells."""
    if pd.isna(value):
        return False
    return re.search(pattern, str(value), flags=re.IGNORECASE) is not None


def ordinal_ece(likert: np.ndarray, correct: np.ndarray) -> float:
    """
    Ordinal ECE on the 0–4 Likert scale, mapped to [0,1] via Likert/4.
    Empty bins are excluded from the weighted mean.
    Inputs already filtered to diagnosis-given + valid-Likert.
    """
    if len(likert) == 0:
        return float("nan")
    n = len(likert)
    total = 0.0
    for bin_val, mapped_conf in LIKERT_TO_PROB.items():
        mask = likert == bin_val
        n_bin = mask.sum()
        if n_bin == 0:
            continue
        emp_acc = correct[mask].mean()
        total += (n_bin / n) * abs(emp_acc - mapped_conf)
    return total


def spearman_rho(likert: np.ndarray, correct: np.ndarray) -> float:
    if len(likert) < 3:
        return float("nan")
    if np.unique(likert).size < 2 or np.unique(correct).size < 2:
        return float("nan")
    rho, _ = stats.spearmanr(likert, correct)
    return rho


# ---------------------------------------------------------------------------
# Cell classification
# ---------------------------------------------------------------------------

def classify_cell(diagnosis: str, likert_raw, score) -> str:
    """
    Classify a single model-case cell into one of:
      - 'abstention'    : diagnosis indicates 'I don't know'
      - 'tech_failure'  : diagnosis indicates PARSE_FAILED / API_ERROR
      - 'answered_valid': model gave a real diagnosis with a valid 0–4 Likert
      - 'answered_dirty_likert' : real diagnosis but Likert is invalid → exclude from calibration
      - 'missing'       : diagnosis is NaN/blank
    """
    if pd.isna(diagnosis) or str(diagnosis).strip() == "":
        return "missing"

    s = str(diagnosis)
    if matches_pattern(s, ABSTENTION_PATTERN):
        return "abstention"
    if matches_pattern(s, TECH_FAIL_PATTERN):
        return "tech_failure"

    likert_num = pd.to_numeric(pd.Series([likert_raw]), errors="coerce").iloc[0]
    if pd.isna(likert_num) or likert_num not in LIKERT_TO_PROB:
        return "answered_dirty_likert"
    return "answered_valid"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_csv_robust(path: Path) -> pd.DataFrame:
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"Could not decode {path} with utf-8/cp1252/latin-1")


def _nonblank_mask(series: pd.Series) -> pd.Series:
    return series.notna() & series.astype(str).str.strip().ne("")


def _normalise_case_ids(df: pd.DataFrame) -> pd.Series:
    return df["Master_Case_ID"].astype("string").fillna("").str.strip()


def validate_inputs(scored: pd.DataFrame, likert: pd.DataFrame) -> None:
    """Fail fast on schema or alignment problems that could corrupt final results."""
    errors: list[str] = []

    scored_required = ["Master_Case_ID", "Ground_Truth_Diagnosis"]
    likert_required = ["Master_Case_ID"]
    for letter in MODEL_LETTERS:
        scored_required.extend([f"Diagnosis_Model_{letter}", f"Score_Model_{letter}"])
        likert_required.extend([f"Diagnosis_Model_{letter}", f"Likert_Model_{letter}"])

    for name, df, required in (
        ("scored", scored, scored_required),
        ("likert", likert, likert_required),
    ):
        missing = [col for col in required if col not in df.columns]
        if missing:
            errors.append(f"{name} file is missing required columns: {missing}")
        if len(df) != 200:
            errors.append(f"{name} file has {len(df)} rows, expected 200")

    if errors:
        raise ValueError("Input validation failed:\n- " + "\n- ".join(errors))

    scored_ids = _normalise_case_ids(scored)
    likert_ids = _normalise_case_ids(likert)
    for name, ids in (("scored", scored_ids), ("likert", likert_ids)):
        blank_count = int(ids.eq("").sum())
        if blank_count:
            errors.append(f"{name} file has {blank_count} blank Master_Case_ID value(s)")
        dupes = ids[ids.duplicated()].drop_duplicates().head(10).tolist()
        if dupes:
            errors.append(f"{name} file has duplicate Master_Case_ID value(s): {dupes}")

    scored_id_set = set(scored_ids)
    likert_id_set = set(likert_ids)
    missing_in_likert = sorted(scored_id_set - likert_id_set)[:10]
    extra_in_likert = sorted(likert_id_set - scored_id_set)[:10]
    if missing_in_likert:
        errors.append(f"cases in scored file but not likert file: {missing_in_likert}")
    if extra_in_likert:
        errors.append(f"cases in likert file but not scored file: {extra_in_likert}")

    gt_missing = int((~_nonblank_mask(scored["Ground_Truth_Diagnosis"])).sum())
    if gt_missing:
        errors.append(f"scored file has {gt_missing} blank Ground_Truth_Diagnosis value(s)")

    if errors:
        raise ValueError("Input validation failed:\n- " + "\n- ".join(errors))

    for letter in MODEL_LETTERS:
        score_col = f"Score_Model_{letter}"
        score_raw = scored[score_col]
        score_num = pd.to_numeric(score_raw, errors="coerce")
        invalid_score = _nonblank_mask(score_raw) & ~score_num.isin([0, 1])
        if invalid_score.any():
            case_examples = scored_ids[invalid_score].head(10).tolist()
            errors.append(f"{score_col} has non-binary score value(s) at cases: {case_examples}")

    likert_by_id = likert.assign(_case_id=likert_ids).set_index("_case_id")
    checked_errors = 0
    for _, row in scored.assign(_case_id=scored_ids).iterrows():
        case_id = row["_case_id"]
        likert_row = likert_by_id.loc[case_id]
        for letter in MODEL_LETTERS:
            diagnosis_col = f"Diagnosis_Model_{letter}"
            likert_col = f"Likert_Model_{letter}"
            diagnosis = row[diagnosis_col]

            if pd.isna(diagnosis) or str(diagnosis).strip() == "":
                continue
            if matches_pattern(diagnosis, ABSTENTION_PATTERN) or matches_pattern(diagnosis, TECH_FAIL_PATTERN):
                continue

            likert_raw = likert_row[likert_col]
            likert_num = pd.to_numeric(pd.Series([likert_raw]), errors="coerce").iloc[0]
            if pd.isna(likert_num) or likert_num not in LIKERT_TO_PROB:
                errors.append(
                    f"{likert_col} is missing/invalid for answered diagnosis at case {case_id}"
                )
                checked_errors += 1

            if checked_errors >= 20:
                errors.append("additional validation errors suppressed after first 20 findings")
                break
        if checked_errors >= 20:
            break

    if errors:
        raise ValueError("Input validation failed:\n- " + "\n- ".join(errors))


def melt_to_long(scored: pd.DataFrame, likert: pd.DataFrame) -> pd.DataFrame:
    """Build a long-format frame: one row per (Master_Case_ID, Model_Letter)."""
    rows = []
    # join keys
    scored_idx = scored.set_index("Master_Case_ID")
    likert_idx = likert.set_index("Master_Case_ID")

    for case_id in scored_idx.index:
        gt = scored_idx.loc[case_id, "Ground_Truth_Diagnosis"]
        for letter in MODEL_LETTERS:
            diag_col = f"Diagnosis_Model_{letter}"
            score_col = f"Score_Model_{letter}"
            likert_col = f"Likert_Model_{letter}"
            diagnosis = scored_idx.loc[case_id, diag_col]
            score_raw = scored_idx.loc[case_id, score_col]
            likert_raw = likert_idx.loc[case_id, likert_col] if case_id in likert_idx.index else np.nan

            # Score: NaN means ungraded; coerce to int when available
            score_num = pd.to_numeric(pd.Series([score_raw]), errors="coerce").iloc[0]

            cls = classify_cell(diagnosis, likert_raw, score_raw)

            rows.append({
                "Master_Case_ID": case_id,
                "Model_Letter": letter,
                "Model_Name": UNBLIND_MAP[letter],
                "Ground_Truth": gt,
                "Diagnosis": diagnosis,
                "Likert_Raw": likert_raw,
                "Score_Raw": score_raw,
                "Score": score_num,
                "Class": cls,
            })
    return pd.DataFrame(rows)


def per_model_metrics(long_df: pd.DataFrame, model_letter: str) -> dict:
    sub = long_df[long_df["Model_Letter"] == model_letter].copy()
    n_total = len(sub)  # should be 200

    # Class counts
    n_abstention = (sub["Class"] == "abstention").sum()
    n_tech_fail = (sub["Class"] == "tech_failure").sum()
    n_missing = (sub["Class"] == "missing").sum()
    n_answered_valid = (sub["Class"] == "answered_valid").sum()
    n_answered_dirty = (sub["Class"] == "answered_dirty_likert").sum()
    n_answered = n_answered_valid + n_answered_dirty

    # --- Primary accuracy: /200, abstentions+tech failures score 0 ---
    # If a cell is abstention/tech_failure, score is forced to 0 (regardless of what's in the score column)
    # Otherwise we use the human-graded score
    score_for_acc = sub["Score"].copy()
    score_for_acc.loc[sub["Class"].isin(["abstention", "tech_failure"])] = 0
    n_correct = int(score_for_acc.sum(skipna=True))
    n_scored_cells = score_for_acc.notna().sum()
    n_ungraded = n_total - n_scored_cells

    primary_acc = n_correct / n_total if n_total else float("nan")
    acc_lo, acc_hi = wilson_ci(n_correct, n_total)

    # Coverage = diagnosis-given (any answered, valid or dirty likert)
    coverage = n_answered / n_total
    cov_lo, cov_hi = wilson_ci(n_answered, n_total)

    abst_rate = n_abstention / n_total
    abst_lo, abst_hi = wilson_ci(n_abstention, n_total)

    tech_rate = n_tech_fail / n_total

    # Conditional accuracy: among diagnosis-given cells (use raw score on answered cells)
    answered_mask = sub["Class"].isin(["answered_valid", "answered_dirty_likert"])
    answered_scores = sub.loc[answered_mask, "Score"]
    n_answered_graded = answered_scores.notna().sum()
    n_answered_correct = int(answered_scores.sum(skipna=True))
    cond_acc = n_answered_correct / n_answered_graded if n_answered_graded else float("nan")

    # --- Calibration: only on answered_valid cells with non-null score ---
    cal_mask = (sub["Class"] == "answered_valid") & sub["Score"].notna()
    cal = sub.loc[cal_mask].copy()
    cal_likert = pd.to_numeric(cal["Likert_Raw"], errors="coerce").to_numpy()
    cal_correct = cal["Score"].astype(int).to_numpy()
    n_cal = len(cal)

    # --- Confidence distribution: independent of scoring completeness ---
    # Per Codex #2: mean/median Likert should reflect the model's confidence behavior,
    # which is a property of all diagnosis-given outputs with valid Likert,
    # NOT just those that have been graded.
    conf_mask = sub["Class"] == "answered_valid"
    conf_likert_all = pd.to_numeric(sub.loc[conf_mask, "Likert_Raw"],
                                     errors="coerce").dropna().to_numpy()
    n_conf_set = len(conf_likert_all)

    if n_conf_set > 0:
        mean_likert = float(conf_likert_all.mean())
        median_likert = float(np.median(conf_likert_all))
    else:
        mean_likert = median_likert = float("nan")

    # --- Confidence-bucket rates (Codex #3) ---
    # Rate of high-conf and very-high-conf usage among the calibration-eligible set.
    # A model can look "safe" by rarely emitting Likert=4; rate columns expose that.
    n_hc_total = int((conf_likert_all >= 3).sum()) if n_conf_set else 0
    n_vhc_total = int((conf_likert_all == 4).sum()) if n_conf_set else 0
    high_conf_rate = n_hc_total / n_conf_set if n_conf_set else float("nan")
    very_high_conf_rate = n_vhc_total / n_conf_set if n_conf_set else float("nan")

    if n_cal > 0:
        ece = ordinal_ece(cal_likert, cal_correct)
        rho = spearman_rho(cal_likert, cal_correct)
    else:
        ece = rho = float("nan")

    # --- Safety metrics ---
    # High-confidence (Likert ≥3) error rate among answered_valid w/ score
    hc_mask = cal_likert >= 3
    n_hc = int(hc_mask.sum())
    n_hc_wrong = int((cal_correct[hc_mask] == 0).sum()) if n_hc else 0
    hc_err_rate = n_hc_wrong / n_hc if n_hc else float("nan")
    hc_lo, hc_hi = wilson_ci(n_hc_wrong, n_hc) if n_hc else (float("nan"), float("nan"))

    # Very-high-confidence (Likert =4) error rate
    vhc_mask = cal_likert == 4
    n_vhc = int(vhc_mask.sum())
    n_vhc_wrong = int((cal_correct[vhc_mask] == 0).sum()) if n_vhc else 0
    vhc_err_rate = n_vhc_wrong / n_vhc if n_vhc else float("nan")
    vhc_lo, vhc_hi = wilson_ci(n_vhc_wrong, n_vhc) if n_vhc else (float("nan"), float("nan"))

    return {
        "Model_Letter": model_letter,
        "Model": UNBLIND_MAP[model_letter],
        # Accuracy
        "n_correct": n_correct,
        "n_total": n_total,
        "n_ungraded": int(n_ungraded),
        "Primary_Accuracy": primary_acc,
        "Primary_Accuracy_CI_lo": acc_lo,
        "Primary_Accuracy_CI_hi": acc_hi,
        # Coverage / refusal
        "Coverage": coverage,
        "Coverage_CI_lo": cov_lo,
        "Coverage_CI_hi": cov_hi,
        "Abstention_Rate": abst_rate,
        "Abstention_CI_lo": abst_lo,
        "Abstention_CI_hi": abst_hi,
        "Technical_Failure_Rate": tech_rate,
        # Conditional acc
        "Conditional_Accuracy_among_answered": cond_acc,
        "n_answered": n_answered,
        "n_answered_graded": int(n_answered_graded),
        # Likert summary
        "n_calibration_set": n_cal,
        "n_confidence_set": n_conf_set,
        "Mean_Likert": mean_likert,
        "Median_Likert": median_likert,
        # Confidence-bucket usage rates (Codex #3) — independent of scoring
        "High_Conf_Rate": high_conf_rate,
        "Very_High_Conf_Rate": very_high_conf_rate,
        # Calibration metrics
        "Ordinal_ECE": ece,
        "Spearman_rho": rho,
        # Safety metrics
        "n_high_conf": n_hc,
        "n_high_conf_wrong": n_hc_wrong,
        "High_Conf_Error_Rate": hc_err_rate,
        "HC_Err_CI_lo": hc_lo,
        "HC_Err_CI_hi": hc_hi,
        "n_very_high_conf": n_vhc,
        "n_very_high_conf_wrong": n_vhc_wrong,
        "Very_High_Conf_Error_Rate": vhc_err_rate,
        "VHC_Err_CI_lo": vhc_lo,
        "VHC_Err_CI_hi": vhc_hi,
        # Diagnostics
        "n_dirty_likert_answered": int(n_answered_dirty),
        "n_missing": int(n_missing),
    }


def build_results_table(long_df: pd.DataFrame) -> pd.DataFrame:
    rows = [per_model_metrics(long_df, L) for L in MODEL_LETTERS]
    df = pd.DataFrame(rows)
    # Sort: VHC error rate asc, accuracy desc, ECE asc
    df = df.sort_values(
        by=["Very_High_Conf_Error_Rate", "Primary_Accuracy", "Ordinal_ECE"],
        ascending=[True, False, True],
        na_position="last",
    ).reset_index(drop=True)
    return df


def _format_tied_models(df: pd.DataFrame, col: str, ascending: bool, value_fmt: str = "{:.1f}%",
                         scale: float = 100.0) -> tuple[str, float]:
    """
    Find tied extreme model(s) on a column and format them.
    ascending=True picks lowest; False picks highest.
    Returns (formatted_model_string, value).
    """
    s = df[col].dropna()
    if len(s) == 0:
        return ("NA", float("nan"))
    target = s.min() if ascending else s.max()
    # Tie tolerance: 0.5 percentage points on rates, equivalent on raw scale
    tol = 0.005 if scale == 100 else 0.001
    tied = df[np.isclose(df[col], target, atol=tol)]["Model"].tolist()
    if len(tied) == 1:
        return (tied[0], target)
    elif len(tied) == 2:
        return (f"{tied[0]} and {tied[1]}", target)
    else:
        return (", ".join(tied[:-1]) + f", and {tied[-1]}", target)


def write_abstract_placeholders(df: pd.DataFrame, out: Path, partial: bool = False) -> None:
    """Fill in the placeholders from Suvrankar's locked Results sentence."""
    acc = df["Primary_Accuracy"] * 100
    mean_lk = df["Mean_Likert"]
    ece = df["Ordinal_ECE"]
    rho = df["Spearman_rho"]
    abst = df["Abstention_Rate"] * 100

    # Tied best/worst on VHC error rate (lower = safer)
    best_vhc_str, best_vhc_val = _format_tied_models(df, "Very_High_Conf_Error_Rate", ascending=True)
    worst_vhc_str, worst_vhc_val = _format_tied_models(df, "Very_High_Conf_Error_Rate", ascending=False)

    # Best/worst on accuracy
    best_acc_str, best_acc_val = _format_tied_models(df, "Primary_Accuracy", ascending=False)
    worst_acc_str, worst_acc_val = _format_tied_models(df, "Primary_Accuracy", ascending=True)

    lines = []
    if partial:
        lines.append("#" * 72)
        lines.append("#  PARTIAL RESULTS — DO NOT SUBMIT")
        lines.append("#  Some answered cells were not human-scored.")
        lines.append("#  Numbers below are biased and incomplete.")
        lines.append("#" * 72)
        lines.append("")
    lines.append("=" * 72)
    lines.append("ABSTRACT PLACEHOLDER VALUES")
    lines.append("=" * 72)
    lines.append("")
    lines.append("Methods sentence (locked):")
    lines.append('"Model confidence was recorded on a standardized 0–4 clinically')
    lines.append('interpretable Likert scale, with 0 indicating very low confidence')
    lines.append('and 4 indicating very high confidence."')
    lines.append("")
    lines.append("-" * 72)
    lines.append("Results paragraph values:")
    lines.append("-" * 72)
    lines.append("")
    lines.append(f"  Accuracy range:           {acc.min():.1f}%  to  {acc.max():.1f}%")
    lines.append(f"    [lowest:  {worst_acc_str}]")
    lines.append(f"    [highest: {best_acc_str}]")
    lines.append("")
    lines.append(f"  Mean Likert range:        {mean_lk.min():.2f}  to  {mean_lk.max():.2f}  (on 0–4 scale)")
    lines.append(f"    [lowest:  {df.loc[mean_lk.idxmin(),'Model']}]")
    lines.append(f"    [highest: {df.loc[mean_lk.idxmax(),'Model']}]")
    lines.append("")
    lines.append(f"  Very-high-confidence error rate (Likert=4):")
    lines.append(f"    LOWEST  (safest at peak confidence): {best_vhc_str} at {best_vhc_val*100:.1f}%")
    lines.append(f"    HIGHEST (most overconfident):        {worst_vhc_str} at {worst_vhc_val*100:.1f}%")
    lines.append("")
    lines.append(f"  Ordinal ECE range:        {ece.min():.3f}  to  {ece.max():.3f}")
    lines.append(f"  Spearman ρ range:         {rho.min():.3f}  to  {rho.max():.3f}")
    lines.append(f"  Abstention rate range:    {abst.min():.1f}%  to  {abst.max():.1f}%")
    lines.append("")
    lines.append("-" * 72)
    lines.append("DRAFT RESULTS PARAGRAPH (copy-paste ready):")
    lines.append("-" * 72)
    lines.append("")
    # Build the narrative carefully so tied models read naturally.
    para = (
        f"Across 2,000 model-case interpretations, overall diagnostic accuracy "
        f"ranged from {acc.min():.1f}% to {acc.max():.1f}%. Mean self-reported "
        f"confidence among diagnosis-given outputs ranged from {mean_lk.min():.2f} "
        f"to {mean_lk.max():.2f} on the 0–4 scale. Very-high-confidence errors "
        f"(Likert = 4) varied substantially: "
    )
    if best_vhc_str == worst_vhc_str:
        para += f"all evaluable models showed a very-high-confidence error rate of {best_vhc_val*100:.1f}%. "
    else:
        para += (
            f"{best_vhc_str} demonstrated the lowest very-high-confidence error rate "
            f"at {best_vhc_val*100:.1f}%, while {worst_vhc_str} showed the highest "
            f"at {worst_vhc_val*100:.1f}%. "
        )
    para += (
        f"Ordinal ECE ranged from {ece.min():.3f} to {ece.max():.3f}, and "
        f"confidence–correctness correlation ranged from Spearman ρ {rho.min():.2f} "
        f"to {rho.max():.2f}. Abstention rates ranged from {abst.min():.1f}% to "
        f"{abst.max():.1f}%."
    )
    lines.append(para)
    lines.append("")
    lines.append("-" * 72)
    lines.append("CAVEAT — denominator awareness:")
    lines.append("-" * 72)
    lines.append("")
    lines.append("Per-model VHC denominator (n with Likert=4) — small denominators")
    lines.append("inflate uncertainty around the headline VHC error rate:")
    for _, r in df.iterrows():
        lines.append(f"  {r['Model']:20s}  n_VHC={int(r['n_very_high_conf']):3d}  "
                     f"VHC_err={r['Very_High_Conf_Error_Rate']*100 if pd.notna(r['Very_High_Conf_Error_Rate']) else float('nan'):5.1f}%  "
                     f"VHC_rate={r['Very_High_Conf_Rate']*100 if pd.notna(r['Very_High_Conf_Rate']) else float('nan'):5.1f}%")
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")


def write_log(long_df: pd.DataFrame, df_results: pd.DataFrame, out: Path) -> None:
    lines = []
    lines.append("RadLE-RSNA Analysis Log")
    lines.append("=" * 72)
    lines.append("")
    lines.append("Cell classification per model:")
    cls_pivot = pd.crosstab(long_df["Model_Letter"], long_df["Class"])
    lines.append(cls_pivot.to_string())
    lines.append("")
    lines.append("Ungraded cells per model (Score is NaN for non-abstention/non-tech rows):")
    for L in MODEL_LETTERS:
        sub = long_df[long_df["Model_Letter"] == L]
        # ungraded among answered (the ones humans had to grade)
        ung = ((sub["Class"].isin(["answered_valid", "answered_dirty_likert"])) & sub["Score"].isna()).sum()
        lines.append(f"  Model_{L} ({UNBLIND_MAP[L]}): ungraded answered cells = {ung}")
    lines.append("")
    lines.append("Sparse Likert bin warnings (n=0 in any used bin):")
    for L in MODEL_LETTERS:
        cal = long_df[(long_df["Model_Letter"] == L) & (long_df["Class"] == "answered_valid")]
        cal_likert = pd.to_numeric(cal["Likert_Raw"], errors="coerce").dropna().astype(int)
        bin_counts = {b: int((cal_likert == b).sum()) for b in range(5)}
        empty = [b for b, n in bin_counts.items() if n == 0]
        if empty:
            lines.append(f"  Model_{L}: empty Likert bins = {empty}  (counts: {bin_counts})")
    lines.append("")
    lines.append("=" * 72)
    lines.append("Per-model results (sorted by VHC error rate ascending):")
    lines.append("=" * 72)
    pretty_cols = [
        "Model", "Primary_Accuracy", "Coverage", "Abstention_Rate",
        "Mean_Likert", "Median_Likert",
        "High_Conf_Error_Rate", "Very_High_Conf_Error_Rate",
        "Ordinal_ECE", "Spearman_rho", "Technical_Failure_Rate",
    ]
    lines.append(df_results[pretty_cols].to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True, help="Path to radiologist-scored diagnosis CSV")
    ap.add_argument("--likert", required=True, help="Path to Likert review CSV")
    ap.add_argument("--out",    default="./outputs", help="Output directory")
    ap.add_argument("--allow-partial", action="store_true",
                    help="Allow analysis on a partially-scored file (NOT FOR SUBMISSION)")
    args = ap.parse_args()

    scored_path = Path(args.scored)
    likert_path = Path(args.likert)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] Loading inputs...")
    scored = load_csv_robust(scored_path)
    likert = load_csv_robust(likert_path)

    print(f"[2/5] Validating schema, case IDs, scores, ground truth, and Likert values...")
    validate_inputs(scored, likert)

    print(f"[3/5] Melting to long format & classifying cells...")
    long_df = melt_to_long(scored, likert)
    long_df.to_csv(out_dir / "long_format.csv", index=False, encoding="utf-8")

    # ---- HARD STOP on ungraded cells (unless --allow-partial) ----
    ungraded_mask = (long_df["Class"].isin(["answered_valid", "answered_dirty_likert"])) & \
                     long_df["Score"].isna()
    ungraded_total = int(ungraded_mask.sum())
    if ungraded_total > 0:
        per_model = (long_df[ungraded_mask].groupby("Model_Letter").size()
                     .reindex(MODEL_LETTERS, fill_value=0))
        print()
        print("=" * 72)
        print(f"INCOMPLETE SCORING DETECTED — {ungraded_total} answered cells lack a Score")
        print("=" * 72)
        for L in MODEL_LETTERS:
            n = int(per_model[L])
            if n > 0:
                print(f"  Model_{L} ({UNBLIND_MAP[L]}): {n} ungraded answered cells")
        print()
        if not args.allow_partial:
            print("REFUSING to write final results. Re-run with --allow-partial to override")
            print("(produces results clearly marked as PARTIAL — NOT FOR SUBMISSION).")
            sys.exit(2)
        else:
            print("Proceeding with --allow-partial. Outputs will be marked PARTIAL.")
            print()

    print(f"[4/5] Computing per-model metrics...")
    df_results = build_results_table(long_df)
    df_results.to_csv(out_dir / "results_table.csv", index=False, encoding="utf-8")

    print(f"[5/5] Writing abstract placeholders & log...")
    write_abstract_placeholders(df_results, out_dir / "abstract_placeholders.txt",
                                 partial=(ungraded_total > 0))
    write_log(long_df, df_results, out_dir / "analysis_log.txt")

    print()
    print(f"Outputs written to: {out_dir.resolve()}")
    print(f"  - results_table.csv")
    print(f"  - abstract_placeholders.txt")
    print(f"  - analysis_log.txt")
    print(f"  - long_format.csv (intermediate)")
    print()
    # Quick console summary
    print("=" * 72)
    print("QUICK SUMMARY (sorted by very-high-confidence error rate ascending)")
    print("=" * 72)
    summary_cols = ["Model", "Primary_Accuracy", "Coverage",
                    "Very_High_Conf_Error_Rate", "Ordinal_ECE", "Spearman_rho"]
    print(df_results[summary_cols].to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    main()
