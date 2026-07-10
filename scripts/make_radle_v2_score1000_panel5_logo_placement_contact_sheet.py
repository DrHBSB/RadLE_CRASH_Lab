#!/usr/bin/env python3
"""Prototype logo-placement options for the Score2000 Panel 5 PNG."""

from __future__ import annotations

import argparse
import base64
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

from PIL import Image, ImageDraw, ImageFont

import make_radle_v2_score1000_panel23_svg as panel_svg
from make_radle_v2_score1000_panel23_svg import read_csv, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PANEL = (
    REPO_ROOT
    / "outputs"
    / "radle_v2_stats"
    / "final_scoring_radiologist_20260706_001147"
    / "likert5_score1000"
    / "handwritten_panels_model_group_color_final"
    / "panel_2_score1000_5_0_clean_score1000_bar_chart.png"
)
DEFAULT_OUT_DIR = DEFAULT_PANEL.parent / "panel5_logo_placement_options"
DEFAULT_SOURCE_PANEL_DIR = DEFAULT_PANEL.parent
LOGO_DIR = REPO_ROOT / "scripts" / "assets" / "radle_score1000_logos"
BASE_YTOP140_SVG = "panel_2_score1000_5_0_clean_score1000_bar_chart_ytop140_tick100.svg"
BASE_YTOP140_PNG = "panel_2_score1000_5_0_clean_score1000_bar_chart_ytop140_tick100.png"
PROMOTED_54_BASENAME = "panel_2_score1000_5_4_icon_ribbon_score1000_bar_chart"
PROMOTED_54_TITLE = "Panel 5.4 icon ribbon Score2000 bar chart"

W, H = 3600, 2840
CHART_X = 360.0
CHART_Y = 610.0
CHART_W = 3080.0
CHART_H = 1540.0
BAR_W = 230.0
SCORE2000_SHIFT = 1000.0
SCORE2000_BASELINE = 1000.0
Y_MIN = 0.0
Y_MAX = 2000.0
Y_TICKS = [0, 500, 1000, 1500, 2000]
LOGO_SCALE = 1.5
ZERO_Y = CHART_Y + ((Y_MAX - SCORE2000_BASELINE) / (Y_MAX - Y_MIN)) * CHART_H
CHART_BOTTOM = CHART_Y + CHART_H
SLOT_W = CHART_W / 6
PANEL_TITLE = "Diagnostic outcomes stratified by confidence"
FIGURE_TITLE_Y = 166.0
FIGURE_TITLE_FONT_PX = 90
PANEL_TITLE_Y = 394.0
PANEL_TITLE_FONT_PX = 80
SCORE_VALUE_FONT_PX = 57
SCORE_TICK_FONT_PX = 45
FOOTER_DIVIDER_Y = 2500.0
FOOTER_X = CHART_X
FOOTER_RIGHT_X = CHART_X + CHART_W
FOOTER_FIRST_LINE_Y = 2600.0
FOOTER_LINE_STEP = 66.0
FOOTER_FONT_PX = 55
IDK_SCORE = 1


def footer_lines_for_idk_score(idk_score: int) -> list[str]:
    all_idk_score1000 = 200 * idk_score
    all_idk_score2000 = all_idk_score1000 + int(SCORE2000_SHIFT)
    return [
        "Score2000 (left of each reader/model): Score2000 = Score1000 + 1000 on a shifted 0..2000 display scale.",
        (
            "Correct reads earn +1 to +5; wrong reads lose -1 to -5; \"I don't know\" earns +1; blank/failed answers score 0."
            if idk_score == 1
            else "Correct reads earn +1 to +5; wrong reads lose -1 to -5; \"I don't know\" earns 0; blank/failed answers score 0."
        ),
        (
            f"Over 200 cases Score1000 runs -1000 to +1000; all-IDK lands at Score1000 +{all_idk_score1000} and Score2000 {all_idk_score2000}."
            if idk_score == 1
            else f"Over 200 cases Score1000 runs -1000 to +1000; all-IDK lands at Score1000 0 and Score2000 {all_idk_score2000}."
        ),
    ]


FOOTER_LINES = footer_lines_for_idk_score(IDK_SCORE)
OPTION4_REDUCED_KEYS = {"grok_4_3", "claude_fable_5", "gemini_3_1_pro", "gpt_5_5"}
OPTION4_GUIDE_DROP_PX = 48


