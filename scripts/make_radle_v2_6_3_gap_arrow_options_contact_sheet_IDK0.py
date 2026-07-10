#!/usr/bin/env python3
"""Generate Panel 6.3 gap-arrow option sheet for the IDK0 lane."""

from __future__ import annotations

import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]
PANEL_DIR = (
    REPO_ROOT
    / "outputs"
    / "radle_v2_stats"
    / "final_scoring_radiologist_20260708_161500_IDK0"
    / "likert5_score1000_IDK0"
    / "handwritten_panels_model_group_color_final_IDK0"
)
SOURCE_SVG = PANEL_DIR / "panel_2_score1000_6_3_closed_open_through_medgemma_score1000_bar_chart.svg"
SOURCE_PNG = PANEL_DIR / "panel_2_score1000_6_3_closed_open_through_medgemma_score1000_bar_chart.png"
SVG_NS = "http://www.w3.org/2000/svg"
NS = f"{{{SVG_NS}}}"
BLUE = "#2f55e7"
INK = "#131e35"
MUTED = "#536170"
HUMAN_LINE = "#1b324d"
TOP_AI_LINE = "#d97757"
PAPER = "#ffffff"
CARD_BORDER = "#d7e0e7"
DIAGONAL_ARM_RATIO = float(os.environ.get("RADLE_GAP_ARROW_DIAGONAL_RATIO", "0.12"))
DIAGONAL_RATIO_LABEL = f"{DIAGONAL_ARM_RATIO:.0%}"
DIAGONAL_RATIO_SLUG = f"diag{int(round(DIAGONAL_ARM_RATIO * 100))}"
OUT_DIR = PANEL_DIR / f"gap_arrow_{DIAGONAL_RATIO_SLUG}_IDK0"
CONTACT_SHEET = OUT_DIR / f"panel_6_3_gap_arrow_{DIAGONAL_RATIO_SLUG}_contact_sheet.png"
MANIFEST = OUT_DIR / f"panel_6_3_gap_arrow_{DIAGONAL_RATIO_SLUG}_manifest.json"
DIAGONAL_ARM_45_PROJECTION = 0.7071067811865476


@dataclass(frozen=True)
class Option:
    key: str
    title: str
    subtitle: str
    style: str


OPTIONS = [
    Option(
        "A",
        f"Slim Diagonal {DIAGONAL_RATIO_LABEL}",
        f"Continuous thin shaft; each chevron arm is {DIAGONAL_RATIO_LABEL} of arrow height",
        "slim_long",
    ),
    Option(
        "B",
        f"Split Diagonal {DIAGONAL_RATIO_LABEL}",
        f"B/E hybrid: center pause; each chevron arm is {DIAGONAL_RATIO_LABEL} of arrow height",
        "split_long",
    ),
    Option(
        "C",
        f"Airy Diagonal {DIAGONAL_RATIO_LABEL}",
        f"Hairline shaft with the lightest {DIAGONAL_RATIO_LABEL} diagonal-arm treatment",
        "airy_long",
    ),
    Option(
        "D",
        f"Firm Diagonal {DIAGONAL_RATIO_LABEL}",
        f"Continuous shaft with a slightly firmer {DIAGONAL_RATIO_LABEL} arm treatment",
        "taut_wide",
    ),
    Option(
        "E",
        f"Split Firm {DIAGONAL_RATIO_LABEL}",
        f"The strongest B/E version with {DIAGONAL_RATIO_LABEL} diagonal arms",
        "wide_split",
    ),
    Option(
        "F",
        f"Balanced Diagonal {DIAGONAL_RATIO_LABEL}",
        f"Sleek default candidate with compact {DIAGONAL_RATIO_LABEL} diagonal arms",
        "balanced_long",
    ),
]


