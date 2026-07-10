"""Generate a contact sheet for candidate awarded-bin Likert palettes.

This is a design-only artifact. It does not modify the production Panel 2/3
generator or any existing Score1000 outputs.
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
    / "handwritten_panels_blue_likert_palette_options"
)
SVG_FILE = "blue_likert_palette_contract_sheet.svg"
HTML_FILE = "blue_likert_palette_contract_sheet.html"
PNG_FILE = "blue_likert_palette_contract_sheet.png"
JSON_FILE = "blue_likert_palette_options.json"

PAPER = "#fbfaf5"
CARD = "#ffffff"
INK = "#202124"
MUTED = "#5f6368"
RULE = "#d7d0c5"
BAR_OUTLINE = "#8a9299"
CURRENT_REDS = ["#fee5d9", "#fcae91", "#fb6a4a", "#de2d26", "#7f0000"]
LEGEND_LABELS = ["C L4", "C L3", "C L2", "C L1", "C L0", "IDK +1", "W L0", "W L1", "W L2", "W L3", "W L4"]

SELECTED_ROWS = [
    {
        "kind": "option",
        "name": "Blue Option A to current reds",
        "note": "Blue midpoint bridge for correct/IDK, then current wrong-confidence reds with no gray separator.",
        "colors": ["#08306b", "#155190", "#2171b5", "#6baed6", "#bdd7e7", "#deebf7", *CURRENT_REDS],
    },
    {
        "kind": "option",
        "name": "Green Option B to current reds",
        "note": "Deep-loaded green for correct/IDK, then current wrong-confidence reds with no gray separator.",
        "colors": ["#003d24", "#005a32", "#00733f", "#238b45", "#74c476", "#e5f5e0", *CURRENT_REDS],
    },
    {
        "kind": "option",
        "name": "Green Option C shifted to current reds",
        "note": "Removed #209879; #3fa986 becomes C L2; new C L1 is softer #6dc1a2.",
        "colors": ["#004c3f", "#00876c", "#3fa986", "#6dc1a2", "#9ad8bd", "#e5f5e0", *CURRENT_REDS],
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


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.strip().lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def label_fill(color: str) -> str:
    r, g, b = hex_to_rgb(color)
    # Relative luminance approximation is sufficient for black/white labels.
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    return "#ffffff" if luminance < 0.48 else INK


def bar_row(row: dict[str, object], index: int, y: int) -> list[str]:
    colors = [str(color) for color in row["colors"]]
    bar_x = 90
    bar_w = 1620
    bar_h = 84
    seg_w = bar_w / len(colors)
    clip_id = f"bar-clip-{index}"
    parts: list[str] = []
    title_size = 32
    title_weight = 780
    parts.append(text(90, y, str(row["name"]), title_size, title_weight))
    parts.append(text(90, y + 36, str(row["note"]), 20, 460, MUTED))
    bar_y = y + 72
    parts.append(
        f'<clipPath id="{clip_id}"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" '
        f'height="{bar_h}" rx="17" ry="17"/></clipPath>'
    )
    for idx, color in enumerate(colors):
        x = bar_x + idx * seg_w
        parts.append(
            f'<rect x="{x:.1f}" y="{bar_y}" width="{seg_w + 0.4:.1f}" height="{bar_h}" '
            f'fill="{esc(color)}" clip-path="url(#{clip_id})"/>'
        )
        label_color = label_fill(color)
        code_y = bar_y + (bar_h / 2) + 8
        parts.append(
            text(
                x + seg_w / 2,
                code_y,
                color.lower(),
                23,
                780,
                label_color,
                "middle",
            )
        )
    parts.append(
        f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="17" ry="17" '
        f'fill="none" stroke="{BAR_OUTLINE}" stroke-width="2.2"/>'
    )
    label_y = bar_y + bar_h + 31
    for idx, label in enumerate(LEGEND_LABELS):
        x = bar_x + idx * seg_w + seg_w / 2
        parts.append(text(x, label_y, label, 15, 620, MUTED, "middle"))
    return parts


def build_svg() -> str:
    width, height = 1800, 1040
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f"<title>Selected Likert legend palette contract sheet</title>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{PAPER}"/>',
        f'<rect x="44" y="42" width="{width - 88}" height="{height - 84}" rx="20" '
        f'fill="{CARD}" stroke="{RULE}" stroke-width="2"/>',
        text(90, 112, "Selected Likert legend options", 48, 830),
        text(
            90,
            156,
            "Single-line legend bars: correct/IDK colors flow directly into current wrong-confidence reds.",
            25,
            460,
            MUTED,
        ),
    ]
    y_positions = [245, 495, 745]
    for idx, (row, y) in enumerate(zip(SELECTED_ROWS, y_positions, strict=True)):
        parts.extend(bar_row(row, idx, y))
    parts.append(text(90, 982, "Kept: Blue A, Green B, Green C. Current reds are appended on the same legend line; no gray segment.", 22, 640, INK))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def build_html(svg_source: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Selected Likert legend palette contract sheet</title>
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
                "purpose": "Design-only blue and green Likert palette contact sheet",
                "current_reds": CURRENT_REDS,
                "legend_labels": LEGEND_LABELS,
                "selected_rows": SELECTED_ROWS,
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