@dataclass(frozen=True)
class Series:
    key: str
    label: str
    score: float
    logo: str
    color: str
    is_human: bool = False


SERIES = [
    Series("human_baseline", "Human baseline", 1018.5, "board_certified_radiologists_logo.png", "#131e35", True),
    Series("grok_4_3", "Grok 4.3", 763.0, "grok_4_3_logo.png", "#313131"),
    Series("claude_fable_5", "Claude Fable 5", 758.0, "claude_fable_5_logo.png", "#D97757"),
    Series("gemini_3_1_pro", "Gemini 3.1 Pro", 660.0, "gemini_3_1_pro_logo.png", "#4796E3"),
    Series("gpt_5_5", "GPT-5.5", 651.0, "gpt_5_5_logo.png", "#74AA9C"),
    Series("octomed_7b", "OctoMed 7B", 627.0, "octomed_7b_logo.png", "#F27B73"),
]


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
    return CHART_Y + ((Y_MAX - score) / (Y_MAX - Y_MIN)) * CHART_H


def row_geometry(index: int, score: float) -> dict[str, float]:
    bar_x = CHART_X + index * SLOT_W + (SLOT_W - BAR_W) / 2
    sy = score_y(score)
    bar_y = min(sy, ZERO_Y)
    bar_h = abs(sy - ZERO_Y)
    return {
        "bar_x": bar_x,
        "bar_y": bar_y,
        "bar_h": bar_h,
        "center_x": bar_x + BAR_W / 2,
        "value_y": bar_y - 22 if score >= SCORE2000_BASELINE else bar_y + bar_h + 46,
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
        r"(\.score1000-bar-value \{[^}]*font-size: )38px;": rf"\g<1>{SCORE_VALUE_FONT_PX}px;",
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


def build_ymax100_base_panel(source_panel_dir: Path, out_dir: Path) -> Path:
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
        variant_label="5.0 clean Score2000 vertical bar chart",
        y_min=Y_MIN,
        y_max=Y_MAX,
        ticks=Y_TICKS,
        include_model_icons=False,
        bar_colors=panel_svg.SCORE1000_BAR_COLORS_WARM_REFRESH,
        panel_title=PANEL_TITLE,
        chart_y=CHART_Y,
        footer_note="",
    )
    svg = append_345_footer(apply_svg_layout_overrides(strip_score1000_axis_note(svg)))
    write_text(svg_path, svg)
    render_svg_to_png(svg_path, png_path)
    return png_path


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


def option_previous_style(base: Image.Image) -> Image.Image:
    canvas = base.copy().convert("RGBA")
    for i, item in enumerate(SERIES):
        geom = row_geometry(i, item.score)
        raw_size = 118 if item.is_human else 112
        logo_size = scaled_logo_size(raw_size)
        if item.is_human:
            plate = "none"
            halo = False
        else:
            plate = "none"
            halo = True
        if item.score >= SCORE2000_BASELINE:
            # Keep one visible air gap above bars at or above the shifted baseline.
            cy = max(350 + logo_size / 2, geom["bar_y"] - 105 - logo_size / 2)
        else:
            # Keep one visible air gap below each bar below the shifted baseline.
            bar_end_y = geom["bar_y"] + geom["bar_h"]
            cy = min(CHART_BOTTOM - logo_size / 2 - 42, bar_end_y + 92 + logo_size / 2)
        draw_logo(canvas, item, geom["center_x"], cy, logo_size=logo_size, backplate=plate, halo=halo)
    return canvas


def option_uniform_badges(base: Image.Image) -> Image.Image:
    canvas = base.copy().convert("RGBA")
    for i, item in enumerate(SERIES):
        geom = row_geometry(i, item.score)
        if item.is_human:
            cy = max(350, geom["bar_y"] - 210)
            draw_logo(canvas, item, geom["center_x"], cy, logo_size=scaled_logo_size(138), backplate="none", halo=False)
        else:
            cy = geom["bar_y"] - 166
            raw_size = 116 if item.key == "octomed_7b" else 104
            draw_logo(canvas, item, geom["center_x"], cy, logo_size=scaled_logo_size(raw_size), backplate="none", halo=False)
    return canvas


