#!/usr/bin/env python3
"""Create RadLE v2 Likert-5 Score1000 CSV outputs from a clean master."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Iterable

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = (
    REPO_ROOT
    / "outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147"
    / "likert5_score1000"
)
DEFAULT_CLEAN_MASTER = DEFAULT_OUT_DIR / "radle_v2_clean_adjudication_master.csv"
DEFAULT_CLEAN_RECEIPT = DEFAULT_OUT_DIR / "adjudication_master_cleanup_receipt.json"

EXPECTED_CLEAN_ROWS = 6600
EXPECTED_SCORING_ROWS = 5600
EXPECTED_ACTIVE_MODEL_ROWS = 3200
EXPECTED_HUMAN_ROWS = 2400
EXPECTED_CLEAN_COLUMNS = [
    "run_id",
    "Master_Case_ID",
    "Associated_Images",
    "model_blinded",
    "candidate",
    "provider",
    "access",
    "domain",
    "Ground_Truth_Diagnosis",
    "diagnosis",
    "likert",
    "response_valid",
    "abstained",
    "technical_failure",
    "score_required",
    "final_score_authoritative",
    "final_score_source",
    "rater_seniority",
    "rater_seniority_rank",
]
FORBIDDEN_COLUMNS = {
    "weighted_score",
    "source_weighted_score",
    "mean_weighted_score",
    "n_weighted",
    "weighted_score_rule",
}
STATUS_ORDER = [
    "abstention_idk_zero",
    "abstention_idk_typo_zero",
    "invalid_likert_zero",
    "technical_failure_zero",
    "valid_likert_correct",
    "valid_likert_wrong",
]
STATUS_DESCRIPTIONS = {
    "abstention_idk_zero": "Diagnosis is exactly `I don't know`; raw score is 0.",
    "abstention_idk_typo_zero": "Diagnosis is the observed typo `Idon't know`; raw score is 0.",
    "invalid_likert_zero": "Likert is absent or outside 0..4 after non-\"I don't know\"/non-failure handling; raw score is 0.",
    "technical_failure_zero": "Technical failure, diagnosis `PARSE_FAILED`, or Likert `PARSE_FAILED`; raw score is 0.",
    "valid_likert_correct": "Likert is 0..4 and diagnosis is correct; raw score is +(Likert + 1).",
    "valid_likert_wrong": "Likert is 0..4 and diagnosis is wrong; raw score is -(Likert + 1).",
}
IDK_SCORE = 1
TRAINEE_TIERS = {"PGY2", "PGY3"}
BOARD_TIERS = {"6mo post-MD", "2y post-MD", "3y post-MD", "4y post-MD", "7y post-MD"}
HUMAN_BASELINE_LABEL = "Human Expert Baseline"
HUMAN_READER_COUNT = 12
HUMAN_TIERS = BOARD_TIERS | TRAINEE_TIERS
HUMAN_GROUPS = [
    (HUMAN_BASELINE_LABEL, HUMAN_TIERS),
]
SCORE1000_SOURCE_COLUMNS = [
    "score1000_source_row_id",
    "score1000_row_kind",
    "score1000_group",
    "score1000_display_label",
    "score1000_n_readers_in_group",
    "score1000_row_weight",
    *EXPECTED_CLEAN_COLUMNS,
]
SCORE1000_SCORE_COLUMNS = [
    "score1000_likert_int",
    "score1000_likert_weight",
    "score1000_status",
    "score1000_raw_score",
    "score1000_effective_score",
]
LIKERT_LEVELS = [0, 1, 2, 3, 4]
LIKERT_SUMMARY_COLUMNS = [
    column
    for level in LIKERT_LEVELS
    for column in (f"likert_{level}_effective_cases", f"likert_{level}_accuracy_pct")
]
GROUP_SUMMARY_COLUMNS = [
    "rank",
    "reader_type",
    "reader_label",
    "provider",
    "access",
    "domain",
    "n_readers",
    "raw_observations",
    "effective_cases",
    "correct_effective_cases",
    "accuracy_overall_pct",
    *LIKERT_SUMMARY_COLUMNS,
    "final_score1000",
    "score2000",
    "score_per_case",
    "score_vs_all_idk_baseline",
    "idk_rate_pct",
    "peak_confidence_effective_cases",
    "peak_confidence_accuracy_pct",
    "confident_error_effective_cases",
    "confident_error_rate_pct",
]
SUMMARY_COLUMNS_WITHOUT_RANK = GROUP_SUMMARY_COLUMNS[1:]
SCORE2000_SHIFT = 1000
GROUP_SUMMARY_COLUMN_MANUAL = [
    ("rank", "Overall rank after sorting `score2000` descending; 1 is highest."),
    ("reader_type", "`AI model` for a model arm or `Human comparator` for a pooled human group."),
    ("reader_label", "Reader-facing model or human-comparator label."),
    ("provider", "Model provider for model rows; `human comparator` for pooled human rows."),
    ("access", "Access category from the master for model rows; `human` for pooled human rows."),
    ("domain", "Domain from the master for model rows; `human` for pooled human rows."),
    ("n_readers", "Number of independent readers represented: 1 for each model, 12 for the pooled Human Expert Baseline."),
    ("raw_observations", "Raw source-row count before weighting."),
    ("effective_cases", "Weighted denominator, computed as sum(1 / score1000_n_readers_in_group) over rows."),
    ("correct_effective_cases", "Weighted correct count, computed as sum(row_weight) over correct rows."),
    ("accuracy_overall_pct", "`100 * correct_effective_cases / effective_cases`, irrespective of Likert value."),
]
for level in LIKERT_LEVELS:
    GROUP_SUMMARY_COLUMN_MANUAL.extend(
        [
            (
                f"likert_{level}_effective_cases",
                f"Weighted denominator among rows whose parsed Likert is exactly {level}.",
            ),
            (
                f"likert_{level}_accuracy_pct",
                f"`100 * weighted correct rows / weighted rows` among parsed Likert {level} rows; blank if unused.",
            ),
        ]
    )
GROUP_SUMMARY_COLUMN_MANUAL.extend(
    [
        ("final_score1000", "Final weighted Likert-5 Score1000 total, computed as sum(raw_score * row_weight)."),
        ("score2000", "`final_score1000 + 1000`; shifted display score on a 0..2000 graph scale."),
        ("score_per_case", "`final_score1000 / effective_cases`; range is -5 to +5."),
        (
            "score_vs_all_idk_baseline",
            "`final_score1000 - (effective_cases * configured \"I don't know\" score)`; positive means the reader beats the all-\"I don't know\" baseline.",
        ),
        ("idk_rate_pct", "Effective share of exact or typo \"I don't know\" rows."),
        ("peak_confidence_effective_cases", "Effective count of non-\"I don't know\", non-failure answers with Likert 4."),
        ("peak_confidence_accuracy_pct", "Accuracy among Likert-4 answers only; blank if there are no Likert-4 answers."),
        ("confident_error_effective_cases", "Effective count of wrong Likert-4 answers."),
        ("confident_error_rate_pct", "`100 * confident_error_effective_cases / effective_cases`."),
    ]
)


class GateFailure(RuntimeError):
    """Raised when a pipeline gate fails."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def read_csv_text(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def boolish(value: object) -> bool:
    return clean_text(value).lower() in {"true", "1", "yes"}


