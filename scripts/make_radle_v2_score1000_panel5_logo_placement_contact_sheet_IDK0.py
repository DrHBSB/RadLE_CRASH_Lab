#!/usr/bin/env python3
"""Prototype logo-placement options for the Score2000 Panel 5 PNG."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

import make_radle_v2_score1000_panel23_svg_IDK0 as panel_svg

read_csv = panel_svg.read_csv
write_text = panel_svg.write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PANEL = (
    REPO_ROOT
    / "outputs"
    / "radle_v2_stats"
    / "final_scoring_radiologist_20260708_161500_IDK0"
    / "likert5_score1000_IDK0"
    / "handwritten_panels_model_group_color_final_IDK0"
    / "panel_2_score1000_5_0_clean_score1000_bar_chart.png"
)
DEFAULT_OUT_DIR = DEFAULT_PANEL.parent / "panel5_logo_placement_options"
DEFAULT_SOURCE_PANEL_DIR = DEFAULT_PANEL.parent
LOGO_DIR = REPO_ROOT / "scripts" / "assets" / "radle_score1000_logos"
BASE_YTOP140_SVG = "panel_2_score1000_5_0_clean_score1000_bar_chart_ytop140_tick100.svg"
BASE_YTOP140_PNG = "panel_2_score1000_5_0_clean_score1000_bar_chart_ytop140_tick100.png"
PROMOTED_54_BASENAME = "panel_2_score1000_5_4_icon_ribbon_score1000_bar_chart"
PROMOTED_54_TITLE = "Panel 5.4 bottom-logo confidence-weighted diagnosis chart"
PROMOTED_54_CAPTION = (
    "Panel 5.4. Bottom-logo closed/API-model companion using the shifted confidence-weighted "
    "diagnosis score with an A1 kink after 1000; model logos sit under the x-axis names "
    "and are bound to bars by reader_label."
)
PROMOTED_54_READER_LABELS = list(panel_svg.SCORE1000_BAR_CLOSED_READER_LABELS)
PROMOTED_54_BAR_COLORS = panel_svg.SCORE1000_BAR_COLORS_PALETTE_A

W, H = 3600, 2840
CHART_X = 360.0
CHART_Y = 540.0
CHART_W = 3080.0
CHART_H = 1610.0
BAR_W = 230.0
SCORE2000_SHIFT = 1000.0
SCORE2000_BASELINE = 1000.0
Y_MIN = 0.0
Y_MAX = 2000.0
Y_TICKS = panel_svg.SCORE1000_BAR_A1_TICKS
AXIS_BREAK_AFTER = panel_svg.SCORE1000_BAR_AXIS_BREAK_AFTER
AXIS_BREAK_STYLE = "a1_double_slash"
AXIS_BREAK_TOP_FRACTION = panel_svg.SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION
LOGO_SCALE = 1.5
ZERO_Y = panel_svg.score1000_bar_scaled_y(
    SCORE2000_BASELINE,
    y_min=Y_MIN,
    y_max=Y_MAX,
    chart_y=CHART_Y,
    chart_h=CHART_H,
    axis_break_after=AXIS_BREAK_AFTER,
    axis_break_top_fraction=AXIS_BREAK_TOP_FRACTION,
)
CHART_BOTTOM = CHART_Y + CHART_H
SVG_NS = "{http://www.w3.org/2000/svg}"
PANEL_TITLE = panel_svg.SCORE1000_BAR_PANEL_TITLE
FIGURE_TITLE_Y = 166.0
FIGURE_TITLE_FONT_PX = 90
PANEL_TITLE_Y = 394.0
PANEL_TITLE_FONT_PX = 80
SCORE_VALUE_FONT_PX = panel_svg.SCORE1000_BAR_VALUE_FONT_SIZE
SCORE_TICK_FONT_PX = 45
FOOTER_DIVIDER_Y = 2500.0
FOOTER_X = CHART_X
FOOTER_RIGHT_X = CHART_X + CHART_W
FOOTER_FIRST_LINE_Y = 2586.0
FOOTER_LINE_STEP = 54.0
FOOTER_FONT_PX = 44
IDK_SCORE = 1


def footer_lines_for_idk_score(idk_score: int) -> list[str]:
    return panel_svg.score1000_bar_footer_lines(idk_score)


FOOTER_LINES = footer_lines_for_idk_score(IDK_SCORE)
OPTION4_REDUCED_KEYS = {"grok_4_3", "claude_fable_5", "gemini_3_1_pro", "gpt_5_5"}
BOTTOM_LOGO_CENTER_Y = 2390.0


@dataclass(frozen=True)
class Series:
    key: str
    label: str
    score: float
    logo: str
    color: str
    is_human: bool = False


@dataclass(frozen=True)
class BarSlot:
    reader_label: str
    reader_key: str
    score: float
    x: float
    y: float
    width: float
    height: float
    color: str

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2


SELECTED_READER_LABELS = set(PROMOTED_54_READER_LABELS)
SERIES_METADATA = {
    "Human Expert Baseline": {
        "key": "human_expert_baseline",
        "label": "Human Expert Baseline",
        "logo": "human_expert_baseline_radiologist_navy_logo.png",
        "color": PROMOTED_54_BAR_COLORS["Human Expert Baseline"],
        "is_human": True,
    },
    "claude_fable_5": {
        "key": "claude_fable_5",
        "label": "Claude Fable 5",
        "logo": "claude_fable_5_logo.png",
        "color": PROMOTED_54_BAR_COLORS["claude_fable_5"],
        "is_human": False,
    },
    "grok_4_3": {
        "key": "grok_4_3",
        "label": "Grok 4.3",
        "logo": "grok_4_3_logo.png",
        "color": PROMOTED_54_BAR_COLORS["grok_4_3"],
        "is_human": False,
    },
    "gemini_3_1_pro": {
        "key": "gemini_3_1_pro",
        "label": "Gemini 3.1 Pro",
        "logo": "gemini_3_1_pro_logo.png",
        "color": PROMOTED_54_BAR_COLORS["gemini_3_1_pro"],
        "is_human": False,
    },
    "gpt_5_5": {
        "key": "gpt_5_5",
        "label": "GPT-5.5",
        "logo": "gpt_5_5_logo.png",
        "color": PROMOTED_54_BAR_COLORS["gpt_5_5"],
        "is_human": False,
    },
    "qwen_3_7_plus": {
        "key": "qwen_3_7_plus",
        "label": "Qwen 3.7 Plus",
        "logo": "qwen_3_7_plus_logo.png",
        "color": PROMOTED_54_BAR_COLORS["qwen_3_7_plus"],
        "is_human": False,
    },
    "glm_5v_turbo": {
        "key": "glm_5v_turbo",
        "label": "GLM-5V Turbo",
        "logo": "glm_5v_turbo_logo.png",
        "color": PROMOTED_54_BAR_COLORS["glm_5v_turbo"],
        "is_human": False,
    },
    "octomed_7b": {
        "key": "octomed_7b",
        "label": "OctoMed 7B",
        "logo": "octomed_7b_logo.png",
        "color": PROMOTED_54_BAR_COLORS["octomed_7b"],
        "is_human": False,
    },
}


def read_source_bar_slots(source_svg_path: Path) -> list[BarSlot]:
    root = ET.parse(source_svg_path).getroot()
    bars = [elem for elem in root.findall(f".//{SVG_NS}rect") if elem.get("data-score1000-bar") == "true"]
    if not bars:
        raise ValueError(f"Promoted Panel 5.4 source SVG has no data-score1000-bar rectangles: {source_svg_path}")
    slots: list[BarSlot] = []
    seen: set[str] = set()
    for index, bar in enumerate(bars):
        reader_label = str(bar.get("data-reader-label") or "").strip()
        if not reader_label:
            raise ValueError(f"Promoted Panel 5.4 source bar {index} is missing data-reader-label: {source_svg_path}")
        if reader_label in seen:
            raise ValueError(f"Promoted Panel 5.4 source SVG has duplicate bar reader_label={reader_label!r}")
        seen.add(reader_label)
        score_text = str(bar.get("data-score2000-value") or bar.get("data-score1000-value") or "").strip()
        if not score_text:
            raise ValueError(f"Promoted Panel 5.4 source bar {reader_label!r} is missing Score2000 metadata")
        reader_key = str(bar.get("data-reader-key") or panel_svg.score1000_bar_reader_key(reader_label))
        slots.append(
            BarSlot(
                reader_label=reader_label,
                reader_key=reader_key,
                score=float(score_text),
                x=float(bar.get("x", "nan")),
                y=float(bar.get("y", "nan")),
                width=float(bar.get("width", "nan")),
                height=float(bar.get("height", "nan")),
                color=str(bar.get("fill") or SERIES_METADATA.get(reader_label, {}).get("color") or "#000000"),
            )
        )
    return slots


def load_series(source_panel_dir: Path, bar_slots: list[BarSlot]) -> list[Series]:
    expected_reader_labels = [slot.reader_label for slot in bar_slots]
    rows = read_csv(source_panel_dir / "score1000_panel23_bins.csv")
    row_by_label = {row["reader_label"]: row for row in rows}
    missing_rows = [label for label in expected_reader_labels if label not in row_by_label]
    if missing_rows:
        raise ValueError(f"Panel 5.4 source SVG bars are missing from score1000_panel23_bins.csv: {missing_rows}")
    missing_catalog = [label for label in expected_reader_labels if label not in SERIES_METADATA]
    if missing_catalog:
        raise ValueError(f"Panel 5.4 has no explicit logo catalog mapping for reader_label(s): {missing_catalog}")
    slot_by_label = {slot.reader_label: slot for slot in bar_slots}
    return [
        Series(
            key=str(SERIES_METADATA[reader_label]["key"]),
            label=str(SERIES_METADATA[reader_label]["label"]),
            score=float(row_by_label[reader_label]["score2000"]),
            logo=str(SERIES_METADATA[reader_label]["logo"]),
            color=slot_by_label[reader_label].color,
            is_human=bool(SERIES_METADATA[reader_label]["is_human"]),
        )
        for reader_label in expected_reader_labels
    ]


def validate_series_matches_bars(series: list[Series], bar_slots: list[BarSlot]) -> None:
    labels_from_series = [csv_reader_label(item) for item in series]
    labels_from_bars = [slot.reader_label for slot in bar_slots]
    if labels_from_series != labels_from_bars:
        raise ValueError(f"Panel 5.4 series/bar order mismatch: series={labels_from_series} bars={labels_from_bars}")
    for item, slot in zip(series, bar_slots):
        if item.key != slot.reader_key:
            raise ValueError(
                f"Panel 5.4 logo key mismatch for {slot.reader_label}: catalog={item.key!r} source_bar={slot.reader_key!r}"
            )
        if abs(item.score - slot.score) > 0.05:
            raise ValueError(
                f"Panel 5.4 Score2000 mismatch for {slot.reader_label}: csv={item.score:.6f} source_bar={slot.score:.6f}"
            )
        logo_path = LOGO_DIR / item.logo
        if not logo_path.exists():
            raise FileNotFoundError(f"Panel 5.4 logo asset missing for {slot.reader_label}: {logo_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=None, help="Optional pre-rendered base PNG. Default builds a 0..2000 Score2000 y-axis base.")
    parser.add_argument("--source-panel-dir", type=Path, default=DEFAULT_SOURCE_PANEL_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--idk-score", type=int, choices=[0, 1], default=1)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def configure_idk_score(idk_score: int) -> None:
    global IDK_SCORE, FOOTER_LINES
    IDK_SCORE = idk_score
    FOOTER_LINES = footer_lines_for_idk_score(idk_score)
    panel_svg.configure_idk_score(idk_score)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def hex_to_rgba(value: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha)


def score_y(score: float) -> float:
    return panel_svg.score1000_bar_scaled_y(
        score,
        y_min=Y_MIN,
        y_max=Y_MAX,
        chart_y=CHART_Y,
        chart_h=CHART_H,
        axis_break_after=AXIS_BREAK_AFTER,
        axis_break_top_fraction=AXIS_BREAK_TOP_FRACTION,
    )


def row_geometry(index: int, score: float, series_count: int) -> dict[str, float]:
    slot_w = CHART_W / series_count
    bar_x = CHART_X + index * slot_w + (slot_w - BAR_W) / 2
    sy = score_y(score)
    bar_y = sy
    bar_h = max(0.0, CHART_BOTTOM - sy)
    return {
        "bar_x": bar_x,
        "bar_y": bar_y,
        "bar_h": bar_h,
        "center_x": bar_x + BAR_W / 2,
        "value_y": bar_y - 22,
    }


def render_svg_to_png(svg_path: Path, png_path: Path) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        try:
            render_svg_to_png_with_chrome(svg_path, png_path)
            return
        except Exception:
            render_svg_to_png_with_node(svg_path, png_path)
            return

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto(svg_path.resolve().as_uri(), wait_until="networkidle")
        page.locator("svg").screenshot(path=str(png_path))
        page.close()
        browser.close()


def render_svg_to_png_with_chrome(svg_path: Path, png_path: Path) -> None:
    candidates = [
        shutil.which("chrome"),
        shutil.which("msedge"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    browser_path = next((Path(path) for path in candidates if path and Path(path).exists()), None)
    if browser_path is None:
        raise RuntimeError("Chrome or Edge was not found for SVG rendering")

    with tempfile.TemporaryDirectory(prefix="radle_score1000_chrome_") as profile:
        subprocess.run(
            [
                str(browser_path),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
                f"--window-size={W},{H}",
                f"--user-data-dir={profile}",
                f"--screenshot={png_path.resolve()}",
                svg_path.resolve().as_uri(),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def render_svg_to_png_with_node(svg_path: Path, png_path: Path) -> None:
    bundled_node = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "bin" / "node.exe"
    bundled_node_modules = bundled_node.parents[1] / "node_modules"
    if bundled_node.exists() and bundled_node_modules.exists():
        node_exe = bundled_node
        node_modules = bundled_node_modules
    else:
        node_exe = Path(shutil.which("node") or bundled_node)
        node_modules = node_exe.parents[1] / "node_modules"
    if not node_exe.exists():
        raise RuntimeError(f"Node.js was not found for SVG rendering: {node_exe}")
    if not node_modules.exists():
        raise RuntimeError(f"Node.js modules were not found for SVG rendering: {node_modules}")

    js = r"""