def option_baseline_row(base: Image.Image) -> Image.Image:
    canvas = base.copy().convert("RGBA")
    for i, item in enumerate(SERIES):
        geom = row_geometry(i, item.score)
        if item.is_human:
            draw_logo(canvas, item, geom["center_x"], ZERO_Y + 126, logo_size=scaled_logo_size(148), backplate="none", halo=False)
        else:
            draw_logo(canvas, item, geom["center_x"], ZERO_Y + 126, logo_size=scaled_logo_size(92), backplate="circle")
    return canvas


def option_top_ribbon(base: Image.Image) -> Image.Image:
    canvas = base.copy().convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")
    ribbon_top = 530
    ribbon_bottom = 760
    ribbon_center = (ribbon_top + ribbon_bottom) / 2
    draw.rounded_rectangle((430, ribbon_top, 3370, ribbon_bottom), radius=30, fill=(255, 255, 255, 238), outline=(176, 190, 197, 255), width=3)
    for i, item in enumerate(SERIES):
        geom = row_geometry(i, item.score)
        raw_size = 107 if item.key in OPTION4_REDUCED_KEYS else 133
        draw_logo(canvas, item, geom["center_x"], ribbon_center, logo_size=scaled_logo_size(raw_size), backplate="none", halo=False)
        draw.line((geom["center_x"], ribbon_bottom - 1, geom["center_x"], ribbon_bottom + OPTION4_GUIDE_DROP_PX), fill=hex_to_rgba(item.color, 165), width=4)
    return canvas


def option_human_vs_model_split(base: Image.Image) -> Image.Image:
    canvas = base.copy().convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")
    model_badge_top = CHART_BOTTOM + 142
    model_badge_bottom = CHART_BOTTOM + 294
    model_badge_center = (model_badge_top + model_badge_bottom) / 2
    for i, item in enumerate(SERIES):
        geom = row_geometry(i, item.score)
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
    ("panel_2_score1000_5_logo_option_4_top_ribbon.png", option_top_ribbon),
]

DISCARDED_OPTION_FILES = [
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


def write_png_wrapper_svg(png_path: Path, svg_path: Path, title: str) -> None:
    data_uri = "data:image/png;base64," + base64.b64encode(png_path.read_bytes()).decode("ascii")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <title>{html.escape(title)}</title>
  <image href="{data_uri}" x="0" y="0" width="{W}" height="{H}" preserveAspectRatio="xMidYMid meet"/>
</svg>
"""
    write_text(svg_path, svg)


def promote_option_4_to_panel_54(option4_path: Path, target_dir: Path) -> dict[str, object]:
    target_dir.mkdir(parents=True, exist_ok=True)
    promoted_png = target_dir / f"{PROMOTED_54_BASENAME}.png"
    promoted_svg = target_dir / f"{PROMOTED_54_BASENAME}.svg"
    Image.open(option4_path).convert("RGB").save(promoted_png)
    write_png_wrapper_svg(promoted_png, promoted_svg, PROMOTED_54_TITLE)
    return {
        "panel_variant": "5.4",
        "source_option": 4,
        "source_option_file": str(option4_path.relative_to(REPO_ROOT)),
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


def main() -> None:
    args = parse_args()
    configure_idk_score(args.idk_score)
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    panel = args.panel.resolve() if args.panel else build_ymax100_base_panel(args.source_panel_dir, out_dir)

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
        renderer(base).convert("RGB").save(out_path)
        option_paths.append(out_path)

    contact_sheet = out_dir / "panel_2_score1000_5_logo_placement_contact_sheet.png"
    make_contact_sheet(option_paths, contact_sheet)
    promoted_variant = promote_option_4_to_panel_54(option_paths[3], args.source_panel_dir.resolve())

    manifest = {
        "generated_at": utc_now(),
        "generator": str(Path(__file__).relative_to(REPO_ROOT)),
        "source_panel": str(panel.relative_to(REPO_ROOT)),
        "source_panel_sha256": sha256_file(panel),
        "score_y_min": Y_MIN,
        "score_y_max": Y_MAX,
        "score_ticks": Y_TICKS,
        "display_score_column": "score2000",
        "baseline": SCORE2000_BASELINE,
        "score2000_rule": panel_svg.score2000_rule_metadata(),
        "idk_score": IDK_SCORE,
        "all_idk_baseline": IDK_SCORE * 200,
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