LONG_FLAG_STYLES: dict[str, dict[str, float | bool]] = {
    "slim_long": {
        "shaft_width": 8.0,
        "head_len_ratio": DIAGONAL_ARM_RATIO,
        "opacity": 0.94,
        "shaft_pad": 10.0,
        "split": False,
    },
    "split_long": {
        "shaft_width": 8.0,
        "head_len_ratio": DIAGONAL_ARM_RATIO,
        "opacity": 0.94,
        "shaft_pad": 10.0,
        "split": True,
        "gap": 34.0,
    },
    "airy_long": {
        "shaft_width": 6.0,
        "head_len_ratio": DIAGONAL_ARM_RATIO,
        "opacity": 0.82,
        "shaft_pad": 12.0,
        "split": False,
    },
    "taut_wide": {
        "shaft_width": 9.0,
        "head_len_ratio": DIAGONAL_ARM_RATIO,
        "opacity": 0.91,
        "shaft_pad": 9.0,
        "split": False,
    },
    "wide_split": {
        "shaft_width": 9.0,
        "head_len_ratio": DIAGONAL_ARM_RATIO,
        "opacity": 0.92,
        "shaft_pad": 10.0,
        "split": True,
        "gap": 38.0,
    },
    "balanced_long": {
        "shaft_width": 8.0,
        "head_len_ratio": DIAGONAL_ARM_RATIO,
        "opacity": 0.94,
        "shaft_pad": 10.0,
        "split": False,
    },
}


def diagonal_arm_projection(arrow_height: float, cfg: dict[str, float | bool]) -> tuple[float, float]:
    arm_len = arrow_height * float(cfg["head_len_ratio"])
    projected = arm_len * DIAGONAL_ARM_45_PROJECTION
    return projected, projected


def svg_elem(tag: str, attrs: dict[str, object]) -> ET.Element:
    elem = ET.Element(f"{NS}{tag}")
    for key, value in attrs.items():
        elem.set(key, str(value))
    return elem


def line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    width: float,
    color: str = BLUE,
    opacity: float = 0.96,
    kind: str,
) -> ET.Element:
    return svg_elem(
        "line",
        {
            "class": "score1000-gap-arrow",
            "x1": f"{x1:.1f}",
            "y1": f"{y1:.1f}",
            "x2": f"{x2:.1f}",
            "y2": f"{y2:.1f}",
            "data-score-gap-arrow": kind,
            "style": (
                f"stroke:{color};stroke-width:{width:g};stroke-linecap:round;"
                f"stroke-linejoin:round;fill:none;opacity:{opacity:g};"
            ),
        },
    )


def polygon(points: list[tuple[float, float]], *, color: str = BLUE, opacity: float = 0.96, kind: str) -> ET.Element:
    return svg_elem(
        "polygon",
        {
            "class": "score1000-gap-arrow",
            "points": " ".join(f"{x:.1f},{y:.1f}" for x, y in points),
            "data-score-gap-arrow": kind,
            "style": f"fill:{color};stroke:none;opacity:{opacity:g};",
        },
    )


def rect(x: float, y: float, w: float, h: float, *, fill: str, opacity: float, kind: str) -> ET.Element:
    return svg_elem(
        "rect",
        {
            "class": "score1000-gap-arrow",
            "x": f"{x:.1f}",
            "y": f"{y:.1f}",
            "width": f"{w:.1f}",
            "height": f"{h:.1f}",
            "rx": f"{w / 2:.1f}",
            "data-score-gap-arrow": kind,
            "style": f"fill:{fill};stroke:none;opacity:{opacity:g};",
        },
    )


def circle(cx: float, cy: float, r: float, *, fill: str, opacity: float, kind: str) -> ET.Element:
    return svg_elem(
        "circle",
        {
            "class": "score1000-gap-arrow",
            "cx": f"{cx:.1f}",
            "cy": f"{cy:.1f}",
            "r": f"{r:.1f}",
            "data-score-gap-arrow": kind,
            "style": f"fill:{fill};stroke:none;opacity:{opacity:g};",
        },
    )


def arrow_geometry(root: ET.Element) -> tuple[ET.Element, float, float, float]:
    overlay = root.find(f".//{NS}g[@class='score1000-gap-overlay']")
    if overlay is None:
        raise RuntimeError("Missing score1000-gap-overlay group")
    human_line = overlay.find(f"{NS}line[@data-score-gap-line='human']")
    ai_line = overlay.find(f"{NS}line[@data-score-gap-line='top-ai']")
    shaft = overlay.find(f"{NS}line[@data-score-gap-arrow='shaft']")
    if human_line is None or ai_line is None or shaft is None:
        raise RuntimeError("Missing gap overlay geometry anchors")
    human_y = float(human_line.get("y1", "nan"))
    ai_y = float(ai_line.get("y1", "nan"))
    arrow_x = float(shaft.get("x1", "nan"))
    return overlay, arrow_x, min(human_y, ai_y), max(human_y, ai_y)


