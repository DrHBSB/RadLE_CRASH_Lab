#!/usr/bin/env python3
"""Generate a model bar-color contact sheet for the expanded RadLE roster."""

from __future__ import annotations

import argparse
import hashlib
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
    / "model_bar_color_contact_sheet"
)
LOGO_DIR = REPO_ROOT / "scripts" / "assets" / "radle_score1000_logos"
FONT_DIR = REPO_ROOT / "scripts" / "assets" / "fonts"
TITLE_FONT_PATH = FONT_DIR / "SpaceGrotesk-wght.ttf"
BODY_FONT_PATH = FONT_DIR / "Lexend-wght.ttf"

PNG_NAME = "model_bar_color_contact_sheet.png"
JSON_NAME = "model_bar_color_contact_sheet.json"

PAPER = "#fbfaf5"
CARD = "#ffffff"
INK = "#131e35"
MUTED = "#5f6368"
BORDER = "#d7d0c5"
GRID = "#e6e1d8"
WHITE = "#ffffff"

CANVAS_W = 3600
CANVAS_H = 2300
MARGIN_X = 90
TOP_Y = 70
CARD_W = 3420
RECOMMENDED_CARD_H = 610
ALT_CARD_H = 370
CARD_GAP = 42
BAR_W = 150
BAR_H_RECOMMENDED = 220
BAR_H_ALT = 122
LOGO_BOX = 94
ALT_LOGO_BOX = 62


@dataclass(frozen=True)
class ModelSpec:
    key: str
    label_lines: tuple[str, ...]
    logo_file: str
    category: str
    provider: str
    logo_scale: float = 0.86


MODELS = (
    ModelSpec("claude_fable_5", ("Claude", "Fable 5"), "claude_fable_5_logo.png", "closed generalist", "Anthropic"),
    ModelSpec("grok_4_3", ("Grok", "4.3"), "grok_4_3_logo.png", "closed generalist", "xAI"),
    ModelSpec("gemini_3_1_pro", ("Gemini", "3.1 Pro"), "gemini_3_1_pro_logo.png", "closed generalist", "Google"),
    ModelSpec("gpt_5_5", ("GPT-5.5",), "gpt_5_5_logo.png", "closed generalist", "OpenAI"),
    ModelSpec("octomed_7b", ("OctoMed", "7B"), "octomed_7b_logo.png", "open medical", "OctoMed", 1.02),
    ModelSpec("nemotron_3_omni", ("Nemotron", "3 Omni"), "nemotron_3_omni_logo.png", "open generalist", "NVIDIA"),
    ModelSpec("qwen_3_7_plus", ("Qwen", "3.7 Plus"), "qwen_3_7_plus_logo.png", "closed generalist", "Alibaba"),
    ModelSpec("glm_5v_turbo", ("GLM-5V", "Turbo"), "glm_5v_turbo_logo.png", "closed generalist", "Z.AI", 0.96),
    ModelSpec("minimax_m3", ("MiniMax", "M3"), "minimax_m3_logo.png", "open generalist", "MiniMax"),
    ModelSpec("gemma_4_31b", ("Gemma 4", "31B"), "gemma_4_31b_logo.png", "open generalist", "Google"),
    ModelSpec("lingshu_32b", ("Lingshu", "32B"), "lingshu_32b_logo.png", "open medical", "Lingshu", 0.94),
    ModelSpec("medgemma_1_5_4b", ("MedGemma", "1.5 4B"), "medgemma_1_5_4b_logo.png", "open medical", "Google"),
    ModelSpec("llama_4_maverick", ("Llama 4", "Maverick"), "llama_4_maverick_logo.png", "open generalist", "Meta", 0.92),
    ModelSpec("internvl3_5_8b", ("InternVL3.5", "8B"), "internvl3_5_8b_logo.png", "open generalist", "OpenGVLab", 0.96),
    ModelSpec("mistral_large_3_2512", ("Mistral", "Large 3", "2512"), "mistral_large_3_2512_logo.png", "open generalist", "Mistral", 0.9),
    ModelSpec(
        "human_expert_baseline",
        ("Human", "Expert", "Baseline"),
        "human_expert_baseline_deep_crimson_logo.png",
        "human baseline",
        "Radiologists",
        0.98,
    ),
)

