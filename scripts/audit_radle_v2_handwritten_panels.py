#!/usr/bin/env python3
"""Audit RadLE v2 handwritten SVG confidence-panel artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd


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

CRITERIA = ("qual_human200",)
INACTIVE_CRITERIA = ("experience",)
SVG_NS = "{http://www.w3.org/2000/svg}"
PANEL_FILES = [
    "panel_1_strict_confidence_outcomes.svg",
    "panel_2_strict_safety_shield.svg",
    "panel_3_strict_peak_certainty_ppv.svg",
]
REQUIRED_FILES = [
    "qual_human200_weighted_source_master.csv",
    "group_summary.csv",
    "seniority_tier_summary.csv",
    "confidence_outcome_summary.csv",
    "stats_provenance.json",
    *PANEL_FILES,
    "contact_sheet.html",
    "captions.md",
    "figure_manifest.json",
    "data_provenance.md",
    "reviewer_checklist.md",
    "font_sizes.csv",
    "handwritten_panels_qa.txt",
]
MOJIBAKE_MARKERS = ["\ufffd", "Ã¢", "Ãƒ", "Ã‚", "\ufeff"]
STALE_MARKERS = [
    "RadLE Stats",
    "Handwritten SVG Panels",
    "outputs/Raw Outputs",
    "outputs\\Raw Outputs",
    "results_table.csv",
    "long_format.csv",
]
READER_FACING_BANNED = [
    "strict old-panel",
    "strict old",
    "old-panel",
    "old panel",
    "old-reference",
    "creative companion",
    "implementation",
    "generator",
    "variant",
    "source_csv",
    "deployment risk",
    "deployed",
    "hallucination",
    "safety shield",
    "verified safe",
    "protected cases",
    "protected",
    "protection versus",
    "hazard",
    "misleading hazard",
    "misleading hallucination",
]
REQUIRED_VISIBLE_HUMAN_LABELS = {
    "qual_human200": [
        "Board-certified radiologists",
        "Radiology trainees",
    ],
}

EXPECTED_GROUPS = {
    "qual_human200": [
        ("Radiology Trainees", ["PGY2", "PGY3"], 200.0, 458 / 6, "38.17"),
        (
            "Post-MD Radiologists",
            ["6mo post-MD", "2y post-MD", "3y post-MD", "4y post-MD", "7y post-MD"],
            200.0,
            466 / 6,
            "38.83",
        ),
    ],
}

NUMERIC_CONFIDENCE_KEYS = [
    "row_order",
    "n_raters",
    "normalization_divisor",
    "n",
    "n_correct",
    "peak_wrong_n",
    "peak_correct_n",
    "cautious_n",
    "deferred_n",
    "n_peak_conf",
    "verified_safe_n",
    "safe_uncertainty_n",
    "misleading_hazard_n",
    "confidence_volume_n",
]
STRING_CONFIDENCE_KEYS = [
    "row_kind",
    "display_name",
    "display_label",
    "group",
    "members",
    "candidate",
    "provider",
    "access",
    "domain",
    "normalization_mode",
    "normalization_unit",
    "accuracy_pct_label",
    "ppv_correct_label",
    "ppv_wrong_label",
]

NORMALIZED_COUNT_COLUMNS = [
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


class AuditFailure(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise AuditFailure(f"Missing CSV: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def close_enough(actual: object, expected: object, tolerance: float = 1e-4) -> bool:
    return abs(float(actual) - float(expected)) <= tolerance


def count_label(value: object) -> str:
    numeric = float(value)
    if abs(numeric - round(numeric)) < 1e-6:
        return str(int(round(numeric)))
    return f"{numeric:.1f}"


def audit_normalized_count_columns(row: dict[str, str], context: str) -> None:
    if row.get("normalization_mode") != "human_mean_per_reader_200":
        return
    divisor = float(row.get("normalization_divisor", 0) or 0)
    if divisor <= 0:
        raise AuditFailure(f"{context}: invalid normalization_divisor {divisor}")
    for column in NORMALIZED_COUNT_COLUMNS:
        source_column = f"source_{column}"
        if column not in row or source_column not in row:
            continue
        if str(row[source_column]).strip() == "":
            continue
        expected = float(row[source_column]) / divisor
        if not close_enough(row[column], expected):
            raise AuditFailure(
                f"{context}: {column} expected source/divisor {expected}, got {row[column]}"
            )


def write_note(out_root: Path, phase: str, lines: list[str]) -> Path:
    path = out_root / f"handwritten_panels_audit_{phase}.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


def assert_contains(path: Path, expected: str) -> None:
    text = path.read_text(encoding="utf-8")
    if expected not in text:
        raise AuditFailure(f"{path} does not contain required text: {expected}")


def scan_text_file(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    issues: list[str] = []
    for marker in MOJIBAKE_MARKERS:
        if marker in raw:
            issues.append(f"mojibake marker {marker!r}")
    for marker in STALE_MARKERS:
        if marker in raw:
            issues.append(f"stale marker {marker!r}")
    return issues


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "metadata"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "metadata"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth and data.strip():
            self.parts.append(data.strip())


def svg_reader_text(path: Path) -> str:
    root = ET.parse(path).getroot()
    parts: list[str] = []
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag in {"title", "desc", "text", "tspan"} and elem.text:
            parts.append(elem.text)
    return "\n".join(parts)


def html_reader_text(path: Path) -> str:
    parser = VisibleTextParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return "\n".join(parser.parts)


def assert_reader_facing_copy(criterion: str, out_dir: Path) -> None:
    reader_texts: list[tuple[Path, str]] = []
    for filename in PANEL_FILES:
        reader_texts.append((out_dir / filename, svg_reader_text(out_dir / filename)))
    reader_texts.append((out_dir / "captions.md", (out_dir / "captions.md").read_text(encoding="utf-8")))
    reader_texts.append((out_dir / "contact_sheet.html", html_reader_text(out_dir / "contact_sheet.html")))

    combined = "\n".join(text for _, text in reader_texts)
    combined_lower = combined.lower()
    for marker in READER_FACING_BANNED:
        if marker.lower() in combined_lower:
            offenders = [
                str(path)
                for path, text in reader_texts
                if marker.lower() in text.lower()
            ]
            raise AuditFailure(
                f"reader-facing banned phrase {marker!r} appears in {', '.join(offenders)}"
            )
    for label in REQUIRED_VISIBLE_HUMAN_LABELS[criterion]:
        if label not in combined:
            raise AuditFailure(f"reader-facing human label missing: {label}")


def audit_preflight(master: Path) -> list[str]:
    lines = ["PHASE preflight", f"timestamp_utc={utc_now()}"]
    if not master.exists():
        raise AuditFailure(f"Master CSV not found: {master}")
    digest = sha256_file(master)
    if digest != EXPECTED_MASTER_SHA256:
        raise AuditFailure(f"Master SHA mismatch: expected {EXPECTED_MASTER_SHA256}, got {digest}")
    df = pd.read_csv(master)
    if len(df) != 6000 or len(df.columns) != 20:
        raise AuditFailure(f"Master shape mismatch: rows={len(df)} cols={len(df.columns)}")
    required = {
        "candidate",
        "provider",
        "access",
        "domain",
        "likert",
        "score_required",
        "abstained",
        "technical_failure",
        "final_score_authoritative",
        "rater_seniority",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise AuditFailure(f"Master missing required columns: {missing}")
    scores = pd.to_numeric(df["final_score_authoritative"], errors="raise").astype(int)
    if sorted(scores.unique().tolist()) != [0, 1]:
        raise AuditFailure("final_score_authoritative must contain only 0/1")
    correct = int((scores == 1).sum())
    if correct != 1255:
        raise AuditFailure(f"Master correct total mismatch: {correct}")
    lines.append(f"[PASS] master rows=6000 cols=20 correct=1255 sha256={digest}")
    return lines


def audit_group_rows(criterion: str, group_rows: list[dict[str, str]], tier_rows: list[dict[str, str]], lines: list[str]) -> None:
    by_group = {row["group"]: row for row in group_rows}
    for group, members, expected_n, expected_correct, expected_pct in EXPECTED_GROUPS[criterion]:
        row = by_group.get(group)
        if not row:
            raise AuditFailure(f"{criterion}: missing group {group}")
        actual_members = [value.strip() for value in row["members"].split(";")]
        if actual_members != members:
            raise AuditFailure(f"{criterion} {group}: members expected {members}, got {actual_members}")
        if not close_enough(row["n"], expected_n):
            raise AuditFailure(f"{criterion} {group}: n expected {expected_n}, got {row['n']}")
        if not close_enough(row["n_correct"], expected_correct):
            raise AuditFailure(f"{criterion} {group}: correct expected {expected_correct}, got {row['n_correct']}")
        if row["accuracy_pct_label"] != expected_pct:
            raise AuditFailure(f"{criterion} {group}: pct expected {expected_pct}, got {row['accuracy_pct_label']}")
        if row.get("normalization_mode") != "human_mean_per_reader_200":
            raise AuditFailure(f"{criterion} {group}: missing human200 normalization mode")
        if not close_enough(row.get("normalization_divisor", 0), row["n_raters"]):
            raise AuditFailure(f"{criterion} {group}: normalization divisor does not match n_raters")
        audit_normalized_count_columns(row, f"{criterion} group_summary {group}")
        lines.append(
            f"[PASS] {criterion} {group} {expected_correct:.2f}/{expected_n:.2f} {expected_pct}%"
        )
    if len(tier_rows) != 7:
        raise AuditFailure(f"{criterion}: expected 7 tier rows, got {len(tier_rows)}")
    for tier_row in tier_rows:
        audit_normalized_count_columns(
            tier_row, f"{criterion} seniority_tier_summary {tier_row['tier']}"
        )
    if not close_enough(sum(float(row["n"]) for row in group_rows), 400.0):
        raise AuditFailure(f"{criterion}: grouped effective n does not sum to 400")
    if not close_enough(sum(float(row["n_correct"]) for row in group_rows), 924 / 6):
        raise AuditFailure(f"{criterion}: grouped effective correct does not sum to {924 / 6}")


def audit_confidence_rows(criterion: str, rows: list[dict[str, str]], lines: list[str]) -> None:
    if len(rows) != 17:
        raise AuditFailure(f"{criterion}: expected 17 confidence rows, got {len(rows)}")
    model_rows = [row for row in rows if row["row_kind"] == "model"]
    human_rows = [row for row in rows if row["row_kind"] == "human_comparator"]
    if len(model_rows) != 15:
        raise AuditFailure(f"{criterion}: expected 15 model confidence rows, got {len(model_rows)}")
    if len(human_rows) != 2:
        raise AuditFailure(f"{criterion}: expected 2 human comparator rows, got {len(human_rows)}")
    if not close_enough(sum(float(row["n"]) for row in model_rows), 3000.0):
        raise AuditFailure(f"{criterion}: model rows should sum to n=3000")
    for row in human_rows:
        if row.get("normalization_mode") != "human_mean_per_reader_200":
            raise AuditFailure(f"{criterion} {row['display_name']}: missing human200 normalization")
        if not close_enough(row["n"], 200.0):
            raise AuditFailure(f"{criterion} {row['display_name']}: expected effective n=200, got {row['n']}")
        audit_normalized_count_columns(row, f"{criterion} confidence_summary {row['display_name']}")
    for row in rows:
        n = float(row["n"])
        peak_wrong = float(row["peak_wrong_n"])
        peak_correct = float(row["peak_correct_n"])
        cautious = float(row["cautious_n"])
        deferred = float(row["deferred_n"])
        if not close_enough(peak_wrong + peak_correct + cautious + deferred, n):
            raise AuditFailure(f"{criterion} {row['display_name']}: confidence buckets do not sum to n")
        if not close_enough(row["n_peak_conf"], peak_wrong + peak_correct):
            raise AuditFailure(f"{criterion} {row['display_name']}: peak denominator mismatch")
        if not close_enough(row["verified_safe_n"], peak_correct):
            raise AuditFailure(f"{criterion} {row['display_name']}: confident-correct bucket mismatch")
        if not close_enough(row["misleading_hazard_n"], peak_wrong):
            raise AuditFailure(f"{criterion} {row['display_name']}: confident-error bucket mismatch")
        if not close_enough(row["safe_uncertainty_n"], cautious + deferred):
            raise AuditFailure(f"{criterion} {row['display_name']}: safe uncertainty mismatch")
        peak = float(row["n_peak_conf"])
        if peak:
            expected_ppv = f"{round(100 * peak_correct / peak):.0f}%"
            expected_wrong = f"{round(100 * peak_wrong / peak):.0f}%"
            if row["ppv_correct_label"] != expected_ppv or row["ppv_wrong_label"] != expected_wrong:
                raise AuditFailure(f"{criterion} {row['display_name']}: PPV labels mismatch")
    expected_humans = {group[0] for group in EXPECTED_GROUPS[criterion]}
    actual_humans = {row["display_name"] for row in human_rows}
    if actual_humans != expected_humans:
        raise AuditFailure(f"{criterion}: human comparator rows expected {expected_humans}, got {actual_humans}")
    actual_labels = {row["display_label"] for row in human_rows}
    expected_labels = set(REQUIRED_VISIBLE_HUMAN_LABELS[criterion])
    if actual_labels != expected_labels:
        raise AuditFailure(f"{criterion}: human display labels expected {expected_labels}, got {actual_labels}")
    lines.append(f"[PASS] {criterion} confidence rows: 15 model + 2 human comparator rows")


def audit_post_stats(out_root: Path) -> list[str]:
    lines = ["PHASE post-stats", f"timestamp_utc={utc_now()}"]
    for criterion in CRITERIA:
        out_dir = out_root / criterion
        group_rows = read_csv(out_dir / "group_summary.csv")
        tier_rows = read_csv(out_dir / "seniority_tier_summary.csv")
        confidence_rows = read_csv(out_dir / "confidence_outcome_summary.csv")
        prov = json.loads((out_dir / "stats_provenance.json").read_text(encoding="utf-8"))
        if prov.get("master_sha256") != EXPECTED_MASTER_SHA256:
            raise AuditFailure(f"{criterion}: stats_provenance missing expected master SHA")
        weighted_source_name = prov.get("weighted_source_file")
        if weighted_source_name != "qual_human200_weighted_source_master.csv":
            raise AuditFailure(f"{criterion}: missing weighted source file provenance")
        weighted_source = pd.read_csv(out_dir / str(weighted_source_name))
        original_columns = pd.read_csv(DEFAULT_MASTER, nrows=0).columns.tolist()
        missing_original = [column for column in original_columns if column not in weighted_source.columns]
        if missing_original:
            raise AuditFailure(f"{criterion}: weighted source missing master columns {missing_original}")
        if len(weighted_source) != 5400:
            raise AuditFailure(f"{criterion}: weighted source expected 5400 rows, got {len(weighted_source)}")
        human_source = weighted_source[weighted_source["normalization_row_kind"] == "human_comparator"]
        by_label = human_source.groupby("normalization_display_label")["normalization_weight"].sum().round(6).to_dict()
        expected_weights = {
            "Board-certified radiologists": 200.0,
            "Radiology trainees": 200.0,
        }
        for label, expected_weight in expected_weights.items():
            if not close_enough(by_label.get(label, -1), expected_weight):
                raise AuditFailure(
                    f"{criterion}: weighted source effective n for {label} expected {expected_weight}, got {by_label.get(label)}"
                )
        audit_group_rows(criterion, group_rows, tier_rows, lines)
        audit_confidence_rows(criterion, confidence_rows, lines)
    return lines


def parse_svg(path: Path) -> tuple[ET.Element, dict[str, object]]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise AuditFailure(f"SVG XML parse failed for {path}: {exc}") from exc
    metadata = root.find(f"{SVG_NS}metadata")
    if metadata is None or not (metadata.text or "").strip():
        raise AuditFailure(f"{path}: missing metadata")
    try:
        payload = json.loads(html.unescape(metadata.text or ""))
    except json.JSONDecodeError as exc:
        raise AuditFailure(f"{path}: metadata is not valid JSON") from exc
    return root, payload


def audit_svg_geometry(path: Path, root: ET.Element) -> list[str]:
    issues: list[str] = []
    width = float(root.get("width", "0"))
    height = float(root.get("height", "0"))
    if width != 3600 or height != 2700:
        issues.append(f"unexpected canvas {width}x{height}")
    for elem in list(root.iter()):
        tag = elem.tag.split("}")[-1]
        if tag == "text":
            x = float(elem.get("x", "0"))
            y = float(elem.get("y", "0"))
            if not (20 <= x <= width - 20 and 20 <= y <= height - 20):
                issues.append(f"text out of frame at x={x:g} y={y:g}")
        elif tag == "rect":
            x = float(elem.get("x", "0"))
            y = float(elem.get("y", "0"))
            w = float(elem.get("width", "0"))
            h = float(elem.get("height", "0"))
            if x < 0 or y < 0 or x + w > width + 1 or y + h > height + 1:
                issues.append(f"rect out of canvas at x={x:g} y={y:g} w={w:g} h={h:g}")
        elif tag == "line":
            x1 = float(elem.get("x1", "0"))
            y1 = float(elem.get("y1", "0"))
            x2 = float(elem.get("x2", "0"))
            y2 = float(elem.get("y2", "0"))
            if min(x1, x2) < 0 or max(x1, x2) > width + 1 or min(y1, y2) < 0 or max(y1, y2) > height + 1:
                issues.append(f"line out of canvas at x1={x1:g} y1={y1:g} x2={x2:g} y2={y2:g}")
        elif tag == "circle":
            cx = float(elem.get("cx", "0"))
            cy = float(elem.get("cy", "0"))
            r = float(elem.get("r", "0"))
            if cx - r < 0 or cx + r > width + 1 or cy - r < 0 or cy + r > height + 1:
                issues.append(f"circle out of canvas at cx={cx:g} cy={cy:g} r={r:g}")
    return [f"{path.name}: {issue}" for issue in issues]


def svg_text_lines(elem: ET.Element) -> list[str]:
    lines: list[str] = []
    if elem.text and elem.text.strip():
        lines.append(elem.text.strip())
    for child in elem:
        tag = child.tag.split("}")[-1]
        if tag == "tspan" and child.text and child.text.strip():
            lines.append(child.text.strip())
    return lines


def audit_unwrapped_human_labels(criterion: str, path: Path, root: ET.Element) -> None:
    row_label_lines: list[str] = []
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag == "text" and elem.get("class", "") == "row-label":
            row_label_lines.extend(svg_text_lines(elem))
    for label in REQUIRED_VISIBLE_HUMAN_LABELS[criterion]:
        if label not in row_label_lines:
            raise AuditFailure(f"{path}: human row label is missing or wrapped: {label}")


def audit_metadata_against_csv(criterion: str, payload: dict[str, object], csv_rows: list[dict[str, str]], path: Path) -> None:
    if payload.get("criterion") != criterion:
        raise AuditFailure(f"{path}: metadata criterion mismatch")
    if payload.get("master_sha256") != EXPECTED_MASTER_SHA256:
        raise AuditFailure(f"{path}: metadata missing expected master SHA")
    if payload.get("source_csv") != "confidence_outcome_summary.csv":
        raise AuditFailure(f"{path}: metadata source_csv mismatch")
    payload_rows = payload.get("rows")
    if not isinstance(payload_rows, list) or len(payload_rows) != len(csv_rows):
        raise AuditFailure(f"{path}: metadata row count mismatch")
    by_name = {row["display_name"]: row for row in csv_rows}
    for item in payload_rows:
        if not isinstance(item, dict):
            raise AuditFailure(f"{path}: metadata row item is not an object")
        name = str(item.get("display_name", ""))
        row = by_name.get(name)
        if row is None:
            raise AuditFailure(f"{path}: metadata row {name!r} not found in CSV")
        for key in NUMERIC_CONFIDENCE_KEYS:
            expected = float(row[key])
            actual = float(item.get(key, -999999))
            if not close_enough(actual, expected):
                raise AuditFailure(f"{path}: {name} metadata {key} expected {expected}, got {actual}")
        for key in STRING_CONFIDENCE_KEYS:
            expected = str(row[key])
            actual = str(item.get(key, ""))
            if actual != expected:
                raise AuditFailure(f"{path}: {name} metadata {key} expected {expected!r}, got {actual!r}")


def audit_post_svg(out_root: Path) -> list[str]:
    lines = ["PHASE post-svg", f"timestamp_utc={utc_now()}"]
    for criterion in INACTIVE_CRITERIA:
        inactive_dir = out_root / criterion
        if inactive_dir.exists():
            raise AuditFailure(f"inactive artifact root still exists: {inactive_dir}")
    for criterion in CRITERIA:
        out_dir = out_root / criterion
        missing = [name for name in REQUIRED_FILES if not (out_dir / name).exists()]
        if missing:
            raise AuditFailure(f"{criterion}: missing required files: {', '.join(missing)}")
        extra_panels = sorted(path.name for path in out_dir.glob("panel_*.svg") if path.name not in PANEL_FILES)
        if extra_panels:
            raise AuditFailure(f"{criterion}: stale panel SVG files remain: {extra_panels}")
        manifest = json.loads((out_dir / "figure_manifest.json").read_text(encoding="utf-8"))
        if manifest.get("master_sha256") != EXPECTED_MASTER_SHA256:
            raise AuditFailure(f"{criterion}: manifest missing expected master SHA")
        assert_contains(out_dir / "data_provenance.md", EXPECTED_MASTER_SHA256)
        assert_contains(out_dir / "data_provenance.md", "confidence_outcome_summary.csv")

        text_files = [
            path
            for path in out_dir.iterdir()
            if path.suffix.lower() in {".svg", ".html", ".md", ".json", ".txt", ".csv"}
        ]
        for path in text_files:
            issues = scan_text_file(path)
            if issues:
                raise AuditFailure(f"{path}: {'; '.join(issues)}")
        assert_reader_facing_copy(criterion, out_dir)

        csv_rows = read_csv(out_dir / "confidence_outcome_summary.csv")
        manifest_panels = {panel["file"]: panel for panel in manifest.get("panels", [])}
        if sorted(manifest_panels) != sorted(PANEL_FILES):
            raise AuditFailure(f"{criterion}: manifest panel file set mismatch")
        for filename in PANEL_FILES:
            path = out_dir / filename
            root, payload = parse_svg(path)
            audit_metadata_against_csv(criterion, payload, csv_rows, path)
            expected_sha = manifest_panels.get(filename, {}).get("sha256")
            actual_sha = sha256_text(path)
            if expected_sha != actual_sha:
                raise AuditFailure(f"{path}: manifest SHA mismatch expected {expected_sha}, got {actual_sha}")
            geometry_issues = audit_svg_geometry(path, root)
            if geometry_issues:
                raise AuditFailure("; ".join(geometry_issues))
            audit_unwrapped_human_labels(criterion, path, root)
            lines.append(f"[PASS] {criterion} {filename} XML/metadata/hash")
    return lines


def required_caption_tokens(criterion: str, rows: list[dict[str, str]]) -> set[str]:
    tokens = {EXPECTED_MASTER_SHA256, "confidence_outcome_summary.csv"}
    tokens.add("Human comparator rows are effective n=200 averages")
    for row in rows:
        if row["row_kind"] != "human_comparator":
            continue
        label = row["display_label"]
        tokens.add(f"{label} confident error {count_label(row['peak_wrong_n'])}/{count_label(row['n'])}")
        tokens.add(f"{label} PPV {row['ppv_correct_label']} (n={count_label(row['n_peak_conf'])})")
        safe_answers = float(row["verified_safe_n"]) + float(row["safe_uncertainty_n"])
        tokens.add(f"{label} safe answers {count_label(safe_answers)}/{count_label(row['n'])}")
    return tokens


def audit_final_reconcile(out_root: Path) -> list[str]:
    lines = ["PHASE final-reconcile", f"timestamp_utc={utc_now()}"]
    for criterion in INACTIVE_CRITERIA:
        inactive_dir = out_root / criterion
        if inactive_dir.exists():
            raise AuditFailure(f"inactive artifact root still exists: {inactive_dir}")
    for criterion in CRITERIA:
        out_dir = out_root / criterion
        csv_rows = read_csv(out_dir / "confidence_outcome_summary.csv")
        captions_text = (out_dir / "captions.md").read_text(encoding="utf-8")
        manifest_text = (out_dir / "figure_manifest.json").read_text(encoding="utf-8")
        provenance_text = (out_dir / "data_provenance.md").read_text(encoding="utf-8")
        svg_text = "\n".join((out_dir / filename).read_text(encoding="utf-8") for filename in PANEL_FILES)

        for token in required_caption_tokens(criterion, csv_rows):
            if token not in captions_text and token not in manifest_text and token not in provenance_text:
                raise AuditFailure(f"{criterion}: missing reconciliation token {token!r}")
        for filename in PANEL_FILES:
            _, payload = parse_svg(out_dir / filename)
            audit_metadata_against_csv(criterion, payload, csv_rows, out_dir / filename)
        if EXPECTED_MASTER_SHA256 not in manifest_text or EXPECTED_MASTER_SHA256 not in provenance_text:
            raise AuditFailure(f"{criterion}: manifest/provenance missing master SHA")
        assert_reader_facing_copy(criterion, out_dir)
        if "Experienced Post-MD" in svg_text + captions_text:
            raise AuditFailure("qual artifacts mention experience-only group Experienced Post-MD")
        lines.append(f"[PASS] {criterion} captions, manifest, provenance, and SVG metadata reconcile to confidence CSV")
    return lines


def audit_visual_qa(out_root: Path) -> list[str]:
    lines = ["PHASE visual-qa", f"timestamp_utc={utc_now()}"]
    render_dir = out_root / "_visual_qa"
    render_dir.mkdir(parents=True, exist_ok=True)
    active_pngs = {f"{criterion}_contact_sheet.png" for criterion in CRITERIA}
    for stale_png in render_dir.glob("*_contact_sheet.png"):
        if stale_png.name not in active_pngs:
            stale_png.unlink()
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - depends on local optional dep
        raise AuditFailure(f"playwright is required for visual-qa render: {exc}") from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1500, "height": 2300}, device_scale_factor=1)
        for criterion in CRITERIA:
            url = (out_root / criterion / "contact_sheet.html").resolve().as_uri()
            page.goto(url, wait_until="networkidle")
            screenshot = render_dir / f"{criterion}_contact_sheet.png"
            page.screenshot(path=str(screenshot), full_page=True)
            lines.append(f"[PASS] rendered {screenshot}")
        browser.close()
    lines.append("Fresh render inspected by script: screenshots created. Human visual inspection still required.")
    return lines


def run_phase(phase: str, master: Path, out_root: Path) -> list[str]:
    if phase == "preflight":
        return audit_preflight(master)
    if phase == "post-stats":
        return audit_post_stats(out_root)
    if phase == "post-svg":
        return audit_post_svg(out_root)
    if phase == "final-reconcile":
        return audit_final_reconcile(out_root)
    if phase == "visual-qa":
        return audit_visual_qa(out_root)
    if phase == "all":
        lines: list[str] = []
        for subphase in ["preflight", "post-stats", "post-svg", "final-reconcile", "visual-qa"]:
            lines.extend(run_phase(subphase, master, out_root))
        return lines
    raise AuditFailure(f"Unknown phase: {phase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument(
        "--phase",
        choices=["preflight", "post-stats", "post-svg", "visual-qa", "final-reconcile", "all"],
        default="all",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    master = args.master.resolve()
    out_root = args.out_root.resolve()
    try:
        lines = run_phase(args.phase, master, out_root)
    except AuditFailure as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1) from exc
    note = write_note(out_root, args.phase, lines)
    for line in lines:
        print(line)
    print(f"[PASS] wrote audit note {note}")


if __name__ == "__main__":
    main()