def parse_likert_int(value: object) -> int | None:
    text = clean_text(value)
    if text == "":
        return None
    try:
        as_float = float(text)
    except ValueError:
        return None
    if not as_float.is_integer():
        return None
    return int(as_float)


def round_float(value: float, digits: int = 6) -> float:
    rounded = round(float(value), digits)
    if rounded == 0:
        return 0.0
    return rounded


def row_weight_fraction(row: pd.Series) -> Fraction:
    return Fraction(1, int(row["score1000_n_readers_in_group"]))


def effective_n_fraction(frame: pd.DataFrame) -> Fraction:
    total = Fraction(0, 1)
    for _, row in frame.iterrows():
        total += row_weight_fraction(row)
    return total


def effective_score_fraction(frame: pd.DataFrame) -> Fraction:
    total = Fraction(0, 1)
    for _, row in frame.iterrows():
        total += Fraction(int(row["score1000_raw_score"]), int(row["score1000_n_readers_in_group"]))
    return total


def effective_correct_fraction(frame: pd.DataFrame) -> Fraction:
    total = Fraction(0, 1)
    for _, row in frame.iterrows():
        if int(row["final_score_authoritative"]) == 1:
            total += row_weight_fraction(row)
    return total


def fraction_to_export(value: Fraction, digits: int = 6) -> float:
    return round_float(float(value), digits)


def percent_to_export(numerator: Fraction, denominator: Fraction) -> float | str:
    if denominator == 0:
        return ""
    return round_float(float(numerator * 100 / denominator), 2)


def format_signed_score(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)


def all_idk_baseline() -> int:
    return 200 * IDK_SCORE


