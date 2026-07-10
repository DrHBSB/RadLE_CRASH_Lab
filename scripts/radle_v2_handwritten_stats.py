#!/usr/bin/env python3
"""Build RadLE v2 handwritten-panel summary CSVs.

This script reads the authoritative final long master read-only and writes the
supporting CSV/provenance files used by the handwritten SVG generator. It does
not render SVGs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from radle_metrics import metrics, wilson


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ROOT = (
    REPO_ROOT
    / "outputs"
    / "radle_v2_stats"
    / "final_scoring_radiologist_20260706_001147"
)
DEFAULT_MASTER = DEFAULT_OUT_ROOT / "radle_v2_final_long_master.csv"
EXPECTED_MASTER_SHA256 = (
    "7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED"
)

REQUIRED_COLUMNS = [
    "run_id",
    "Master_Case_ID",
    "candidate",
    "provider",
    "access",
    "domain",
    "likert",
    "final_score_authoritative",
    "score_required",
    "abstained",
    "technical_failure",
    "weighted_score",
    "rater_seniority",
    "rater_seniority_rank",
]

EXPECTED_SENIORITY_COUNTS = {
    "": 3600,
    "PGY2": 400,
    "PGY3": 800,
    "6mo post-MD": 200,
    "2y post-MD": 200,
    "3y post-MD": 400,
    "4y post-MD": 200,
    "7y post-MD": 200,
}

GROUPING_CONTRACTS = {
    "qual": {
        "title": "Qualification grouping",
        "groups": [
            {
                "group": "Radiology Trainees",
                "display_label": "Radiology trainees",
                "order": 1,
                "members": ["PGY2", "PGY3"],
                "expected_n": 1200,
                "expected_n_correct": 458,
                "expected_accuracy_pct": "38.17",
            },
            {
                "group": "Post-MD Radiologists",
                "display_label": "Board-certified radiologists",
                "order": 2,
                "members": [
                    "6mo post-MD",
                    "2y post-MD",
                    "3y post-MD",
                    "4y post-MD",
                    "7y post-MD",
                ],
                "expected_n": 1200,
                "expected_n_correct": 466,
                "expected_accuracy_pct": "38.83",
            },
        ],
    },
    "qual_human200": {
        "title": "Qualification grouping, human comparators normalized to n=200",
        "base_criterion": "qual",
        "normalization_mode": "human_mean_per_reader_200",
        "weighted_source_file": "qual_human200_weighted_source_master.csv",
        "groups": [
            {
                "group": "Radiology Trainees",
                "display_label": "Radiology trainees",
                "order": 1,
                "members": ["PGY2", "PGY3"],
                "expected_n": 200.0,
                "expected_n_correct": 458 / 6,
                "expected_accuracy_pct": "38.17",
            },
            {
                "group": "Post-MD Radiologists",
                "display_label": "Board-certified radiologists",
                "order": 2,
                "members": [
                    "6mo post-MD",
                    "2y post-MD",
                    "3y post-MD",
                    "4y post-MD",
                    "7y post-MD",
                ],
                "expected_n": 200.0,
                "expected_n_correct": 466 / 6,
                "expected_accuracy_pct": "38.83",
            },
        ],
    },
}

ACTIVE_CRITERIA = ("qual_human200",)

MODEL_DISPLAY_NAMES = {
    "gpt_5_5": "GPT-5.5",
    "claude_fable_5": "Claude Fable 5",
    "gemini_3_1_pro": "Gemini 3.1 Pro",
    "qwen_3_7_plus": "Qwen 3.7 Plus",
    "glm_5v_turbo": "GLM-5V Turbo",
    "gemma_4_31b": "Gemma 4 31B",
    "llama_4_maverick": "Llama 4 Maverick",
    "grok_4_3": "Grok 4.3",
    "minimax_m3": "MiniMax M3",
    "lingshu_32b": "Lingshu 32B",
    "octomed_7b": "OctoMed 7B",
    "internvl3_5_8b": "InternVL3.5 8B",
    "medgemma_1_5_4b": "MedGemma 1.5 4B",
    "mistral_large_3_2512": "Mistral Large 3",
    "nemotron_3_omni": "Nemotron 3 Omni",
}

METRIC_COLUMNS = [
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

NORMALIZABLE_COUNT_COLUMNS = [
    "n",
    "n_correct",
    "n_attempted",
    "n_abstained",
    "n_technical_failure",
    "n_weighted",
    "peak_wrong_n",
    "peak_correct_n",
    "cautious_n",
    "deferred_n",
    "abstained_n",
    "technical_failure_n",
    "other_deferred_n",
    "n_peak_conf",
    "verified_safe_n",
    "safe_uncertainty_n",
    "misleading_hazard_n",
    "confidence_volume_n",
]

NORMALIZATION_COLUMNS = [
    "normalization_mode",
    "normalization_unit",
    "normalization_divisor",
    *[f"source_{column}" for column in NORMALIZABLE_COUNT_COLUMNS],
]

CONFIDENCE_COLUMNS = [
    "criterion",
    "row_order",
    "row_kind",
    "display_name",
    "display_label",
    "group",
    "members",
    "candidate",
    "provider",
    "access",
    "domain",
    "n_raters",
    *NORMALIZATION_COLUMNS,
    *METRIC_COLUMNS,
    "accuracy_pct",
    "accuracy_pct_label",
    "peak_wrong_n",
    "peak_correct_n",
    "cautious_n",
    "deferred_n",
    "abstained_n",
    "technical_failure_n",
    "other_deferred_n",
    "n_peak_conf",
    "ppv_correct_pct",
    "ppv_wrong_pct",
    "ppv_correct_label",
    "ppv_wrong_label",
    "verified_safe_n",
    "safe_uncertainty_n",
    "misleading_hazard_n",
    "confidence_volume_n",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def pct_label(n_correct: float, n: float) -> str:
    if n == 0:
        return "nan"
    return f"{(100 * n_correct / n):.2f}"


def rounded_float(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def values_close(actual: object, expected: object, tolerance: float = 1e-4) -> bool:
    return abs(float(actual) - float(expected)) <= tolerance


def apply_normalization_metadata(
    row: dict[str, object],
    *,
    mode: str,
    unit: str,
    divisor: float,
) -> None:
    row["normalization_mode"] = mode
    row["normalization_unit"] = unit
    row["normalization_divisor"] = rounded_float(divisor)
    for column in NORMALIZABLE_COUNT_COLUMNS:
        if column in row:
            source_value = float(row[column])
            row[f"source_{column}"] = rounded_float(source_value)
            row[column] = rounded_float(source_value / divisor)
        else:
            row[f"source_{column}"] = ""

    n = float(row.get("n", 0) or 0)
    n_correct = float(row.get("n_correct", 0) or 0)
    n_attempted = float(row.get("n_attempted", 0) or 0)
    n_peak_conf = float(row.get("n_peak_conf", 0) or 0)
    peak_correct = float(row.get("peak_correct_n", 0) or 0)
    peak_wrong = float(row.get("peak_wrong_n", 0) or 0)

    accuracy = n_correct / n if n else float("nan")
    acc_lo, acc_hi = wilson(n_correct, n) if n else (float("nan"), float("nan"))
    attempted_accuracy = n_correct / n_attempted if n_attempted else float("nan")
    att_lo, att_hi = (
        wilson(n_correct, n_attempted) if n_attempted else (float("nan"), float("nan"))
    )

    row["accuracy"] = rounded_float(accuracy, 4)
    row["acc_ci_lo"] = rounded_float(acc_lo, 4) if acc_lo == acc_lo else acc_lo
    row["acc_ci_hi"] = rounded_float(acc_hi, 4) if acc_hi == acc_hi else acc_hi
    row["attempted_accuracy"] = (
        rounded_float(attempted_accuracy, 4)
        if attempted_accuracy == attempted_accuracy
        else attempted_accuracy
    )
    row["att_ci_lo"] = rounded_float(att_lo, 4) if att_lo == att_lo else att_lo
    row["att_ci_hi"] = rounded_float(att_hi, 4) if att_hi == att_hi else att_hi
    row["accuracy_pct"] = rounded_float(float(row["accuracy"]) * 100, 2)
    row["accuracy_pct_label"] = f"{float(row['accuracy_pct']):.2f}"

    if n_peak_conf:
        ppv_correct_pct = 100 * peak_correct / n_peak_conf
        ppv_wrong_pct = 100 * peak_wrong / n_peak_conf
        row["ppv_correct_pct"] = rounded_float(ppv_correct_pct, 2)
        row["ppv_wrong_pct"] = rounded_float(ppv_wrong_pct, 2)
        row["ppv_correct_label"] = f"{ppv_correct_pct:.0f}%"
        row["ppv_wrong_label"] = f"{ppv_wrong_pct:.0f}%"
    elif "ppv_correct_pct" in row:
        row["ppv_correct_pct"] = 0.0
        row["ppv_wrong_pct"] = 0.0
        row["ppv_correct_label"] = "NA"
        row["ppv_wrong_label"] = "NA"


def normalize_bool_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in ["score_required", "abstained", "technical_failure"]:
        out[column] = out[column].map(
            lambda value: str(value).strip().lower() in {"true", "1", "yes"}
        )
    out["final_score_authoritative"] = pd.to_numeric(
        out["final_score_authoritative"], errors="raise"
    ).astype(int)
    out["likert_num"] = pd.to_numeric(out["likert"], errors="coerce")
    out["rater_seniority"] = out["rater_seniority"].fillna("").astype(str)
    out["rater_seniority_rank"] = out["rater_seniority_rank"].fillna("")
    return out


def validate_preflight(master: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    if not master.exists():
        raise FileNotFoundError(f"Master CSV not found: {master}")
    master_sha = sha256_file(master)
    if master_sha != EXPECTED_MASTER_SHA256:
        raise ValueError(
            "Master SHA256 mismatch: "
            f"expected {EXPECTED_MASTER_SHA256}, got {master_sha}"
        )

    df = pd.read_csv(master)
    master_column_count = int(len(df.columns))
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Master CSV missing required columns: {', '.join(missing)}")
    if len(df) != 6000:
        raise ValueError(f"Expected 6000 master rows, got {len(df)}")
    if len(df.columns) != 20:
        raise ValueError(f"Expected 20 master columns, got {len(df.columns)}")

    df = normalize_bool_columns(df)
    score_values = sorted(df["final_score_authoritative"].dropna().unique().tolist())
    if score_values != [0, 1]:
        raise ValueError(f"final_score_authoritative values must be [0, 1], got {score_values}")
    n_correct = int((df["final_score_authoritative"] == 1).sum())
    if n_correct != 1255:
        raise ValueError(f"Expected 1255 correct rows, got {n_correct}")

    seniority_counts = {
        str(key): int(value)
        for key, value in df["rater_seniority"].value_counts(dropna=False).items()
    }
    if seniority_counts != EXPECTED_SENIORITY_COUNTS:
        raise ValueError(
            "rater_seniority counts mismatch: "
            f"expected {EXPECTED_SENIORITY_COUNTS}, got {seniority_counts}"
        )

    print(f"[PASS] preflight rows={len(df)} cols={master_column_count} correct={n_correct}")
    return df, {
        "master_path": str(master),
        "master_sha256": master_sha,
        "rows": int(len(df)),
        "columns": master_column_count,
        "n_correct": n_correct,
        "seniority_counts": seniority_counts,
        "generated_at_utc": utc_now(),
    }


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_group_summary(
    df: pd.DataFrame,
    criterion: str,
    contract: dict[str, object],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    group_rows: list[dict[str, object]] = []
    tier_rows: list[dict[str, object]] = []
    normalize_human = contract.get("normalization_mode") == "human_mean_per_reader_200"

    groups = contract["groups"]
    assert isinstance(groups, list)
    assigned_members: set[str] = set()

    for group_spec in groups:
        group_name = str(group_spec["group"])
        order = int(group_spec["order"])
        members = [str(member) for member in group_spec["members"]]
        assigned_members.update(members)
        group_df = df[df["rater_seniority"].isin(members)].copy()
        row = {
            "criterion": criterion,
            "group_order": order,
            "group": group_name,
            "members": "; ".join(members),
            "n_tiers": len(members),
            "n_raters": int(group_df["provider"].nunique()),
        }
        row.update(metrics(group_df))
        if normalize_human:
            apply_normalization_metadata(
                row,
                mode="human_mean_per_reader_200",
                unit="mean_group_reader",
                divisor=max(1, int(row["n_raters"])),
            )
        else:
            apply_normalization_metadata(row, mode="raw", unit="pooled_group", divisor=1)
        row["accuracy_pct"] = round(float(row["accuracy"]) * 100, 2)
        row["accuracy_pct_label"] = f"{row['accuracy_pct']:.2f}"
        group_rows.append(row)

        expected_n = float(group_spec["expected_n"])
        expected_correct = float(group_spec["expected_n_correct"])
        expected_pct = str(group_spec["expected_accuracy_pct"])
        actual_pct = pct_label(float(row["n_correct"]), float(row["n"]))
        if not values_close(row["n"], expected_n):
            raise ValueError(f"{criterion} {group_name}: expected n={expected_n}, got {row['n']}")
        if not values_close(row["n_correct"], expected_correct):
            raise ValueError(
                f"{criterion} {group_name}: expected n_correct={expected_correct}, "
                f"got {row['n_correct']}"
            )
        if actual_pct != expected_pct:
            raise ValueError(
                f"{criterion} {group_name}: expected accuracy_pct={expected_pct}, got {actual_pct}"
            )
        print(
            f"[PASS] {criterion} {group_name} "
            f"{float(row['n_correct']):.2f}/{float(row['n']):.2f} {actual_pct}%"
        )

        for tier in members:
            tier_df = group_df[group_df["rater_seniority"] == tier].copy()
            tier_rank = ""
            rank_values = [
                str(value)
                for value in tier_df["rater_seniority_rank"].dropna().unique().tolist()
                if str(value).strip()
            ]
            if rank_values:
                tier_rank = rank_values[0].replace(".0", "")
            tier_row = {
                "criterion": criterion,
                "group_order": order,
                "group": group_name,
                "tier": tier,
                "rater_seniority_rank": tier_rank,
                "n_raters": int(tier_df["provider"].nunique()),
            }
            tier_row.update(metrics(tier_df))
            if normalize_human:
                apply_normalization_metadata(
                    tier_row,
                    mode="human_mean_per_reader_200",
                    unit="mean_tier_reader",
                    divisor=max(1, int(tier_row["n_raters"])),
                )
            else:
                apply_normalization_metadata(tier_row, mode="raw", unit="pooled_tier", divisor=1)
            tier_row["accuracy_pct"] = round(float(tier_row["accuracy"]) * 100, 2)
            tier_row["accuracy_pct_label"] = f"{tier_row['accuracy_pct']:.2f}"
            tier_rows.append(tier_row)

    expected_human_members = {
        "PGY2",
        "PGY3",
        "6mo post-MD",
        "2y post-MD",
        "3y post-MD",
        "4y post-MD",
        "7y post-MD",
    }
    if assigned_members != expected_human_members:
        raise ValueError(
            f"{criterion}: assigned members mismatch: "
            f"expected {sorted(expected_human_members)}, got {sorted(assigned_members)}"
        )
    assigned_n = sum(float(row["n"]) for row in group_rows)
    assigned_correct = sum(float(row["n_correct"]) for row in group_rows)
    expected_assigned_n = sum(float(group["expected_n"]) for group in groups)
    expected_assigned_correct = sum(float(group["expected_n_correct"]) for group in groups)
    if not values_close(assigned_n, expected_assigned_n) or not values_close(
        assigned_correct, expected_assigned_correct
    ):
        raise ValueError(
            f"{criterion}: expected human assigned n/correct "
            f"{expected_assigned_n}/{expected_assigned_correct}, got {assigned_n}/{assigned_correct}"
        )
    return group_rows, tier_rows


def display_name_for_candidate(candidate: str) -> str:
    if candidate in MODEL_DISPLAY_NAMES:
        return MODEL_DISPLAY_NAMES[candidate]
    return candidate.replace("_", " ").title()


def confidence_counts(frame: pd.DataFrame) -> dict[str, object]:
    score_required = frame["score_required"]
    likert = frame["likert_num"]
    score = frame["final_score_authoritative"]

    peak = score_required & (likert == 4)
    peak_correct = peak & (score == 1)
    peak_wrong = peak & (score == 0)
    cautious = score_required & likert.isin([1, 2, 3])

    peak_correct_n = int(peak_correct.sum())
    peak_wrong_n = int(peak_wrong.sum())
    cautious_n = int(cautious.sum())
    n = int(len(frame))
    deferred_n = n - peak_correct_n - peak_wrong_n - cautious_n
    if deferred_n < 0:
        raise ValueError("confidence bucket counts exceeded row count")

    abstained_n = int(frame["abstained"].sum())
    technical_failure_n = int(frame["technical_failure"].sum())
    other_deferred_n = max(0, deferred_n - abstained_n - technical_failure_n)
    n_peak_conf = peak_correct_n + peak_wrong_n
    if n_peak_conf:
        ppv_correct_pct = round(100 * peak_correct_n / n_peak_conf, 2)
        ppv_wrong_pct = round(100 * peak_wrong_n / n_peak_conf, 2)
        ppv_correct_label = f"{ppv_correct_pct:.0f}%"
        ppv_wrong_label = f"{ppv_wrong_pct:.0f}%"
    else:
        ppv_correct_pct = 0.0
        ppv_wrong_pct = 0.0
        ppv_correct_label = "NA"
        ppv_wrong_label = "NA"

    return {
        "peak_wrong_n": peak_wrong_n,
        "peak_correct_n": peak_correct_n,
        "cautious_n": cautious_n,
        "deferred_n": deferred_n,
        "abstained_n": abstained_n,
        "technical_failure_n": technical_failure_n,
        "other_deferred_n": other_deferred_n,
        "n_peak_conf": n_peak_conf,
        "ppv_correct_pct": ppv_correct_pct,
        "ppv_wrong_pct": ppv_wrong_pct,
        "ppv_correct_label": ppv_correct_label,
        "ppv_wrong_label": ppv_wrong_label,
        "verified_safe_n": peak_correct_n,
        "safe_uncertainty_n": cautious_n + deferred_n,
        "misleading_hazard_n": peak_wrong_n,
        "confidence_volume_n": n_peak_conf,
    }


def confidence_row(
    criterion: str,
    row_kind: str,
    display_name: str,
    display_label: str,
    group: str,
    members: str,
    frame: pd.DataFrame,
    candidate: str = "",
    provider: str = "",
    access: str = "",
    domain: str = "",
    normalization_mode: str = "raw",
    normalization_unit: str = "row",
    normalization_divisor: float = 1.0,
) -> dict[str, object]:
    row: dict[str, object] = {
        "criterion": criterion,
        "row_order": 0,
        "row_kind": row_kind,
        "display_name": display_name,
        "display_label": display_label,
        "group": group,
        "members": members,
        "candidate": candidate,
        "provider": provider,
        "access": access,
        "domain": domain,
        "n_raters": int(frame["provider"].nunique()),
    }
    row.update(metrics(frame))
    row["accuracy_pct"] = round(float(row["accuracy"]) * 100, 2)
    row["accuracy_pct_label"] = f"{row['accuracy_pct']:.2f}"
    row.update(confidence_counts(frame))
    apply_normalization_metadata(
        row,
        mode=normalization_mode,
        unit=normalization_unit,
        divisor=normalization_divisor,
    )
    if (
        not values_close(
            float(row["peak_wrong_n"])
            + float(row["peak_correct_n"])
            + float(row["cautious_n"])
            + float(row["deferred_n"]),
            float(row["n"]),
        )
    ):
        raise ValueError(f"{criterion} {display_name}: confidence buckets do not sum to n")
    if not values_close(
        row["n_peak_conf"], float(row["peak_wrong_n"]) + float(row["peak_correct_n"])
    ):
        raise ValueError(f"{criterion} {display_name}: peak confidence denominator mismatch")
    return row


def build_confidence_summary(
    df: pd.DataFrame,
    criterion: str,
    contract: dict[str, object],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    normalize_human = contract.get("normalization_mode") == "human_mean_per_reader_200"
    model_df = df[(df["domain"] != "human") & (df["access"] != "excluded")].copy()
    for (candidate, provider, access, domain), frame in model_df.groupby(
        ["candidate", "provider", "access", "domain"], dropna=False, sort=False
    ):
        if len(frame) != 200:
            raise ValueError(f"{candidate}/{provider}: expected 200 model rows, got {len(frame)}")
        rows.append(
            confidence_row(
                criterion=criterion,
                row_kind="model",
                display_name=display_name_for_candidate(str(candidate)),
                display_label=display_name_for_candidate(str(candidate)),
                group="AI model",
                members="",
                frame=frame,
                candidate=str(candidate),
                provider=str(provider),
                access=str(access),
                domain=str(domain),
                normalization_mode="raw",
                normalization_unit="model_arm",
                normalization_divisor=1,
            )
        )

    groups = contract["groups"]
    assert isinstance(groups, list)
    for group_spec in groups:
        group_name = str(group_spec["group"])
        display_label = str(group_spec["display_label"])
        members = [str(member) for member in group_spec["members"]]
        frame = df[df["rater_seniority"].isin(members)].copy()
        n_raters = int(frame["provider"].nunique())
        rows.append(
            confidence_row(
                criterion=criterion,
                row_kind="human_comparator",
                display_name=group_name,
                display_label=display_label,
                group=group_name,
                members="; ".join(members),
                frame=frame,
                candidate="",
                provider="human comparator",
                access="human",
                domain="human",
                normalization_mode=(
                    "human_mean_per_reader_200" if normalize_human else "raw"
                ),
                normalization_unit=(
                    "mean_group_reader" if normalize_human else "pooled_group"
                ),
                normalization_divisor=max(1, n_raters) if normalize_human else 1,
            )
        )

    rows.sort(key=lambda row: (-float(row["accuracy"]), str(row["display_name"])))
    for idx, row in enumerate(rows, start=1):
        row["row_order"] = idx
    if len([row for row in rows if row["row_kind"] == "model"]) != 15:
        raise ValueError(f"{criterion}: expected 15 non-excluded model rows")
    if len([row for row in rows if row["row_kind"] == "human_comparator"]) != 2:
        raise ValueError(f"{criterion}: expected 2 human comparator rows")
    if sum(int(float(row["n"])) for row in rows if row["row_kind"] == "model") != 3000:
        raise ValueError(f"{criterion}: expected non-excluded model n=3000")
    if normalize_human:
        for row in rows:
            if row["row_kind"] == "human_comparator" and not values_close(row["n"], 200.0):
                raise ValueError(f"{criterion} {row['display_name']}: expected normalized n=200")
    return rows


def build_weighted_source_master(
    df: pd.DataFrame,
    criterion: str,
    contract: dict[str, object],
) -> pd.DataFrame:
    model_df = df[(df["domain"] != "human") & (df["access"] != "excluded")].copy()
    model_df["normalization_criterion"] = criterion
    model_df["normalization_row_kind"] = "model"
    model_df["normalization_group"] = "AI model"
    model_df["normalization_display_label"] = model_df["candidate"].map(
        lambda value: display_name_for_candidate(str(value))
    )
    model_df["normalization_weight"] = 1.0
    model_df["normalization_mode"] = "raw"
    model_df["normalization_unit"] = "model_arm"
    model_df["normalization_divisor"] = 1.0
    model_df["normalization_source_n_raters"] = 1

    human_frames: list[pd.DataFrame] = []
    groups = contract["groups"]
    assert isinstance(groups, list)
    for group_spec in groups:
        members = [str(member) for member in group_spec["members"]]
        frame = df[df["rater_seniority"].isin(members)].copy()
        n_raters = int(frame["provider"].nunique())
        frame["normalization_criterion"] = criterion
        frame["normalization_row_kind"] = "human_comparator"
        frame["normalization_group"] = str(group_spec["group"])
        frame["normalization_display_label"] = str(group_spec["display_label"])
        frame["normalization_weight"] = 1.0 / max(1, n_raters)
        frame["normalization_mode"] = str(contract.get("normalization_mode", "raw"))
        frame["normalization_unit"] = "mean_group_reader"
        frame["normalization_divisor"] = float(max(1, n_raters))
        frame["normalization_source_n_raters"] = n_raters
        human_frames.append(frame)

    out = pd.concat([model_df, *human_frames], ignore_index=True, sort=False)
    original_columns = list(df.columns)
    extra_columns = [
        "normalization_criterion",
        "normalization_row_kind",
        "normalization_group",
        "normalization_display_label",
        "normalization_weight",
        "normalization_mode",
        "normalization_unit",
        "normalization_divisor",
        "normalization_source_n_raters",
    ]
    return out[original_columns + extra_columns]


def write_outputs(df: pd.DataFrame, out_root: Path, preflight: dict[str, object]) -> None:
    for criterion in ACTIVE_CRITERIA:
        contract = GROUPING_CONTRACTS[criterion]
        criterion_dir = out_root / criterion
        criterion_dir.mkdir(parents=True, exist_ok=True)
        group_rows, tier_rows = build_group_summary(df, criterion, contract)
        confidence_rows = build_confidence_summary(df, criterion, contract)
        weighted_source_file = str(contract.get("weighted_source_file", ""))
        if weighted_source_file:
            weighted_source = build_weighted_source_master(df, criterion, contract)
            weighted_source.to_csv(criterion_dir / weighted_source_file, index=False)

        group_fields = [
            "criterion",
            "group_order",
            "group",
            "members",
            "n_tiers",
            "n_raters",
            *NORMALIZATION_COLUMNS,
            *METRIC_COLUMNS,
            "accuracy_pct",
            "accuracy_pct_label",
        ]
        tier_fields = [
            "criterion",
            "group_order",
            "group",
            "tier",
            "rater_seniority_rank",
            "n_raters",
            *NORMALIZATION_COLUMNS,
            *METRIC_COLUMNS,
            "accuracy_pct",
            "accuracy_pct_label",
        ]
        write_csv(criterion_dir / "group_summary.csv", group_rows, group_fields)
        write_csv(criterion_dir / "seniority_tier_summary.csv", tier_rows, tier_fields)
        write_csv(
            criterion_dir / "confidence_outcome_summary.csv",
            confidence_rows,
            CONFIDENCE_COLUMNS,
        )

        provenance = {
            **preflight,
            "criterion": criterion,
            "criterion_title": contract["title"],
            "base_criterion": contract.get("base_criterion", criterion),
            "normalization_mode": contract.get("normalization_mode", "raw"),
            "weighted_source_file": weighted_source_file,
            "grouping_contract": contract["groups"],
            "confidence_definitions": {
                "peak_correct_n": "score_required true, likert == 4, final_score_authoritative == 1",
                "peak_wrong_n": "score_required true, likert == 4, final_score_authoritative == 0",
                "cautious_n": "score_required true, likert in [1, 2, 3]",
                "deferred_n": "all remaining rows, including abstention, technical failure, invalid/missing Likert, and Likert 0 residuals",
                "ppv_correct_pct": "peak_correct_n / (peak_correct_n + peak_wrong_n) * 100",
            },
            "outputs": [
                "group_summary.csv",
                "seniority_tier_summary.csv",
                "confidence_outcome_summary.csv",
                "stats_provenance.json",
                *([weighted_source_file] if weighted_source_file else []),
            ],
        }
        (criterion_dir / "stats_provenance.json").write_text(
            json.dumps(provenance, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"[PASS] wrote stats {criterion_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    master = args.master.resolve()
    out_root = args.out_root.resolve()
    df, preflight = validate_preflight(master)
    write_outputs(df, out_root, preflight)
    print("[PASS] stats generation complete")


if __name__ == "__main__":
    main()
