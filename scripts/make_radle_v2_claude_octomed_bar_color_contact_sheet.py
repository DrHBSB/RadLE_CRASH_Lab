#!/usr/bin/env python3
"""Generate a bar-focused contact sheet for Claude and OctoMed color options."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = (
    REPO_ROOT
    / "outputs"
    / "radle_v2_stats"
    / "final_scoring_radiologist_20260706_001147"
    / "likert5_score1000"
    / "handwritten_panels_model_group_color_final"
    / "bar_color_contact_sheet"
)
LOGO_DIR = REPO_ROOT / "scripts" / "assets" / "radle_score1000_logos"
FONT_DIR = REPO_ROOT / "scripts" / "assets" / "fonts"
TITLE_FONT_PATH = FONT_DIR / "SpaceGrotesk-wght.ttf"
BODY_FONT_PATH = FONT_DIR / "Lexend-wght.ttf"

PNG_NAME = "claude_octomed_bar_color_contact_sheet.png"
JSON_NAME = "claude_octomed_bar_color_contact_sheet.json"

PAPER = "#fbfaf5"
CARD = "#ffffff"
INK = "#1b324d"
BODY = "#131e35"
MUTED = "#5f6368"
BORDER = "#d7d0c5"
GRID = "#e4dfd6"
WHITE = "#ffffff"

CANVAS_W = 2400
CANVAS_H = 1820
MARGIN_X = 90
TOP_Y = 78
SECTION_GAP = 110
CARD_GAP_X = 56
CARD_W = 696
CARD_H = 560
CARD_RADIUS = 28
BAR_W = 180
BAR_RADIUS = 24
LOGO_BOX = 104
LOGO_RADIUS = 18
MAX_BAR_H = 300
SCALE_MIN = -500.0
SCALE_MAX = 0.0


@dataclass(frozen=True)
class BarOption:
    name: str
    hex_code: str


@dataclass(frozen=True)
class ModelGroup:
    key: str
    label: str
    score: float
    logo_file: str
    logo_scale: float
    options: tuple[BarOption, BarOption, BarOption]


MODEL_GROUPS = (
    ModelGroup(
        key="claude_fable_5",
        label="Claude Fable 5",
        score=-242.0,
        logo_file="claude_fable_5_logo.png",
        logo_scale=0.82,
        options=(
            BarOption("Deep Chart Terracotta", "#C25B40"),
            BarOption("Core Anthropic Clay", "#D97757"),
            BarOption("Muted Mesa", "#E08C73"),
        ),
    ),
    ModelGroup(
        key="octomed_7b",
        label="OctoMed 7B",
        score=-373.0,
        logo_file="octomed_7b_logo.png",
        logo_scale=1.18,
        options=(
            BarOption("Deep Crimson Salmon", "#D95A53"),
            BarOption("True Octopus Coral", "#F27B73"),
            BarOption("Soft Shell Coral", "#F7A19B"),
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def text_w(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    x_center: float,
    y_top: float,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    draw.text((x_center - width / 2, y_top), text, font=font, fill=fill)


def fit_logo(logo: Image.Image, box_size: int, scale: float) -> Image.Image:
    target = max(1, int(box_size * scale))
    resized = logo.copy()
    resized.thumbnail((target, target), Image.Resampling.LANCZOS)
    return resized


def paste_logo(
    canvas: Image.Image,
    logo_path: Path,
    x_center: float,
    y_top: float,
    box_size: int,
    logo_scale: float,
) -> None:
    box_x = int(round(x_center - box_size / 2))
    box_y = int(round(y_top))
    box = Image.new("RGBA", (box_size, box_size), (255, 255, 255, 255))
    mask = Image.new("L", (box_size, box_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, box_size - 1, box_size - 1), radius=LOGO_RADIUS, fill=255)
    rounded = Image.new("RGBA", (box_size, box_size), (255, 255, 255, 0))
    rounded.paste(box, (0, 0), mask)
    canvas.alpha_composite(rounded, (box_x, box_y))

    logo = Image.open(logo_path).convert("RGBA")
    fitted = fit_logo(logo, box_size - 18, logo_scale)
    paste_x = box_x + (box_size - fitted.width) // 2
    paste_y = box_y + (box_size - fitted.height) // 2
    canvas.alpha_composite(fitted, (paste_x, paste_y))


def bar_height(score: float) -> float:
    span = SCALE_MAX - SCALE_MIN
    if span <= 0:
        return 0.0
    magnitude = max(0.0, min(abs(score), abs(SCALE_MIN)))
    return (magnitude / span) * MAX_BAR_H


def draw_preview_card(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    group: ModelGroup,
    option: BarOption,
    card_x: int,
    card_y: int,
    fonts: dict[str, ImageFont.FreeTypeFont],
) -> None:
    card_rect = (card_x, card_y, card_x + CARD_W, card_y + CARD_H)
    draw.rounded_rectangle(card_rect, radius=CARD_RADIUS, fill=CARD, outline=BORDER, width=3)

    x_center = card_x + CARD_W / 2
    draw_centered_text(draw, x_center, card_y + 28, option.name, fonts["card_title"], BODY)
    draw_centered_text(draw, x_center, card_y + 72, option.hex_code.upper(), fonts["hex"], MUTED)

    baseline_y = card_y + 170
    draw.line((card_x + 42, baseline_y, card_x + CARD_W - 42, baseline_y), fill=GRID, width=4)
    draw_centered_text(draw, card_x + 56, baseline_y - 26, "0", fonts["tick"], MUTED)

    current_label = f"score {group.score:.0f}"
    current_w = text_w(draw, current_label, fonts["meta"])
    draw.text((card_x + CARD_W - 34 - current_w, card_y + 28), current_label, font=fonts["meta"], fill=MUTED)

    bar_h = bar_height(group.score)
    bar_x = int(round(x_center - BAR_W / 2))
    bar_y = int(round(baseline_y))
    bar_bottom = int(round(bar_y + bar_h))
    draw.rounded_rectangle((bar_x, bar_y, bar_x + BAR_W, bar_bottom), radius=BAR_RADIUS, fill=option.hex_code)

    logo_y = min(bar_y + 30, bar_bottom - LOGO_BOX - 18)
    paste_logo(
        canvas,
        LOGO_DIR / group.logo_file,
        x_center=x_center,
        y_top=logo_y,
        box_size=LOGO_BOX,
        logo_scale=group.logo_scale,
    )

    score_y = bar_bottom + 18
    draw_centered_text(draw, x_center, score_y, f"{group.score:.0f}", fonts["score"], option.hex_code)
    draw_centered_text(draw, x_center, card_y + CARD_H - 92, group.label, fonts["model"], BODY)


def build_sheet(out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), hex_to_rgb(PAPER) + (255,))
    draw = ImageDraw.Draw(canvas)
    fonts = {
        "title": load_font(TITLE_FONT_PATH, 64),
        "subtitle": load_font(BODY_FONT_PATH, 26),
        "section": load_font(TITLE_FONT_PATH, 42),
        "card_title": load_font(TITLE_FONT_PATH, 26),
        "hex": load_font(BODY_FONT_PATH, 22),
        "meta": load_font(BODY_FONT_PATH, 20),
        "tick": load_font(BODY_FONT_PATH, 18),
        "score": load_font(BODY_FONT_PATH, 34),
        "model": load_font(BODY_FONT_PATH, 24),
    }

    draw_centered_text(draw, CANVAS_W / 2, TOP_Y, "Claude + OctoMed bar color options", fonts["title"], INK)
    draw_centered_text(
        draw,
        CANVAS_W / 2,
        TOP_Y + 82,
        "Bar-only previews using the live model logos and current score labels",
        fonts["subtitle"],
        MUTED,
    )

    section_y = TOP_Y + 180
    for group in MODEL_GROUPS:
        draw.text((MARGIN_X, section_y), group.label, font=fonts["section"], fill=INK)
        draw.text(
            (MARGIN_X, section_y + 50),
            "Three warm-direction bar candidates ranked strongest to softest",
            font=fonts["subtitle"],
            fill=MUTED,
        )
        cards_y = section_y + 110
        for idx, option in enumerate(group.options):
            card_x = MARGIN_X + idx * (CARD_W + CARD_GAP_X)
            draw_preview_card(canvas, draw, group, option, card_x, cards_y, fonts)
        section_y = cards_y + CARD_H + SECTION_GAP

    png_path = out_dir / PNG_NAME
    canvas.save(png_path)

    manifest = {
        "generated_at": utc_now(),
        "generator": str(Path(__file__).relative_to(REPO_ROOT)).replace("\\", "/"),
        "output_png": str(png_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "scale": {"score_min": SCALE_MIN, "score_max": SCALE_MAX, "max_bar_height_px": MAX_BAR_H},
        "models": [
            {
                "key": group.key,
                "label": group.label,
                "score": group.score,
                "logo_file": f"scripts/assets/radle_score1000_logos/{group.logo_file}",
                "options": [{"name": option.name, "hex": option.hex_code} for option in group.options],
            }
            for group in MODEL_GROUPS
        ],
    }
    json_path = out_dir / JSON_NAME
    json_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"png": png_path, "json": json_path}


def main() -> None:
    args = parse_args()
    outputs = build_sheet(args.out_dir.resolve())
    print(f"[PASS] wrote {outputs['png']}")
    print(f"[PASS] wrote {outputs['json']}")


if __name__ == "__main__":
    main()