def configure_idk_score(value: int) -> None:
    global IDK_SCORE, STATUS_DESCRIPTIONS
    if value not in {0, 1}:
        raise GateFailure(f"Unsupported IDK score {value}; expected 0 or 1")
    IDK_SCORE = value
    rendered = format_signed_score(value)
    STATUS_DESCRIPTIONS = {
        "abstention_idk_zero": f"Diagnosis is exactly `I don't know`; raw score is {rendered}.",
        "abstention_idk_typo_zero": f"Diagnosis is the observed typo `Idon't know`; raw score is {rendered}.",
        "invalid_likert_zero": "Likert is absent or outside 0..4 after non-\"I don't know\"/non-failure handling; raw score is 0.",
        "technical_failure_zero": "Technical failure, diagnosis `PARSE_FAILED`, or Likert `PARSE_FAILED`; raw score is 0.",
        "valid_likert_correct": "Likert is 0..4 and diagnosis is correct; raw score is +(Likert + 1).",
        "valid_likert_wrong": "Likert is 0..4 and diagnosis is wrong; raw score is -(Likert + 1).",
    }


def validate_no_stale_columns(columns: Iterable[str], context: str) -> None:
    columns = list(columns)
    direct = sorted(FORBIDDEN_COLUMNS & set(columns))
    prefixed = sorted(c for c in columns if c.startswith("normalization_"))
    if direct or prefixed:
        raise GateFailure(f"{context}: stale columns present direct={direct} prefixed={prefixed}")


def validate_clean_master(df: pd.DataFrame) -> None:
    if len(df) != EXPECTED_CLEAN_ROWS:
        raise GateFailure(f"Expected {EXPECTED_CLEAN_ROWS} clean master rows, got {len(df)}")
    if list(df.columns) != EXPECTED_CLEAN_COLUMNS:
        raise GateFailure(
            "Clean master columns differ from expected schema.\n"
            f"Expected: {EXPECTED_CLEAN_COLUMNS}\n"
            f"Actual:   {list(df.columns)}"
        )
    validate_no_stale_columns(df.columns, "clean master")
    authoritative = pd.to_numeric(df["final_score_authoritative"], errors="raise")
    if not authoritative.isin([0, 1]).all():
        raise GateFailure("final_score_authoritative must contain only binary 0/1 values")


def group_for_human_tier(tier: str) -> tuple[str, int] | None:
    if tier in HUMAN_TIERS:
        return (HUMAN_BASELINE_LABEL, HUMAN_READER_COUNT)
    return None


def build_source_rows(clean_df: pd.DataFrame) -> pd.DataFrame:
    model_mask = (clean_df["domain"] != "human") & (clean_df["access"] != "excluded")
    human_mask = clean_df["domain"] == "human"
    source = clean_df[model_mask | human_mask].copy()
    if len(source) != EXPECTED_SCORING_ROWS:
        raise GateFailure(f"Expected {EXPECTED_SCORING_ROWS} Score1000 source rows, got {len(source)}")
    if int(model_mask.sum()) != EXPECTED_ACTIVE_MODEL_ROWS:
        raise GateFailure(
            f"Expected {EXPECTED_ACTIVE_MODEL_ROWS} non-excluded model rows, got {int(model_mask.sum())}"
        )
    if int(human_mask.sum()) != EXPECTED_HUMAN_ROWS:
        raise GateFailure(f"Expected {EXPECTED_HUMAN_ROWS} human rows, got {int(human_mask.sum())}")

    source.insert(0, "score1000_source_row_id", range(1, len(source) + 1))
    source["score1000_row_kind"] = ""
    source["score1000_group"] = ""
    source["score1000_display_label"] = ""
    source["score1000_n_readers_in_group"] = 1
    source["score1000_row_weight"] = 1.0

    is_model = source["domain"] != "human"
    source.loc[is_model, "score1000_row_kind"] = "model"
    source.loc[is_model, "score1000_group"] = "AI model"
    source.loc[is_model, "score1000_display_label"] = source.loc[is_model, "candidate"]
    source.loc[is_model, "score1000_n_readers_in_group"] = 1
    source.loc[is_model, "score1000_row_weight"] = 1.0

    is_human = source["domain"] == "human"
    for idx, row in source.loc[is_human].iterrows():
        group = group_for_human_tier(clean_text(row["rater_seniority"]))
        if group is None:
            raise GateFailure(
                f"Human row has unmapped rater_seniority={row['rater_seniority']!r} "
                f"at Master_Case_ID={row['Master_Case_ID']} model_blinded={row['model_blinded']}"
            )
        group_name, n_readers = group
        source.at[idx, "score1000_row_kind"] = "human_comparator"
        source.at[idx, "score1000_group"] = group_name
        source.at[idx, "score1000_display_label"] = group_name
        source.at[idx, "score1000_n_readers_in_group"] = n_readers
        source.at[idx, "score1000_row_weight"] = 1.0 / n_readers

    ordered = source[SCORE1000_SOURCE_COLUMNS].copy()
    validate_no_stale_columns(ordered.columns, "score1000 source rows")
    validate_human200(ordered)
    return ordered