const { chromium } = require('playwright');
const [svgPath, pngPath, width, height] = process.argv.slice(1);
const fileUrl = 'file:///' + svgPath.replace(/\\/g, '/');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: Number(width), height: Number(height) }, deviceScaleFactor: 1 });
  await page.goto(fileUrl, { waitUntil: 'networkidle' });
  await page.locator('svg').screenshot({ path: pngPath });
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
"""
    env = os.environ.copy()
    env["NODE_PATH"] = str(node_modules)
    subprocess.run(
        [str(node_exe), "-e", js, str(svg_path.resolve()), str(png_path.resolve()), str(W), str(H)],
        check=True,
        env=env,
    )


def append_345_footer(svg: str) -> str:
    footer = [f'<line class="axis" x1="{FOOTER_X:.1f}" y1="{FOOTER_DIVIDER_Y:.1f}" x2="{FOOTER_RIGHT_X:.1f}" y2="{FOOTER_DIVIDER_Y:.1f}" />']
    for idx, line_text in enumerate(FOOTER_LINES):
        footer.append(
            f'<text class="score1000-footer" x="{FOOTER_X:.1f}" y="{FOOTER_FIRST_LINE_Y + idx * FOOTER_LINE_STEP:.1f}" text-anchor="start">'
            f"{html.escape(line_text, quote=False)}</text>"
        )
    return svg.replace("</svg>", "\n".join(footer) + "\n</svg>")


def apply_svg_layout_overrides(svg: str) -> str:
    svg = re.sub(
        r'(<text class="figure-title" x="1800\.0" y=")144\.0(" text-anchor="middle">)',
        rf"\g<1>{FIGURE_TITLE_Y:.1f}\2",
        svg,
    )
    svg = re.sub(
        r'(<text class="title" x="1800\.0" y=")332\.0(" text-anchor="middle">)',
        rf"\g<1>{PANEL_TITLE_Y:.1f}\2",
        svg,
    )
    svg = svg.replace(">Score1000</text>", ">Score2000</text>")
    replacements = {
        r"(\.figure-title \{[^}]*font-size: )[0-9.]+px;": rf"\g<1>{FIGURE_TITLE_FONT_PX}px;",
        r"(\.title \{[^}]*font-size: )54px;": rf"\g<1>{PANEL_TITLE_FONT_PX}px;",
        r"(\.score1000-panel-title \{[^}]*font-size: )[0-9.]+px;": rf"\g<1>{PANEL_TITLE_FONT_PX}px;",
        r"(\.score1000-tick-label \{[^}]*font-size: )30px;": rf"\g<1>{SCORE_TICK_FONT_PX}px;",
        r"(\.score1000-bar-value \{[^}]*font-size: )[0-9.]+px;": rf"\g<1>{SCORE_VALUE_FONT_PX}px;",
        r"(\.score1000-footer \{[^}]*font-size: )[0-9.]+px;": rf"\g<1>{FOOTER_FONT_PX}px;",
    }
    for pattern, replacement in replacements.items():
        svg = re.sub(pattern, replacement, svg)
    if ".score1000-footer" not in svg:
        svg = svg.replace(
            "</style>",
            (
                f"      .score1000-footer {{ font-family: Lexend, \"Helvetica Neue\", Helvetica, Arial, sans-serif; "
                f"font-size: {FOOTER_FONT_PX}px; font-weight: 400; fill: #202124; letter-spacing: 0; }}\n"
                "    </style>"
            ),
        )
    return svg


def strip_score1000_axis_note(svg: str) -> str:
    svg = re.sub(
        r'\n<text class="variant-legend-label" x="1800\.0" y="2410\.0" text-anchor="middle">'
        r"Higher is better\. Axis range shown: .*?</text>",
        "",
        svg,
    )
    return re.sub(
        r"Higher is better; y-axis spans (-?\d+(?:\.\d+)?) to (-?\d+(?:\.\d+)?)\.",
        r"Y-axis spans \1 to \2 on the shifted Score2000 display scale.",
        svg,
    )


def build_ymax100_base_panel(source_panel_dir: Path, out_dir: Path) -> tuple[Path, Path]:
    source_panel_dir = source_panel_dir.resolve()
    svg_path = out_dir / BASE_YTOP140_SVG
    png_path = out_dir / BASE_YTOP140_PNG
    rows = read_csv(source_panel_dir / "score1000_panel23_bins.csv")
    provenance = json.loads((source_panel_dir / "score1000_likert_direction_provenance.json").read_text(encoding="utf-8"))
    panel_svg.SCORE1000_BAR_CHART_Y = CHART_Y
    panel_svg.SCORE1000_BAR_CHART_H = CHART_H
    svg = panel_svg.panel_5_score1000_bar_chart(
        rows,
        provenance,
        variant_label="5.0 clean confidence-weighted diagnosis vertical bar chart",
        y_min=Y_MIN,
        y_max=Y_MAX,
        ticks=Y_TICKS,
        selected_reader_labels=PROMOTED_54_READER_LABELS,
        include_model_icons=False,
        bar_colors=PROMOTED_54_BAR_COLORS,
        panel_title=PANEL_TITLE,
        chart_y=CHART_Y,
        footer_note="",
        axis_break_after=AXIS_BREAK_AFTER,
        axis_break_style=AXIS_BREAK_STYLE,
        axis_break_top_fraction=AXIS_BREAK_TOP_FRACTION,
    )
    svg = append_345_footer(apply_svg_layout_overrides(strip_score1000_axis_note(svg)))
    write_text(svg_path, svg)
    render_svg_to_png(svg_path, png_path)
    return svg_path, png_path


def load_logo(name: str) -> Image.Image:
    return Image.open(LOGO_DIR / name).convert("RGBA")


def fit_logo(logo: Image.Image, size: int) -> Image.Image:
    work = logo.copy()
    work.thumbnail((size, size), Image.Resampling.LANCZOS)
    return work


def scaled_logo_size(size: int) -> int:
    return int(round(size * LOGO_SCALE))


def paste_logo(canvas: Image.Image, logo: Image.Image, center_x: float, center_y: float) -> None:
    x = round(center_x - logo.width / 2)
    y = round(center_y - logo.height / 2)
    canvas.alpha_composite(logo, (x, y))


def draw_logo(
    canvas: Image.Image,
    series: Series,
    center_x: float,
    center_y: float,
    *,
    logo_size: int,
    backplate: str = "circle",
    alpha: int = 255,
    halo: bool = True,
) -> None:
    draw = ImageDraw.Draw(canvas, "RGBA")
    color = hex_to_rgba(series.color, 255)
    logo = fit_logo(load_logo(series.logo), logo_size)
    logo.putalpha(logo.getchannel("A").point(lambda p: int(p * alpha / 255)))
    pad = 18
    box = logo_size + pad * 2
    x0 = center_x - box / 2
    y0 = center_y - box / 2
    x1 = center_x + box / 2
    y1 = center_y + box / 2

    if backplate == "circle":
        if halo:
            draw.ellipse((x0 - 7, y0 - 7, x1 + 7, y1 + 7), fill=(255, 255, 255, 230))
        draw.ellipse((x0, y0, x1, y1), fill=(255, 255, 255, 235), outline=color, width=5)
    elif backplate == "pill":
        if halo:
            draw.rounded_rectangle((x0 - 8, y0 - 8, x1 + 8, y1 + 8), radius=box / 2, fill=(255, 255, 255, 220))
        draw.rounded_rectangle((x0, y0, x1, y1), radius=box / 2, fill=(255, 255, 255, 238), outline=color, width=5)
    elif backplate == "none" and halo:
        draw.ellipse((center_x - logo_size / 2 - 10, center_y - logo_size / 2 - 10, center_x + logo_size / 2 + 10, center_y + logo_size / 2 + 10), fill=(255, 255, 255, 210))

    paste_logo(canvas, logo, center_x, center_y)


def option_previous_style(base: Image.Image, series: list[Series]) -> Image.Image:
    canvas = base.copy().convert("RGBA")
    for i, item in enumerate(series):
        geom = row_geometry(i, item.score, len(series))
        raw_size = 118 if item.is_human else 112
        logo_size = scaled_logo_size(raw_size)
        if item.is_human:
            plate = "none"
            halo = False
        else:
            plate = "none"
            halo = True
        # Score2000 bars use a 0-origin baseline; the shifted 1000 line is reference-only.
        cy = max(350 + logo_size / 2, geom["bar_y"] - 105 - logo_size / 2)
        draw_logo(canvas, item, geom["center_x"], cy, logo_size=logo_size, backplate=plate, halo=halo)
    return canvas


def option_uniform_badges(base: Image.Image, series: list[Series]) -> Image.Image:
    canvas = base.copy().convert("RGBA")
    for i, item in enumerate(series):
        geom = row_geometry(i, item.score, len(series))
        if item.is_human:
            cy = max(350, geom["bar_y"] - 210)
            draw_logo(canvas, item, geom["center_x"], cy, logo_size=scaled_logo_size(138), backplate="none", halo=False)
        else:
            cy = geom["bar_y"] - 166
            raw_size = 116 if item.key == "octomed_7b" else 104
            draw_logo(canvas, item, geom["center_x"], cy, logo_size=scaled_logo_size(raw_size), backplate="none", halo=False)
    return canvas


def option_baseline_row(base: Image.Image, series: list[Series]) -> Image.Image:
    canvas = base.copy().convert("RGBA")
    for i, item in enumerate(series):
        geom = row_geometry(i, item.score, len(series))
        if item.is_human:
            draw_logo(canvas, item, geom["center_x"], ZERO_Y + 126, logo_size=scaled_logo_size(148), backplate="none", halo=False)
        else:
            draw_logo(canvas, item, geom["center_x"], ZERO_Y + 126, logo_size=scaled_logo_size(92), backplate="circle")
    return canvas


def bottom_logo_size(item: Series) -> int:
    raw_size = 90 if item.key in OPTION4_REDUCED_KEYS else 104
    return scaled_logo_size(raw_size)


def option_bottom_logos(base: Image.Image, series: list[Series]) -> Image.Image:
    canvas = base.copy().convert("RGBA")
    for i, item in enumerate(series):
        geom = row_geometry(i, item.score, len(series))
        draw_logo(canvas, item, geom["center_x"], BOTTOM_LOGO_CENTER_Y, logo_size=bottom_logo_size(item), backplate="none", halo=False)
    return canvas


def option_human_vs_model_split(base: Image.Image, series: list[Series]) -> Image.Image:
    canvas = base.copy().convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")
    model_badge_top = CHART_BOTTOM + 142
    model_badge_bottom = CHART_BOTTOM + 294
    model_badge_center = (model_badge_top + model_badge_bottom) / 2
    for i, item in enumerate(series):
        geom = row_geometry(i, item.score, len(series))
        if item.is_human:
            draw_logo(canvas, item, geom["center_x"], max(350, geom["bar_y"] - 188), logo_size=scaled_logo_size(138), backplate="none", halo=False)
        else:
            draw.rounded_rectangle(
                (geom["center_x"] - 88, model_badge_top, geom["center_x"] + 88, model_badge_bottom),
                radius=28,
                fill=(255, 255, 255, 238),
                outline=hex_to_rgba(item.color, 255),
                width=4,
            )
            draw_logo(canvas, item, geom["center_x"], model_badge_center, logo_size=scaled_logo_size(68), backplate="none", halo=False)
            draw.line(
                (geom["center_x"], model_badge_top - 12, geom["center_x"], CHART_BOTTOM + 86),
                fill=hex_to_rgba(item.color, 120),
                width=4,
            )
    return canvas


OPTIONS = [
    ("panel_2_score1000_5_logo_option_1_prior_radle_style.png", option_previous_style),
    ("panel_2_score1000_5_logo_option_2_uniform_badges.png", option_uniform_badges),
    ("panel_2_score1000_5_logo_option_3_baseline_rail.png", option_baseline_row),
    ("panel_2_score1000_5_logo_option_4_bottom_logos.png", option_bottom_logos),
]

DISCARDED_OPTION_FILES = [
    "panel_2_score1000_5_logo_option_4_top_ribbon.png",
    "panel_2_score1000_5_logo_option_5_human_model_split.png",
    "panel_2_score1000_5_0_clean_score1000_bar_chart_ymax100.png",
    "panel_2_score1000_5_0_clean_score1000_bar_chart_ymax100.svg",
]


def make_contact_sheet(option_paths: list[Path], out_path: Path) -> None:
    thumbs: list[Image.Image] = []
    for path in option_paths:
        im = Image.open(path).convert("RGB")
        im.thumbnail((1220, 962), Image.Resampling.LANCZOS)
        thumbs.append(im)

    pad = 44
    title_h = 98
    card_w = 1290
    card_h = 1046
    n_rows = max(1, ceil(len(thumbs) / 2))
    sheet = Image.new("RGB", (pad * 2 + card_w * 2 + pad, title_h + card_h * n_rows + pad * (n_rows + 1)), (239, 237, 231))
    draw = ImageDraw.Draw(sheet)
    try:
        title_font = ImageFont.truetype("arial.ttf", 42)
        label_font = ImageFont.truetype("arial.ttf", 28)
    except OSError:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
    draw.text((pad, 28), "Panel 5 logo placement contact sheet (Score2000 0..2000)", fill=(32, 33, 36), font=title_font)

    for idx, thumb in enumerate(thumbs):
        col = idx % 2
        row = idx // 2
        x = pad + col * (card_w + pad)
        y = title_h + pad + row * (card_h + pad)
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=10, fill=(255, 255, 255), outline=(210, 205, 196), width=2)
        tx = x + (card_w - thumb.width) // 2
        ty = y + 28
        sheet.paste(thumb, (tx, ty))
        label = f"Option {idx + 1}"
        draw.text((x + 26, y + card_h - 48), label, fill=(95, 99, 104), font=label_font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def svg_bottom_logo_overlay(series: list[Series], bar_slots: list[BarSlot]) -> str:
    validate_series_matches_bars(series, bar_slots)
    series_by_reader_label = {csv_reader_label(item): item for item in series}
    order = "|".join(series_by_reader_label[slot.reader_label].key for slot in bar_slots)
    parts = [
        (
            f'<g id="panel-5-4-bottom-logos" data-panel-variant="5.4" '
            f'data-logo-layout="bottom-under-labels" data-logo-center-y="{BOTTOM_LOGO_CENTER_Y:.1f}" '
            f'data-logo-binding-key="reader_label" data-bar-slot-source="data-score1000-bar" '
            f'data-series-order="{html.escape(order, quote=True)}">'
        )
    ]
    for i, slot in enumerate(bar_slots):
        item = series_by_reader_label[slot.reader_label]
        logo_size = bottom_logo_size(item)
        x = slot.center_x - logo_size / 2
        y = BOTTOM_LOGO_CENTER_Y - logo_size / 2
        reader_label = html.escape(slot.reader_label, quote=True)
        display_label = html.escape(item.label, quote=True)
        key = html.escape(item.key, quote=True)
        score = f"{item.score:.6f}".rstrip("0").rstrip(".")
        source_logo = html.escape(item.logo, quote=True)
        parts.append(
            (
                f'<image class="score1000-bottom-logo" data-reader-label="{reader_label}" '
                f'data-reader-display-label="{display_label}" data-reader-key="{key}" '
                f'data-bound-bar-label="{reader_label}" data-score2000-value="{score}" '
                f'data-series-index="{i}" data-source-logo="{source_logo}" '
                f'x="{x:.1f}" y="{y:.1f}" width="{logo_size}" height="{logo_size}" '
                f'preserveAspectRatio="xMidYMid meet" href="{panel_svg.asset_data_uri(LOGO_DIR / item.logo)}" />'
            )
        )
    parts.append("</g>")
    return "\n".join(parts)


def csv_reader_label(item: Series) -> str:
    return "Human Expert Baseline" if item.is_human else item.key


def series_metadata(series: list[Series]) -> list[dict[str, object]]:
    return [
        {
            "reader_label": csv_reader_label(item),
            "key": item.key,
            "label": item.label,
            "score2000": item.score,
            "logo": item.logo,
            "color": item.color,
            "is_human": item.is_human,
        }
        for item in series
    ]


def bar_slot_metadata(bar_slots: list[BarSlot]) -> list[dict[str, object]]:
    return [
        {
            "reader_label": slot.reader_label,
            "reader_key": slot.reader_key,
            "score2000": slot.score,
            "center_x": slot.center_x,
            "x": slot.x,
            "y": slot.y,
            "width": slot.width,
            "height": slot.height,
            "color": slot.color,
        }
        for slot in bar_slots
    ]


def update_promoted_svg_metadata(svg: str, series: list[Series], bar_slots: list[BarSlot]) -> str:
    validate_series_matches_bars(series, bar_slots)
    metadata_match = re.search(r'<metadata id="radle-panel-data">(.*?)</metadata>', svg, flags=re.DOTALL)
    if metadata_match is None:
        raise ValueError("Promoted Panel 5.4 source SVG is missing radle-panel-data metadata")
    payload = json.loads(html.unescape(metadata_match.group(1)))
    payload["variant"] = PROMOTED_54_TITLE
    payload["promoted_panel_variant"] = "5.4"
    payload["display_score_column"] = "score2000"
    payload["logo_binding_key"] = "reader_label"
    payload["bar_slot_source"] = "data-score1000-bar"
    payload["logo_layout"] = "bottom-under-labels"
    payload["promotion_series_order"] = [item.key for item in series]
    payload["promotion_series"] = series_metadata(series)
    payload["promotion_bar_slots"] = bar_slot_metadata(bar_slots)
    chart_meta = payload.get("score1000_bar_chart")
    if isinstance(chart_meta, dict):
        chart_meta["promoted_panel_variant"] = "5.4"
        chart_meta["logo_binding_key"] = "reader_label"
        chart_meta["bar_slot_source"] = "data-score1000-bar"
        chart_meta["logo_layout"] = "bottom-under-labels"
        chart_meta["bottom_logo_center_y"] = BOTTOM_LOGO_CENTER_Y
        chart_meta["bottom_logo_series_order"] = [item.key for item in series]
        chart_meta["bottom_logo_series"] = series_metadata(series)
        chart_meta["bottom_logo_bar_slots"] = bar_slot_metadata(bar_slots)
    encoded_payload = html.escape(json.dumps(payload, sort_keys=True), quote=True)
    svg = (
        svg[: metadata_match.start(1)]
        + encoded_payload
        + svg[metadata_match.end(1) :]
    )
    svg = re.sub(
        r"<title>.*?</title>",
        f"<title>{html.escape(PROMOTED_54_TITLE)}</title>",
        svg,
        count=1,
        flags=re.DOTALL,
    )
    return re.sub(
        r"<desc>.*?</desc>",
        (
            "<desc>"
            "Panel 5.4 bottom-logo closed/API-model vertical bar chart using the shifted Score2000 display scale with an A1 kink after 1000; "
            "logos sit under the x-axis names and are bound to the matching SVG bars."
            "</desc>"
        ),
        svg,
        count=1,
        flags=re.DOTALL,
    )


def write_promoted_54_svg(source_svg_path: Path, svg_path: Path, series: list[Series], bar_slots: list[BarSlot]) -> None:
    svg = source_svg_path.read_text(encoding="utf-8")
    svg = update_promoted_svg_metadata(svg, series, bar_slots)
    write_text(svg_path, svg.replace("</svg>", svg_bottom_logo_overlay(series, bar_slots) + "\n</svg>"))


def promote_option_4_to_panel_54(
    option4_path: Path,
    source_svg_path: Path,
    target_dir: Path,
    series: list[Series],
    bar_slots: list[BarSlot],
) -> dict[str, object]:
    target_dir.mkdir(parents=True, exist_ok=True)
    promoted_png = target_dir / f"{PROMOTED_54_BASENAME}.png"
    promoted_svg = target_dir / f"{PROMOTED_54_BASENAME}.svg"
    write_promoted_54_svg(source_svg_path, promoted_svg, series, bar_slots)
    render_svg_to_png(promoted_svg, promoted_png)
    return {
        "panel_variant": "5.4",
        "source_option": 4,
        "source_option_file": str(option4_path.relative_to(REPO_ROOT)),
        "source_svg_file": str(source_svg_path.relative_to(REPO_ROOT)),
        "series": [
            {
                "key": item.key,
                "label": item.label,
                "score2000": item.score,
                "logo": item.logo,
                "color": item.color,
                "is_human": item.is_human,
            }
            for item in series
        ],
        "bar_slots": bar_slot_metadata(bar_slots),
        "png": {
            "file": str(promoted_png.relative_to(REPO_ROOT)),
            "sha256": sha256_file(promoted_png),
            "bytes": promoted_png.stat().st_size,
        },
        "svg": {
            "file": str(promoted_svg.relative_to(REPO_ROOT)),
            "sha256": sha256_file(promoted_svg),
            "bytes": promoted_svg.stat().st_size,
        },
    }


def append_promoted_54_to_contact_sheet(target_dir: Path) -> None:
    contact_sheet = target_dir / "contact_sheet.html"
    if not contact_sheet.exists():
        raise FileNotFoundError(f"Cannot register promoted Panel 5.4; contact sheet is missing: {contact_sheet}")
    svg_path = target_dir / f"{PROMOTED_54_BASENAME}.svg"
    svg = svg_path.read_text(encoding="utf-8")
    start = "<!-- promoted-panel-5-4-start -->"
    end = "<!-- promoted-panel-5-4-end -->"
    doc = contact_sheet.read_text(encoding="utf-8")
    doc = re.sub(
        rf"\n?{re.escape(start)}.*?{re.escape(end)}\n?",
        "\n",
        doc,
        flags=re.DOTALL,
    )
    card = (
        f"\n{start}\n"
        f'<figure data-panel-id="5.4" data-panel-file="{PROMOTED_54_BASENAME}.svg">'
        f"{svg}<figcaption>{html.escape(PROMOTED_54_CAPTION)}</figcaption></figure>\n"
        f"{end}\n"
    )
    if "</body>" not in doc:
        raise ValueError(f"Cannot append promoted Panel 5.4; contact sheet has no </body>: {contact_sheet}")
    write_text(contact_sheet, doc.replace("</body>", card + "</body>", 1))


def replace_marked_block(text: str, start: str, end: str, block: str, anchor: str | None = None) -> str:
    text = re.sub(
        rf"\n?{re.escape(start)}.*?{re.escape(end)}\n?",
        "\n",
        text,
        flags=re.DOTALL,
    )
    if anchor and anchor in text:
        return text.replace(anchor, block + "\n" + anchor, 1)
    return text.rstrip() + "\n\n" + block


def update_promoted_54_support_files(
    target_dir: Path,
    promoted_variant: dict[str, object],
    series: list[Series],
) -> None:
    start = "<!-- promoted-panel-5-4-support-start -->"
    end = "<!-- promoted-panel-5-4-support-end -->"
    order_text = ", ".join(item.label for item in series)

    captions_path = target_dir / "captions.md"
    captions = captions_path.read_text(encoding="utf-8")
    captions_block = "\n".join(
        [
            start,
            "## Panel 5.4. Confidence-weighted diagnosis correctness with bottom logos",
            (
                "A bottom-logo closed/API-model companion shows the pooled human baseline plus all closed/API models "
                f"({order_text}) on the shifted confidence-weighted diagnosis score axis with an A1 kink after 1000. Logos sit under the x-axis names, "
                "are generated as vector SVG overlay content, and are bound to bars by stable `reader_label`."
            ),
            "",
            end,
            "",
        ]
    )
    write_text(captions_path, replace_marked_block(captions, start, end, captions_block, "Source master SHA256"))

    data_md_path = target_dir / "data_provenance.md"
    data_md = data_md_path.read_text(encoding="utf-8")
    data_block = "\n".join(
        [
            start,
            (
                "- Variant `5.4` is the promoted bottom-logo closed/API-model confidence-weighted diagnosis panel. It uses the same shifted "
                f"0 to 2000 display scale, A1 kink after 1000, and closed/API CSV rank order as the vertical bar chart ({order_text}), "
                "and is emitted as inspectable SVG with separate bar, tick, and bottom-logo elements. "
                "Logos are placed under the x-axis names by matching each SVG bar's stable `reader_label` to the explicit logo catalog."
            ),
            end,
        ]
    )
    write_text(data_md_path, replace_marked_block(data_md, start, end, data_block, "- Variant `5.5`"))

    checklist_path = target_dir / "reviewer_checklist.md"
    checklist = checklist_path.read_text(encoding="utf-8")
    checklist_block = "\n".join(
        [
            start,
            "- [ ] Variant 5.4 uses the pooled human baseline plus all closed/API-model confidence-weighted score data, A1 kinked y-axis after 1000, and places each logo under the x-axis name for its SVG bar by stable `reader_label`.",
            "- [ ] Variant 5.4 is present in the main contact sheet, manifest, audit report, and rendered QA outputs as inspectable SVG rather than a PNG wrapper.",
            end,
        ]
    )
    write_text(
        checklist_path,
        replace_marked_block(checklist, start, end, checklist_block, "- [ ] Variant 5.5"),
    )

    data_json_path = target_dir / "data_provenance.json"
    data_json = json.loads(data_json_path.read_text(encoding="utf-8"))
    panels = list(data_json.get("panels", []))
    promoted_svg = f"{PROMOTED_54_BASENAME}.svg"
    if promoted_svg not in panels:
        panels.append(promoted_svg)
    data_json["panels"] = panels
    data_json.pop("promoted_panel_5_4", None)
    data_json["promoted_variant_5_4"] = {
        "panel_id": "5.4",
        "file": promoted_svg,
        "variant": PROMOTED_54_TITLE,
        "caption": PROMOTED_54_CAPTION,
        "display_score_column": "score2000",
        "logo_binding_key": "reader_label",
        "bar_slot_source": "data-score1000-bar",
        "logo_layout": "bottom-under-labels",
        "bottom_logo_center_y": BOTTOM_LOGO_CENTER_Y,
        "score_y_min": Y_MIN,
        "score_y_max": Y_MAX,
        "score_ticks": Y_TICKS,
        "score_axis_break_after": AXIS_BREAK_AFTER,
        "score_axis_break_style": AXIS_BREAK_STYLE,
        "score_axis_break_top_fraction": AXIS_BREAK_TOP_FRACTION,
        "reader_keys": [item.key for item in series],
        "selected_reader_labels": [csv_reader_label(item) for item in series],
        "source_option_file": promoted_variant["source_option_file"],
        "source_svg_file": promoted_variant["source_svg_file"],
        "series": promoted_variant["series"],
        "bar_slots": promoted_variant["bar_slots"],
    }
    data_json["updated_at"] = utc_now()
    write_text(data_json_path, json.dumps(data_json, indent=2) + "\n")


def manifest_file_entry(path: Path) -> dict[str, object]:
    entry: dict[str, object] = {
        "path": str(path.resolve().relative_to(REPO_ROOT)),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }
    if path.suffix.lower() == ".csv":
        entry["rows"] = max(0, sum(1 for _ in path.open("r", encoding="utf-8")) - 1)
    return entry


def update_main_figure_manifest(target_dir: Path, promoted_variant: dict[str, object], series: list[Series]) -> None:
    manifest_path = target_dir / "figure_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Cannot register promoted Panel 5.4; manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    svg_name = f"{PROMOTED_54_BASENAME}.svg"
    png_name = f"{PROMOTED_54_BASENAME}.png"
    promoted_panel = {
        "panel_id": "5.4",
        "file": svg_name,
        "variant": PROMOTED_54_TITLE,
        "layout": "score1000_bar_chart_bottom_logos",
        "palette_key": "option_c_teal_green_to_current_red",
        "selected_reader_labels": [csv_reader_label(item) for item in series],
        "reader_keys": [item.key for item in series],
        "score_y_min": Y_MIN,
        "score_y_max": Y_MAX,
        "score_ticks": Y_TICKS,
        "score_axis_break_after": AXIS_BREAK_AFTER,
        "score_axis_break_style": AXIS_BREAK_STYLE,
        "score_axis_break_top_fraction": AXIS_BREAK_TOP_FRACTION,
        "display_score_column": "score2000",
        "logo_binding_key": "reader_label",
        "bar_slot_source": "data-score1000-bar",
        "logo_layout": "bottom-under-labels",
        "bottom_logo_center_y": BOTTOM_LOGO_CENTER_Y,
        "score2000_rule": panel_svg.score2000_rule_metadata(),
        "source_svg": promoted_variant["source_svg_file"],
        "source_option_file": promoted_variant["source_option_file"],
        "series": promoted_variant["series"],
        "bar_slots": promoted_variant["bar_slots"],
    }
    manifest["panels"] = [
        panel
        for panel in manifest.get("panels", [])
        if not (isinstance(panel, dict) and panel.get("file") == svg_name)
    ]
    manifest["panels"].append(promoted_panel)
    manifest_file_names = (
        svg_name,
        png_name,
        "contact_sheet.html",
        "captions.md",
        "data_provenance.md",
        "data_provenance.json",
        "reviewer_checklist.md",
    )
    promoted_paths = {str((target_dir / name).resolve().relative_to(REPO_ROOT)) for name in manifest_file_names}
    manifest["files"] = [
        entry
        for entry in manifest.get("files", [])
        if not (isinstance(entry, dict) and str(entry.get("path")) in promoted_paths)
    ]
    manifest["files"].extend(manifest_file_entry(target_dir / name) for name in manifest_file_names)
    manifest["promoted_panel_generator"] = str(Path(__file__).relative_to(REPO_ROOT))
    manifest["updated_at"] = utc_now()
    write_text(manifest_path, json.dumps(manifest, indent=2) + "\n")


def main() -> None:
    args = parse_args()
    configure_idk_score(args.idk_score)
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    source_panel_dir = args.source_panel_dir.resolve()
    if args.panel:
        panel = args.panel.resolve()
        source_svg_path = panel.with_suffix(".svg")
        if not source_svg_path.exists():
            raise FileNotFoundError(f"Promoted Panel 5.4 needs a source SVG beside the base PNG: {source_svg_path}")
    else:
        source_svg_path, panel = build_ymax100_base_panel(source_panel_dir, out_dir)
    bar_slots = read_source_bar_slots(source_svg_path)
    series = load_series(source_panel_dir, bar_slots)
    validate_series_matches_bars(series, bar_slots)

    base = Image.open(panel).convert("RGBA")
    if base.size != (W, H):
        raise ValueError(f"Expected panel size {(W, H)}, got {base.size}: {panel}")

    for filename in DISCARDED_OPTION_FILES:
        stale = out_dir / filename
        if stale.exists():
            stale.unlink()

    option_paths: list[Path] = []
    for filename, renderer in OPTIONS:
        out_path = out_dir / filename
        renderer(base, series).convert("RGB").save(out_path)
        option_paths.append(out_path)

    contact_sheet = out_dir / "panel_2_score1000_5_logo_placement_contact_sheet.png"
    make_contact_sheet(option_paths, contact_sheet)
    promoted_variant = promote_option_4_to_panel_54(option_paths[3], source_svg_path, source_panel_dir, series, bar_slots)
    append_promoted_54_to_contact_sheet(source_panel_dir)
    update_promoted_54_support_files(source_panel_dir, promoted_variant, series)
    update_main_figure_manifest(source_panel_dir, promoted_variant, series)

    manifest = {
        "generated_at": utc_now(),
        "generator": str(Path(__file__).relative_to(REPO_ROOT)),
        "source_panel": str(panel.relative_to(REPO_ROOT)),
        "source_svg": str(source_svg_path.relative_to(REPO_ROOT)),
        "source_panel_sha256": sha256_file(panel),
        "source_svg_sha256": sha256_file(source_svg_path),
        "score_y_min": Y_MIN,
        "score_y_max": Y_MAX,
        "score_ticks": Y_TICKS,
        "score_axis_break_after": AXIS_BREAK_AFTER,
        "score_axis_break_style": AXIS_BREAK_STYLE,
        "score_axis_break_top_fraction": AXIS_BREAK_TOP_FRACTION,
        "display_score_column": "score2000",
        "baseline": SCORE2000_BASELINE,
        "bar_origin": Y_MIN,
        "reference_line": SCORE2000_BASELINE,
        "logo_layout": "bottom-under-labels",
        "bottom_logo_center_y": BOTTOM_LOGO_CENTER_Y,
        "score2000_rule": panel_svg.score2000_rule_metadata(),
        "idk_score": IDK_SCORE,
        "all_idk_baseline": IDK_SCORE * 200,
        "series": series_metadata(series),
        "bar_slots": bar_slot_metadata(bar_slots),
        "logo_dir": str(LOGO_DIR.relative_to(REPO_ROOT)),
        "options": [
            {
                "option": i + 1,
                "file": str(path.relative_to(REPO_ROOT)),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for i, path in enumerate(option_paths)
        ],
        "contact_sheet": {
            "file": str(contact_sheet.relative_to(REPO_ROOT)),
            "sha256": sha256_file(contact_sheet),
            "bytes": contact_sheet.stat().st_size,
        },
        "promoted_variant": promoted_variant,
    }
    (out_dir / "panel_2_score1000_5_logo_placement_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[PASS] wrote {contact_sheet}")
    for path in option_paths:
        print(f"[PASS] wrote {path}")
    print(f"[PASS] promoted option 4 to {promoted_variant['png']['file']}")


if __name__ == "__main__":
    main()
