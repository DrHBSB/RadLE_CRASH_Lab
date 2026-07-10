"""Generate a category-color option sheet for RadLE Score1000 panels.

This is a design-only artifact. It explores category key/text colors separately
from the outcome legend colors and does not modify production panel outputs.
"""

from __future__ import annotations

import asyncio
import html
import json
from pathlib import Path


OUT_DIR = (
    Path("outputs")
    / "radle_v2_stats"
    / "final_scoring_radiologist_20260706_001147"
    / "likert5_score1000"
    / "handwritten_panels_category_palette_options"
)
SVG_FILE = "category_palette_options.svg"
HTML_FILE = "category_palette_options.html"
PNG_FILE = "category_palette_options.png"
JSON_FILE = "category_palette_options.json"

PAPER = "#fbfaf5"
CARD = "#ffffff"
INK = "#202124"
MUTED = "#5f6368"
RULE = "#d7d0c5"
OUTLINE = "#8a9299"

CATEGORIES = ["Human reference", "Closed generalist", "Open generalist", "Open medical"]
SAMPLE_COLUMNS = [
    ("Human reference", ["Board-certified radiologists", "Radiology trainees"]),
    ("Closed generalist", ["Gemini 3.1 Pro", "Qwen 3.7 Plus"]),
    ("Open generalist", ["Nemotron 3 Omni", "Llama 4 Maverick"]),
    ("Open medical", ["OctoMed 7B", "Lingshu 32B"]),
]

PALETTES = [
    {
        "name": "Current reference - green now conflicts",
        "status": "reference",
        "rationale": "Shows the existing category grammar. Open generalist uses green/teal, which becomes unsafe if green is promoted into the outcome bars.",
        "colors": {
            "Human reference": "#5f6368",
            "Closed generalist": "#6f43d6",
            "Open generalist": "#00876c",
            "Open medical": "#b04a8a",
        },
    },
    {
        "name": "E0 - current blue and terracotta base",
        "status": "candidate",
        "rationale": "Baseline from the last pass. Blue radiologists and gray closed-source work; the open pair is related but a little muted.",
        "colors": {
            "Human reference": "#2f6f9f",
            "Closed generalist": "#5c6268",
            "Open generalist": "#a15c38",
            "Open medical": "#9b4555",
        },
    },
    {
        "name": "E1 - darker gray, brighter brown, pinker medical",
        "status": "candidate",
        "rationale": "Recommended balance. Closed-source gets more authority, open-generalist gains copper energy, and open-medical shifts clearly pink.",
        "colors": {
            "Human reference": "#2f6f9f",
            "Closed generalist": "#4b535b",
            "Open generalist": "#b65f2f",
            "Open medical": "#b64068",
        },
    },
    {
        "name": "E2 - brighter clinical blue, rose medical",
        "status": "candidate",
        "rationale": "Slightly more screen-forward. Radiologists pop more, closed-source stays dark neutral, and medical becomes a clean rose.",
        "colors": {
            "Human reference": "#347eb1",
            "Closed generalist": "#47515a",
            "Open generalist": "#bd6a32",
            "Open medical": "#c04a78",
        },
    },
    {
        "name": "E3 - deeper blue, charcoal gray, magenta lean",
        "status": "candidate",
        "rationale": "More contrast in the top categories. Open-generalist stays brown-copper while open-medical moves closer to magenta.",
        "colors": {
            "Human reference": "#256a9a",
            "Closed generalist": "#424a52",
            "Open generalist": "#b7552c",
            "Open medical": "#ad3d6b",
        },
    },
    {
        "name": "E4 - print-muted, still distinct",
        "status": "candidate",
        "rationale": "Lower-chroma version for manuscript figures. The gray is darker, brown is warmer, and medical is pink without feeling neon.",
        "colors": {
            "Human reference": "#2d719b",
            "Closed generalist": "#485057",
            "Open generalist": "#aa603a",
            "Open medical": "#a84560",
        },
    },
    {
        "name": "E5 - maximum category separation",
        "status": "candidate",
        "rationale": "The most legible at a glance. It gives every category a stronger identity while keeping green/teal free for the bars.",
        "colors": {
            "Human reference": "#1f77b4",
            "Closed generalist": "#3f464c",
            "Open generalist": "#c26a2e",
            "Open medical": "#c23b76",
        },
    },
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def text(
    x: float,
    y: float,
    value: str,
    size: int,
    weight: int = 500,
    fill: str = INK,
    anchor: str = "start",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Inter, Helvetica, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}">{esc(value)}</text>'
    )


def wrap_note(value: str, width: int = 100) -> list[str]:
    words = value.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if len(candidate) > width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines[:3]


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.strip().lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def swatch_label_fill(color: str) -> str:
    r, g, b = hex_to_rgb(color)
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    return "#ffffff" if luminance < 0.48 else INK


