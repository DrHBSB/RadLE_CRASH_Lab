#!/usr/bin/env python3
"""Audit the RadLE v2 Likert-5 Score1000 output lane."""

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
EXPECTED_SOURCE_SHA256 = "7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED"
EXPECTED_SOURCE_COLUMNS = [
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
    "weighted_score",
    "rater_seniority",
    "rater_seniority_rank",
]
EXPECTED_CLEAN_COLUMNS = [c for c in EXPECTED_SOURCE_COLUMNS if c != "weighted_score"]
FORBIDDEN_COLUMNS = {
    "weighted_score",
    "source_weighted_score",
    "mean_weighted_score",
    "n_weighted",
    "weighted_score_rule",
}
STATUS_ORDER = [
    "abstention_idk_reward",
    "abstention_idk_typo_reward",
    "invalid_likert_zero",
    "technical_failure_zero",
    "valid_likert_correct",
    "valid_likert_wrong",
]
EXPECTED_STATUS_COUNTS = {
    "abstention_idk_reward": 688,
    "abstention_idk_typo_reward": 5,
    "invalid_likert_zero": 1,
    "technical_failure_zero": 10,
    "valid_likert_correct": 1224,
    "valid_likert_wrong": 3472,
}
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
    "score_per_case",
    "score_vs_all_idk_baseline",
    "idk_rate_pct",
    "peak_confidence_effective_cases",
    "peak_confidence_accuracy_pct",
    "confident_error_effective_cases",
    "confident_error_rate_pct",
]
SUMMARY_COLUMNS_WITHOUT_RANK = GROUP_SUMMARY_COLUMNS[1:]
REQUIRED_FILES = [
    "radle_v2_clean_adjudication_master.csv",
    "adjudication_master_cleanup_receipt.json",
    "score1000_source_rows.csv",
    "score1000_scored_rows.csv",
    "score1000_group_summary.csv",
    "score1000_model_summary.csv",
    "score1000_human_comparator_summary.csv",
    "score1000_status_audit.csv",
    "data_provenance.json",
    "data_provenance.md",
    "README.md",
    "score1000_group_summary_manual.md",
    "audit_notes.md",
    "manifest.json",
]
CSV_FILES = [name for name in REQUIRED_FILES if name.endswith(".csv")]
AUDIT_REPORT_JSON = "score1000_audit_report.json"
AUDIT_REPORT_MD = "score1000_audit_report.md"


class AuditFailure(RuntimeError):
    """Raised when an audit gate fails."""


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


def resolve_recorded_path(recorded: str) -> Path:
    path = Path(recorded)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


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


def close_enough(actual: object, expected: object, tol: float = 1e-6) -> bool:
    return abs(float(actual) - float(expected)) <= tol


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


def validate_no_stale_columns(columns: Iterable[str], context: str) -> None:
    columns = list(columns)
    direct = sorted(FORBIDDEN_COLUMNS & set(columns))
    prefixed = sorted(c for c in columns if c.startswith("normalization_"))
    if direct or prefixed:
        raise AuditFailure(f"{context}: stale columns present direct={direct} prefixed={prefixed}")


def expected_score(row: pd.Series) -> tuple[int | None, int | None, str, int, float]:
    diagnosis = clean_text(row["diagnosis"])
    likert_int = parse_likert_int(row["likert"])
    row_weight = float(row["score1000_row_weight"])
    correct = int(row["final_score_authoritative"])
    if boolish(row["technical_failure"]) or diagnosis == "PARSE_FAILED" or clean_text(row["likert"]) == "PARSE_FAILED":
        return (likert_int, None, "technical_failure_zero", 0, 0.0)
    if diagnosis == "I don't know":
        return (likert_int, 1, "abstention_idk_reward", 1, row_weight)
    if diagnosis == "Idon't know":
        return (likert_int, 1, "abstention_idk_typo_reward", 1, row_weight)
    if likert_int not in {0, 1, 2, 3, 4}:
        return (likert_int, None, "invalid_likert_zero", 0, 0.0)
    likert_weight = likert_int + 1
    raw_score = likert_weight if correct == 1 else -likert_weight
    status = "valid_likert_correct" if correct == 1 else "valid_likert_wrong"
    return (likert_int, likert_weight, status, raw_score, float(Fraction(raw_score, int(row["score1000_n_readers_in_group"]))))