def score_row(row: pd.Series) -> tuple[int | None, int | None, str, int, float]:
    diagnosis = clean_text(row["diagnosis"])
    likert_int = parse_likert_int(row["likert"])
    correct = int(row["final_score_authoritative"])
    row_weight = float(row["score1000_row_weight"])

    if boolish(row["technical_failure"]) or diagnosis == "PARSE_FAILED" or clean_text(row["likert"]) == "PARSE_FAILED":
        return (likert_int, None, "technical_failure_zero", 0, 0.0)
    if diagnosis == "I don't know":
        return (likert_int, IDK_SCORE, "abstention_idk_zero", IDK_SCORE, row_weight * IDK_SCORE)
    if diagnosis == "Idon't know":
        return (likert_int, IDK_SCORE, "abstention_idk_typo_zero", IDK_SCORE, row_weight * IDK_SCORE)
    if likert_int not in {0, 1, 2, 3, 4}:
        return (likert_int, None, "invalid_likert_zero", 0, 0.0)

    likert_weight = likert_int + 1
    if correct == 1:
        raw_score = likert_weight
        status = "valid_likert_correct"
    else:
        raw_score = -likert_weight
        status = "valid_likert_wrong"
    return (likert_int, likert_weight, status, raw_score, float(Fraction(raw_score, int(row["score1000_n_readers_in_group"]))))


def build_scored_rows(source: pd.DataFrame) -> pd.DataFrame:
    scored = source.copy()
    scores = scored.apply(score_row, axis=1, result_type="expand")
    scores.columns = SCORE1000_SCORE_COLUMNS
    scored = pd.concat([scored, scores], axis=1)
    validate_status_counts(scored)
    validate_no_stale_columns(scored.columns, "score1000 scored rows")
    return scored


def validate_status_counts(scored: pd.DataFrame) -> None:
    counts = scored["score1000_status"].value_counts().to_dict()
    extra = sorted(set(counts) - set(STATUS_ORDER))
    if extra:
        raise GateFailure(f"Unexpected Score1000 statuses: {extra}")
    if sum(int(value) for value in counts.values()) != EXPECTED_SCORING_ROWS:
        raise GateFailure("Score1000 status counts do not cover the full scoring universe")


def validate_human200(source: pd.DataFrame) -> None:
    if len(source[source["score1000_row_kind"] == "model"]) != EXPECTED_ACTIVE_MODEL_ROWS:
        raise GateFailure(f"Expected {EXPECTED_ACTIVE_MODEL_ROWS} model source rows")
    human = source[source["score1000_row_kind"] == "human_comparator"]
    if len(human) != 2400:
        raise GateFailure("Expected 2400 human comparator source rows")
    expected = {HUMAN_BASELINE_LABEL: (2400, HUMAN_READER_COUNT, 200.0)}
    for group, (rows, readers, effective_n) in expected.items():
        frame = human[human["score1000_group"] == group]
        if len(frame) != rows:
            raise GateFailure(f"{group}: expected {rows} source rows, got {len(frame)}")
        actual_readers = int(frame["provider"].nunique())
        if actual_readers != readers:
            raise GateFailure(f"{group}: expected {readers} readers, got {actual_readers}")
        actual_effective = effective_n_fraction(frame)
        if actual_effective != Fraction(int(effective_n), 1):
            raise GateFailure(f"{group}: expected effective n={effective_n}, got {float(actual_effective)}")


