#!/usr/bin/env python3
"""Generate RadLE v2 handwritten-style confidence SVG panel artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ROOT = (
    REPO_ROOT
    / "outputs"
    / "radle_v2_stats"
    / "final_scoring_radiologist_20260706_001147"
)
EXPECTED_MASTER_SHA256 = (
    "7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED"
)

W, H = 3600, 2700
FONT = "Inter, Helvetica Neue, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, Menlo, Consolas, monospace"

INK = "#202124"
MUTED = "#5f6368"
PAPER = "#fbfaf5"
FRAME = "#b0bec5"
GRID = "#e2e6e8"
HAZARD = "#d62728"
HAZARD_DARK = "#9f1d20"
CORRECT = "#2ca02c"
CORRECT_DARK = "#1f7a21"
SHIELD = "#005b96"
SHIELD_DARK = "#00416f"
CAUTIOUS = "#cfd8dc"
CAUTIOUS_DARK = "#8fa1aa"
DEFERRED = "#f7f9f9"
NOTE = "#f4efe3"

CRITERION_META = {
    "qual": {
        "title": "Qualification comparison",
        "short_title": "Qualification",
        "subtitle": "Human comparators are board-certified radiologists and radiology trainees.",
        "invariant": "6mo post-MD is included with the board-certified radiologist comparator.",
    },
    "qual_human200": {
        "title": "Qualification comparison, human-normalized",
        "short_title": "Qualification, human n=200",
        "subtitle": "Human comparators are normalized to the mean reader, matching model denominators.",
        "invariant": "Human comparator rows are effective n=200 averages; all source rows are preserved in the weighted source CSV.",
    },
}

PANEL_SPECS = [
    {
        "panel_id": 1,
        "file": "panel_1_strict_confidence_outcomes.svg",
        "title": "Confidence vs. Correctness: Outcomes by Confidence Level",
        "subtitle": "Peak-confidence wrong answers, peak-confidence correct answers, cautious answers, and deferrals are separated.",
        "concept": "confidence_outcomes",
        "variant": "strict",
    },
    {
        "panel_id": 2,
        "file": "panel_2_strict_safety_shield.svg",
        "title": "Calibration: Safe Answers vs. Confident Errors",
        "subtitle": "Correct certainty and cautious uncertainty are safe; confident wrong answers are the danger.",
        "concept": "safety_shield",
        "variant": "strict",
    },
    {
        "panel_id": 3,
        "file": "panel_3_strict_peak_certainty_ppv.svg",
        "title": "Reliability of Peak-Confidence Answers",
        "subtitle": "Among Likert 4 answers, the figure shows how often peak certainty was correct.",
        "concept": "peak_certainty_ppv",
        "variant": "strict",
    },
]

PANEL_FILES = [str(spec["file"]) for spec in PANEL_SPECS]

FONT_SIZE_ROWS = [
    ("title", ".title", "svg_panel", 74, "Panel title"),
    ("subtitle", ".subtitle", "svg_panel", 42, "Panel subtitle"),
    ("header", ".header", "svg_panel", 42, "Axis header"),
    ("row_label", ".row-label", "svg_panel", 36, "Row labels"),
    ("bar", ".bar-label", "svg_panel", 34, "Bar labels"),
    ("axis", ".axis-label", "svg_panel", 34, "Axis labels"),
    ("legend", ".legend-label", "svg_panel", 34, "Legend labels"),
    ("small", ".small", "svg_panel", 30, "Small explanatory text"),
    ("micro", ".micro", "svg_panel", 24, "Micro labels and metadata"),
    ("caption", ".caption", "svg_panel", 28, "Footer caption"),
    ("contact_h1", "h1", "contact_sheet", 26, "Contact sheet heading"),
    ("contact_figcaption", "figcaption", "contact_sheet", 15, "Contact sheet captions"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def fnum(row: dict[str, str], key: str) -> float:
    return float(row[key])


def inum(row: dict[str, str], key: str) -> int:
    return int(round(float(row[key])))


def is_human200(row: dict[str, str]) -> bool:
    return row.get("normalization_mode") == "human_mean_per_reader_200"


def count_label_value(value: float, *, force_decimal: bool = False) -> str:
    if abs(value - round(value)) < 1e-6 and not force_decimal:
        return str(int(round(value)))
    return f"{value:.1f}"


def count_label(row: dict[str, str], key: str) -> str:
    return count_label_value(fnum(row, key), force_decimal=is_human200(row))


def count_data_value(row: dict[str, str], key: str) -> str:
    return f"{fnum(row, key):.6f}".rstrip("0").rstrip(".")


def sum_count_label(row: dict[str, str], keys: list[str]) -> str:
    return count_label_value(sum(fnum(row, key) for key in keys), force_decimal=is_human200(row))


def pct(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}%"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def row_label(row: dict[str, str]) -> str:
    name = row.get("display_label") or row["display_name"]
    if row["row_kind"] == "human_comparator":
        return name
    return name


def row_n_label(row: dict[str, str]) -> str:
    if row["row_kind"] == "human_comparator":
        if is_human200(row):
            return f"n=200 avg ({inum(row, 'n_raters')} readers)"
        return f"n={inum(row, 'n')} ({inum(row, 'n_raters')} readers)"
    return "n=200"


def row_payload(row: dict[str, str]) -> dict[str, object]:
    keys = [
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
        "normalization_mode",
        "normalization_unit",
        "normalization_divisor",
        "n",
        "n_correct",
        "accuracy_pct_label",
        "peak_wrong_n",
        "peak_correct_n",
        "cautious_n",
        "deferred_n",
        "n_peak_conf",
        "ppv_correct_label",
        "ppv_wrong_label",
        "verified_safe_n",
        "safe_uncertainty_n",
        "misleading_hazard_n",
        "confidence_volume_n",
    ]
    out: dict[str, object] = {}
    for key in keys:
        value = row.get(key, "")
        if key in {
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
        }:
            if key in {"row_order", "n_raters"}:
                out[key] = int(round(float(value))) if str(value).strip() else 0
            else:
                out[key] = round(float(value), 6) if str(value).strip() else 0
        else:
            out[key] = value
    return out


def svg_style() -> str:
    return f"""
    <style>
      svg {{ background: {PAPER}; }}
      .frame {{ fill: #ffffff; stroke: {FRAME}; stroke-width: 3; }}
      .title {{ font-family: {FONT}; font-size: 74px; font-weight: 750; fill: {INK}; letter-spacing: 0; }}
      .subtitle {{ font-family: {FONT}; font-size: 42px; font-weight: 400; fill: {INK}; letter-spacing: 0; }}
      .header {{ font-family: {FONT}; font-size: 42px; font-weight: 700; fill: {INK}; letter-spacing: 0; }}
      .row-label {{ font-family: {FONT}; font-size: 36px; font-weight: 700; fill: {INK}; letter-spacing: 0; }}
      .row-meta {{ font-family: {MONO}; font-size: 22px; fill: {MUTED}; letter-spacing: 0; }}
      .axis-label {{ font-family: {MONO}; font-size: 34px; fill: {INK}; letter-spacing: 0; }}
      .bar-label {{ font-family: {MONO}; font-size: 34px; font-weight: 800; fill: {INK}; letter-spacing: 0; }}
      .bar-label-white {{ font-family: {MONO}; font-size: 34px; font-weight: 800; fill: #ffffff; letter-spacing: 0; }}
      .legend-label {{ font-family: {FONT}; font-size: 34px; font-weight: 700; fill: {INK}; letter-spacing: 0; }}
      .small {{ font-family: {FONT}; font-size: 30px; fill: {INK}; letter-spacing: 0; }}
      .micro {{ font-family: {MONO}; font-size: 24px; fill: {MUTED}; letter-spacing: 0; }}
      .caption {{ font-family: {FONT}; font-size: 28px; fill: {INK}; letter-spacing: 0; }}
      .grid {{ stroke: {GRID}; stroke-width: 2; stroke-dasharray: 7 12; }}
      .axis {{ stroke: {INK}; stroke-width: 3; }}
      .bar {{ stroke-width: 2.5; }}
      .note {{ fill: {NOTE}; stroke: #d6c9a8; stroke-width: 2; }}
      .centerline {{ stroke: {INK}; stroke-width: 3; stroke-dasharray: 12 12; }}
    </style>
    """


def defs() -> str:
    return f"""
    <defs>
      <pattern id="deferredHatch" width="18" height="18" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="18" height="18" fill="{DEFERRED}" />
        <line x1="0" y1="0" x2="0" y2="18" stroke="#d8dfe2" stroke-width="4" />
      </pattern>
    </defs>
    """


def text(x: float, y: float, value: object, cls: str = "small", anchor: str = "start") -> str:
    return f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}">{esc(value)}</text>'


def multiline_text(
    x: float,
    y: float,
    lines: Iterable[object],
    cls: str = "small",
    gap: float = 40,
    anchor: str = "start",
) -> str:
    chunks = [f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}">']
    for idx, value in enumerate(lines):
        dy = 0 if idx == 0 else gap
        chunks.append(f'<tspan x="{x:.1f}" dy="{dy:.1f}">{esc(value)}</tspan>')
    chunks.append("</text>")
    return "".join(chunks)


def line(x1: float, y1: float, x2: float, y2: float, cls: str = "axis") -> str:
    return f'<line class="{cls}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" />'


def rect(
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str,
    stroke: str = "#1f1f1f",
    rx: float = 8,
    cls: str = "bar",
    extra: str = "",
) -> str:
    width = max(0.0, width)
    return (
        f'<rect class="{cls}" x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" '
        f'height="{height:.1f}" rx="{rx:.1f}" fill="{fill}" stroke="{stroke}" {extra}/>'
    )


def circle(x: float, y: float, r: float, fill: str, stroke: str = "#1f1f1f") -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="3" />'


def metadata_block(criterion: str, spec: dict[str, object], rows: list[dict[str, str]], provenance: dict[str, object]) -> str:
    data = {
        "criterion": criterion,
        "panel_id": spec["panel_id"],
        "concept": spec["concept"],
        "variant": spec["variant"],
        "master_sha256": provenance["master_sha256"],
        "source_csv": "confidence_outcome_summary.csv",
        "rows": [row_payload(row) for row in rows],
    }
    return f"<metadata id=\"radle-panel-data\">{esc(json.dumps(data, sort_keys=True))}</metadata>"


def svg_open(criterion: str, spec: dict[str, object], rows: list[dict[str, str]], provenance: dict[str, object]) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">',
        f"<title>{esc(spec['title'])}</title>",
        f"<desc>{esc(spec['subtitle'])}</desc>",
        metadata_block(criterion, spec, rows, provenance),
        defs(),
        svg_style(),
        '<rect class="frame" x="28" y="28" width="3544" height="2644" rx="22" />',
    ]


def add_header(parts: list[str], criterion: str, spec: dict[str, object]) -> None:
    meta = CRITERION_META[criterion]
    parts.append(text(80, 150, spec["title"], "title"))
    parts.append(text(80, 220, spec["subtitle"], "subtitle"))
    parts.append(text(80, 276, meta["subtitle"], "small"))


def add_footer(parts: list[str], criterion: str, provenance: dict[str, object]) -> None:
    parts.append(line(80, 2560, 3520, 2560, "axis"))
    parts.append(text(80, 2610, f"Source: final radiologist master; SHA256 {provenance['master_sha256']}", "caption"))
    parts.append(text(80, 2646, f"{CRITERION_META[criterion]['short_title']} comparison; {CRITERION_META[criterion]['invariant']}", "micro"))


def add_percent_axis(parts: list[str], chart_x: float, axis_y: float, chart_w: float, label: str) -> None:
    for tick in range(0, 101, 20):
        x = chart_x + chart_w * tick / 100
        parts.append(line(x, 520, x, axis_y, "grid"))
        parts.append(text(x, axis_y + 42, f"{tick}%", "axis-label", "middle"))
    parts.append(line(chart_x, axis_y, chart_x + chart_w, axis_y, "axis"))
    parts.append(text(chart_x + chart_w / 2, axis_y + 94, label, "header", "middle"))


def legend_item(parts: list[str], x: float, y: float, label: str, fill: str, stroke: str = "#1f1f1f") -> None:
    parts.append(rect(x, y - 30, 42, 32, fill, stroke=stroke, rx=5))
    parts.append(text(x + 60, y, label, "legend-label"))


def add_bottom_legend(parts: list[str], items: list[tuple[str, str, str]], y: float = 2446) -> None:
    widths = [len(label) * 19 + 110 for label, _, _ in items]
    total = sum(widths)
    x = (W - total) / 2
    for idx, (label, fill, stroke) in enumerate(items):
        legend_item(parts, x, y, label, fill, stroke)
        x += widths[idx]


def label_inside(value: object, width: float, min_width: float = 88) -> bool:
    return width >= max(min_width, 19 * len(str(value)) + 30)


def add_segment_label(
    parts: list[str],
    x: float,
    y: float,
    width: float,
    value: float,
    label: str,
    fill: str,
    chart_left: float,
    chart_right: float,
) -> None:
    if value <= 0:
        return
    white = fill in {HAZARD, CORRECT, SHIELD, HAZARD_DARK, CORRECT_DARK, SHIELD_DARK}
    if label_inside(label, width):
        parts.append(text(x + width / 2, y + 48, label, "bar-label-white" if white else "bar-label", "middle"))
        return
    outside = x + width + 16
    if outside < chart_right - 8:
        parts.append(text(outside, y + 48, label, "bar-label"))
    elif x - 16 > chart_left:
        parts.append(text(x - 16, y + 48, label, "bar-label", "end"))


def row_y(index: int) -> float:
    return 584 + index * 94


def row_label_lines(label: str) -> list[str]:
    return [label]


def add_row_label(parts: list[str], row: dict[str, str], y: float) -> None:
    lines = row_label_lines(row_label(row))
    parts.append(multiline_text(80, y + 30, lines, "row-label", gap=36))
    meta_y = y + 78 if len(lines) == 1 else y + 118
    parts.append(text(80, meta_y, row_n_label(row), "row-meta"))
    if row["row_kind"] == "human_comparator":
        parts.append(rect(60, y - 9, 8, 84, "#111111", stroke="#111111", rx=2))


def segment_width(value: float, n: float, chart_w: float) -> float:
    if n <= 0:
        return 0
    return chart_w * value / n


def panel_strict_confidence(criterion: str, rows: list[dict[str, str]], provenance: dict[str, object]) -> str:
    spec = PANEL_SPECS[0]
    parts = svg_open(criterion, spec, rows, provenance)
    add_header(parts, criterion, spec)
    chart_x, chart_w, bar_h = 720, 2760, 66
    axis_y = 2250
    parts.append(text(chart_x + chart_w / 2, 482, "Share of each row denominator; labels show effective counts", "header", "middle"))
    add_percent_axis(parts, chart_x, axis_y, chart_w, "Percent of row denominator")
    for idx, row in enumerate(rows):
        y = row_y(idx)
        add_row_label(parts, row, y)
        n = fnum(row, "n")
        segments = [
            ("peak_wrong_n", HAZARD, HAZARD_DARK),
            ("peak_correct_n", CORRECT, CORRECT_DARK),
            ("cautious_n", CAUTIOUS, CAUTIOUS_DARK),
            ("deferred_n", "url(#deferredHatch)", CAUTIOUS_DARK),
        ]
        x = chart_x
        for key, fill, stroke in segments:
            value = fnum(row, key)
            w = segment_width(value, n, chart_w)
            if value:
                parts.append(rect(x, y, w, bar_h, fill, stroke=stroke, rx=7, extra=f'data-value="{count_data_value(row, key)}" data-row="{esc(row_label(row))}" data-key="{key}"'))
                add_segment_label(parts, x, y, w, value, count_label(row, key), fill, chart_x, chart_x + chart_w)
            x += w
    add_bottom_legend(
        parts,
        [
            ("Confident Error", HAZARD, HAZARD_DARK),
            ("Confident & Correct", CORRECT, CORRECT_DARK),
            ("Clinically Cautious", CAUTIOUS, CAUTIOUS_DARK),
            ("Deferred / Other", "url(#deferredHatch)", CAUTIOUS_DARK),
        ],
    )
    add_footer(parts, criterion, provenance)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def panel_strict_safety(criterion: str, rows: list[dict[str, str]], provenance: dict[str, object]) -> str:
    spec = PANEL_SPECS[1]
    parts = svg_open(criterion, spec, rows, provenance)
    add_header(parts, criterion, spec)
    chart_x, chart_w, bar_h = 720, 2760, 66
    axis_y = 2250
    parts.append(text(chart_x + chart_w / 2, 482, "Safe answers vs confident errors", "header", "middle"))
    add_percent_axis(parts, chart_x, axis_y, chart_w, "Percent of row denominator")
    for idx, row in enumerate(rows):
        y = row_y(idx)
        add_row_label(parts, row, y)
        n = fnum(row, "n")
        segments = [
            ("verified_safe_n", SHIELD, SHIELD_DARK),
            ("safe_uncertainty_n", CAUTIOUS, CAUTIOUS_DARK),
            ("misleading_hazard_n", HAZARD, HAZARD_DARK),
        ]
        x = chart_x
        for key, fill, stroke in segments:
            value = fnum(row, key)
            w = segment_width(value, n, chart_w)
            if value:
                parts.append(rect(x, y, w, bar_h, fill, stroke=stroke, rx=7, extra=f'data-value="{count_data_value(row, key)}" data-row="{esc(row_label(row))}" data-key="{key}"'))
                add_segment_label(parts, x, y, w, value, count_label(row, key), fill, chart_x, chart_x + chart_w)
            x += w
    add_bottom_legend(
        parts,
        [
            ("Confident & Correct", SHIELD, SHIELD_DARK),
            ("Cautious (Safe)", CAUTIOUS, CAUTIOUS_DARK),
            ("Confident Error", HAZARD, HAZARD_DARK),
        ],
    )
    add_footer(parts, criterion, provenance)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def panel_strict_ppv(criterion: str, rows: list[dict[str, str]], provenance: dict[str, object]) -> str:
    spec = PANEL_SPECS[2]
    parts = svg_open(criterion, spec, rows, provenance)
    add_header(parts, criterion, spec)
    chart_x, chart_w, bar_h = 780, 2440, 66
    metric_x = 3388
    axis_y = 2250
    parts.append(text(chart_x + chart_w / 2, 482, "Proportion of peak-confidence answers", "header", "middle"))
    add_percent_axis(parts, chart_x, axis_y, chart_w, "Peak-confidence PPV")
    for idx, row in enumerate(rows):
        y = row_y(idx)
        add_row_label(parts, row, y)
        correct_pct = fnum(row, "ppv_correct_pct")
        wrong_pct = fnum(row, "ppv_wrong_pct")
        correct_w = chart_w * correct_pct / 100
        wrong_w = chart_w * wrong_pct / 100
        parts.append(rect(chart_x, y, correct_w, bar_h, CORRECT, stroke=CORRECT_DARK, rx=7, extra=f'data-value="{row["ppv_correct_label"]}" data-row="{esc(row_label(row))}" data-key="ppv_correct_pct"'))
        parts.append(rect(chart_x + correct_w, y, wrong_w, bar_h, HAZARD, stroke=HAZARD_DARK, rx=7, extra=f'data-value="{row["ppv_wrong_label"]}" data-row="{esc(row_label(row))}" data-key="ppv_wrong_pct"'))
        if label_inside(row["ppv_correct_label"], correct_w):
            parts.append(text(chart_x + correct_w / 2, y + 48, row["ppv_correct_label"], "bar-label-white", "middle"))
        elif correct_w > 0:
            parts.append(text(chart_x - 18, y + 48, row["ppv_correct_label"], "bar-label", "end"))
        if label_inside(row["ppv_wrong_label"], wrong_w):
            parts.append(text(chart_x + correct_w + wrong_w / 2, y + 48, row["ppv_wrong_label"], "bar-label-white", "middle"))
        parts.append(text(metric_x, y + 46, f"(n={count_label(row, 'n_peak_conf')})", "row-meta", "end"))
    add_bottom_legend(
        parts,
        [
            ("Confident & Correct", CORRECT, CORRECT_DARK),
            ("Confident Error", HAZARD, HAZARD_DARK),
        ],
    )
    add_footer(parts, criterion, provenance)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


PANEL_BUILDERS = {
    1: panel_strict_confidence,
    2: panel_strict_safety,
    3: panel_strict_ppv,
}


def write_font_sizes(out_dir: Path) -> None:
    path = out_dir / "font_sizes.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["key", "css_selector", "scope", "size_px", "description"])
        writer.writerows(FONT_SIZE_ROWS)


def write_contact_sheet(out_dir: Path, criterion: str, manifest: dict[str, object]) -> None:
    figures = []
    for panel in manifest["panels"]:
        filename = str(panel["file"])
        title = esc(panel["title"])
        svg_source = (out_dir / filename).read_text(encoding="utf-8")
        figures.append(
            f"""
            <figure>
              <div class="svg-wrap">{svg_source}</div>
              <figcaption>{title}</figcaption>
            </figure>
            """
        )
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RadLE v2 confidence panels - {esc(criterion)}</title>
  <style>
    body {{ margin: 24px; background: #f4f1e8; color: {INK}; font-family: {FONT}; }}
    h1 {{ font-size: 26px; margin: 0 0 8px; }}
    .meta {{ font-family: {MONO}; font-size: 13px; margin-bottom: 18px; }}
    .grid {{ display: grid; grid-template-columns: 1fr; gap: 22px; max-width: 1500px; }}
    figure {{ margin: 0; padding: 16px; background: #fffdf7; border: 1px solid #cfc5ad; }}
    .svg-wrap svg {{ display: block; width: 100%; height: auto; border: 0; }}
    figcaption {{ margin-top: 10px; font-size: 15px; }}
  </style>
</head>
<body>
  <h1>RadLE v2 confidence panels - {esc(criterion)}</h1>
  <div class="meta">master_sha256={esc(manifest["master_sha256"])}</div>
  <div class="grid">
    {"".join(figures)}
  </div>
</body>
</html>
"""
    write_text(out_dir / "contact_sheet.html", html_doc)


def write_captions(out_dir: Path, criterion: str, rows: list[dict[str, str]]) -> None:
    meta = CRITERION_META[criterion]
    human_rows = [row for row in rows if row["row_kind"] == "human_comparator"]
    lines = [
        f"# RadLE v2 confidence-panel captions - {meta['short_title']}",
        "",
        f"Comparator definition: {meta['invariant']}",
        "",
    ]
    for spec in PANEL_SPECS:
        lines.extend(
            [
                f"## Panel {spec['panel_id']}. {spec['title']}",
                str(spec["subtitle"]),
            ]
        )
        if spec["concept"] == "confidence_outcomes":
            lines.append(
                "Displayed buckets are confident error, confident correct, clinically cautious, and deferred/other. "
                + "Human comparator rows: "
                + "; ".join(
                    f"{row_label(row)} confident error {count_label(row, 'peak_wrong_n')}/{count_label(row, 'n')}, correct peak {count_label(row, 'peak_correct_n')}/{count_label(row, 'n')}"
                    for row in human_rows
                )
                + "."
            )
        elif spec["concept"] == "safety_shield":
            lines.append(
                "Displayed calibration buckets are confident and correct, cautious safe, and confident error. "
                + "; ".join(
                    f"{row_label(row)} safe answers {sum_count_label(row, ['verified_safe_n', 'safe_uncertainty_n'])}/{count_label(row, 'n')} vs confident error {count_label(row, 'misleading_hazard_n')}/{count_label(row, 'n')}"
                    for row in human_rows
                )
                + "."
            )
        else:
            lines.append(
                "Displayed PPV is calculated only among Likert 4 peak-confidence answers. "
                + "; ".join(
                    f"{row_label(row)} PPV {row['ppv_correct_label']} (n={count_label(row, 'n_peak_conf')})"
                    for row in human_rows
                )
                + "."
            )
        lines.append("")
    write_text(out_dir / "captions.md", "\n".join(lines))


def write_provenance(out_dir: Path, criterion: str, provenance: dict[str, object], manifest: dict[str, object]) -> None:
    meta = CRITERION_META[criterion]
    lines = [
        f"# RadLE v2 confidence-panel provenance - {meta['short_title']}",
        "",
        f"- Master CSV: `{provenance['master_path']}`",
        f"- Master CSV SHA256: `{provenance['master_sha256']}`",
        f"- Master rows: `{provenance['rows']}`",
        f"- Master columns: `{provenance['columns']}`",
        f"- Master correct total: `{provenance['n_correct']}`",
        f"- Criterion: `{criterion}`",
        f"- Generated at UTC: `{manifest['generated_at_utc']}`",
        f"- Generator: `{Path(__file__).name}`",
        "",
        "## Grouping Contract",
        "",
    ]
    for group in provenance["grouping_contract"]:
        lines.append(f"- {group['group']}: {', '.join(group['members'])}")
    lines.extend(
        [
            "",
            "## Confidence Definitions",
            "",
        ]
    )
    for key, value in provenance.get("confidence_definitions", {}).items():
        lines.append(f"- `{key}`: {value}")
    source_files = [
        "group_summary.csv",
        "seniority_tier_summary.csv",
        "confidence_outcome_summary.csv",
        "stats_provenance.json",
    ]
    weighted_source_file = str(provenance.get("weighted_source_file", "") or "")
    if weighted_source_file:
        source_files.append(weighted_source_file)
    lines.extend(
        [
            "",
            "## Source Files",
            "",
        ]
    )
    for source_file in source_files:
        lines.append(f"- `{source_file}`")
    lines.extend(["", "## Generated Files", ""])
    for panel in manifest["panels"]:
        lines.append(f"- `{panel['file']}` SHA256 `{panel['sha256']}`")
    lines.extend(
        [
            "- `contact_sheet.html`",
            "- `captions.md`",
            "- `figure_manifest.json`",
            "- `font_sizes.csv`",
            "- `reviewer_checklist.md`",
            "- `handwritten_panels_qa.txt`",
            "",
        ]
    )
    write_text(out_dir / "data_provenance.md", "\n".join(lines))


def write_reviewer_checklist(out_dir: Path, criterion: str) -> None:
    lines = [
        f"# Reviewer checklist - {criterion}",
        "",
        "- [ ] Confirm master SHA256 in `data_provenance.md` and `figure_manifest.json` matches the expected final master.",
        "- [ ] Confirm group memberships match the criterion-specific contract.",
        "- [ ] Confirm every displayed count, percentage, and `n=` matches `confidence_outcome_summary.csv`.",
        "- [ ] Confirm `6mo post-MD` is assigned to the correct group for this criterion.",
        "- [ ] Confirm panels 1-3 preserve stacked horizontal bar grammar and semantic legends.",
        "- [ ] Confirm SVG text is readable at contact-sheet scale.",
        "- [ ] Confirm no text is clipped at the frame edge.",
        "- [ ] Confirm legends and labels do not overlap bars or each other.",
        "- [ ] Confirm no stale reference-folder paths appear.",
        "- [ ] Confirm no mojibake appears in SVGs, captions, manifest, or provenance.",
        "",
    ]
    write_text(out_dir / "reviewer_checklist.md", "\n".join(lines))


def write_qa_stub(out_dir: Path, criterion: str, panel_paths: list[Path]) -> None:
    lines = [
        f"RadLE v2 confidence panels QA - {criterion}",
        f"Generated at UTC: {utc_now()}",
        "Generator completed. Phase audit notes are written at the final-scoring root by scripts/audit_radle_v2_handwritten_panels.py.",
        "Fresh visual screenshots are written under the final-scoring root _visual_qa folder.",
        "Panel files:",
        *[f"- {path.name}" for path in panel_paths],
        "",
    ]
    write_text(out_dir / "handwritten_panels_qa.txt", "\n".join(lines))


def load_inputs(out_dir: Path) -> tuple[list[dict[str, str]], dict[str, object]]:
    rows = read_csv_rows(out_dir / "confidence_outcome_summary.csv")
    provenance_path = out_dir / "stats_provenance.json"
    if not provenance_path.exists():
        raise FileNotFoundError(f"Missing stats provenance: {provenance_path}")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if provenance.get("master_sha256") != EXPECTED_MASTER_SHA256:
        raise ValueError(
            f"{out_dir}: expected master SHA {EXPECTED_MASTER_SHA256}, "
            f"got {provenance.get('master_sha256')}"
        )
    if len(rows) != 17:
        raise ValueError(f"{out_dir}: expected 17 confidence rows, got {len(rows)}")
    return rows, provenance


def build_criterion(out_root: Path, criterion: str) -> None:
    out_dir = out_root / criterion
    rows, provenance = load_inputs(out_dir)
    panel_paths: list[Path] = []
    panels_manifest: list[dict[str, object]] = []

    active_names = set(PANEL_FILES)
    for stale in out_dir.glob("panel_*.svg"):
        if stale.name not in active_names:
            stale.unlink()

    for spec in PANEL_SPECS:
        panel_id = int(spec["panel_id"])
        builder = PANEL_BUILDERS[panel_id]
        svg = builder(criterion, rows, provenance)
        path = out_dir / str(spec["file"])
        write_text(path, svg)
        panel_paths.append(path)
        panels_manifest.append(
            {
                "panel_id": panel_id,
                "file": path.name,
                "title": spec["title"],
                "concept": spec["concept"],
                "variant": spec["variant"],
                "sha256": sha256_text(svg),
                "source_csvs": ["confidence_outcome_summary.csv"],
            }
        )

    source_files = [
        "group_summary.csv",
        "seniority_tier_summary.csv",
        "confidence_outcome_summary.csv",
        "stats_provenance.json",
    ]
    weighted_source_file = str(provenance.get("weighted_source_file", "") or "")
    if weighted_source_file:
        source_files.append(weighted_source_file)
    manifest = {
        "schema": "radle_v2_confidence_panel_manifest_v1",
        "criterion": criterion,
        "criterion_title": CRITERION_META[criterion]["title"],
        "master_path": provenance["master_path"],
        "master_sha256": provenance["master_sha256"],
        "generated_at_utc": utc_now(),
        "generator": str(Path(__file__).name),
        "canvas": {"width": W, "height": H},
        "panels": panels_manifest,
        "required_support_files": [
            *source_files,
            "contact_sheet.html",
            "captions.md",
            "data_provenance.md",
            "reviewer_checklist.md",
            "font_sizes.csv",
            "handwritten_panels_qa.txt",
        ],
    }
    write_font_sizes(out_dir)
    write_captions(out_dir, criterion, rows)
    write_contact_sheet(out_dir, criterion, manifest)
    write_reviewer_checklist(out_dir, criterion)
    write_qa_stub(out_dir, criterion, panel_paths)
    write_text(out_dir / "figure_manifest.json", json.dumps(manifest, indent=2) + "\n")
    write_provenance(out_dir, criterion, provenance, manifest)
    print(f"[PASS] generated confidence panels {out_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument(
        "--criteria",
        nargs="*",
        choices=sorted(CRITERION_META),
        default=["qual_human200"],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_root = args.out_root.resolve()
    for criterion in args.criteria:
        build_criterion(out_root, criterion)
    print("[PASS] SVG generation complete")


if __name__ == "__main__":
    main()