PALETTES = (
    {
        "id": "A",
        "name": "Provider-family",
        "note": "Same-provider models stay in a hue family; variants use shade or clinical shift.",
        "colors": {
            "claude_fable_5": "#D97757",
            "grok_4_3": "#3F464C",
            "gemini_3_1_pro": "#4285F4",
            "gpt_5_5": "#10A37F",
            "octomed_7b": "#E85D75",
            "nemotron_3_omni": "#76B900",
            "qwen_3_7_plus": "#7B61E7",
            "glm_5v_turbo": "#155AD6",
            "minimax_m3": "#E43D68",
            "gemma_4_31b": "#72A6FF",
            "lingshu_32b": "#006C7A",
            "medgemma_1_5_4b": "#00A6D6",
            "llama_4_maverick": "#1877F2",
            "internvl3_5_8b": "#536DFE",
            "mistral_large_3_2512": "#F59E0B",
            "human_expert_baseline": "#A61E2E",
        },
    },
    {
        "id": "B",
        "name": "Role-family",
        "note": "Closed, open-general, and medical groups get visibly different families.",
        "colors": {
            "claude_fable_5": "#6B5B7A",
            "grok_4_3": "#263238",
            "gemini_3_1_pro": "#315F9F",
            "gpt_5_5": "#2A766C",
            "octomed_7b": "#D96C4F",
            "nemotron_3_omni": "#8DAE2B",
            "qwen_3_7_plus": "#6950A1",
            "glm_5v_turbo": "#1F4F88",
            "minimax_m3": "#B65A7A",
            "gemma_4_31b": "#7CA6D8",
            "lingshu_32b": "#006B78",
            "medgemma_1_5_4b": "#46A6C6",
            "llama_4_maverick": "#2F80ED",
            "internvl3_5_8b": "#6B73C8",
            "mistral_large_3_2512": "#CA8A04",
            "human_expert_baseline": "#A61E2E",
        },
    },
    {
        "id": "C",
        "name": "Max-separation",
        "note": "Prioritizes adjacent-bar contrast over provider or brand identity.",
        "colors": {
            "claude_fable_5": "#D55E00",
            "grok_4_3": "#000000",
            "gemini_3_1_pro": "#0072B2",
            "gpt_5_5": "#009E73",
            "octomed_7b": "#CC79A7",
            "nemotron_3_omni": "#F0E442",
            "qwen_3_7_plus": "#AA3377",
            "glm_5v_turbo": "#56B4E9",
            "minimax_m3": "#E15759",
            "gemma_4_31b": "#4E79A7",
            "lingshu_32b": "#228833",
            "medgemma_1_5_4b": "#66CCEE",
            "llama_4_maverick": "#005AB5",
            "internvl3_5_8b": "#5D3A9B",
            "mistral_large_3_2512": "#E69F00",
            "human_expert_baseline": "#A61E2E",
        },
    },
    {
        "id": "D",
        "name": "Muted manuscript",
        "note": "Lower-chroma tones for print layouts and conservative journal figures.",
        "colors": {
            "claude_fable_5": "#8F5748",
            "grok_4_3": "#44484C",
            "gemini_3_1_pro": "#5A7595",
            "gpt_5_5": "#5E7C70",
            "octomed_7b": "#A9635D",
            "nemotron_3_omni": "#6C7F3D",
            "qwen_3_7_plus": "#6D628A",
            "glm_5v_turbo": "#415F86",
            "minimax_m3": "#8C536A",
            "gemma_4_31b": "#6F7F9F",
            "lingshu_32b": "#3C6A72",
            "medgemma_1_5_4b": "#5B8CA5",
            "llama_4_maverick": "#4B6D91",
            "internvl3_5_8b": "#626A8D",
            "mistral_large_3_2512": "#9C6F2A",
            "human_expert_baseline": "#A61E2E",
        },
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def text_fill_for(color: str) -> str:
    red, green, blue = hex_to_rgb(color)
    luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
    return WHITE if luminance < 0.48 else INK


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def draw_centered(
    draw: ImageDraw.ImageDraw,
    x_center: float,
    y: float,
    value: str,
    font: ImageFont.ImageFont,
    fill: str,
) -> None:
    left, top, right, bottom = draw.textbbox((0, 0), value, font=font)
    draw.text((x_center - (right - left) / 2, y - top), value, font=font, fill=fill)


def fill_rgba(fill: str, alpha: int = 255) -> tuple[int, int, int, int]:
    return hex_to_rgb(fill) + (alpha,)


def draw_vertical_centered(
    canvas: Image.Image,
    value: str,
    x_center: float,
    y_center: float,
    font: ImageFont.ImageFont,
    fill: str,
) -> None:
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    left, top, right, bottom = probe.textbbox((0, 0), value, font=font)
    pad = 4
    text_img = Image.new("RGBA", (right - left + pad * 2, bottom - top + pad * 2), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_img)
    text_draw.text((pad - left, pad - top), value, font=font, fill=fill_rgba(fill, 230))
    rotated = text_img.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
    canvas.alpha_composite(
        rotated,
        (
            int(round(x_center - rotated.width / 2)),
            int(round(y_center - rotated.height / 2)),
        ),
    )


def draw_model_label(
    draw: ImageDraw.ImageDraw,
    x_center: float,
    y: float,
    model: ModelSpec,
    font: ImageFont.ImageFont,
    fill: str,
    line_gap: int = 29,
) -> None:
    for idx, line in enumerate(model.label_lines):
        draw_centered(draw, x_center, y + idx * line_gap, line, font, fill)


def fit_logo(path: Path, box: int, scale: float) -> Image.Image:
    logo = Image.open(path).convert("RGBA")
    target = max(1, int(round(box * scale)))
    logo.thumbnail((target, target), Image.Resampling.LANCZOS)
    return logo


def paste_logo(canvas: Image.Image, path: Path, center_x: float, center_y: float, box: int, scale: float) -> None:
    x0 = int(round(center_x - box / 2))
    y0 = int(round(center_y - box / 2))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle((x0, y0, x0 + box, y0 + box), radius=16, fill=(255, 255, 255, 235), outline=(215, 208, 197, 255), width=2)
    logo = fit_logo(path, box - 14, scale)
    canvas.alpha_composite(logo, (x0 + (box - logo.width) // 2, y0 + (box - logo.height) // 2))


def draw_palette_card(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    palette: dict[str, object],
    y: int,
    height: int,
    fonts: dict[str, ImageFont.ImageFont],
    *,
    recommended: bool = False,
) -> None:
    draw.rounded_rectangle((MARGIN_X, y, MARGIN_X + CARD_W, y + height), radius=26, fill=CARD, outline=BORDER, width=3)
    title = f"{palette['id']}. {palette['name']}"
    draw.text((MARGIN_X + 42, y + 30), title, font=fonts["card_title"], fill=INK)
    draw.text((MARGIN_X + 42, y + 78), str(palette["note"]), font=fonts["note"], fill=MUTED)
    if recommended:
        badge = "recommended"
        left, top, right, bottom = draw.textbbox((0, 0), badge, font=fonts["badge"])
        bw = right - left + 34
        bx = MARGIN_X + CARD_W - bw - 42
        by = y + 32
        draw.rounded_rectangle((bx, by, bx + bw, by + 38), radius=19, fill="#E8F1EA", outline="#9DB5A2", width=2)
        draw.text((bx + 17, by + 5), badge, font=fonts["badge"], fill="#2F6B45")

    colors = palette["colors"]
    assert isinstance(colors, dict)
    n = len(MODELS)
    col_w = (CARD_W - 120) / n
    start_x = MARGIN_X + 60
    bar_top = y + (176 if recommended else 142)
    bar_h = BAR_H_RECOMMENDED if recommended else BAR_H_ALT
    bar_w = BAR_W if recommended else 112
    logo_box = LOGO_BOX if recommended else ALT_LOGO_BOX

    draw.line((MARGIN_X + 48, bar_top + bar_h + 1, MARGIN_X + CARD_W - 48, bar_top + bar_h + 1), fill=GRID, width=2)
    for idx, model in enumerate(MODELS):
        x_center = start_x + idx * col_w + col_w / 2
        color = str(colors[model.key])
        bar_x0 = x_center - bar_w / 2
        draw.rounded_rectangle((bar_x0, bar_top, bar_x0 + bar_w, bar_top + bar_h), radius=16, fill=color)
        side_fill = text_fill_for(color)
        if recommended:
            draw_vertical_centered(
                canvas,
                model.provider,
                bar_x0 + 15,
                bar_top + bar_h / 2,
                fonts["provider_side"],
                side_fill,
            )
            paste_logo(canvas, LOGO_DIR / model.logo_file, x_center, bar_top + 62, logo_box, model.logo_scale)
            draw_centered(draw, x_center, bar_top + bar_h + 26, color.upper(), fonts["hex"], color)
            draw_model_label(draw, x_center, bar_top + bar_h + 66, model, fonts["model"], INK)
        else:
            draw_vertical_centered(
                canvas,
                model.provider,
                bar_x0 + 13,
                bar_top + bar_h / 2,
                fonts["alt_provider_side"],
                side_fill,
            )
            draw_centered(draw, x_center, bar_top + 39, palette["id"], fonts["alt_id"], side_fill)
            paste_logo(canvas, LOGO_DIR / model.logo_file, x_center, bar_top + bar_h + 44, logo_box, model.logo_scale)
            draw_centered(draw, x_center, bar_top + bar_h + 88, color.upper(), fonts["alt_hex"], color)


def build_sheet(out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), hex_to_rgb(PAPER) + (255,))
    draw = ImageDraw.Draw(canvas, "RGBA")
    fonts: dict[str, ImageFont.ImageFont] = {
        "title": load_font(TITLE_FONT_PATH, 72),
        "subtitle": load_font(BODY_FONT_PATH, 30),
        "card_title": load_font(TITLE_FONT_PATH, 42),
        "note": load_font(BODY_FONT_PATH, 25),
        "badge": load_font(BODY_FONT_PATH, 22),
        "hex": load_font(BODY_FONT_PATH, 22),
        "model": load_font(BODY_FONT_PATH, 24),
        "provider_side": load_font(BODY_FONT_PATH, 17),
        "alt_id": load_font(TITLE_FONT_PATH, 54),
        "alt_hex": load_font(BODY_FONT_PATH, 16),
        "alt_provider_side": load_font(BODY_FONT_PATH, 12),
    }

    draw_centered(draw, CANVAS_W / 2, TOP_Y, "RadLE model and human bar color contact sheet", fonts["title"], INK)
    draw_centered(
        draw,
        CANVAS_W / 2,
        TOP_Y + 82,
        "Provider labels sit on the left side of each bar; the human baseline uses the expert comparator role.",
        fonts["subtitle"],
        MUTED,
    )

    y = 220
    for idx, palette in enumerate(PALETTES):
        recommended = idx == 0
        height = RECOMMENDED_CARD_H if recommended else ALT_CARD_H
        draw_palette_card(canvas, draw, palette, y, height, fonts, recommended=recommended)
        y += height + CARD_GAP

    png_path = out_dir / PNG_NAME
    canvas.convert("RGB").save(png_path)

    manifest = {
        "generated_at": utc_now(),
        "generator": rel(Path(__file__)),
        "output_png": rel(png_path),
        "purpose": "Design-only model and human baseline bar color suggestions for expanded RadLE Score1000 bar charts.",
        "notes": [
            "Palette A is the recommended default if provider-family continuity matters most.",
            "Palette B tests category-level grouping by closed, open-general, and open-medical roles.",
            "Palette C prioritizes color separation over provider identity.",
            "Palette D is a muted print-safe fallback.",
            "Human Expert Baseline uses the deep-crimson board-certified radiologists icon and fixed #A61E2E bar color.",
            "Provider labels are model owner/source labels placed on the left side of each bar, not necessarily runtime routing providers.",
            "Sample bars use equal height to isolate color choice; they are not data encodings.",
            "No production figure script was modified by this generator.",
        ],
        "models": [
            {
                "key": model.key,
                "label": " ".join(model.label_lines),
                "category": model.category,
                "provider": model.provider,
                "logo": rel(LOGO_DIR / model.logo_file),
            }
            for model in MODELS
        ],
        "palettes": PALETTES,
    }
    json_path = out_dir / JSON_NAME
    json_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest["files"] = {
        "png": {"file": rel(png_path), "sha256": sha256_file(png_path), "bytes": png_path.stat().st_size},
        "json": {"file": rel(json_path), "sha256": sha256_file(json_path), "bytes": json_path.stat().st_size},
    }
    json_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"png": png_path, "json": json_path}


def main() -> None:
    args = parse_args()
    outputs = build_sheet(args.out_dir.resolve())
    print(f"[PASS] wrote {outputs['png']}")
    print(f"[PASS] wrote {outputs['json']}")


if __name__ == "__main__":
    main()