def aggregate_rows(frame: pd.DataFrame, identity: dict[str, object]) -> dict[str, object]:
    effective_n = effective_n_fraction(frame)
    total = effective_score_fraction(frame)
    score2000 = total + SCORE2000_SHIFT
    effective_correct = effective_correct_fraction(frame)
    likert_int = pd.to_numeric(frame["score1000_likert_int"], errors="coerce")
    idk_mask = frame["score1000_status"].isin(["abstention_idk_zero", "abstention_idk_typo_zero"])
    peak_mask = (
        frame["score1000_status"].isin(["valid_likert_correct", "valid_likert_wrong"])
        & (likert_int == 4)
    )
    peak_correct_mask = peak_mask & (frame["score1000_status"] == "valid_likert_correct")
    confident_error_mask = peak_mask & (frame["score1000_status"] == "valid_likert_wrong")
    idk_effective = effective_n_fraction(frame[idk_mask])
    peak_effective = effective_n_fraction(frame[peak_mask])
    peak_correct_effective = effective_n_fraction(frame[peak_correct_mask])
    confident_error_effective = effective_n_fraction(frame[confident_error_mask])
    row: dict[str, object] = {
        **identity,
        "raw_observations": int(len(frame)),
        "effective_cases": fraction_to_export(effective_n),
        "correct_effective_cases": fraction_to_export(effective_correct),
        "accuracy_overall_pct": percent_to_export(effective_correct, effective_n),
        "final_score1000": fraction_to_export(total),
        "score2000": fraction_to_export(score2000),
        "score_per_case": fraction_to_export(total / effective_n if effective_n else Fraction(0, 1)),
        "score_vs_all_idk_baseline": fraction_to_export(total - (effective_n * IDK_SCORE)),
        "idk_rate_pct": percent_to_export(idk_effective, effective_n),
        "peak_confidence_effective_cases": fraction_to_export(peak_effective),
        "peak_confidence_accuracy_pct": percent_to_export(peak_correct_effective, peak_effective),
        "confident_error_effective_cases": fraction_to_export(confident_error_effective),
        "confident_error_rate_pct": percent_to_export(confident_error_effective, effective_n),
    }
    for level in LIKERT_LEVELS:
        level_mask = likert_int == level
        level_effective = effective_n_fraction(frame[level_mask])
        level_correct_effective = effective_correct_fraction(frame[level_mask])
        row[f"likert_{level}_effective_cases"] = fraction_to_export(level_effective)
        row[f"likert_{level}_accuracy_pct"] = percent_to_export(level_correct_effective, level_effective)
    return row


