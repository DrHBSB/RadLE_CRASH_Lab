#!/usr/bin/env python3
"""Generate RadLE v2 Score1000 handwritten-style Panel 2/3 SVG artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from datetime import datetime, timezone
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

W, H = 3600, 2700
FONT = "Inter, Helvetica Neue, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, Menlo, Consolas, monospace"
PAPER = "#fbfaf5"
FRAME = "#b0bec5"
INK = "#202124"
MUTED = "#5f6368"
GRID = "#e1e7ea"
NEUTRAL = "#c7ccd1"
NEUTRAL_STROKE = "#7f878d"
TRACK = "#f2f0ea"

CORRECT_ORDER = ["correct_l4", "correct_l3", "correct_l2", "correct_l1", "correct_l0"]
WRONG_ORDER = ["wrong_l0", "wrong_l1", "wrong_l2", "wrong_l3", "wrong_l4"]
BIN_ORDER = [*CORRECT_ORDER, "neutral", *WRONG_ORDER]
DOT_ORDER = [f"dot_{key}" for key in BIN_ORDER]
PANEL_FILES = [
    "panel_2_score1000_edge_justified_ledger.svg",
    "panel_3_score1000_100_barcode_percentage_strip.svg",
]
DOT_DISPLAY_TOTAL = 100
COLORS = {
    "correct_l4": "#08306b",
    "correct_l3": "#2171b5",
    "correct_l2": "#6baed6",
    "correct_l1": "#bdd7e7",
    "correct_l0": "#deebf7",
    "neutral": NEUTRAL,
    "wrong_l0": "#fee5d9",
    "wrong_l1": "#fcae91",
    "wrong_l2": "#fb6a4a",
    "wrong_l3": "#de2d26",
    "wrong_l4": "#7f0000",
}
STROKES = {
    "correct_l4": "#061f46",
    "correct_l3": "#15558e",
    "correct_l2": "#4f8fb9",
    "correct_l1": "#87aebf",
    "correct_l0": "#8aa8b8",
    "neutral": NEUTRAL_STROKE,
    "wrong_l0": "#c99a8b",
    "wrong_l1": "#c77d6f",
    "wrong_l2": "#bd4b36",
    "wrong_l3": "#9f1d20",
    "wrong_l4": "#4f0000",
}
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
FONT_SIZE_ROWS = [
    ("title", ".title", "svg_panel", 70, "Panel title"),
    ("subtitle", ".subtitle", "svg_panel", 38, "Panel subtitle"),
    ("header", ".header", "svg_panel", 38, "Axis/header text"),
    ("row_label", ".row-label", "svg_panel", 32, "Row labels"),
    ("row_meta", ".row-meta", "svg_panel", 22, "Row metadata"),
    ("axis", ".axis-label", "svg_panel", 28, "Axis labels"),
    ("bar", ".bar-label", "svg_panel", 28, "Bar labels"),
    ("legend", ".legend-label", "svg_panel", 29, "Legend labels"),
    ("small", ".small", "svg_panel", 26, "Small explanatory text"),
    ("micro", ".micro", "svg_panel", 22, "Metadata/footer text"),
    ("caption", ".caption", "svg_panel", 26, "Footer caption"),
    ("contact_h1", "h1", "contact_sheet", 26, "Contact sheet heading"),
    ("contact_figcaption", "figcaption", "contact_sheet", 15, "Contact sheet captions"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def fnum(row: dict[str, str], key: str) -> float:
    return float(row[key])


def inum(row: dict[str, str], key: str) -> int:
    return int(round(float(row[key])))


def count_label(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f"{value:.1f}"


def display_name(row: dict[str, str]) -> str:
    label = row["reader_label"]
    if label in DISPLAY_NAMES:
        return DISPLAY_NAMES[label]
    return label


def score_label(row: dict[str, str]) -> str:
    return count_label(fnum(row, "final_score1000"))


def style() -> str:
    return f"""
    <style>
      svg {{ background: {PAPER}; }}
      .frame {{ fill: #ffffff; stroke: {FRAME}; stroke-width: 3; }}
      .title {{ font-family: {FONT}; font-size: 70px; font-weight: 760; fill: {INK}; letter-spacing: 0; }}
      .subtitle {{ font-family: {FONT}; font-size: 38px; font-weight: 400; fill: {INK}; letter-spacing: 0; }}
      .header {{ font-family: {FONT}; font-size: 38px; font-weight: 720; fill: {INK}; letter-spacing: 0; }}
      .row-label {{ font-family: {FONT}; font-size: 32px; font-weight: 730; fill: {INK}; letter-spacing: 0; }}
      .score-label {{ font-family: {MONO}; font-size: 28px; font-weight: 800; fill: {INK}; letter-spacing: 0; }}
      .row-meta {{ font-family: {MONO}; font-size: 22px; fill: {MUTED}; letter-spacing: 0; }}
      .axis-label {{ font-family: {MONO}; font-size: 28px; fill: {INK}; letter-spacing: 0; }}
      .bar-label {{ font-family: {MONO}; font-size: 28px; font-weight: 800; fill: {INK}; letter-spacing: 0; }}
      .bar-label-white {{ font-family: {MONO}; font-size: 28px; font-weight: 800; fill: #ffffff; letter-spacing: 0; }}
      .legend-label {{ font-family: {FONT}; font-size: 29px; font-weight: 700; fill: {INK}; letter-spacing: 0; }}
      .small {{ font-family: {FONT}; font-size: 26px; fill: {INK}; letter-spacing: 0; }}
      .micro {{ font-family: {MONO}; font-size: 22px; fill: {MUTED}; letter-spacing: 0; }}
      .caption {{ font-family: {FONT}; font-size: 26px; fill: {INK}; letter-spacing: 0; }}
      .grid {{ stroke: {GRID}; stroke-width: 2; stroke-dasharray: 7 12; }}
      .axis {{ stroke: {INK}; stroke-width: 3; }}
      .bar {{ stroke-width: 2.4; }}
      .bar-segments .bar {{ shape-rendering: crispEdges; }}
      .bar-outline {{ fill: none; stroke: rgba(45,52,57,.18); stroke-width: 1.2; }}
      .legend-outline {{ fill: none; stroke: rgba(45,52,57,.22); stroke-width: 1.2; }}
      .barcode-unit {{ stroke-width: 1.2; }}
      .track {{ fill: {TRACK}; stroke: #dfd9ce; stroke-width: 1.4; }}
    </style>
    """


def text(x: float, y: float, value: object, cls: str = "small", anchor: str = "start", extra: str = "") -> str:
    attrs = f" {extra}" if extra else ""
    return f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}"{attrs}>{esc(value)}</text>'


def line(x1: float, y1: float, x2: float, y2: float, cls: str = "axis") -> str:
    return f'<line class="{cls}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" />'


def rect(x: float, y: float, width: float, height: float, fill: str, stroke: str, cls: str = "bar", rx: float = 7, extra: str = "") -> str:
    width = max(0.0, width)
    return (
        f'<rect class="{cls}" x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" '
        f'rx="{rx:.1f}" fill="{fill}" stroke="{stroke}" {extra}/>'
    )


def capsule(x: float, y: float, width: float, height: float, fill: str, stroke: str, extra: str = "") -> str:
    return rect(x, y, width, height, fill, stroke, cls="barcode-unit", rx=width / 2, extra=extra)


def clip_path_rect(clip_id: str, x: float, y: float, width: float, height: float, rx: float) -> str:
    return (
        f'<clipPath id="{esc(clip_id)}" clipPathUnits="userSpaceOnUse">'
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="{rx:.1f}" />'
        f"</clipPath>"
    )


def payload_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in rows:
        item: dict[str, object] = {
            "rank": inum(row, "rank"),
            "reader_type": row["reader_type"],
            "reader_label": row["reader_label"],
            "display_name": display_name(row),
            "n_readers": inum(row, "n_readers"),
            "effective_cases": fnum(row, "effective_cases"),
            "final_score1000": fnum(row, "final_score1000"),
            "bins": {key: fnum(row, key) for key in BIN_ORDER},
            "dot_bins": {key: inum(row, f"dot_{key}") for key in BIN_ORDER},
        }
        out.append(item)
    return out


def svg_open(panel_id: int, title: str, desc: str, rows: list[dict[str, str]], provenance: dict[str, object]) -> list[str]:
    metadata = {
        "panel_id": panel_id,
        "source_csv": "likert5_score1000/score1000_scored_rows.csv",
        "summary_csv": "handwritten_panels/score1000_panel23_bins.csv",
        "source_master_sha256": provenance["source_master_sha256"],
        "score1000_scored_rows_sha256": provenance["score1000_scored_rows"]["sha256"],
        "rows": payload_rows(rows),
    }
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">',
        f"<title>{esc(title)}</title>",
        f"<desc>{esc(desc)}</desc>",
        f'<metadata id="radle-panel-data">{esc(json.dumps(metadata, sort_keys=True))}</metadata>',
        style(),
        '<rect class="frame" x="28" y="28" width="3544" height="2644" rx="22" />',
    ]


def add_header(parts: list[str], title: str, subtitle: str) -> None:
    parts.append(text(80, 142, title, "title"))
    parts.append(text(80, 206, subtitle, "subtitle"))
    parts.append(text(80, 262, "Each row totals 200 effective cases; color intensity encodes Likert confidence.", "small"))


def add_footer(parts: list[str], provenance: dict[str, object]) -> None:
    parts.append(line(80, 2560, 3520, 2560, "axis"))
    parts.append(text(80, 2608, f"Source: Score1000 scored rows file; master SHA256 {provenance['source_master_sha256']}", "caption"))
    parts.append(text(80, 2644, "Correct diagnoses are shown left; I don't know/failure/invalid outcomes center; wrong diagnoses right.", "micro"))


def add_human_marker(parts: list[str], row: dict[str, str], x: float, y: float, height: float) -> None:
    if row["reader_type"] == "Human comparator":
        parts.append(rect(x, y - 12, 8, height + 24, "#111111", "#111111", cls="bar", rx=2))


def add_row_identity(parts: list[str], row: dict[str, str], score_x: float, name_x: float, y: float) -> None:
    parts.append(text(score_x, y, score_label(row), "score-label", "end"))
    parts.append(text(name_x, y, display_name(row), "row-label", "end"))


def add_ledger_axis(parts: list[str], chart_x: float, y_top: float, axis_y: float, chart_w: float) -> None:
    for value in [0, 50, 100, 150, 200]:
        x = chart_x + chart_w * value / 200
        parts.append(line(x, y_top, x, axis_y, "grid"))
        parts.append(text(x, axis_y + 38, f"{value}", "axis-label", "middle"))
    parts.append(line(chart_x, axis_y, chart_x + chart_w, axis_y, "axis"))
    parts.append(text(chart_x, axis_y + 86, "Correct reads", "header", "start"))
    parts.append(text(chart_x + chart_w / 2, axis_y + 86, "200 effective cases", "header", "middle"))
    parts.append(text(chart_x + chart_w, axis_y + 86, "Wrong reads", "header", "end"))


def add_segment_label(
    parts: list[str],
    x: float,
    y: float,
    width: float,
    height: float,
    label: str,
    fill: str,
    anchor: str = "middle",
) -> None:
    if width < max(74, len(label) * 17):
        return
    cls = "bar-label-white" if fill in {COLORS["correct_l4"], COLORS["correct_l3"], COLORS["wrong_l3"], COLORS["wrong_l4"]} else "bar-label"
    parts.append(text(x, y + height / 2, label, cls, anchor, extra='dominant-baseline="middle"'))


def panel_2(rows: list[dict[str, str]], provenance: dict[str, object]) -> str:
    title = "Correctness and Confidence Ledger"
    subtitle = "Each row is one 200-case bar: correct reads left, I don't know outcomes middle, wrong reads right."
    parts = svg_open(2, title, subtitle, rows, provenance)
    add_header(parts, title, subtitle)
    chart_x, chart_w, bar_h = 760, 2300, 54
    row_step, y0, axis_y = 108, 410, 2270
    score_x, name_x = 150, 620
    parts.append(text(score_x, y0 - 54, "Score", "axis-label", "end"))
    parts.append(text(name_x, y0 - 54, "Reader / model", "axis-label", "end"))
    add_ledger_axis(parts, chart_x, y0 - 40, axis_y, chart_w)
    for idx, row in enumerate(rows):
        y = y0 + idx * row_step
        add_human_marker(parts, row, chart_x - 46, y, bar_h)
        parts.append(rect(chart_x, y - 7, chart_w, bar_h + 14, TRACK, "#e1d9cd", cls="track", rx=9))
        clip_id = f"panel2-row-{idx}"
        parts.append(f"<defs>{clip_path_rect(clip_id, chart_x, y, chart_w, bar_h, 10)}</defs>")
        parts.append(f'<g class="bar-segments" clip-path="url(#{clip_id})">')

        x = chart_x
        for key in BIN_ORDER:
            value = fnum(row, key)
            width = chart_w * value / 200
            if width:
                parts.append(rect(x, y, width, bar_h, COLORS[key], "none", rx=0, extra=f'data-bin="{key}" data-value="{row[key]}"'))
                add_segment_label(parts, x + width / 2, y, width, bar_h, count_label(value), COLORS[key])
            x += width
        parts.append("</g>")
        parts.append(rect(chart_x, y, chart_w, bar_h, "none", "rgba(45,52,57,.18)", cls="bar-outline", rx=10))

        parts.append(text(chart_x - 18, y + 41, count_label(fnum(row, "correct_total")), "bar-label", "end"))
        parts.append(text(chart_x + chart_w + 18, y + 41, count_label(fnum(row, "wrong_total")), "bar-label", "start"))
        add_row_identity(parts, row, score_x, name_x, y + 41)
    add_legend(parts, 2424, chart_x, chart_w, "panel2")
    add_footer(parts, provenance)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def display_sequence(row: dict[str, str]) -> list[str]:
    seq: list[str] = []
    for key in BIN_ORDER:
        seq.extend([key] * inum(row, f"dot_{key}"))
    if len(seq) != DOT_DISPLAY_TOTAL:
        raise ValueError(f"{row['reader_label']}: expected {DOT_DISPLAY_TOTAL} display units, got {len(seq)}")
    return seq


def panel_3(rows: list[dict[str, str]], provenance: dict[str, object]) -> str:
    title = "One Hundred Percentage Bars, Colored by Outcome"
    subtitle = "Each row has 100 thin capsule bars: about one mark per percentage point, rounded from exact 200-case bins."
    parts = svg_open(3, title, subtitle, rows, provenance)
    add_header(parts, title, subtitle)
    unit_w, unit_h, gap = 11.0, 30.0, 13.6
    start_x, y0, row_step = 760, 390, 108
    score_x, name_x = 150, 620
    totals_x = 3500
    parts.append(text(score_x, 338, "Score", "axis-label", "end"))
    parts.append(text(name_x, 338, "Reader / model", "axis-label", "end"))
    parts.append(text(totals_x, 338, "correct / I don't know / wrong", "axis-label", "end"))
    for idx, row in enumerate(rows):
        y = y0 + idx * row_step
        add_human_marker(parts, row, start_x - 46, y, unit_h)
        parts.append(rect(start_x - 18, y - 20, 2448, 40, TRACK, "#e1d9cd", cls="track", rx=12))
        for unit_idx, key in enumerate(display_sequence(row)):
            x = start_x + unit_idx * (unit_w + gap)
            parts.append(capsule(x, y - unit_h / 2, unit_w, unit_h, COLORS[key], STROKES[key], extra=f'data-bin="{key}" data-row="{esc(display_name(row))}"'))
        add_row_identity(parts, row, score_x, name_x, y + 3)
        parts.append(text(totals_x, y + 3, f"{count_label(fnum(row, 'correct_total'))} / {count_label(fnum(row, 'neutral_total'))} / {count_label(fnum(row, 'wrong_total'))}", "bar-label", "end"))
    add_legend(parts, 2388, start_x - 18, 2448, "panel3")
    add_footer(parts, provenance)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def add_legend(parts: list[str], y: float, x0: float, legend_w: float, panel_key: str) -> None:
    bar_h = 36.0
    segment_w = legend_w / len(BIN_ORDER)
    bar_y = y + 24
    correct_mid = x0 + segment_w * 2.5
    neutral_mid = x0 + segment_w * 5.5
    wrong_mid = x0 + segment_w * 8.5
    parts.append(text(correct_mid, y, "Correct, by confidence", "legend-label", "middle"))
    parts.append(text(neutral_mid, y, "I don't know", "legend-label", "middle"))
    parts.append(text(wrong_mid, y, "Wrong, by confidence", "legend-label", "middle"))
    for idx, key in enumerate(BIN_ORDER):
        parts.append(
            rect(
                x0 + idx * segment_w,
                bar_y,
                segment_w,
                bar_h,
                COLORS[key],
                "none",
                cls="bar",
                rx=0,
                extra=f'data-legend-panel="{panel_key}" data-legend-bin="{key}"',
            )
        )
    parts.append(
        rect(
            x0,
            bar_y,
            legend_w,
            bar_h,
            "none",
            "rgba(45,52,57,.22)",
            cls="legend-outline",
            rx=8,
            extra=f'data-legend-panel="{panel_key}"',
        )
    )
    left_y = bar_y + bar_h + 44
    bracket_y = bar_y + bar_h + 18
    parts.append(line(x0, bracket_y, x0 + segment_w * 5, bracket_y, "axis"))
    parts.append(line(x0 + segment_w * 6, bracket_y, x0 + segment_w * 11, bracket_y, "axis"))
    parts.append(line(x0, bracket_y - 9, x0, bracket_y + 9, "axis"))
    parts.append(line(x0 + segment_w * 5, bracket_y - 9, x0 + segment_w * 5, bracket_y + 9, "axis"))
    parts.append(line(x0 + segment_w * 6, bracket_y - 9, x0 + segment_w * 6, bracket_y + 9, "axis"))
    parts.append(line(x0 + segment_w * 11, bracket_y - 9, x0 + segment_w * 11, bracket_y + 9, "axis"))
    parts.append(text(x0, left_y, "L4 high confidence", "bar-label", "start"))
    parts.append(text(x0 + segment_w * 5, left_y, "L0 low confidence", "bar-label", "end"))
    parts.append(text(x0 + segment_w * 6, left_y, "L0 low confidence", "bar-label", "start"))
    parts.append(text(x0 + segment_w * 11, left_y, "L4 high confidence", "bar-label", "end"))


def write_contact_sheet(out_dir: Path) -> None:
    cards: list[str] = []
    for filename in PANEL_FILES:
        svg = (out_dir / filename).read_text(encoding="utf-8")
        caption = "Panel 2. Edge-justified 200-case ledger." if filename.startswith("panel_2") else "Panel 3. One hundred-bar percentage strip."
        cards.append(f"<figure>{svg}<figcaption>{esc(caption)}</figcaption></figure>")
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>RadLE v2 Score1000 Panels 2 and 3</title>
<style>
body {{ margin: 0; padding: 28px; background: #efede7; font-family: {FONT}; color: {INK}; }}
h1 {{ font-size: 26px; margin: 0 0 18px 0; }}
figure {{ margin: 0 0 34px 0; background: white; padding: 12px; border: 1px solid #d7d0c5; }}
svg {{ width: 100%; height: auto; display: block; }}
figcaption {{ font-size: 15px; margin-top: 8px; color: {MUTED}; }}
</style>
</head>
<body>
<h1>RadLE v2 Score1000 handwritten panels 2 and 3</h1>
{''.join(cards)}
</body>
</html>
"""
    write_text(out_dir / "contact_sheet.html", html_doc)


def write_support_files(out_dir: Path, provenance: dict[str, object], rows: list[dict[str, str]]) -> None:
    captions = [
        "# Captions",
        "",
        "## Panel 2. Correctness and confidence distribution",
        "Edge-justified stacked bars show 200 effective cases per reader or model. All Likert levels remain visible: correct diagnoses start at the left edge in blue, I don't know/failure/invalid outcomes follow in grey, and wrong diagnoses continue to the right edge in red.",
        "",
        "## Panel 3. One hundred percentage bars, colored by outcome",
        "Each row has 100 displayed thin capsule bars, so each mark is about one percentage point. Marks use deterministic largest-remainder apportionment from exact 200-case bins; exact values are preserved in `score1000_panel23_bins.csv` and SVG metadata. The left-side row label pairs the final Score1000 value with the formatted reader/model name.",
        "",
        f"Source master SHA256: `{provenance['source_master_sha256']}`",
    ]
    write_text(out_dir / "captions.md", "\n".join(captions) + "\n")

    data_prov = [
        "# Data Provenance",
        "",
        f"- Source master SHA256: `{provenance['source_master_sha256']}`",
        f"- Score1000 scored rows: `{provenance['score1000_scored_rows']['path']}`",
        f"- Score1000 scored rows SHA256: `{provenance['score1000_scored_rows']['sha256']}`",
        "- Summary CSV: `score1000_panel23_bins.csv`",
        "- Percentage-mark display: deterministic largest-remainder apportionment to 100 barcode-style capsule bars per row.",
    ]
    write_text(out_dir / "data_provenance.md", "\n".join(data_prov) + "\n")
    write_text(
        out_dir / "data_provenance.json",
        json.dumps(
            {
                **provenance,
                "generated_at": utc_now(),
                "panel_package": rel(out_dir),
                "panels": PANEL_FILES,
            },
            indent=2,
        )
        + "\n",
    )
    checklist = [
        "# Reviewer Checklist",
        "",
        "- [ ] Panel 2 bars are justified from left edge to right edge and each row spans 200 effective cases.",
        "- [ ] Panel 2 preserves all 11 Likert bins, with only the row silhouette rounded and all internal cuts square, flush, and unstroked.",
        "- [ ] The legend is the B3 equal-width 11-bin bar with `Correct, by confidence`, `I don't know`, and `Wrong, by confidence` labels.",
        "- [ ] Panel 2 labels appear only where segments are large enough.",
        "- [ ] Panel 3 has 100 barcode-style capsule bars per row, does not wrap, and pale marks remain visible.",
        "- [ ] Visible row identity appears left of the bars as a right-aligned Score1000 value plus formatted reader/model name.",
        "- [ ] Visible model names are publication-formatted, with no raw lowercase underscore identifiers.",
        "- [ ] Human labels read `Board-certified radiologists` and `Radiology trainees`.",
        "- [ ] No Panel 4/5 files are present.",
    ]
    write_text(out_dir / "reviewer_checklist.md", "\n".join(checklist) + "\n")
    write_text(out_dir / "handwritten_panels_qa.txt", "Generated; structural audit and visual QA required after generation.\n")
    with (out_dir / "font_sizes.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["name", "selector", "surface", "size_px", "purpose"])
        writer.writerows(FONT_SIZE_ROWS)


def write_manifest(out_dir: Path, provenance: dict[str, object]) -> dict[str, object]:
    files = [
        "score1000_panel23_bins.csv",
        "score1000_likert_direction_provenance.json",
        *PANEL_FILES,
        "contact_sheet.html",
        "captions.md",
        "data_provenance.json",
        "data_provenance.md",
        "reviewer_checklist.md",
        "font_sizes.csv",
        "handwritten_panels_qa.txt",
    ]
    manifest = {
        "generated_at": utc_now(),
        "generator": rel(Path(__file__)),
        "source_master_sha256": provenance["source_master_sha256"],
        "score1000_scored_rows_sha256": provenance["score1000_scored_rows"]["sha256"],
        "panels": [{"panel_id": 2, "file": PANEL_FILES[0]}, {"panel_id": 3, "file": PANEL_FILES[1]}],
        "files": [],
    }
    for name in files:
        path = out_dir / name
        entry: dict[str, object] = {"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
        if path.suffix == ".csv":
            entry["rows"] = max(0, sum(1 for _ in path.open("r", encoding="utf-8")) - 1)
        manifest["files"].append(entry)
    write_text(out_dir / "figure_manifest.json", json.dumps(manifest, indent=2) + "\n")
    return manifest


def clean_stale_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    allowed = {
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
        "score1000_panel23_audit_report.json",
        "score1000_panel23_audit_report.md",
    }
    for path in out_dir.iterdir():
        if path.is_file() and path.name not in allowed:
            path.unlink()
    for path in out_dir.glob("panel_*.svg"):
        if path.name not in PANEL_FILES:
            path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score-root", type=Path, default=DEFAULT_SCORE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    score_root = args.score_root.resolve()
    out_dir = args.out_dir.resolve()
    clean_stale_outputs(out_dir)
    rows = read_csv(out_dir / "score1000_panel23_bins.csv")
    provenance = json.loads((out_dir / "score1000_likert_direction_provenance.json").read_text(encoding="utf-8"))
    if str(provenance["source_master_sha256"]).upper() != EXPECTED_SOURCE_SHA256:
        raise ValueError("Unexpected source master SHA in panel provenance")

    write_text(out_dir / PANEL_FILES[0], panel_2(rows, provenance))
    write_text(out_dir / PANEL_FILES[1], panel_3(rows, provenance))
    write_support_files(out_dir, provenance, rows)
    write_contact_sheet(out_dir)
    write_manifest(out_dir, provenance)
    print(f"[PASS] generated Score1000 Panel 2/3 package {out_dir}")


if __name__ == "__main__":
    main()
