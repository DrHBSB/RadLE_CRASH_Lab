#!/usr/bin/env python3
"""Audit RadLE v2 Score1000 handwritten Panel 2/3 artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from fractions import Fraction
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
DEFAULT_VARIANT_OUT_DIR = DEFAULT_SCORE_ROOT / "handwritten_panels_model_group_color_final"
EXPECTED_SOURCE_SHA256 = "7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED"
EXPECTED_FIGURE_TITLE = "Radiology's Last Exam 2.0"
EXPECTED_FIGURE_TITLE_Y = 144.0
EXPECTED_PANEL2_TITLE = "Diagnostic outcomes stratified by confidence"
EXPECTED_SCORE2000_BAR_TITLE = "Confidence-weighted diagnosis correctness"
EXPECTED_SCORE2000_BAR_AXIS_TITLE = "Confidence-weighted diagnosis score"
EXPECTED_SCORE2000_BAR_CLOSED_TITLE = (
    "Proprietary Frontier Vision Language Models (VLMs) vs Human Expert Baseline"
)
EXPECTED_SCORE2000_BAR_OPEN_TITLE = "Open-access models vs 12 radiologists/trainees"
EXPECTED_SCORE2000_BAR_OPEN_VLM_TITLE = (
    "Open-Weights Vision Language Models (VLMs) vs Human Expert Baseline"
)
EXPECTED_SCORE2000_BAR_THROUGH_MEDGEMMA_TITLE = "Models through MedGemma vs 12 radiologists/trainees"
EXPECTED_SCORE2000_BAR_CLOSED_OPEN_THROUGH_MEDGEMMA_TITLE = (
    "Confidence-Weighted Diagnosis Scores: AI Models vs Human Expert Baseline"
)
EXPECTED_SCORE2000_BAR_ALL_MODEL_TITLE = (
    "Frontier Vision Language Models (VLMs) vs Human Expert Baseline"
)
IDK_SCORE = 1


def signed_score(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)


def likert_legend_labels(idk_score: int) -> list[str]:
    return [
        "C L4",
        "C L3",
        "C L2",
        "C L1",
        "C L0",
        f"IDK {signed_score(idk_score)}",
        "W L0",
        "W L1",
        "W L2",
        "W L3",
        "W L4",
    ]


def score1000_bar_footer_lines(idk_score: int) -> list[str]:
    all_idk_score1000 = 200 * idk_score
    all_idk_score2000 = all_idk_score1000 + 1000
    idk_line = (
        "\"I don't know\" responses add 1 before display shifting; blank/failed responses score 0."
        if idk_score == 1
        else "\"I don't know\"/blank/failed responses score 0 before display shifting."
    )
    return [
        "Confidence-weighted diagnosis correctness across 200 adjudicated radiology cases; not accuracy or calibration.",
        "Human reference pools 12 radiologists/trainees; correct diagnoses add 1-5 by confidence, wrong diagnoses subtract 1-5.",
        f"{idk_line} Displayed score = raw + 1000; {all_idk_score2000} is the all-\"I don't know\" baseline.",
    ]


def promoted_panel5_footer_lines(idk_score: int) -> list[str]:
    return score1000_bar_footer_lines(idk_score)


def score1000_footer_note(idk_score: int) -> str:
    return " ".join(score1000_bar_footer_lines(idk_score))


FOOTER_SCORE1000_NOTE = score1000_footer_note(IDK_SCORE)
LOGO_ASSET_DIR = REPO_ROOT / "scripts" / "assets" / "radle_score1000_logos"
SVG_NS = "{http://www.w3.org/2000/svg}"

PANEL_FILES = [
    "panel_2_score1000_edge_justified_ledger.svg",
    "panel_3_score1000_100_barcode_percentage_strip.svg",
]
VARIANT_PANEL_FILES = [
    "panel_2_score1000_2_1_revised_colored_model_names.svg",
    "panel_2_score1000_3_1_revised_grouped_bands.svg",
    "panel_2_score1000_2_2_option_a_blue_to_red_colored_model_names.svg",
    "panel_2_score1000_3_2_option_a_blue_to_red_grouped_bands.svg",
    "panel_2_score1000_2_3_option_c_teal_green_to_red_colored_model_names.svg",
    "panel_2_score1000_3_3_option_c_teal_green_to_red_grouped_bands.svg",
    "panel_2_score1000_2_4_shared_palette_colored_model_names.svg",
    "panel_2_score1000_3_4_shared_palette_grouped_bands.svg",
    "panel_2_score1000_2_5_shared_palette_colored_scores_and_names.svg",
    "panel_2_score1000_3_5_shared_palette_grouped_bands_colored_scores.svg",
    "panel_2_score1000_5_0_clean_score1000_bar_chart.svg",
    "panel_2_score1000_5_1_icon_score1000_bar_chart.svg",
    "panel_2_score1000_5_5_icon_score1000_bar_chart.svg",
    "panel_2_score1000_5_6_open_models_bottom_logo_score1000_bar_chart.svg",
    "panel_2_score1000_6_0_human_through_medgemma_barcode_score1000_bar_chart.svg",
    "panel_2_score1000_6_1_closed_models_score1000_bar_chart.svg",
    "panel_2_score1000_6_1_1_closed_models_gap_score1000_bar_chart.svg",
    "panel_2_score1000_6_2_open_models_score1000_bar_chart.svg",
    "panel_2_score1000_6_2_1_open_models_gap_score1000_bar_chart.svg",
    "panel_2_score1000_6_3_closed_open_through_medgemma_score1000_bar_chart.svg",
    "panel_2_score1000_6_4_all_models_score1000_bar_chart.svg",
]
PROMOTED_PANEL5_SVG = "panel_2_score1000_5_4_icon_ribbon_score1000_bar_chart.svg"
PROMOTED_PANEL5_PNG = "panel_2_score1000_5_4_icon_ribbon_score1000_bar_chart.png"
PROMOTED_PANEL5_TITLE = "Panel 5.4 bottom-logo confidence-weighted diagnosis chart"
PROMOTED_PANEL5_LAYOUT = "score1000_bar_chart_bottom_logos"
PROMOTED_PANEL5_LOGO_LAYOUT = "bottom-under-labels"
PROMOTED_PANEL5_BOTTOM_LOGO_CENTER_Y = 2390.0
PROMOTED_PANEL5_FILES = [
    PROMOTED_PANEL5_SVG,
    PROMOTED_PANEL5_PNG,
]
PROMOTED_PANEL5_SELECTED_READER_LABELS = [
    "Human Expert Baseline",
    "claude_fable_5",
    "grok_4_3",
    "gemini_3_1_pro",
    "gpt_5_5",
    "qwen_3_7_plus",
    "glm_5v_turbo",
]
PROMOTED_PANEL5_KEY_BY_READER_LABEL = {
    "Human Expert Baseline": "human_expert_baseline",
    "claude_fable_5": "claude_fable_5",
    "grok_4_3": "grok_4_3",
    "gemini_3_1_pro": "gemini_3_1_pro",
    "gpt_5_5": "gpt_5_5",
    "qwen_3_7_plus": "qwen_3_7_plus",
    "glm_5v_turbo": "glm_5v_turbo",
}
PROMOTED_PANEL5_DISPLAY_BY_READER_LABEL = {
    "Human Expert Baseline": "Human Expert Baseline",
    "claude_fable_5": "Claude Fable 5",
    "grok_4_3": "Grok 4.3",
    "gemini_3_1_pro": "Gemini 3.1 Pro",
    "gpt_5_5": "GPT-5.5",
    "qwen_3_7_plus": "Qwen 3.7 Plus",
    "glm_5v_turbo": "GLM-5V Turbo",
}
REQUIRED_FILES = [
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
]
VARIANT_REQUIRED_FILES = [
    "score1000_panel23_bins.csv",
    "score1000_likert_direction_provenance.json",
    *VARIANT_PANEL_FILES,
    *PROMOTED_PANEL5_FILES,
    "contact_sheet.html",
    "captions.md",
    "figure_manifest.json",
    "data_provenance.json",
    "data_provenance.md",
    "reviewer_checklist.md",
    "font_sizes.csv",
    "handwritten_panels_qa.txt",
]
CORRECT_BINS = ["correct_l4", "correct_l3", "correct_l2", "correct_l1", "correct_l0"]
WRONG_BINS = ["wrong_l0", "wrong_l1", "wrong_l2", "wrong_l3", "wrong_l4"]
BIN_COLUMNS = [*CORRECT_BINS, "neutral", *WRONG_BINS]
DOT_COLUMNS = [f"dot_{key}" for key in BIN_COLUMNS]
DOT_DISPLAY_TOTAL = 100
EXPECTED_COMPARATORS = 16
EXPECTED_PANEL3_UNITS = EXPECTED_COMPARATORS * DOT_DISPLAY_TOTAL
LIKERT_LEGEND_LABELS = likert_legend_labels(IDK_SCORE)
OUTCOME_PALETTES = {
    "current": {
        "name": "Current blue-gray-red outcome palette",
        "colors": {
            "correct_l4": "#08306b",
            "correct_l3": "#2171b5",
            "correct_l2": "#6baed6",
            "correct_l1": "#bdd7e7",
            "correct_l0": "#deebf7",
            "neutral": "#c7ccd1",
            "wrong_l0": "#fee5d9",
            "wrong_l1": "#fcae91",
            "wrong_l2": "#fb6a4a",
            "wrong_l3": "#de2d26",
            "wrong_l4": "#7f0000",
        },
    },
    "option_a_blue_to_current_red": {
        "name": "Option A blue-to-current-red outcome palette",
        "colors": {
            "correct_l4": "#08306b",
            "correct_l3": "#155190",
            "correct_l2": "#2171b5",
            "correct_l1": "#6baed6",
            "correct_l0": "#bdd7e7",
            "neutral": "#deebf7",
            "wrong_l0": "#fee5d9",
            "wrong_l1": "#fcae91",
            "wrong_l2": "#fb6a4a",
            "wrong_l3": "#de2d26",
            "wrong_l4": "#7f0000",
        },
    },
    "option_c_teal_green_to_current_red": {
        "name": "Option C teal-green-to-current-red outcome palette",
        "colors": {
            "correct_l4": "#004c3f",
            "correct_l3": "#006c52",
            "correct_l2": "#00876c",
            "correct_l1": "#3fa986",
            "correct_l0": "#9ad8bd",
            "neutral": "#e5f5e0",
            "wrong_l0": "#fee5d9",
            "wrong_l1": "#fcae91",
            "wrong_l2": "#fb6a4a",
            "wrong_l3": "#de2d26",
            "wrong_l4": "#7f0000",
        },
    },
}
SCORE1000_BAR_COLORS_WARM_REFRESH = {
    "Human Expert Baseline": "#1b324d",
    "grok_4_3": "#313131",
    "claude_fable_5": "#d97757",
    "gemini_3_1_pro": "#4796e3",
    "gpt_5_5": "#74aa9c",
    "octomed_7b": "#f27b73",
}
SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED = {
    "Human Expert Baseline": "#1b324d",
    "claude_fable_5": "#d97757",
    "grok_4_3": "#3f464c",
    "gemini_3_1_pro": "#4285f4",
    "gpt_5_5": "#10a37f",
    "octomed_7b": "#e85d75",
    "nemotron_3_omni": "#76b900",
    "qwen_3_7_plus": "#7b61e7",
    "glm_5v_turbo": "#155ad6",
    "minimax_m3": "#e43d68",
    "gemma_4_31b": "#72a6ff",
    "lingshu_32b": "#006c7a",
    "medgemma_1_5_4b": "#00a6d6",
    "llama_4_maverick": "#1877f2",
    "internvl3_5_8b": "#536dfe",
    "mistral_large_3_2512": "#f59e0b",
}
SCORE1000_BAR_COLORS_PALETTE_A = SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED
SCORE1000_BAR_THROUGH_MEDGEMMA_READER_LABELS = [
    "Human Expert Baseline",
    "claude_fable_5",
    "grok_4_3",
    "gemini_3_1_pro",
    "gpt_5_5",
    "octomed_7b",
    "nemotron_3_omni",
    "qwen_3_7_plus",
    "glm_5v_turbo",
    "minimax_m3",
    "gemma_4_31b",
    "lingshu_32b",
    "medgemma_1_5_4b",
]
SCORE1000_BAR_ALL_MODEL_READER_LABELS = [
    *SCORE1000_BAR_THROUGH_MEDGEMMA_READER_LABELS,
    "llama_4_maverick",
    "internvl3_5_8b",
    "mistral_large_3_2512",
]
SCORE1000_BAR_CLOSED_READER_LABELS = [
    "Human Expert Baseline",
    "claude_fable_5",
    "grok_4_3",
    "gemini_3_1_pro",
    "gpt_5_5",
    "qwen_3_7_plus",
    "glm_5v_turbo",
]
SCORE1000_BAR_OPEN_READER_LABELS = [
    "Human Expert Baseline",
    "octomed_7b",
    "nemotron_3_omni",
    "minimax_m3",
    "gemma_4_31b",
    "lingshu_32b",
    "medgemma_1_5_4b",
    "llama_4_maverick",
    "internvl3_5_8b",
    "mistral_large_3_2512",
]
SCORE1000_BAR_6_1_LOGO_IMAGE_MULTIPLIERS = {
    "gemini_3_1_pro": 1.09,
}
SCORE1000_BAR_6_2_LOGO_IMAGE_MULTIPLIERS = {
    "gemma_4_31b": 1.10,
    "lingshu_32b": 1.10,
    "medgemma_1_5_4b": 1.10,
    "internvl3_5_8b": 1.23,
}
SCORE1000_BAR_6_4_LOGO_IMAGE_MULTIPLIERS = {
    "gemma_4_31b": 1.15,
    "lingshu_32b": 1.18,
    "medgemma_1_5_4b": 1.15,
    "internvl3_5_8b": 1.38,
    "minimax_m3": 1.07,
}
SCORE1000_BAR_6_4_Y_AXIS_LEFT_SHIFT = 21.3
VARIANT_FILE_SPECS = {
    VARIANT_PANEL_FILES[0]: {
        "panel_id": "2.1",
        "variant": "2.1 revised colored model names",
        "layout": "colored_names",
        "palette_key": "current",
        "show_group_headers": False,
        "color_row_names": True,
    },
    VARIANT_PANEL_FILES[1]: {
        "panel_id": "3.1",
        "variant": "3.1 revised grouped bands",
        "layout": "grouped_bands",
        "palette_key": "current",
        "show_group_headers": True,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[2]: {
        "panel_id": "2.2",
        "variant": "2.2 Option A blue-to-red colored model names",
        "layout": "colored_names",
        "palette_key": "option_a_blue_to_current_red",
        "chart_x": 1015,
        "chart_w": 2320,
        "score_x": 150,
        "category_key_shift_x": -75,
        "show_group_headers": False,
        "color_row_names": True,
    },
    VARIANT_PANEL_FILES[3]: {
        "panel_id": "3.2",
        "variant": "3.2 Option A blue-to-red grouped bands",
        "layout": "grouped_bands",
        "palette_key": "option_a_blue_to_current_red",
        "chart_x": 1015,
        "chart_w": 2320,
        "score_x": 150,
        "category_key_shift_x": -75,
        "show_group_headers": False,
        "color_row_names": True,
    },
    VARIANT_PANEL_FILES[4]: {
        "panel_id": "2.3",
        "variant": "2.3 Option C teal-green-to-red colored model names",
        "layout": "colored_names",
        "palette_key": "option_c_teal_green_to_current_red",
        "chart_x": 1015,
        "chart_w": 2320,
        "score_x": 150,
        "category_key_shift_x": -75,
        "category_colors": {
            "Human Expert Baseline": "#2f6f9f",
            "Closed generalist": "#3f464c",
            "Open generalist": "#c26a2e",
            "Open medical": "#bd3f70",
        },
        "show_group_headers": False,
        "color_row_names": True,
    },
    VARIANT_PANEL_FILES[5]: {
        "panel_id": "3.3",
        "variant": "3.3 Option C teal-green-to-red grouped bands",
        "layout": "grouped_bands",
        "palette_key": "option_c_teal_green_to_current_red",
        "chart_x": 1015,
        "chart_w": 2320,
        "score_x": 150,
        "category_key_shift_x": -75,
        "category_colors": {
            "Human Expert Baseline": "#2f6f9f",
            "Closed generalist": "#3f464c",
            "Open generalist": "#c26a2e",
            "Open medical": "#bd3f70",
        },
        "show_group_headers": False,
        "color_row_names": True,
    },
    VARIANT_PANEL_FILES[6]: {
        "panel_id": "2.4",
        "variant": "2.4 shared-image category palette colored model names",
        "layout": "colored_names",
        "palette_key": "option_c_teal_green_to_current_red",
        "chart_x": 1015,
        "chart_w": 2320,
        "score_x": 150,
        "category_key_shift_x": -75,
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "show_group_headers": False,
        "color_row_names": True,
    },
    VARIANT_PANEL_FILES[7]: {
        "panel_id": "3.4",
        "variant": "3.4 shared-image category palette grouped bands",
        "layout": "grouped_bands",
        "palette_key": "option_c_teal_green_to_current_red",
        "chart_x": 1015,
        "chart_w": 2320,
        "score_x": 150,
        "category_key_shift_x": -75,
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "show_group_headers": False,
        "color_row_names": True,
    },
    VARIANT_PANEL_FILES[8]: {
        "panel_id": "2.5",
        "variant": "2.5 shared-image category palette colored scores and model names",
        "layout": "colored_names",
        "palette_key": "option_c_teal_green_to_current_red",
        "chart_x": 935,
        "chart_w": 2400,
        "score_x": 170,
        "name_x": 790,
        "category_key_shift_x": -75,
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "show_group_headers": False,
        "color_row_names": True,
        "color_scores": True,
    },
    VARIANT_PANEL_FILES[9]: {
        "panel_id": "3.5",
        "variant": "3.5 shared-image category palette grouped bands with colored scores",
        "layout": "grouped_bands",
        "palette_key": "option_c_teal_green_to_current_red",
        "chart_x": 935,
        "chart_w": 2400,
        "score_x": 170,
        "name_x": 790,
        "category_key_shift_x": -75,
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "show_group_headers": False,
        "color_row_names": True,
        "color_scores": True,
    },
    VARIANT_PANEL_FILES[10]: {
        "panel_id": "5.0",
        "variant": "5.0 clean confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "selected_reader_labels": [
            "Human Expert Baseline",
            "claude_fable_5",
            "grok_4_3",
            "gemini_3_1_pro",
            "gpt_5_5",
            "octomed_7b",
        ],
        "score_y_min": 0.0,
        "score_y_max": 2000.0,
        "score_ticks": [0, 500, 1000, 2000],
        "score_axis_break_after": 1000.0,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": 0.18,
        "axis_title": EXPECTED_SCORE2000_BAR_AXIS_TITLE,
        "use_variant_footer": True,
        "footer_lines": score1000_bar_footer_lines(IDK_SCORE),
        "footer_cls": "score1000-footer",
        "footer_text_y": 2586.0,
        "footer_line_step": 54.0,
        "footer_divider_y": 2500.0,
        "footer_font_px": 44.0,
        "footer_x": 215.0,
        "footer_right_x": 3440.0,
        "svg_h": 2840.0,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[11]: {
        "panel_id": "5.1",
        "variant": "5.1 icon confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "selected_reader_labels": [
            "Human Expert Baseline",
            "claude_fable_5",
            "grok_4_3",
            "gemini_3_1_pro",
            "gpt_5_5",
            "octomed_7b",
        ],
        "bar_colors": SCORE1000_BAR_COLORS_WARM_REFRESH,
        "score_y_min": 0.0,
        "score_y_max": 2000.0,
        "score_ticks": [0, 500, 1000, 2000],
        "score_axis_break_after": 1000.0,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": 0.18,
        "include_model_icons": True,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.5,
        "score_chart_y": 540.0,
        "figure_title_x": 1800.0,
        "figure_title_y": 166.0,
        "figure_title_font_px": 90.0,
        "panel_title": EXPECTED_SCORE2000_BAR_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": 394.0,
        "panel_title_font_px": 80.0,
        "axis_title": EXPECTED_SCORE2000_BAR_AXIS_TITLE,
        "tick_label_font_px": 45.0,
        "bar_value_font_scale": 1.5,
        "use_variant_footer": True,
        "footer_lines": score1000_bar_footer_lines(IDK_SCORE),
        "footer_cls": "score1000-footer",
        "footer_text_y": 2586.0,
        "footer_line_step": 54.0,
        "footer_divider_y": 2500.0,
        "footer_font_px": 44.0,
        "footer_x": 215.0,
        "footer_right_x": 3440.0,
        "x_label_y_offset": 78.0,
        "svg_h": 2840.0,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[12]: {
        "panel_id": "5.5",
        "variant": "5.5 refreshed-palette icon confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "selected_reader_labels": [
            "Human Expert Baseline",
            "claude_fable_5",
            "grok_4_3",
            "gemini_3_1_pro",
            "gpt_5_5",
            "octomed_7b",
        ],
        "bar_colors": SCORE1000_BAR_COLORS_WARM_REFRESH,
        "score_y_min": 0.0,
        "score_y_max": 2000.0,
        "score_ticks": [0, 500, 1000, 2000],
        "score_axis_break_after": 1000.0,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": 0.18,
        "include_model_icons": True,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.5,
        "score_chart_y": 540.0,
        "figure_title_x": 1800.0,
        "figure_title_y": 166.0,
        "figure_title_font_px": 90.0,
        "panel_title": EXPECTED_SCORE2000_BAR_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": 394.0,
        "panel_title_font_px": 80.0,
        "axis_title": EXPECTED_SCORE2000_BAR_AXIS_TITLE,
        "tick_label_font_px": 45.0,
        "bar_value_font_scale": 1.5,
        "use_variant_footer": True,
        "footer_lines": score1000_bar_footer_lines(IDK_SCORE),
        "footer_cls": "score1000-footer",
        "footer_text_y": 2586.0,
        "footer_line_step": 54.0,
        "footer_divider_y": 2500.0,
        "footer_font_px": 44.0,
        "footer_x": 215.0,
        "footer_right_x": 3440.0,
        "x_label_y_offset": 78.0,
        "svg_h": 2840.0,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[13]: {
        "panel_id": "5.6",
        "variant": "5.6 open-model bottom-logo confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "selected_reader_labels": SCORE1000_BAR_OPEN_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED,
        "score_y_min": 0.0,
        "score_y_max": 2000.0,
        "score_ticks": [0, 500, 1000, 2000],
        "score_axis_break_after": 1000.0,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": 0.18,
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2490.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.55,
        "score_chart_y": 540.0,
        "figure_title_x": 1800.0,
        "figure_title_y": 166.0,
        "figure_title_font_px": 90.0,
        "panel_title": EXPECTED_SCORE2000_BAR_OPEN_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": 394.0,
        "panel_title_font_px": 80.0,
        "axis_title": EXPECTED_SCORE2000_BAR_AXIS_TITLE,
        "tick_label_font_px": 45.0,
        "bar_value_font_scale": 1.35,
        "x_label_y_offset": 78.0,
        "x_label_font_px": 46.0,
        "x_label_line_step": 54.0,
        "use_variant_footer": False,
        "show_footer": False,
        "svg_h": 2840.0,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[14]: {
        "panel_id": "6.0",
        "variant": "6.0 Human-through-MedGemma barcode confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "selected_reader_labels": SCORE1000_BAR_THROUGH_MEDGEMMA_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_PALETTE_A,
        "score_y_min": 0.0,
        "score_y_max": 2000.0,
        "score_ticks": [0, 500, 1000, 2000],
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2395.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 0.82,
        "score_chart_y": 540.0,
        "score_bar_width": 150.0,
        "score_axis_break_after": 1000.0,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": 0.18,
        "include_barcode_overlay": True,
        "barcode_units": 18,
        "barcode_capsule_w": 24.0,
        "barcode_capsule_h": 10.0,
        "barcode_capsule_gap": 18.0,
        "barcode_outcome_palette_key": "option_c_teal_green_to_current_red",
        "figure_title_x": 1800.0,
        "figure_title_y": 166.0,
        "figure_title_font_px": 90.0,
        "panel_title": EXPECTED_SCORE2000_BAR_THROUGH_MEDGEMMA_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": 394.0,
        "panel_title_font_px": 80.0,
        "axis_title": EXPECTED_SCORE2000_BAR_AXIS_TITLE,
        "tick_label_font_px": 45.0,
        "bar_value_font_scale": 1.05,
        "use_variant_footer": True,
        "footer_lines": score1000_bar_footer_lines(IDK_SCORE),
        "footer_cls": "score1000-footer",
        "footer_text_y": 2608.0,
        "footer_line_step": 54.0,
        "footer_divider_y": 2550.0,
        "footer_font_px": 44.0,
        "footer_x": 215.0,
        "footer_right_x": 3440.0,
        "x_label_y_offset": 78.0,
        "svg_h": 2840.0,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[15]: {
        "panel_id": "6.1",
        "variant": "6.1 closed-model confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "selected_reader_labels": SCORE1000_BAR_CLOSED_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED,
        "score_y_min": 0.0,
        "score_y_max": 2000.0,
        "score_ticks": [0, 500, 1000, 2000],
        "score_axis_break_after": 1000.0,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": 0.18,
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2490.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.55,
        "bar_logo_image_multipliers": SCORE1000_BAR_6_1_LOGO_IMAGE_MULTIPLIERS,
        "score_chart_y": 540.0,
        "score_chart_h": 1700.0,
        "figure_title_x": 1800.0,
        "figure_title_y": 166.0,
        "figure_title_font_px": 90.0,
        "panel_title": EXPECTED_SCORE2000_BAR_CLOSED_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": 394.0,
        "panel_title_font_px": 80.0,
        "axis_title": EXPECTED_SCORE2000_BAR_AXIS_TITLE,
        "tick_label_font_px": 45.0,
        "bar_value_font_scale": 1.35,
        "x_label_y_offset": 78.0,
        "x_label_font_px": 46.0,
        "x_label_line_step": 54.0,
        "use_variant_footer": False,
        "show_footer": False,
        "svg_h": 2840.0,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[16]: {
        "panel_id": "6.1.1",
        "variant": "6.1.1 closed-model confidence-weighted diagnosis vertical bar chart with gap overlay",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "selected_reader_labels": SCORE1000_BAR_CLOSED_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED,
        "score_y_min": 0.0,
        "score_y_max": 2000.0,
        "score_ticks": [0, 500, 1000, 2000],
        "score_axis_break_after": 1000.0,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": 0.18,
        "include_score_gap_overlay": True,
        "score_gap_date_label": "July 10, 2026",
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2490.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.55,
        "bar_logo_image_multipliers": SCORE1000_BAR_6_1_LOGO_IMAGE_MULTIPLIERS,
        "score_chart_y": 540.0,
        "score_chart_h": 1700.0,
        "figure_title_x": 1800.0,
        "figure_title_y": 166.0,
        "figure_title_font_px": 90.0,
        "panel_title": EXPECTED_SCORE2000_BAR_CLOSED_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": 394.0,
        "panel_title_font_px": 80.0,
        "axis_title": EXPECTED_SCORE2000_BAR_AXIS_TITLE,
        "tick_label_font_px": 45.0,
        "bar_value_font_scale": 1.35,
        "x_label_y_offset": 78.0,
        "x_label_font_px": 46.0,
        "x_label_line_step": 54.0,
        "use_variant_footer": False,
        "show_footer": False,
        "svg_h": 2840.0,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[17]: {
        "panel_id": "6.2",
        "variant": "6.2 open-model confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "selected_reader_labels": SCORE1000_BAR_OPEN_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED,
        "score_y_min": 0.0,
        "score_y_max": 2000.0,
        "score_ticks": [0, 500, 1000, 2000],
        "score_axis_break_after": 1000.0,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": 0.18,
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2490.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.55,
        "bar_logo_image_multipliers": SCORE1000_BAR_6_2_LOGO_IMAGE_MULTIPLIERS,
        "score_chart_y": 540.0,
        "score_chart_h": 1700.0,
        "figure_title_x": 1800.0,
        "figure_title_y": 166.0,
        "figure_title_font_px": 90.0,
        "panel_title": EXPECTED_SCORE2000_BAR_OPEN_VLM_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": 394.0,
        "panel_title_font_px": 80.0,
        "axis_title": EXPECTED_SCORE2000_BAR_AXIS_TITLE,
        "tick_label_font_px": 45.0,
        "bar_value_font_scale": 1.35,
        "x_label_y_offset": 78.0,
        "x_label_font_px": 46.0,
        "x_label_line_step": 54.0,
        "use_variant_footer": False,
        "show_footer": False,
        "svg_h": 2840.0,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[18]: {
        "panel_id": "6.2.1",
        "variant": "6.2.1 open-model confidence-weighted diagnosis vertical bar chart with gap overlay",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "selected_reader_labels": SCORE1000_BAR_OPEN_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED,
        "score_y_min": 0.0,
        "score_y_max": 2000.0,
        "score_ticks": [0, 500, 1000, 2000],
        "score_axis_break_after": 1000.0,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": 0.18,
        "include_score_gap_overlay": True,
        "score_gap_date_label": "July 10, 2026",
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2490.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.55,
        "bar_logo_image_multipliers": SCORE1000_BAR_6_2_LOGO_IMAGE_MULTIPLIERS,
        "score_chart_y": 540.0,
        "score_chart_h": 1700.0,
        "figure_title_x": 1800.0,
        "figure_title_y": 166.0,
        "figure_title_font_px": 90.0,
        "panel_title": EXPECTED_SCORE2000_BAR_OPEN_VLM_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": 394.0,
        "panel_title_font_px": 80.0,
        "axis_title": EXPECTED_SCORE2000_BAR_AXIS_TITLE,
        "tick_label_font_px": 45.0,
        "bar_value_font_scale": 1.35,
        "x_label_y_offset": 78.0,
        "x_label_font_px": 46.0,
        "x_label_line_step": 54.0,
        "use_variant_footer": False,
        "show_footer": False,
        "svg_h": 2840.0,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[19]: {
        "panel_id": "6.3",
        "variant": "6.3 through-MedGemma confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "selected_reader_labels": SCORE1000_BAR_THROUGH_MEDGEMMA_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED,
        "score_y_min": 0.0,
        "score_y_max": 2000.0,
        "score_ticks": [0, 500, 1000, 2000],
        "score_axis_break_after": 1000.0,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": 0.18,
        "include_score_gap_overlay": True,
        "score_gap_date_label": "July 10, 2026",
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2490.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 0.82,
        "score_chart_y": 540.0,
        "score_chart_h": 1700.0,
        "score_bar_width": 150.0,
        "figure_title_x": 1800.0,
        "figure_title_y": 166.0,
        "figure_title_font_px": 90.0,
        "panel_title": EXPECTED_SCORE2000_BAR_CLOSED_OPEN_THROUGH_MEDGEMMA_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": 394.0,
        "panel_title_font_px": 80.0,
        "axis_title": EXPECTED_SCORE2000_BAR_AXIS_TITLE,
        "tick_label_font_px": 45.0,
        "bar_value_font_scale": 1.05,
        "use_variant_footer": False,
        "show_footer": False,
        "x_label_y_offset": 78.0,
        "svg_h": 2840.0,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[20]: {
        "panel_id": "6.4",
        "variant": "6.4 all-model confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": {
            "Human Expert Baseline": "#131e35",
            "Closed generalist": "#84848e",
            "Open generalist": "#6f9cda",
            "Open medical": "#1b324d",
        },
        "text_colors": {
            "text": "#131e35",
            "figure_title": "#1b324d",
        },
        "selected_reader_labels": SCORE1000_BAR_ALL_MODEL_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED,
        "score_y_min": 0.0,
        "score_y_max": 2000.0,
        "score_ticks": [0, 500, 1000, 2000],
        "score_axis_break_after": 1000.0,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": 0.18,
        "include_score_gap_overlay": True,
        "score_gap_date_label": "July 10, 2026",
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2490.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.40,
        "bar_logo_image_multipliers": SCORE1000_BAR_6_4_LOGO_IMAGE_MULTIPLIERS,
        "score_chart_y": 540.0,
        "score_chart_h": 1700.0,
        "score_bar_width": 150.0,
        "y_axis_left_shift": SCORE1000_BAR_6_4_Y_AXIS_LEFT_SHIFT,
        "figure_title_x": 1800.0,
        "figure_title_y": 166.0,
        "figure_title_font_px": 90.0,
        "panel_title": EXPECTED_SCORE2000_BAR_ALL_MODEL_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": 424.0,
        "panel_title_font_px": 80.0,
        "axis_title": EXPECTED_SCORE2000_BAR_AXIS_TITLE,
        "tick_label_font_px": 45.0,
        "bar_value_font_scale": 1.05,
        "x_label_y_offset": 78.0,
        "x_label_font_px": 30.0,
        "x_label_line_step": 38.0,
        "use_variant_footer": False,
        "show_footer": False,
        "svg_h": 2840.0,
        "show_group_headers": False,
        "color_row_names": False,
    },
}
VARIANT_GROUPED_FILES = {
    filename for filename, spec in VARIANT_FILE_SPECS.items() if spec["layout"] == "grouped_bands"
}
VARIANT_RANK_FILES = {
    filename for filename, spec in VARIANT_FILE_SPECS.items() if spec["layout"] == "colored_names"
}
NEW_NO_GRAY_VARIANT_FILES = {filename for filename, spec in VARIANT_FILE_SPECS.items() if spec["palette_key"] != "current"}
CATEGORY_COLORS = {
    "Human Expert Baseline": "#5f6368",
    "Closed generalist": "#6f43d6",
    "Open generalist": "#00876c",
    "Open medical": "#b04a8a",
}
OPTION_C_CATEGORY_COLORS = {
    "Human Expert Baseline": "#2f6f9f",
    "Closed generalist": "#3f464c",
    "Open generalist": "#c26a2e",
    "Open medical": "#bd3f70",
}
SHARED_IMAGE_CATEGORY_COLORS = {
    "Human Expert Baseline": "#131e35",
    "Closed generalist": "#84848e",
    "Open generalist": "#6f9cda",
    "Open medical": "#1b324d",
}
SHARED_IMAGE_TEXT_COLORS = {
    "text": "#131e35",
    "figure_title": "#1b324d",
}
CATEGORY_COLOR_VALUES = {value.lower() for value in CATEGORY_COLORS.values()}
ALL_CATEGORY_COLOR_VALUES = (
    CATEGORY_COLOR_VALUES
    | {value.lower() for value in OPTION_C_CATEGORY_COLORS.values()}
    | {value.lower() for value in SHARED_IMAGE_CATEGORY_COLORS.values()}
)
CATEGORY_ORDER = ["Human Expert Baseline", "Closed generalist", "Open generalist", "Open medical"]
VARIANT_CONTENT_Y_SHIFT = 48
VARIANT_SVG_H = 2840
VARIANT_HEADER_MIN_Y = 470
VARIANT_X_AXIS_Y = 2290 + VARIANT_CONTENT_Y_SHIFT
VARIANT_LEGEND_Y = 2424
VARIANT_FOOTER_DIVIDER_Y = 2600
VARIANT_FOOTER_TEXT_Y = 2648
VARIANT_FOOTER_LINE_STEP = 52
VARIANT_CHART_X = 940
VARIANT_CHART_W = 2470
VARIANT_GROUP_HEADER_X = 170
VARIANT_GROUP_RULE_X1 = 150
VARIANT_GROUP_RULE_X2 = 760
VARIANT_BAR_H = {
    VARIANT_PANEL_FILES[0]: 66.0,
    VARIANT_PANEL_FILES[1]: 62.0,
    VARIANT_PANEL_FILES[2]: 66.0,
    VARIANT_PANEL_FILES[3]: 62.0,
    VARIANT_PANEL_FILES[4]: 66.0,
    VARIANT_PANEL_FILES[5]: 62.0,
    VARIANT_PANEL_FILES[6]: 66.0,
    VARIANT_PANEL_FILES[7]: 62.0,
    VARIANT_PANEL_FILES[8]: 66.0,
    VARIANT_PANEL_FILES[9]: 62.0,
}
SCORE1000_BAR_COLORS = {
    "Human Expert Baseline": "#1b324d",
    "grok_4_3": "#3f464c",
    "claude_fable_5": "#84848e",
    "gemini_3_1_pro": "#2f6f9f",
    "gpt_5_5": "#1b324d",
    "octomed_7b": "#4c9f8f",
}
SCORE2000_SHIFT = 1000.0
SCORE2000_BASELINE = 1000.0
SCORE1000_BAR_Y_MIN = 0.0
SCORE1000_BAR_Y_MAX = 2000.0
SCORE1000_BAR_TICKS = [0, 500, 1000, 2000]
SCORE1000_BAR_A1_TICKS = [0, 500, 1000, 2000]
SCORE1000_BAR_CHART_X = 360.0
SCORE1000_BAR_CHART_Y = 520.0
SCORE1000_BAR_CHART_Y_5_1 = 540.0
SCORE1000_BAR_FIGURE_TITLE_X_5_1 = 1800.0
SCORE1000_BAR_FIGURE_TITLE_Y_5_1 = 166.0
SCORE1000_BAR_PANEL_TITLE_Y_5_1 = 394.0
SCORE1000_BAR_CHART_W = 3080.0
SCORE1000_BAR_CHART_H = 1610.0
SCORE1000_BAR_CHART_H_NO_FOOTER = 1700.0
SCORE1000_BAR_W = 230.0
SCORE1000_BAR_W_DENSE = 150.0
SCORE1000_BAR_VALUE_FONT_SIZE = 44.0
SCORE1000_BAR_X_LABEL_FONT_SIZE = 40.0
SCORE1000_BAR_X_LABEL_LINE_STEP = 48.0
SCORE1000_BAR_TICK_LABEL_X_OFFSET = 50.0
SCORE1000_BAR_AXIS_TITLE_X_OFFSET = 175.0
SCORE1000_BAR_AXIS_BREAK_AFTER = 1000.0
SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION = 0.18
SCORE1000_BAR_AXIS_BREAK_GAP = 42.0
SCORE1000_BAR_GAP_DATE_LABEL = "July 10, 2026"
SCORE1000_BAR_GAP_OVERLAY_LINE_START_FRACTION = 0.08
SCORE1000_BAR_GAP_OVERLAY_LINE_END_FRACTION = 0.88
SCORE1000_BAR_GAP_OVERLAY_ARROW_LINE_FRACTION = 0.66
SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_LINE_FRACTION = 0.33
SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_PRE_ARROW_FRACTION = 0.66
SCORE1000_BAR_GAP_OVERLAY_ARROW_X_FRACTION = (
    SCORE1000_BAR_GAP_OVERLAY_LINE_START_FRACTION
    + (SCORE1000_BAR_GAP_OVERLAY_LINE_END_FRACTION - SCORE1000_BAR_GAP_OVERLAY_LINE_START_FRACTION)
    * SCORE1000_BAR_GAP_OVERLAY_ARROW_LINE_FRACTION
)
SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL = "Average Human Expert Baseline"
SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_MASK_W = 850.0
SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_MASK_H = 74.0
SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_BASELINE_OFFSET = 17.0
SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL = "Best Performing AI Model"
SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_MASK_W = 690.0
SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_MASK_H = 74.0
SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_BASELINE_OFFSET = 17.0
SCORE1000_BAR_GAP_OVERLAY_ARROW_DIAGONAL_RATIO = 0.12
SCORE1000_BAR_GAP_OVERLAY_ARROW_45_PROJECTION = 0.7071067811865476
SCORE1000_BAR_BARCODE_UNITS = 18
SCORE1000_BAR_BARCODE_CAPSULE_W = 24.0
SCORE1000_BAR_BARCODE_CAPSULE_H = 10.0
SCORE1000_BAR_BARCODE_CAPSULE_GAP = 18.0
SCORE1000_BAR_BARCODE_TOP_PAD = 14.0
SCORE1000_BAR_BARCODE_BOTTOM_PAD = 14.0
SCORE1000_BAR_BARCODE_PALETTE = "option_c_teal_green_to_current_red"
VARIANT_KEY_SWATCH_X = {
    "Human Expert Baseline": 1980,
    "Closed generalist": 2496,
    "Open generalist": 2867,
    "Open medical": 3204,
}


def expected_variant_chart_x(filename: str) -> float:
    return float(VARIANT_FILE_SPECS[filename].get("chart_x", VARIANT_CHART_X))


def expected_variant_chart_w(filename: str) -> float:
    return float(VARIANT_FILE_SPECS[filename].get("chart_w", VARIANT_CHART_W))


def expected_variant_score_x(filename: str) -> float:
    return float(VARIANT_FILE_SPECS[filename].get("score_x", 134))


def expected_variant_name_x(filename: str) -> float:
    return float(VARIANT_FILE_SPECS[filename].get("name_x", 820))


def expected_variant_key_x(filename: str, category: str) -> float:
    return VARIANT_KEY_SWATCH_X[category] + float(VARIANT_FILE_SPECS[filename].get("category_key_shift_x", 0))


def expected_variant_category_colors(filename: str) -> dict[str, str]:
    return dict(VARIANT_FILE_SPECS[filename].get("category_colors", CATEGORY_COLORS))  # type: ignore[arg-type]


def expected_variant_text_colors(filename: str) -> dict[str, str] | None:
    text_colors = VARIANT_FILE_SPECS[filename].get("text_colors")
    if text_colors is None:
        return None
    return dict(text_colors)  # type: ignore[arg-type]


def expected_variant_bar_colors(filename: str) -> dict[str, str]:
    return dict(VARIANT_FILE_SPECS[filename].get("bar_colors", SCORE1000_BAR_COLORS))  # type: ignore[arg-type]


VARIANT_LOGO_ASSETS = {
    "left-affiliation-logo": LOGO_ASSET_DIR / "kcdha_logo.svg",
    "right-lab-logo": LOGO_ASSET_DIR / "crash_lab_logo.png",
}
VARIANT_LOGO_LAYOUT = {
    "left-affiliation-logo": {"x": 80, "y": 70, "width": 380, "height": 119},
    "right-lab-logo": {"x": 3150, "y": 82, "width": 370, "height": 132},
}
SCORE1000_BAR_LOGO_ASSETS = {
    "Human Expert Baseline": LOGO_ASSET_DIR / "human_expert_baseline_radiologist_navy_logo.png",
    "grok_4_3": LOGO_ASSET_DIR / "grok_4_3_logo.png",
    "claude_fable_5": LOGO_ASSET_DIR / "claude_fable_5_logo.png",
    "gemini_3_1_pro": LOGO_ASSET_DIR / "gemini_3_1_pro_logo.png",
    "gpt_5_5": LOGO_ASSET_DIR / "gpt_5_5_logo.png",
    "octomed_7b": LOGO_ASSET_DIR / "octomed_7b_logo.png",
    "nemotron_3_omni": LOGO_ASSET_DIR / "nemotron_3_omni_logo.png",
    "qwen_3_7_plus": LOGO_ASSET_DIR / "qwen_3_7_plus_logo.png",
    "glm_5v_turbo": LOGO_ASSET_DIR / "glm_5v_turbo_logo.png",
    "minimax_m3": LOGO_ASSET_DIR / "minimax_m3_logo.png",
    "gemma_4_31b": LOGO_ASSET_DIR / "gemma_4_31b_logo.png",
    "lingshu_32b": LOGO_ASSET_DIR / "lingshu_32b_logo.png",
    "medgemma_1_5_4b": LOGO_ASSET_DIR / "medgemma_1_5_4b_logo.png",
    "llama_4_maverick": LOGO_ASSET_DIR / "llama_4_maverick_logo.png",
    "internvl3_5_8b": LOGO_ASSET_DIR / "internvl3_5_8b_logo.png",
    "mistral_large_3_2512": LOGO_ASSET_DIR / "mistral_large_3_2512_logo.png",
}
SCORE1000_BAR_FALLBACK_BADGES = {}
SCORE1000_BAR_READER_KEYS = {
    "Human Expert Baseline": "human_expert_baseline",
    "claude_fable_5": "claude_fable_5",
    "grok_4_3": "grok_4_3",
    "gemini_3_1_pro": "gemini_3_1_pro",
    "gpt_5_5": "gpt_5_5",
    "octomed_7b": "octomed_7b",
    "nemotron_3_omni": "nemotron_3_omni",
    "qwen_3_7_plus": "qwen_3_7_plus",
    "glm_5v_turbo": "glm_5v_turbo",
    "minimax_m3": "minimax_m3",
    "gemma_4_31b": "gemma_4_31b",
    "lingshu_32b": "lingshu_32b",
    "medgemma_1_5_4b": "medgemma_1_5_4b",
    "llama_4_maverick": "llama_4_maverick",
    "internvl3_5_8b": "internvl3_5_8b",
    "mistral_large_3_2512": "mistral_large_3_2512",
}
SCORE1000_BAR_LOGO_BOX = 124.0
SCORE1000_BAR_LOGO_IMAGE = 96.0
SCORE1000_BAR_OCTOMED_LOGO_SCALE = 1.2
SCORE1000_BAR_HUMAN_LOGO_Y = 360.0
SCORE1000_BAR_HUMAN_SCORE_GAP = 42.0
SCORE1000_BAR_NEGATIVE_SCORE_GAP = 62.0
SCORE1000_BAR_HUMAN_LOGO_GAP = 70.0
SCORE1000_BAR_FOOTER_DIVIDER_Y = 2500.0
SCORE1000_BAR_FOOTER_TEXT_Y = 2600.0
SCORE1000_BAR_FOOTER_LINE_STEP = 66.0
SCORE1000_BAR_FOOTER_LINES = score1000_bar_footer_lines(IDK_SCORE)
CATEGORY_MODEL_GROUPS = {
    "Closed generalist": {
        "gpt_5_5",
        "claude_fable_5",
        "gemini_3_1_pro",
        "grok_4_3",
        "qwen_3_7_plus",
        "glm_5v_turbo",
    },
    "Open generalist": {
        "gemma_4_31b",
        "llama_4_maverick",
        "mistral_large_3_2512",
        "nemotron_3_omni",
        "minimax_m3",
        "internvl3_5_8b",
    },
    "Open medical": {
        "medgemma_1_5_4b",
        "octomed_7b",
        "lingshu_32b",
    },
}


def configure_idk_score(idk_score: int) -> None:
    if idk_score not in {0, 1}:
        raise AuditFailure(f"Unsupported IDK score: {idk_score}")
    global IDK_SCORE, LIKERT_LEGEND_LABELS, SCORE1000_BAR_FOOTER_LINES, FOOTER_SCORE1000_NOTE
    IDK_SCORE = idk_score
    LIKERT_LEGEND_LABELS = likert_legend_labels(idk_score)
    SCORE1000_BAR_FOOTER_LINES = score1000_bar_footer_lines(idk_score)
    FOOTER_SCORE1000_NOTE = score1000_footer_note(idk_score)
    for spec in VARIANT_FILE_SPECS.values():
        if spec.get("use_variant_footer"):
            spec["footer_lines"] = SCORE1000_BAR_FOOTER_LINES


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


def score1000_bar_reader_key(reader_label: str) -> str:
    try:
        return SCORE1000_BAR_READER_KEYS[reader_label]
    except KeyError as exc:
        raise AuditFailure(f"Missing Score2000 bar reader key for {reader_label!r}") from exc


def count_label(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f"{value:.1f}"


def score_label(row: dict[str, str]) -> str:
    return count_label(score2000_value(row))


def score2000_value(row: dict[str, str]) -> float:
    value = str(row.get("score2000", "")).strip()
    if value:
        return float(value)
    return float(row["final_score1000"]) + SCORE2000_SHIFT


def display_name(row: dict[str, str]) -> str:
    return DISPLAY_NAMES.get(row["reader_label"], row["reader_label"])


def score1000_gap_data_number(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def expected_score_gap_overlay_metadata(
    rows: list[dict[str, str]],
    expected_labels: list[str],
    expected_bar_colors: dict[str, str],
    *,
    date_label: str,
) -> dict[str, object]:
    by_label = {row["reader_label"]: row for row in rows}
    selected_rows = [by_label[label] for label in expected_labels]
    human_rows = [row for row in selected_rows if row["reader_label"] == "Human Expert Baseline"]
    if len(human_rows) != 1:
        raise AuditFailure("Score gap overlay expected exactly one Human Expert Baseline row")
    ai_rows = [row for row in selected_rows if row["reader_type"] == "AI model"]
    if not ai_rows:
        raise AuditFailure("Score gap overlay expected at least one visible AI model row")
    top_ai_score = max(score2000_value(row) for row in ai_rows)
    top_ai_row = next(row for row in ai_rows if abs(score2000_value(row) - top_ai_score) < 1e-9)
    human_row = human_rows[0]
    human_score = score2000_value(human_row)
    gap_value = human_score - top_ai_score
    gap_abs_value = abs(gap_value)
    gap_rounded = int(gap_abs_value + 0.5)
    gap_direction = "Human-AI" if gap_value >= 0 else "AI-Human"
    return {
        "enabled": True,
        "human_label": human_row["reader_label"],
        "human_display_label": display_name(human_row),
        "human_score": human_score,
        "human_color": expected_bar_colors[human_row["reader_label"]],
        "top_ai_label": top_ai_row["reader_label"],
        "top_ai_display_label": display_name(top_ai_row),
        "top_ai_score": top_ai_score,
        "top_ai_color": expected_bar_colors[top_ai_row["reader_label"]],
        "gap_value": gap_value,
        "gap_abs_value": gap_abs_value,
        "gap_rounded": gap_rounded,
        "gap_direction": gap_direction,
        "date_label": date_label,
        "visible_label": f"{gap_rounded} point {gap_direction} gap: {date_label}",
    }


def score2000_expected_labels(rows: list[dict[str, str]], selected_labels: list[str]) -> list[str]:
    by_label = {row["reader_label"]: row for row in rows}
    missing = [label for label in selected_labels if label not in by_label]
    if missing:
        raise AuditFailure(f"Selected Score2000 labels are missing from source rows: {missing}")
    selected = [by_label[label] for label in selected_labels]
    return [row["reader_label"] for row in sorted(selected, key=lambda row: (-score2000_value(row), row["reader_label"]))]


NEUTRAL_STATUSES = {
    "abstention_idk_zero",
    "abstention_idk_typo_zero",
    "invalid_likert_zero",
    "technical_failure_zero",
}
MOJIBAKE_MARKERS = ["\ufffd", "Ã", "Â", "â€", "\ufeff"]
STALE_MARKERS = [
    "confidence_outcome_summary.csv",
    "qual_human200_weighted_source_master.csv",
    "panel_1_",
    "panel_4_",
    "panel_5_",
    "panel_6_",
    "panel_2_score1000_diverging_bar.svg",
    "panel_3_score1000_200_dot_strip.svg",
    "panel_3_score1000_100_dot_percentage_strip.svg",
    "Two Hundred Effective",
    "200 dots per row",
    "Two hundred-dot",
    "One Hundred Percentage Dots",
    "100 dots per row",
    "Deployment Risk",
    "hallucination",
    "Safety Shield",
    "hazard",
]


class AuditFailure(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest().upper()


def outcome_palette_colors(palette_key: str) -> dict[str, str]:
    return dict(OUTCOME_PALETTES[palette_key]["colors"])


def outcome_palette_metadata(palette_key: str) -> dict[str, object]:
    colors = outcome_palette_colors(palette_key)
    return {
        "key": palette_key,
        "name": OUTCOME_PALETTES[palette_key]["name"],
        "bin_order": BIN_COLUMNS,
        "legend_labels": LIKERT_LEGEND_LABELS,
        "colors": {key: colors[key] for key in BIN_COLUMNS},
    }


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def expected_source_csv_values(score_root: Path) -> set[str]:
    values = {rel(score_root / "score1000_scored_rows.csv")}
    if IDK_SCORE == 1:
        values.add("likert5_score1000/score1000_scored_rows.csv")
    return values


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise AuditFailure(f"Missing CSV: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def clean_text(value: object) -> str:
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def frac(value: object) -> Fraction:
    return Fraction(clean_text(value) or "0")


def close_enough(actual: object, expected: object, tolerance: float = 1e-4) -> bool:
    return abs(float(actual) - float(expected)) <= tolerance


def parse_likert(value: str) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if not number.is_integer():
        return None
    return int(number)


def bin_for_row(row: dict[str, str]) -> str:
    status = row["score1000_status"]
    if status in NEUTRAL_STATUSES:
        return "neutral"
    likert = parse_likert(row["score1000_likert_int"])
    if likert not in {0, 1, 2, 3, 4}:
        raise AuditFailure(f"Valid scored row has invalid Likert: {row['score1000_likert_int']}")
    if status == "valid_likert_correct":
        return f"correct_l{likert}"
    if status == "valid_likert_wrong":
        return f"wrong_l{likert}"
    raise AuditFailure(f"Unexpected status: {status}")


def display_key(row: dict[str, str]) -> tuple[str, str]:
    if row["score1000_row_kind"] == "human_comparator":
        return ("Human comparator", row["score1000_group"])
    return ("AI model", row["candidate"])


def category_for_row(row: dict[str, str]) -> str:
    if row["reader_type"] == "Human comparator":
        return "Human Expert Baseline"
    label = row["reader_label"]
    for category, labels in CATEGORY_MODEL_GROUPS.items():
        if label in labels:
            return category
    raise AuditFailure(f"Unmapped model category for {label!r}")


def grouped_row_labels(rows: list[dict[str, str]]) -> list[str]:
    labels: list[str] = []
    for category in CATEGORY_ORDER:
        labels.extend(row["reader_label"] for row in rows if category_for_row(row) == category)
    return labels


def expected_bins(scored_rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, Fraction]]:
    out: dict[tuple[str, str], dict[str, Fraction]] = {}
    for row in scored_rows:
        key = display_key(row)
        out.setdefault(key, {column: Fraction(0, 1) for column in BIN_COLUMNS})
        out[key][bin_for_row(row)] += Fraction(1, int(row["score1000_n_readers_in_group"]))
    return out


def audit_csv(score_root: Path, out_dir: Path) -> list[dict[str, str]]:
    rows = read_csv(out_dir / "score1000_panel23_bins.csv")
    scored = read_csv(score_root / "score1000_scored_rows.csv")
    if len(rows) != EXPECTED_COMPARATORS:
        raise AuditFailure(f"Expected {EXPECTED_COMPARATORS} panel summary rows, got {len(rows)}")
    expected = expected_bins(scored)
    for row in rows:
        key = (row["reader_type"], row["reader_label"])
        if key not in expected:
            raise AuditFailure(f"Unexpected panel row: {key}")
        total = sum((frac(row[column]) for column in BIN_COLUMNS), Fraction(0, 1))
        if not close_enough(total, 200):
            raise AuditFailure(f"{key}: bins sum to {total}, expected 200")
        if not close_enough(row["effective_cases"], 200):
            raise AuditFailure(f"{key}: effective_cases is not 200")
        if str(row.get("score2000", "")).strip() == "":
            raise AuditFailure(f"{key}: score2000 is missing")
        if not close_enough(row["score2000"], float(row["final_score1000"]) + SCORE2000_SHIFT):
            raise AuditFailure(f"{key}: score2000 must equal final_score1000 + 1000")
        correct = sum((frac(row[column]) for column in CORRECT_BINS), Fraction(0, 1))
        wrong = sum((frac(row[column]) for column in WRONG_BINS), Fraction(0, 1))
        if not close_enough(row["correct_total"], correct):
            raise AuditFailure(f"{key}: correct_total mismatch")
        if not close_enough(row["wrong_total"], wrong):
            raise AuditFailure(f"{key}: wrong_total mismatch")
        if not close_enough(row["neutral_total"], row["neutral"]):
            raise AuditFailure(f"{key}: neutral_total mismatch")
        for column in BIN_COLUMNS:
            if not close_enough(row[column], expected[key][column]):
                raise AuditFailure(f"{key}: {column} expected {float(expected[key][column])}, got {row[column]}")
        dot_total = sum(int(float(row[column])) for column in DOT_COLUMNS)
        if dot_total != DOT_DISPLAY_TOTAL or int(float(row["dot_total"])) != DOT_DISPLAY_TOTAL:
            raise AuditFailure(f"{key}: expected {DOT_DISPLAY_TOTAL} display units, got {dot_total}/{row['dot_total']}")
    return rows


def scan_text(path: Path) -> None:
    raw = path.read_text(encoding="utf-8", errors="replace")
    for marker in MOJIBAKE_MARKERS:
        if marker in raw:
            raise AuditFailure(f"{path}: mojibake marker {marker!r}")
    for marker in STALE_MARKERS:
        if marker in raw:
            raise AuditFailure(f"{path}: stale marker {marker!r}")
    if IDK_SCORE == 0:
        for marker in ("IDK +1", "safe +1", "lands at +200", "baseline of +200", "\"I don't know\" scores +1"):
            if marker in raw:
                raise AuditFailure(f"{path}: stale IDK +1 marker {marker!r}")


def element_texts(root: ET.Element) -> list[str]:
    return ["".join(text.itertext()).strip() for text in root.findall(f".//{SVG_NS}text")]


def parse_svg(path: Path) -> tuple[ET.Element, dict[str, object]]:
    root = ET.parse(path).getroot()
    title = root.find(f"{SVG_NS}title")
    desc = root.find(f"{SVG_NS}desc")
    if title is None or not clean_text(title.text):
        raise AuditFailure(f"{path}: missing title")
    if desc is None or not clean_text(desc.text):
        raise AuditFailure(f"{path}: missing desc")
    metadata = root.find(f"{SVG_NS}metadata")
    if metadata is None:
        raise AuditFailure(f"{path}: missing metadata")
    payload = json.loads(html.unescape(metadata.text or ""))
    return root, payload


def audit_panel2_edge_justified(root: ET.Element, path: Path) -> None:
    if root.findall(f".//{SVG_NS}line[@class='centerline']"):
        raise AuditFailure(f"{path}: Panel 2 must be edge-justified, not centerline anchored")
    clip_paths = root.findall(f".//{SVG_NS}clipPath")
    if len(clip_paths) != EXPECTED_COMPARATORS:
        raise AuditFailure(f"{path}: expected {EXPECTED_COMPARATORS} row clip paths, got {len(clip_paths)}")
    for clip_path in clip_paths:
        clip_id = clip_path.get("id", "")
        if not clip_id.startswith("panel2-row-"):
            raise AuditFailure(f"{path}: unexpected Panel 2 clip path id {clip_id!r}")
        clip_rect = clip_path.find(f"{SVG_NS}rect")
        if clip_rect is None:
            raise AuditFailure(f"{path}: row clip path missing rounded rect")
        if float(clip_rect.get("rx", "0")) <= 0:
            raise AuditFailure(f"{path}: row clip path must provide rounded outer corners")
    tracks = root.findall(f".//{SVG_NS}rect[@class='track']")
    if len(tracks) != EXPECTED_COMPARATORS:
        raise AuditFailure(f"{path}: expected {EXPECTED_COMPARATORS} row tracks, got {len(tracks)}")
    track_by_y = {round(float(track.get("y", "0")) + 7, 1): track for track in tracks}
    segments_by_y: dict[float, list[ET.Element]] = {}
    outlines = root.findall(f".//{SVG_NS}rect[@class='bar-outline']")
    if len(outlines) != EXPECTED_COMPARATORS:
        raise AuditFailure(f"{path}: expected {EXPECTED_COMPARATORS} Panel 2 row outlines, got {len(outlines)}")
    for segment in root.findall(f".//{SVG_NS}rect"):
        if segment.get("data-bin") in BIN_COLUMNS:
            if float(segment.get("rx", "0")) != 0:
                raise AuditFailure(f"{path}: internal segment {segment.get('data-bin')} must have rx=0")
            if (segment.get("stroke") or "").lower() != "none":
                raise AuditFailure(f"{path}: internal segment {segment.get('data-bin')} must be unstroked")
            y = round(float(segment.get("y", "0")), 1)
            segments_by_y.setdefault(y, []).append(segment)
    for y, track in track_by_y.items():
        segments = segments_by_y.get(y)
        if not segments:
            raise AuditFailure(f"{path}: no bar segments for y={y}")
        track_x = float(track.get("x", "0"))
        track_w = float(track.get("width", "0"))
        left = min(float(segment.get("x", "0")) for segment in segments)
        right = max(float(segment.get("x", "0")) + float(segment.get("width", "0")) for segment in segments)
        total_w = sum(float(segment.get("width", "0")) for segment in segments)
        if abs(left - track_x) > 0.2:
            raise AuditFailure(f"{path}: row y={y} first segment is not justified to left edge")
        if abs(right - (track_x + track_w)) > 2.0:
            raise AuditFailure(f"{path}: row y={y} last segment is not justified to right edge")
        if abs(total_w - track_w) > 2.0:
            raise AuditFailure(f"{path}: row y={y} segment widths do not span the full track")


def audit_panel3_percentage_marks(root: ET.Element, path: Path) -> None:
    if root.findall(f".//{SVG_NS}circle"):
        raise AuditFailure(f"{path}: Panel 3 must use barcode capsule bars, not circle dots")
    units = root.findall(f".//{SVG_NS}rect[@class='barcode-unit']")
    if len(units) != EXPECTED_PANEL3_UNITS:
        raise AuditFailure(f"{path}: expected {EXPECTED_PANEL3_UNITS} barcode units, got {len(units)}")
    rows: dict[str, set[float]] = {}
    for unit in units:
        row = unit.get("data-row", "")
        rows.setdefault(row, set()).add(round(float(unit.get("y", "0")), 1))
        if float(unit.get("rx", "0")) <= 0:
            raise AuditFailure(f"{path}: barcode unit for row {row!r} must have rounded capsule ends")
    if len(rows) != EXPECTED_COMPARATORS:
        raise AuditFailure(f"{path}: expected barcode units for {EXPECTED_COMPARATORS} rows, got {len(rows)}")
    for row, y_positions in rows.items():
        if len(y_positions) != 1:
            raise AuditFailure(f"{path}: row {row!r} wraps across {len(y_positions)} y-positions")


def audit_b3_legend(
    root: ET.Element,
    path: Path,
    expected_id: int,
    expected_colors: dict[str, str] | None = None,
) -> None:
    expected_colors = expected_colors or outcome_palette_colors("current")
    legend_bins = [rect for rect in root.findall(f".//{SVG_NS}rect") if rect.get("data-legend-bin")]
    observed_bins = [rect.get("data-legend-bin", "") for rect in legend_bins]
    if observed_bins != BIN_COLUMNS:
        raise AuditFailure(f"{path}: B3 legend bins mismatch: {observed_bins}")
    for rect in legend_bins:
        key = rect.get("data-legend-bin", "")
        expected_fill = expected_colors[key].lower()
        actual_fill = (rect.get("fill") or "").lower()
        if actual_fill != expected_fill:
            raise AuditFailure(f"{path}: B3 legend {key} fill {actual_fill} != expected {expected_fill}")
    outlines = root.findall(f".//{SVG_NS}rect[@class='legend-outline']")
    if len(outlines) != 1:
        raise AuditFailure(f"{path}: expected one B3 legend outline")
    legend_outline = outlines[0]
    panel_key = f"panel{expected_id}"
    if legend_outline.get("data-legend-panel") != panel_key:
        raise AuditFailure(f"{path}: B3 legend panel key mismatch")
    for rect in legend_bins:
        if rect.get("data-legend-panel") != panel_key:
            raise AuditFailure(f"{path}: B3 legend bin panel key mismatch")
    tracks = root.findall(f".//{SVG_NS}rect[@class='track']")
    if not tracks:
        raise AuditFailure(f"{path}: no data tracks available for B3 legend alignment check")
    data_x = float(tracks[0].get("x", "0"))
    data_w = float(tracks[0].get("width", "0"))
    legend_x = float(legend_outline.get("x", "0"))
    legend_w = float(legend_outline.get("width", "0"))
    if abs(legend_x - data_x) > 0.2 or abs(legend_w - data_w) > 0.2:
        raise AuditFailure(
            f"{path}: B3 legend span x={legend_x} w={legend_w} does not match data span x={data_x} w={data_w}"
        )
    legend_y = float(legend_outline.get("y", "0"))
    legend_h = float(legend_outline.get("height", "0"))
    legend_bottom = legend_y + legend_h
    for axis_line in root.findall(f".//{SVG_NS}line[@class='axis']"):
        x_values = [float(axis_line.get(attr, "0")) for attr in ("x1", "x2")]
        y_values = [float(axis_line.get(attr, "0")) for attr in ("y1", "y2")]
        overlaps_legend = min(x_values) <= legend_x + legend_w and max(x_values) >= legend_x
        below_bar = min(y_values) >= legend_bottom and max(y_values) <= legend_bottom + 40
        if overlaps_legend and below_bar:
            raise AuditFailure(f"{path}: B3 legend bracket/tick line is present")
    texts = ["".join(text.itertext()).strip() for text in root.findall(f".//{SVG_NS}text")]
    required = [
        "Correct, by confidence",
        "I don't know",
        "Wrong, by confidence",
        "L4 high confidence",
        "L0 low confidence",
    ]
    for label in required:
        if label not in texts:
            raise AuditFailure(f"{path}: B3 legend missing {label!r}")
    stale = {"Correct L4", "Correct L2", "Correct L0", "Wrong L0", "Wrong L2", "Wrong L4"}
    found_stale = sorted(stale.intersection(texts))
    if found_stale:
        raise AuditFailure(f"{path}: stale sampled legend labels present: {found_stale}")


def audit_visible_row_identity(root: ET.Element, path: Path, score_header: str = "Score2000") -> None:
    texts = element_texts(root)
    joined = "\n".join(texts)
    if "n=200" in joined:
        raise AuditFailure(f"{path}: visible row-level n=200 metadata is present")
    raw_labels = sorted(label for label in DISPLAY_NAMES if label in texts)
    if raw_labels:
        raise AuditFailure(f"{path}: visible raw underscore model labels present: {raw_labels}")
    missing = sorted(display for display in DISPLAY_NAMES.values() if display not in texts)
    if missing:
        raise AuditFailure(f"{path}: formatted display labels missing: {missing}")
    for required in ["Human Expert Baseline", score_header, "Reader / model"]:
        if required not in texts:
            raise AuditFailure(f"{path}: required visible row identity label missing: {required!r}")


def audit_score1000_rule_metadata(payload: dict[str, object], path: Path) -> None:
    rule = payload.get("score1000_rule")
    if rule is None and IDK_SCORE == 1:
        return
    if not isinstance(rule, dict):
        raise AuditFailure(f"{path}: missing score1000_rule metadata")
    if int(rule.get("idk_score", -1)) != IDK_SCORE:
        raise AuditFailure(f"{path}: IDK score metadata mismatch")
    if int(rule.get("all_idk_baseline", -1)) != IDK_SCORE * 200:
        raise AuditFailure(f"{path}: all-IDK baseline metadata mismatch")


def audit_score2000_rule_metadata(payload: dict[str, object], path: Path) -> None:
    rule = payload.get("score2000_rule")
    if not isinstance(rule, dict):
        raise AuditFailure(f"{path}: missing score2000_rule metadata")
    if rule.get("formula") != "score2000 = final_score1000 + 1000":
        raise AuditFailure(f"{path}: score2000 formula metadata mismatch")
    if rule.get("display_range") != [0, 2000]:
        raise AuditFailure(f"{path}: score2000 display range metadata mismatch")
    if rule.get("source_range") != [-1000, 1000]:
        raise AuditFailure(f"{path}: score2000 source range metadata mismatch")
    if rule.get("rank_preserving") is not True:
        raise AuditFailure(f"{path}: score2000 rank-preserving metadata mismatch")


def audit_svg(score_root: Path, out_dir: Path, rows: list[dict[str, str]]) -> None:
    by_label = {row["reader_label"]: row for row in rows}
    expected_sources = expected_source_csv_values(score_root)
    for expected_id, filename in [(2, PANEL_FILES[0]), (3, PANEL_FILES[1])]:
        path = out_dir / filename
        root, payload = parse_svg(path)
        if int(payload.get("panel_id", 0)) != expected_id:
            raise AuditFailure(f"{path}: panel_id mismatch")
        if payload.get("source_csv") not in expected_sources:
            raise AuditFailure(f"{path}: source_csv mismatch")
        audit_score1000_rule_metadata(payload, path)
        audit_score2000_rule_metadata(payload, path)
        if str(payload.get("source_master_sha256", "")).upper() != EXPECTED_SOURCE_SHA256:
            raise AuditFailure(f"{path}: source master SHA mismatch")
        payload_rows = payload.get("rows")
        if not isinstance(payload_rows, list) or len(payload_rows) != EXPECTED_COMPARATORS:
            raise AuditFailure(f"{path}: metadata row count mismatch")
        for item in payload_rows:
            if not isinstance(item, dict):
                raise AuditFailure(f"{path}: metadata row is not an object")
            label = str(item.get("reader_label", ""))
            row = by_label.get(label)
            if row is None:
                raise AuditFailure(f"{path}: metadata row {label!r} not found in summary")
            if not close_enough(item.get("score2000", -999), row["score2000"]):
                raise AuditFailure(f"{path}: metadata {label} score2000 mismatch")
            bins = item.get("bins")
            dot_bins = item.get("dot_bins")
            if not isinstance(bins, dict) or not isinstance(dot_bins, dict):
                raise AuditFailure(f"{path}: metadata missing bins")
            for column in BIN_COLUMNS:
                if not close_enough(bins.get(column, -999), row[column]):
                    raise AuditFailure(f"{path}: metadata {label} {column} mismatch")
                if int(float(dot_bins.get(column, -999))) != int(float(row[f"dot_{column}"])):
                    raise AuditFailure(f"{path}: metadata {label} dot_{column} mismatch")
        if expected_id == 2:
            audit_panel2_edge_justified(root, path)
        if expected_id == 3:
            audit_panel3_percentage_marks(root, path)
        audit_b3_legend(root, path, expected_id)
        audit_visible_row_identity(root, path)


def audit_variant_category_key(root: ET.Element, path: Path, filename: str) -> None:
    texts = element_texts(root)
    expected_category_colors = expected_variant_category_colors(filename)
    for category, color in expected_category_colors.items():
        if category not in texts:
            raise AuditFailure(f"{path}: category key missing {category!r}")
        swatches = root.findall(f".//{SVG_NS}rect[@data-category-key='{category}']")
        if len(swatches) != 1:
            raise AuditFailure(f"{path}: expected one category swatch for {category}, got {len(swatches)}")
        if (swatches[0].get("fill") or "").lower() != color:
            raise AuditFailure(f"{path}: category swatch color mismatch for {category}")
        actual_x = float(swatches[0].get("x", "nan"))
        expected_x = expected_variant_key_x(filename, category)
        if abs(actual_x - expected_x) > 0.1:
            raise AuditFailure(
                f"{path}: category key x-position for {category} is {actual_x}, expected {expected_x}"
            )
        key_texts = [
            elem
            for elem in root.findall(f".//{SVG_NS}text")
            if elem.get("data-category-key") == category
        ]
        if len(key_texts) != 1:
            raise AuditFailure(f"{path}: expected one category key text for {category}, got {len(key_texts)}")
        if color not in (key_texts[0].get("style") or "").lower():
            raise AuditFailure(f"{path}: category key text color mismatch for {category}")


def audit_category_color_scope(
    root: ET.Element,
    path: Path,
    expected_colors: dict[str, str] | None = None,
) -> None:
    expected_colors = expected_colors or outcome_palette_colors("current")
    for rect in root.findall(f".//{SVG_NS}rect"):
        fill = (rect.get("fill") or "").lower()
        if rect.get("data-bin") in BIN_COLUMNS:
            key = rect.get("data-bin", "")
            expected_fill = expected_colors[key].lower()
            if fill != expected_fill:
                raise AuditFailure(f"{path}: outcome bin {key} has fill {fill}, expected {expected_fill}")
            continue
        if rect.get("data-legend-bin") in BIN_COLUMNS:
            key = rect.get("data-legend-bin", "")
            expected_fill = expected_colors[key].lower()
            if fill != expected_fill:
                raise AuditFailure(f"{path}: outcome legend bin {key} has fill {fill}, expected {expected_fill}")
            continue
        if fill in ALL_CATEGORY_COLOR_VALUES and rect.get("data-category-key") is None:
            raise AuditFailure(f"{path}: category color {fill} used on non-key rectangle")
    for elem in root.iter():
        style = elem.get("style") or ""
        for color in ALL_CATEGORY_COLOR_VALUES:
            if color in style.lower():
                is_scoped_text = elem.tag == f"{SVG_NS}text" and any(
                    elem.get(attr)
                    for attr in ("data-category", "data-category-key", "data-category-header", "data-score-category")
                )
                if not is_scoped_text:
                    raise AuditFailure(f"{path}: category color {color} used in unscoped style attribute")
    if root.findall(f".//{SVG_NS}circle"):
        raise AuditFailure(f"{path}: unexpected circle marker present")


def audit_variant_outcome_palette(root: ET.Element, payload: dict[str, object], path: Path, filename: str) -> None:
    spec = VARIANT_FILE_SPECS[filename]
    palette_key = str(spec["palette_key"])
    expected_metadata = outcome_palette_metadata(palette_key)
    expected_colors = outcome_palette_colors(palette_key)
    actual_metadata = payload.get("outcome_palette")
    if not isinstance(actual_metadata, dict):
        raise AuditFailure(f"{path}: metadata missing outcome_palette")
    if actual_metadata.get("key") != palette_key:
        raise AuditFailure(f"{path}: outcome palette key {actual_metadata.get('key')} != expected {palette_key}")
    if actual_metadata.get("name") != expected_metadata["name"]:
        raise AuditFailure(f"{path}: outcome palette name mismatch")
    if actual_metadata.get("bin_order") != BIN_COLUMNS:
        raise AuditFailure(f"{path}: outcome palette bin order mismatch")
    if actual_metadata.get("legend_labels") != LIKERT_LEGEND_LABELS:
        raise AuditFailure(f"{path}: outcome palette legend label order mismatch")
    actual_colors = actual_metadata.get("colors")
    if not isinstance(actual_colors, dict):
        raise AuditFailure(f"{path}: outcome palette colors missing")
    for key in BIN_COLUMNS:
        expected_fill = expected_colors[key].lower()
        if str(actual_colors.get(key, "")).lower() != expected_fill:
            raise AuditFailure(f"{path}: metadata color for {key} is {actual_colors.get(key)}, expected {expected_fill}")
    expected_category_colors = expected_variant_category_colors(filename)
    actual_category_colors = payload.get("category_colors")
    if actual_category_colors != expected_category_colors:
        raise AuditFailure(f"{path}: category color metadata mismatch: {actual_category_colors} != {expected_category_colors}")

    legend_bins = [rect for rect in root.findall(f".//{SVG_NS}rect") if rect.get("data-legend-bin")]
    if [rect.get("data-legend-bin", "") for rect in legend_bins] != BIN_COLUMNS:
        raise AuditFailure(f"{path}: legend bin order changed")
    neutral_index = BIN_COLUMNS.index("neutral")
    wrong_l0_index = BIN_COLUMNS.index("wrong_l0")
    if neutral_index != 5 or wrong_l0_index != 6:
        raise AuditFailure(f"{path}: neutral/IDK is not immediately before wrong_l0")
    neutral_legend_fill = (legend_bins[neutral_index].get("fill") or "").lower()
    if neutral_legend_fill != expected_colors["neutral"].lower():
        raise AuditFailure(f"{path}: IDK/neutral legend fill {neutral_legend_fill} != expected {expected_colors['neutral']}")

    for rect in root.findall(f".//{SVG_NS}rect"):
        role_key = rect.get("data-bin") or rect.get("data-legend-bin")
        if role_key in BIN_COLUMNS:
            expected_fill = expected_colors[role_key].lower()
            actual_fill = (rect.get("fill") or "").lower()
            if actual_fill != expected_fill:
                raise AuditFailure(f"{path}: {role_key} fill {actual_fill} != expected {expected_fill}")
            if filename in NEW_NO_GRAY_VARIANT_FILES and actual_fill == "#c7ccd1":
                raise AuditFailure(f"{path}: new variant contains forbidden gray #c7ccd1 in outcome bins")


def audit_variant_text_colors(
    root: ET.Element,
    path: Path,
    rows: list[dict[str, str]],
    *,
    show_group_headers: bool,
    color_row_names: bool,
    color_scores: bool,
    expected_category_colors: dict[str, str],
) -> None:
    if show_group_headers:
        for category, color in expected_category_colors.items():
            headers = [
                elem
                for elem in root.findall(f".//{SVG_NS}text")
                if elem.get("data-category-header") == category
            ]
            if len(headers) != 1:
                raise AuditFailure(f"{path}: expected one group header for {category}, got {len(headers)}")
            if color not in (headers[0].get("style") or "").lower():
                raise AuditFailure(f"{path}: group header color mismatch for {category}")
        row_name_colored = [
            elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("data-category")
        ]
        if row_name_colored:
            raise AuditFailure(f"{path}: grouped variant should color group headers, not individual row names")
    else:
        headers = [
            elem
            for elem in root.findall(f".//{SVG_NS}text")
            if elem.get("data-category-header")
        ]
        if headers:
            raise AuditFailure(f"{path}: group headers should be hidden, got {len(headers)}")

    for row in rows:
        category = category_for_row(row)
        expected_color = expected_category_colors[category]
        display = DISPLAY_NAMES.get(row["reader_label"], row["reader_label"])
        matches = [
            elem
            for elem in root.findall(f".//{SVG_NS}text")
            if "".join(elem.itertext()).strip() == display and elem.get("data-category") == category
        ]
        if color_row_names:
            if len(matches) != 1:
                raise AuditFailure(f"{path}: expected one colored row name for {display}, got {len(matches)}")
            if expected_color not in (matches[0].get("style") or "").lower():
                raise AuditFailure(f"{path}: row name color mismatch for {display}")
        elif matches:
            raise AuditFailure(f"{path}: row name should not be category-colored for {display}")

        score_matches = [
            elem
            for elem in root.findall(f".//{SVG_NS}text")
            if "".join(elem.itertext()).strip() == score_label(row)
            and elem.get("data-reader-label") == row["reader_label"]
            and elem.get("data-score-category") == category
        ]
        if color_scores:
            if len(score_matches) != 1:
                raise AuditFailure(
                    f"{path}: expected one category-colored score for {display}, got {len(score_matches)}"
                )
            if expected_color not in (score_matches[0].get("style") or "").lower():
                raise AuditFailure(f"{path}: score color mismatch for {display}")
        elif score_matches:
            raise AuditFailure(f"{path}: score should not be category-colored for {display}")


def text_y_by_label(root: ET.Element, label: str) -> list[float]:
    values: list[float] = []
    for elem in root.findall(f".//{SVG_NS}text"):
        if "".join(elem.itertext()).strip() == label:
            values.append(float(elem.get("y", "0")))
    return values


def audit_variant_header_spacing(root: ET.Element, path: Path, filename: str, show_group_headers: bool) -> None:
    score_headers = [
        elem
        for elem in root.findall(f".//{SVG_NS}text")
        if "".join(elem.itertext()).strip() == "Score"
    ]
    if len(score_headers) != 1:
        raise AuditFailure(f"{path}: expected one Score header, got {len(score_headers)}")
    score_y = float(score_headers[0].get("y", "0"))
    score_x = float(score_headers[0].get("x", "nan"))
    expected_score_x = expected_variant_score_x(filename)
    if abs(score_x - expected_score_x) > 0.1:
        raise AuditFailure(f"{path}: Score header x={score_x}, expected {expected_score_x}")
    reader_headers = [
        elem
        for elem in root.findall(f".//{SVG_NS}text")
        if "".join(elem.itertext()).strip() == "Reader / model"
    ]
    if len(reader_headers) != 1:
        raise AuditFailure(f"{path}: expected one Reader / model header, got {len(reader_headers)}")
    expected_name_x = expected_variant_name_x(filename)
    reader_x = float(reader_headers[0].get("x", "nan"))
    if abs(reader_x - expected_name_x) > 0.1:
        raise AuditFailure(f"{path}: Reader / model header x={reader_x}, expected {expected_name_x}")
    if score_y < VARIANT_HEADER_MIN_Y:
        raise AuditFailure(f"{path}: Score header y={score_y} is still too high/tight")
    score_labels = [
        elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("class") == "variant-score-label"
    ]
    if len(score_labels) != EXPECTED_COMPARATORS:
        raise AuditFailure(f"{path}: expected {EXPECTED_COMPARATORS} score labels, got {len(score_labels)}")
    for elem in score_labels:
        actual_x = float(elem.get("x", "nan"))
        if abs(actual_x - expected_score_x) > 0.1:
            raise AuditFailure(f"{path}: score label x={actual_x}, expected {expected_score_x}")
    row_name_labels = [
        elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("class") == "variant-row-label"
    ]
    if len(row_name_labels) != EXPECTED_COMPARATORS:
        raise AuditFailure(f"{path}: expected {EXPECTED_COMPARATORS} reader/model labels, got {len(row_name_labels)}")
    for elem in row_name_labels:
        actual_x = float(elem.get("x", "nan"))
        if abs(actual_x - expected_name_x) > 0.1:
            raise AuditFailure(f"{path}: reader/model label x={actual_x}, expected {expected_name_x}")
    count_labels = [
        elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("class") == "variant-count-label"
    ]
    if count_labels:
        expected_count_labels = 2 * EXPECTED_COMPARATORS
        if len(count_labels) != expected_count_labels:
            raise AuditFailure(f"{path}: expected {expected_count_labels} outside count labels, got {len(count_labels)}")
        expected_left_count_x = expected_variant_chart_x(filename) - 18
        expected_right_count_x = expected_variant_chart_x(filename) + expected_variant_chart_w(filename) + 18
        left_count_labels = [elem for elem in count_labels if elem.get("text-anchor") == "end"]
        right_count_labels = [elem for elem in count_labels if elem.get("text-anchor") == "start"]
        if len(left_count_labels) != EXPECTED_COMPARATORS or len(right_count_labels) != EXPECTED_COMPARATORS:
            raise AuditFailure(
                f"{path}: expected {EXPECTED_COMPARATORS} left and {EXPECTED_COMPARATORS} right count labels, got "
                f"{len(left_count_labels)} left and {len(right_count_labels)} right"
            )
        for elem in left_count_labels:
            actual_x = float(elem.get("x", "nan"))
            if abs(actual_x - expected_left_count_x) > 0.1:
                raise AuditFailure(f"{path}: left count label x={actual_x}, expected {expected_left_count_x}")
        for elem in right_count_labels:
            actual_x = float(elem.get("x", "nan"))
            if abs(actual_x - expected_right_count_x) > 0.1:
                raise AuditFailure(f"{path}: right count label x={actual_x}, expected {expected_right_count_x}")
    if show_group_headers:
        group_y_values = text_y_by_label(root, "Human Expert Baseline")
        group_header_y = max(group_y_values) if group_y_values else 0
        if group_header_y - score_y < 48:
            raise AuditFailure(f"{path}: first group header gap {group_header_y - score_y:.1f}px is below 48px")


def audit_variant_logos(root: ET.Element, payload: dict[str, object], path: Path) -> None:
    chart_meta = payload.get("score1000_bar_chart")
    top_logo_scale = 1.0
    if isinstance(chart_meta, dict):
        top_logo_scale = float(chart_meta.get("top_logo_scale", 1.0))
    images = [
        elem
        for elem in root.findall(f".//{SVG_NS}image")
        if elem.get("class") == "top-logo" and elem.get("data-logo")
    ]
    observed_roles = {str(elem.get("data-logo")) for elem in images}
    expected_roles = set(VARIANT_LOGO_ASSETS)
    if observed_roles != expected_roles:
        raise AuditFailure(f"{path}: top logo roles mismatch: {observed_roles}")
    for elem in images:
        role = str(elem.get("data-logo"))
        expected = VARIANT_LOGO_LAYOUT[role]
        expected_width = expected["width"] * top_logo_scale
        expected_height = expected["height"] * top_logo_scale
        expected_x = expected["x"]
        if role == "right-lab-logo":
            expected_x = expected["x"] + expected["width"] - expected_width
        expected_values = {
            "x": expected_x,
            "y": expected["y"],
            "width": expected_width,
            "height": expected_height,
        }
        for attr, expected_value in expected_values.items():
            actual = float(elem.get(attr, "nan"))
            if abs(actual - expected_value) > 0.1:
                raise AuditFailure(f"{path}: {role} {attr}={actual}, expected {expected_value}")
        href = elem.get("href") or elem.get("{http://www.w3.org/1999/xlink}href") or ""
        if not href.startswith("data:image/"):
            raise AuditFailure(f"{path}: {role} is not embedded as a data image URI")

    metadata_logos = payload.get("logos")
    if not isinstance(metadata_logos, list):
        raise AuditFailure(f"{path}: metadata missing logo list")
    by_role = {str(item.get("role")): item for item in metadata_logos if isinstance(item, dict)}
    if set(by_role) != expected_roles:
        raise AuditFailure(f"{path}: metadata logo roles mismatch: {set(by_role)}")
    for role, asset_path in VARIANT_LOGO_ASSETS.items():
        item = by_role[role]
        if str(item.get("source")) != rel(asset_path):
            raise AuditFailure(f"{path}: metadata source mismatch for {role}")
        if str(item.get("sha256", "")).upper() != sha256_file(asset_path):
            raise AuditFailure(f"{path}: metadata logo SHA mismatch for {role}")


def audit_variant_figure_title(
    root: ET.Element,
    path: Path,
    expected_x: float = 1800.0,
    expected_y: float = EXPECTED_FIGURE_TITLE_Y,
) -> None:
    figure_titles = [
        elem
        for elem in root.findall(f".//{SVG_NS}text")
        if elem.get("class") == "figure-title" and "".join(elem.itertext()).strip() == EXPECTED_FIGURE_TITLE
    ]
    if len(figure_titles) != 1:
        raise AuditFailure(f"{path}: expected one visible figure title {EXPECTED_FIGURE_TITLE!r}, got {len(figure_titles)}")
    figure_title_x = float(figure_titles[0].get("x", "nan"))
    figure_title_y = float(figure_titles[0].get("y", "nan"))
    if abs(figure_title_x - expected_x) > 0.1:
        raise AuditFailure(
            f"{path}: figure title x must be {expected_x:g}, got {figure_title_x:g}"
        )
    if abs(figure_title_y - expected_y) > 0.1:
        raise AuditFailure(
            f"{path}: figure title y must be {expected_y:g}, got {figure_title_y:g}"
        )


def audit_variant_panel_title(root: ET.Element, path: Path) -> None:
    doc_title = root.find(f"{SVG_NS}title")
    if doc_title is None or "".join(doc_title.itertext()).strip() != EXPECTED_PANEL2_TITLE:
        raise AuditFailure(f"{path}: SVG title must be {EXPECTED_PANEL2_TITLE!r}")
    audit_variant_figure_title(root, path)
    visible_titles = [
        elem
        for elem in root.findall(f".//{SVG_NS}text")
        if elem.get("class") == "title" and "".join(elem.itertext()).strip() == EXPECTED_PANEL2_TITLE
    ]
    if len(visible_titles) != 1:
        raise AuditFailure(f"{path}: expected one visible panel title {EXPECTED_PANEL2_TITLE!r}, got {len(visible_titles)}")
    title_y = float(visible_titles[0].get("y", "nan"))
    expected_title_y = 234 + VARIANT_CONTENT_Y_SHIFT
    if abs(title_y - expected_title_y) > 0.1:
        raise AuditFailure(f"{path}: visible panel title y={title_y}, expected {expected_title_y}")


def css_fills(root: ET.Element, selector: str) -> list[str]:
    fills: list[str] = []
    for style_elem in root.findall(f".//{SVG_NS}style"):
        css = "".join(style_elem.itertext())
        for line in css.splitlines():
            stripped = line.strip().lower()
            if not stripped.startswith(f"{selector.lower()} {{"):
                continue
            for chunk in stripped.split(";"):
                chunk = chunk.strip()
                if chunk.startswith("fill:"):
                    fills.append(chunk.split(":", 1)[1].strip())
    return fills


def audit_variant_text_theme(root: ET.Element, payload: dict[str, object], path: Path, filename: str) -> None:
    expected_text_colors = expected_variant_text_colors(filename)
    actual_text_colors = payload.get("text_colors")
    if expected_text_colors is None:
        if actual_text_colors is not None:
            raise AuditFailure(f"{path}: unexpected text_colors metadata")
        return
    if actual_text_colors != expected_text_colors:
        raise AuditFailure(f"{path}: text color metadata mismatch: {actual_text_colors} != {expected_text_colors}")

    text_fill = expected_text_colors["text"].lower()
    figure_fill = expected_text_colors["figure_title"].lower()
    for selector, expected_fill in {
        ".figure-title": figure_fill,
        ".title": text_fill,
        ".variant-subtitle": text_fill,
        ".variant-axis-label": text_fill,
        ".variant-row-label": text_fill,
        ".variant-score-label": text_fill,
        ".variant-count-label": text_fill,
        ".variant-confidence-label": text_fill,
        ".variant-legend-label": text_fill,
        ".variant-group-label": text_fill,
        ".variant-micro": text_fill,
    }.items():
        fills = css_fills(root, selector)
        if not fills or any(fill != expected_fill for fill in fills):
            raise AuditFailure(f"{path}: {selector} CSS fills {fills}, expected {expected_fill}")

    for selector, expected_fill in {
        ".variant-bar-label": "#202124",
        ".variant-bar-label-white": "#ffffff",
    }.items():
        fills = css_fills(root, selector)
        if not fills or any(fill != expected_fill for fill in fills):
            raise AuditFailure(f"{path}: in-bar {selector} CSS fills {fills}, expected {expected_fill}")


def audit_variant_axis_legend_spacing(root: ET.Element, path: Path, filename: str) -> None:
    expected_chart_x = expected_variant_chart_x(filename)
    expected_chart_w = expected_variant_chart_w(filename)
    axis_candidates = []
    for elem in root.findall(f".//{SVG_NS}line"):
        if elem.get("class") != "axis":
            continue
        x1 = float(elem.get("x1", "nan"))
        x2 = float(elem.get("x2", "nan"))
        y1 = float(elem.get("y1", "nan"))
        y2 = float(elem.get("y2", "nan"))
        if (
            abs(x1 - expected_chart_x) <= 0.1
            and abs(x2 - (expected_chart_x + expected_chart_w)) <= 0.1
            and abs(y1 - y2) <= 0.1
        ):
            axis_candidates.append(y1)
    if len(axis_candidates) != 1:
        raise AuditFailure(f"{path}: expected one x-axis candidate, got {axis_candidates}")
    axis_y = axis_candidates[0]
    if abs(axis_y - VARIANT_X_AXIS_Y) > 0.1:
        raise AuditFailure(f"{path}: x-axis y={axis_y}, expected {VARIANT_X_AXIS_Y}")
    legend_y_values = text_y_by_label(root, "Correct, by confidence")
    if len(legend_y_values) != 1:
        raise AuditFailure(f"{path}: expected one bottom legend label, got {len(legend_y_values)}")
    legend_y = legend_y_values[0]
    if abs(legend_y - VARIANT_LEGEND_Y) > 0.1:
        raise AuditFailure(f"{path}: legend y={legend_y}, expected {VARIANT_LEGEND_Y}")
    tick_to_legend_gap = legend_y - (axis_y + 38)
    if tick_to_legend_gap > 60:
        raise AuditFailure(f"{path}: x-axis tick to legend gap remains too large ({tick_to_legend_gap:.1f}px)")


def audit_variant_accessible_layout(root: ET.Element, path: Path, filename: str) -> None:
    outlines = root.findall(f".//{SVG_NS}rect[@class='bar-outline']")
    if len(outlines) != EXPECTED_COMPARATORS:
        raise AuditFailure(f"{path}: expected {EXPECTED_COMPARATORS} accessible variant bar outlines, got {len(outlines)}")
    expected_h = VARIANT_BAR_H[filename]
    expected_chart_x = expected_variant_chart_x(filename)
    expected_chart_w = expected_variant_chart_w(filename)
    for outline in outlines:
        actual_x = float(outline.get("x", "nan"))
        actual_w = float(outline.get("width", "nan"))
        actual_h = float(outline.get("height", "nan"))
        if abs(actual_x - expected_chart_x) > 0.1 or abs(actual_w - expected_chart_w) > 0.1:
            raise AuditFailure(
                f"{path}: variant bar span x={actual_x} width={actual_w} "
                f"does not match expected x={expected_chart_x} width={expected_chart_w}"
            )
        if abs(actual_h - expected_h) > 0.1:
            raise AuditFailure(f"{path}: variant bar height {actual_h} does not match expected {expected_h}")

    class_counts: dict[str, int] = {}
    for elem in root.findall(f".//{SVG_NS}text"):
        cls = elem.get("class") or ""
        class_counts[cls] = class_counts.get(cls, 0) + 1
    required_minimums = {
        "variant-subtitle": 1,
        "variant-axis-label": 7,
        "variant-score-label": EXPECTED_COMPARATORS,
        "variant-row-label": EXPECTED_COMPARATORS,
        "variant-bar-label": 8,
        "variant-legend-label": 7,
        "variant-micro": 2,
    }
    for cls, minimum in required_minimums.items():
        if class_counts.get(cls, 0) < minimum:
            raise AuditFailure(f"{path}: expected at least {minimum} text nodes with class {cls}, got {class_counts.get(cls, 0)}")
    spec = VARIANT_FILE_SPECS[filename]
    show_group_headers = bool(spec.get("show_group_headers", False))
    if show_group_headers and class_counts.get("variant-group-label", 0) != 4:
        raise AuditFailure(f"{path}: grouped variant must have four accessible group labels")
    if not show_group_headers and class_counts.get("variant-group-label", 0) != 0:
        raise AuditFailure(f"{path}: variant must not have left-side group labels")
    group_rules = [
        elem
        for elem in root.findall(f".//{SVG_NS}line")
        if elem.get("class") == "axis"
        and abs(float(elem.get("x1", "nan")) - VARIANT_GROUP_RULE_X1) <= 0.1
        and abs(float(elem.get("x2", "nan")) - VARIANT_GROUP_RULE_X2) <= 0.1
    ]
    if show_group_headers:
        for elem in root.findall(f".//{SVG_NS}text"):
            if elem.get("data-category-header"):
                actual_x = float(elem.get("x", "nan"))
                if abs(actual_x - VARIANT_GROUP_HEADER_X) > 0.1:
                    raise AuditFailure(
                        f"{path}: grouped category header x={actual_x}, expected {VARIANT_GROUP_HEADER_X}"
                    )
        if len(group_rules) != 4:
            raise AuditFailure(f"{path}: expected four grouped category rules, got {len(group_rules)}")
    elif group_rules:
        raise AuditFailure(f"{path}: variant must not have left-side group rules")
    for legacy_cls in ("subtitle", "row-label", "score-label", "micro"):
        if class_counts.get(legacy_cls, 0):
            raise AuditFailure(f"{path}: accessible variant still uses legacy small text class {legacy_cls}")


def score1000_bar_scale(
    value: float,
    y_min: float = SCORE1000_BAR_Y_MIN,
    y_max: float = SCORE1000_BAR_Y_MAX,
    chart_y: float = SCORE1000_BAR_CHART_Y,
    chart_h: float = SCORE1000_BAR_CHART_H,
) -> float:
    return chart_y + ((y_max - value) / (y_max - y_min)) * chart_h


def score1000_bar_axis_break_y(
    chart_y: float,
    chart_h: float,
    top_fraction: float,
) -> float:
    return chart_y + chart_h * top_fraction


def score1000_bar_scaled_y(
    value: float,
    *,
    y_min: float,
    y_max: float,
    chart_y: float,
    chart_h: float,
    axis_break_after: float | None = None,
    axis_break_top_fraction: float = SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
) -> float:
    if axis_break_after is None:
        return score1000_bar_scale(value, y_min, y_max, chart_y, chart_h)
    break_y = score1000_bar_axis_break_y(chart_y, chart_h, axis_break_top_fraction)
    chart_bottom = chart_y + chart_h
    if value <= axis_break_after:
        return chart_bottom - ((value - y_min) / (axis_break_after - y_min)) * (chart_bottom - break_y)
    return break_y - ((value - axis_break_after) / (y_max - axis_break_after)) * (break_y - chart_y)


def expected_score1000_bar_barcode_sequence(row: dict[str, str], max_units: int) -> list[str]:
    counts = {key: int(float(row.get(f"dot_{key}", 0))) for key in BIN_COLUMNS}
    total = sum(counts.values())
    if max_units <= 0 or total <= 0:
        return []
    quotas = {key: counts[key] * max_units / total for key in BIN_COLUMNS}
    base_counts = {key: int(quotas[key]) for key in BIN_COLUMNS}
    remaining = max_units - sum(base_counts.values())
    ranked = sorted(BIN_COLUMNS, key=lambda key: (quotas[key] - base_counts[key], counts[key]), reverse=True)
    for key in ranked[:remaining]:
        base_counts[key] += 1
    sequence: list[str] = []
    for key in BIN_COLUMNS:
        sequence.extend([key] * base_counts[key])
    return sequence


def audit_score_gap_overlay(
    root: ET.Element,
    chart_meta: dict[str, object],
    path: Path,
    rows: list[dict[str, str]],
    expected_labels: list[str],
    expected_bar_colors: dict[str, str],
    *,
    expected_y_min: float,
    expected_y_max: float,
    expected_chart_y: float,
    expected_chart_h: float,
    expected_axis_break_after: float | None,
    expected_axis_break_top_fraction: float,
    expected_date_label: str,
) -> None:
    expected = expected_score_gap_overlay_metadata(
        rows,
        expected_labels,
        expected_bar_colors,
        date_label=expected_date_label,
    )
    overlay_meta = chart_meta.get("score_gap_overlay")
    if not isinstance(overlay_meta, dict):
        raise AuditFailure(f"{path}: score gap overlay metadata missing")
    for key in ("human_score", "top_ai_score", "gap_value", "gap_abs_value"):
        if not close_enough(overlay_meta.get(key, "nan"), expected[key]):
            raise AuditFailure(f"{path}: score gap overlay metadata {key} mismatch")
    for key in (
        "human_label",
        "human_display_label",
        "human_color",
        "top_ai_label",
        "top_ai_display_label",
        "top_ai_color",
        "gap_rounded",
        "gap_direction",
        "date_label",
        "visible_label",
    ):
        if overlay_meta.get(key) != expected[key]:
            raise AuditFailure(f"{path}: score gap overlay metadata {key} mismatch")

    human_score = float(expected["human_score"])
    top_ai_score = float(expected["top_ai_score"])
    human_y = score1000_bar_scaled_y(
        human_score,
        y_min=expected_y_min,
        y_max=expected_y_max,
        chart_y=expected_chart_y,
        chart_h=expected_chart_h,
        axis_break_after=expected_axis_break_after,
        axis_break_top_fraction=expected_axis_break_top_fraction,
    )
    top_ai_y = score1000_bar_scaled_y(
        top_ai_score,
        y_min=expected_y_min,
        y_max=expected_y_max,
        chart_y=expected_chart_y,
        chart_h=expected_chart_h,
        axis_break_after=expected_axis_break_after,
        axis_break_top_fraction=expected_axis_break_top_fraction,
    )
    line_x1 = SCORE1000_BAR_CHART_X + SCORE1000_BAR_CHART_W * SCORE1000_BAR_GAP_OVERLAY_LINE_START_FRACTION
    line_x2 = SCORE1000_BAR_CHART_X + SCORE1000_BAR_CHART_W * SCORE1000_BAR_GAP_OVERLAY_LINE_END_FRACTION
    line_w = line_x2 - line_x1
    arrow_x = line_x1 + line_w * SCORE1000_BAR_GAP_OVERLAY_ARROW_LINE_FRACTION
    human_label_x = line_x1 + line_w * SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_LINE_FRACTION
    top_ai_label_x = line_x1 + (arrow_x - line_x1) * SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_PRE_ARROW_FRACTION
    top_ai_label_y = top_ai_y + SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_BASELINE_OFFSET
    arrow_top_y = min(human_y, top_ai_y)
    arrow_bottom_y = max(human_y, top_ai_y)

    overlay_groups = [
        elem for elem in root.findall(f".//{SVG_NS}g") if elem.get("class") == "score1000-gap-overlay"
    ]
    if len(overlay_groups) != 1:
        raise AuditFailure(f"{path}: expected one score gap overlay group, got {len(overlay_groups)}")
    overlay_group = overlay_groups[0]
    expected_data_attrs = {
        "data-human-score": score1000_gap_data_number(float(expected["human_score"])),
        "data-human-label": str(expected["human_label"]),
        "data-human-display-label": str(expected["human_display_label"]),
        "data-top-ai-score": score1000_gap_data_number(float(expected["top_ai_score"])),
        "data-top-ai-label": str(expected["top_ai_label"]),
        "data-top-ai-display-label": str(expected["top_ai_display_label"]),
        "data-gap-value": score1000_gap_data_number(float(expected["gap_value"])),
        "data-gap-abs-value": score1000_gap_data_number(float(expected["gap_abs_value"])),
        "data-gap-rounded": str(expected["gap_rounded"]),
        "data-gap-direction": str(expected["gap_direction"]),
        "data-score-gap-date-label": expected_date_label,
        "data-arrow-head-diagonal-ratio": f"{SCORE1000_BAR_GAP_OVERLAY_ARROW_DIAGONAL_RATIO:g}",
        "data-arrow-line-fraction": f"{SCORE1000_BAR_GAP_OVERLAY_ARROW_LINE_FRACTION:g}",
        "data-human-label-line-fraction": f"{SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_LINE_FRACTION:g}",
        "data-top-ai-label-pre-arrow-fraction": f"{SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_PRE_ARROW_FRACTION:g}",
        "data-human-label-text": SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL,
        "data-top-ai-label-text": SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL,
    }
    for attr, expected_value in expected_data_attrs.items():
        if overlay_group.get(attr) != expected_value:
            raise AuditFailure(f"{path}: score gap overlay {attr} mismatch")

    direct_children = list(root)
    axis_title_idx = next(
        (
            idx
            for idx, elem in enumerate(direct_children)
            if elem.tag == f"{SVG_NS}text" and elem.get("class") == "score1000-axis-title"
        ),
        None,
    )
    overlay_idx = next(
        (
            idx
            for idx, elem in enumerate(direct_children)
            if elem.tag == f"{SVG_NS}g" and elem.get("class") == "score1000-gap-overlay"
        ),
        None,
    )
    first_bar_idx = next(
        (
            idx
            for idx, elem in enumerate(direct_children)
            if elem.tag == f"{SVG_NS}rect" and elem.get("data-score1000-bar") == "true"
        ),
        None,
    )
    if axis_title_idx is None or overlay_idx is None or first_bar_idx is None:
        raise AuditFailure(f"{path}: score gap overlay draw-order anchors missing")
    if not axis_title_idx < overlay_idx < first_bar_idx:
        raise AuditFailure(f"{path}: score gap overlay must render after axis title and before bars")

    line_by_kind = {
        elem.get("data-score-gap-line"): elem
        for elem in root.findall(f".//{SVG_NS}line")
        if elem.get("class") == "score1000-gap-line"
    }
    if set(line_by_kind) != {"human", "top-ai"}:
        raise AuditFailure(f"{path}: score gap overlay lines mismatch")
    expected_lines = {
        "human": (human_y, str(expected["human_color"]), None, float(expected["human_score"])),
        "top-ai": (top_ai_y, str(expected["top_ai_color"]), str(expected["top_ai_label"]), float(expected["top_ai_score"])),
    }
    for kind, (expected_y, expected_color, expected_reader, expected_score) in expected_lines.items():
        elem = line_by_kind[kind]
        for attr, expected_value in {"x1": line_x1, "x2": line_x2, "y1": expected_y, "y2": expected_y}.items():
            actual = float(elem.get(attr, "nan"))
            if abs(actual - expected_value) > 0.1:
                raise AuditFailure(f"{path}: score gap {kind} line {attr}={actual}, expected {expected_value}")
        style = (elem.get("style") or "").lower()
        if f"stroke:{expected_color}".lower() not in style:
            raise AuditFailure(f"{path}: score gap {kind} line color mismatch")
        if "stroke-dasharray" not in style:
            raise AuditFailure(f"{path}: score gap {kind} line must be dashed")
        if elem.get("data-score2000-value") != score1000_gap_data_number(expected_score):
            raise AuditFailure(f"{path}: score gap {kind} line score metadata mismatch")
        if expected_reader is not None and elem.get("data-reader-label") != expected_reader:
            raise AuditFailure(f"{path}: score gap top-ai line reader metadata mismatch")

    arrow_lines = [
        elem for elem in root.findall(f".//{SVG_NS}line") if elem.get("class") == "score1000-gap-arrow"
    ]
    if len(arrow_lines) != 5:
        raise AuditFailure(f"{path}: expected five score gap arrow segments, got {len(arrow_lines)}")
    shaft = next((elem for elem in arrow_lines if elem.get("data-score-gap-arrow") == "shaft"), None)
    if shaft is None:
        raise AuditFailure(f"{path}: score gap arrow shaft missing")
    for attr, expected_value in {"x1": arrow_x, "x2": arrow_x, "y1": arrow_top_y, "y2": arrow_bottom_y}.items():
        actual = float(shaft.get(attr, "nan"))
        if abs(actual - expected_value) > 0.1:
            raise AuditFailure(f"{path}: score gap arrow shaft {attr}={actual}, expected {expected_value}")

    expected_arrow_head_len = (arrow_bottom_y - arrow_top_y) * SCORE1000_BAR_GAP_OVERLAY_ARROW_DIAGONAL_RATIO
    expected_arrow_head_w = expected_arrow_head_len * SCORE1000_BAR_GAP_OVERLAY_ARROW_45_PROJECTION
    expected_arrow_head_h = expected_arrow_head_len * SCORE1000_BAR_GAP_OVERLAY_ARROW_45_PROJECTION
    expected_heads = [
        ("top-head", arrow_x, arrow_top_y, arrow_x - expected_arrow_head_w, arrow_top_y + expected_arrow_head_h),
        ("top-head", arrow_x, arrow_top_y, arrow_x + expected_arrow_head_w, arrow_top_y + expected_arrow_head_h),
        (
            "bottom-head",
            arrow_x,
            arrow_bottom_y,
            arrow_x - expected_arrow_head_w,
            arrow_bottom_y - expected_arrow_head_h,
        ),
        (
            "bottom-head",
            arrow_x,
            arrow_bottom_y,
            arrow_x + expected_arrow_head_w,
            arrow_bottom_y - expected_arrow_head_h,
        ),
    ]
    actual_heads: list[tuple[str, float, float, float, float]] = []
    for elem in arrow_lines:
        kind = elem.get("data-score-gap-arrow")
        if kind in {"top-head", "bottom-head"}:
            actual_heads.append(
                (
                    kind,
                    float(elem.get("x1", "nan")),
                    float(elem.get("y1", "nan")),
                    float(elem.get("x2", "nan")),
                    float(elem.get("y2", "nan")),
                )
            )
    if len(actual_heads) != 4:
        raise AuditFailure(f"{path}: expected four score gap arrow heads, got {len(actual_heads)}")
    remaining_heads = actual_heads[:]
    for expected_head in expected_heads:
        match_idx = next(
            (
                idx
                for idx, actual_head in enumerate(remaining_heads)
                if actual_head[0] == expected_head[0]
                and all(abs(actual_head[j] - expected_head[j]) <= 0.1 for j in range(1, 5))
            ),
            None,
        )
        if match_idx is None:
            raise AuditFailure(f"{path}: score gap arrow head geometry mismatch; expected {expected_head}")
        del remaining_heads[match_idx]
    for kind, x1, y1, x2, y2 in actual_heads:
        actual_diag = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        if abs(actual_diag - expected_arrow_head_len) > 0.2:
            raise AuditFailure(
                f"{path}: score gap {kind} diagonal length={actual_diag}, expected {expected_arrow_head_len}"
            )

    human_label_masks = [
        elem
        for elem in root.findall(f".//{SVG_NS}rect")
        if elem.get("data-score-gap-human-label-mask") == "true"
    ]
    if len(human_label_masks) != 1:
        raise AuditFailure(f"{path}: expected one score gap human label mask, got {len(human_label_masks)}")
    mask = human_label_masks[0]
    expected_mask = {
        "x": human_label_x - SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_MASK_W / 2.0,
        "y": human_y - SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_MASK_H / 2.0,
        "width": SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_MASK_W,
        "height": SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_MASK_H,
    }
    for attr, expected_value in expected_mask.items():
        actual = float(mask.get(attr, "nan"))
        if abs(actual - expected_value) > 0.1:
            raise AuditFailure(f"{path}: score gap human label mask {attr}={actual}, expected {expected_value}")

    top_ai_label_masks = [
        elem
        for elem in root.findall(f".//{SVG_NS}rect")
        if elem.get("data-score-gap-top-ai-label-mask") == "true"
    ]
    if len(top_ai_label_masks) != 1:
        raise AuditFailure(f"{path}: expected one score gap top-AI label mask, got {len(top_ai_label_masks)}")
    top_ai_mask = top_ai_label_masks[0]
    expected_top_ai_mask = {
        "x": top_ai_label_x - SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_MASK_W / 2.0,
        "y": top_ai_y - SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_MASK_H / 2.0,
        "width": SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_MASK_W,
        "height": SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_MASK_H,
    }
    for attr, expected_value in expected_top_ai_mask.items():
        actual = float(top_ai_mask.get(attr, "nan"))
        if abs(actual - expected_value) > 0.1:
            raise AuditFailure(f"{path}: score gap top-AI label mask {attr}={actual}, expected {expected_value}")

    gap_labels = [
        elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("data-score-gap-label") == "true"
    ]
    if len(gap_labels) != 1:
        raise AuditFailure(f"{path}: expected one score gap label, got {len(gap_labels)}")
    if "".join(gap_labels[0].itertext()).strip() != str(expected["visible_label"]):
        raise AuditFailure(f"{path}: score gap visible label mismatch")
    human_labels = [
        elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("data-score-gap-human-label") == "true"
    ]
    top_ai_labels = [
        elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("data-score-gap-top-ai-label") == "true"
    ]
    if len(human_labels) != 1 or len(top_ai_labels) != 1:
        raise AuditFailure(f"{path}: score gap band labels missing")
    human_label_text = "".join(human_labels[0].itertext()).strip()
    if human_label_text != SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL:
        raise AuditFailure(f"{path}: score gap human label must be one unwrapped line")
    if human_labels[0].find(f"{SVG_NS}tspan") is not None:
        raise AuditFailure(f"{path}: score gap human label is wrapped into tspans")
    expected_human_label_y = human_y + SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_BASELINE_OFFSET
    if abs(float(human_labels[0].get("x", "nan")) - human_label_x) > 0.1:
        raise AuditFailure(f"{path}: score gap human label x mismatch")
    if abs(float(human_labels[0].get("y", "nan")) - expected_human_label_y) > 0.1:
        raise AuditFailure(f"{path}: score gap human label y mismatch")
    if "".join(top_ai_labels[0].itertext()).strip() != SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL:
        raise AuditFailure(f"{path}: score gap top-AI label text mismatch")
    if top_ai_labels[0].find(f"{SVG_NS}tspan") is not None:
        raise AuditFailure(f"{path}: score gap top-AI label is wrapped into tspans")
    if abs(float(top_ai_labels[0].get("x", "nan")) - top_ai_label_x) > 0.1:
        raise AuditFailure(f"{path}: score gap top-AI label x mismatch")
    if abs(float(top_ai_labels[0].get("y", "nan")) - top_ai_label_y) > 0.1:
        raise AuditFailure(f"{path}: score gap top-AI label y mismatch")


def audit_score1000_bar_chart(
    root: ET.Element,
    payload: dict[str, object],
    path: Path,
    filename: str,
    rows: list[dict[str, str]],
) -> None:
    spec = VARIANT_FILE_SPECS[filename]
    selected_set = list(spec["selected_reader_labels"])  # type: ignore[index]
    expected_labels = score2000_expected_labels(rows, selected_set)
    expected_y_min = float(spec.get("score_y_min", SCORE1000_BAR_Y_MIN))
    expected_y_max = float(spec.get("score_y_max", SCORE1000_BAR_Y_MAX))
    expected_ticks = list(spec.get("score_ticks", SCORE1000_BAR_TICKS))  # type: ignore[arg-type]
    expected_include_icons = bool(spec.get("include_model_icons", False))
    expected_top_logo_scale = float(spec.get("top_logo_scale", 1.0))
    expected_bar_logo_scale = float(spec.get("bar_logo_scale", 1.0))
    expected_bar_logo_image_multipliers = dict(spec.get("bar_logo_image_multipliers", {}))
    expected_chart_y = float(spec.get("score_chart_y", SCORE1000_BAR_CHART_Y))
    expected_chart_h = float(spec.get("score_chart_h", SCORE1000_BAR_CHART_H))
    expected_y_axis_left_shift = float(spec.get("y_axis_left_shift", 0.0))
    expected_axis_x = SCORE1000_BAR_CHART_X - expected_y_axis_left_shift
    expected_figure_title_x = float(spec.get("figure_title_x", 1800.0))
    expected_figure_title_y = float(spec.get("figure_title_y", EXPECTED_FIGURE_TITLE_Y))
    expected_figure_title_font_px = spec.get("figure_title_font_px")
    expected_panel_title = str(spec.get("panel_title", EXPECTED_SCORE2000_BAR_TITLE))
    expected_panel_title_cls = str(spec.get("panel_title_cls", "title"))
    expected_panel_title_y = float(spec.get("panel_title_y", 332.0))
    expected_panel_title_font_px = spec.get("panel_title_font_px")
    expected_axis_title = str(spec.get("axis_title", EXPECTED_SCORE2000_BAR_AXIS_TITLE))
    expected_tick_label_font_px = spec.get("tick_label_font_px")
    expected_bar_value_font_scale = float(spec.get("bar_value_font_scale", 1.0))
    expected_variant_footer = bool(spec.get("use_variant_footer", False))
    expected_show_footer = bool(spec.get("show_footer", True))
    expected_footer_lines = list(spec.get("footer_lines", []))  # type: ignore[arg-type]
    expected_footer_cls = str(spec.get("footer_cls", "variant-micro"))
    expected_footer_text_y = float(spec.get("footer_text_y", VARIANT_FOOTER_TEXT_Y))
    expected_footer_line_step = float(spec.get("footer_line_step", VARIANT_FOOTER_LINE_STEP))
    expected_footer_divider_y = float(spec.get("footer_divider_y", VARIANT_FOOTER_DIVIDER_Y))
    expected_footer_font_px = spec.get("footer_font_px")
    expected_footer_x = float(spec.get("footer_x", 80.0))
    expected_footer_right_x = float(spec.get("footer_right_x", 3520.0))
    expected_x_label_y_offset = float(spec.get("x_label_y_offset", 78.0))
    expected_x_label_font_px = spec.get("x_label_font_px")
    expected_x_label_line_step = float(spec.get("x_label_line_step", SCORE1000_BAR_X_LABEL_LINE_STEP))
    expected_logo_position = str(spec.get("logo_position", "inside_bar"))
    expected_bottom_logo_center_y = spec.get("bottom_logo_center_y")
    expected_bar_width = float(spec.get("score_bar_width", SCORE1000_BAR_W))
    expected_svg_h = float(spec.get("svg_h", VARIANT_SVG_H))
    expected_axis_break_after = (
        float(spec["score_axis_break_after"]) if "score_axis_break_after" in spec else None
    )
    expected_axis_break_style = str(spec["score_axis_break_style"]) if "score_axis_break_style" in spec else None
    expected_axis_break_top_fraction = float(
        spec.get("score_axis_break_top_fraction", SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION)
    )
    expected_include_barcode_overlay = bool(spec.get("include_barcode_overlay", False))
    expected_barcode_units = int(spec.get("barcode_units", SCORE1000_BAR_BARCODE_UNITS))
    expected_barcode_capsule_w = float(spec.get("barcode_capsule_w", SCORE1000_BAR_BARCODE_CAPSULE_W))
    expected_barcode_capsule_h = float(spec.get("barcode_capsule_h", SCORE1000_BAR_BARCODE_CAPSULE_H))
    expected_barcode_capsule_gap = float(spec.get("barcode_capsule_gap", SCORE1000_BAR_BARCODE_CAPSULE_GAP))
    expected_barcode_palette_key = str(spec.get("barcode_outcome_palette_key", SCORE1000_BAR_BARCODE_PALETTE))
    expected_include_score_gap_overlay = bool(spec.get("include_score_gap_overlay", False))
    expected_score_gap_date_label = str(spec.get("score_gap_date_label", SCORE1000_BAR_GAP_DATE_LABEL))
    expected_bar_colors = expected_variant_bar_colors(filename)
    by_label = {row["reader_label"]: row for row in rows}
    if any(label not in by_label for label in selected_set):
        raise AuditFailure(f"{path}: selected Score2000 labels are not all present in source rows")
    stylesheet = "\n".join("".join(elem.itertext()) for elem in root.findall(f".//{SVG_NS}style"))

    doc_title = root.find(f"{SVG_NS}title")
    if doc_title is None or "".join(doc_title.itertext()).strip() != expected_panel_title:
        raise AuditFailure(f"{path}: SVG title must be {expected_panel_title!r}")
    visible_titles = [
        elem
        for elem in root.findall(f".//{SVG_NS}text")
        if elem.get("class") == expected_panel_title_cls and "".join(elem.itertext()).strip() == expected_panel_title
    ]
    if len(visible_titles) != 1:
        raise AuditFailure(f"{path}: expected one visible title {expected_panel_title!r}, got {len(visible_titles)}")
    if abs(float(visible_titles[0].get("y", "nan")) - expected_panel_title_y) > 0.1:
        raise AuditFailure(f"{path}: visible title y mismatch")
    if expected_panel_title_font_px is not None and f"font-size:{float(expected_panel_title_font_px):.1f}px" not in (
        visible_titles[0].get("style") or ""
    ):
        raise AuditFailure(f"{path}: visible title font-size mismatch")
    audit_variant_figure_title(root, path, expected_figure_title_x, expected_figure_title_y)
    figure_title = next(
        elem
        for elem in root.findall(f".//{SVG_NS}text")
        if elem.get("class") == "figure-title" and "".join(elem.itertext()).strip() == EXPECTED_FIGURE_TITLE
    )
    if expected_figure_title_font_px is not None and f"font-size:{float(expected_figure_title_font_px):.1f}px" not in (
        figure_title.get("style") or ""
    ):
        raise AuditFailure(f"{path}: figure title font-size mismatch")

    chart_meta = payload.get("score1000_bar_chart")
    if not isinstance(chart_meta, dict):
        raise AuditFailure(f"{path}: metadata missing score1000_bar_chart")
    if chart_meta.get("selected_reader_labels") != expected_labels:
        raise AuditFailure(f"{path}: selected reader metadata mismatch")
    if chart_meta.get("selected_reader_set") != selected_set:
        raise AuditFailure(f"{path}: selected reader set metadata mismatch")
    if chart_meta.get("logo_binding_key") != "reader_label":
        raise AuditFailure(f"{path}: logo binding key metadata mismatch")
    selected_readers = chart_meta.get("selected_readers")
    if not isinstance(selected_readers, list) or len(selected_readers) != len(expected_labels):
        raise AuditFailure(f"{path}: selected reader binding metadata mismatch")
    selected_binding_by_label = {str(item.get("reader_label")): item for item in selected_readers if isinstance(item, dict)}
    if list(selected_binding_by_label) != expected_labels:
        raise AuditFailure(f"{path}: selected reader binding order mismatch: {list(selected_binding_by_label)}")
    for label in expected_labels:
        binding = selected_binding_by_label[label]
        if binding.get("reader_key") != score1000_bar_reader_key(label):
            raise AuditFailure(f"{path}: selected reader key mismatch for {label}")
        if label in SCORE1000_BAR_LOGO_ASSETS:
            if binding.get("logo_kind") != "asset":
                raise AuditFailure(f"{path}: selected reader logo kind mismatch for {label}")
            if binding.get("logo_source") != rel(SCORE1000_BAR_LOGO_ASSETS[label]):
                raise AuditFailure(f"{path}: selected reader logo source mismatch for {label}")
            if str(binding.get("logo_sha256", "")).upper() != sha256_file(SCORE1000_BAR_LOGO_ASSETS[label]):
                raise AuditFailure(f"{path}: selected reader logo SHA mismatch for {label}")
        else:
            badge = SCORE1000_BAR_FALLBACK_BADGES[label]
            if binding.get("logo_kind") != "svg_text_badge":
                raise AuditFailure(f"{path}: selected reader fallback logo kind mismatch for {label}")
            if binding.get("fallback_badge_label") != badge["label"]:
                raise AuditFailure(f"{path}: selected reader fallback badge label mismatch for {label}")
        if str(binding.get("color", "")).lower() != expected_bar_colors[label]:
            raise AuditFailure(f"{path}: selected reader color mismatch for {label}")
    if chart_meta.get("display_score_column") != "score2000":
        raise AuditFailure(f"{path}: display score column metadata mismatch")
    if not close_enough(chart_meta.get("baseline", "nan"), SCORE2000_BASELINE):
        raise AuditFailure(f"{path}: Score2000 baseline metadata mismatch")
    if not close_enough(chart_meta.get("bar_origin", "nan"), expected_y_min):
        raise AuditFailure(f"{path}: Score2000 bar origin metadata mismatch")
    if not close_enough(chart_meta.get("reference_line", "nan"), SCORE2000_BASELINE):
        raise AuditFailure(f"{path}: Score2000 reference line metadata mismatch")
    audit_score2000_rule_metadata({"score2000_rule": chart_meta.get("score2000_rule")}, path)
    if not close_enough(chart_meta.get("y_min", "nan"), expected_y_min):
        raise AuditFailure(f"{path}: y_min metadata mismatch")
    if not close_enough(chart_meta.get("y_max", "nan"), expected_y_max):
        raise AuditFailure(f"{path}: y_max metadata mismatch")
    if chart_meta.get("ticks") != expected_ticks:
        raise AuditFailure(f"{path}: y tick metadata mismatch")
    if not close_enough(chart_meta.get("bar_width", "nan"), expected_bar_width):
        raise AuditFailure(f"{path}: bar_width metadata mismatch")
    if expected_axis_break_after is None:
        if chart_meta.get("axis_break_after") is not None:
            raise AuditFailure(f"{path}: unexpected axis_break_after metadata")
    elif not close_enough(chart_meta.get("axis_break_after", "nan"), expected_axis_break_after):
        raise AuditFailure(f"{path}: axis_break_after metadata mismatch")
    if chart_meta.get("axis_break_style") != expected_axis_break_style:
        raise AuditFailure(f"{path}: axis_break_style metadata mismatch")
    if not close_enough(chart_meta.get("axis_break_top_fraction", "nan"), expected_axis_break_top_fraction):
        raise AuditFailure(f"{path}: axis_break_top_fraction metadata mismatch")
    if bool(chart_meta.get("include_barcode_overlay", False)) != expected_include_barcode_overlay:
        raise AuditFailure(f"{path}: include_barcode_overlay metadata mismatch")
    if int(chart_meta.get("barcode_units", 0)) != expected_barcode_units:
        raise AuditFailure(f"{path}: barcode_units metadata mismatch")
    if not close_enough(chart_meta.get("barcode_capsule_w", "nan"), expected_barcode_capsule_w):
        raise AuditFailure(f"{path}: barcode_capsule_w metadata mismatch")
    if not close_enough(chart_meta.get("barcode_capsule_h", "nan"), expected_barcode_capsule_h):
        raise AuditFailure(f"{path}: barcode_capsule_h metadata mismatch")
    if not close_enough(chart_meta.get("barcode_capsule_gap", "nan"), expected_barcode_capsule_gap):
        raise AuditFailure(f"{path}: barcode_capsule_gap metadata mismatch")
    if chart_meta.get("barcode_outcome_palette_key") != expected_barcode_palette_key:
        raise AuditFailure(f"{path}: barcode_outcome_palette_key metadata mismatch")
    expected_barcode_bin_order = BIN_COLUMNS if expected_include_barcode_overlay else None
    if chart_meta.get("barcode_bin_order_bottom_to_top") != expected_barcode_bin_order:
        raise AuditFailure(f"{path}: barcode bin order metadata mismatch")
    if bool(chart_meta.get("include_score_gap_overlay", False)) != expected_include_score_gap_overlay:
        raise AuditFailure(f"{path}: include_score_gap_overlay metadata mismatch")
    if chart_meta.get("score_gap_date_label") != expected_score_gap_date_label:
        raise AuditFailure(f"{path}: score_gap_date_label metadata mismatch")
    if expected_include_score_gap_overlay:
        if not isinstance(chart_meta.get("score_gap_overlay"), dict):
            raise AuditFailure(f"{path}: score gap overlay metadata missing")
    elif chart_meta.get("score_gap_overlay") is not None:
        raise AuditFailure(f"{path}: unexpected score gap overlay metadata")
    if bool(chart_meta.get("include_model_icons", False)) != expected_include_icons:
        raise AuditFailure(f"{path}: include_model_icons metadata mismatch")
    if not close_enough(chart_meta.get("top_logo_scale", "nan"), expected_top_logo_scale):
        raise AuditFailure(f"{path}: top_logo_scale metadata mismatch")
    if not close_enough(chart_meta.get("bar_logo_scale", "nan"), expected_bar_logo_scale):
        raise AuditFailure(f"{path}: bar_logo_scale metadata mismatch")
    if chart_meta.get("bar_logo_image_multipliers") != expected_bar_logo_image_multipliers:
        raise AuditFailure(f"{path}: bar_logo_image_multipliers metadata mismatch")
    if not close_enough(chart_meta.get("chart_y", "nan"), expected_chart_y):
        raise AuditFailure(f"{path}: chart_y metadata mismatch")
    if not close_enough(chart_meta.get("chart_h", "nan"), expected_chart_h):
        raise AuditFailure(f"{path}: chart_h metadata mismatch")
    if not close_enough(chart_meta.get("y_axis_left_shift", 0.0), expected_y_axis_left_shift):
        raise AuditFailure(f"{path}: y_axis_left_shift metadata mismatch")
    if not close_enough(chart_meta.get("figure_title_x", "nan"), expected_figure_title_x):
        raise AuditFailure(f"{path}: figure_title_x metadata mismatch")
    if not close_enough(chart_meta.get("figure_title_y", "nan"), expected_figure_title_y):
        raise AuditFailure(f"{path}: figure_title_y metadata mismatch")
    if chart_meta.get("figure_title_font_px") != expected_figure_title_font_px:
        raise AuditFailure(f"{path}: figure_title_font_px metadata mismatch")
    if chart_meta.get("panel_title_cls") != expected_panel_title_cls:
        raise AuditFailure(f"{path}: panel_title_cls metadata mismatch")
    if not close_enough(chart_meta.get("panel_title_y", "nan"), expected_panel_title_y):
        raise AuditFailure(f"{path}: panel_title_y metadata mismatch")
    if chart_meta.get("panel_title_font_px") != expected_panel_title_font_px:
        raise AuditFailure(f"{path}: panel_title_font_px metadata mismatch")
    if chart_meta.get("axis_title") != expected_axis_title:
        raise AuditFailure(f"{path}: axis_title metadata mismatch")
    if chart_meta.get("tick_label_font_px") != expected_tick_label_font_px:
        raise AuditFailure(f"{path}: tick_label_font_px metadata mismatch")
    if not close_enough(chart_meta.get("bar_value_font_scale", "nan"), expected_bar_value_font_scale):
        raise AuditFailure(f"{path}: bar_value_font_scale metadata mismatch")
    if bool(chart_meta.get("use_variant_footer", False)) != expected_variant_footer:
        raise AuditFailure(f"{path}: use_variant_footer metadata mismatch")
    if bool(chart_meta.get("show_footer", True)) != expected_show_footer:
        raise AuditFailure(f"{path}: show_footer metadata mismatch")
    if chart_meta.get("footer_lines") != (expected_footer_lines or None):
        raise AuditFailure(f"{path}: footer_lines metadata mismatch")
    if chart_meta.get("footer_cls") != expected_footer_cls:
        raise AuditFailure(f"{path}: footer_cls metadata mismatch")
    if not close_enough(chart_meta.get("footer_text_y", "nan"), expected_footer_text_y):
        raise AuditFailure(f"{path}: footer_text_y metadata mismatch")
    if not close_enough(chart_meta.get("footer_line_step", "nan"), expected_footer_line_step):
        raise AuditFailure(f"{path}: footer_line_step metadata mismatch")
    if not close_enough(chart_meta.get("footer_divider_y", "nan"), expected_footer_divider_y):
        raise AuditFailure(f"{path}: footer_divider_y metadata mismatch")
    if chart_meta.get("footer_font_px") != expected_footer_font_px:
        raise AuditFailure(f"{path}: footer_font_px metadata mismatch")
    if not close_enough(chart_meta.get("footer_x", "nan"), expected_footer_x):
        raise AuditFailure(f"{path}: footer_x metadata mismatch")
    if not close_enough(chart_meta.get("footer_right_x", "nan"), expected_footer_right_x):
        raise AuditFailure(f"{path}: footer_right_x metadata mismatch")
    if not close_enough(chart_meta.get("x_label_y_offset", "nan"), expected_x_label_y_offset):
        raise AuditFailure(f"{path}: x_label_y_offset metadata mismatch")
    if chart_meta.get("x_label_font_px") != expected_x_label_font_px:
        raise AuditFailure(f"{path}: x_label_font_px metadata mismatch")
    if not close_enough(chart_meta.get("x_label_line_step", "nan"), expected_x_label_line_step):
        raise AuditFailure(f"{path}: x_label_line_step metadata mismatch")
    if chart_meta.get("logo_position") != expected_logo_position:
        raise AuditFailure(f"{path}: logo_position metadata mismatch")
    if expected_bottom_logo_center_y is None:
        if chart_meta.get("bottom_logo_center_y") is not None:
            raise AuditFailure(f"{path}: unexpected bottom_logo_center_y metadata")
    elif not close_enough(chart_meta.get("bottom_logo_center_y", "nan"), float(expected_bottom_logo_center_y)):
        raise AuditFailure(f"{path}: bottom_logo_center_y metadata mismatch")
    if not close_enough(chart_meta.get("octomed_logo_scale", "nan"), SCORE1000_BAR_OCTOMED_LOGO_SCALE):
        raise AuditFailure(f"{path}: octomed_logo_scale metadata mismatch")
    actual_bar_colors = chart_meta.get("bar_colors")
    if actual_bar_colors != expected_bar_colors:
        raise AuditFailure(f"{path}: bar color metadata mismatch")
    if expected_include_icons:
        bar_logos = chart_meta.get("bar_logos")
        if not isinstance(bar_logos, list) or len(bar_logos) != len(SCORE1000_BAR_LOGO_ASSETS):
            raise AuditFailure(f"{path}: expected {len(SCORE1000_BAR_LOGO_ASSETS)} bar logo metadata rows")
        logo_by_label = {str(item.get("reader_label")): item for item in bar_logos if isinstance(item, dict)}
        if set(logo_by_label) != set(SCORE1000_BAR_LOGO_ASSETS):
            raise AuditFailure(f"{path}: bar logo metadata labels mismatch: {set(logo_by_label)}")
        for label, asset_path in SCORE1000_BAR_LOGO_ASSETS.items():
            item = logo_by_label[label]
            if str(item.get("source")) != rel(asset_path):
                raise AuditFailure(f"{path}: bar logo source mismatch for {label}")
            if str(item.get("sha256", "")).upper() != sha256_file(asset_path):
                raise AuditFailure(f"{path}: bar logo SHA mismatch for {label}")
        fallback_badges = chart_meta.get("fallback_logo_badges")
        if not isinstance(fallback_badges, list) or len(fallback_badges) != len(SCORE1000_BAR_FALLBACK_BADGES):
            raise AuditFailure(f"{path}: expected {len(SCORE1000_BAR_FALLBACK_BADGES)} fallback badge metadata rows")
        badge_by_label = {str(item.get("reader_label")): item for item in fallback_badges if isinstance(item, dict)}
        if set(badge_by_label) != set(SCORE1000_BAR_FALLBACK_BADGES):
            raise AuditFailure(f"{path}: fallback badge metadata labels mismatch")
        for label, badge in SCORE1000_BAR_FALLBACK_BADGES.items():
            item = badge_by_label[label]
            if item.get("kind") != "svg_text_badge":
                raise AuditFailure(f"{path}: fallback badge kind mismatch for {label}")
            if item.get("label") != badge["label"] or item.get("short_label") != badge["short_label"]:
                raise AuditFailure(f"{path}: fallback badge label mismatch for {label}")
    elif "bar_logos" in chart_meta:
        raise AuditFailure(f"{path}: bar logo metadata present when icons are disabled")
    elif "fallback_logo_badges" in chart_meta:
        raise AuditFailure(f"{path}: fallback badge metadata present when icons are disabled")

    tick_lines = {
        int(float(elem.get("data-score1000-tick", "nan"))): elem
        for elem in root.findall(f".//{SVG_NS}line")
        if elem.get("data-score1000-tick") is not None
    }
    if set(tick_lines) != set(expected_ticks):
        raise AuditFailure(f"{path}: emitted tick lines mismatch: {sorted(tick_lines)}")
    for tick in expected_ticks:
        elem = tick_lines[tick]
        if elem.get("class") != "score2000-grid":
            raise AuditFailure(f"{path}: tick {tick} must render as faint score2000-grid")
        expected_y = score1000_bar_scaled_y(
            float(tick),
            y_min=expected_y_min,
            y_max=expected_y_max,
            chart_y=expected_chart_y,
            chart_h=expected_chart_h,
            axis_break_after=expected_axis_break_after,
            axis_break_top_fraction=expected_axis_break_top_fraction,
        )
        y1 = float(elem.get("y1", "nan"))
        y2 = float(elem.get("y2", "nan"))
        x1 = float(elem.get("x1", "nan"))
        x2 = float(elem.get("x2", "nan"))
        if abs(y1 - expected_y) > 0.1 or abs(y2 - expected_y) > 0.1:
            raise AuditFailure(f"{path}: tick {tick} y mismatch: {y1}, {y2}, expected {expected_y}")
        if abs(x1 - expected_axis_x) > 0.1 or abs(x2 - (SCORE1000_BAR_CHART_X + SCORE1000_BAR_CHART_W)) > 0.1:
            raise AuditFailure(f"{path}: tick {tick} x-span mismatch")
    zero_lines = [
        elem for elem in root.findall(f".//{SVG_NS}line") if elem.get("data-score1000-zero-line") == "true"
    ]
    if len(zero_lines) != 1:
        raise AuditFailure(f"{path}: expected one Score1000 zero line, got {len(zero_lines)}")
    if zero_lines[0].get("class") != "score2000-grid":
        raise AuditFailure(f"{path}: shifted 1000 reference line must render as faint score2000-grid")
    axis_break_marks = [
        elem for elem in root.findall(f".//{SVG_NS}line") if elem.get("data-score2000-axis-break-mark") == "true"
    ]
    if expected_axis_break_style == "a1_double_slash":
        if len(axis_break_marks) != 2:
            raise AuditFailure(f"{path}: expected two A1 axis-break marks, got {len(axis_break_marks)}")
        expected_break_y = score1000_bar_axis_break_y(
            expected_chart_y,
            expected_chart_h,
            expected_axis_break_top_fraction,
        )
        actual_midpoints = sorted((float(elem.get("y1", "nan")) + float(elem.get("y2", "nan"))) / 2 for elem in axis_break_marks)
        expected_midpoints = sorted([expected_break_y - 13.0, expected_break_y + 13.0])
        for actual, expected in zip(actual_midpoints, expected_midpoints, strict=True):
            if abs(actual - expected) > 0.1:
                raise AuditFailure(f"{path}: A1 axis-break mark midpoint {actual}, expected {expected}")
        for elem in axis_break_marks:
            if elem.get("class") != "score2000-axis-break-mark":
                raise AuditFailure(f"{path}: A1 axis-break mark class mismatch")
    elif axis_break_marks:
        raise AuditFailure(f"{path}: unexpected axis-break marks")

    tick_labels = [
        elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("data-score1000-tick-label") is not None
    ]
    if sorted(int(float(elem.get("data-score1000-tick-label", "nan"))) for elem in tick_labels) != expected_ticks:
        raise AuditFailure(f"{path}: y-axis tick label mismatch")
    if expected_tick_label_font_px is not None:
        expected_tick_style = f"font-size:{float(expected_tick_label_font_px):.1f}px"
        for elem in tick_labels:
            if expected_tick_style not in (elem.get("style") or ""):
                raise AuditFailure(f"{path}: tick label font-size mismatch")
    expected_tick_label_x = expected_axis_x - SCORE1000_BAR_TICK_LABEL_X_OFFSET
    for elem in tick_labels:
        if elem.get("text-anchor") != "end":
            raise AuditFailure(f"{path}: y-axis tick label anchor mismatch")
        if abs(float(elem.get("x", "nan")) - expected_tick_label_x) > 0.1:
            raise AuditFailure(f"{path}: y-axis tick label x mismatch")
    axis_titles = [
        elem
        for elem in root.findall(f".//{SVG_NS}text")
        if elem.get("class") == "score1000-axis-title" and "".join(elem.itertext()).strip() == expected_axis_title
    ]
    if len(axis_titles) != 1:
        raise AuditFailure(f"{path}: expected one {expected_axis_title!r} y-axis title")
    expected_axis_title_transform = (
        f"translate({expected_axis_x - SCORE1000_BAR_AXIS_TITLE_X_OFFSET:.1f} "
        f"{expected_chart_y + expected_chart_h / 2:.1f}) rotate(-90)"
    )
    if axis_titles[0].get("transform") != expected_axis_title_transform:
        raise AuditFailure(f"{path}: y-axis title transform mismatch")

    if expected_include_score_gap_overlay:
        audit_score_gap_overlay(
            root,
            chart_meta,
            path,
            rows,
            expected_labels,
            expected_bar_colors,
            expected_y_min=expected_y_min,
            expected_y_max=expected_y_max,
            expected_chart_y=expected_chart_y,
            expected_chart_h=expected_chart_h,
            expected_axis_break_after=expected_axis_break_after,
            expected_axis_break_top_fraction=expected_axis_break_top_fraction,
            expected_date_label=expected_score_gap_date_label,
        )
    else:
        overlay_groups = [
            elem for elem in root.findall(f".//{SVG_NS}g") if elem.get("class") == "score1000-gap-overlay"
        ]
        if overlay_groups:
            raise AuditFailure(f"{path}: unexpected score gap overlay group")

    bars = [
        elem for elem in root.findall(f".//{SVG_NS}rect") if elem.get("data-score1000-bar") == "true"
    ]
    if len(bars) != len(expected_labels):
        raise AuditFailure(f"{path}: expected {len(expected_labels)} Score1000 bars, got {len(bars)}")
    bars_by_label = {str(elem.get("data-reader-label")): elem for elem in bars}
    if list(bars_by_label) != expected_labels:
        raise AuditFailure(f"{path}: Score1000 bar order mismatch: {list(bars_by_label)}")

    value_labels = [
        elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("class") == "score1000-bar-value"
    ]
    value_by_label = {str(elem.get("data-reader-label")): elem for elem in value_labels}
    if set(value_by_label) != set(expected_labels):
        raise AuditFailure(f"{path}: Score1000 value labels mismatch")

    x_labels = [
        elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("data-score1000-x-label") is not None
    ]
    if [str(elem.get("data-score1000-x-label")) for elem in x_labels] != expected_labels:
        raise AuditFailure(f"{path}: x-axis label order mismatch")
    x_label_by_label = {str(elem.get("data-score1000-x-label")): elem for elem in x_labels}
    x_label_css = "\n".join(line for line in stylesheet.splitlines() if ".score1000-x-label" in line)
    expected_x_label_css = (
        f"font-size: {SCORE1000_BAR_X_LABEL_FONT_SIZE:g}px",
        f"font-size:{SCORE1000_BAR_X_LABEL_FONT_SIZE:g}px",
        f"font-size: {SCORE1000_BAR_X_LABEL_FONT_SIZE:.1f}px",
    )
    if not x_label_css or not any(token in x_label_css for token in expected_x_label_css):
        raise AuditFailure(f"{path}: x-axis label font-size CSS mismatch")
    expected_x_label_y = expected_chart_y + expected_chart_h + expected_x_label_y_offset
    for elem in x_labels:
        if abs(float(elem.get("y", "nan")) - expected_x_label_y) > 0.1:
            raise AuditFailure(f"{path}: x-axis label y mismatch")
        if expected_x_label_font_px is not None and f"font-size:{float(expected_x_label_font_px):.1f}px" not in (
            elem.get("style") or ""
        ):
            raise AuditFailure(f"{path}: x-axis label inline font-size mismatch")
        tspans = elem.findall(f"{SVG_NS}tspan")
        for tspan_idx, tspan in enumerate(tspans):
            expected_dy = 0.0 if tspan_idx == 0 else expected_x_label_line_step
            if abs(float(tspan.get("dy", "nan")) - expected_dy) > 0.1:
                raise AuditFailure(f"{path}: x-axis label line-step mismatch")

    slot_w = SCORE1000_BAR_CHART_W / len(expected_labels)
    bar_origin_y = score1000_bar_scaled_y(
        expected_y_min,
        y_min=expected_y_min,
        y_max=expected_y_max,
        chart_y=expected_chart_y,
        chart_h=expected_chart_h,
        axis_break_after=expected_axis_break_after,
        axis_break_top_fraction=expected_axis_break_top_fraction,
    )
    axis_break_y = (
        score1000_bar_axis_break_y(expected_chart_y, expected_chart_h, expected_axis_break_top_fraction)
        if expected_axis_break_after is not None
        else None
    )
    for idx, label in enumerate(expected_labels):
        row = by_label[label]
        score = score2000_value(row)
        expected_score_y = score1000_bar_scaled_y(
            score,
            y_min=expected_y_min,
            y_max=expected_y_max,
            chart_y=expected_chart_y,
            chart_h=expected_chart_h,
            axis_break_after=expected_axis_break_after,
            axis_break_top_fraction=expected_axis_break_top_fraction,
        )
        expected_x = SCORE1000_BAR_CHART_X + idx * slot_w + (slot_w - expected_bar_width) / 2
        expected_y = expected_score_y
        expected_h = max(0.0, bar_origin_y - expected_score_y)
        expected_center_x = expected_x + expected_bar_width / 2
        bar = bars_by_label[label]
        if (bar.get("fill") or "").lower() != expected_bar_colors[label]:
            raise AuditFailure(f"{path}: {label} bar color mismatch")
        if bar.get("data-reader-key") != score1000_bar_reader_key(label):
            raise AuditFailure(f"{path}: {label} bar reader key mismatch")
        if label in SCORE1000_BAR_LOGO_ASSETS:
            if bar.get("data-logo-source") != rel(SCORE1000_BAR_LOGO_ASSETS[label]):
                raise AuditFailure(f"{path}: {label} bar logo source metadata mismatch")
        elif bar.get("data-logo-source") is not None:
            raise AuditFailure(f"{path}: {label} fallback badge bar must not claim a logo source")
        if bar.get("data-score2000-value") != score_label(row):
            raise AuditFailure(f"{path}: {label} bar Score2000 metadata mismatch")
        if bar.get("data-score1000-value") != score_label(row):
            raise AuditFailure(f"{path}: {label} bar score label metadata mismatch")
        for attr, expected in {"x": expected_x, "y": expected_y, "width": expected_bar_width, "height": expected_h}.items():
            actual = float(bar.get(attr, "nan"))
            if abs(actual - expected) > 0.1:
                raise AuditFailure(f"{path}: {label} bar {attr}={actual}, expected {expected}")
        value = value_by_label[label]
        if "".join(value.itertext()).strip() != score_label(row):
            raise AuditFailure(f"{path}: {label} visible score value mismatch")
        expected_font_size = SCORE1000_BAR_VALUE_FONT_SIZE * expected_bar_value_font_scale
        if f"font-size:{expected_font_size:.1f}px" not in (value.get("style") or ""):
            raise AuditFailure(f"{path}: {label} score value font-size mismatch")
        expected_value_y = expected_y - 22
        if expected_include_icons and row["reader_type"] == "Human comparator":
            expected_value_y = expected_y - SCORE1000_BAR_HUMAN_SCORE_GAP
        expected_value_fill = expected_bar_colors[label]
        if axis_break_y is not None and expected_value_y < expected_chart_y + 10:
            expected_value_y = expected_y + 42
            expected_value_fill = "#ffffff"
        if expected_value_fill not in (value.get("style") or "").lower():
            raise AuditFailure(f"{path}: {label} score value color mismatch")
        for attr, expected in {"x": expected_center_x, "y": expected_value_y}.items():
            actual = float(value.get(attr, "nan"))
            if abs(actual - expected) > 0.1:
                raise AuditFailure(f"{path}: {label} score value {attr}={actual}, expected {expected}")
        if label == "Human Expert Baseline":
            human_x_label_style = (x_label_by_label[label].get("style") or "").lower()
            if expected_bar_colors[label] not in human_x_label_style:
                raise AuditFailure(f"{path}: Human Expert Baseline x-axis label color mismatch")

    barcode_overlays = [
        elem for elem in root.findall(f".//{SVG_NS}g") if elem.get("class") == "score1000-barcode-overlay"
    ]
    barcode_capsules = [
        elem for elem in root.findall(f".//{SVG_NS}rect") if elem.get("class") == "score1000-barcode-capsule"
    ]
    if expected_include_barcode_overlay:
        if [str(elem.get("data-reader-label")) for elem in barcode_overlays] != expected_labels:
            raise AuditFailure(f"{path}: barcode overlay order mismatch")
        barcode_colors = outcome_palette_colors(expected_barcode_palette_key)
        capsules_by_label: dict[str, list[ET.Element]] = {label: [] for label in expected_labels}
        for elem in barcode_capsules:
            label = str(elem.get("data-reader-label"))
            if label not in capsules_by_label:
                raise AuditFailure(f"{path}: unexpected barcode capsule label {label}")
            capsules_by_label[label].append(elem)
        for idx, label in enumerate(expected_labels):
            row = by_label[label]
            score = score2000_value(row)
            expected_score_y = score1000_bar_scaled_y(
                score,
                y_min=expected_y_min,
                y_max=expected_y_max,
                chart_y=expected_chart_y,
                chart_h=expected_chart_h,
                axis_break_after=expected_axis_break_after,
                axis_break_top_fraction=expected_axis_break_top_fraction,
            )
            expected_x = SCORE1000_BAR_CHART_X + idx * slot_w + (slot_w - expected_bar_width) / 2
            expected_center_x = expected_x + expected_bar_width / 2
            expected_capsule_x = expected_center_x - expected_barcode_capsule_w / 2
            usable_h = max(
                0.0,
                bar_origin_y
                - expected_score_y
                - SCORE1000_BAR_BARCODE_TOP_PAD
                - SCORE1000_BAR_BARCODE_BOTTOM_PAD,
            )
            max_units = min(
                expected_barcode_units,
                int((usable_h + expected_barcode_capsule_gap) // (expected_barcode_capsule_h + expected_barcode_capsule_gap)),
            )
            expected_sequence = expected_score1000_bar_barcode_sequence(row, max_units)
            overlay = barcode_overlays[idx]
            if int(overlay.get("data-barcode-units", "0")) != len(expected_sequence):
                raise AuditFailure(f"{path}: {label} barcode overlay unit count mismatch")
            if int(overlay.get("data-barcode-source-units", "0")) != DOT_DISPLAY_TOTAL:
                raise AuditFailure(f"{path}: {label} barcode source unit count mismatch")
            if overlay.get("data-barcode-order") != "bottom-to-top":
                raise AuditFailure(f"{path}: {label} barcode order metadata mismatch")
            actual_capsules = sorted(
                capsules_by_label[label],
                key=lambda elem: int(elem.get("data-bottom-to-top-index", "-1")),
            )
            if len(actual_capsules) != len(expected_sequence):
                raise AuditFailure(
                    f"{path}: {label} expected {len(expected_sequence)} barcode capsules, got {len(actual_capsules)}"
                )
            expected_total_h = (
                len(expected_sequence) * expected_barcode_capsule_h
                + max(0, len(expected_sequence) - 1) * expected_barcode_capsule_gap
            )
            expected_start_y = bar_origin_y - SCORE1000_BAR_BARCODE_BOTTOM_PAD - expected_total_h
            for unit_idx, (elem, expected_bin) in enumerate(zip(actual_capsules, expected_sequence, strict=True)):
                expected_y = expected_start_y + (len(expected_sequence) - 1 - unit_idx) * (
                    expected_barcode_capsule_h + expected_barcode_capsule_gap
                )
                if elem.get("data-bin") != expected_bin:
                    raise AuditFailure(f"{path}: {label} barcode bin order mismatch at unit {unit_idx}")
                if (elem.get("fill") or "").lower() != barcode_colors[expected_bin]:
                    raise AuditFailure(f"{path}: {label} barcode fill mismatch at unit {unit_idx}")
                for attr, expected in {
                    "x": expected_capsule_x,
                    "y": expected_y,
                    "width": expected_barcode_capsule_w,
                    "height": expected_barcode_capsule_h,
                    "rx": expected_barcode_capsule_h / 2,
                }.items():
                    actual = float(elem.get(attr, "nan"))
                    if abs(actual - expected) > 0.1:
                        raise AuditFailure(f"{path}: {label} barcode capsule {attr}={actual}, expected {expected}")
    elif barcode_overlays or barcode_capsules:
        raise AuditFailure(f"{path}: barcode overlay emitted when disabled")

    icon_prefix = "score1000-bottom" if expected_logo_position == "bottom_under_labels" else "score1000-bar"
    icon_images = [
        elem for elem in root.findall(f".//{SVG_NS}image") if elem.get("class") == f"{icon_prefix}-logo"
    ]
    icon_backplates = [
        elem for elem in root.findall(f".//{SVG_NS}rect") if elem.get("class") == f"{icon_prefix}-logo-backplate"
    ]
    fallback_icons = [
        elem for elem in root.findall(f".//{SVG_NS}rect") if elem.get("class") == f"{icon_prefix}-logo-fallback"
    ]
    fallback_texts = [
        elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("data-score1000-bar-logo-fallback-text")
    ]
    if expected_include_icons:
        expected_asset_labels = [label for label in expected_labels if label in SCORE1000_BAR_LOGO_ASSETS]
        expected_badge_labels = [label for label in expected_labels if label in SCORE1000_BAR_FALLBACK_BADGES]
        expected_backplate_labels = (
            []
            if expected_logo_position == "bottom_under_labels"
            else [label for label in expected_asset_labels if by_label[label]["reader_type"] != "Human comparator"]
        )
        if (
            len(icon_images) != len(expected_asset_labels)
            or len(fallback_icons) != len(expected_badge_labels)
            or len(fallback_texts) != len(expected_badge_labels)
            or len(icon_backplates) != len(expected_backplate_labels)
        ):
            raise AuditFailure(
                f"{path}: expected {len(expected_asset_labels)} asset icons, {len(expected_badge_labels)} badges, "
                f"and {len(expected_backplate_labels)} backplates; got {len(icon_images)} asset icons, "
                f"{len(fallback_icons)} badges, {len(fallback_texts)} badge labels, and {len(icon_backplates)} backplates"
            )
        icons_by_label = {str(elem.get("data-score1000-bar-logo")): elem for elem in icon_images}
        fallback_by_label = {str(elem.get("data-score1000-bar-logo")): elem for elem in fallback_icons}
        fallback_text_by_label = {str(elem.get("data-score1000-bar-logo-fallback-text")): elem for elem in fallback_texts}
        backplates_by_label = {str(elem.get("data-score1000-bar-logo-backplate")): elem for elem in icon_backplates}
        if list(icons_by_label) != expected_asset_labels:
            raise AuditFailure(f"{path}: asset icon order mismatch: {list(icons_by_label)} != {expected_asset_labels}")
        if list(fallback_by_label) != expected_badge_labels:
            raise AuditFailure(f"{path}: fallback badge order mismatch: {list(fallback_by_label)} != {expected_badge_labels}")
        if list(fallback_text_by_label) != expected_badge_labels:
            raise AuditFailure(f"{path}: fallback badge text order mismatch")
        if list(backplates_by_label) != expected_backplate_labels:
            raise AuditFailure(f"{path}: icon backplate order mismatch")
        for idx, label in enumerate(expected_labels):
            row = by_label[label]
            score = score2000_value(row)
            expected_score_y = score1000_bar_scaled_y(
                score,
                y_min=expected_y_min,
                y_max=expected_y_max,
                chart_y=expected_chart_y,
                chart_h=expected_chart_h,
                axis_break_after=expected_axis_break_after,
                axis_break_top_fraction=expected_axis_break_top_fraction,
            )
            expected_bar_y = expected_score_y
            expected_center_x = (
                SCORE1000_BAR_CHART_X
                + idx * slot_w
                + (slot_w - expected_bar_width) / 2
                + expected_bar_width / 2
            )
            is_human = row["reader_type"] == "Human comparator"
            expected_icon_box = SCORE1000_BAR_LOGO_BOX * expected_bar_logo_scale
            expected_icon_image = expected_icon_box if is_human else SCORE1000_BAR_LOGO_IMAGE * expected_bar_logo_scale
            if label == "octomed_7b":
                expected_icon_image *= SCORE1000_BAR_OCTOMED_LOGO_SCALE
            expected_icon_image *= expected_bar_logo_image_multipliers.get(label, 1.0)
            expected_icon_box_x = expected_center_x - expected_icon_box / 2
            expected_value_y = expected_bar_y - 22
            if is_human:
                expected_value_y = expected_bar_y - SCORE1000_BAR_HUMAN_SCORE_GAP
            value_inside_bar_for_break = False
            if axis_break_y is not None and expected_value_y < expected_chart_y + 10:
                expected_value_y = expected_bar_y + 42
                value_inside_bar_for_break = True
            if expected_logo_position == "bottom_under_labels":
                if expected_bottom_logo_center_y is None:
                    raise AuditFailure(f"{path}: bottom-under-label logo variant missing expected center y")
                expected_icon_center_y = float(expected_bottom_logo_center_y)
                expected_icon_x = expected_center_x - expected_icon_image / 2
                expected_icon_y = expected_icon_center_y - expected_icon_image / 2
                if label in SCORE1000_BAR_LOGO_ASSETS:
                    icon = icons_by_label[label]
                    if icon.get("data-reader-label") != label:
                        raise AuditFailure(f"{path}: {label} bottom icon reader label mismatch")
                    if icon.get("data-reader-key") != score1000_bar_reader_key(label):
                        raise AuditFailure(f"{path}: {label} bottom icon reader key mismatch")
                    if icon.get("data-logo-kind") != "asset":
                        raise AuditFailure(f"{path}: {label} bottom icon kind mismatch")
                    if icon.get("data-source-logo") != rel(SCORE1000_BAR_LOGO_ASSETS[label]):
                        raise AuditFailure(f"{path}: {label} bottom icon logo source mismatch")
                    for attr, expected in {
                        "x": expected_icon_x,
                        "y": expected_icon_y,
                        "width": expected_icon_image,
                        "height": expected_icon_image,
                    }.items():
                        actual = float(icon.get(attr, "nan"))
                        if abs(actual - expected) > 0.1:
                            raise AuditFailure(f"{path}: {label} bottom icon {attr}={actual}, expected {expected}")
                else:
                    badge = fallback_by_label[label]
                    badge_text = fallback_text_by_label[label]
                    if badge.get("data-reader-label") != label:
                        raise AuditFailure(f"{path}: {label} fallback badge reader label mismatch")
                    if badge.get("data-reader-key") != score1000_bar_reader_key(label):
                        raise AuditFailure(f"{path}: {label} fallback badge reader key mismatch")
                    if badge.get("data-logo-kind") != "svg_text_badge":
                        raise AuditFailure(f"{path}: {label} fallback badge kind mismatch")
                    if badge.get("data-fallback-badge-label") != SCORE1000_BAR_FALLBACK_BADGES[label]["label"]:
                        raise AuditFailure(f"{path}: {label} fallback badge label mismatch")
                    for attr, expected in {
                        "x": expected_icon_x,
                        "y": expected_icon_y,
                        "width": expected_icon_image,
                        "height": expected_icon_image,
                    }.items():
                        actual = float(badge.get(attr, "nan"))
                        if abs(actual - expected) > 0.1:
                            raise AuditFailure(f"{path}: {label} fallback badge {attr}={actual}, expected {expected}")
                    if "".join(badge_text.itertext()).strip() != SCORE1000_BAR_FALLBACK_BADGES[label]["short_label"]:
                        raise AuditFailure(f"{path}: {label} fallback badge visible text mismatch")
                x_label_bottom = expected_x_label_y + expected_x_label_line_step * (2 - 1)
                if expected_icon_y <= x_label_bottom:
                    raise AuditFailure(f"{path}: {label} bottom logo overlaps x-label area")
                if expected_show_footer:
                    if expected_footer_divider_y - (expected_icon_y + expected_icon_image) < 12:
                        raise AuditFailure(f"{path}: {label} bottom logo too close to footer divider")
                elif expected_svg_h - (expected_icon_y + expected_icon_image) < 80:
                    raise AuditFailure(f"{path}: {label} bottom logo too close to frame bottom")
                continue

            if label not in SCORE1000_BAR_LOGO_ASSETS:
                raise AuditFailure(f"{path}: inside-bar icon layout cannot use fallback badge for {label}")
            expected_icon_y = (
                max(
                    SCORE1000_BAR_HUMAN_LOGO_Y,
                    expected_value_y - SCORE1000_BAR_HUMAN_LOGO_GAP - expected_icon_image,
                )
                if is_human
                else expected_bar_y + 30
            )
            if is_human:
                if label in backplates_by_label:
                    raise AuditFailure(f"{path}: human icon for {label} must not have a backplate")
            else:
                backplate = backplates_by_label[label]
                if backplate.get("data-reader-label") != label:
                    raise AuditFailure(f"{path}: {label} icon backplate reader label mismatch")
                if backplate.get("data-reader-key") != score1000_bar_reader_key(label):
                    raise AuditFailure(f"{path}: {label} icon backplate reader key mismatch")
                for attr, expected in {
                    "x": expected_icon_box_x,
                    "y": expected_icon_y,
                    "width": expected_icon_box,
                    "height": expected_icon_box,
                }.items():
                    actual = float(backplate.get(attr, "nan"))
                    if abs(actual - expected) > 0.1:
                        raise AuditFailure(f"{path}: {label} icon backplate {attr}={actual}, expected {expected}")
            icon = icons_by_label[label]
            if icon.get("data-reader-label") != label:
                raise AuditFailure(f"{path}: {label} icon reader label mismatch")
            if icon.get("data-reader-key") != score1000_bar_reader_key(label):
                raise AuditFailure(f"{path}: {label} icon reader key mismatch")
            if icon.get("data-source-logo") != rel(SCORE1000_BAR_LOGO_ASSETS[label]):
                raise AuditFailure(f"{path}: {label} icon logo source mismatch")
            for attr, expected in {
                "x": expected_center_x - expected_icon_image / 2,
                "y": expected_icon_y,
                "width": expected_icon_image,
                "height": expected_icon_image,
            }.items():
                if attr == "y" and not is_human:
                    expected = expected_icon_y + (expected_icon_box - expected_icon_image) / 2
                actual = float(icon.get(attr, "nan"))
                if abs(actual - expected) > 0.1:
                    raise AuditFailure(f"{path}: {label} icon {attr}={actual}, expected {expected}")
            if is_human:
                icon_bottom = expected_icon_y + expected_icon_image
                if value_inside_bar_for_break:
                    if not (expected_value_y > expected_bar_y and icon_bottom < expected_bar_y):
                        raise AuditFailure(f"{path}: human kink stack order must be score inside bar and icon above bar for {label}")
                    if expected_bar_y - icon_bottom < 12.0:
                        raise AuditFailure(f"{path}: human icon too close to kinked bar for {label}")
                else:
                    if not (expected_bar_y > expected_value_y > icon_bottom):
                        raise AuditFailure(f"{path}: human stack order must be bar, score, icon for {label}")
                    if expected_value_y - icon_bottom < SCORE1000_BAR_HUMAN_LOGO_GAP - 0.1:
                        raise AuditFailure(f"{path}: human score/icon gap too small for {label}")
    elif icon_images or icon_backplates or fallback_icons or fallback_texts:
        raise AuditFailure(f"{path}: bar icons emitted when icons are disabled")

    higher_is_better = [
        elem
        for elem in root.findall(f".//{SVG_NS}text")
        if "Higher is better" in "".join(elem.itertext())
    ]
    footer_lines = [elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("class") == expected_footer_cls]
    divider_lines = [
        elem
        for elem in root.findall(f".//{SVG_NS}line")
        if elem.get("class") == "axis"
        and abs(float(elem.get("y1", "nan")) - expected_footer_divider_y) <= 0.1
        and abs(float(elem.get("y2", "nan")) - expected_footer_divider_y) <= 0.1
        and abs(float(elem.get("x1", "nan")) - expected_footer_x) <= 0.1
        and abs(float(elem.get("x2", "nan")) - expected_footer_right_x) <= 0.1
    ]
    if not expected_show_footer:
        if higher_is_better:
            raise AuditFailure(f"{path}: fallback footer emitted when footer is suppressed")
        if footer_lines:
            raise AuditFailure(f"{path}: shared variant footer emitted when footer is suppressed")
        if divider_lines:
            raise AuditFailure(f"{path}: footer divider emitted when footer is suppressed")
    elif expected_variant_footer:
        if higher_is_better:
            raise AuditFailure(f"{path}: old Higher-is-better footer line must be removed")
        actual_footer_lines = ["".join(elem.itertext()).strip() for elem in footer_lines]
        if actual_footer_lines != expected_footer_lines:
            raise AuditFailure(f"{path}: variant footer text mismatch")
        for idx, elem in enumerate(footer_lines):
            if abs(float(elem.get("x", "nan")) - expected_footer_x) > 0.1:
                raise AuditFailure(f"{path}: variant footer x mismatch")
            expected_y = expected_footer_text_y + idx * expected_footer_line_step
            if abs(float(elem.get("y", "nan")) - expected_y) > 0.1:
                raise AuditFailure(f"{path}: variant footer line {idx} y mismatch")
            if expected_footer_font_px is not None and f"font-size:{float(expected_footer_font_px):.1f}px" not in (
                elem.get("style") or ""
            ):
                raise AuditFailure(f"{path}: variant footer font-size mismatch")
        if len(divider_lines) != 1:
            raise AuditFailure(f"{path}: expected one shared variant footer divider")
    else:
        if footer_lines:
            raise AuditFailure(f"{path}: shared variant footer emitted when disabled")


def audit_variant_svg(score_root: Path, out_dir: Path, rows: list[dict[str, str]]) -> None:
    by_label = {row["reader_label"]: row for row in rows}
    expected_sources = expected_source_csv_values(score_root)
    for filename in VARIANT_PANEL_FILES:
        spec = VARIANT_FILE_SPECS[filename]
        layout = str(spec["layout"])
        grouped = filename in VARIANT_GROUPED_FILES
        expected_order = (
            score2000_expected_labels(rows, list(spec["selected_reader_labels"]))  # type: ignore[index]
            if layout == "score1000_bar_chart"
            else grouped_row_labels(rows)
            if grouped
            else [row["reader_label"] for row in rows]
        )
        expected_colors = outcome_palette_colors(str(spec["palette_key"]))
        expected_category_colors = expected_variant_category_colors(filename)
        expected_svg_h = float(spec.get("svg_h", VARIANT_SVG_H))
        path = out_dir / filename
        root, payload = parse_svg(path)
        expected_viewboxes = {f"0 0 3600 {expected_svg_h}", f"0 0 3600 {expected_svg_h:g}"}
        if not close_enough(root.get("height", "nan"), expected_svg_h) or root.get("viewBox") not in expected_viewboxes:
            raise AuditFailure(f"{path}: variant SVG canvas must be 3600x{expected_svg_h}")
        expected_panel_id = 5 if layout == "score1000_bar_chart" else 2
        if int(payload.get("panel_id", 0)) != expected_panel_id:
            raise AuditFailure(f"{path}: variant panel_id must be {expected_panel_id}")
        if payload.get("variant") != spec["variant"]:
            raise AuditFailure(f"{path}: variant metadata mismatch")
        if payload.get("source_csv") not in expected_sources:
            raise AuditFailure(f"{path}: source_csv mismatch")
        audit_score1000_rule_metadata(payload, path)
        audit_score2000_rule_metadata(payload, path)
        if str(payload.get("source_master_sha256", "")).upper() != EXPECTED_SOURCE_SHA256:
            raise AuditFailure(f"{path}: source master SHA mismatch")
        payload_rows = payload.get("rows")
        if not isinstance(payload_rows, list) or len(payload_rows) != len(expected_order):
            raise AuditFailure(f"{path}: metadata row count mismatch")
        observed_order = []
        for item in payload_rows:
            if not isinstance(item, dict):
                raise AuditFailure(f"{path}: metadata row is not an object")
            label = str(item.get("reader_label", ""))
            observed_order.append(label)
            row = by_label.get(label)
            if row is None:
                raise AuditFailure(f"{path}: metadata row {label!r} not found in summary")
            if not close_enough(item.get("score2000", -999), row["score2000"]):
                raise AuditFailure(f"{path}: metadata {label} score2000 mismatch")
            bins = item.get("bins")
            if not isinstance(bins, dict):
                raise AuditFailure(f"{path}: metadata missing bins")
            for column in BIN_COLUMNS:
                if not close_enough(bins.get(column, -999), row[column]):
                    raise AuditFailure(f"{path}: metadata {label} {column} mismatch")
        if observed_order != expected_order:
            raise AuditFailure(f"{path}: row order mismatch: {observed_order}")
        if layout == "score1000_bar_chart":
            audit_variant_logos(root, payload, path)
            audit_variant_text_theme(root, payload, path, filename)
            audit_score1000_bar_chart(root, payload, path, filename, rows)
            continue
        audit_panel2_edge_justified(root, path)
        audit_b3_legend(root, path, 2, expected_colors=expected_colors)
        audit_visible_row_identity(root, path, score_header="Score")
        audit_variant_category_key(root, path, filename)
        audit_category_color_scope(root, path, expected_colors=expected_colors)
        audit_variant_outcome_palette(root, payload, path, filename)
        audit_variant_header_spacing(root, path, filename, show_group_headers=bool(spec.get("show_group_headers", False)))
        audit_variant_logos(root, payload, path)
        audit_variant_panel_title(root, path)
        audit_variant_text_theme(root, payload, path, filename)
        audit_variant_axis_legend_spacing(root, path, filename)
        audit_variant_accessible_layout(root, path, filename)
        audit_variant_text_colors(
            root,
            path,
            rows,
            show_group_headers=bool(spec.get("show_group_headers", False)),
            color_row_names=bool(spec.get("color_row_names", False)),
            color_scores=bool(spec.get("color_scores", False)),
            expected_category_colors=expected_category_colors,
        )
        texts = element_texts(root)
        if filename in VARIANT_RANK_FILES and any(text.endswith("models") for text in texts):
            raise AuditFailure(f"{path}: rank-preserving variant must not contain per-row/group model subtext")


def audit_promoted_panel5_svg(out_dir: Path, rows: list[dict[str, str]]) -> None:
    path = out_dir / PROMOTED_PANEL5_SVG
    root, payload = parse_svg(path)
    expected_labels = score2000_expected_labels(rows, PROMOTED_PANEL5_SELECTED_READER_LABELS)
    expected_keys = [PROMOTED_PANEL5_KEY_BY_READER_LABEL[label] for label in expected_labels]
    expected_display_labels = [PROMOTED_PANEL5_DISPLAY_BY_READER_LABEL[label] for label in expected_labels]
    by_label = {row["reader_label"]: row for row in rows}

    if root.get("width") != "3600" or not close_enough(root.get("height", "nan"), 2840.0):
        raise AuditFailure(f"{path}: promoted 5.4 SVG canvas must be 3600x2840")
    if root.get("viewBox") not in {"0 0 3600 2840", "0 0 3600 2840.0"}:
        raise AuditFailure(f"{path}: promoted 5.4 viewBox mismatch: {root.get('viewBox')}")
    doc_title = root.find(f"{SVG_NS}title")
    if doc_title is None or "".join(doc_title.itertext()).strip() != PROMOTED_PANEL5_TITLE:
        raise AuditFailure(f"{path}: promoted 5.4 SVG title mismatch")
    visible_score_title = [
        elem
        for elem in root.findall(f".//{SVG_NS}text")
        if elem.get("class") in {"title", "score1000-panel-title"}
        and "".join(elem.itertext()).strip() == EXPECTED_SCORE2000_BAR_TITLE
    ]
    if len(visible_score_title) != 1:
        raise AuditFailure(f"{path}: promoted 5.4 visible title must be {EXPECTED_SCORE2000_BAR_TITLE!r}")
    if abs(float(visible_score_title[0].get("y", "nan")) - 394.0) > 0.1:
        raise AuditFailure(f"{path}: promoted 5.4 visible title y mismatch")
    title_cls = str(visible_score_title[0].get("class"))
    inline_title_style = visible_score_title[0].get("style") or ""
    stylesheet = "\n".join("".join(elem.itertext()) for elem in root.findall(f".//{SVG_NS}style"))
    title_font_in_css = (
        f".{title_cls} " in stylesheet
        and ("font-size: 80px" in stylesheet or "font-size:80px" in stylesheet or "font-size: 80.0px" in stylesheet)
    )
    if f"font-size:{80.0:.1f}px" not in inline_title_style and not title_font_in_css:
        raise AuditFailure(f"{path}: promoted 5.4 visible title font-size mismatch")
    if payload.get("promoted_panel_variant") != "5.4":
        raise AuditFailure(f"{path}: promoted 5.4 metadata missing promoted_panel_variant")
    if payload.get("variant") != PROMOTED_PANEL5_TITLE:
        raise AuditFailure(f"{path}: promoted 5.4 metadata variant mismatch")
    if payload.get("display_score_column") != "score2000":
        raise AuditFailure(f"{path}: promoted 5.4 display score metadata mismatch")
    if payload.get("logo_binding_key") != "reader_label":
        raise AuditFailure(f"{path}: promoted 5.4 logo binding metadata mismatch")
    if payload.get("bar_slot_source") != "data-score1000-bar":
        raise AuditFailure(f"{path}: promoted 5.4 bar slot source metadata mismatch")
    if payload.get("logo_layout") != PROMOTED_PANEL5_LOGO_LAYOUT:
        raise AuditFailure(f"{path}: promoted 5.4 logo layout metadata mismatch")
    if payload.get("promotion_series_order") != expected_keys:
        raise AuditFailure(f"{path}: promoted 5.4 metadata order mismatch: {payload.get('promotion_series_order')}")
    promotion_bar_slots = payload.get("promotion_bar_slots")
    if not isinstance(promotion_bar_slots, list) or len(promotion_bar_slots) != len(expected_labels):
        raise AuditFailure(f"{path}: promoted 5.4 promotion bar slot metadata mismatch")
    if [str(item.get("reader_label")) for item in promotion_bar_slots if isinstance(item, dict)] != expected_labels:
        raise AuditFailure(f"{path}: promoted 5.4 promotion bar slot order mismatch")
    chart_meta = payload.get("score1000_bar_chart")
    if not isinstance(chart_meta, dict):
        raise AuditFailure(f"{path}: promoted 5.4 metadata missing score1000_bar_chart")
    if chart_meta.get("logo_binding_key") != "reader_label":
        raise AuditFailure(f"{path}: promoted 5.4 chart logo binding metadata mismatch")
    if chart_meta.get("bar_slot_source") != "data-score1000-bar":
        raise AuditFailure(f"{path}: promoted 5.4 chart bar slot source metadata mismatch")
    if chart_meta.get("logo_layout") != PROMOTED_PANEL5_LOGO_LAYOUT:
        raise AuditFailure(f"{path}: promoted 5.4 chart logo layout metadata mismatch")
    if not close_enough(chart_meta.get("bottom_logo_center_y", "nan"), PROMOTED_PANEL5_BOTTOM_LOGO_CENTER_Y):
        raise AuditFailure(f"{path}: promoted 5.4 bottom logo center y metadata mismatch")
    if chart_meta.get("bottom_logo_series_order") != expected_keys:
        raise AuditFailure(f"{path}: promoted 5.4 chart metadata bottom-logo order mismatch")
    bottom_logo_bar_slots = chart_meta.get("bottom_logo_bar_slots")
    if not isinstance(bottom_logo_bar_slots, list) or len(bottom_logo_bar_slots) != len(expected_labels):
        raise AuditFailure(f"{path}: promoted 5.4 chart bottom-logo bar slot metadata mismatch")
    if [str(item.get("reader_label")) for item in bottom_logo_bar_slots if isinstance(item, dict)] != expected_labels:
        raise AuditFailure(f"{path}: promoted 5.4 chart bottom-logo bar slot order mismatch")
    if chart_meta.get("display_score_column") != "score2000":
        raise AuditFailure(f"{path}: promoted 5.4 chart display score column mismatch")
    if not close_enough(chart_meta.get("y_min", "nan"), 0.0):
        raise AuditFailure(f"{path}: promoted 5.4 chart y_min metadata mismatch")
    if not close_enough(chart_meta.get("y_max", "nan"), 2000.0):
        raise AuditFailure(f"{path}: promoted 5.4 chart y_max metadata mismatch")
    if not close_enough(chart_meta.get("bar_origin", "nan"), 0.0):
        raise AuditFailure(f"{path}: promoted 5.4 chart bar origin metadata mismatch")
    if not close_enough(chart_meta.get("reference_line", "nan"), SCORE2000_BASELINE):
        raise AuditFailure(f"{path}: promoted 5.4 chart reference line metadata mismatch")
    if chart_meta.get("ticks") != SCORE1000_BAR_A1_TICKS:
        raise AuditFailure(f"{path}: promoted 5.4 chart tick metadata mismatch")
    if not close_enough(chart_meta.get("axis_break_after", "nan"), SCORE1000_BAR_AXIS_BREAK_AFTER):
        raise AuditFailure(f"{path}: promoted 5.4 chart axis_break_after metadata mismatch")
    if chart_meta.get("axis_break_style") != "a1_double_slash":
        raise AuditFailure(f"{path}: promoted 5.4 chart axis_break_style metadata mismatch")
    if not close_enough(
        chart_meta.get("axis_break_top_fraction", "nan"), SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION
    ):
        raise AuditFailure(f"{path}: promoted 5.4 chart axis_break_top_fraction metadata mismatch")

    texts = root.findall(f".//{SVG_NS}text")
    footer_lines = [
        "".join(elem.itertext()).strip()
        for elem in texts
        if elem.get("class") == "score1000-footer"
    ]
    if footer_lines != promoted_panel5_footer_lines(IDK_SCORE):
        raise AuditFailure(f"{path}: promoted 5.4 footer text mismatch: {footer_lines}")
    if any("left of each reader/model" in line for line in footer_lines):
        raise AuditFailure(f"{path}: promoted 5.4 footer still describes left-side row labels")
    promoted_axis_titles = [
        elem
        for elem in texts
        if elem.get("class") == "score1000-axis-title" and "".join(elem.itertext()).strip() == EXPECTED_SCORE2000_BAR_AXIS_TITLE
    ]
    if len(promoted_axis_titles) != 1:
        raise AuditFailure(f"{path}: promoted 5.4 expected one y-axis title")
    expected_axis_title_transform = (
        f"translate({SCORE1000_BAR_CHART_X - SCORE1000_BAR_AXIS_TITLE_X_OFFSET:.1f} "
        f"{float(chart_meta.get('chart_y', SCORE1000_BAR_CHART_Y)) + SCORE1000_BAR_CHART_H / 2:.1f}) rotate(-90)"
    )
    if promoted_axis_titles[0].get("transform") != expected_axis_title_transform:
        raise AuditFailure(f"{path}: promoted 5.4 y-axis title transform mismatch")
    bars = [elem for elem in root.findall(f".//{SVG_NS}rect") if elem.get("data-score1000-bar") == "true"]
    tick_lines = [
        elem for elem in root.findall(f".//{SVG_NS}line") if elem.get("data-score1000-tick") is not None
    ]
    all_images = root.findall(f".//{SVG_NS}image")
    if not texts or len(bars) != len(expected_labels) or not tick_lines:
        raise AuditFailure(
            f"{path}: promoted 5.4 must be an inspectable vector SVG with text, bars, and ticks "
            f"(texts={len(texts)}, bars={len(bars)}, ticks={len(tick_lines)}, images={len(all_images)})"
        )
    if len(all_images) == 1 and not bars:
        raise AuditFailure(f"{path}: promoted 5.4 is still a one-image PNG wrapper")

    observed_bar_labels = [str(elem.get("data-reader-label")) for elem in bars]
    if observed_bar_labels != expected_labels:
        raise AuditFailure(f"{path}: promoted 5.4 bar order mismatch: {observed_bar_labels} != {expected_labels}")
    bars_by_label = {str(elem.get("data-reader-label")): elem for elem in bars}
    tick_values = sorted(int(float(elem.get("data-score1000-tick", "nan"))) for elem in tick_lines)
    if tick_values != SCORE1000_BAR_TICKS:
        raise AuditFailure(f"{path}: promoted 5.4 tick values mismatch: {tick_values}")
    for elem in tick_lines:
        if elem.get("class") != "score2000-grid":
            raise AuditFailure(f"{path}: promoted 5.4 tick {elem.get('data-score1000-tick')} must render as faint score2000-grid")
    tick_labels = [
        elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("data-score1000-tick-label") is not None
    ]
    if sorted(int(float(elem.get("data-score1000-tick-label", "nan"))) for elem in tick_labels) != SCORE1000_BAR_TICKS:
        raise AuditFailure(f"{path}: promoted 5.4 y-axis tick label mismatch")
    expected_tick_label_x = SCORE1000_BAR_CHART_X - SCORE1000_BAR_TICK_LABEL_X_OFFSET
    for elem in tick_labels:
        if elem.get("text-anchor") != "end":
            raise AuditFailure(f"{path}: promoted 5.4 y-axis tick label anchor mismatch")
        if abs(float(elem.get("x", "nan")) - expected_tick_label_x) > 0.1:
            raise AuditFailure(f"{path}: promoted 5.4 y-axis tick label x mismatch")
    x_labels = [
        elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("data-score1000-x-label") is not None
    ]
    if [str(elem.get("data-score1000-x-label")) for elem in x_labels] != expected_labels:
        raise AuditFailure(f"{path}: promoted 5.4 x-axis label order mismatch")
    x_label_css = "\n".join(line for line in stylesheet.splitlines() if ".score1000-x-label" in line)
    expected_x_label_css = (
        f"font-size: {SCORE1000_BAR_X_LABEL_FONT_SIZE:g}px",
        f"font-size:{SCORE1000_BAR_X_LABEL_FONT_SIZE:g}px",
        f"font-size: {SCORE1000_BAR_X_LABEL_FONT_SIZE:.1f}px",
    )
    if not x_label_css or not any(token in x_label_css for token in expected_x_label_css):
        raise AuditFailure(f"{path}: promoted 5.4 x-axis label font-size CSS mismatch")
    for elem in x_labels:
        tspans = elem.findall(f"{SVG_NS}tspan")
        for tspan_idx, tspan in enumerate(tspans):
            expected_dy = 0.0 if tspan_idx == 0 else SCORE1000_BAR_X_LABEL_LINE_STEP
            if abs(float(tspan.get("dy", "nan")) - expected_dy) > 0.1:
                raise AuditFailure(f"{path}: promoted 5.4 x-axis label line-step mismatch")
    zero_lines = [
        elem for elem in root.findall(f".//{SVG_NS}line") if elem.get("data-score1000-zero-line") == "true"
    ]
    if len(zero_lines) != 1:
        raise AuditFailure(f"{path}: promoted 5.4 expected one shifted-baseline line, got {len(zero_lines)}")
    if zero_lines[0].get("class") != "score2000-grid":
        raise AuditFailure(f"{path}: promoted 5.4 shifted baseline must render as faint score2000-grid")
    chart_y = float(chart_meta.get("chart_y", SCORE1000_BAR_CHART_Y))
    slot_w = SCORE1000_BAR_CHART_W / len(expected_labels)
    origin_y = score1000_bar_scaled_y(
        0.0,
        y_min=0.0,
        y_max=2000.0,
        chart_y=chart_y,
        chart_h=SCORE1000_BAR_CHART_H,
        axis_break_after=SCORE1000_BAR_AXIS_BREAK_AFTER,
        axis_break_top_fraction=SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
    )
    reference_y = score1000_bar_scaled_y(
        SCORE2000_BASELINE,
        y_min=0.0,
        y_max=2000.0,
        chart_y=chart_y,
        chart_h=SCORE1000_BAR_CHART_H,
        axis_break_after=SCORE1000_BAR_AXIS_BREAK_AFTER,
        axis_break_top_fraction=SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
    )
    actual_reference_y = float(zero_lines[0].get("y1", "nan"))
    if abs(actual_reference_y - reference_y) > 0.1:
        raise AuditFailure(f"{path}: promoted 5.4 shifted reference line y mismatch")
    axis_break_marks = [
        elem for elem in root.findall(f".//{SVG_NS}line") if elem.get("data-score2000-axis-break-mark") == "true"
    ]
    if len(axis_break_marks) != 2:
        raise AuditFailure(f"{path}: promoted 5.4 expected two A1 axis-break marks, got {len(axis_break_marks)}")
    expected_break_y = score1000_bar_axis_break_y(
        chart_y,
        SCORE1000_BAR_CHART_H,
        SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
    )
    actual_midpoints = sorted((float(elem.get("y1", "nan")) + float(elem.get("y2", "nan"))) / 2 for elem in axis_break_marks)
    expected_midpoints = sorted([expected_break_y - 13.0, expected_break_y + 13.0])
    for actual, expected in zip(actual_midpoints, expected_midpoints, strict=True):
        if abs(actual - expected) > 0.1:
            raise AuditFailure(f"{path}: promoted 5.4 A1 axis-break mark midpoint {actual}, expected {expected}")
    for elem in axis_break_marks:
        if elem.get("class") != "score2000-axis-break-mark":
            raise AuditFailure(f"{path}: promoted 5.4 A1 axis-break mark class mismatch")
    value_labels = [
        elem for elem in root.findall(f".//{SVG_NS}text") if elem.get("class") == "score1000-bar-value"
    ]
    values_by_label = {str(elem.get("data-reader-label")): elem for elem in value_labels}
    if set(values_by_label) != set(expected_labels):
        raise AuditFailure(f"{path}: promoted 5.4 score value labels mismatch")
    for idx, (reader_label, bar) in enumerate(zip(expected_labels, bars)):
        expected_score = score2000_value(by_label[reader_label])
        expected_score_y = score1000_bar_scaled_y(
            expected_score,
            y_min=0.0,
            y_max=2000.0,
            chart_y=chart_y,
            chart_h=SCORE1000_BAR_CHART_H,
            axis_break_after=SCORE1000_BAR_AXIS_BREAK_AFTER,
            axis_break_top_fraction=SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
        )
        expected_x = SCORE1000_BAR_CHART_X + idx * slot_w + (slot_w - SCORE1000_BAR_W) / 2
        expected_h = max(0.0, origin_y - expected_score_y)
        if bar.get("data-reader-key") != PROMOTED_PANEL5_KEY_BY_READER_LABEL[reader_label]:
            raise AuditFailure(f"{path}: promoted 5.4 {reader_label} bar reader key mismatch")
        if bar.get("data-logo-source") != rel(SCORE1000_BAR_LOGO_ASSETS[reader_label]):
            raise AuditFailure(f"{path}: promoted 5.4 {reader_label} bar logo source metadata mismatch")
        if bar.get("data-score2000-value") != score_label(by_label[reader_label]):
            raise AuditFailure(f"{path}: promoted 5.4 {reader_label} bar Score2000 metadata mismatch")
        for attr, expected in {"x": expected_x, "y": expected_score_y, "width": SCORE1000_BAR_W, "height": expected_h}.items():
            actual = float(bar.get(attr, "nan"))
            if abs(actual - expected) > 0.1:
                raise AuditFailure(f"{path}: promoted 5.4 {reader_label} positive bar {attr}={actual}, expected {expected}")
        value = values_by_label[reader_label]
        expected_font_size = SCORE1000_BAR_VALUE_FONT_SIZE
        if f"font-size:{expected_font_size:.1f}px" not in (value.get("style") or ""):
            raise AuditFailure(f"{path}: promoted 5.4 {reader_label} score value font-size mismatch")
        expected_value_y = expected_score_y - 22
        if expected_value_y < SCORE1000_BAR_CHART_Y_5_1 + 10:
            expected_value_y = expected_score_y + 42
        if abs(float(value.get("y", "nan")) - expected_value_y) > 0.1:
            raise AuditFailure(f"{path}: promoted 5.4 {reader_label} score label y mismatch")

    if root.findall(f".//{SVG_NS}rect[@class='score1000-logo-ribbon']"):
        raise AuditFailure(f"{path}: promoted 5.4 must not contain a top logo ribbon rectangle")
    if root.findall(f".//{SVG_NS}line[@class='score1000-ribbon-guide']"):
        raise AuditFailure(f"{path}: promoted 5.4 must not contain top ribbon guide lines")
    bottom_logo_groups = [
        elem for elem in root.findall(f".//{SVG_NS}g") if elem.get("id") == "panel-5-4-bottom-logos"
    ]
    if len(bottom_logo_groups) != 1:
        raise AuditFailure(f"{path}: promoted 5.4 expected one bottom-logo group, got {len(bottom_logo_groups)}")
    expected_order_attr = "|".join(expected_keys)
    group = bottom_logo_groups[0]
    if group.get("data-series-order") != expected_order_attr:
        raise AuditFailure(f"{path}: promoted 5.4 bottom-logo order attr mismatch")
    if group.get("data-logo-binding-key") != "reader_label":
        raise AuditFailure(f"{path}: promoted 5.4 bottom-logo binding key mismatch")
    if group.get("data-bar-slot-source") != "data-score1000-bar":
        raise AuditFailure(f"{path}: promoted 5.4 bottom-logo bar slot source mismatch")
    if group.get("data-logo-layout") != PROMOTED_PANEL5_LOGO_LAYOUT:
        raise AuditFailure(f"{path}: promoted 5.4 bottom-logo layout attr mismatch")
    if not close_enough(group.get("data-logo-center-y", "nan"), PROMOTED_PANEL5_BOTTOM_LOGO_CENTER_Y):
        raise AuditFailure(f"{path}: promoted 5.4 bottom-logo center y attr mismatch")

    logos = [elem for elem in root.findall(f".//{SVG_NS}image") if elem.get("class") == "score1000-bottom-logo"]
    if len(logos) != len(expected_keys):
        raise AuditFailure(f"{path}: promoted 5.4 expected {len(expected_keys)} bottom logos, got {len(logos)}")
    logo_order = [str(elem.get("data-reader-label")) for elem in logos]
    if logo_order != expected_labels:
        raise AuditFailure(f"{path}: promoted 5.4 bottom-logo reader-label order mismatch logos={logo_order}")
    logos_by_label = {str(elem.get("data-reader-label")): elem for elem in logos}
    if set(logos_by_label) != set(expected_labels):
        raise AuditFailure(f"{path}: promoted 5.4 bottom-logo reader-label set mismatch")
    x_label_y = max(
        float(elem.get("y", "nan"))
        for elem in root.findall(f".//{SVG_NS}text")
        if elem.get("data-score1000-x-label") is not None
    )
    for idx, reader_label in enumerate(expected_labels):
        logo = logos_by_label[reader_label]
        key = PROMOTED_PANEL5_KEY_BY_READER_LABEL[reader_label]
        display_label = PROMOTED_PANEL5_DISPLAY_BY_READER_LABEL[reader_label]
        if logo.get("data-reader-key") != key:
            raise AuditFailure(f"{path}: promoted 5.4 bottom-logo key mismatch for {reader_label}")
        if logo.get("data-reader-display-label") != display_label:
            raise AuditFailure(f"{path}: promoted 5.4 bottom-logo display label mismatch for {reader_label}")
        if logo.get("data-bound-bar-label") != reader_label:
            raise AuditFailure(f"{path}: promoted 5.4 bottom-logo bound bar label mismatch for {reader_label}")
        if logo.get("data-source-logo") != Path(str(SCORE1000_BAR_LOGO_ASSETS[reader_label])).name:
            raise AuditFailure(f"{path}: promoted 5.4 bottom-logo source mismatch for {reader_label}")
        if int(logo.get("data-series-index", "-1")) != idx:
            raise AuditFailure(f"{path}: promoted 5.4 bottom-logo series index mismatch for {reader_label}")
        expected_score = score2000_value(by_label[reader_label])
        actual_logo_score = float(logo.get("data-score2000-value", "nan"))
        if abs(actual_logo_score - expected_score) > 0.001:
            raise AuditFailure(f"{path}: promoted 5.4 score metadata mismatch for {reader_label}")
        bound_bar = bars_by_label[reader_label]
        expected_center_x = float(bound_bar.get("x", "nan")) + float(bound_bar.get("width", "nan")) / 2
        actual_logo_center_x = float(logo.get("x", "nan")) + float(logo.get("width", "nan")) / 2
        if abs(actual_logo_center_x - expected_center_x) > 0.1:
            raise AuditFailure(f"{path}: promoted 5.4 bottom-logo x-position mismatch for {reader_label}")
        actual_logo_center_y = float(logo.get("y", "nan")) + float(logo.get("height", "nan")) / 2
        if abs(actual_logo_center_y - PROMOTED_PANEL5_BOTTOM_LOGO_CENTER_Y) > 0.1:
            raise AuditFailure(f"{path}: promoted 5.4 bottom-logo y-position mismatch for {reader_label}")
        logo_y = float(logo.get("y", "nan"))
        logo_bottom = logo_y + float(logo.get("height", "nan"))
        if logo_y <= x_label_y + 55:
            raise AuditFailure(f"{path}: promoted 5.4 bottom-logo too close to x-axis label for {reader_label}")
        if logo_bottom >= 2500.0 - 20:
            raise AuditFailure(f"{path}: promoted 5.4 bottom-logo too close to footer divider for {reader_label}")


def audit_required_files(out_dir: Path) -> None:
    missing = [name for name in REQUIRED_FILES if not (out_dir / name).exists()]
    if missing:
        raise AuditFailure(f"Missing panel package files: {missing}")
    extra_panels = sorted(path.name for path in out_dir.glob("panel_*.svg") if path.name not in PANEL_FILES)
    if extra_panels:
        raise AuditFailure(f"Unexpected panel files: {extra_panels}")
    for path in out_dir.iterdir():
        if path.is_file() and path.suffix.lower() in {".svg", ".html", ".md", ".json", ".txt", ".csv"}:
            scan_text(path)


def audit_variant_required_files(out_dir: Path) -> None:
    missing = [name for name in VARIANT_REQUIRED_FILES if not (out_dir / name).exists()]
    if missing:
        raise AuditFailure(f"Missing variant package files: {missing}")
    missing_promoted = [name for name in PROMOTED_PANEL5_FILES if not (out_dir / name).exists()]
    if missing_promoted:
        raise AuditFailure(f"Missing promoted Panel 5 files: {missing_promoted}")
    allowed_panel_files = set(VARIANT_PANEL_FILES) | {
        name for name in PROMOTED_PANEL5_FILES if name.endswith(".svg")
    }
    extra_panels = sorted(path.name for path in out_dir.glob("panel_*.svg") if path.name not in allowed_panel_files)
    if extra_panels:
        raise AuditFailure(f"Unexpected variant panel files: {extra_panels}")
    for path in out_dir.iterdir():
        if path.is_file() and path.suffix.lower() in {".svg", ".html", ".md", ".json", ".txt", ".csv"}:
            scan_text(path)
    contact_sheet = (out_dir / "contact_sheet.html").read_text(encoding="utf-8")
    if contact_sheet.count("promoted-panel-5-4-start") != 1 or contact_sheet.count("promoted-panel-5-4-end") != 1:
        raise AuditFailure("Variant contact sheet must include exactly one promoted Panel 5.4 card")
    if PROMOTED_PANEL5_SVG not in contact_sheet or "Panel 5.4." not in contact_sheet:
        raise AuditFailure("Variant contact sheet missing promoted Panel 5.4 content")
    for name in ("captions.md", "data_provenance.md", "reviewer_checklist.md"):
        text = (out_dir / name).read_text(encoding="utf-8")
        if text.count("promoted-panel-5-4-support-start") != 1 or text.count("promoted-panel-5-4-support-end") != 1:
            raise AuditFailure(f"{name} must include exactly one promoted Panel 5.4 support block")
        if "5.4" not in text:
            raise AuditFailure(f"{name} missing promoted Panel 5.4 support text")
    data_provenance = json.loads((out_dir / "data_provenance.json").read_text(encoding="utf-8"))
    if PROMOTED_PANEL5_SVG not in data_provenance.get("panels", []):
        raise AuditFailure("data_provenance.json panels list missing promoted Panel 5.4")
    promoted = data_provenance.get("promoted_variant_5_4")
    if not isinstance(promoted, dict) or promoted.get("file") != PROMOTED_PANEL5_SVG:
        raise AuditFailure("data_provenance.json missing promoted Panel 5.4 metadata")
    if promoted.get("logo_binding_key") != "reader_label" or promoted.get("bar_slot_source") != "data-score1000-bar":
        raise AuditFailure("data_provenance.json promoted Panel 5.4 logo binding metadata mismatch")
    if promoted.get("logo_layout") != PROMOTED_PANEL5_LOGO_LAYOUT:
        raise AuditFailure("data_provenance.json promoted Panel 5.4 logo layout metadata mismatch")
    if not close_enough(promoted.get("bottom_logo_center_y", "nan"), PROMOTED_PANEL5_BOTTOM_LOGO_CENTER_Y):
        raise AuditFailure("data_provenance.json promoted Panel 5.4 bottom logo center metadata mismatch")
    promoted_bar_slots = promoted.get("bar_slots")
    if not isinstance(promoted_bar_slots, list) or len(promoted_bar_slots) != len(PROMOTED_PANEL5_SELECTED_READER_LABELS):
        raise AuditFailure("data_provenance.json promoted Panel 5.4 bar slot metadata mismatch")


def audit_manifest(out_dir: Path) -> None:
    manifest = json.loads((out_dir / "figure_manifest.json").read_text(encoding="utf-8"))
    panel_set = {int(panel["panel_id"]) for panel in manifest.get("panels", [])}
    if panel_set != {2, 3}:
        raise AuditFailure(f"Manifest panel set must be {{2,3}}, got {panel_set}")
    by_path = {entry["path"]: entry for entry in manifest.get("files", [])}
    for name in REQUIRED_FILES:
        if name == "figure_manifest.json":
            continue
        path = out_dir / name
        key = rel(path)
        entry = by_path.get(key)
        if entry is None:
            raise AuditFailure(f"Manifest missing {key}")
        if str(entry.get("sha256", "")).upper() != sha256_file(path):
            raise AuditFailure(f"Manifest SHA mismatch for {key}")


def audit_variant_manifest(out_dir: Path) -> None:
    manifest = json.loads((out_dir / "figure_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("mode") != "model-group-color-final":
        raise AuditFailure("Variant manifest mode mismatch")
    panel_files = {panel.get("file") for panel in manifest.get("panels", [])}
    expected_panel_files = set(VARIANT_PANEL_FILES) | {PROMOTED_PANEL5_SVG}
    if panel_files != expected_panel_files:
        raise AuditFailure(f"Variant manifest panel files mismatch: {panel_files}")
    panels_by_file = {panel.get("file"): panel for panel in manifest.get("panels", []) if isinstance(panel, dict)}
    for filename, spec in VARIANT_FILE_SPECS.items():
        panel = panels_by_file.get(filename)
        if panel is None:
            raise AuditFailure(f"Variant manifest missing panel entry for {filename}")
        for key in ("panel_id", "variant", "layout", "palette_key"):
            if panel.get(key) != spec[key]:
                raise AuditFailure(f"Variant manifest {filename} {key} mismatch: {panel.get(key)} != {spec[key]}")
        if panel.get("category_colors") != expected_variant_category_colors(filename):
            raise AuditFailure(f"Variant manifest {filename} category_colors mismatch")
        expected_text_colors = expected_variant_text_colors(filename)
        if expected_text_colors is None:
            if "text_colors" in panel:
                raise AuditFailure(f"Variant manifest {filename} unexpected text_colors")
        elif panel.get("text_colors") != expected_text_colors:
            raise AuditFailure(f"Variant manifest {filename} text_colors mismatch")
        if bool(panel.get("color_scores", False)) != bool(spec.get("color_scores", False)):
            raise AuditFailure(f"Variant manifest {filename} color_scores mismatch")
        if spec["layout"] == "score1000_bar_chart":
            expected_selected = score2000_expected_labels(
                read_csv(out_dir / "score1000_panel23_bins.csv"),
                list(spec["selected_reader_labels"]),  # type: ignore[arg-type]
            )
            if panel.get("selected_reader_labels") != expected_selected:
                raise AuditFailure(f"Variant manifest {filename} selected_reader_labels mismatch")
            if panel.get("bar_colors") != expected_variant_bar_colors(filename):
                raise AuditFailure(f"Variant manifest {filename} bar_colors mismatch")
            if bool(panel.get("include_score_gap_overlay", False)) != bool(
                spec.get("include_score_gap_overlay", False)
            ):
                raise AuditFailure(f"Variant manifest {filename} include_score_gap_overlay mismatch")
            if panel.get("score_gap_date_label") != spec.get("score_gap_date_label"):
                raise AuditFailure(f"Variant manifest {filename} score_gap_date_label mismatch")
            if panel.get("bar_logo_image_multipliers", {}) != dict(spec.get("bar_logo_image_multipliers", {})):
                raise AuditFailure(f"Variant manifest {filename} bar_logo_image_multipliers mismatch")
            if panel.get("logo_position") != spec.get("logo_position", "inside_bar"):
                raise AuditFailure(f"Variant manifest {filename} logo_position mismatch")
            if "bottom_logo_center_y" in spec and not close_enough(
                panel.get("bottom_logo_center_y", "nan"),
                float(spec["bottom_logo_center_y"]),
            ):
                raise AuditFailure(f"Variant manifest {filename} bottom_logo_center_y mismatch")
    promoted_panel = panels_by_file.get(PROMOTED_PANEL5_SVG)
    if promoted_panel is None:
        raise AuditFailure(f"Variant manifest missing promoted panel entry for {PROMOTED_PANEL5_SVG}")
    expected_promoted_labels = score2000_expected_labels(
        read_csv(out_dir / "score1000_panel23_bins.csv"),
        PROMOTED_PANEL5_SELECTED_READER_LABELS,
    )
    expected_promoted_keys = [PROMOTED_PANEL5_KEY_BY_READER_LABEL[label] for label in expected_promoted_labels]
    promoted_expected = {
        "panel_id": "5.4",
        "variant": PROMOTED_PANEL5_TITLE,
        "layout": PROMOTED_PANEL5_LAYOUT,
        "palette_key": "option_c_teal_green_to_current_red",
        "selected_reader_labels": expected_promoted_labels,
        "reader_keys": expected_promoted_keys,
        "score_y_min": 0.0,
        "score_y_max": 2000.0,
        "score_ticks": SCORE1000_BAR_TICKS,
        "display_score_column": "score2000",
        "logo_binding_key": "reader_label",
        "bar_slot_source": "data-score1000-bar",
        "logo_layout": PROMOTED_PANEL5_LOGO_LAYOUT,
        "bottom_logo_center_y": PROMOTED_PANEL5_BOTTOM_LOGO_CENTER_Y,
    }
    for key, expected in promoted_expected.items():
        if promoted_panel.get(key) != expected:
            raise AuditFailure(f"Variant manifest promoted 5.4 {key} mismatch: {promoted_panel.get(key)} != {expected}")
    promoted_series = promoted_panel.get("series")
    if not isinstance(promoted_series, list) or len(promoted_series) != len(expected_promoted_labels):
        raise AuditFailure("Variant manifest promoted 5.4 series metadata mismatch")
    if [item.get("key") for item in promoted_series if isinstance(item, dict)] != expected_promoted_keys:
        raise AuditFailure("Variant manifest promoted 5.4 series order mismatch")
    promoted_bar_slots = promoted_panel.get("bar_slots")
    if not isinstance(promoted_bar_slots, list) or len(promoted_bar_slots) != len(expected_promoted_labels):
        raise AuditFailure("Variant manifest promoted 5.4 bar slot metadata mismatch")
    if [item.get("reader_label") for item in promoted_bar_slots if isinstance(item, dict)] != expected_promoted_labels:
        raise AuditFailure("Variant manifest promoted 5.4 bar slot order mismatch")
    if promoted_panel.get("score2000_rule") != {
        "formula": "score2000 = final_score1000 + 1000",
        "display_range": [0, 2000],
        "source_range": [-1000, 1000],
        "rank_preserving": True,
    }:
        raise AuditFailure("Variant manifest promoted 5.4 Score2000 rule mismatch")
    palettes = manifest.get("outcome_palettes")
    if not isinstance(palettes, dict):
        raise AuditFailure("Variant manifest missing outcome_palettes")
    expected_palette_keys = {str(spec["palette_key"]) for spec in VARIANT_FILE_SPECS.values()}
    if set(palettes) != expected_palette_keys:
        raise AuditFailure(f"Variant manifest palette keys mismatch: {set(palettes)} != {expected_palette_keys}")
    for key in expected_palette_keys:
        if palettes.get(key) != outcome_palette_metadata(key):
            raise AuditFailure(f"Variant manifest outcome palette metadata mismatch for {key}")
    by_path = {entry["path"]: entry for entry in manifest.get("files", [])}
    for name in VARIANT_REQUIRED_FILES:
        if name == "figure_manifest.json":
            continue
        path = out_dir / name
        key = rel(path)
        entry = by_path.get(key)
        if entry is None:
            raise AuditFailure(f"Variant manifest missing {key}")
        if str(entry.get("sha256", "")).upper() != sha256_file(path):
            raise AuditFailure(f"Variant manifest SHA mismatch for {key}")
    logo_assets = manifest.get("logo_assets")
    if not isinstance(logo_assets, list):
        raise AuditFailure("Variant manifest missing logo_assets")
    logo_by_role = {str(item.get("role")): item for item in logo_assets if isinstance(item, dict)}
    if set(logo_by_role) != set(VARIANT_LOGO_ASSETS):
        raise AuditFailure(f"Variant manifest logo roles mismatch: {set(logo_by_role)}")
    for role, asset_path in VARIANT_LOGO_ASSETS.items():
        item = logo_by_role[role]
        if str(item.get("source")) != rel(asset_path):
            raise AuditFailure(f"Variant manifest logo source mismatch for {role}")
        if str(item.get("sha256", "")).upper() != sha256_file(asset_path):
            raise AuditFailure(f"Variant manifest logo SHA mismatch for {role}")


def svg_viewport(path: Path, fallback_width: int = 3600, fallback_height: int = 2700) -> dict[str, int]:
    try:
        root = ET.parse(path).getroot()
        width = int(float(str(root.get("width", fallback_width))))
        height = int(float(str(root.get("height", fallback_height))))
    except Exception:
        width = fallback_width
        height = fallback_height
    return {"width": width, "height": height}


def render_visual_outputs(out_dir: Path, score_root: Path) -> dict[str, str]:
    render_dir = score_root / "_visual_qa"
    render_dir.mkdir(parents=True, exist_ok=True)
    rendered = {
        "contact_sheet": render_dir / "score1000_panel23_contact_sheet.png",
        "panel_2": render_dir / "panel_2_score1000_edge_justified_ledger.png",
        "panel_3": render_dir / "panel_3_score1000_100_barcode_percentage_strip.png",
    }
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        raise AuditFailure(f"playwright is required for visual QA: {exc}") from exc
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        contact_page = browser.new_page(viewport={"width": 1500, "height": 2200}, device_scale_factor=1)
        contact_page.goto((out_dir / "contact_sheet.html").resolve().as_uri(), wait_until="networkidle")
        contact_page.screenshot(path=str(rendered["contact_sheet"]), full_page=True)
        contact_page.close()
        for key, filename in [("panel_2", PANEL_FILES[0]), ("panel_3", PANEL_FILES[1])]:
            page = browser.new_page(viewport={"width": 3600, "height": 2700}, device_scale_factor=1)
            page.goto((out_dir / filename).resolve().as_uri(), wait_until="networkidle")
            page.locator("svg").screenshot(path=str(rendered[key]))
            page.close()
            package_png = out_dir / rendered[key].name
            shutil.copyfile(rendered[key], package_png)
            rendered[f"{key}_package"] = package_png
        browser.close()
    return {key: str(path) for key, path in rendered.items()}


def render_variant_visual_outputs(out_dir: Path, score_root: Path) -> dict[str, str]:
    render_dir = score_root / "_visual_qa"
    render_dir.mkdir(parents=True, exist_ok=True)
    rendered = {
        "contact_sheet": render_dir / "score1000_panel2_group_color_final_contact_sheet.png",
    }
    render_targets: list[tuple[str, str]] = []
    for filename in VARIANT_PANEL_FILES:
        panel_id = str(VARIANT_FILE_SPECS[filename]["panel_id"])
        key = f"variant_{panel_id.replace('.', '_')}"
        rendered[key] = render_dir / filename.replace(".svg", ".png")
        render_targets.append((key, filename))
    rendered["variant_5_4"] = render_dir / PROMOTED_PANEL5_PNG
    render_targets.append(("variant_5_4", PROMOTED_PANEL5_SVG))
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        raise AuditFailure(f"playwright is required for visual QA: {exc}") from exc
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        contact_page = browser.new_page(viewport={"width": 1500, "height": 2200}, device_scale_factor=1)
        contact_page.goto((out_dir / "contact_sheet.html").resolve().as_uri(), wait_until="networkidle")
        contact_page.screenshot(path=str(rendered["contact_sheet"]), full_page=True)
        contact_page.close()
        for key, filename in render_targets:
            page = browser.new_page(viewport=svg_viewport(out_dir / filename), device_scale_factor=1)
            page.goto((out_dir / filename).resolve().as_uri(), wait_until="networkidle")
            page.locator("svg").screenshot(path=str(rendered[key]))
            page.close()
            package_png = out_dir / rendered[key].name
            shutil.copyfile(rendered[key], package_png)
            rendered[f"{key}_package"] = package_png
        shutil.copyfile(rendered["contact_sheet"], out_dir / "contact_sheet.png")
        rendered["contact_sheet_package"] = out_dir / "contact_sheet.png"
        browser.close()
    return {key: str(path) for key, path in rendered.items()}


def write_report(out_dir: Path, rows: list[dict[str, str]], rendered: dict[str, str] | None) -> None:
    report = {
        "generated_at": utc_now(),
        "result": "pass",
        "rows": len(rows),
        "panels": [2, 3],
        "screenshot": rendered.get("contact_sheet") if rendered else None,
        "rendered_pngs": rendered or {},
    }
    (out_dir / "score1000_panel23_audit_report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    lines = [
        "# Score1000 Panel 2/3 Audit Report",
        "",
        "- Result: pass",
        f"- Rows: {len(rows)}",
        "- Panels: 2, 3",
    ]
    if rendered:
        lines.append(f"- Visual QA contact sheet: `{rendered['contact_sheet']}`")
        lines.append(f"- Panel 2 PNG: `{rendered['panel_2']}`")
        lines.append(f"- Panel 3 PNG: `{rendered['panel_3']}`")
    (out_dir / "score1000_panel23_audit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_variant_report(out_dir: Path, rows: list[dict[str, str]], rendered: dict[str, str] | None) -> None:
    panel_ids = [str(spec["panel_id"]) for spec in VARIANT_FILE_SPECS.values()] + ["5.4"]
    report = {
        "generated_at": utc_now(),
        "result": "pass",
        "rows": len(rows),
        "mode": "model-group-color-final",
        "panels": panel_ids,
        "screenshot": rendered.get("contact_sheet") if rendered else None,
        "rendered_pngs": rendered or {},
    }
    (out_dir / "score1000_panel2_group_color_audit_report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    lines = [
        "# Score1000 Panel 2 Group-Color Audit Report",
        "",
        "- Result: pass",
        f"- Rows: {len(rows)}",
        f"- Panels: {', '.join(panel_ids)}",
    ]
    if rendered:
        lines.append(f"- Visual QA contact sheet: `{rendered['contact_sheet']}`")
        for spec in VARIANT_FILE_SPECS.values():
            panel_id = str(spec["panel_id"])
            key = f"variant_{panel_id.replace('.', '_')}"
            lines.append(f"- Variant {panel_id} PNG: `{rendered[key]}`")
        lines.append(f"- Variant 5.4 PNG: `{rendered['variant_5_4']}`")
    (out_dir / "score1000_panel2_group_color_audit_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["production", "model-group-color-final"], default="production")
    parser.add_argument("--score-root", type=Path, default=DEFAULT_SCORE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--source-panel-dir", type=Path, default=None)
    parser.add_argument("--skip-visual-qa", action="store_true")
    parser.add_argument("--idk-score", type=int, choices=[0, 1], default=1)
    return parser.parse_args()


def main_variant(args: argparse.Namespace) -> None:
    score_root = args.score_root.resolve()
    out_dir = (args.out_dir if args.out_dir != DEFAULT_OUT_DIR else DEFAULT_VARIANT_OUT_DIR).resolve()
    try:
        audit_variant_required_files(out_dir)
        rows = audit_csv(score_root, out_dir)
        audit_variant_svg(score_root, out_dir, rows)
        audit_promoted_panel5_svg(out_dir, rows)
        audit_variant_manifest(out_dir)
        rendered = None if args.skip_visual_qa else render_variant_visual_outputs(out_dir, score_root)
        write_variant_report(out_dir, rows, rendered)
    except AuditFailure as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1) from exc
    print(f"[PASS] audited Score1000 Panel 2 group-color package {out_dir}")
    if rendered:
        for path in rendered.values():
            print(f"[PASS] rendered {path}")


def main() -> None:
    args = parse_args()
    configure_idk_score(args.idk_score)
    if args.mode == "model-group-color-final":
        main_variant(args)
        return
    score_root = args.score_root.resolve()
    out_dir = args.out_dir.resolve()
    try:
        audit_required_files(out_dir)
        rows = audit_csv(score_root, out_dir)
        audit_svg(score_root, out_dir, rows)
        audit_manifest(out_dir)
        rendered = None if args.skip_visual_qa else render_visual_outputs(out_dir, score_root)
        write_report(out_dir, rows, rendered)
    except AuditFailure as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1) from exc
    print(f"[PASS] audited Score1000 Panel 2/3 package {out_dir}")
    if rendered:
        for path in rendered.values():
            print(f"[PASS] rendered {path}")


if __name__ == "__main__":
    main()