def remove_current_arrow(overlay: ET.Element) -> int:
    removed = 0
    for elem in list(overlay):
        if elem.get("class") == "score1000-gap-arrow":
            overlay.remove(elem)
            removed += 1
    return removed


def arrow_elements(option: Option, x: float, y_top: float, y_bottom: float) -> list[ET.Element]:
    cfg = LONG_FLAG_STYLES.get(option.style)
    if cfg is None:
        raise ValueError(f"Unsupported option style: {option.style}")
    head_w, head_h = diagonal_arm_projection(y_bottom - y_top, cfg)
    shaft_width = float(cfg["shaft_width"])
    opacity = float(cfg["opacity"])
    shaft_pad = float(cfg["shaft_pad"])
    elems = [
        line(x, y_top, x - head_w, y_top + head_h, width=shaft_width, opacity=opacity, kind="top-head-left"),
        line(x, y_top, x + head_w, y_top + head_h, width=shaft_width, opacity=opacity, kind="top-head-right"),
        line(
            x,
            y_bottom,
            x - head_w,
            y_bottom - head_h,
            width=shaft_width,
            opacity=opacity,
            kind="bottom-head-left",
        ),
        line(
            x,
            y_bottom,
            x + head_w,
            y_bottom - head_h,
            width=shaft_width,
            opacity=opacity,
            kind="bottom-head-right",
        ),
    ]
    if bool(cfg["split"]):
        mid = (y_top + y_bottom) / 2.0
        gap = float(cfg.get("gap", 34.0))
        elems.extend(
            [
                line(x, y_top + shaft_pad, x, mid - gap, width=shaft_width, opacity=opacity, kind="upper-shaft"),
                line(x, mid + gap, x, y_bottom - shaft_pad, width=shaft_width, opacity=opacity, kind="lower-shaft"),
            ]
        )
    else:
        elems.append(
            line(x, y_top + shaft_pad, x, y_bottom - shaft_pad, width=shaft_width, opacity=opacity, kind="shaft")
        )
    return elems


def write_option_svg(option: Option, source_svg: Path, out_svg: Path) -> None:
    if option.style == "current":
        shutil.copyfile(source_svg, out_svg)
        return
    tree = ET.parse(source_svg)
    root = tree.getroot()
    overlay, x, y_top, y_bottom = arrow_geometry(root)
    remove_current_arrow(overlay)
    insert_at = 0
    for idx, child in enumerate(list(overlay)):
        if child.get("data-score-gap-line") in {"human", "top-ai"}:
            insert_at = idx + 1
    for elem in reversed(arrow_elements(option, x, y_top, y_bottom)):
        overlay.insert(insert_at, elem)
    root.set("data-gap-arrow-option", option.key)
    root.set("data-gap-arrow-option-title", option.title)
    ET.register_namespace("", SVG_NS)
    tree.write(out_svg, encoding="utf-8", xml_declaration=False)


def render_svgs(option_svgs: list[Path]) -> list[Path]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("playwright is required to render SVG options") from exc
    pngs: list[Path] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 3600, "height": 2840}, device_scale_factor=1)
            page.set_default_timeout(120000)
            for svg in option_svgs:
                png = svg.with_suffix(".png")
                page.goto(svg.resolve().as_uri(), wait_until="networkidle")
                page.screenshot(path=str(png), full_page=True, timeout=120000)
                pngs.append(png)
        finally:
            browser.close()
    return pngs


def load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_path = REPO_ROOT / "scripts" / "assets" / "fonts" / "Lexend-wght.ttf"
    try:
        return ImageFont.truetype(str(font_path), size=size)
    except OSError:
        return ImageFont.load_default()


def draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    x1: float,
    y: float,
    x2: float,
    *,
    fill: str,
    width: int,
    dash: int = 34,
    gap: int = 30,
) -> None:
    x = x1
    while x < x2:
        draw.line((x, y, min(x + dash, x2), y), fill=fill, width=width)
        x += dash + gap


