#!/usr/bin/env python3
"""Generate a contact sheet comparing Score1000 Panel 5 human-emphasis options."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from make_radle_v2_score1000_panel23_svg import (
    DEFAULT_OUT_DIR,
    DEFAULT_SCORE_ROOT,
    DEFAULT_VARIANT_OUT_DIR,
    FONT,
    INK,
    MUTED,
    PAPER,
    SCORE1000_BAR_READER_LABELS,
    esc,
    font_face_css,
    panel_5_score1000_bar_chart,
    read_csv,
    rel,
    sha256_file,
    utc_now,
    write_text,
)


OPTION_OUT_DIR = DEFAULT_VARIANT_OUT_DIR / "panel5_options"
OPTION_FILES = [
    "panel_2_score1000_5_1_compressed_positive_axis.svg",
    "panel_2_score1000_5_2_human_emphasis_markers.svg",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-panel-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--out-dir", type=Path, default=OPTION_OUT_DIR)
    parser.add_argument("--skip-render", action="store_true")
    return parser.parse_args()


def write_contact_sheet(out_dir: Path) -> None:
    captions = {
        OPTION_FILES[0]: "Option 1. Same rows with larger reader/model icons, y-axis compressed to -500 to +30.",
        OPTION_FILES[1]: "Option 2. Current -500 to +50 y-axis with larger reader/model icons and subtle human emphasis markers.",
    }
    cards = []
    for filename in OPTION_FILES:
        svg = (out_dir / filename).read_text(encoding="utf-8")
        cards.append(f"<figure>{svg}<figcaption>{html.escape(captions[filename])}</figcaption></figure>")
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>RadLE v2 Score1000 Panel 5 Options</title>
<style>
{font_face_css()}
body {{ margin: 0; padding: 28px; background: #efede7; font-family: {FONT}; color: {INK}; }}
h1 {{ font-size: 26px; margin: 0 0 18px 0; }}
figure {{ margin: 0 0 34px 0; background: white; padding: 12px; border: 1px solid #d7d0c5; }}
svg {{ width: 100%; height: auto; display: block; }}
figcaption {{ font-size: 18px; margin-top: 10px; color: {MUTED}; }}
</style>
</head>
<body>
<h1>RadLE v2 Score1000 Panel 5 options</h1>
{''.join(cards)}
</body>
</html>
"""
    write_text(out_dir / "score1000_panel5_options_contact_sheet.html", html_doc)


def write_manifest(out_dir: Path) -> None:
    files = [
        *OPTION_FILES,
        "score1000_panel5_options_contact_sheet.html",
    ]
    manifest = {
        "generated_at": utc_now(),
        "generator": rel(Path(__file__)),
        "selected_reader_labels": SCORE1000_BAR_READER_LABELS,
        "options": [
            {
                "option": "1",
                "file": OPTION_FILES[0],
                "description": "Compressed positive y-axis ceiling; y-axis domain -500 to +30.",
                "reader_model_icons": True,
            },
            {
                "option": "2",
                "file": OPTION_FILES[1],
                "description": "Current y-axis domain -500 to +50 with human emphasis markers.",
                "reader_model_icons": True,
            },
        ],
        "files": [],
    }
    for name in files:
        path = out_dir / name
        manifest["files"].append({"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    write_text(out_dir / "score1000_panel5_options_manifest.json", json.dumps(manifest, indent=2) + "\n")


def render_outputs(out_dir: Path) -> dict[str, Path]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"playwright is required for visual QA: {exc}") from exc

    rendered = {
        "contact_sheet": out_dir / "score1000_panel5_options_contact_sheet.png",
    }
    for filename in OPTION_FILES:
        rendered[filename.replace(".svg", "")] = out_dir / filename.replace(".svg", ".png")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        contact_page = browser.new_page(viewport={"width": 1500, "height": 2600}, device_scale_factor=1)
        contact_page.goto((out_dir / "score1000_panel5_options_contact_sheet.html").resolve().as_uri(), wait_until="networkidle")
        contact_page.screenshot(path=str(rendered["contact_sheet"]), full_page=True)
        contact_page.close()
        for filename in OPTION_FILES:
            page = browser.new_page(viewport={"width": 3600, "height": 2840}, device_scale_factor=1)
            page.goto((out_dir / filename).resolve().as_uri(), wait_until="networkidle")
            page.locator("svg").screenshot(path=str(rendered[filename.replace(".svg", "")]))
            page.close()
        browser.close()
    return rendered


def main() -> None:
    args = parse_args()
    source_panel_dir = args.source_panel_dir.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = read_csv(source_panel_dir / "score1000_panel23_bins.csv")
    provenance = json.loads((source_panel_dir / "score1000_likert_direction_provenance.json").read_text(encoding="utf-8"))

    option_1_svg = panel_5_score1000_bar_chart(
        rows,
        provenance,
        variant_label="5.1 option 1 compressed positive Score1000 axis",
        y_min=-500.0,
        y_max=30.0,
        ticks=[-500, -400, -300, -200, -100, 0, 30],
        include_model_icons=True,
        top_logo_scale=1.12,
        footer_note="Option 1: compressed positive ceiling. Axis range shown: -500 to +30 Score1000.",
    )
    option_2_svg = panel_5_score1000_bar_chart(
        rows,
        provenance,
        variant_label="5.2 option 2 human emphasis markers",
        y_min=-500.0,
        y_max=50.0,
        ticks=[-500, -400, -300, -200, -100, 0, 50],
        emphasize_humans=True,
        include_model_icons=True,
        top_logo_scale=1.12,
        footer_note="Option 2: current axis with human emphasis markers. Axis range shown: -500 to +50 Score1000.",
    )
    write_text(out_dir / OPTION_FILES[0], option_1_svg)
    write_text(out_dir / OPTION_FILES[1], option_2_svg)
    write_contact_sheet(out_dir)
    write_manifest(out_dir)

    rendered = {} if args.skip_render else render_outputs(out_dir)
    print(f"[PASS] generated Panel 5 option contact sheet {out_dir}")
    for key, path in rendered.items():
        print(f"[PASS] rendered {key}: {path}")


if __name__ == "__main__":
    main()