def draw_palette(palette: dict[str, object], index: int, y: int) -> list[str]:
    colors = palette["colors"]
    assert isinstance(colors, dict)
    sample_mode = str(palette.get("sample_mode", "colored_text"))
    parts: list[str] = []
    name = str(palette["name"])
    status = str(palette["status"])
    title_fill = INK if status == "candidate" else "#7a4d00"
    parts.append(text(90, y, name, 32, 790, title_fill))
    note_y = y + 36
    for line in wrap_note(str(palette["rationale"])):
        parts.append(text(90, note_y, line, 19, 450, MUTED))
        note_y += 25

    key_y = y + 112
    x0 = 90
    box_w = 365
    gap = 22
    for idx, category in enumerate(CATEGORIES):
        x = x0 + idx * (box_w + gap)
        color = str(colors[category])
        parts.append(
            f'<rect x="{x:.1f}" y="{key_y:.1f}" width="{box_w}" height="68" '
            f'rx="10" ry="10" fill="{esc(color)}" stroke="{OUTLINE}" stroke-width="1.8" '
            f'data-palette="{index}" data-category="{esc(category)}"/>'
        )
        parts.append(text(x + 18, key_y + 29, category, 19, 790, swatch_label_fill(color)))
        parts.append(text(x + 18, key_y + 54, color.lower(), 19, 760, swatch_label_fill(color)))

    sample_y = key_y + 114
    parts.append(text(90, sample_y - 24, "Ranked-list sample", 18, 700, MUTED))
    for idx, (category, labels) in enumerate(SAMPLE_COLUMNS):
        x = 90 + idx * 390
        color = str(colors[category])
        if sample_mode == "neutral_rule":
            parts.append(text(x, sample_y, labels[0], 21, 820, "#3f464c"))
            parts.append(text(x, sample_y + 31, labels[1], 21, 820, "#3f464c"))
            parts.append(
                f'<rect x="{x:.1f}" y="{sample_y + 7:.1f}" width="210" height="5" '
                f'rx="2.5" fill="{esc(color)}" data-sample-rule="{esc(category)}"/>'
            )
            parts.append(text(x, sample_y + 63, category, 16, 620, color))
        else:
            parts.append(text(x, sample_y, labels[0], 21, 820, color))
            parts.append(text(x, sample_y + 31, labels[1], 21, 820, color))
            parts.append(text(x, sample_y + 63, category, 16, 560, color))
    return parts


def build_svg() -> str:
    width = 1800
    first_y = 270
    row_h = 390
    height = first_y + (len(PALETTES) - 1) * row_h + 390
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        "<title>RadLE category palette options</title>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{PAPER}"/>',
        f'<rect x="44" y="42" width="{width - 88}" height="{height - 84}" rx="20" '
        f'fill="{CARD}" stroke="{RULE}" stroke-width="2"/>',
        text(90, 112, "Blue-radiologist category color variants", 47, 830),
        text(
            90,
            156,
            "Use these only for category key, model names, and group headers. Outcome bars keep the green Likert palette.",
            24,
            460,
            MUTED,
        ),
        text(
            90,
            192,
            "Constraint: keep green/teal out of category colors when green is used for outcome bars; blue can be reserved for radiologists.",
            22,
            650,
            "#7a4d00",
        ),
    ]
    y_positions = [first_y + i * row_h for i in range(len(PALETTES))]
    for idx, (palette, y) in enumerate(zip(PALETTES, y_positions, strict=True)):
        parts.extend(draw_palette(palette, idx, y))
        if idx == 0:
            parts.append(f'<line x1="90" y1="{first_y + row_h - 42}" x2="1710" y2="{first_y + row_h - 42}" stroke="{RULE}" stroke-width="2"/>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def build_html(svg_source: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>RadLE category palette options</title>
  <style>
    body {{
      margin: 0;
      padding: 24px;
      background: #efede7;
      font-family: Inter, Helvetica, Arial, sans-serif;
      color: {INK};
    }}
    main {{
      width: 1800px;
      margin: 0 auto;
    }}
    svg {{
      display: block;
      width: 1800px;
      height: auto;
      box-shadow: 0 1px 8px rgba(32, 33, 36, 0.08);
    }}
  </style>
</head>
<body>
<main>
{svg_source}
</main>
</body>
</html>
"""


async def render_png(html_path: Path, png_path: Path) -> bool:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return False
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1900, "height": 1160}, device_scale_factor=1)
        await page.goto(html_path.resolve().as_uri())
        await page.screenshot(path=str(png_path), full_page=True)
        await browser.close()
    return True


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    svg_source = build_svg()
    svg_path = OUT_DIR / SVG_FILE
    html_path = OUT_DIR / HTML_FILE
    png_path = OUT_DIR / PNG_FILE
    svg_path.write_text(svg_source, encoding="utf-8")
    html_path.write_text(build_html(svg_source), encoding="utf-8")
    (OUT_DIR / JSON_FILE).write_text(
        json.dumps(
            {
                "purpose": "Design-only E-style category palette variants when green/teal is reserved for outcome bars and blue identifies radiologists",
                "categories": CATEGORIES,
                "palettes": PALETTES,
                "production_files_modified": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    rendered = asyncio.run(render_png(html_path, png_path))
    print(f"[PASS] wrote {svg_path}")
    print(f"[PASS] wrote {html_path}")
    print(f"[PASS] wrote {OUT_DIR / JSON_FILE}")
    if rendered:
        print(f"[PASS] rendered {png_path}")
    else:
        print("[WARN] Playwright unavailable; PNG was not rendered")


if __name__ == "__main__":
    main()
