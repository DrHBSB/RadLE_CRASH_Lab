#!/usr/bin/env python3
"""Build the RadLE v2 clean adjudication master for the Score1000 lane.

This script treats the current final long master as an immutable input snapshot.
It writes a cleaned adjudication-only CSV under the Score1000 output root and
does not mutate the source master.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    REPO_ROOT
    / "outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147"
    / "radle_v2_final_long_master.csv"
)
DEFAULT_OUT_DIR = (
    REPO_ROOT
    / "outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147"
    / "likert5_score1000"
)

EXPECTED_INPUT_SHA256 = "7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED"
EXPECTED_ROWS = 6000
EXPECTED_INPUT_COLUMNS = [
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
REMOVED_SCORE_COLUMNS = ["weighted_score"]
FORBIDDEN_SCORE_COLUMNS = {
    "weighted_score",
    "source_weighted_score",
    "mean_weighted_score",
    "n_weighted",
    "weighted_score_rule",
}
KEY_COLUMNS = ["Master_Case_ID", "model_blinded"]


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


def validate_input_snapshot(path: Path, df: pd.DataFrame, actual_sha: str) -> None:
    if actual_sha != EXPECTED_INPUT_SHA256:
        raise GateFailure(
            f"Input SHA256 mismatch: expected {EXPECTED_INPUT_SHA256}, got {actual_sha}"
        )
    if len(df) != EXPECTED_ROWS:
        raise GateFailure(f"Expected {EXPECTED_ROWS} input rows, got {len(df)}")
    if list(df.columns) != EXPECTED_INPUT_COLUMNS:
        raise GateFailure(
            "Input columns differ from locked snapshot.\n"
            f"Expected: {EXPECTED_INPUT_COLUMNS}\n"
            f"Actual:   {list(df.columns)}"
        )
    if df.duplicated(KEY_COLUMNS).any():
        dupes = int(df.duplicated(KEY_COLUMNS).sum())
        raise GateFailure(f"Duplicate key rows found in input snapshot: {dupes}")
    correct_total = int(pd.to_numeric(df["final_score_authoritative"], errors="raise").sum())
    if correct_total != 1255:
        raise GateFailure(f"Expected 1255 correct rows, got {correct_total}")
    normalization_columns = [c for c in df.columns if c.startswith("normalization_")]
    if normalization_columns:
        raise GateFailure(f"Input snapshot unexpectedly contains normalization columns: {normalization_columns}")
    removable_present = [c for c in REMOVED_SCORE_COLUMNS if c in df.columns]
    if removable_present != REMOVED_SCORE_COLUMNS:
        raise GateFailure(f"Expected removable score columns {REMOVED_SCORE_COLUMNS}, got {removable_present}")
    unexpected_forbidden = sorted((FORBIDDEN_SCORE_COLUMNS - set(REMOVED_SCORE_COLUMNS)) & set(df.columns))
    if unexpected_forbidden:
        raise GateFailure(f"Unexpected stale score columns in input: {unexpected_forbidden}")


def build_clean_master(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.drop(columns=REMOVED_SCORE_COLUMNS)
    expected_clean_columns = [c for c in EXPECTED_INPUT_COLUMNS if c not in REMOVED_SCORE_COLUMNS]
    if list(clean.columns) != expected_clean_columns:
        raise GateFailure("Clean master columns did not match expected post-removal schema")
    if len(clean.columns) != 19:
        raise GateFailure(f"Expected 19 clean columns, got {len(clean.columns)}")
    if list(map(tuple, clean[KEY_COLUMNS].to_numpy())) != list(map(tuple, df[KEY_COLUMNS].to_numpy())):
        raise GateFailure("Clean master key order does not match source snapshot")
    if not clean.equals(df[expected_clean_columns]):
        raise GateFailure("Clean master changed non-score column values")
    return clean


def write_receipt(
    *,
    source_path: Path,
    clean_path: Path,
    receipt_path: Path,
    source_sha: str,
    clean_sha: str,
    source_df: pd.DataFrame,
    clean_df: pd.DataFrame,
) -> dict[str, object]:
    receipt = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "generator": rel(Path(__file__)),
        "source_master": {
            "path": rel(source_path),
            "sha256": source_sha,
            "rows": int(len(source_df)),
            "columns": list(source_df.columns),
            "column_count": int(len(source_df.columns)),
            "correct_total": int(pd.to_numeric(source_df["final_score_authoritative"], errors="raise").sum()),
        },
        "clean_adjudication_master": {
            "path": rel(clean_path),
            "sha256": clean_sha,
            "rows": int(len(clean_df)),
            "columns": list(clean_df.columns),
            "column_count": int(len(clean_df.columns)),
            "correct_total": int(pd.to_numeric(clean_df["final_score_authoritative"], errors="raise").sum()),
        },
        "removed_columns": REMOVED_SCORE_COLUMNS,
        "row_order_preserved": True,
        "non_score_values_preserved": True,
        "source_master_mutated": False,
        "stale_score_gate": {
            "forbidden_columns": sorted(FORBIDDEN_SCORE_COLUMNS),
            "forbidden_prefixes": ["normalization_"],
            "passed": True,
        },
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input final long master CSV.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Score1000 output directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_path = args.input.resolve()
    out_dir = args.out_dir.resolve()
    clean_path = out_dir / "radle_v2_clean_adjudication_master.csv"
    receipt_path = out_dir / "adjudication_master_cleanup_receipt.json"

    if not source_path.exists():
        raise GateFailure(f"Input master not found: {source_path}")
    out_dir.mkdir(parents=True, exist_ok=True)

    source_sha = sha256_file(source_path)
    source_df = read_csv_text(source_path)
    validate_input_snapshot(source_path, source_df, source_sha)

    clean_df = build_clean_master(source_df)
    clean_df.to_csv(clean_path, index=False)

    clean_readback = read_csv_text(clean_path)
    if list(clean_readback.columns) != list(clean_df.columns) or len(clean_readback) != len(clean_df):
        raise GateFailure("Clean master readback shape mismatch")
    if not clean_readback.equals(clean_df):
        raise GateFailure("Clean master readback values differ from generated frame")

    clean_sha = sha256_file(clean_path)
    write_receipt(
        source_path=source_path,
        clean_path=clean_path,
        receipt_path=receipt_path,
        source_sha=source_sha,
        clean_sha=clean_sha,
        source_df=source_df,
        clean_df=clean_df,
    )

    print(
        f"[PASS] input snapshot rows={len(source_df)} cols={len(source_df.columns)} "
        f"sha256={source_sha}"
    )
    print(
        f"[PASS] clean adjudication master rows={len(clean_df)} cols={len(clean_df.columns)} "
        f"correct={int(pd.to_numeric(clean_df['final_score_authoritative'], errors='raise').sum())}"
    )
    print(f"[PASS] removed stale score columns: {', '.join(REMOVED_SCORE_COLUMNS)}")
    print(f"[PASS] wrote {rel(clean_path)}")
    print(f"[PASS] wrote {rel(receipt_path)}")


if __name__ == "__main__":
    main()
