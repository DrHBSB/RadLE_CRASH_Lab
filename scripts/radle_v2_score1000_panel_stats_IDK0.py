#!/usr/bin/env python3
"""Build Score1000-native summary CSVs for RadLE v2 handwritten panels 2/3."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE_ROOT = (
    REPO_ROOT
    / "outputs"
    / "radle_v2_stats"
    / "final_scoring_radiologist_20260706_001147"
    / "likert5_score1000"
)
DEFAULT_OUT_DIR = DEFAULT_SCORE_ROOT / "handwritten_panels"
EXPECTED_SOURCE_SHA256 = "7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED"
EXPECTED_SCORING_ROWS = 5600
EFFECTIVE_CASES_PER_ROW = 200
DOT_DISPLAY_TOTAL = 100
SCORE2000_SHIFT = 1000
EXPECTED_COMPARATORS = 17

CORRECT_BINS = ["correct_l4", "correct_l3", "correct_l2", "correct_l1", "correct_l0"]
WRONG_BINS = ["wrong_l0", "wrong_l1", "wrong_l2", "wrong_l3", "wrong_l4"]
NEUTRAL_BIN = "neutral"
BIN_COLUMNS = [*CORRECT_BINS, NEUTRAL_BIN, *WRONG_BINS]
DOT_COLUMNS = [f"dot_{column}" for column in BIN_COLUMNS]
SUMMARY_COLUMNS = [
    "rank",
    "reader_type",
    "reader_label",
    "provider",
    "access",
    "domain",
    "n_readers",
    "raw_observations",
    "effective_cases",
    "final_score1000",
    "score2000",
    *BIN_COLUMNS,
    "correct_total",
    "neutral_total",
    "wrong_total",
    *DOT_COLUMNS,
    "dot_total",
]
NEUTRAL_STATUSES = {
    "abstention_idk_zero",
    "abstention_idk_typo_zero",
    "invalid_likert_zero",
    "technical_failure_zero",
}
VALID_STATUSES = {"valid_likert_correct", "valid_likert_wrong"}


class StatsFailure(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise StatsFailure(f"Missing CSV: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fraction_from_decimal(text: str) -> Fraction:
    return Fraction(str(text))


def fraction_to_export(value: Fraction, digits: int = 6) -> str:
    number = round(float(value), digits)
    if number == 0:
        number = 0.0
    text = f"{number:.{digits}f}".rstrip("0").rstrip(".")
    return text if text else "0"


def parse_likert(value: str) -> int | None:
    text = str(value).strip()
    if text == "":
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if not number.is_integer():
        return None
    return int(number)


def bin_for_row(row: dict[str, str]) -> str:
    status = row["score1000_status"]
    if status in NEUTRAL_STATUSES:
        return NEUTRAL_BIN
    if status not in VALID_STATUSES:
        raise StatsFailure(f"Unexpected Score1000 status: {status}")
    likert = parse_likert(row["score1000_likert_int"])
    if likert not in {0, 1, 2, 3, 4}:
        raise StatsFailure(f"Valid row has invalid likert {row['score1000_likert_int']!r}")
    if status == "valid_likert_correct":
        return f"correct_l{likert}"
    return f"wrong_l{likert}"


def effective_weight(row: dict[str, str]) -> Fraction:
    return Fraction(1, int(row["score1000_n_readers_in_group"]))


def display_key(row: dict[str, str]) -> tuple[str, str]:
    if row["score1000_row_kind"] == "human_comparator":
        return ("Human comparator", row["score1000_group"])
    return ("AI model", row["candidate"])


def largest_remainder(values: dict[str, Fraction], total: int = DOT_DISPLAY_TOTAL) -> dict[str, int]:
    floors = {key: int(value) for key, value in values.items()}
    remainder = total - sum(floors.values())
    if remainder < 0:
        raise StatsFailure(f"Dot floors exceed total {total}: {sum(floors.values())}")
    ranked = sorted(
        values,
        key=lambda key: (values[key] - floors[key], -BIN_COLUMNS.index(key)),
        reverse=True,
    )
    out = dict(floors)
    for key in ranked[:remainder]:
        out[key] += 1
    if sum(out.values()) != total:
        raise StatsFailure(f"Dot apportionment expected {total}, got {sum(out.values())}")
    return out


def identity_rows(group_summary: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = sorted(group_summary, key=lambda row: int(float(row["rank"])))
    if len(rows) != EXPECTED_COMPARATORS:
        raise StatsFailure(f"Expected {EXPECTED_COMPARATORS} comparator rows, got {len(rows)}")
    expected_labels = [
        row["reader_label"]
        for row in sorted(
            rows,
            key=lambda row: (-float(row["score2000"]), row["reader_label"]),
        )
    ]
    actual_labels = [row["reader_label"] for row in rows]
    if actual_labels != expected_labels:
        raise StatsFailure("Group summary rank order is not sorted by score2000 descending")
    for row in rows:
        if Fraction(row["score2000"]) != Fraction(row["final_score1000"]) + SCORE2000_SHIFT:
            raise StatsFailure(f"{row['reader_label']}: score2000 must equal final_score1000 + 1000")
    return rows


def build_summary(scored_rows: list[dict[str, str]], group_summary: list[dict[str, str]]) -> list[dict[str, object]]:
    if len(scored_rows) != EXPECTED_SCORING_ROWS:
        raise StatsFailure(f"Expected {EXPECTED_SCORING_ROWS} scored rows, got {len(scored_rows)}")

    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in scored_rows:
        grouped.setdefault(display_key(row), []).append(row)

    out_rows: list[dict[str, object]] = []
    for identity in identity_rows(group_summary):
        key = (identity["reader_type"], identity["reader_label"])
        frame = grouped.get(key)
        if frame is None:
            raise StatsFailure(f"No scored rows for {key}")

        counts = {column: Fraction(0, 1) for column in BIN_COLUMNS}
        for row in frame:
            counts[bin_for_row(row)] += effective_weight(row)

        effective_cases = sum(counts.values(), Fraction(0, 1))
        if effective_cases != Fraction(EFFECTIVE_CASES_PER_ROW, 1):
            raise StatsFailure(f"{key}: expected effective_cases={EFFECTIVE_CASES_PER_ROW}, got {effective_cases}")

        correct_total = sum((counts[column] for column in CORRECT_BINS), Fraction(0, 1))
        wrong_total = sum((counts[column] for column in WRONG_BINS), Fraction(0, 1))
        neutral_total = counts[NEUTRAL_BIN]
        if correct_total + wrong_total + neutral_total != Fraction(EFFECTIVE_CASES_PER_ROW, 1):
            raise StatsFailure(f"{key}: bin totals do not sum to {EFFECTIVE_CASES_PER_ROW}")
        dot_values = {
            column: counts[column] * DOT_DISPLAY_TOTAL / EFFECTIVE_CASES_PER_ROW
            for column in BIN_COLUMNS
        }
        dots = largest_remainder(dot_values)

        out: dict[str, object] = {
            "rank": int(float(identity["rank"])),
            "reader_type": identity["reader_type"],
            "reader_label": identity["reader_label"],
            "provider": identity["provider"],
            "access": identity["access"],
            "domain": identity["domain"],
            "n_readers": int(float(identity["n_readers"])),
            "raw_observations": len(frame),
            "effective_cases": str(EFFECTIVE_CASES_PER_ROW),
            "final_score1000": identity["final_score1000"],
            "score2000": identity["score2000"],
            "correct_total": fraction_to_export(correct_total),
            "neutral_total": fraction_to_export(neutral_total),
            "wrong_total": fraction_to_export(wrong_total),
            "dot_total": DOT_DISPLAY_TOTAL,
        }
        for column in BIN_COLUMNS:
            out[column] = fraction_to_export(counts[column])
            out[f"dot_{column}"] = dots[column]
        out_rows.append(out)

    return out_rows


def write_provenance(score_root: Path, out_dir: Path, rows: list[dict[str, object]]) -> None:
    score_prov = json.loads((score_root / "data_provenance.json").read_text(encoding="utf-8"))
    source_sha = str(score_prov["source_master"]["sha256"]).upper()
    if source_sha != EXPECTED_SOURCE_SHA256:
        raise StatsFailure(f"Unexpected source SHA: {source_sha}")
    summary_path = out_dir / "score1000_panel23_bins.csv"
    data = {
        "generated_at": utc_now(),
        "generator": rel(Path(__file__)),
        "output_root": rel(out_dir),
        "score1000_root": rel(score_root),
        "source_master_sha256": source_sha,
        "score1000_scored_rows": {
            "path": rel(score_root / "score1000_scored_rows.csv"),
            "sha256": sha256_file(score_root / "score1000_scored_rows.csv"),
        },
        "summary_csv": {
            "path": rel(summary_path),
            "sha256": sha256_file(summary_path),
            "rows": len(rows),
        },
        "classification": {
            "correct": "valid_likert_correct rows grouped by score1000_likert_int 0..4",
            "wrong": "valid_likert_wrong rows grouped by score1000_likert_int 0..4",
            "neutral": sorted(NEUTRAL_STATUSES),
            "dot_display": "largest-remainder apportionment from exact 200-case bins to exactly 100 percentage display units per row",
            "dot_display_total": DOT_DISPLAY_TOTAL,
            "dot_display_unit": "percentage_point",
        },
        "score2000_rule": {
            "formula": "score2000 = final_score1000 + 1000",
            "display_range": [0, 2000],
            "source_range": [-1000, 1000],
            "rank_preserving": True,
        },
    }
    (out_dir / "score1000_likert_direction_provenance.json").write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def configure_expected_source_sha256(value: str | None) -> None:
    if value is None:
        return
    normalized = value.strip().upper()
    if len(normalized) != 64 or any(char not in "0123456789ABCDEF" for char in normalized):
        raise StatsFailure("--expected-source-sha256 must be a 64-character SHA256 digest")
    global EXPECTED_SOURCE_SHA256
    EXPECTED_SOURCE_SHA256 = normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score-root", type=Path, default=DEFAULT_SCORE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--expected-source-sha256", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_expected_source_sha256(args.expected_source_sha256)
    score_root = args.score_root.resolve()
    out_dir = args.out_dir.resolve()
    scored_rows = read_csv(score_root / "score1000_scored_rows.csv")
    group_summary = read_csv(score_root / "score1000_group_summary.csv")
    summary_rows = build_summary(scored_rows, group_summary)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "score1000_panel23_bins.csv"
    write_csv(summary_path, summary_rows, SUMMARY_COLUMNS)
    write_provenance(score_root, out_dir, summary_rows)
    print(f"[PASS] wrote {summary_path}")
    print("[PASS] every comparator sums to 200 effective cases and 100 percentage display units")


if __name__ == "__main__":
    main()