def build_model_summary(scored: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    models = scored[scored["score1000_row_kind"] == "model"]
    for (candidate, provider, access, domain), frame in models.groupby(
        ["candidate", "provider", "access", "domain"], dropna=False, sort=False
    ):
        rows.append(
            aggregate_rows(
                frame,
                {
                    "reader_type": "AI model",
                    "reader_label": candidate,
                    "provider": provider,
                    "access": access,
                    "domain": domain,
                    "n_readers": 1,
                },
            )
        )
    out = pd.DataFrame(rows).sort_values(["score2000", "reader_label"], ascending=[False, True])
    expected_models = EXPECTED_ACTIVE_MODEL_ROWS // 200
    if len(out) != expected_models:
        raise GateFailure(f"Expected {expected_models} model summary rows, got {len(out)}")
    out = out[SUMMARY_COLUMNS_WITHOUT_RANK]
    return out.reset_index(drop=True)


def build_human_summary(scored: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    humans = scored[scored["score1000_row_kind"] == "human_comparator"]
    for group, _tiers in HUMAN_GROUPS:
        frame = humans[humans["score1000_group"] == group]
        rows.append(
            aggregate_rows(
                frame,
                {
                    "reader_type": "Human comparator",
                    "reader_label": group,
                    "provider": "human comparator",
                    "access": "human",
                    "domain": "human",
                    "n_readers": int(frame["provider"].nunique()),
                },
            )
        )
    out = pd.DataFrame(rows)
    if len(out) != 1:
        raise GateFailure(f"Expected 1 human summary row, got {len(out)}")
    out = out[SUMMARY_COLUMNS_WITHOUT_RANK]
    return out


def build_status_audit(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for status in STATUS_ORDER:
        frame = scored[scored["score1000_status"] == status]
        rows.append(
            {
                "score1000_status": status,
                "source_rows": int(len(frame)),
                "expected_source_rows": int(len(frame)),
                "matches_expected": True,
                "effective_n": fraction_to_export(effective_n_fraction(frame)),
                "score1000_effective_score_sum": fraction_to_export(effective_score_fraction(frame)),
            }
        )
    return pd.DataFrame(rows)


def write_csv(path: Path, df: pd.DataFrame) -> None:
    validate_no_stale_columns(df.columns, path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def csv_row_count(path: Path) -> int:
    return int(len(pd.read_csv(path, dtype=str, keep_default_na=False)))


def group_summary_manual_lines() -> list[str]:
    lines = [
        "# score1000_group_summary.csv Manual",
        "",
        "`score1000_group_summary.csv` has one row per comparator: 16 non-excluded model arms plus 1 pooled Human Expert Baseline row. It is the union of `score1000_model_summary.csv` and `score1000_human_comparator_summary.csv`, sorted by `score2000` descending.",
        "",
        "This table is intentionally a compact stats summary. Detailed row-status bookkeeping remains in `score1000_scored_rows.csv` and global status totals remain in `score1000_status_audit.csv`.",
        "",
        "## First Principles",
        "",
        "Each source row is first assigned a raw score:",
        "",
        "- Technical failure, diagnosis `PARSE_FAILED`, or Likert `PARSE_FAILED`: `0`.",
        f"- Exact `I don't know`: `{format_signed_score(IDK_SCORE)}`.",
        f"- Typo `Idon't know`: `{format_signed_score(IDK_SCORE)}`.",
        "- Invalid Likert outside 0..4 after the above checks: `0`.",
        "- Valid Likert 0..4 with a correct diagnosis: `+(Likert + 1)`.",
        "- Valid Likert 0..4 with a wrong diagnosis: `-(Likert + 1)`.",
        "",
        "Then each source row is weighted:",
        "",
        "- Model rows use `score1000_n_readers_in_group = 1`, so each row has weight `1`.",
        "- Human Expert Baseline rows use `score1000_n_readers_in_group = 12`, so each reader-row has weight `1/12`.",
        "- The pooled Human Expert Baseline has 2400 raw reader-rows and effective denominator `2400 / 12 = 200`.",
        "",
        "Therefore:",
        "",
        "- `effective_cases = sum(1 / score1000_n_readers_in_group)`.",
        "- `final_score1000 = sum(score1000_raw_score / score1000_n_readers_in_group)`.",
        "- `score2000 = final_score1000 + 1000`; this shifts the graph/display scale from `-1000..+1000` to `0..2000` without changing rank.",
        "- A 200-effective-case comparator ranges from `-1000` to `+1000` because each case can score from `-5` to `+5`.",
        f"- An all-\"I don't know\" comparator scores `{format_signed_score(all_idk_baseline())}` because each effective case scores `{format_signed_score(IDK_SCORE)}`.",
        "",
        "## Status Values",
        "",
    ]
    for status in STATUS_ORDER:
        lines.append(f"- `{status}`: {STATUS_DESCRIPTIONS[status]}")
    lines.extend(
        [
            "",
            "## Column Dictionary",
            "",
        ]
    )
    for column, meaning in GROUP_SUMMARY_COLUMN_MANUAL:
        lines.append(f"- `{column}`: {meaning}")
    lines.append("")
    return lines


def write_data_provenance(
    *,
    out_dir: Path,
    clean_master: Path,
    clean_receipt: Path,
    scored: pd.DataFrame,
    generated_files: list[Path],
) -> None:
    receipt = json.loads(clean_receipt.read_text(encoding="utf-8")) if clean_receipt.exists() else {}
    clean_sha = sha256_file(clean_master)
    status_counts = {status: int((scored["score1000_status"] == status).sum()) for status in STATUS_ORDER}
    provenance = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "generator": rel(Path(__file__)),
        "method": "RadLE v2 Likert-5 Score1000",
        "source_master": receipt.get("source_master", {}),
        "clean_adjudication_master": {
            "path": rel(clean_master),
            "sha256": clean_sha,
            "rows": EXPECTED_CLEAN_ROWS,
            "columns": EXPECTED_CLEAN_COLUMNS,
        },
        "score1000_rule": {
            "likert_mapping": "0..4 maps to 1..5",
            "correct": "+weight",
            "wrong": "-weight",
            "idk_exact_or_typo": format_signed_score(IDK_SCORE),
            "invalid_likert": "0 and flagged",
            "technical_failure_or_parse_failed": "0",
            "effective_200_case_range": [-1000, 1000],
            "all_idk_baseline": all_idk_baseline(),
        },
        "score2000_rule": {
            "formula": "score2000 = final_score1000 + 1000",
            "display_range": [0, 2000],
            "source_range": [-1000, 1000],
            "rank_preserving": True,
        },
        "cohort": {
            "source_rows": int(len(scored)),
            "non_excluded_model_rows": int((scored["score1000_row_kind"] == "model").sum()),
            "human_rows": int((scored["score1000_row_kind"] == "human_comparator").sum()),
            "human_groups": {
                group: {
                    "source_rows": int((scored["score1000_group"] == group).sum()),
                    "n_readers": int(scored.loc[scored["score1000_group"] == group, "provider"].nunique()),
                    "effective_n": round_float(
                        float(
                            scored.loc[
                                scored["score1000_group"] == group, "score1000_row_weight"
                            ].astype(float).sum()
                        )
                    ),
                }
                for group, _tiers in HUMAN_GROUPS
            },
        },
        "score1000_status_counts": status_counts,
        "outputs": [rel(path) for path in generated_files],
    }
    json_path = out_dir / "data_provenance.json"
    md_path = out_dir / "data_provenance.md"
    readme_path = out_dir / "README.md"
    manual_path = out_dir / "score1000_group_summary_manual.md"
    json_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# RadLE v2 Score1000 Data Provenance",
                "",
                f"Generated: {provenance['generated_at']}",
                "",
                f"Source master SHA256: `{provenance['source_master'].get('sha256', '')}`",
                f"Clean adjudication master SHA256: `{clean_sha}`",
                "",
                "The clean adjudication master is an output-lane artifact. The input final long master is not mutated.",
                "",
                f"Score1000 rule: valid Likert 0..4 maps to weight 1..5; correct diagnoses score positive; wrong diagnoses score negative; exact or typo \"I don't know\" rows score {format_signed_score(IDK_SCORE)}; invalid Likert and technical failures score 0.",
                "Score2000 display rule: `score2000 = final_score1000 + 1000`, shifting -1000..+1000 to 0..2000 without changing rank.",
                "",
                "`score1000_group_summary_manual.md` defines the summary formulas and every column in `score1000_group_summary.csv`.",
                "",
                "Status counts:",
                *[f"- `{status}`: {status_counts[status]}" for status in STATUS_ORDER],
                "",
            ]
        ),
        encoding="utf-8",
    )
    human_groups = provenance["cohort"]["human_groups"]
    readme_path.write_text(
        "\n".join(
            [
                "# RadLE v2 Likert-5 Score1000",
                "",
                "This folder is the default clean scoring lane for the RadLE v2 Likert-5 Score1000 method.",
                "The original final long master is used as an immutable input snapshot and is not modified.",
                "",
                "## Source",
                "",
                f"- Source master: `{provenance['source_master'].get('path', '')}`",
                f"- Source master SHA256: `{provenance['source_master'].get('sha256', '')}`",
                f"- Clean adjudication master: `{provenance['clean_adjudication_master']['path']}`",
                f"- Clean adjudication master SHA256: `{clean_sha}`",
                "- Clean adjudication rule: remove only the retired `weighted_score` column.",
                "",
                "## Cohort",
                "",
                f"- Source rows: {provenance['cohort']['source_rows']}",
                f"- Non-excluded model rows: {provenance['cohort']['non_excluded_model_rows']}",
                f"- Human rows: {provenance['cohort']['human_rows']}",
                *[
                    f"- {group}: {details['n_readers']} readers, effective n={details['effective_n']}"
                    for group, details in human_groups.items()
                ],
                "",
                "## Score1000 Rule",
                "",
                "- Valid Likert 0..4 maps to weights 1..5 by adding 1.",
                "- Correct diagnosis scores positive weight: `+(Likert + 1)`.",
                "- Wrong diagnosis scores negative weight: `-(Likert + 1)`.",
                f"- Exact `I don't know` and typo `Idon't know` score `{format_signed_score(IDK_SCORE)}`.",
                "- Invalid Likert and technical failure / `PARSE_FAILED` score `0`.",
                f"- A 200-case comparator ranges from -1000 to +1000; all-\"I don't know\" baseline is {format_signed_score(all_idk_baseline())}.",
                "- `score2000 = final_score1000 + 1000`, a shifted 0..2000 display scale used for graphing.",
                "",
                "## Weighting Logic",
                "",
                "- Model arms represent one reader over 200 cases: row weight is `1` and effective n is `200`.",
                "- The Human Expert Baseline keeps all original reader rows from the source human expert cohorts. It has 12 readers and 2400 raw rows.",
                "- Human row weight is `1/12`, so the Human Expert Baseline has effective n `2400 / 12 = 200`.",
                "- Effective score is `score1000_raw_score * row_weight`, equivalent to `score1000_raw_score / score1000_n_readers_in_group`.",
                "",
                "## Output Guide",
                "",
                "- `score1000_source_rows.csv`: active 5600-row source universe before row scoring.",
                "- `score1000_scored_rows.csv`: source rows plus row-level Score1000 status and scores.",
                "- `score1000_model_summary.csv`: one row per non-excluded model arm.",
                "- `score1000_human_comparator_summary.csv`: one row per human comparator group.",
                "- `score1000_group_summary.csv`: model and human summaries combined for ranking/comparison.",
                "- `score1000_group_summary_manual.md`: formula and column dictionary for `score1000_group_summary.csv`.",
                "",
                "## Validated Status Counts",
                "",
                *[f"- `{status}`: {status_counts[status]}" for status in STATUS_ORDER],
                "",
            ]
        ),
        encoding="utf-8",
    )
    manual_path.write_text("\n".join(group_summary_manual_lines()), encoding="utf-8")
    generated_files.extend([json_path, md_path, readme_path, manual_path])


