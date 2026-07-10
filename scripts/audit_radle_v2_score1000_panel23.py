#!/usr/bin/env python3
"""Audit RadLE v2 Score1000 handwritten Panel 2/3 artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import xml.etree.ElementTree as ET
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
SVG_NS = "{http://www.w3.org/2000/svg}"

PANEL_FILES = [
    "panel_2_score1000_edge_justified_ledger.svg",
    "panel_3_score1000_100_barcode_percentage_strip.svg",
]
REQUIRED_FILES = [
    "score1000_panel23_bins.csv",
    "score1000_likert_direction_provenance.json",
    *PANEL_FILES,
    "contact_sheet.html",
    "captions.md",
    "figure_manifest.json",
    "data_provenance.json",
    "data_provenance.md",
    "reviewer_checklist.md",
    "font_sizes.csv",
    "handwritten_panels_qa.txt",
]
CORRECT_BINS = ["correct_l4", "correct_l3", "correct_l2", "correct_l1", "correct_l0"]
WRONG_BINS = ["wrong_l0", "wrong_l1", "wrong_l2", "wrong_l3", "wrong_l4"]
BIN_COLUMNS = [*CORRECT_BINS, "neutral", *WRONG_BINS]
DOT_COLUMNS = [f"dot_{key}" for key in BIN_COLUMNS]
DOT_DISPLAY_TOTAL = 100
EXPECTED_PANEL3_UNITS = 17 * DOT_DISPLAY_TOTAL
DISPLAY_NAMES = {
    "grok_4_3": "Grok 4.3",
    "claude_fable_5": "Claude Fable 5",
    "gemini_3_1_pro": "Gemini 3.1 Pro",
    "gpt_5_5": "GPT-5.5",
    "octomed_7b": "OctoMed 7B",
    "nemotron_3_omni": "Nemotron 3 Omni",
    "qwen_3_7_plus": "Qwen 3.7 Plus",
    "glm_5v_turbo": "GLM-5V Turbo",
    "minimax_m3": "MiniMax M3",
    "gemma_4_31b": "Gemma 4 31B",
    "medgemma_1_5_4b": "MedGemma 1.5 4B",
    "lingshu_32b": "Lingshu 32B",
    "llama_4_maverick": "Llama 4 Maverick",
    "internvl3_5_8b": "InternVL 3.5 8B",
    "mistral_large_3_2512": "Mistral Large 3 2512",
}
NEUTRAL_STATUSES = {
    "abstention_idk_reward",
    "abstention_idk_typo_reward",
    "invalid_likert_zero",
    "technical_failure_zero",
}
MOJIBAKE_MARKERS = ["\ufffd", "Ã", "Â", "â€", "\ufeff"]
STALE_MARKERS = [
    "confidence_outcome_summary.csv",
    "qual_human200_weighted_source_master.csv",
    "panel_1_",
    "panel_4_",
    "panel_5_",
    "panel_6_",
    "panel_2_score1000_diverging_bar.svg",
    "panel_3_score1000_200_dot_strip.svg",
    "panel_3_score1000_100_dot_percentage_strip.svg",
    "Two Hundred Effective",
    "200 dots per row",
    "Two hundred-dot",
    "One Hundred Percentage Dots",
    "100 dots per row",
    "Deployment Risk",
    "hallucination",
    "Safety Shield",
    "hazard",
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
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest().upper()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise AuditFailure(f"Missing CSV: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def clean_text(value: object) -> str:
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def frac(value: object) -> Fraction:
    return Fraction(clean_text(value) or "0")


def close_enough(actual: object, expected: object, tolerance: float = 1e-4) -> bool:
    return abs(float(actual) - float(expected)) <= tolerance


def parse_likert(value: str) -> int | None:
    text = clean_text(value)
    if not text:
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
        return "neutral"
    likert = parse_likert(row["score1000_likert_int"])
    if likert not in {0, 1, 2, 3, 4}:
        raise AuditFailure(f"Valid scored row has invalid Likert: {row['score1000_likert_int']}")
    if status == "valid_likert_correct":
        return f"correct_l{likert}"
    if status == "valid_likert_wrong":
        return f"wrong_l{likert}"
    raise AuditFailure(f"Unexpected status: {status}")


def display_key(row: dict[str, str]) -> tuple[str, str]:
    if row["score1000_row_kind"] == "human_comparator":
        return ("Human comparator", row["score1000_group"])
    return ("AI model", row["candidate"])


def expected_bins(scored_rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, Fraction]]:
    out: dict[tuple[str, str], dict[str, Fraction]] = {}
    for row in scored_rows:
        key = display_key(row)
        out.setdefault(key, {column: Fraction(0, 1) for column in BIN_COLUMNS})
        out[key][bin_for_row(row)] += Fraction(1, int(row["score1000_n_readers_in_group"]))
    return out


def audit_csv(score_root: Path, out_dir: Path) -> list[dict[str, str]]:
    rows = read_csv(out_dir / "score1000_panel23_bins.csv")
    scored = read_csv(score_root / "score1000_scored_rows.csv")
    if len(rows) != 17:
        raise AuditFailure(f"Expected 17 panel summary rows, got {len(rows)}")
    expected = expected_bins(scored)
    for row in rows:
        key = (row["reader_type"], row["reader_label"])
        if key not in expected:
            raise AuditFailure(f"Unexpected panel row: {key}")
        total = sum((frac(row[column]) for column in BIN_COLUMNS), Fraction(0, 1))
        if not close_enough(total, 200):
            raise AuditFailure(f"{key}: bins sum to {total}, expected 200")
        if not close_enough(row["effective_cases"], 200):
            raise AuditFailure(f"{key}: effective_cases is not 200")
        correct = sum((frac(row[column]) for column in CORRECT_BINS), Fraction(0, 1))
        wrong = sum((frac(row[column]) for column in WRONG_BINS), Fraction(0, 1))
        if not close_enough(row["correct_total"], correct):
            raise AuditFailure(f"{key}: correct_total mismatch")
        if not close_enough(row["wrong_total"], wrong):
            raise AuditFailure(f"{key}: wrong_total mismatch")
        if not close_enough(row["neutral_total"], row["neutral"]):
            raise AuditFailure(f"{key}: neutral_total mismatch")
        for column in BIN_COLUMNS:
            if not close_enough(row[column], expected[key][column]):
                raise AuditFailure(f"{key}: {column} expected {float(expected[key][column])}, got {row[column]}")
        dot_total = sum(int(float(row[column])) for column in DOT_COLUMNS)
        if dot_total != DOT_DISPLAY_TOTAL or int(float(row["dot_total"])) != DOT_DISPLAY_TOTAL:
            raise AuditFailure(f"{key}: expected {DOT_DISPLAY_TOTAL} display units, got {dot_total}/{row['dot_total']}")
    return rows


def scan_text(path: Path) -> None:
    raw = path.read_text(encoding="utf-8", errors="replace")
    for marker in MOJIBAKE_MARKERS:
        if marker in raw:
            raise AuditFailure(f"{path}: mojibake marker {marker!r}")
    for marker in STALE_MARKERS:
        if marker in raw:
            raise AuditFailure(f"{path}: stale marker {marker!r}")


def parse_svg(path: Path) -> tuple[ET.Element, dict[str, object]]:
    root = ET.parse(path).getroot()
    title = root.find(f"{SVG_NS}title")
    desc = root.find(f"{SVG_NS}desc")
    if title is None or not clean_text(title.text):
        raise AuditFailure(f"{path}: missing title")
    if desc is None or not clean_text(desc.text):
        raise AuditFailure(f"{path}: missing desc")
    metadata = root.find(f"{SVG_NS}metadata")
    if metadata is None:
        raise AuditFailure(f"{path}: missing metadata")
    payload = json.loads(html.unescape(metadata.text or ""))
    return root, payload


def audit_panel2_edge_justified(root: ET.Element, path: Path) -> None:
    if root.findall(f".//{SVG_NS}line[@class='centerline']"):
        raise AuditFailure(f"{path}: Panel 2 must be edge-justified, not centerline anchored")
    clip_paths = root.findall(f".//{SVG_NS}clipPath")
    if len(clip_paths) != 17:
        raise AuditFailure(f"{path}: expected 17 row clip paths, got {len(clip_paths)}")
    for clip_path in clip_paths:
        clip_id = clip_path.get("id", "")
        if not clip_id.startswith("panel2-row-"):
            raise AuditFailure(f"{path}: unexpected Panel 2 clip path id {clip_id!r}")
        clip_rect = clip_path.find(f"{SVG_NS}rect")
        if clip_rect is None:
            raise AuditFailure(f"{path}: row clip path missing rounded rect")
        if float(clip_rect.get("rx", "0")) <= 0:
            raise AuditFailure(f"{path}: row clip path must provide rounded outer corners")
    tracks = root.findall(f".//{SVG_NS}rect[@class='track']")
    if len(tracks) != 17:
        raise AuditFailure(f"{path}: expected 17 row tracks, got {len(tracks)}")
    track_by_y = {round(float(track.get("y", "0")) + 7, 1): track for track in tracks}
    segments_by_y: dict[float, list[ET.Element]] = {}
    outlines = root.findall(f".//{SVG_NS}rect[@class='bar-outline']")
    if len(outlines) != 17:
        raise AuditFailure(f"{path}: expected 17 Panel 2 row outlines, got {len(outlines)}")
    for segment in root.findall(f".//{SVG_NS}rect"):
        if segment.get("data-bin") in BIN_COLUMNS:
            if float(segment.get("rx", "0")) != 0:
                raise AuditFailure(f"{path}: internal segment {segment.get('data-bin')} must have rx=0")
            if (segment.get("stroke") or "").lower() != "none":
                raise AuditFailure(f"{path}: internal segment {segment.get('data-bin')} must be unstroked")
            y = round(float(segment.get("y", "0")), 1)
            segments_by_y.setdefault(y, []).append(segment)
    for y, track in track_by_y.items():
        segments = segments_by_y.get(y)
        if not segments:
            raise AuditFailure(f"{path}: no bar segments for y={y}")
        track_x = float(track.get("x", "0"))
        track_w = float(track.get("width", "0"))
        left = min(float(segment.get("x", "0")) for segment in segments)
        right = max(float(segment.get("x", "0")) + float(segment.get("width", "0")) for segment in segments)
        total_w = sum(float(segment.get("width", "0")) for segment in segments)
        if abs(left - track_x) > 0.2:
            raise AuditFailure(f"{path}: row y={y} first segment is not justified to left edge")
        if abs(right - (track_x + track_w)) > 2.0:
            raise AuditFailure(f"{path}: row y={y} last segment is not justified to right edge")
        if abs(total_w - track_w) > 2.0:
            raise AuditFailure(f"{path}: row y={y} segment widths do not span the full track")


def audit_panel3_percentage_marks(root: ET.Element, path: Path) -> None:
    if root.findall(f".//{SVG_NS}circle"):
        raise AuditFailure(f"{path}: Panel 3 must use barcode capsule bars, not circle dots")
    units = root.findall(f".//{SVG_NS}rect[@class='barcode-unit']")
    if len(units) != EXPECTED_PANEL3_UNITS:
        raise AuditFailure(f"{path}: expected {EXPECTED_PANEL3_UNITS} barcode units, got {len(units)}")
    rows: dict[str, set[float]] = {}
    for unit in units:
        row = unit.get("data-row", "")
        rows.setdefault(row, set()).add(round(float(unit.get("y", "0")), 1))
        if float(unit.get("rx", "0")) <= 0:
            raise AuditFailure(f"{path}: barcode unit for row {row!r} must have rounded capsule ends")
    if len(rows) != 17:
        raise AuditFailure(f"{path}: expected barcode units for 17 rows, got {len(rows)}")
    for row, y_positions in rows.items():
        if len(y_positions) != 1:
            raise AuditFailure(f"{path}: row {row!r} wraps across {len(y_positions)} y-positions")


def audit_b3_legend(root: ET.Element, path: Path, expected_id: int) -> None:
    legend_bins = [rect for rect in root.findall(f".//{SVG_NS}rect") if rect.get("data-legend-bin")]
    observed_bins = [rect.get("data-legend-bin", "") for rect in legend_bins]
    if observed_bins != BIN_COLUMNS:
        raise AuditFailure(f"{path}: B3 legend bins mismatch: {observed_bins}")
    outlines = root.findall(f".//{SVG_NS}rect[@class='legend-outline']")
    if len(outlines) != 1:
        raise AuditFailure(f"{path}: expected one B3 legend outline")
    legend_outline = outlines[0]
    panel_key = f"panel{expected_id}"
    if legend_outline.get("data-legend-panel") != panel_key:
        raise AuditFailure(f"{path}: B3 legend panel key mismatch")
    for rect in legend_bins:
        if rect.get("data-legend-panel") != panel_key:
            raise AuditFailure(f"{path}: B3 legend bin panel key mismatch")
    tracks = root.findall(f".//{SVG_NS}rect[@class='track']")
    if not tracks:
        raise AuditFailure(f"{path}: no data tracks available for B3 legend alignment check")
    data_x = float(tracks[0].get("x", "0"))
    data_w = float(tracks[0].get("width", "0"))
    legend_x = float(legend_outline.get("x", "0"))
    legend_w = float(legend_outline.get("width", "0"))
    if abs(legend_x - data_x) > 0.2 or abs(legend_w - data_w) > 0.2:
        raise AuditFailure(
            f"{path}: B3 legend span x={legend_x} w={legend_w} does not match data span x={data_x} w={data_w}"
        )
    texts = ["".join(text.itertext()).strip() for text in root.findall(f".//{SVG_NS}text")]
    required = [
        "Correct, by confidence",
        "I don't know",
        "Wrong, by confidence",
        "L4 high confidence",
        "L0 low confidence",
    ]
    for label in required:
        if label not in texts:
            raise AuditFailure(f"{path}: B3 legend missing {label!r}")
    stale = {"Correct L4", "Correct L2", "Correct L0", "Wrong L0", "Wrong L2", "Wrong L4"}
    found_stale = sorted(stale.intersection(texts))
    if found_stale:
        raise AuditFailure(f"{path}: stale sampled legend labels present: {found_stale}")


def audit_visible_row_identity(root: ET.Element, path: Path) -> None:
    texts = ["".join(text.itertext()).strip() for text in root.findall(f".//{SVG_NS}text")]
    joined = "\n".join(texts)
    if "n=200" in joined:
        raise AuditFailure(f"{path}: visible row-level n=200 metadata is present")
    raw_labels = sorted(label for label in DISPLAY_NAMES if label in texts)
    if raw_labels:
        raise AuditFailure(f"{path}: visible raw underscore model labels present: {raw_labels}")
    missing = sorted(display for display in DISPLAY_NAMES.values() if display not in texts)
    if missing:
        raise AuditFailure(f"{path}: formatted display labels missing: {missing}")
    for required in ["Board-certified radiologists", "Radiology trainees", "Score", "Reader / model"]:
        if required not in texts:
            raise AuditFailure(f"{path}: required visible row identity label missing: {required!r}")


def audit_svg(out_dir: Path, rows: list[dict[str, str]]) -> None:
    by_label = {row["reader_label"]: row for row in rows}
    for expected_id, filename in [(2, PANEL_FILES[0]), (3, PANEL_FILES[1])]:
        path = out_dir / filename
        root, payload = parse_svg(path)
        if int(payload.get("panel_id", 0)) != expected_id:
            raise AuditFailure(f"{path}: panel_id mismatch")
        if payload.get("source_csv") != "likert5_score1000/score1000_scored_rows.csv":
            raise AuditFailure(f"{path}: source_csv mismatch")
        if str(payload.get("source_master_sha256", "")).upper() != EXPECTED_SOURCE_SHA256:
            raise AuditFailure(f"{path}: source master SHA mismatch")
        payload_rows = payload.get("rows")
        if not isinstance(payload_rows, list) or len(payload_rows) != 17:
            raise AuditFailure(f"{path}: metadata row count mismatch")
        for item in payload_rows:
            if not isinstance(item, dict):
                raise AuditFailure(f"{path}: metadata row is not an object")
            label = str(item.get("reader_label", ""))
            row = by_label.get(label)
            if row is None:
                raise AuditFailure(f"{path}: metadata row {label!r} not found in summary")
            bins = item.get("bins")
            dot_bins = item.get("dot_bins")
            if not isinstance(bins, dict) or not isinstance(dot_bins, dict):
                raise AuditFailure(f"{path}: metadata missing bins")
            for column in BIN_COLUMNS:
                if not close_enough(bins.get(column, -999), row[column]):
                    raise AuditFailure(f"{path}: metadata {label} {column} mismatch")
                if int(float(dot_bins.get(column, -999))) != int(float(row[f"dot_{column}"])):
                    raise AuditFailure(f"{path}: metadata {label} dot_{column} mismatch")
        if expected_id == 2:
            audit_panel2_edge_justified(root, path)
        if expected_id == 3:
            audit_panel3_percentage_marks(root, path)
        audit_b3_legend(root, path, expected_id)
        audit_visible_row_identity(root, path)


def audit_required_files(out_dir: Path) -> None:
    missing = [name for name in REQUIRED_FILES if not (out_dir / name).exists()]
    if missing:
        raise AuditFailure(f"Missing panel package files: {missing}")
    extra_panels = sorted(path.name for path in out_dir.glob("panel_*.svg") if path.name not in PANEL_FILES)
    if extra_panels:
        raise AuditFailure(f"Unexpected panel files: {extra_panels}")
    for path in out_dir.iterdir():
        if path.is_file() and path.suffix.lower() in {".svg", ".html", ".md", ".json", ".txt", ".csv"}:
            scan_text(path)


def audit_manifest(out_dir: Path) -> None:
    manifest = json.loads((out_dir / "figure_manifest.json").read_text(encoding="utf-8"))
    panel_set = {int(panel["panel_id"]) for panel in manifest.get("panels", [])}
    if panel_set != {2, 3}:
        raise AuditFailure(f"Manifest panel set must be {{2,3}}, got {panel_set}")
    by_path = {entry["path"]: entry for entry in manifest.get("files", [])}
    for name in REQUIRED_FILES:
        if name == "figure_manifest.json":
            continue
        path = out_dir / name
        key = rel(path)
        entry = by_path.get(key)
        if entry is None:
            raise AuditFailure(f"Manifest missing {key}")
        if str(entry.get("sha256", "")).upper() != sha256_file(path):
            raise AuditFailure(f"Manifest SHA mismatch for {key}")


def render_contact_sheet(out_dir: Path, score_root: Path) -> str:
    render_dir = score_root / "_visual_qa"
    render_dir.mkdir(parents=True, exist_ok=True)
    screenshot = render_dir / "score1000_panel23_contact_sheet.png"
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        raise AuditFailure(f"playwright is required for visual QA: {exc}") from exc
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1500, "height": 2200}, device_scale_factor=1)
        page.goto((out_dir / "contact_sheet.html").resolve().as_uri(), wait_until="networkidle")
        page.screenshot(path=str(screenshot), full_page=True)
        browser.close()
    return str(screenshot)


def write_report(out_dir: Path, rows: list[dict[str, str]], screenshot: str | None) -> None:
    report = {
        "generated_at": utc_now(),
        "result": "pass",
        "rows": len(rows),
        "panels": [2, 3],
        "screenshot": screenshot,
    }
    (out_dir / "score1000_panel23_audit_report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    lines = [
        "# Score1000 Panel 2/3 Audit Report",
        "",
        "- Result: pass",
        f"- Rows: {len(rows)}",
        "- Panels: 2, 3",
    ]
    if screenshot:
        lines.append(f"- Visual QA screenshot: `{screenshot}`")
    (out_dir / "score1000_panel23_audit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score-root", type=Path, default=DEFAULT_SCORE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--skip-visual-qa", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    score_root = args.score_root.resolve()
    out_dir = args.out_dir.resolve()
    try:
        audit_required_files(out_dir)
        rows = audit_csv(score_root, out_dir)
        audit_svg(out_dir, rows)
        audit_manifest(out_dir)
        screenshot = None if args.skip_visual_qa else render_contact_sheet(out_dir, score_root)
        write_report(out_dir, rows, screenshot)
    except AuditFailure as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1) from exc
    print(f"[PASS] audited Score1000 Panel 2/3 package {out_dir}")
    if screenshot:
        print(f"[PASS] rendered {screenshot}")


if __name__ == "__main__":
    main()
