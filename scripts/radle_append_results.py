"""Append one or more RadLE model-result column families to a wide result CSV.

This script is intentionally roster-agnostic. It discovers models from
``Diagnosis_<model_key>`` columns and appends every non-key column from the
incoming result file after validating that case IDs and image metadata align.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


KEY_COLUMNS = ["Master_Case_ID", "Associated_Images", "Image_SHA256"]
CASE_KEY = "Master_Case_ID"
DIAGNOSIS_PREFIX = "Diagnosis_"
PUBLIC_CASE_MODEL = "RadLE_v2_public_model_results.csv"
PUBLIC_MODEL_SUMMARY = "RadLE_v2_public_model_summary.csv"
PUBLIC_SANITIZED_CALL_LOG = "RadLE_v2_public_sanitized_call_log.csv"
PUBLIC_MANIFEST = "RadLE_v2_public_manifest.json"
FINAL_RESULTS = "RadLE_v2_results_final.csv"
SCORER_VIEW = "scorer_view.csv"


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


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing output without --overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, object], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing output without --overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json_if_exists(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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
    keys = []
    for column in fieldnames:
        if column.startswith(DIAGNOSIS_PREFIX) and len(column) > len(DIAGNOSIS_PREFIX):
            keys.append(column[len(DIAGNOSIS_PREFIX):])
    return keys


def parse_key_columns(value: str) -> list[str]:
    columns = [part.strip() for part in value.split(",") if part.strip()]
    if CASE_KEY not in columns:
        raise ValueError(f"--key-columns must include {CASE_KEY}")
    return columns


def model_columns(fieldnames: Iterable[str], model_key: str, key_columns: list[str]) -> list[str]:
    suffix = f"_{model_key}"
    return [column for column in fieldnames if column not in key_columns and column.endswith(suffix)]


def order_columns(fieldnames: list[str], key_columns: list[str], column_order: str) -> list[str]:
    if column_order == "preserve":
        return fieldnames
    if column_order != "diagnosis-likert-pairs":
        raise ValueError(f"Unknown column order: {column_order}")

    ordered: list[str] = []
    seen: set[str] = set()
    for column in key_columns:
        if column in fieldnames and column not in seen:
            ordered.append(column)
            seen.add(column)

    for model_key in discover_model_keys(fieldnames):
        for column in (f"Diagnosis_{model_key}", f"Likert_{model_key}"):
            if column in fieldnames and column not in seen:
                ordered.append(column)
                seen.add(column)

    for column in fieldnames:
        if column not in seen:
            ordered.append(column)
            seen.add(column)

    return ordered


def index_by_case(rows: list[dict[str, str]], label: str) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    duplicates: list[str] = []
    blanks = 0
    for row in rows:
        case_id = (row.get(CASE_KEY) or "").strip()
        if not case_id:
            blanks += 1
            continue
        if case_id in indexed:
            duplicates.append(case_id)
        else:
            indexed[case_id] = row
    if blanks:
        raise ValueError(f"{label} has {blanks} blank {CASE_KEY} value(s)")
    if duplicates:
        sample = sorted(set(duplicates))[:10]
        raise ValueError(f"{label} has duplicate {CASE_KEY} value(s), sample: {sample}")
    return indexed


def compare_key_sets(base_cases: set[str], incoming_cases: set[str]) -> None:
    missing_in_incoming = sorted(base_cases - incoming_cases, key=case_sort_key)
    extra_in_incoming = sorted(incoming_cases - base_cases, key=case_sort_key)
    if missing_in_incoming or extra_in_incoming:
        parts = []
        if missing_in_incoming:
            parts.append(f"missing from incoming: {missing_in_incoming[:10]}")
        if extra_in_incoming:
            parts.append(f"extra in incoming: {extra_in_incoming[:10]}")
        raise ValueError("Case ID sets do not match; " + "; ".join(parts))


def case_sort_key(value: str) -> tuple[int, object]:
    try:
        return (0, int(value))
    except ValueError:
        return (1, value)


def find_metadata_mismatches(
    base_rows: list[dict[str, str]],
    incoming_by_case: dict[str, dict[str, str]],
    key_columns: list[str],
) -> list[dict[str, str]]:
    mismatches: list[dict[str, str]] = []
    for base_row in base_rows:
        case_id = (base_row.get(CASE_KEY) or "").strip()
        incoming_row = incoming_by_case[case_id]
        for column in key_columns:
            if column == CASE_KEY:
                continue
            base_value = base_row.get(column, "")
            incoming_value = incoming_row.get(column, "")
            if base_value != incoming_value:
                mismatches.append({
                    CASE_KEY: case_id,
                    "column": column,
                    "base_value": base_value,
                    "incoming_value": incoming_value,
                })
    return mismatches


def build_output_rows(
    base_rows: list[dict[str, str]],
    incoming_by_case: dict[str, dict[str, str]],
    incoming_append_columns: list[str],
) -> list[dict[str, str]]:
    output_rows: list[dict[str, str]] = []
    for base_row in base_rows:
        case_id = (base_row.get(CASE_KEY) or "").strip()
        incoming_row = incoming_by_case[case_id]
        combined = dict(base_row)
        for column in incoming_append_columns:
            combined[column] = incoming_row.get(column, "")
        output_rows.append(combined)
    return output_rows


def remove_existing_model_columns(
    base_fieldnames: list[str],
    base_rows: list[dict[str, str]],
    incoming_model_keys: list[str],
    key_columns: list[str],
) -> tuple[list[str], list[dict[str, str]], dict[str, list[str]]]:
    removed_by_model: dict[str, list[str]] = {}
    columns_to_remove: set[str] = set()
    for model_key in incoming_model_keys:
        columns = model_columns(base_fieldnames, model_key, key_columns)
        if columns:
            removed_by_model[model_key] = columns
            columns_to_remove.update(columns)

    if not columns_to_remove:
        return base_fieldnames, base_rows, removed_by_model

    kept_fieldnames = [column for column in base_fieldnames if column not in columns_to_remove]
    kept_rows = [
        {column: value for column, value in row.items() if column not in columns_to_remove}
        for row in base_rows
    ]
    return kept_fieldnames, kept_rows, removed_by_model


def build_manifest(
    *,
    base_path: Path,
    incoming_path: Path,
    output_path: Path,
    base_fieldnames: list[str],
    incoming_fieldnames: list[str],
    output_fieldnames: list[str],
    base_rows: list[dict[str, str]],
    incoming_rows: list[dict[str, str]],
    incoming_model_keys: list[str],
    replaced_model_columns: dict[str, list[str]],
    metadata_mismatches: list[dict[str, str]],
    key_columns: list[str],
    column_order: str,
    dry_run: bool,
) -> dict[str, object]:
    manifest: dict[str, object] = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "base_csv": str(base_path.resolve()),
        "incoming_csv": str(incoming_path.resolve()),
        "output_csv": str(output_path.resolve()),
        "base_sha256": sha256_file(base_path),
        "incoming_sha256": sha256_file(incoming_path),
        "output_sha256": None if dry_run else sha256_file(output_path),
        "base_rows": len(base_rows),
        "base_columns": len(base_fieldnames),
        "incoming_rows": len(incoming_rows),
        "incoming_columns": len(incoming_fieldnames),
        "output_rows": len(base_rows),
        "output_columns": len(output_fieldnames),
        "key_columns": key_columns,
        "column_order": column_order,
        "appended_model_keys": incoming_model_keys,
        "replaced_model_columns": replaced_model_columns,
        "metadata_mismatch_count": len(metadata_mismatches),
        "metadata_mismatch_sample": metadata_mismatches[:10],
        "dry_run": dry_run,
    }
    return manifest


def append_results(args: argparse.Namespace) -> int:
    base_path = args.base.resolve()
    incoming_path = args.incoming.resolve()
    output_path = args.output.resolve()
    key_columns = parse_key_columns(args.key_columns)

    base_fieldnames, base_rows = read_csv(base_path)
    incoming_fieldnames, incoming_rows = read_csv(incoming_path)

    require_columns(base_fieldnames, key_columns, "base CSV")
    require_columns(incoming_fieldnames, key_columns, "incoming CSV")

    base_model_keys = discover_model_keys(base_fieldnames)
    incoming_model_keys = discover_model_keys(incoming_fieldnames)
    if not incoming_model_keys:
        raise ValueError(f"incoming CSV has no {DIAGNOSIS_PREFIX}<model_key> columns: {incoming_path}")

    duplicate_incoming_model_keys = sorted({key for key in incoming_model_keys if incoming_model_keys.count(key) > 1})
    if duplicate_incoming_model_keys:
        raise ValueError(f"incoming CSV has duplicate discovered model keys: {duplicate_incoming_model_keys}")

    collisions = sorted(set(base_model_keys) & set(incoming_model_keys))
    if collisions and not args.replace_existing_model:
        raise ValueError(
            "Incoming model key(s) already exist in base CSV: "
            f"{collisions}. Use --replace-existing-model to replace those column families."
        )

    base_by_case = index_by_case(base_rows, "base CSV")
    incoming_by_case = index_by_case(incoming_rows, "incoming CSV")
    compare_key_sets(set(base_by_case), set(incoming_by_case))

    metadata_mismatches = find_metadata_mismatches(base_rows, incoming_by_case, key_columns)
    if metadata_mismatches and not args.allow_metadata_mismatch:
        sample = metadata_mismatches[:5]
        raise ValueError(
            f"Incoming metadata differs from base for {len(metadata_mismatches)} cell(s); "
            f"sample: {sample}. Use --allow-metadata-mismatch to append anyway."
        )

    if args.replace_existing_model:
        base_fieldnames, base_rows, replaced_model_columns = remove_existing_model_columns(
            base_fieldnames,
            base_rows,
            incoming_model_keys,
            key_columns,
        )
        base_by_case = index_by_case(base_rows, "base CSV")
    else:
        replaced_model_columns = {}

    incoming_append_columns = [column for column in incoming_fieldnames if column not in key_columns]
    overlapping_columns = [column for column in incoming_append_columns if column in base_fieldnames]
    if overlapping_columns:
        raise ValueError(f"Incoming non-key column(s) already exist after replacement handling: {overlapping_columns}")

    output_fieldnames = order_columns(
        base_fieldnames + incoming_append_columns,
        key_columns,
        args.column_order,
    )
    output_rows = build_output_rows(base_rows, incoming_by_case, incoming_append_columns)

    expected_columns = len(base_fieldnames) + len(incoming_append_columns)
    if len(output_fieldnames) != expected_columns:
        raise AssertionError("Internal column-count mismatch while building output")
    if len(output_rows) != len(base_rows):
        raise AssertionError("Internal row-count mismatch while building output")

    if not args.dry_run:
        write_csv(output_path, output_fieldnames, output_rows, args.overwrite)

    manifest = build_manifest(
        base_path=base_path,
        incoming_path=incoming_path,
        output_path=output_path,
        base_fieldnames=base_fieldnames,
        incoming_fieldnames=incoming_fieldnames,
        output_fieldnames=output_fieldnames,
        base_rows=base_rows,
        incoming_rows=incoming_rows,
        incoming_model_keys=incoming_model_keys,
        replaced_model_columns=replaced_model_columns,
        metadata_mismatches=metadata_mismatches,
        key_columns=key_columns,
        column_order=args.column_order,
        dry_run=args.dry_run,
    )

    manifest_path = args.manifest.resolve() if args.manifest else output_path.with_suffix(output_path.suffix + ".manifest.json")
    if not args.dry_run:
        if manifest_path.exists() and not args.overwrite:
            raise FileExistsError(f"Refusing to overwrite existing manifest without --overwrite: {manifest_path}")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"base={base_path}")
    print(f"incoming={incoming_path}")
    print(f"output={output_path}")
    print(f"rows={len(output_rows)}")
    print(f"base_columns={len(base_fieldnames)} incoming_append_columns={len(incoming_append_columns)} output_columns={len(output_fieldnames)}")
    print(f"appended_model_keys={', '.join(incoming_model_keys)}")
    if replaced_model_columns:
        print(f"replaced_model_keys={', '.join(replaced_model_columns)}")
    if metadata_mismatches:
        print(f"metadata_mismatch_count={len(metadata_mismatches)}")
    if args.dry_run:
        print("dry_run=true; no files written")
    else:
        print(f"manifest={manifest_path}")
        print(f"output_sha256={manifest['output_sha256']}")
    return 0


def append_one_csv(
    *,
    base: Path,
    incoming: Path,
    output: Path,
    key_columns: str,
    column_order: str = "preserve",
    overwrite: bool = False,
    replace_existing_model: bool = False,
    allow_metadata_mismatch: bool = False,
    dry_run: bool = False,
) -> int:
    return append_results(argparse.Namespace(
        base=base,
        incoming=incoming,
        output=output,
        manifest=None,
        key_columns=key_columns,
        column_order=column_order,
        overwrite=overwrite,
        replace_existing_model=replace_existing_model,
        allow_metadata_mismatch=allow_metadata_mismatch,
        dry_run=dry_run,
    ))


def append_public_table(
    *,
    base_path: Path | None,
    incoming_path: Path | None,
    output_path: Path,
    combined_run_id: str,
    unique_columns: list[str],
    overwrite: bool,
) -> dict[str, object]:
    sources = [path for path in (base_path, incoming_path) if path and path.exists()]
    if not sources:
        return {
            "output": "",
            "rows": 0,
            "columns": 0,
            "source_files": [],
            "sha256": "",
        }

    fieldnames: list[str] | None = None
    combined_rows: list[dict[str, str]] = []
    source_info: list[dict[str, object]] = []
    for path in sources:
        current_fieldnames, rows = read_csv(path)
        if fieldnames is None:
            fieldnames = current_fieldnames
        elif current_fieldnames != fieldnames:
            raise ValueError(f"Public table schema mismatch for {path}: {current_fieldnames} != {fieldnames}")
        for row in rows:
            out = dict(row)
            if "run_id" in out:
                out["run_id"] = combined_run_id
            combined_rows.append(out)
        source_info.append({
            "path": str(path.resolve()),
            "rows": len(rows),
            "columns": len(current_fieldnames),
            "sha256": sha256_file(path),
        })

    assert fieldnames is not None
    require_columns(fieldnames, unique_columns, str(output_path))
    seen: set[tuple[str, ...]] = set()
    duplicates: list[tuple[str, ...]] = []
    for row in combined_rows:
        key = tuple(row.get(column, "") for column in unique_columns)
        if key in seen:
            duplicates.append(key)
        else:
            seen.add(key)
    if duplicates:
        raise ValueError(f"Duplicate public table key(s) for {output_path}, sample: {duplicates[:10]}")

    write_csv(output_path, fieldnames, combined_rows, overwrite)
    return {
        "output": str(output_path.resolve()),
        "rows": len(combined_rows),
        "columns": len(fieldnames),
        "source_files": source_info,
        "sha256": sha256_file(output_path),
    }


def package_path(run_dir: Path, *parts: str) -> Path:
    return run_dir.joinpath(*parts)


def write_scorer_from_final(final_csv: Path, scorer_csv: Path, overwrite: bool) -> dict[str, int]:
    """Derive the combined scorer view directly from the combined final CSV.

    The per-run ``scorer_view.csv`` files are built by the notebooks from RAW
    benchmark output, before targeted repair runs. Appending those can carry
    pre-repair PARSE_FAILED/empty cells that disagree with the promoted, repaired
    final. Building the combined scorer from the combined final (the promoted
    source of truth) keeps diagnoses and likerts consistent with final.
    """
    fieldnames, rows = read_csv(final_csv)
    require_columns(fieldnames, ["Master_Case_ID"], "combined final CSV")
    scorer_key_columns = [c for c in ("Master_Case_ID", "Associated_Images") if c in fieldnames]
    diag_likert = [
        column
        for column in fieldnames
        if column.startswith("Diagnosis_") or column.startswith("Likert_")
    ]
    keep = scorer_key_columns + diag_likert
    ordered = order_columns(keep, scorer_key_columns, "diagnosis-likert-pairs")
    out_rows = [{column: row.get(column, "") for column in ordered} for row in rows]
    write_csv(scorer_csv, ordered, out_rows, overwrite)
    return {"rows": len(out_rows), "columns": len(ordered)}


def command_package(args: argparse.Namespace) -> int:
    base_run = args.base_run_dir.resolve()
    incoming_run = args.incoming_run_dir.resolve()
    output_run = args.output_run_dir.resolve()
    combined_run_id = args.combined_run_id or output_run.name

    final_output = package_path(output_run, "final", FINAL_RESULTS)
    scorer_output = package_path(output_run, "scorer", SCORER_VIEW)
    public_dir = package_path(output_run, "public_release")

    print("[1/5] Appending final wide result CSV")
    append_one_csv(
        base=package_path(base_run, "final", FINAL_RESULTS),
        incoming=package_path(incoming_run, "final", FINAL_RESULTS),
        output=final_output,
        key_columns=",".join(KEY_COLUMNS),
        column_order="preserve",
        overwrite=args.overwrite,
        replace_existing_model=args.replace_existing_model,
        allow_metadata_mismatch=args.allow_metadata_mismatch,
        dry_run=args.dry_run,
    )

    print("[2/5] Building scorer view (diagnosis/likert pairs) from combined final")
    if not args.dry_run:
        scorer_info = write_scorer_from_final(
            final_csv=final_output,
            scorer_csv=scorer_output,
            overwrite=args.overwrite,
        )
        print(f"scorer rows={scorer_info['rows']} columns={scorer_info['columns']} (derived from combined final)")

    print("[3/5] Appending public case-model table")
    public_case = append_public_table(
        base_path=package_path(base_run, "public_release", PUBLIC_CASE_MODEL),
        incoming_path=package_path(incoming_run, "public_release", PUBLIC_CASE_MODEL),
        output_path=public_dir / PUBLIC_CASE_MODEL,
        combined_run_id=combined_run_id,
        unique_columns=["run_id", "case_uid", "model"],
        overwrite=args.overwrite,
    ) if not args.dry_run else {"dry_run": True}

    print("[4/5] Appending public model summary and sanitized call log")
    public_summary = append_public_table(
        base_path=package_path(base_run, "public_release", PUBLIC_MODEL_SUMMARY),
        incoming_path=package_path(incoming_run, "public_release", PUBLIC_MODEL_SUMMARY),
        output_path=public_dir / PUBLIC_MODEL_SUMMARY,
        combined_run_id=combined_run_id,
        unique_columns=["run_id", "model", "provider"],
        overwrite=args.overwrite,
    ) if not args.dry_run else {"dry_run": True}

    base_log = package_path(base_run, "public_release", PUBLIC_SANITIZED_CALL_LOG)
    incoming_log = package_path(incoming_run, "public_release", PUBLIC_SANITIZED_CALL_LOG)
    public_log = append_public_table(
        base_path=base_log if base_log.exists() else None,
        incoming_path=incoming_log if incoming_log.exists() else None,
        output_path=public_dir / PUBLIC_SANITIZED_CALL_LOG,
        combined_run_id=combined_run_id,
        unique_columns=["run_id", "case_uid", "model", "event", "repair_attempt_number", "timestamp_utc"],
        overwrite=args.overwrite,
    ) if not args.dry_run else {"dry_run": True}

    print("[5/5] Writing combined package manifests")
    base_public_manifest = read_json_if_exists(package_path(base_run, "public_release", PUBLIC_MANIFEST))
    incoming_public_manifest = read_json_if_exists(package_path(incoming_run, "public_release", PUBLIC_MANIFEST))
    public_manifest = {
        "run_id": combined_run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_results_file": FINAL_RESULTS,
        "source_call_log_file": PUBLIC_SANITIZED_CALL_LOG if public_log.get("rows", 0) else "",
        "public_files": {
            "case_model": PUBLIC_CASE_MODEL,
            "model_summary": PUBLIC_MODEL_SUMMARY,
            "sanitized_call_log": PUBLIC_SANITIZED_CALL_LOG if public_log.get("rows", 0) else "",
        },
        "source_public_manifests": [
            base_public_manifest,
            incoming_public_manifest,
        ],
        "privacy_notes": incoming_public_manifest.get("privacy_notes")
        or base_public_manifest.get("privacy_notes")
        or [],
    }

    package_manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "combined_run_id": combined_run_id,
        "base_run_dir": str(base_run),
        "incoming_run_dir": str(incoming_run),
        "output_run_dir": str(output_run),
        "final_csv": str(final_output),
        "final_sha256": None if args.dry_run else sha256_file(final_output),
        "scorer_csv": str(scorer_output),
        "scorer_sha256": None if args.dry_run else sha256_file(scorer_output),
        "public_case_model": public_case,
        "public_model_summary": public_summary,
        "public_sanitized_call_log": public_log,
    }

    if not args.dry_run:
        write_json(public_dir / PUBLIC_MANIFEST, public_manifest, args.overwrite)
        write_json(output_run / "append_package_manifest.json", package_manifest, args.overwrite)

    print(f"combined_run_id={combined_run_id}")
    print(f"output_run_dir={output_run}")
    if args.dry_run:
        print("dry_run=true; package public files/manifests not written")
    else:
        print(f"public_case_rows={public_case['rows']} public_summary_rows={public_summary['rows']} public_log_rows={public_log['rows']}")
        print(f"package_manifest={output_run / 'append_package_manifest.json'}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Append incoming RadLE model-result columns to a wide v2 result CSV."
    )
    parser.add_argument("--package", action="store_true", help="Append a whole run package: final, scorer, and public_release files.")
    parser.add_argument("--base-run-dir", type=Path, help="Base run directory for --package, for example results/radle_v2.")
    parser.add_argument("--incoming-run-dir", type=Path, help="Incoming run directory for --package.")
    parser.add_argument("--output-run-dir", type=Path, help="Output combined run directory for --package.")
    parser.add_argument("--combined-run-id", help="Run ID to write into combined public-release tables. Defaults to output run directory name.")
    parser.add_argument("--base", type=Path, help="Existing wide result CSV to append to.")
    parser.add_argument("--incoming", type=Path, help="New result CSV containing one or more model column families.")
    parser.add_argument("--output", type=Path, help="Combined output CSV path.")
    parser.add_argument("--manifest", type=Path, help="Optional manifest path. Defaults to <output>.manifest.json.")
    parser.add_argument(
        "--key-columns",
        default=",".join(KEY_COLUMNS),
        help=(
            "Comma-separated row identity/metadata columns to validate and keep from the base CSV. "
            "Use Master_Case_ID,Associated_Images for scorer_view.csv files."
        ),
    )
    parser.add_argument(
        "--column-order",
        choices=["preserve", "diagnosis-likert-pairs"],
        default="preserve",
        help="Use diagnosis-likert-pairs for scorer_view.csv readability.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting the output and manifest.")
    parser.add_argument(
        "--replace-existing-model",
        action="store_true",
        help="Replace incoming model column families if their model keys already exist in the base CSV.",
    )
    parser.add_argument(
        "--allow-metadata-mismatch",
        action="store_true",
        help="Append even if Associated_Images or Image_SHA256 differs for matching case IDs.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the merge summary without writing files.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    try:
        if args.package:
            missing = [
                name
                for name in ("base_run_dir", "incoming_run_dir", "output_run_dir")
                if getattr(args, name) is None
            ]
            if missing:
                raise ValueError(f"--package requires: {missing}")
            return command_package(args)
        if args.base is None or args.incoming is None or args.output is None:
            raise ValueError("single-CSV mode requires --base, --incoming, and --output")
        return append_results(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