def draw_text_center(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    *,
    font: ImageFont.ImageFont,
    fill: str = INK,
) -> None:
    try:
        draw.text(xy, text, fill=fill, font=font, anchor="mm")
    except TypeError:
        bbox = draw.textbbox((0, 0), text, font=font)
        draw.text((xy[0] - (bbox[2] - bbox[0]) / 2, xy[1] - (bbox[3] - bbox[1]) / 2), text, fill=fill, font=font)


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[float, float]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_inline_dashed_label(
    draw: ImageDraw.ImageDraw,
    *,
    x1: float,
    x2: float,
    y: float,
    label_x: float,
    label: str,
    line_fill: str,
    font: ImageFont.ImageFont,
    line_width: int = 12,
    label_pad_x: float = 34.0,
) -> None:
    text_w, _ = text_size(draw, label, font)
    gap_left = max(x1, label_x - text_w / 2.0 - label_pad_x)
    gap_right = min(x2, label_x + text_w / 2.0 + label_pad_x)
    if gap_left > x1:
        draw_dashed_line(draw, x1, y, gap_left, fill=line_fill, width=line_width)
    if gap_right < x2:
        draw_dashed_line(draw, gap_right, y, x2, fill=line_fill, width=line_width)
    draw_text_center(draw, (label_x, y - 3.0), label, font=font)


def draw_overlay_labels(
    draw: ImageDraw.ImageDraw,
    *,
    arrow_x: float,
    y_top: float,
    y_bottom: float,
    crop_x: int,
    crop_y: int,
) -> None:
    band_font = load_font(40, bold=True)
    value_font = load_font(28, bold=True)
    ai_label_x = arrow_x - 230.0 - crop_x
    ai_label_y = y_bottom + 86.0 - crop_y
    draw_text_center(draw, (ai_label_x, ai_label_y), "Best Performing AI Model", font=band_font)
    try:
        draw.text(
            (arrow_x + 150.0 - crop_x, (y_top + y_bottom) / 2.0 - crop_y - 10.0),
            "231 point Human-AI gap: July 10, 2026",
            fill=INK,
            font=value_font,
            anchor="lm",
        )
    except TypeError:
        draw.text(
            (arrow_x + 150.0 - crop_x, (y_top + y_bottom) / 2.0 - crop_y - 28.0),
            "231 point Human-AI gap: July 10, 2026",
            fill=INK,
            font=value_font,
        )


def draw_pil_arrow(
    image: Image.Image,
    option: Option,
    *,
    arrow_x: float,
    y_top: float,
    y_bottom: float,
    crop_x: int,
    crop_y: int,
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    x = arrow_x - crop_x
    top = y_top - crop_y
    bottom = y_bottom - crop_y
    cfg = LONG_FLAG_STYLES.get(option.style)
    if cfg is None:
        raise ValueError(f"Unsupported option style: {option.style}")
    head_w, head_h = diagonal_arm_projection(bottom - top, cfg)
    width = int(float(cfg["shaft_width"]))
    alpha = int(float(cfg["opacity"]) * 255)
    shaft_pad = float(cfg["shaft_pad"])
    blue = (47, 85, 231, alpha)
    draw.line((x, top, x - head_w, top + head_h), fill=blue, width=width)
    draw.line((x, top, x + head_w, top + head_h), fill=blue, width=width)
    draw.line((x, bottom, x - head_w, bottom - head_h), fill=blue, width=width)
    draw.line((x, bottom, x + head_w, bottom - head_h), fill=blue, width=width)
    if bool(cfg["split"]):
        mid = (top + bottom) / 2.0
        gap = float(cfg.get("gap", 34.0))
        draw.line((x, top + shaft_pad, x, mid - gap), fill=blue, width=width)
        draw.line((x, mid + gap, x, bottom - shaft_pad), fill=blue, width=width)
    else:
        draw.line((x, top + shaft_pad, x, bottom - shaft_pad), fill=blue, width=width)


def write_option_crop(option: Option, *, arrow_x: float, y_top: float, y_bottom: float) -> Path:
    crop_box = (1120, 700, 3080, 1320)
    crop_x, crop_y = crop_box[0], crop_box[1]
    base = Image.open(SOURCE_PNG).convert("RGB").crop(crop_box)
    draw = ImageDraw.Draw(base)
    cover = (0, 0, crop_box[2] - crop_box[0], crop_box[3] - crop_box[1])
    draw.rectangle(cover, fill="#ffffff")
    human_label_font = load_font(40, bold=True)
    draw_inline_dashed_label(
        draw,
        x1=610 - crop_x,
        x2=3070 - crop_x,
        y=y_top - crop_y,
        label_x=arrow_x - 360.0 - crop_x,
        label="Average Human Expert Baseline",
        line_fill=HUMAN_LINE,
        font=human_label_font,
    )
    draw_dashed_line(
        draw,
        610 - crop_x,
        y_bottom - crop_y,
        3070 - crop_x,
        fill=TOP_AI_LINE,
        width=12,
    )
    draw_overlay_labels(draw, arrow_x=arrow_x, y_top=y_top, y_bottom=y_bottom, crop_x=crop_x, crop_y=crop_y)
    draw_pil_arrow(base, option, arrow_x=arrow_x, y_top=y_top, y_bottom=y_bottom, crop_x=crop_x, crop_y=crop_y)
    out = OUT_DIR / f"gap_arrow_{option.key}_{option.style}_crop.png"
    base.save(out)
    return out


def draw_card(
    sheet: Image.Image,
    option: Option,
    crop_png: Path,
    *,
    x: int,
    y: int,
    w: int,
    h: int,
) -> None:
    draw = ImageDraw.Draw(sheet)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=18, fill="#ffffff", outline=CARD_BORDER, width=3)
    header_font = load_font(40, bold=True)
    sub_font = load_font(23)
    draw.text((x + 30, y + 24), f"Option {option.key}: {option.title}", fill=INK, font=header_font)
    draw.text((x + 30, y + 76), option.subtitle, fill=MUTED, font=sub_font)
    crop = Image.open(crop_png).convert("RGB")
    img_w = w - 60
    img_h = int(crop.height * img_w / crop.width)
    crop = crop.resize((img_w, img_h), Image.Resampling.LANCZOS)
    sheet.paste(crop, (x + 30, y + 124))