def validate_required_files(out_dir: Path) -> None:
    missing = [name for name in REQUIRED_FILES if not (out_dir / name).exists()]
    if missing:
        raise AuditFailure(f"Missing required output files: {missing}")
    visual_files = [p.name for p in out_dir.iterdir() if p.suffix.lower() in {".svg", ".html", ".png"}]
    if visual_files:
        raise AuditFailure(f"Score1000 lane must not contain generated visual artifacts: {visual_files}")


def validate_clean_master(out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    clean_path = out_dir / "radle_v2_clean_adjudication_master.csv"
    receipt_path = out_dir / "adjudication_master_cleanup_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    source_path = resolve_recorded_path(str(receipt["source_master"]["path"]))
    if not source_path.exists():
        raise AuditFailure(f"Recorded source master does not exist: {source_path}")
    source_sha = sha256_file(source_path)
    if source_sha != EXPECTED_SOURCE_SHA256:
        raise AuditFailure(f"Source master SHA mismatch: expected {EXPECTED_SOURCE_SHA256}, got {source_sha}")
    if str(receipt["source_master"]["sha256"]).upper() != EXPECTED_SOURCE_SHA256:
        raise AuditFailure("Receipt source SHA does not match locked source SHA")

    source = read_csv_text(source_path)
    clean = read_csv_text(clean_path)
    if list(source.columns) != EXPECTED_SOURCE_COLUMNS:
        raise AuditFailure("Source columns no longer match the locked input snapshot")
    if list(clean.columns) != EXPECTED_CLEAN_COLUMNS:
        raise AuditFailure("Clean master columns do not match expected adjudication schema")
    if len(source) != 6000 or len(clean) != 6000:
        raise AuditFailure(f"Expected 6000 source/clean rows, got {len(source)}/{len(clean)}")
    if int(pd.to_numeric(clean["final_score_authoritative"], errors="raise").sum()) != 1255:
        raise AuditFailure("Clean master correctness total is not 1255")
    validate_no_stale_columns(clean.columns, "clean master")
    if list(map(tuple, source[["Master_Case_ID", "model_blinded"]].to_numpy())) != list(
        map(tuple, clean[["Master_Case_ID", "model_blinded"]].to_numpy())
    ):
        raise AuditFailure("Clean master key order differs from source snapshot")
    if not clean.equals(source[EXPECTED_CLEAN_COLUMNS]):
        raise AuditFailure("Clean master changed non-score source values")
    if str(receipt["clean_adjudication_master"]["sha256"]).upper() != sha256_file(clean_path):
        raise AuditFailure("Receipt clean SHA does not match current clean master")
    if receipt.get("removed_columns") != ["weighted_score"]:
        raise AuditFailure(f"Expected removed_columns ['weighted_score'], got {receipt.get('removed_columns')}")
    return source, clean, receipt


def validate_csv_schemas(out_dir: Path) -> dict[str, pd.DataFrame]:
    frames = {}
    for name in CSV_FILES:
        frame = read_csv_text(out_dir / name)
        validate_no_stale_columns(frame.columns, name)
        frames[name] = frame
    return frames


def validate_source_and_scored(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    source = frames["score1000_source_rows.csv"]
    scored = frames["score1000_scored_rows.csv"]
    if len(source) != 5400 or len(scored) != 5400:
        raise AuditFailure(f"Expected 5400 source/scored rows, got {len(source)}/{len(scored)}")
    if list(source["score1000_source_row_id"]) != list(scored["score1000_source_row_id"]):
        raise AuditFailure("Source and scored row ids differ")
    row_kind_counts = scored["score1000_row_kind"].value_counts().to_dict()
    if row_kind_counts.get("model", 0) != 3000 or row_kind_counts.get("human_comparator", 0) != 2400:
        raise AuditFailure(f"Unexpected row_kind counts: {row_kind_counts}")
    model = scored[scored["score1000_row_kind"] == "model"]
    if not (model["score1000_row_weight"].astype(float) == 1.0).all():
        raise AuditFailure("Model row weights are not all 1")
    human = scored[scored["score1000_row_kind"] == "human_comparator"]
    for group in ("Board-certified radiologists", "Radiology trainees"):
        frame = human[human["score1000_group"] == group]
        if len(frame) != 1200:
            raise AuditFailure(f"{group}: expected 1200 source rows, got {len(frame)}")
        if frame["provider"].nunique() != 6:
            raise AuditFailure(f"{group}: expected 6 readers, got {frame['provider'].nunique()}")
        if not close_enough(frame["score1000_row_weight"].astype(float).sum(), 200.0):
            raise AuditFailure(f"{group}: effective denominator does not sum to 200")

    expected = scored.apply(expected_score, axis=1, result_type="expand")
    expected.columns = [
        "expected_likert_int",
        "expected_likert_weight",
        "expected_status",
        "expected_raw_score",
        "expected_effective_score",
    ]
    for col, expected_col in [
        ("score1000_status", "expected_status"),
        ("score1000_raw_score", "expected_raw_score"),
    ]:
        if list(scored[col].astype(str)) != list(expected[expected_col].astype(str)):
            raise AuditFailure(f"Scored column {col} does not match independent audit calculation")
    for idx, (actual, expected_value) in enumerate(
        zip(scored["score1000_effective_score"].astype(float), expected["expected_effective_score"].astype(float))
    ):
        if not close_enough(actual, expected_value):
            raise AuditFailure(f"Effective score mismatch at scored row {idx + 1}: {actual} vs {expected_value}")

    counts = scored["score1000_status"].value_counts().to_dict()
    for status, expected_count in EXPECTED_STATUS_COUNTS.items():
        if int(counts.get(status, 0)) != expected_count:
            raise AuditFailure(f"{status}: expected {expected_count}, got {counts.get(status, 0)}")
    extra = sorted(set(counts) - set(EXPECTED_STATUS_COUNTS))
    if extra:
        raise AuditFailure(f"Unexpected Score1000 statuses: {extra}")
    return scored


def aggregate(frame: pd.DataFrame) -> dict[str, float | int | str]:
    effective_n = effective_n_fraction(frame)
    total = effective_score_fraction(frame)
    effective_correct = effective_correct_fraction(frame)
    likert_int = pd.to_numeric(frame["score1000_likert_int"], errors="coerce")
    idk_mask = frame["score1000_status"].isin(["abstention_idk_reward", "abstention_idk_typo_reward"])
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
    row: dict[str, float | int | str] = {
        "raw_observations": int(len(frame)),
        "effective_cases": fraction_to_export(effective_n),
        "correct_effective_cases": fraction_to_export(effective_correct),
        "accuracy_overall_pct": percent_to_export(effective_correct, effective_n),
        "final_score1000": fraction_to_export(total),
        "score_per_case": fraction_to_export(total / effective_n if effective_n else Fraction(0, 1)),
        "score_vs_all_idk_baseline": fraction_to_export(total - effective_n),
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


def validate_summary_row(row: pd.Series, frame: pd.DataFrame, context: str) -> None:
    expected = aggregate(frame)
    for field, expected_value in expected.items():
        actual = row[field]
        if expected_value == "":
            if clean_text(actual) != "":
                raise AuditFailure(f"{context} {field}: expected blank, got {actual}")
        elif isinstance(expected_value, int):
            if int(float(actual)) != expected_value:
                raise AuditFailure(f"{context} {field}: expected {expected_value}, got {actual}")
        elif not close_enough(actual, expected_value):
            raise AuditFailure(f"{context} {field}: expected {expected_value}, got {actual}")


def validate_summaries(frames: dict[str, pd.DataFrame], scored: pd.DataFrame) -> None:
    model_summary = frames["score1000_model_summary.csv"]
    human_summary = frames["score1000_human_comparator_summary.csv"]
    group_summary = frames["score1000_group_summary.csv"]
    if len(model_summary) != 15:
        raise AuditFailure(f"Expected 15 model summary rows, got {len(model_summary)}")
    if len(human_summary) != 2:
        raise AuditFailure(f"Expected 2 human summary rows, got {len(human_summary)}")
    if len(group_summary) != 17:
        raise AuditFailure(f"Expected 17 group summary rows, got {len(group_summary)}")
    if list(model_summary.columns) != SUMMARY_COLUMNS_WITHOUT_RANK:
        raise AuditFailure("Model summary columns do not match the compact stats schema")
    if list(human_summary.columns) != SUMMARY_COLUMNS_WITHOUT_RANK:
        raise AuditFailure("Human summary columns do not match the compact stats schema")
    if list(group_summary.columns) != GROUP_SUMMARY_COLUMNS:
        raise AuditFailure("Group summary columns do not match the compact stats schema")

    for _, row in model_summary.iterrows():
        frame = scored[
            (scored["score1000_row_kind"] == "model")
            & (scored["candidate"] == row["reader_label"])
            & (scored["provider"] == row["provider"])
            & (scored["access"] == row["access"])
            & (scored["domain"] == row["domain"])
        ]
        validate_summary_row(row, frame, f"model {row['reader_label']}/{row['provider']}")

    for _, row in human_summary.iterrows():
        frame = scored[
            (scored["score1000_row_kind"] == "human_comparator")
            & (scored["score1000_group"] == row["reader_label"])
        ]
        validate_summary_row(row, frame, f"human {row['reader_label']}")

    combined = pd.concat([model_summary, human_summary], ignore_index=True, sort=False)
    group_keys = set(zip(group_summary["reader_type"], group_summary["reader_label"]))
    combined_keys = set(zip(combined["reader_type"], combined["reader_label"]))
    if group_keys != combined_keys:
        raise AuditFailure("Group summary rows do not match model + human summary rows")
    expected_rank = list(range(1, len(group_summary) + 1))
    actual_rank = [int(value) for value in group_summary["rank"]]
    if actual_rank != expected_rank:
        raise AuditFailure(f"Group summary rank is not consecutive: {actual_rank}")
    for _, row in group_summary.iterrows():
        key_match = combined[
            (combined["reader_type"] == row["reader_type"])
            & (combined["reader_label"] == row["reader_label"])
        ]
        if len(key_match) != 1:
            raise AuditFailure(f"Group summary row has no unique combined match: {row['reader_label']}")
        for column in SUMMARY_COLUMNS_WITHOUT_RANK:
            if clean_text(row[column]) != clean_text(key_match.iloc[0][column]):
                raise AuditFailure(f"Group summary {row['reader_label']} column {column} differs from component summary")


def validate_status_audit(frames: dict[str, pd.DataFrame], scored: pd.DataFrame) -> None:
    audit = frames["score1000_status_audit.csv"]
    if list(audit["score1000_status"]) != STATUS_ORDER:
        raise AuditFailure("Status audit row order mismatch")
    for _, row in audit.iterrows():
        status = row["score1000_status"]
        frame = scored[scored["score1000_status"] == status]
        if int(row["source_rows"]) != EXPECTED_STATUS_COUNTS[status]:
            raise AuditFailure(f"Status audit source_rows mismatch for {status}")
        if clean_text(row["matches_expected"]).lower() != "true":
            raise AuditFailure(f"Status audit matches_expected is not true for {status}")
        if not close_enough(row["effective_n"], fraction_to_export(effective_n_fraction(frame))):
            raise AuditFailure(f"Status audit effective_n mismatch for {status}")
        if not close_enough(
            row["score1000_effective_score_sum"],
            fraction_to_export(effective_score_fraction(frame)),
        ):
            raise AuditFailure(f"Status audit score sum mismatch for {status}")


def validate_provenance(out_dir: Path, scored: pd.DataFrame) -> None:
    data = json.loads((out_dir / "data_provenance.json").read_text(encoding="utf-8"))
    if str(data["source_master"]["sha256"]).upper() != EXPECTED_SOURCE_SHA256:
        raise AuditFailure("Data provenance source SHA mismatch")
    if str(data["clean_adjudication_master"]["sha256"]).upper() != sha256_file(
        out_dir / "radle_v2_clean_adjudication_master.csv"
    ):
        raise AuditFailure("Data provenance clean SHA mismatch")
    for status, expected_count in EXPECTED_STATUS_COUNTS.items():
        if int(data["score1000_status_counts"][status]) != expected_count:
            raise AuditFailure(f"Data provenance status count mismatch for {status}")
    if int(data["cohort"]["source_rows"]) != len(scored):
        raise AuditFailure("Data provenance source row count mismatch")


def validate_manifest(out_dir: Path) -> None:
    data = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    generator = str(data.get("generator", "")).replace("/", "\\")
    if generator != "scripts\\make_radle_v2_likert5_score1000_csvs.py":
        raise AuditFailure(f"Manifest was not generated by the Score1000 maker: {data.get('generator')}")
    by_path = {entry["path"]: entry for entry in data["files"]}
    expected_paths = {rel(out_dir / name) for name in REQUIRED_FILES if name != "manifest.json"}
    actual_paths = set(by_path)
    if actual_paths != expected_paths:
        raise AuditFailure(
            "Manifest entries differ from generator outputs.\n"
            f"Expected: {sorted(expected_paths)}\n"
            f"Actual:   {sorted(actual_paths)}"
        )
    for name in REQUIRED_FILES:
        if name == "manifest.json":
            continue
        path = out_dir / name
        key = rel(path)
        if key not in by_path:
            raise AuditFailure(f"Manifest missing {key}")
        if str(by_path[key]["sha256"]).upper() != sha256_file(path):
            raise AuditFailure(f"Manifest SHA mismatch for {key}")


def write_audit_report(out_dir: Path, scored: pd.DataFrame) -> None:
    human = scored[scored["score1000_row_kind"] == "human_comparator"]
    human_totals = {
        group: fraction_to_export(effective_score_fraction(human[human["score1000_group"] == group]))
        for group in ("Board-certified radiologists", "Radiology trainees")
    }
    report = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "generator": rel(Path(__file__)),
        "audited_output_root": rel(out_dir),
        "result": "pass",
        "read_only_generated_artifacts": True,
        "validated_generator_manifest": rel(out_dir / "manifest.json"),
        "stale_score_gate_scope": "CSV schemas and row-level/summary data; provenance may mention removed source metadata.",
        "human_comparator_score1000_totals": human_totals,
        "checks": [
            "preflight clean adjudication master and source snapshot",
            "stale-score CSV schema gate",
            "cohort and Human200 denominator gate",
            "Score1000 row-status and score-rule gate",
            "summary field reconciliation gate",
            "provenance gate",
            "generator manifest gate",
        ],
    }
    json_path = out_dir / AUDIT_REPORT_JSON
    md_path = out_dir / AUDIT_REPORT_MD
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# RadLE v2 Score1000 Audit Report",
                "",
                f"Generated: {report['generated_at']}",
                "",
                "Result: pass",
                "",
                "The audit validated the generator-produced `manifest.json` without rewriting it.",
                "",
                "Stale-score gate scope: CSV schemas and row-level/summary data. Provenance and receipts may mention `weighted_score` only as removed/source metadata.",
                "",
                "Human comparator Score1000 totals:",
                f"- Board-certified radiologists: {human_totals['Board-certified radiologists']}",
                f"- Radiology trainees: {human_totals['Radiology trainees']}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir.resolve()
    validate_required_files(out_dir)
    validate_clean_master(out_dir)
    frames = validate_csv_schemas(out_dir)
    scored = validate_source_and_scored(frames)
    validate_summaries(frames, scored)
    validate_status_audit(frames, scored)
    validate_provenance(out_dir, scored)
    validate_manifest(out_dir)
    write_audit_report(out_dir, scored)

    print("[PASS] preflight clean adjudication master and source snapshot")
    print("[PASS] stale-score schema gate")
    print("[PASS] cohort and human200 gates")
    print("[PASS] score1000 status and row-score gates")
    print("[PASS] final summary reconciliation")
    print("[PASS] provenance and manifest gates")
    print(f"[PASS] wrote {rel(out_dir / AUDIT_REPORT_JSON)}")
    print(f"[PASS] wrote {rel(out_dir / AUDIT_REPORT_MD)}")
    print(f"[PASS] audited {rel(out_dir)}")


if __name__ == "__main__":
    main()
