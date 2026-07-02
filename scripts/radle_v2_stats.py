"""Dynamic RadLE v2 stats preparation helpers.

The commands here deliberately avoid hardcoded model rosters. They discover
model keys from wide result columns named ``Diagnosis_<model_key>``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


KEY_COLUMNS = ["Master_Case_ID", "Associated_Images", "Image_SHA256"]
CASE_KEY = "Master_Case_ID"
GROUND_TRUTH_COLUMN = "Ground_Truth_Diagnosis"
DIAGNOSIS_PREFIX = "Diagnosis_"

OPTIONAL_MODEL_FIELDS = {
    "Diagnosis": "diagnosis",
    "Likert": "likert",
    "Provider": "provider",
    "Prompt_Tokens": "prompt_tokens",
    "Total_Tokens_Out": "completion_tokens",
    "Reasoning_Tokens": "reasoning_tokens",
    "Latency": "latency_seconds",
    "Timestamp_UTC": "timestamp_utc",
    "OpenRouter_Response_Model": "response_model",
    "Usage_JSON": "usage_json",
    "Raw_Response": "raw_response",
    "Reasoning": "reasoning",
    "Reasoning_Raw": "reasoning_raw",
    "Reasoning_Details": "reasoning_details",
    "Actual_Request_Extra": "actual_request_extra",
    "Grok_Fallback_Used": "grok_fallback_used",
}

LONG_COLUMNS = [
    "run_id",
    "Master_Case_ID",
    "Associated_Images",
    "Image_SHA256",
    "model_key",
    "Ground_Truth_Diagnosis",
    "diagnosis",
    "likert",
    "provider",
    "prompt_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "latency_seconds",
    "timestamp_utc",
    "response_model",
    "response_valid",
    "abstained",
    "technical_failure",
    "score_required",
    "usage_json",
    "raw_response",
    "reasoning",
    "reasoning_raw",
    "reasoning_details",
    "actual_request_extra",
    "grok_fallback_used",
]

SCORING_COLUMNS = [
    "row_uid",
    "run_id",
    "Master_Case_ID",
    "model_key",
    "Ground_Truth_Diagnosis",
    "diagnosis",
    "likert",
    "provider",
    "response_valid",
    "abstained",
    "technical_failure",
    "score_required",
    "score_binary",
    "score_likert",
    "judge_verdict",
    "judge_confidence",
    "judge_match_type",
    "needs_human_review",
    "likert_weight",
    "weighted_score",
    "weighted_score_rule",
    "judge_rationale",
    "judge_model",
    "judge_status",
    "judged_utc",
]


def set_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    set_csv_field_limit()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    if not fieldnames:
        raise ValueError(f"CSV has no header: {path}")
    if not rows:
        raise ValueError(f"CSV has no data rows: {path}")
    return fieldnames, rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file without --overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temp_path.replace(path)


def write_json(path: Path, payload: dict[str, object], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file without --overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_columns(fieldnames: Iterable[str], required: Iterable[str], label: str) -> None:
    fields = set(fieldnames)
    missing = [column for column in required if column not in fields]
    if missing:
        raise ValueError(f"{label} is missing required column(s): {missing}")


def discover_model_keys(fieldnames: Iterable[str]) -> list[str]:
    model_keys: list[str] = []
    for column in fieldnames:
        if column.startswith(DIAGNOSIS_PREFIX) and len(column) > len(DIAGNOSIS_PREFIX):
            model_keys.append(column[len(DIAGNOSIS_PREFIX):])
    return model_keys


def case_sort_key(value: str) -> tuple[int, object]:
    try:
        return (0, int(str(value)))
    except ValueError:
        return (1, str(value))


def index_ground_truth(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    duplicates: list[str] = []
    for row in rows:
        case_id = clean(row.get(CASE_KEY, ""))
        if not case_id:
            continue
        if case_id in indexed:
            duplicates.append(case_id)
        else:
            indexed[case_id] = row
    if duplicates:
        raise ValueError(f"ground-truth CSV has duplicate {CASE_KEY} value(s): {sorted(set(duplicates))[:10]}")
    return indexed


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def normalize_text(value: object) -> str:
    text = clean(value).lower()
    text = text.replace("’", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_abstention(diagnosis: str) -> bool:
    text = normalize_text(diagnosis)
    return text in {
        "i don t know",
        "i dont know",
        "do not know",
        "don t know",
        "dont know",
        "unknown",
        "uncertain",
        "cannot determine",
        "can not determine",
        "unable to determine",
        "no diagnosis",
    }


def is_technical_failure(diagnosis: str) -> bool:
    text = clean(diagnosis).upper()
    if not text:
        return True
    failure_markers = {
        "PARSE_FAILED",
        "JSON_MISSING_KEY",
        "INVALID_OR_MISSING_LIKERT",
        "PROVIDER_BLOCKED",
        "API_ERROR",
        "MALFORMED_JSON",
        "REPAIR_EXHAUSTED",
    }
    return text in failure_markers or text.startswith("ERROR:")


def is_response_valid(diagnosis: str) -> bool:
    return not is_technical_failure(diagnosis)


def make_row_uid(run_id: str, case_id: str, model_key: str) -> str:
    return f"{run_id}|{case_id}|{model_key}"


def model_value(row: dict[str, str], field_prefix: str, model_key: str) -> str:
    return row.get(f"{field_prefix}_{model_key}", "")


def build_long_rows(
    wide_rows: list[dict[str, str]],
    wide_fieldnames: list[str],
    gt_rows: list[dict[str, str]],
    run_id: str,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    require_columns(wide_fieldnames, KEY_COLUMNS, "wide results CSV")
    gt_fieldnames = list(gt_rows[0].keys()) if gt_rows else []
    require_columns(gt_fieldnames, [CASE_KEY, GROUND_TRUTH_COLUMN], "ground-truth CSV")

    model_keys = discover_model_keys(wide_fieldnames)
    if not model_keys:
        raise ValueError(f"wide results CSV has no {DIAGNOSIS_PREFIX}<model_key> columns")

    gt_by_case = index_ground_truth(gt_rows)
    missing_gt: list[str] = []
    long_rows: list[dict[str, str]] = []
    missing_companion_columns: dict[str, list[str]] = {}

    for model_key in model_keys:
        missing = [
            f"{field_prefix}_{model_key}"
            for field_prefix in ("Diagnosis", "Likert")
            if f"{field_prefix}_{model_key}" not in wide_fieldnames
        ]
        if missing:
            missing_companion_columns[model_key] = missing

    if missing_companion_columns:
        raise ValueError(f"missing required model companion columns: {missing_companion_columns}")

    for wide_row in wide_rows:
        case_id = clean(wide_row.get(CASE_KEY, ""))
        gt_row = gt_by_case.get(case_id)
        if not gt_row:
            missing_gt.append(case_id)
            ground_truth = ""
        else:
            ground_truth = clean(gt_row.get(GROUND_TRUTH_COLUMN, ""))

        for model_key in model_keys:
            diagnosis = clean(model_value(wide_row, "Diagnosis", model_key))
            technical_failure = is_technical_failure(diagnosis)
            abstained = is_abstention(diagnosis)
            response_valid = is_response_valid(diagnosis)
            score_required = response_valid and not abstained

            out_row = {
                "run_id": run_id,
                "Master_Case_ID": case_id,
                "Associated_Images": wide_row.get("Associated_Images", ""),
                "Image_SHA256": wide_row.get("Image_SHA256", ""),
                "model_key": model_key,
                "Ground_Truth_Diagnosis": ground_truth,
                "response_valid": bool_text(response_valid),
                "abstained": bool_text(abstained),
                "technical_failure": bool_text(technical_failure),
                "score_required": bool_text(score_required),
            }
            for field_prefix, output_name in OPTIONAL_MODEL_FIELDS.items():
                out_row[output_name] = wide_row.get(f"{field_prefix}_{model_key}", "")
            long_rows.append(out_row)

    duplicate_keys: list[str] = []
    seen = set()
    for row in long_rows:
        key = (row["Master_Case_ID"], row["model_key"])
        if key in seen:
            duplicate_keys.append(f"{key[0]}|{key[1]}")
        seen.add(key)

    expected_rows = len(wide_rows) * len(model_keys)
    qa = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "case_count": len(wide_rows),
        "model_count": len(model_keys),
        "model_keys": model_keys,
        "expected_rows": expected_rows,
        "actual_rows": len(long_rows),
        "duplicate_case_model_count": len(duplicate_keys),
        "duplicate_case_model_sample": duplicate_keys[:10],
        "missing_ground_truth_count": len(missing_gt),
        "missing_ground_truth_sample": sorted(set(missing_gt), key=case_sort_key)[:10],
        "score_required_count": sum(1 for row in long_rows if row["score_required"] == "true"),
        "abstention_count": sum(1 for row in long_rows if row["abstained"] == "true"),
        "technical_failure_count": sum(1 for row in long_rows if row["technical_failure"] == "true"),
    }

    if len(long_rows) != expected_rows:
        raise AssertionError(f"expected {expected_rows} long rows but built {len(long_rows)}")
    if duplicate_keys:
        raise ValueError(f"duplicate case-model rows detected: {duplicate_keys[:10]}")
    if missing_gt:
        raise ValueError(f"missing ground truth for case IDs: {sorted(set(missing_gt), key=case_sort_key)[:10]}")

    return long_rows, qa


def command_long(args: argparse.Namespace) -> int:
    input_path = args.input.resolve()
    ground_truth_path = args.ground_truth.resolve()
    out_dir = args.out.resolve()
    run_id = args.run_id or input_path.stem

    wide_fieldnames, wide_rows = read_csv(input_path)
    _, gt_rows = read_csv(ground_truth_path)
    long_rows, qa = build_long_rows(wide_rows, wide_fieldnames, gt_rows, run_id)
    qa.update({
        "input_csv": str(input_path),
        "input_sha256": sha256_file(input_path),
        "ground_truth_csv": str(ground_truth_path),
        "ground_truth_sha256": sha256_file(ground_truth_path),
    })

    long_path = out_dir / "long_format.csv"
    qa_path = out_dir / "raw_qa_summary.json"
    write_csv(long_path, LONG_COLUMNS, long_rows, args.overwrite)
    qa["long_format_csv"] = str(long_path)
    qa["long_format_sha256"] = sha256_file(long_path)
    write_json(qa_path, qa, args.overwrite)

    print(f"long_format={long_path}")
    print(f"raw_qa_summary={qa_path}")
    print(f"case_count={qa['case_count']} model_count={qa['model_count']} rows={qa['actual_rows']}")
    print(f"score_required_count={qa['score_required_count']} abstention_count={qa['abstention_count']} technical_failure_count={qa['technical_failure_count']}")
    return 0


def command_scoring_worklist(args: argparse.Namespace) -> int:
    long_path = args.long.resolve()
    out_dir = args.out.resolve()
    _, long_rows = read_csv(long_path)
    require_columns(long_rows[0].keys(), [
        "run_id",
        CASE_KEY,
        "model_key",
        GROUND_TRUTH_COLUMN,
        "diagnosis",
        "score_required",
    ], "long-format CSV")

    rows: list[dict[str, str]] = []
    for row in long_rows:
        score_required = clean(row.get("score_required", "")).lower() == "true"
        if args.only_score_required and not score_required:
            continue
        run_id = clean(row.get("run_id", ""))
        case_id = clean(row.get(CASE_KEY, ""))
        model_key = clean(row.get("model_key", ""))
        rows.append({
            "row_uid": make_row_uid(run_id, case_id, model_key),
            "run_id": run_id,
            "Master_Case_ID": case_id,
            "model_key": model_key,
            "Ground_Truth_Diagnosis": row.get(GROUND_TRUTH_COLUMN, ""),
            "diagnosis": row.get("diagnosis", ""),
            "likert": row.get("likert", ""),
            "provider": row.get("provider", ""),
            "response_valid": row.get("response_valid", ""),
            "abstained": row.get("abstained", ""),
            "technical_failure": row.get("technical_failure", ""),
            "score_required": row.get("score_required", ""),
            "score_binary": "",
            "score_likert": "",
            "judge_verdict": "",
            "judge_confidence": "",
            "judge_match_type": "",
            "needs_human_review": "",
            "likert_weight": "",
            "weighted_score": "",
            "weighted_score_rule": "signed model Likert confidence: correct=+Likert, wrong=-Likert",
            "judge_rationale": "",
            "judge_model": "",
            "judge_status": "",
            "judged_utc": "",
        })

    path = out_dir / "scoring_worklist.csv"
    write_csv(path, SCORING_COLUMNS, rows, args.overwrite)
    required = sum(1 for row in rows if row["score_required"].lower() == "true")
    print(f"scoring_worklist={path}")
    print(f"rows={len(rows)} score_required={required}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare dynamic RadLE v2 result files for stats and judging.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    long_parser = subparsers.add_parser("long", help="Convert wide results to canonical long format.")
    long_parser.add_argument("--input", type=Path, required=True)
    long_parser.add_argument("--ground-truth", type=Path, required=True)
    long_parser.add_argument("--out", type=Path, required=True)
    long_parser.add_argument("--run-id")
    long_parser.add_argument("--overwrite", action="store_true")
    long_parser.set_defaults(func=command_long)

    worklist_parser = subparsers.add_parser("scoring-worklist", help="Create a scoring worklist from long format.")
    worklist_parser.add_argument("--long", type=Path, required=True)
    worklist_parser.add_argument("--out", type=Path, required=True)
    worklist_parser.add_argument("--only-score-required", action="store_true")
    worklist_parser.add_argument("--overwrite", action="store_true")
    worklist_parser.set_defaults(func=command_scoring_worklist)

    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