def write_contact_sheet(options: list[Option], crop_pngs: list[Path]) -> None:
    sheet_w = 3600
    margin = 90
    gutter = 60
    card_w = (sheet_w - 2 * margin - gutter) // 2
    card_h = 720
    title_h = 175
    rows = 3
    sheet_h = title_h + rows * card_h + (rows - 1) * gutter + margin
    sheet = Image.new("RGB", (sheet_w, sheet_h), PAPER)
    draw = ImageDraw.Draw(sheet)
    title_font = load_font(58, bold=True)
    body_font = load_font(28)
    draw.text((margin, 55), f"Panel 6.3 {DIAGONAL_RATIO_LABEL} Diagonal-Arm Arrow Options", fill=INK, font=title_font)
    draw.text(
        (margin, 124),
        (
            "All options keep the B/E language: thin blue shaft, open chevrons, "
            f"diagonal arm length = {DIAGONAL_RATIO_LABEL} of arrow height."
        ),
        fill=MUTED,
        font=body_font,
    )
    for idx, (option, crop_png) in enumerate(zip(options, crop_pngs, strict=True)):
        col = idx % 2
        row = idx // 2
        x = margin + col * (card_w + gutter)
        y = title_h + row * (card_h + gutter)
        draw_card(sheet, option, crop_png, x=x, y=y, w=card_w, h=card_h)
    sheet.save(CONTACT_SHEET)


def main() -> None:
    if not SOURCE_SVG.exists():
        raise FileNotFoundError(f"Missing source SVG: {SOURCE_SVG}")
    if not SOURCE_PNG.exists():
        raise FileNotFoundError(f"Missing source PNG: {SOURCE_PNG}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_root = ET.parse(SOURCE_SVG).getroot()
    _, arrow_x, y_top, y_bottom = arrow_geometry(source_root)
    option_svgs: list[Path] = []
    option_crops: list[Path] = []
    for option in OPTIONS:
        out_svg = OUT_DIR / f"gap_arrow_{option.key}_{option.style}.svg"
        write_option_svg(option, SOURCE_SVG, out_svg)
        option_svgs.append(out_svg)
        option_crops.append(write_option_crop(option, arrow_x=arrow_x, y_top=y_top, y_bottom=y_bottom))
    write_contact_sheet(OPTIONS, option_crops)
    manifest = {
        "source_svg": str(SOURCE_SVG),
        "contact_sheet": str(CONTACT_SHEET),
        "options": [
            {
                "key": option.key,
                "title": option.title,
                "subtitle": option.subtitle,
                "style": option.style,
                "svg": str(svg),
                "crop_png": str(crop_png),
            }
            for option, svg, crop_png in zip(OPTIONS, option_svgs, option_crops, strict=True)
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[PASS] wrote {CONTACT_SHEET}")
    print(f"[PASS] wrote {MANIFEST}")


if __name__ == "__main__":
    main()