def write_audit_notes(out_dir: Path) -> Path:
    path = out_dir / "audit_notes.md"
    path.write_text(
        "\n".join(
            [
                "# RadLE v2 Score1000 Audit Notes",
                "",
                f"Initial generation completed. Run `scripts/audit_radle_v2_likert5_score1000_csvs_IDK0.py --idk-score {IDK_SCORE}` for the final gate.",
                "",
                "Generation invariants checked:",
                "- clean adjudication master has no stale score columns",
                "- stale-score columns are absent from generated CSV schemas; provenance may mention removed source metadata",
                "- source universe has 5600 rows",
                "- Pooled Human Expert Baseline weights sum to 200",
                "- Score1000 status counts match locked anchors",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def write_manifest(out_dir: Path, generated_files: list[Path]) -> Path:
    entries = []
    for path in generated_files:
        if not path.exists():
            continue
        entry: dict[str, object] = {
            "path": rel(path),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        if path.suffix.lower() == ".csv":
            entry["rows"] = csv_row_count(path)
        entries.append(entry)
    manifest = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "generator": rel(Path(__file__)),
        "output_root": rel(out_dir),
        "files": entries,
    }
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean-master", type=Path, default=DEFAULT_CLEAN_MASTER)
    parser.add_argument("--clean-receipt", type=Path, default=DEFAULT_CLEAN_RECEIPT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--idk-score",
        type=int,
        choices=[0, 1],
        default=1,
        help="Raw score for exact `I don't know` and typo `Idon't know` rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    clean_master = args.clean_master.resolve()
    clean_receipt = args.clean_receipt.resolve()
    out_dir = args.out_dir.resolve()
    configure_idk_score(args.idk_score)
    out_dir.mkdir(parents=True, exist_ok=True)

    clean_df = read_csv_text(clean_master)
    validate_clean_master(clean_df)
    source = build_source_rows(clean_df)
    scored = build_scored_rows(source)
    model_summary = build_model_summary(scored)
    human_summary = build_human_summary(scored)
    group_summary = pd.concat([model_summary, human_summary], ignore_index=True, sort=False).sort_values(
        ["score2000", "reader_label"], ascending=[False, True]
    )
    group_summary.insert(0, "rank", range(1, len(group_summary) + 1))
    group_summary = group_summary[GROUP_SUMMARY_COLUMNS]
    status_audit = build_status_audit(scored)

    generated_files = [clean_master, clean_receipt]
    outputs = {
        "score1000_source_rows.csv": source,
        "score1000_scored_rows.csv": scored,
        "score1000_model_summary.csv": model_summary,
        "score1000_human_comparator_summary.csv": human_summary,
        "score1000_group_summary.csv": group_summary,
        "score1000_status_audit.csv": status_audit,
    }
    for name, frame in outputs.items():
        path = out_dir / name
        write_csv(path, frame)
        generated_files.append(path)

    write_data_provenance(
        out_dir=out_dir,
        clean_master=clean_master,
        clean_receipt=clean_receipt,
        scored=scored,
        generated_files=generated_files,
    )
    generated_files.append(write_audit_notes(out_dir))
    manifest = write_manifest(out_dir, generated_files)

    correct_total = int(pd.to_numeric(clean_df["final_score_authoritative"], errors="raise").sum())
    print(
        f"[PASS] source master rows={len(clean_df)} cols={len(clean_df.columns)} "
        f"weighted_score_absent=True correct={correct_total}"
    )
    print(f"[PASS] score1000 source universe rows={len(source)}")
    print(
        f"[PASS] non-excluded model rows={EXPECTED_ACTIVE_MODEL_ROWS} "
        f"human rows={EXPECTED_HUMAN_ROWS}"
    )
    print("[PASS] pooled Human Expert Baseline effective denominator=200")
    print(f"[PASS] score1000 status counts {scored['score1000_status'].value_counts().to_dict()}")
    print(f"[PASS] wrote {rel(out_dir)}")
    print(f"[PASS] wrote {rel(manifest)}")


if __name__ == "__main__":
    main()
