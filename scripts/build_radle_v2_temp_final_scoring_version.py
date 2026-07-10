#!/usr/bin/env python3
"""Initialize a sibling RadLE v2 temporary final-scoring folder.

This script does not mutate the official final-scoring folder. It copies the
locked final long master into a new sibling folder under outputs/radle_v2_stats
and writes provenance so downstream scripts can treat the sibling as a candidate
version.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
STATS_ROOT = REPO_ROOT / "outputs/radle_v2_stats"
DEFAULT_SOURCE_DIR = STATS_ROOT / "final_scoring_radiologist_20260706_001147"
DEFAULT_SOURCE_MASTER = DEFAULT_SOURCE_DIR / "radle_v2_final_long_master.csv"
DEFAULT_INPUT_WORKBOOK = STATS_ROOT / "radle_v2_dual_judge_scored_combined_with_codex_v2.xlsx"
DEFAULT_LABEL = "temp_3_5_5_4"
EXPECTED_ROWS = 6000
EXPECTED_SOURCE_SHA256 = "7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED"
EXPECTED_COLUMNS = [
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
KEY_COLUMNS = ["Master_Case_ID", "model_blinded"]


class BuildFailure(RuntimeError):
    """Raised when the temp candidate folder cannot be initialized safely."""


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


def slugify_label(value: str) -> str:
    label = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip())
    label = re.sub(r"_+", "_", label).strip("_").lower()
    if not label:
        raise BuildFailure("Label became empty after slugification")
    return label


def default_dest_name(label: str) -> str:
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    return f"final_scoring_radiologist_{stamp}_{slugify_label(label)}"


def validate_dest_name(name: str) -> None:
    if "/" in name or "\\" in name or name in {".", ".."}:
        raise BuildFailure(f"Destination name must be a folder name, got: {name!r}")
    if not name.startswith("final_scoring_radiologist_"):
        raise BuildFailure(
            "Destination name must start with 'final_scoring_radiologist_' "
            f"for safety, got: {name!r}"
        )


def read_master(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def validate_source_master(path: Path, expected_sha: str | None) -> tuple[pd.DataFrame, str]:
    if not path.exists():
        raise BuildFailure(f"Source master not found: {path}")
    source_sha = sha256_file(path)
    if expected_sha and source_sha != expected_sha:
        raise BuildFailure(f"Source master SHA mismatch: expected {expected_sha}, got {source_sha}")
    df = read_master(path)
    if len(df) != EXPECTED_ROWS:
        raise BuildFailure(f"Expected {EXPECTED_ROWS} source rows, got {len(df)}")
    if list(df.columns) != EXPECTED_COLUMNS:
        raise BuildFailure(
            "Source master columns differ from expected final-long schema.\n"
            f"Expected: {EXPECTED_COLUMNS}\n"
            f"Actual:   {list(df.columns)}"
        )
    duplicate_keys = int(df.duplicated(KEY_COLUMNS).sum())
    if duplicate_keys:
        raise BuildFailure(f"Source master has duplicate key rows: {duplicate_keys}")
    scores = pd.to_numeric(df["final_score_authoritative"], errors="raise")
    if not set(scores.unique()).issubset({0, 1}):
        raise BuildFailure("final_score_authoritative must contain only 0/1 values")
    return df, source_sha


def write_readme(dest_dir: Path, source_master: Path, source_sha: str, workbook: Path | None) -> None:
    workbook_line = f"- Input workbook recorded for provenance: `{rel(workbook)}`\n" if workbook else ""
    body = (
        "# RadLE v2 Temporary Final Scoring Version\n\n"
        "This folder is a sibling candidate lane. It was initialized from the official "
        "final scoring master and is safe to use for temporary 3.5 / 5.4 follow-on work.\n\n"
        f"- Source master: `{rel(source_master)}`\n"
        f"- Source master SHA256: `{source_sha}`\n"
        f"{workbook_line}"
        "- Official source folder was not mutated.\n"
        "- Regenerate derived outputs in this folder rather than copying stale outputs.\n"
    )
    (dest_dir / "README.md").write_text(body, encoding="utf-8")


def write_receipt(
    *,
    dest_dir: Path,
    source_master: Path,
    dest_master: Path,
    input_workbook: Path | None,
    source_df: pd.DataFrame,
    source_sha: str,
    dest_sha: str,
) -> dict[str, object]:
    scores = pd.to_numeric(source_df["final_score_authoritative"], errors="raise")
    receipt = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "generator": rel(Path(__file__)),
        "purpose": "temporary sibling final-scoring candidate for 3.5 / 5.4 follow-on work",
        "official_source_mutated": False,
        "source_folder": rel(source_master.parent),
        "destination_folder": rel(dest_dir),
        "source_master": {
            "path": rel(source_master),
            "sha256": source_sha,
            "rows": int(len(source_df)),
            "columns": list(source_df.columns),
            "column_count": int(len(source_df.columns)),
        },
        "candidate_master": {
            "path": rel(dest_master),
            "sha256": dest_sha,
            "rows": int(len(source_df)),
            "columns": list(source_df.columns),
            "column_count": int(len(source_df.columns)),
        },
        "input_workbook": None,
        "validation": {
            "duplicate_keys": int(source_df.duplicated(KEY_COLUMNS).sum()),
            "correct_total": int(scores.sum()),
            "final_score_distribution": {
                str(int(k)): int(v) for k, v in scores.value_counts().sort_index().items()
            },
            "final_score_source_mix": {
                str(k): int(v) for k, v in source_df["final_score_source"].value_counts().items()
            },
            "row_order_preserved": True,
            "master_copy_sha_matches_source": dest_sha == source_sha,
        },
        "next_step": (
            "Run scripts/build_radle_v2_score1000_pipeline.ps1 with -InputMaster set to "
            f"{rel(dest_master)} and -OutDir set to {rel(dest_dir / 'likert5_score1000')}."
        ),
    }
    if input_workbook is not None:
        receipt["input_workbook"] = {
            "path": rel(input_workbook),
            "sha256": sha256_file(input_workbook),
            "exists": True,
        }
    receipt_path = dest_dir / "temp_final_scoring_version_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-master", type=Path, default=DEFAULT_SOURCE_MASTER)
    parser.add_argument("--input-workbook", type=Path, default=DEFAULT_INPUT_WORKBOOK)
    parser.add_argument("--dest-name", default=None, help="Sibling folder name under outputs/radle_v2_stats.")
    parser.add_argument("--label", default=DEFAULT_LABEL, help="Label used when --dest-name is omitted.")
    parser.add_argument(
        "--skip-source-sha-gate",
        action="store_true",
        help="Allow copying a structurally valid source master with a non-official SHA.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_master = args.source_master.resolve()
    expected_sha = None if args.skip_source_sha_gate else EXPECTED_SOURCE_SHA256
    source_df, source_sha = validate_source_master(source_master, expected_sha)

    dest_name = args.dest_name or default_dest_name(args.label)
    validate_dest_name(dest_name)
    dest_dir = (STATS_ROOT / dest_name).resolve()
    stats_root = STATS_ROOT.resolve()
    if stats_root not in dest_dir.parents:
        raise BuildFailure(f"Destination must stay under {stats_root}, got {dest_dir}")
    if dest_dir.exists():
        raise BuildFailure(f"Destination already exists; choose a new --dest-name: {dest_dir}")

    dest_dir.mkdir(parents=True)
    dest_master = dest_dir / "radle_v2_final_long_master.csv"
    shutil.copy2(source_master, dest_master)
    dest_sha = sha256_file(dest_master)
    if dest_sha != source_sha:
        raise BuildFailure(f"Copied master SHA mismatch: source={source_sha}, dest={dest_sha}")

    input_workbook = args.input_workbook.resolve() if args.input_workbook else None
    if input_workbook is not None and not input_workbook.exists():
        input_workbook = None

    write_readme(dest_dir, source_master, source_sha, input_workbook)
    write_receipt(
        dest_dir=dest_dir,
        source_master=source_master,
        dest_master=dest_master,
        input_workbook=input_workbook,
        source_df=source_df,
        source_sha=source_sha,
        dest_sha=dest_sha,
    )

    print("[PASS] initialized temp final scoring version")
    print(f"folder {rel(dest_dir)}")
    print(f"master {rel(dest_master)}")
    print(f"sha256 {dest_sha}")
    print(f"rows {len(source_df)}")


if __name__ == "__main__":
    main()
