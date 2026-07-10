#!/usr/bin/env python3
"""Generate RadLE v2 Score1000 handwritten-style Panel 2/3 SVG artifacts."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html
import json
import shutil
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
DEFAULT_VARIANT_OUT_DIR = DEFAULT_SCORE_ROOT / "handwritten_panels_model_group_color_final"
EXPECTED_SOURCE_SHA256 = "7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED"
LOGO_ASSET_DIR = REPO_ROOT / "scripts" / "assets" / "radle_score1000_logos"
FONT_ASSET_DIR = REPO_ROOT / "scripts" / "assets" / "fonts"

W, H = 3600, 2700
TITLE_FONT = '"Space Grotesk", Lexend, "Helvetica Neue", Helvetica, Arial, sans-serif'
FONT = 'Lexend, "Helvetica Neue", Helvetica, Arial, sans-serif'
MONO = FONT
FONT_ASSETS = {
    "Space Grotesk": {
        "path": FONT_ASSET_DIR / "SpaceGrotesk-wght.ttf",
        "weight": "300 900",
    },
    "Lexend": {
        "path": FONT_ASSET_DIR / "Lexend-wght.ttf",
        "weight": "100 900",
    },
}
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
DOT_DISPLAY_TOTAL = 100
IDK_SCORE = 1
LABEL_CHAR_W = 17
LABEL_PAD_X = 30
MIN_LABEL_WIDTH = 156
VARIANT_CONTENT_Y_SHIFT = 48
VARIANT_HEADER_Y = 430 + VARIANT_CONTENT_Y_SHIFT
VARIANT_AXIS_Y = 2290 + VARIANT_CONTENT_Y_SHIFT
VARIANT_LEGEND_Y = 2424
VARIANT_GROUP_HEADER_MIN_GAP = 48
VARIANT_BAR_H_2_1 = 66
VARIANT_BAR_H_3_1 = 62
VARIANT_LABEL_DY_2_1 = 48
VARIANT_LABEL_DY_3_1 = 46
VARIANT_CHART_X = 940
VARIANT_CHART_W = 2470
VARIANT_SCORE_X = 134
VARIANT_NAME_X = 820
VARIANT_BALANCED_MARGIN_CHART_X = 1015
VARIANT_BALANCED_MARGIN_CHART_W = 2320
VARIANT_BALANCED_MARGIN_SCORE_X = 150
VARIANT_BALANCED_MARGIN_KEY_SHIFT_X = -75
VARIANT_H = 2840
VARIANT_FOOTER_DIVIDER_Y = 2600
VARIANT_FOOTER_TEXT_Y = 2648
VARIANT_FOOTER_LINE_STEP = 52
VARIANT_FOOTER_WRAP_CHARS = 158
VARIANT_GROUP_HEADER_X = 170
VARIANT_GROUP_RULE_X1 = 150
VARIANT_GROUP_RULE_X2 = 760
VARIANT_SUBTITLE_Y_OFFSET = 14
VARIANT_KEY_SWATCH_X = {
    "Human Expert Baseline": 1980,
    "Closed generalist": 2496,
    "Open generalist": 2867,
    "Open medical": 3204,
}
VARIANT_LOGO_ASSETS = {
    "left-affiliation-logo": LOGO_ASSET_DIR / "kcdha_logo.svg",
    "right-lab-logo": LOGO_ASSET_DIR / "crash_lab_logo.png",
}
MODEL_LOGO_ASSETS = {
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
SCORE1000_BAR_LOGO_ASSETS = {
    "Human Expert Baseline": LOGO_ASSET_DIR / "human_expert_baseline_radiologist_navy_logo.png",
    **MODEL_LOGO_ASSETS,
}
SCORE1000_BAR_FALLBACK_BADGES = {}
VARIANT_LOGO_LAYOUT = {
    "left-affiliation-logo": {
        "x": 80,
        "y": 70,
        "width": 380,
        "height": 119,
        "label": "KCDH-A and Ashoka logo",
    },
    "right-lab-logo": {
        "x": 3150,
        "y": 82,
        "width": 370,
        "height": 132,
        "label": "CRASH Lab logo",
    },
}
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
CATEGORY_ORDER = ["Human Expert Baseline", "Closed generalist", "Open generalist", "Open medical"]
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
SCORE1000_BAR_READER_LABELS = [
    "Human Expert Baseline",
    "claude_fable_5",
    "grok_4_3",
    "gemini_3_1_pro",
    "gpt_5_5",
    "octomed_7b",
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
SCORE1000_BAR_LABEL_LINES = {
    "Human Expert Baseline": ["Human Expert", "Baseline"],
    "grok_4_3": ["Grok", "4.3"],
    "claude_fable_5": ["Claude", "Fable 5"],
    "gemini_3_1_pro": ["Gemini", "3.1 Pro"],
    "gpt_5_5": ["GPT-5.5"],
    "octomed_7b": ["OctoMed", "7B"],
    "nemotron_3_omni": ["Nemotron", "3 Omni"],
    "qwen_3_7_plus": ["Qwen", "3.7 Plus"],
    "glm_5v_turbo": ["GLM-5V", "Turbo"],
    "minimax_m3": ["MiniMax", "M3"],
    "gemma_4_31b": ["Gemma 4", "31B"],
    "lingshu_32b": ["Lingshu", "32B"],
    "medgemma_1_5_4b": ["MedGemma", "1.5 4B"],
    "llama_4_maverick": ["Llama 4", "Maverick"],
    "internvl3_5_8b": ["InternVL", "3.5 8B"],
    "mistral_large_3_2512": ["Mistral Lg", "3 2512"],
}
SCORE1000_BAR_PANEL_TITLE = "Confidence-weighted diagnosis correctness"
SCORE1000_BAR_AXIS_TITLE = "Confidence-weighted diagnosis score"
SCORE1000_BAR_CLOSED_PANEL_TITLE = (
    "Proprietary Frontier Vision Language Models (VLMs) vs Human Expert Baseline"
)
SCORE1000_BAR_OPEN_PANEL_TITLE = "Open-access models vs 12 radiologists/trainees"
SCORE1000_BAR_OPEN_VLM_PANEL_TITLE = (
    "Open-Weights Vision Language Models (VLMs) vs Human Expert Baseline"
)
SCORE1000_BAR_THROUGH_MEDGEMMA_PANEL_TITLE = "Models through MedGemma vs 12 radiologists/trainees"
SCORE1000_BAR_CLOSED_OPEN_THROUGH_MEDGEMMA_PANEL_TITLE = (
    "Confidence-Weighted Diagnosis Scores: AI Models vs Human Expert Baseline"
)
SCORE1000_BAR_ALL_MODEL_PANEL_TITLE = (
    "Frontier Vision Language Models (VLMs) vs Human Expert Baseline"
)
SCORE1000_BAR_READER_KEYS = {
    "Human Expert Baseline": "human_expert_baseline",
    **{reader_label: reader_label for reader_label in SCORE1000_BAR_LABEL_LINES if reader_label != "Human Expert Baseline"},
}
SCORE1000_BAR_COLORS = {
    "Human Expert Baseline": "#1b324d",
    "grok_4_3": "#3f464c",
    "claude_fable_5": "#84848e",
    "gemini_3_1_pro": "#2f6f9f",
    "gpt_5_5": "#1b324d",
    "octomed_7b": "#4c9f8f",
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
SCORE1000_BAR_X_LABEL_Y_OFFSET_5_1 = 78.0
SCORE1000_BAR_CANVAS_H_5_1 = 2840.0
SCORE1000_BAR_FIGURE_TITLE_FONT_PX_5_1 = 90.0
SCORE1000_BAR_PANEL_TITLE_FONT_PX_5_1 = 80.0
SCORE1000_BAR_TICK_LABEL_FONT_PX_5_1 = 45.0
SCORE1000_BAR_FOOTER_FONT_PX_5_1 = 44.0
SCORE1000_BAR_FOOTER_X_5_1 = 215.0
SCORE1000_BAR_FOOTER_RIGHT_X_5_1 = 3440.0
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
SCORE1000_BAR_LOGO_BOX = 124.0
SCORE1000_BAR_LOGO_IMAGE = 96.0
SCORE1000_BAR_OCTOMED_LOGO_SCALE = 1.2
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
SCORE1000_BAR_HUMAN_LOGO_Y = 360.0
SCORE1000_BAR_HUMAN_SCORE_GAP = 42.0
SCORE1000_BAR_NEGATIVE_SCORE_GAP = 62.0
SCORE1000_BAR_HUMAN_LOGO_GAP = 70.0
SCORE1000_BAR_FOOTER_DIVIDER_Y = 2500.0
SCORE1000_BAR_FOOTER_TEXT_Y = 2586.0
SCORE1000_BAR_FOOTER_LINE_STEP = 54.0
SCORE1000_BAR_BARCODE_UNITS = 18
SCORE1000_BAR_BARCODE_CAPSULE_W = 24.0
SCORE1000_BAR_BARCODE_CAPSULE_H = 10.0
SCORE1000_BAR_BARCODE_CAPSULE_GAP = 18.0
SCORE1000_BAR_BARCODE_BOTTOM_PAD = 14.0
SCORE1000_BAR_BARCODE_TOP_PAD = 14.0
SCORE1000_BAR_BARCODE_PALETTE = "option_c_teal_green_to_current_red"
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
SCORE1000_BAR_GAP_OVERLAY_LABEL_X_OFFSET = 150.0
SCORE1000_BAR_GAP_OVERLAY_ARROW_COLOR = "#2f55e7"
SCORE1000_BAR_GAP_OVERLAY_ARROW_DIAGONAL_RATIO = 0.12
SCORE1000_BAR_GAP_OVERLAY_ARROW_45_PROJECTION = 0.7071067811865476
SCORE1000_BAR_GAP_OVERLAY_ARROW_SHAFT_WIDTH = 10.0
SCORE1000_BAR_GAP_OVERLAY_ARROW_HEAD_WIDTH = 8.0


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
    all_idk_score2000 = all_idk_score1000 + int(SCORE2000_SHIFT)
    idk_line = (
        f"\"I don't know\" responses add 1 before display shifting; blank/failed responses score 0."
        if idk_score == 1
        else "\"I don't know\"/blank/failed responses score 0 before display shifting."
    )
    return [
        "Confidence-weighted diagnosis correctness across 200 adjudicated radiology cases; not accuracy or calibration.",
        "Human reference pools 12 radiologists/trainees; correct diagnoses add 1-5 by confidence, wrong diagnoses subtract 1-5.",
        f"{idk_line} Displayed score = raw + 1000; {all_idk_score2000} is the all-\"I don't know\" baseline.",
    ]


def score1000_footer_note(idk_score: int) -> str:
    all_idk_score1000 = 200 * idk_score
    all_idk_score2000 = all_idk_score1000 + int(SCORE2000_SHIFT)
    idk_clause = (
        f"\"I don't know\" earns +1; blank or failed answers score 0. All-\"I don't know\" lands at Score1000 +{all_idk_score1000} "
        f"and displays at Score2000 {all_idk_score2000}."
        if idk_score == 1
        else f"\"I don't know\" earns 0; blank or failed answers score 0. All-\"I don't know\" lands at Score1000 0 "
        f"and displays at Score2000 {all_idk_score2000}."
    )
    return (
        "Displayed score (shown left of each reader/model name) is Score2000 = Score1000 + 1000, shifting the "
        "Score1000 range -1000..+1000 to 0..2000 without changing rank. Score1000 still uses confidence-scaled "
        "per-case points: correct +1 to +5 and wrong -1 to -5; "
        f"{idk_clause}"
    )


def score1000_caption_rule(idk_score: int) -> str:
    return (
        "Score1000 sums per-case points over 200 cases: correct answers score +1 to +5 by confidence, "
        "wrong answers -1 to -5, "
        f"\"I don't know\" scores {signed_score(idk_score) if idk_score else '0'}, "
        "invalid/technical-failure responses score 0; range -1000 to +1000, "
        f"with an all-\"I don't know\" baseline of {signed_score(200 * idk_score) if idk_score else '0'}. "
        "Figures display Score2000 = Score1000 + 1000 on a shifted 0..2000 scale without changing rank."
    )


LIKERT_LEGEND_LABELS = likert_legend_labels(IDK_SCORE)
SCORE1000_BAR_FOOTER_LINES = score1000_bar_footer_lines(IDK_SCORE)
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
OUTCOME_PALETTES = {
    "current": {
        "name": "Current blue-gray-red outcome palette",
        "colors": COLORS,
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
VARIANT_FILE_SPECS = {
    VARIANT_PANEL_FILES[0]: {
        "panel_id": "2.1",
        "variant": "2.1 revised colored model names",
        "layout": "colored_names",
        "palette_key": "current",
        "caption": "Panel 2 variant 2.1. Rank order preserved; model and human names carry category color.",
        "show_group_headers": False,
        "color_row_names": True,
    },
    VARIANT_PANEL_FILES[1]: {
        "panel_id": "3.1",
        "variant": "3.1 revised grouped bands",
        "layout": "grouped_bands",
        "palette_key": "current",
        "caption": "Panel 2 variant 3.1. Rows grouped by category with colored group headers.",
        "show_group_headers": True,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[2]: {
        "panel_id": "2.2",
        "variant": "2.2 Option A blue-to-red colored model names",
        "layout": "colored_names",
        "palette_key": "option_a_blue_to_current_red",
        "chart_x": VARIANT_BALANCED_MARGIN_CHART_X,
        "chart_w": VARIANT_BALANCED_MARGIN_CHART_W,
        "score_x": VARIANT_BALANCED_MARGIN_SCORE_X,
        "category_key_shift_x": VARIANT_BALANCED_MARGIN_KEY_SHIFT_X,
        "caption": "Panel 2 variant 2.2. Rank order preserved with Option A blue-to-current-red outcome colors.",
        "show_group_headers": False,
        "color_row_names": True,
    },
    VARIANT_PANEL_FILES[3]: {
        "panel_id": "3.2",
        "variant": "3.2 Option A blue-to-red grouped bands",
        "layout": "grouped_bands",
        "palette_key": "option_a_blue_to_current_red",
        "chart_x": VARIANT_BALANCED_MARGIN_CHART_X,
        "chart_w": VARIANT_BALANCED_MARGIN_CHART_W,
        "score_x": VARIANT_BALANCED_MARGIN_SCORE_X,
        "category_key_shift_x": VARIANT_BALANCED_MARGIN_KEY_SHIFT_X,
        "caption": "Panel 2 variant 3.2. Rows grouped by category with preserved group gaps, hidden left group headers, category-colored row names, and Option A blue-to-current-red outcome colors.",
        "show_group_headers": False,
        "color_row_names": True,
    },
    VARIANT_PANEL_FILES[4]: {
        "panel_id": "2.3",
        "variant": "2.3 Option C teal-green-to-red colored model names",
        "layout": "colored_names",
        "palette_key": "option_c_teal_green_to_current_red",
        "chart_x": VARIANT_BALANCED_MARGIN_CHART_X,
        "chart_w": VARIANT_BALANCED_MARGIN_CHART_W,
        "score_x": VARIANT_BALANCED_MARGIN_SCORE_X,
        "category_key_shift_x": VARIANT_BALANCED_MARGIN_KEY_SHIFT_X,
        "category_colors": OPTION_C_CATEGORY_COLORS,
        "caption": "Panel 2 variant 2.3. Rank order preserved with Option C teal-green-to-current-red outcome colors and balanced horizontal margins.",
        "show_group_headers": False,
        "color_row_names": True,
    },
    VARIANT_PANEL_FILES[5]: {
        "panel_id": "3.3",
        "variant": "3.3 Option C teal-green-to-red grouped bands",
        "layout": "grouped_bands",
        "palette_key": "option_c_teal_green_to_current_red",
        "chart_x": VARIANT_BALANCED_MARGIN_CHART_X,
        "chart_w": VARIANT_BALANCED_MARGIN_CHART_W,
        "score_x": VARIANT_BALANCED_MARGIN_SCORE_X,
        "category_key_shift_x": VARIANT_BALANCED_MARGIN_KEY_SHIFT_X,
        "category_colors": OPTION_C_CATEGORY_COLORS,
        "caption": "Panel 2 variant 3.3. Rows grouped by category with preserved group gaps, hidden left group headers, category-colored row names, Option C teal-green-to-current-red outcome colors, and balanced horizontal margins.",
        "show_group_headers": False,
        "color_row_names": True,
    },
    VARIANT_PANEL_FILES[6]: {
        "panel_id": "2.4",
        "variant": "2.4 shared-image category palette colored model names",
        "layout": "colored_names",
        "palette_key": "option_c_teal_green_to_current_red",
        "chart_x": VARIANT_BALANCED_MARGIN_CHART_X,
        "chart_w": VARIANT_BALANCED_MARGIN_CHART_W,
        "score_x": VARIANT_BALANCED_MARGIN_SCORE_X,
        "category_key_shift_x": VARIANT_BALANCED_MARGIN_KEY_SHIFT_X,
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "caption": "Panel 2 variant 2.4. Rank order preserved with the shared image category palette, Option C teal-green-to-current-red outcome colors, and balanced horizontal margins.",
        "show_group_headers": False,
        "color_row_names": True,
    },
    VARIANT_PANEL_FILES[7]: {
        "panel_id": "3.4",
        "variant": "3.4 shared-image category palette grouped bands",
        "layout": "grouped_bands",
        "palette_key": "option_c_teal_green_to_current_red",
        "chart_x": VARIANT_BALANCED_MARGIN_CHART_X,
        "chart_w": VARIANT_BALANCED_MARGIN_CHART_W,
        "score_x": VARIANT_BALANCED_MARGIN_SCORE_X,
        "category_key_shift_x": VARIANT_BALANCED_MARGIN_KEY_SHIFT_X,
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "caption": "Panel 2 variant 3.4. Rows grouped by category with preserved group gaps, hidden left group headers, category-colored row names, the shared image category palette, Option C teal-green-to-current-red outcome colors, and balanced horizontal margins.",
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
        "category_key_shift_x": VARIANT_BALANCED_MARGIN_KEY_SHIFT_X,
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "caption": "Panel 2 variant 2.5. Rank order preserved with the shared image category palette; score labels and reader/model names both carry category color.",
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
        "category_key_shift_x": VARIANT_BALANCED_MARGIN_KEY_SHIFT_X,
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "caption": "Panel 2 variant 3.5. Rows grouped by category with preserved group gaps; score labels and reader/model names both carry category color.",
        "show_group_headers": False,
        "color_row_names": True,
        "color_scores": True,
    },
    VARIANT_PANEL_FILES[10]: {
        "panel_id": "5.0",
        "variant": "5.0 clean confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "selected_reader_labels": SCORE1000_BAR_READER_LABELS,
        "score_y_min": SCORE1000_BAR_Y_MIN,
        "score_y_max": SCORE1000_BAR_Y_MAX,
        "score_ticks": SCORE1000_BAR_A1_TICKS,
        "score_axis_break_after": SCORE1000_BAR_AXIS_BREAK_AFTER,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
        "axis_title": SCORE1000_BAR_AXIS_TITLE,
        "use_variant_footer": True,
        "footer_lines": SCORE1000_BAR_FOOTER_LINES,
        "footer_cls": "score1000-footer",
        "footer_text_y": SCORE1000_BAR_FOOTER_TEXT_Y,
        "footer_line_step": SCORE1000_BAR_FOOTER_LINE_STEP,
        "footer_divider_y": SCORE1000_BAR_FOOTER_DIVIDER_Y,
        "footer_font_px": SCORE1000_BAR_FOOTER_FONT_PX_5_1,
        "footer_x": SCORE1000_BAR_FOOTER_X_5_1,
        "footer_right_x": SCORE1000_BAR_FOOTER_RIGHT_X_5_1,
        "svg_h": SCORE1000_BAR_CANVAS_H_5_1,
        "caption": "Panel 2 variant 5.0. Clean vertical confidence-weighted diagnosis chart for the pooled Human Expert Baseline and five selected models.",
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[11]: {
        "panel_id": "5.1",
        "variant": "5.1 icon confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "caption": "Panel 5.1. Confidence-weighted diagnosis chart with refreshed per-model bar colors, larger top logos, and reader/model icons; the Human Expert Baseline icon sits above the shifted baseline.",
        "selected_reader_labels": SCORE1000_BAR_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_WARM_REFRESH,
        "score_y_min": SCORE1000_BAR_Y_MIN,
        "score_y_max": SCORE1000_BAR_Y_MAX,
        "score_ticks": SCORE1000_BAR_A1_TICKS,
        "score_axis_break_after": SCORE1000_BAR_AXIS_BREAK_AFTER,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
        "include_model_icons": True,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.5,
        "score_chart_y": SCORE1000_BAR_CHART_Y_5_1,
        "figure_title_x": SCORE1000_BAR_FIGURE_TITLE_X_5_1,
        "figure_title_y": SCORE1000_BAR_FIGURE_TITLE_Y_5_1,
        "panel_title": SCORE1000_BAR_PANEL_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": SCORE1000_BAR_PANEL_TITLE_Y_5_1,
        "panel_title_font_px": SCORE1000_BAR_PANEL_TITLE_FONT_PX_5_1,
        "axis_title": SCORE1000_BAR_AXIS_TITLE,
        "bar_value_font_scale": 1.5,
        "figure_title_font_px": SCORE1000_BAR_FIGURE_TITLE_FONT_PX_5_1,
        "tick_label_font_px": SCORE1000_BAR_TICK_LABEL_FONT_PX_5_1,
        "x_label_y_offset": SCORE1000_BAR_X_LABEL_Y_OFFSET_5_1,
        "use_variant_footer": True,
        "footer_lines": SCORE1000_BAR_FOOTER_LINES,
        "footer_cls": "score1000-footer",
        "footer_text_y": SCORE1000_BAR_FOOTER_TEXT_Y,
        "footer_line_step": SCORE1000_BAR_FOOTER_LINE_STEP,
        "footer_divider_y": SCORE1000_BAR_FOOTER_DIVIDER_Y,
        "footer_font_px": SCORE1000_BAR_FOOTER_FONT_PX_5_1,
        "footer_x": SCORE1000_BAR_FOOTER_X_5_1,
        "footer_right_x": SCORE1000_BAR_FOOTER_RIGHT_X_5_1,
        "svg_h": SCORE1000_BAR_CANVAS_H_5_1,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[12]: {
        "panel_id": "5.5",
        "variant": "5.5 refreshed-palette icon confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "caption": "Panel 5.5. Palette-refresh checkpoint for the icon confidence-weighted diagnosis chart using Claude #D97757, Grok #313131, Gemini #4796E3, GPT-5.5 #74AA9C, and OctoMed #F27B73; human colors stay unchanged.",
        "selected_reader_labels": SCORE1000_BAR_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_WARM_REFRESH,
        "score_y_min": SCORE1000_BAR_Y_MIN,
        "score_y_max": SCORE1000_BAR_Y_MAX,
        "score_ticks": SCORE1000_BAR_A1_TICKS,
        "score_axis_break_after": SCORE1000_BAR_AXIS_BREAK_AFTER,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
        "include_model_icons": True,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.5,
        "score_chart_y": SCORE1000_BAR_CHART_Y_5_1,
        "figure_title_x": SCORE1000_BAR_FIGURE_TITLE_X_5_1,
        "figure_title_y": SCORE1000_BAR_FIGURE_TITLE_Y_5_1,
        "panel_title": SCORE1000_BAR_PANEL_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": SCORE1000_BAR_PANEL_TITLE_Y_5_1,
        "panel_title_font_px": SCORE1000_BAR_PANEL_TITLE_FONT_PX_5_1,
        "axis_title": SCORE1000_BAR_AXIS_TITLE,
        "bar_value_font_scale": 1.5,
        "figure_title_font_px": SCORE1000_BAR_FIGURE_TITLE_FONT_PX_5_1,
        "tick_label_font_px": SCORE1000_BAR_TICK_LABEL_FONT_PX_5_1,
        "x_label_y_offset": SCORE1000_BAR_X_LABEL_Y_OFFSET_5_1,
        "use_variant_footer": True,
        "footer_lines": SCORE1000_BAR_FOOTER_LINES,
        "footer_cls": "score1000-footer",
        "footer_text_y": SCORE1000_BAR_FOOTER_TEXT_Y,
        "footer_line_step": SCORE1000_BAR_FOOTER_LINE_STEP,
        "footer_divider_y": SCORE1000_BAR_FOOTER_DIVIDER_Y,
        "footer_font_px": SCORE1000_BAR_FOOTER_FONT_PX_5_1,
        "footer_x": SCORE1000_BAR_FOOTER_X_5_1,
        "footer_right_x": SCORE1000_BAR_FOOTER_RIGHT_X_5_1,
        "svg_h": SCORE1000_BAR_CANVAS_H_5_1,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[13]: {
        "panel_id": "5.6",
        "variant": "5.6 open-model bottom-logo confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "caption": "Panel 5.6. Bottom-logo confidence-weighted diagnosis chart for the pooled Human Expert Baseline plus all open-access/open models in the current comparator CSV, including the open medical models.",
        "selected_reader_labels": SCORE1000_BAR_OPEN_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED,
        "score_y_min": SCORE1000_BAR_Y_MIN,
        "score_y_max": SCORE1000_BAR_Y_MAX,
        "score_ticks": SCORE1000_BAR_A1_TICKS,
        "score_axis_break_after": SCORE1000_BAR_AXIS_BREAK_AFTER,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2490.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.55,
        "score_chart_y": SCORE1000_BAR_CHART_Y_5_1,
        "figure_title_x": SCORE1000_BAR_FIGURE_TITLE_X_5_1,
        "figure_title_y": SCORE1000_BAR_FIGURE_TITLE_Y_5_1,
        "panel_title": SCORE1000_BAR_OPEN_PANEL_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": SCORE1000_BAR_PANEL_TITLE_Y_5_1,
        "panel_title_font_px": SCORE1000_BAR_PANEL_TITLE_FONT_PX_5_1,
        "axis_title": SCORE1000_BAR_AXIS_TITLE,
        "bar_value_font_scale": 1.35,
        "figure_title_font_px": SCORE1000_BAR_FIGURE_TITLE_FONT_PX_5_1,
        "tick_label_font_px": SCORE1000_BAR_TICK_LABEL_FONT_PX_5_1,
        "x_label_y_offset": SCORE1000_BAR_X_LABEL_Y_OFFSET_5_1,
        "x_label_font_px": 46.0,
        "x_label_line_step": 54.0,
        "use_variant_footer": False,
        "show_footer": False,
        "svg_h": SCORE1000_BAR_CANVAS_H_5_1,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[14]: {
        "panel_id": "6.0",
        "variant": "6.0 Human-through-MedGemma barcode confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "caption": "Panel 6.0. Confidence-weighted diagnosis chart for the pooled Human Expert Baseline plus all ranked models through MedGemma; centered outcome barcode capsules sit inside each Palette A bar, and logos sit below the reader/model names.",
        "selected_reader_labels": SCORE1000_BAR_THROUGH_MEDGEMMA_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_PALETTE_A,
        "score_y_min": SCORE1000_BAR_Y_MIN,
        "score_y_max": SCORE1000_BAR_Y_MAX,
        "score_ticks": SCORE1000_BAR_A1_TICKS,
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2395.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 0.82,
        "score_chart_y": SCORE1000_BAR_CHART_Y_5_1,
        "score_bar_width": SCORE1000_BAR_W_DENSE,
        "score_axis_break_after": SCORE1000_BAR_AXIS_BREAK_AFTER,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
        "include_barcode_overlay": True,
        "barcode_units": SCORE1000_BAR_BARCODE_UNITS,
        "barcode_capsule_w": SCORE1000_BAR_BARCODE_CAPSULE_W,
        "barcode_capsule_h": SCORE1000_BAR_BARCODE_CAPSULE_H,
        "barcode_capsule_gap": SCORE1000_BAR_BARCODE_CAPSULE_GAP,
        "barcode_outcome_palette_key": SCORE1000_BAR_BARCODE_PALETTE,
        "figure_title_x": SCORE1000_BAR_FIGURE_TITLE_X_5_1,
        "figure_title_y": SCORE1000_BAR_FIGURE_TITLE_Y_5_1,
        "panel_title": SCORE1000_BAR_THROUGH_MEDGEMMA_PANEL_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": SCORE1000_BAR_PANEL_TITLE_Y_5_1,
        "panel_title_font_px": SCORE1000_BAR_PANEL_TITLE_FONT_PX_5_1,
        "axis_title": SCORE1000_BAR_AXIS_TITLE,
        "bar_value_font_scale": 1.05,
        "figure_title_font_px": SCORE1000_BAR_FIGURE_TITLE_FONT_PX_5_1,
        "tick_label_font_px": SCORE1000_BAR_TICK_LABEL_FONT_PX_5_1,
        "x_label_y_offset": SCORE1000_BAR_X_LABEL_Y_OFFSET_5_1,
        "use_variant_footer": True,
        "footer_lines": SCORE1000_BAR_FOOTER_LINES,
        "footer_cls": "score1000-footer",
        "footer_text_y": 2608.0,
        "footer_line_step": SCORE1000_BAR_FOOTER_LINE_STEP,
        "footer_divider_y": 2550.0,
        "footer_font_px": SCORE1000_BAR_FOOTER_FONT_PX_5_1,
        "footer_x": SCORE1000_BAR_FOOTER_X_5_1,
        "footer_right_x": SCORE1000_BAR_FOOTER_RIGHT_X_5_1,
        "svg_h": SCORE1000_BAR_CANVAS_H_5_1,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[15]: {
        "panel_id": "6.1",
        "variant": "6.1 closed-model confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "caption": "Panel 6.1. Confidence-weighted diagnosis chart for the pooled Human Expert Baseline plus all closed/API generalist models in the current comparator CSV.",
        "selected_reader_labels": SCORE1000_BAR_CLOSED_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED,
        "score_y_min": SCORE1000_BAR_Y_MIN,
        "score_y_max": SCORE1000_BAR_Y_MAX,
        "score_ticks": SCORE1000_BAR_A1_TICKS,
        "score_axis_break_after": SCORE1000_BAR_AXIS_BREAK_AFTER,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2490.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.55,
        "bar_logo_image_multipliers": SCORE1000_BAR_6_1_LOGO_IMAGE_MULTIPLIERS,
        "score_chart_y": SCORE1000_BAR_CHART_Y_5_1,
        "score_chart_h": SCORE1000_BAR_CHART_H_NO_FOOTER,
        "figure_title_x": SCORE1000_BAR_FIGURE_TITLE_X_5_1,
        "figure_title_y": SCORE1000_BAR_FIGURE_TITLE_Y_5_1,
        "panel_title": SCORE1000_BAR_CLOSED_PANEL_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": SCORE1000_BAR_PANEL_TITLE_Y_5_1,
        "panel_title_font_px": SCORE1000_BAR_PANEL_TITLE_FONT_PX_5_1,
        "axis_title": SCORE1000_BAR_AXIS_TITLE,
        "bar_value_font_scale": 1.35,
        "figure_title_font_px": SCORE1000_BAR_FIGURE_TITLE_FONT_PX_5_1,
        "tick_label_font_px": SCORE1000_BAR_TICK_LABEL_FONT_PX_5_1,
        "x_label_y_offset": SCORE1000_BAR_X_LABEL_Y_OFFSET_5_1,
        "x_label_font_px": 46.0,
        "x_label_line_step": 54.0,
        "use_variant_footer": False,
        "show_footer": False,
        "svg_h": SCORE1000_BAR_CANVAS_H_5_1,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[16]: {
        "panel_id": "6.1.1",
        "variant": "6.1.1 closed-model confidence-weighted diagnosis vertical bar chart with gap overlay",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "caption": "Panel 6.1.1. Confidence-weighted diagnosis chart for the pooled Human Expert Baseline plus all closed/API generalist models, with the dynamic Human-AI gap overlay.",
        "selected_reader_labels": SCORE1000_BAR_CLOSED_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED,
        "score_y_min": SCORE1000_BAR_Y_MIN,
        "score_y_max": SCORE1000_BAR_Y_MAX,
        "score_ticks": SCORE1000_BAR_A1_TICKS,
        "score_axis_break_after": SCORE1000_BAR_AXIS_BREAK_AFTER,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
        "include_score_gap_overlay": True,
        "score_gap_date_label": SCORE1000_BAR_GAP_DATE_LABEL,
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2490.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.55,
        "bar_logo_image_multipliers": SCORE1000_BAR_6_1_LOGO_IMAGE_MULTIPLIERS,
        "score_chart_y": SCORE1000_BAR_CHART_Y_5_1,
        "score_chart_h": SCORE1000_BAR_CHART_H_NO_FOOTER,
        "figure_title_x": SCORE1000_BAR_FIGURE_TITLE_X_5_1,
        "figure_title_y": SCORE1000_BAR_FIGURE_TITLE_Y_5_1,
        "panel_title": SCORE1000_BAR_CLOSED_PANEL_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": SCORE1000_BAR_PANEL_TITLE_Y_5_1,
        "panel_title_font_px": SCORE1000_BAR_PANEL_TITLE_FONT_PX_5_1,
        "axis_title": SCORE1000_BAR_AXIS_TITLE,
        "bar_value_font_scale": 1.35,
        "figure_title_font_px": SCORE1000_BAR_FIGURE_TITLE_FONT_PX_5_1,
        "tick_label_font_px": SCORE1000_BAR_TICK_LABEL_FONT_PX_5_1,
        "x_label_y_offset": SCORE1000_BAR_X_LABEL_Y_OFFSET_5_1,
        "x_label_font_px": 46.0,
        "x_label_line_step": 54.0,
        "use_variant_footer": False,
        "show_footer": False,
        "svg_h": SCORE1000_BAR_CANVAS_H_5_1,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[17]: {
        "panel_id": "6.2",
        "variant": "6.2 open-model confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "caption": "Panel 6.2. Confidence-weighted diagnosis chart for the pooled Human Expert Baseline plus all open-access/open models in the current comparator CSV, including the open medical models.",
        "selected_reader_labels": SCORE1000_BAR_OPEN_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED,
        "score_y_min": SCORE1000_BAR_Y_MIN,
        "score_y_max": SCORE1000_BAR_Y_MAX,
        "score_ticks": SCORE1000_BAR_A1_TICKS,
        "score_axis_break_after": SCORE1000_BAR_AXIS_BREAK_AFTER,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2490.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.55,
        "bar_logo_image_multipliers": SCORE1000_BAR_6_2_LOGO_IMAGE_MULTIPLIERS,
        "score_chart_y": SCORE1000_BAR_CHART_Y_5_1,
        "score_chart_h": SCORE1000_BAR_CHART_H_NO_FOOTER,
        "figure_title_x": SCORE1000_BAR_FIGURE_TITLE_X_5_1,
        "figure_title_y": SCORE1000_BAR_FIGURE_TITLE_Y_5_1,
        "panel_title": SCORE1000_BAR_OPEN_VLM_PANEL_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": SCORE1000_BAR_PANEL_TITLE_Y_5_1,
        "panel_title_font_px": SCORE1000_BAR_PANEL_TITLE_FONT_PX_5_1,
        "axis_title": SCORE1000_BAR_AXIS_TITLE,
        "bar_value_font_scale": 1.35,
        "figure_title_font_px": SCORE1000_BAR_FIGURE_TITLE_FONT_PX_5_1,
        "tick_label_font_px": SCORE1000_BAR_TICK_LABEL_FONT_PX_5_1,
        "x_label_y_offset": SCORE1000_BAR_X_LABEL_Y_OFFSET_5_1,
        "x_label_font_px": 46.0,
        "x_label_line_step": 54.0,
        "use_variant_footer": False,
        "show_footer": False,
        "svg_h": SCORE1000_BAR_CANVAS_H_5_1,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[18]: {
        "panel_id": "6.2.1",
        "variant": "6.2.1 open-model confidence-weighted diagnosis vertical bar chart with gap overlay",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "caption": "Panel 6.2.1. Confidence-weighted diagnosis chart for the pooled Human Expert Baseline plus all open-access/open models, including the open medical models, with the dynamic Human-AI gap overlay.",
        "selected_reader_labels": SCORE1000_BAR_OPEN_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED,
        "score_y_min": SCORE1000_BAR_Y_MIN,
        "score_y_max": SCORE1000_BAR_Y_MAX,
        "score_ticks": SCORE1000_BAR_A1_TICKS,
        "score_axis_break_after": SCORE1000_BAR_AXIS_BREAK_AFTER,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
        "include_score_gap_overlay": True,
        "score_gap_date_label": SCORE1000_BAR_GAP_DATE_LABEL,
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2490.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.55,
        "bar_logo_image_multipliers": SCORE1000_BAR_6_2_LOGO_IMAGE_MULTIPLIERS,
        "score_chart_y": SCORE1000_BAR_CHART_Y_5_1,
        "score_chart_h": SCORE1000_BAR_CHART_H_NO_FOOTER,
        "figure_title_x": SCORE1000_BAR_FIGURE_TITLE_X_5_1,
        "figure_title_y": SCORE1000_BAR_FIGURE_TITLE_Y_5_1,
        "panel_title": SCORE1000_BAR_OPEN_VLM_PANEL_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": SCORE1000_BAR_PANEL_TITLE_Y_5_1,
        "panel_title_font_px": SCORE1000_BAR_PANEL_TITLE_FONT_PX_5_1,
        "axis_title": SCORE1000_BAR_AXIS_TITLE,
        "bar_value_font_scale": 1.35,
        "figure_title_font_px": SCORE1000_BAR_FIGURE_TITLE_FONT_PX_5_1,
        "tick_label_font_px": SCORE1000_BAR_TICK_LABEL_FONT_PX_5_1,
        "x_label_y_offset": SCORE1000_BAR_X_LABEL_Y_OFFSET_5_1,
        "x_label_font_px": 46.0,
        "x_label_line_step": 54.0,
        "use_variant_footer": False,
        "show_footer": False,
        "svg_h": SCORE1000_BAR_CANVAS_H_5_1,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[19]: {
        "panel_id": "6.3",
        "variant": "6.3 through-MedGemma confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "caption": "Panel 6.3. Confidence-weighted diagnosis chart for the pooled Human Expert Baseline plus all evaluated AI models through MedGemma, excluding later rows after MedGemma.",
        "selected_reader_labels": SCORE1000_BAR_THROUGH_MEDGEMMA_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED,
        "score_y_min": SCORE1000_BAR_Y_MIN,
        "score_y_max": SCORE1000_BAR_Y_MAX,
        "score_ticks": SCORE1000_BAR_A1_TICKS,
        "score_axis_break_after": SCORE1000_BAR_AXIS_BREAK_AFTER,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
        "include_score_gap_overlay": True,
        "score_gap_date_label": SCORE1000_BAR_GAP_DATE_LABEL,
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2490.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 0.82,
        "score_chart_y": SCORE1000_BAR_CHART_Y_5_1,
        "score_chart_h": SCORE1000_BAR_CHART_H_NO_FOOTER,
        "score_bar_width": SCORE1000_BAR_W_DENSE,
        "figure_title_x": SCORE1000_BAR_FIGURE_TITLE_X_5_1,
        "figure_title_y": SCORE1000_BAR_FIGURE_TITLE_Y_5_1,
        "panel_title": SCORE1000_BAR_CLOSED_OPEN_THROUGH_MEDGEMMA_PANEL_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": SCORE1000_BAR_PANEL_TITLE_Y_5_1,
        "panel_title_font_px": SCORE1000_BAR_PANEL_TITLE_FONT_PX_5_1,
        "axis_title": SCORE1000_BAR_AXIS_TITLE,
        "bar_value_font_scale": 1.05,
        "figure_title_font_px": SCORE1000_BAR_FIGURE_TITLE_FONT_PX_5_1,
        "tick_label_font_px": SCORE1000_BAR_TICK_LABEL_FONT_PX_5_1,
        "x_label_y_offset": SCORE1000_BAR_X_LABEL_Y_OFFSET_5_1,
        "use_variant_footer": False,
        "show_footer": False,
        "svg_h": SCORE1000_BAR_CANVAS_H_5_1,
        "show_group_headers": False,
        "color_row_names": False,
    },
    VARIANT_PANEL_FILES[20]: {
        "panel_id": "6.4",
        "variant": "6.4 all-model confidence-weighted diagnosis vertical bar chart",
        "layout": "score1000_bar_chart",
        "palette_key": "option_c_teal_green_to_current_red",
        "category_colors": SHARED_IMAGE_CATEGORY_COLORS,
        "text_colors": SHARED_IMAGE_TEXT_COLORS,
        "caption": "Panel 6.4. Confidence-weighted diagnosis chart for the pooled Human Expert Baseline plus all 15 evaluated AI models in the current comparator CSV.",
        "selected_reader_labels": SCORE1000_BAR_ALL_MODEL_READER_LABELS,
        "bar_colors": SCORE1000_BAR_COLORS_RECOMMENDED_BALANCED,
        "score_y_min": SCORE1000_BAR_Y_MIN,
        "score_y_max": SCORE1000_BAR_Y_MAX,
        "score_ticks": SCORE1000_BAR_A1_TICKS,
        "score_axis_break_after": SCORE1000_BAR_AXIS_BREAK_AFTER,
        "score_axis_break_style": "a1_double_slash",
        "score_axis_break_top_fraction": SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
        "include_score_gap_overlay": True,
        "score_gap_date_label": SCORE1000_BAR_GAP_DATE_LABEL,
        "include_model_icons": True,
        "logo_position": "bottom_under_labels",
        "bottom_logo_center_y": 2490.0,
        "top_logo_scale": 1.68,
        "bar_logo_scale": 1.40,
        "bar_logo_image_multipliers": SCORE1000_BAR_6_4_LOGO_IMAGE_MULTIPLIERS,
        "score_chart_y": SCORE1000_BAR_CHART_Y_5_1,
        "score_chart_h": SCORE1000_BAR_CHART_H_NO_FOOTER,
        "score_bar_width": SCORE1000_BAR_W_DENSE,
        "y_axis_left_shift": SCORE1000_BAR_6_4_Y_AXIS_LEFT_SHIFT,
        "figure_title_x": SCORE1000_BAR_FIGURE_TITLE_X_5_1,
        "figure_title_y": SCORE1000_BAR_FIGURE_TITLE_Y_5_1,
        "panel_title": SCORE1000_BAR_ALL_MODEL_PANEL_TITLE,
        "panel_title_cls": "score1000-panel-title",
        "panel_title_y": 424.0,
        "panel_title_font_px": SCORE1000_BAR_PANEL_TITLE_FONT_PX_5_1,
        "axis_title": SCORE1000_BAR_AXIS_TITLE,
        "bar_value_font_scale": 1.05,
        "figure_title_font_px": SCORE1000_BAR_FIGURE_TITLE_FONT_PX_5_1,
        "tick_label_font_px": SCORE1000_BAR_TICK_LABEL_FONT_PX_5_1,
        "x_label_y_offset": SCORE1000_BAR_X_LABEL_Y_OFFSET_5_1,
        "x_label_font_px": 30.0,
        "x_label_line_step": 38.0,
        "use_variant_footer": False,
        "show_footer": False,
        "svg_h": SCORE1000_BAR_CANVAS_H_5_1,
        "show_group_headers": False,
        "color_row_names": False,
    },
}


def configure_idk_score(idk_score: int) -> None:
    if idk_score not in {0, 1}:
        raise ValueError(f"Unsupported IDK score: {idk_score}")
    global IDK_SCORE, LIKERT_LEGEND_LABELS, SCORE1000_BAR_FOOTER_LINES, FOOTER_SCORE1000_NOTE
    IDK_SCORE = idk_score
    LIKERT_LEGEND_LABELS = likert_legend_labels(idk_score)
    SCORE1000_BAR_FOOTER_LINES = score1000_bar_footer_lines(idk_score)
    FOOTER_SCORE1000_NOTE = score1000_footer_note(idk_score)
    for spec in VARIANT_FILE_SPECS.values():
        if spec.get("use_variant_footer"):
            spec["footer_lines"] = SCORE1000_BAR_FOOTER_LINES


def variant_category_colors(spec: dict[str, object]) -> dict[str, str]:
    return dict(spec.get("category_colors", CATEGORY_COLORS))  # type: ignore[arg-type]


def variant_text_colors(spec: dict[str, object]) -> dict[str, str] | None:
    text_colors = spec.get("text_colors")
    if text_colors is None:
        return None
    return dict(text_colors)  # type: ignore[arg-type]


def variant_bar_colors(spec: dict[str, object]) -> dict[str, str]:
    return dict(spec.get("bar_colors", SCORE1000_BAR_COLORS))  # type: ignore[arg-type]


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
FIGURE_TITLE = "Radiology's Last Exam 2.0"
FIGURE_TITLE_Y = 144
FONT_SIZE_ROWS = [
    ("figure_title", ".figure-title", "svg_panel", 76, "Figure title"),
    ("title", ".title", "svg_panel", 54, "Panel title"),
    ("subtitle", ".subtitle", "svg_panel", 36, "Panel subtitle"),
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
VARIANT_FONT_SIZE_ROWS = [
    ("variant_figure_title", ".figure-title", "svg_panel_variant", 78, "Accessible variant figure title"),
    ("variant_subtitle", ".variant-subtitle", "svg_panel_variant", 42, "Accessible variant subtitle"),
    ("variant_axis", ".variant-axis-label", "svg_panel_variant", 32, "Accessible variant header/axis labels"),
    ("variant_row_label", ".variant-row-label", "svg_panel_variant", 40, "Accessible variant row labels"),
    ("variant_score", ".variant-score-label", "svg_panel_variant", 33, "Accessible variant Score1000 labels"),
    ("variant_bar", ".variant-bar-label", "svg_panel_variant", 31, "Accessible variant bar/count labels"),
    ("variant_legend", ".variant-legend-label", "svg_panel_variant", 33, "Accessible variant legend/category labels"),
    ("variant_group", ".variant-group-label", "svg_panel_variant", 35, "Accessible variant group headers"),
    ("variant_micro", ".variant-micro", "svg_panel_variant", 40, "Accessible variant footer text"),
    ("score1000_footer", ".score1000-footer", "svg_panel_variant", 44, "Score1000 bar chart footer text"),
    ("score1000_x_label", ".score1000-x-label", "svg_panel_variant", 40, "Score1000 bar chart x-axis model names"),
    ("score1000_bar_value", ".score1000-bar-value", "svg_panel_variant", 44, "Score1000 bar chart visible score values"),
    ("score1000_figure_title_5_1", "panel_2_score1000_5_1 figure-title inline", "svg_panel_variant", 90, "Panel 5.1 figure title inline override"),
    ("score1000_panel_title_5_1", "panel_2_score1000_5_1 score1000-panel-title inline", "svg_panel_variant", 80, "Panel 5.1 panel title inline override"),
    ("score1000_tick_label_5_1", "panel_2_score1000_5_1 score1000-tick-label inline", "svg_panel_variant", 45, "Panel 5.1 tick label inline override"),
    ("score1000_footer_5_1", "panel_2_score1000_5_1 score1000-footer inline", "svg_panel_variant", 52, "Panel 5.1 footer inline override"),
    ("score1000_figure_title_5_5", "panel_2_score1000_5_5 figure-title inline", "svg_panel_variant", 90, "Panel 5.5 figure title inline override"),
    ("score1000_panel_title_5_5", "panel_2_score1000_5_5 score1000-panel-title inline", "svg_panel_variant", 80, "Panel 5.5 panel title inline override"),
    ("score1000_tick_label_5_5", "panel_2_score1000_5_5 score1000-tick-label inline", "svg_panel_variant", 45, "Panel 5.5 tick label inline override"),
    ("score1000_footer_5_5", "panel_2_score1000_5_5 score1000-footer inline", "svg_panel_variant", 52, "Panel 5.5 footer inline override"),
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


def logo_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".svg":
        return "image/svg+xml"
    if suffix == ".png":
        return "image/png"
    raise ValueError(f"Unsupported logo asset type: {path}")


def asset_data_uri(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing logo asset: {path}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{logo_mime_type(path)};base64,{encoded}"


def font_data_uri(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing font asset: {path}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:font/ttf;base64,{encoded}"


def font_face_css() -> str:
    rules: list[str] = []
    for family, spec in FONT_ASSETS.items():
        rules.append(
            "\n".join(
                [
                    "      @font-face {",
                    f'        font-family: "{family}";',
                    f'        src: url("{font_data_uri(spec["path"])}") format("truetype");',
                    f'        font-weight: {spec["weight"]};',
                    "        font-style: normal;",
                    "        font-display: block;",
                    "      }",
                ]
            )
        )
    return "\n".join(rules)


def variant_logo_metadata() -> list[dict[str, object]]:
    logos: list[dict[str, object]] = []
    for role, path in VARIANT_LOGO_ASSETS.items():
        layout = VARIANT_LOGO_LAYOUT[role]
        logos.append(
            {
                "role": role,
                "source": rel(path),
                "sha256": sha256_file(path),
                "mime_type": logo_mime_type(path),
                "x": layout["x"],
                "y": layout["y"],
                "width": layout["width"],
                "height": layout["height"],
            }
        )
    return logos


def score1000_bar_logo_metadata() -> list[dict[str, object]]:
    logos: list[dict[str, object]] = []
    for reader_label, path in SCORE1000_BAR_LOGO_ASSETS.items():
        logos.append(
            {
                "reader_label": reader_label,
                "reader_key": score1000_bar_reader_key(reader_label),
                "source": rel(path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "mime_type": logo_mime_type(path),
            }
        )
    return logos


def score1000_bar_fallback_badge_metadata() -> list[dict[str, object]]:
    badges: list[dict[str, object]] = []
    for reader_label, badge in SCORE1000_BAR_FALLBACK_BADGES.items():
        badges.append(
            {
                "reader_label": reader_label,
                "reader_key": score1000_bar_reader_key(reader_label),
                "kind": "svg_text_badge",
                "label": badge["label"],
                "short_label": badge["short_label"],
                "note": badge["note"],
            }
        )
    return badges


def score1000_bar_reader_key(reader_label: str) -> str:
    try:
        return SCORE1000_BAR_READER_KEYS[reader_label]
    except KeyError as exc:
        raise ValueError(f"Missing Score2000 bar reader key for {reader_label!r}") from exc


def score1000_bar_display_label(reader_label: str) -> str:
    return " ".join(SCORE1000_BAR_LABEL_LINES.get(reader_label, [reader_label]))


def score1000_bar_reader_bindings(reader_labels: list[str], bar_colors: dict[str, str]) -> list[dict[str, object]]:
    bindings: list[dict[str, object]] = []
    for reader_label in reader_labels:
        logo_path = SCORE1000_BAR_LOGO_ASSETS.get(reader_label)
        fallback_badge = SCORE1000_BAR_FALLBACK_BADGES.get(reader_label)
        if logo_path is None and fallback_badge is None:
            raise ValueError(f"Missing Score2000 logo asset or fallback badge for {reader_label!r}")
        bindings.append(
            {
                "reader_label": reader_label,
                "reader_key": score1000_bar_reader_key(reader_label),
                "display_label": score1000_bar_display_label(reader_label),
                "logo_kind": "asset" if logo_path is not None else "svg_text_badge",
                **(
                    {
                        "logo_source": rel(logo_path),
                        "logo_sha256": sha256_file(logo_path),
                    }
                    if logo_path is not None
                    else {
                        "fallback_badge_label": fallback_badge["label"],
                        "fallback_badge_short_label": fallback_badge["short_label"],
                    }
                ),
                "color": bar_colors[reader_label],
            }
        )
    return bindings


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def outcome_palette_colors(palette_key: str) -> dict[str, str]:
    palette = OUTCOME_PALETTES[palette_key]
    return dict(palette["colors"])  # copy so callers cannot mutate the module constant


def outcome_palette_metadata(palette_key: str) -> dict[str, object]:
    palette = OUTCOME_PALETTES[palette_key]
    colors = outcome_palette_colors(palette_key)
    return {
        "key": palette_key,
        "name": palette["name"],
        "bin_order": BIN_ORDER,
        "legend_labels": LIKERT_LEGEND_LABELS,
        "colors": {key: colors[key] for key in BIN_ORDER},
    }


def use_white_label(fill: str) -> bool:
    color = fill.strip().lstrip("#")
    if len(color) != 6:
        return False
    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)
    luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
    return luminance < 0.48


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
    return count_label(score2000_value(row))


def score2000_value(row: dict[str, str]) -> float:
    value = str(row.get("score2000", "")).strip()
    if value:
        return fnum(row, "score2000")
    return fnum(row, "final_score1000") + SCORE2000_SHIFT


def score2000_rule_metadata() -> dict[str, object]:
    return {
        "formula": "score2000 = final_score1000 + 1000",
        "display_range": [0, 2000],
        "source_range": [-1000, 1000],
        "rank_preserving": True,
    }


def category_for_row(row: dict[str, str]) -> str:
    if row["reader_type"] == "Human comparator":
        return "Human Expert Baseline"
    label = row["reader_label"]
    for category, labels in CATEGORY_MODEL_GROUPS.items():
        if label in labels:
            return category
    raise ValueError(f"Unmapped model category for {label!r}")


def style(accessible_variant: bool = False, text_colors: dict[str, str] | None = None) -> str:
    text_fill = text_colors.get("text", INK) if text_colors else INK
    muted_fill = text_colors.get("text", MUTED) if text_colors else MUTED
    figure_title_fill = text_colors.get("figure_title", text_fill) if text_colors else INK
    variant_subtitle_fill = text_fill if text_colors else "#3c4043"
    variant_rules = ""
    if accessible_variant:
        variant_rules = f"""
      .figure-title {{ font-family: {TITLE_FONT}; font-size: 78px; font-weight: 800; fill: {figure_title_fill}; letter-spacing: 0; }}
      .variant-subtitle {{ font-family: {TITLE_FONT}; font-size: 42px; font-weight: 540; fill: {variant_subtitle_fill}; letter-spacing: 0; }}
      .variant-axis-label {{ font-family: {MONO}; font-size: 32px; font-weight: 760; fill: {text_fill}; letter-spacing: 0; }}
      .variant-row-label {{ font-family: {FONT}; font-size: 40px; font-weight: 820; fill: {text_fill}; letter-spacing: 0; }}
      .variant-score-label {{ font-family: {MONO}; font-size: 33px; font-weight: 850; fill: {text_fill}; letter-spacing: 0; }}
      .variant-bar-label {{ font-family: {MONO}; font-size: 31px; font-weight: 850; fill: {INK}; letter-spacing: 0; }}
      .variant-bar-label-white {{ font-family: {MONO}; font-size: 31px; font-weight: 850; fill: #ffffff; letter-spacing: 0; }}
      .variant-count-label {{ font-family: {MONO}; font-size: 31px; font-weight: 850; fill: {text_fill}; letter-spacing: 0; }}
      .variant-confidence-label {{ font-family: {MONO}; font-size: 31px; font-weight: 850; fill: {text_fill}; letter-spacing: 0; }}
      .variant-legend-label {{ font-family: {FONT}; font-size: 33px; font-weight: 780; fill: {text_fill}; letter-spacing: 0; }}
      .variant-group-label {{ font-family: {FONT}; font-size: 35px; font-weight: 880; fill: {text_fill}; letter-spacing: 0; }}
      .variant-micro {{ font-family: {MONO}; font-size: 40px; font-weight: 400; fill: {text_fill}; letter-spacing: 0; }}
      .score1000-panel-title {{ font-family: {TITLE_FONT}; font-size: 108px; font-weight: 760; fill: {text_fill}; letter-spacing: 0; }}
      .score1000-axis-title {{ font-family: {FONT}; font-size: 36px; font-weight: 760; fill: {text_fill}; letter-spacing: 0; }}
      .score1000-tick-label {{ font-family: {MONO}; font-size: 30px; font-weight: 620; fill: {text_fill}; letter-spacing: 0; }}
      .score1000-x-label {{ font-family: {FONT}; font-size: {SCORE1000_BAR_X_LABEL_FONT_SIZE:g}px; font-weight: 720; fill: {text_fill}; letter-spacing: 0; }}
      .score1000-bar-value {{ font-family: {MONO}; font-size: {SCORE1000_BAR_VALUE_FONT_SIZE:g}px; font-weight: 850; fill: {text_fill}; letter-spacing: 0; }}
      .score1000-gap-band-label {{ font-family: {TITLE_FONT}; font-size: 50px; font-weight: 830; fill: {text_fill}; letter-spacing: 0; }}
      .score1000-gap-value-label {{ font-family: {FONT}; font-size: 38px; font-weight: 780; fill: {text_fill}; letter-spacing: 0; }}
      .score1000-footer {{ font-family: {MONO}; font-size: 44px; font-weight: 375; fill: {text_fill}; letter-spacing: 0; }}
"""
    return f"""
    <style>
{font_face_css()}
      svg {{ background: {PAPER}; }}
      .frame {{ fill: #ffffff; stroke: {FRAME}; stroke-width: 3; }}
      .figure-title {{ font-family: {TITLE_FONT}; font-size: 76px; font-weight: 800; fill: {figure_title_fill}; letter-spacing: 0; }}
      .title {{ font-family: {TITLE_FONT}; font-size: 54px; font-weight: 760; fill: {text_fill}; letter-spacing: 0; }}
      .subtitle {{ font-family: {FONT}; font-size: 36px; font-weight: 400; fill: {muted_fill}; letter-spacing: 0; }}
      .header {{ font-family: {FONT}; font-size: 38px; font-weight: 720; fill: {text_fill}; letter-spacing: 0; }}
      .row-label {{ font-family: {FONT}; font-size: 32px; font-weight: 730; fill: {text_fill}; letter-spacing: 0; }}
      .score-label {{ font-family: {MONO}; font-size: 28px; font-weight: 800; fill: {text_fill}; letter-spacing: 0; }}
      .row-meta {{ font-family: {MONO}; font-size: 22px; fill: {muted_fill}; letter-spacing: 0; }}
      .axis-label {{ font-family: {MONO}; font-size: 28px; fill: {text_fill}; letter-spacing: 0; }}
      .bar-label {{ font-family: {MONO}; font-size: 28px; font-weight: 800; fill: {INK}; letter-spacing: 0; }}
      .bar-label-white {{ font-family: {MONO}; font-size: 28px; font-weight: 800; fill: #ffffff; letter-spacing: 0; }}
      .count-label {{ font-family: {MONO}; font-size: 28px; font-weight: 800; fill: {text_fill}; letter-spacing: 0; }}
      .confidence-label {{ font-family: {MONO}; font-size: 28px; font-weight: 800; fill: {text_fill}; letter-spacing: 0; }}
      .legend-label {{ font-family: {FONT}; font-size: 29px; font-weight: 700; fill: {text_fill}; letter-spacing: 0; }}
      .small {{ font-family: {FONT}; font-size: 26px; fill: {text_fill}; letter-spacing: 0; }}
      .micro {{ font-family: {MONO}; font-size: 22px; fill: {muted_fill}; letter-spacing: 0; }}
      .caption {{ font-family: {FONT}; font-size: 26px; fill: {text_fill}; letter-spacing: 0; }}
      .grid {{ stroke: {GRID}; stroke-width: 2; stroke-dasharray: 7 12; }}
      .score2000-grid {{ stroke: #dfe5e8; stroke-width: 1.35; stroke-dasharray: none; opacity: 0.72; }}
      .axis {{ stroke: {INK}; stroke-width: 3; }}
      .bar {{ stroke-width: 2.4; }}
      .bar-segments .bar {{ shape-rendering: crispEdges; }}
      .bar-outline {{ fill: none; stroke: rgba(45,52,57,.18); stroke-width: 1.2; }}
      .legend-outline {{ fill: none; stroke: rgba(45,52,57,.22); stroke-width: 1.2; }}
      .barcode-unit {{ stroke-width: 1.2; }}
      .track {{ fill: {TRACK}; stroke: #dfd9ce; stroke-width: 1.4; }}
{variant_rules}    </style>
    """


def text(x: float, y: float, value: object, cls: str = "small", anchor: str = "start", extra: str = "") -> str:
    attrs = f" {extra}" if extra else ""
    return f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}"{attrs}>{esc(value)}</text>'


def line(x1: float, y1: float, x2: float, y2: float, cls: str = "axis", extra: str = "") -> str:
    attrs = f" {extra}" if extra else ""
    return f'<line class="{cls}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"{attrs} />'


def rect(x: float, y: float, width: float, height: float, fill: str, stroke: str, cls: str = "bar", rx: float = 7, extra: str = "") -> str:
    width = max(0.0, width)
    return (
        f'<rect class="{cls}" x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" '
        f'rx="{rx:.1f}" fill="{fill}" stroke="{stroke}" {extra}/>'
    )


def multiline_text(
    x: float,
    y: float,
    lines: list[str],
    cls: str,
    anchor: str = "middle",
    line_step: float = 40,
    extra: str = "",
) -> str:
    attrs = f" {extra}" if extra else ""
    tspans = []
    for idx, line_text in enumerate(lines):
        dy = 0 if idx == 0 else line_step
        tspans.append(f'<tspan x="{x:.1f}" dy="{dy:.1f}">{esc(line_text)}</tspan>')
    return f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}"{attrs}>{"".join(tspans)}</text>'


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
            "score2000": score2000_value(row),
            "bins": {key: fnum(row, key) for key in BIN_ORDER},
            "dot_bins": {key: inum(row, f"dot_{key}") for key in BIN_ORDER},
        }
        out.append(item)
    return out


def svg_open(
    panel_id: int,
    title: str,
    desc: str,
    rows: list[dict[str, str]],
    provenance: dict[str, object],
    variant: str | None = None,
    outcome_palette_key: str = "current",
    category_colors: dict[str, str] | None = None,
    text_colors: dict[str, str] | None = None,
    extra_metadata: dict[str, object] | None = None,
    svg_h: float | None = None,
) -> list[str]:
    active_category_colors = category_colors or CATEGORY_COLORS
    metadata = {
        "panel_id": panel_id,
        "source_csv": provenance["score1000_scored_rows"]["path"],
        "summary_csv": provenance["summary_csv"]["path"],
        "source_master_sha256": provenance["source_master_sha256"],
        "score1000_scored_rows_sha256": provenance["score1000_scored_rows"]["sha256"],
        "score1000_rule": {
            "idk_score": IDK_SCORE,
            "all_idk_baseline": IDK_SCORE * 200,
        },
        "score2000_rule": score2000_rule_metadata(),
        "rows": payload_rows(rows),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    if variant is not None:
        metadata["variant"] = variant
        metadata["category_colors"] = active_category_colors
        metadata["outcome_palette"] = outcome_palette_metadata(outcome_palette_key)
        metadata["logos"] = variant_logo_metadata()
        if text_colors is not None:
            metadata["text_colors"] = text_colors
    svg_h = svg_h if svg_h is not None else (VARIANT_H if variant is not None else H)
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{svg_h}" viewBox="0 0 {W} {svg_h}" role="img">',
        f"<title>{esc(title)}</title>",
        f"<desc>{esc(desc)}</desc>",
        f'<metadata id="radle-panel-data">{esc(json.dumps(metadata, sort_keys=True))}</metadata>',
        style(accessible_variant=variant is not None, text_colors=text_colors),
        f'<rect class="frame" x="28" y="28" width="3544" height="{svg_h - 56}" rx="22" />',
    ]


def wrap_text(value: str, max_chars: int) -> list[str]:
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def wrap_balanced(value: str, max_chars: int) -> list[str]:
    """Wrap into the fewest lines that fit max_chars, then even out line lengths."""
    line_count = len(wrap_text(value, max_chars))
    if line_count <= 1:
        return [value]
    words = value.split()
    target = len(value) / line_count
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > target and len(lines) < line_count - 1:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def add_top_logos(parts: list[str], scale: float = 1.0) -> None:
    for role, path in VARIANT_LOGO_ASSETS.items():
        layout = VARIANT_LOGO_LAYOUT[role]
        width = float(layout["width"]) * scale
        height = float(layout["height"]) * scale
        x = float(layout["x"])
        if role == "right-lab-logo":
            x = float(layout["x"]) + float(layout["width"]) - width
        parts.append(
            (
                f'<image class="top-logo" data-logo="{esc(role)}" '
                f'x="{x:.1f}" y="{float(layout["y"]):.1f}" '
                f'width="{width:.1f}" height="{height:.1f}" '
                f'preserveAspectRatio="xMidYMid meet" '
                f'aria-label="{esc(str(layout["label"]))}" '
                f'href="{asset_data_uri(path)}" />'
            )
        )


def add_header(
    parts: list[str],
    title: str,
    subtitle: str,
    include_logos: bool = False,
    content_y_shift: float = 0,
    subtitle_cls: str = "subtitle",
    subtitle_line_step: float = 48,
    subtitle_y_offset: float = 0,
) -> None:
    if include_logos:
        add_top_logos(parts)
    parts.append(text(W / 2, FIGURE_TITLE_Y, FIGURE_TITLE, "figure-title", "middle"))
    parts.append(text(80, 234 + content_y_shift, title, "title"))
    for idx, line_text in enumerate(wrap_text(subtitle, 172)):
        parts.append(text(80, 292 + content_y_shift + subtitle_y_offset + idx * subtitle_line_step, line_text, subtitle_cls))


FOOTER_SCORE1000_NOTE = score1000_footer_note(IDK_SCORE)


def add_footer(
    parts: list[str],
    provenance: dict[str, object],
    micro_cls: str = "micro",
    text_y: float = 2604,
    line_step: float = 32,
    max_chars: int = 232,
    divider_y: float = 2560,
) -> None:
    parts.append(line(80, divider_y, 3520, divider_y, "axis"))
    for idx, line_text in enumerate(wrap_balanced(FOOTER_SCORE1000_NOTE, max_chars)):
        parts.append(text(80, text_y + idx * line_step, line_text, micro_cls))


def add_row_identity(
    parts: list[str],
    row: dict[str, str],
    score_x: float,
    name_x: float,
    y: float,
    name_color: str | None = None,
    name_weight: int | None = None,
    score_color: str | None = None,
    score_cls: str = "score-label",
    name_cls: str = "row-label",
) -> None:
    score_extra_parts: list[str] = []
    if score_color:
        score_extra_parts.append(f'style="fill:{score_color};"')
        score_extra_parts.append(f'data-score-category="{esc(category_for_row(row))}"')
        score_extra_parts.append(f'data-reader-label="{esc(row["reader_label"])}"')
    parts.append(text(score_x, y, score_label(row), score_cls, "end", extra=" ".join(score_extra_parts)))
    extra_parts: list[str] = []
    if name_color:
        extra_parts.append(f'style="fill:{name_color};"')
        extra_parts.append(f'data-category="{esc(category_for_row(row))}"')
    if name_weight:
        extra_parts.append(f'font-weight="{name_weight}"')
    parts.append(text(name_x, y, display_name(row), name_cls, "end", extra=" ".join(extra_parts)))


def add_ledger_axis(
    parts: list[str],
    chart_x: float,
    y_top: float,
    axis_y: float,
    chart_w: float,
    axis_label_cls: str = "axis-label",
) -> None:
    for value in [0, 50, 100, 150, 200]:
        x = chart_x + chart_w * value / 200
        parts.append(line(x, y_top, x, axis_y, "grid"))
        parts.append(text(x, axis_y + 38, f"{value}", axis_label_cls, "middle"))
    parts.append(line(chart_x, axis_y, chart_x + chart_w, axis_y, "axis"))


def add_segment_label(
    parts: list[str],
    x: float,
    y: float,
    width: float,
    height: float,
    label: str,
    fill: str,
    anchor: str = "middle",
    label_cls: str = "bar-label",
    white_label_cls: str = "bar-label-white",
) -> None:
    if width < max(MIN_LABEL_WIDTH, len(label) * LABEL_CHAR_W + 2 * LABEL_PAD_X):
        return
    cls = white_label_cls if use_white_label(fill) else label_cls
    parts.append(text(x, y + height / 2, label, cls, anchor, extra='dominant-baseline="middle"'))


def add_category_key(
    parts: list[str],
    y: float,
    label_cls: str = "legend-label",
    x_shift: float = 0.0,
    category_colors: dict[str, str] | None = None,
) -> None:
    active_category_colors = category_colors or CATEGORY_COLORS
    items = [
        (VARIANT_KEY_SWATCH_X["Human Expert Baseline"] + x_shift, "Human Expert Baseline"),
        (VARIANT_KEY_SWATCH_X["Closed generalist"] + x_shift, "Closed generalist"),
        (VARIANT_KEY_SWATCH_X["Open generalist"] + x_shift, "Open generalist"),
        (VARIANT_KEY_SWATCH_X["Open medical"] + x_shift, "Open medical"),
    ]
    for swatch_x, category in items:
        color = active_category_colors[category]
        parts.append(
            rect(
                swatch_x,
                y - 22,
                28,
                28,
                color,
                color,
                cls="category-swatch",
                rx=5,
                extra=f'data-category-key="{esc(category)}"',
            )
        )
        parts.append(
            text(
                swatch_x + 40,
                y,
                category,
                label_cls,
                "start",
                extra=f'style="fill:{color};" data-category-key="{esc(category)}"',
            )
        )


def add_panel2_bar_row(
    parts: list[str],
    row: dict[str, str],
    *,
    chart_x: float,
    chart_w: float,
    bar_h: float,
    y: float,
    clip_id: str,
    score_x: float,
    name_x: float,
    label_y: float,
    name_color: str | None = None,
    name_weight: int | None = None,
    score_cls: str = "score-label",
    name_cls: str = "row-label",
    count_cls: str = "bar-label",
    segment_label_cls: str = "bar-label",
    segment_white_label_cls: str = "bar-label-white",
    score_color: str | None = None,
    left_count_gap: float = 18,
    colors: dict[str, str] | None = None,
) -> None:
    colors = colors or COLORS
    parts.append(rect(chart_x, y - 7, chart_w, bar_h + 14, TRACK, "#e1d9cd", cls="track", rx=9))
    parts.append(f"<defs>{clip_path_rect(clip_id, chart_x, y, chart_w, bar_h, 10)}</defs>")
    parts.append(f'<g class="bar-segments" clip-path="url(#{clip_id})">')

    x = chart_x
    for key in BIN_ORDER:
        value = fnum(row, key)
        width = chart_w * value / 200
        if width:
            fill = colors[key]
            parts.append(rect(x, y, width, bar_h, fill, "none", rx=0, extra=f'data-bin="{key}" data-value="{row[key]}"'))
            add_segment_label(
                parts,
                x + width / 2,
                y,
                width,
                bar_h,
                count_label(value),
                fill,
                label_cls=segment_label_cls,
                white_label_cls=segment_white_label_cls,
            )
        x += width
    parts.append("</g>")
    parts.append(rect(chart_x, y, chart_w, bar_h, "none", "rgba(45,52,57,.18)", cls="bar-outline", rx=10))

    parts.append(text(chart_x - left_count_gap, label_y, count_label(fnum(row, "correct_total")), count_cls, "end"))
    parts.append(text(chart_x + chart_w + 18, label_y, count_label(fnum(row, "wrong_total")), count_cls, "start"))
    add_row_identity(
        parts,
        row,
        score_x,
        name_x,
        label_y,
        name_color=name_color,
        name_weight=name_weight,
        score_color=score_color,
        score_cls=score_cls,
        name_cls=name_cls,
    )


def panel_2(rows: list[dict[str, str]], provenance: dict[str, object]) -> str:
    title = "Diagnostic outcomes stratified by confidence"
    subtitle = "Each row is one reader group or model, 200 effective cases, ranked by Score2000. The Human Expert Baseline pools 12 readers; model rows are single evaluation runs."
    parts = svg_open(2, title, subtitle, rows, provenance)
    add_header(parts, title, subtitle)
    chart_x, chart_w, bar_h = 810, 2600, 54
    row_step, y0, axis_y = 108, 430, 2290
    score_x, name_x = 220, 690
    parts.append(text(score_x, y0 - 54, "Score2000", "axis-label", "end"))
    parts.append(text(name_x, y0 - 54, "Reader / model", "axis-label", "end"))
    add_ledger_axis(parts, chart_x, y0 - 40, axis_y, chart_w)
    for idx, row in enumerate(rows):
        y = y0 + idx * row_step
        add_panel2_bar_row(
            parts,
            row,
            chart_x=chart_x,
            chart_w=chart_w,
            bar_h=bar_h,
            y=y,
            clip_id=f"panel2-row-{idx}",
            score_x=score_x,
            name_x=name_x,
            label_y=y + 41,
        )
    add_legend(parts, 2424, chart_x, chart_w, "panel2")
    add_footer(parts, provenance)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def panel_2_variant_colored_names(
    rows: list[dict[str, str]],
    provenance: dict[str, object],
    *,
    variant_label: str = "2.1 revised colored model names",
    palette_key: str = "current",
    chart_x: float = VARIANT_CHART_X,
    chart_w: float = VARIANT_CHART_W,
    score_x: float = VARIANT_SCORE_X,
    name_x: float = VARIANT_NAME_X,
    category_key_shift_x: float = 0.0,
    category_colors: dict[str, str] | None = None,
    text_colors: dict[str, str] | None = None,
    color_scores: bool = False,
) -> str:
    title = "Diagnostic outcomes stratified by confidence"
    subtitle = "Each row is one reader group or model, 200 effective cases, ranked by Score2000. The Human Expert Baseline pools 12 readers; model rows are single evaluation runs."
    outcome_colors = outcome_palette_colors(palette_key)
    active_category_colors = category_colors or CATEGORY_COLORS
    parts = svg_open(
        2,
        title,
        subtitle,
        rows,
        provenance,
        variant=variant_label,
        outcome_palette_key=palette_key,
        category_colors=active_category_colors,
        text_colors=text_colors,
    )
    add_header(
        parts,
        title,
        subtitle,
        include_logos=True,
        content_y_shift=VARIANT_CONTENT_Y_SHIFT,
        subtitle_cls="variant-subtitle",
        subtitle_line_step=54,
        subtitle_y_offset=VARIANT_SUBTITLE_Y_OFFSET,
    )
    bar_h = VARIANT_BAR_H_2_1
    row_step, y0, axis_y = 103, VARIANT_HEADER_Y + 80, VARIANT_AXIS_Y
    outside_count_cls = "variant-count-label" if text_colors else "variant-bar-label"
    confidence_label_cls = "variant-confidence-label" if text_colors else "variant-bar-label"
    parts.append(text(score_x, VARIANT_HEADER_Y, "Score", "variant-axis-label", "end"))
    parts.append(text(name_x, VARIANT_HEADER_Y, "Reader / model", "variant-axis-label", "end"))
    add_category_key(
        parts,
        VARIANT_HEADER_Y,
        label_cls="variant-legend-label",
        x_shift=category_key_shift_x,
        category_colors=active_category_colors,
    )
    add_ledger_axis(parts, chart_x, y0 - 40, axis_y, chart_w, axis_label_cls="variant-axis-label")
    for idx, row in enumerate(rows):
        y = y0 + idx * row_step
        category = category_for_row(row)
        add_panel2_bar_row(
            parts,
            row,
            chart_x=chart_x,
            chart_w=chart_w,
            bar_h=bar_h,
            y=y,
            clip_id=f"panel2-row-2-1-{idx}",
            score_x=score_x,
            name_x=name_x,
            label_y=y + VARIANT_LABEL_DY_2_1,
            name_color=active_category_colors[category],
            name_weight=780,
            score_color=active_category_colors[category] if color_scores else None,
            score_cls="variant-score-label",
            name_cls="variant-row-label",
            count_cls=outside_count_cls,
            segment_label_cls="variant-bar-label",
            segment_white_label_cls="variant-bar-label-white",
            left_count_gap=18,
            colors=outcome_colors,
        )
    add_legend(
        parts,
        VARIANT_LEGEND_Y,
        chart_x,
        chart_w,
        "panel2",
        legend_label_cls="variant-legend-label",
        confidence_label_cls=confidence_label_cls,
        colors=outcome_colors,
    )
    add_footer(
        parts,
        provenance,
        micro_cls="variant-micro",
        text_y=VARIANT_FOOTER_TEXT_Y,
        line_step=VARIANT_FOOTER_LINE_STEP,
        max_chars=VARIANT_FOOTER_WRAP_CHARS,
        divider_y=VARIANT_FOOTER_DIVIDER_Y,
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def grouped_rows(rows: list[dict[str, str]]) -> list[tuple[str, list[dict[str, str]]]]:
    groups: list[tuple[str, list[dict[str, str]]]] = []
    for category in CATEGORY_ORDER:
        group_rows = [row for row in rows if category_for_row(row) == category]
        groups.append((category, group_rows))
    if sum(len(group_rows) for _, group_rows in groups) != len(rows):
        raise ValueError("Grouped row count does not match source row count")
    return groups


def panel_2_variant_grouped_bands(
    rows: list[dict[str, str]],
    provenance: dict[str, object],
    *,
    variant_label: str = "3.1 revised grouped bands",
    palette_key: str = "current",
    show_group_headers: bool = True,
    color_row_names: bool = False,
    chart_x: float = VARIANT_CHART_X,
    chart_w: float = VARIANT_CHART_W,
    score_x: float = VARIANT_SCORE_X,
    name_x: float = VARIANT_NAME_X,
    category_key_shift_x: float = 0.0,
    category_colors: dict[str, str] | None = None,
    text_colors: dict[str, str] | None = None,
    color_scores: bool = False,
) -> str:
    title = "Diagnostic outcomes stratified by confidence"
    subtitle = "Each row is one reader group or model, 200 effective cases, ranked by Score2000. The Human Expert Baseline pools 12 readers; model rows are single evaluation runs."
    outcome_colors = outcome_palette_colors(palette_key)
    active_category_colors = category_colors or CATEGORY_COLORS
    ordered_groups = grouped_rows(rows)
    ordered_rows = [row for _, group_rows in ordered_groups for row in group_rows]
    parts = svg_open(
        2,
        title,
        subtitle,
        ordered_rows,
        provenance,
        variant=variant_label,
        outcome_palette_key=palette_key,
        category_colors=active_category_colors,
        text_colors=text_colors,
    )
    add_header(
        parts,
        title,
        subtitle,
        include_logos=True,
        content_y_shift=VARIANT_CONTENT_Y_SHIFT,
        subtitle_cls="variant-subtitle",
        subtitle_line_step=54,
        subtitle_y_offset=VARIANT_SUBTITLE_Y_OFFSET,
    )
    bar_h = VARIANT_BAR_H_3_1
    row_step = 88
    axis_y = VARIANT_AXIS_Y
    legend_y = VARIANT_LEGEND_Y
    outside_count_cls = "variant-count-label" if text_colors else "variant-bar-label"
    confidence_label_cls = "variant-confidence-label" if text_colors else "variant-bar-label"
    parts.append(text(score_x, VARIANT_HEADER_Y, "Score", "variant-axis-label", "end"))
    parts.append(text(name_x, VARIANT_HEADER_Y, "Reader / model", "variant-axis-label", "end"))
    add_category_key(
        parts,
        VARIANT_HEADER_Y,
        label_cls="variant-legend-label",
        x_shift=category_key_shift_x,
        category_colors=active_category_colors,
    )

    y_cursor = VARIANT_HEADER_Y + VARIANT_GROUP_HEADER_MIN_GAP + 10
    first_bar_y = y_cursor + 28
    add_ledger_axis(parts, chart_x, first_bar_y - 40, axis_y, chart_w, axis_label_cls="variant-axis-label")
    row_idx = 0
    for category, group_rows in ordered_groups:
        color = active_category_colors[category]
        header_label = category if category == "Human Expert Baseline" else f"{category} models"
        if show_group_headers:
            parts.append(
                text(
                    VARIANT_GROUP_HEADER_X,
                    y_cursor,
                    header_label,
                    "variant-group-label",
                    "start",
                    extra=f'style="fill:{color};" data-category-header="{esc(category)}"',
                )
            )
            parts.append(line(VARIANT_GROUP_RULE_X1, y_cursor + 12, VARIANT_GROUP_RULE_X2, y_cursor + 12, "axis"))
        row_y = y_cursor + 28
        for row in group_rows:
            add_panel2_bar_row(
                parts,
                row,
                chart_x=chart_x,
                chart_w=chart_w,
                bar_h=bar_h,
                y=row_y,
                clip_id=f"panel2-row-3-1-{row_idx}",
                score_x=score_x,
                name_x=name_x,
                label_y=row_y + VARIANT_LABEL_DY_3_1,
                score_cls="variant-score-label",
                name_cls="variant-row-label",
                count_cls=outside_count_cls,
                segment_label_cls="variant-bar-label",
                segment_white_label_cls="variant-bar-label-white",
                left_count_gap=18,
                colors=outcome_colors,
                name_color=active_category_colors[category] if color_row_names else None,
                score_color=active_category_colors[category] if color_scores else None,
            )
            row_y += row_step
            row_idx += 1
        y_cursor = row_y + 42
    add_legend(
        parts,
        legend_y,
        chart_x,
        chart_w,
        "panel2",
        legend_label_cls="variant-legend-label",
        confidence_label_cls=confidence_label_cls,
        colors=outcome_colors,
    )
    add_footer(
        parts,
        provenance,
        micro_cls="variant-micro",
        text_y=VARIANT_FOOTER_TEXT_Y,
        line_step=VARIANT_FOOTER_LINE_STEP,
        max_chars=VARIANT_FOOTER_WRAP_CHARS,
        divider_y=VARIANT_FOOTER_DIVIDER_Y,
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def score1000_bar_rows(
    rows: list[dict[str, str]],
    reader_labels: list[str] | None = None,
) -> list[dict[str, str]]:
    active_reader_labels = reader_labels or SCORE1000_BAR_READER_LABELS
    by_label = {row["reader_label"]: row for row in rows}
    missing = [label for label in active_reader_labels if label not in by_label]
    if missing:
        raise ValueError(f"Missing Score1000 bar chart rows: {missing}")
    selected = [by_label[label] for label in active_reader_labels]
    return sorted(selected, key=lambda row: (-score2000_value(row), row["reader_label"]))


def score1000_bar_scale(
    value: float,
    y_min: float = SCORE1000_BAR_Y_MIN,
    y_max: float = SCORE1000_BAR_Y_MAX,
    chart_y: float = SCORE1000_BAR_CHART_Y,
    chart_h: float = SCORE1000_BAR_CHART_H,
) -> float:
    return chart_y + ((y_max - value) / (y_max - y_min)) * chart_h


def score1000_bar_logo_or_badge(
    *,
    label: str,
    reader_key: str,
    center_x: float,
    center_y: float,
    icon_box: float,
    image_size: float,
    color: str,
    backplate: bool = True,
    cls_prefix: str = "score1000-bar",
) -> str:
    logo_asset = SCORE1000_BAR_LOGO_ASSETS.get(label)
    icon_x = center_x - icon_box / 2
    icon_y = center_y - icon_box / 2
    parts: list[str] = []
    if backplate:
        parts.append(
            rect(
                icon_x,
                icon_y,
                icon_box,
                icon_box,
                "#ffffff",
                color,
                cls=f"{cls_prefix}-logo-backplate",
                rx=max(12.0, 18.0 * (icon_box / SCORE1000_BAR_LOGO_BOX)),
                extra=(
                    f'stroke-width="3.5" opacity="0.96" data-score1000-bar-logo-backplate="{esc(label)}" '
                    f'data-reader-label="{esc(label)}" data-reader-key="{esc(reader_key)}"'
                ),
            )
        )
    if logo_asset is not None:
        parts.append(
            f'<image class="{cls_prefix}-logo" data-score1000-bar-logo="{esc(label)}" '
            f'data-reader-label="{esc(label)}" data-reader-key="{esc(reader_key)}" '
            f'data-logo-kind="asset" data-source-logo="{esc(rel(logo_asset))}" '
            f'x="{center_x - image_size / 2:.1f}" y="{center_y - image_size / 2:.1f}" '
            f'width="{image_size:.1f}" height="{image_size:.1f}" preserveAspectRatio="xMidYMid meet" '
            f'href="{asset_data_uri(logo_asset)}" />'
        )
    else:
        badge = SCORE1000_BAR_FALLBACK_BADGES[label]
        parts.append(
            rect(
                center_x - image_size / 2,
                center_y - image_size / 2,
                image_size,
                image_size,
                color,
                color,
                cls=f"{cls_prefix}-logo-fallback",
                rx=max(10.0, image_size / 5),
                extra=(
                    f'data-score1000-bar-logo="{esc(label)}" data-reader-label="{esc(label)}" '
                    f'data-reader-key="{esc(reader_key)}" data-logo-kind="svg_text_badge" '
                    f'data-fallback-badge-label="{esc(badge["label"])}"'
                ),
            )
        )
        parts.append(
            text(
                center_x,
                center_y + image_size * 0.14,
                badge["short_label"],
                "score1000-x-label",
                "middle",
                extra=(
                    f'style="fill:#ffffff;font-size:{max(30.0, image_size * 0.38):.1f}px;font-weight:850;" '
                    f'data-score1000-bar-logo-fallback-text="{esc(label)}" data-reader-label="{esc(label)}" '
                    f'data-reader-key="{esc(reader_key)}"'
                ),
            )
        )
    return "\n".join(parts)


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


def score1000_bar_barcode_sequence(row: dict[str, str], max_units: int) -> list[str]:
    counts = {key: int(float(row.get(f"dot_{key}", 0))) for key in BIN_ORDER}
    total = sum(counts.values())
    if max_units <= 0 or total <= 0:
        return []
    quotas = {key: counts[key] * max_units / total for key in BIN_ORDER}
    base_counts = {key: int(quotas[key]) for key in BIN_ORDER}
    remaining = max_units - sum(base_counts.values())
    ranked = sorted(BIN_ORDER, key=lambda key: (quotas[key] - base_counts[key], counts[key]), reverse=True)
    for key in ranked[:remaining]:
        base_counts[key] += 1
    sequence: list[str] = []
    for key in BIN_ORDER:
        sequence.extend([key] * base_counts[key])
    return sequence


def score1000_bar_barcode_overlay(
    row: dict[str, str],
    *,
    center_x: float,
    bar_y: float,
    bar_bottom: float,
    capsule_w: float,
    capsule_h: float,
    capsule_gap: float,
    units: int,
    colors: dict[str, str],
) -> str:
    usable_h = max(0.0, bar_bottom - bar_y - SCORE1000_BAR_BARCODE_TOP_PAD - SCORE1000_BAR_BARCODE_BOTTOM_PAD)
    max_units = min(units, int((usable_h + capsule_gap) // (capsule_h + capsule_gap)))
    sequence = score1000_bar_barcode_sequence(row, max_units)
    if not sequence:
        return ""
    total_h = len(sequence) * capsule_h + (len(sequence) - 1) * capsule_gap
    start_y = bar_bottom - SCORE1000_BAR_BARCODE_BOTTOM_PAD - total_h
    x = center_x - capsule_w / 2
    parts = [
        (
            f'<g class="score1000-barcode-overlay" data-reader-label="{esc(row["reader_label"])}" '
            f'data-barcode-units="{len(sequence)}" data-barcode-source-units="{DOT_DISPLAY_TOTAL}" '
            f'data-barcode-order="bottom-to-top">'
        )
    ]
    for idx, key in enumerate(sequence):
        y = start_y + (len(sequence) - 1 - idx) * (capsule_h + capsule_gap)
        parts.append(
            rect(
                x,
                y,
                capsule_w,
                capsule_h,
                colors[key],
                colors[key],
                cls="score1000-barcode-capsule",
                rx=capsule_h / 2,
                extra=(
                    f'data-reader-label="{esc(row["reader_label"])}" data-bin="{esc(key)}" '
                    f'data-bottom-to-top-index="{idx}"'
                ),
            )
        )
    parts.append("</g>")
    return "\n".join(parts)


def score1000_gap_data_number(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def score1000_bar_gap_overlay_metadata(
    selected_rows: list[dict[str, str]],
    active_bar_colors: dict[str, str],
    *,
    date_label: str,
) -> dict[str, object]:
    human_rows = [row for row in selected_rows if row["reader_label"] == "Human Expert Baseline"]
    if len(human_rows) != 1:
        raise ValueError("Score gap overlay needs exactly one Human Expert Baseline row")
    ai_rows = [row for row in selected_rows if row["reader_type"] == "AI model"]
    if not ai_rows:
        raise ValueError("Score gap overlay needs at least one visible AI model row")
    top_ai_score = max(score2000_value(row) for row in ai_rows)
    top_ai_row = next(row for row in ai_rows if abs(score2000_value(row) - top_ai_score) < 1e-9)
    human_row = human_rows[0]
    human_score = score2000_value(human_row)
    gap_value = human_score - top_ai_score
    gap_abs_value = abs(gap_value)
    gap_rounded = int(gap_abs_value + 0.5)
    gap_direction = "Human-AI" if gap_value >= 0 else "AI-Human"
    visible_label = f"{gap_rounded} point {gap_direction} gap: {date_label}"
    human_label = human_row["reader_label"]
    top_ai_label = top_ai_row["reader_label"]
    return {
        "enabled": True,
        "human_label": human_label,
        "human_display_label": display_name(human_row),
        "human_score": human_score,
        "human_color": active_bar_colors[human_label],
        "top_ai_label": top_ai_label,
        "top_ai_display_label": display_name(top_ai_row),
        "top_ai_score": top_ai_score,
        "top_ai_color": active_bar_colors[top_ai_label],
        "gap_value": gap_value,
        "gap_abs_value": gap_abs_value,
        "gap_rounded": gap_rounded,
        "gap_direction": gap_direction,
        "date_label": date_label,
        "visible_label": visible_label,
    }


def score1000_bar_gap_overlay_svg(
    overlay: dict[str, object],
    *,
    chart_x: float,
    chart_w: float,
    y_min: float,
    y_max: float,
    chart_y: float,
    chart_h: float,
    axis_break_after: float | None,
    axis_break_top_fraction: float,
) -> str:
    human_score = float(overlay["human_score"])
    top_ai_score = float(overlay["top_ai_score"])
    human_y = score1000_bar_scaled_y(
        human_score,
        y_min=y_min,
        y_max=y_max,
        chart_y=chart_y,
        chart_h=chart_h,
        axis_break_after=axis_break_after,
        axis_break_top_fraction=axis_break_top_fraction,
    )
    top_ai_y = score1000_bar_scaled_y(
        top_ai_score,
        y_min=y_min,
        y_max=y_max,
        chart_y=chart_y,
        chart_h=chart_h,
        axis_break_after=axis_break_after,
        axis_break_top_fraction=axis_break_top_fraction,
    )
    line_x1 = chart_x + chart_w * SCORE1000_BAR_GAP_OVERLAY_LINE_START_FRACTION
    line_x2 = chart_x + chart_w * SCORE1000_BAR_GAP_OVERLAY_LINE_END_FRACTION
    line_w = line_x2 - line_x1
    arrow_x = line_x1 + line_w * SCORE1000_BAR_GAP_OVERLAY_ARROW_LINE_FRACTION
    human_label_x = line_x1 + line_w * SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_LINE_FRACTION
    top_ai_label_x = line_x1 + (arrow_x - line_x1) * SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_PRE_ARROW_FRACTION
    arrow_top_y = min(human_y, top_ai_y)
    arrow_bottom_y = max(human_y, top_ai_y)
    arrow_head_len = (arrow_bottom_y - arrow_top_y) * SCORE1000_BAR_GAP_OVERLAY_ARROW_DIAGONAL_RATIO
    arrow_head_w = arrow_head_len * SCORE1000_BAR_GAP_OVERLAY_ARROW_45_PROJECTION
    arrow_head_h = arrow_head_len * SCORE1000_BAR_GAP_OVERLAY_ARROW_45_PROJECTION
    arrow_mid_y = (arrow_top_y + arrow_bottom_y) / 2
    human_score_attr = score1000_gap_data_number(human_score)
    top_ai_score_attr = score1000_gap_data_number(top_ai_score)
    gap_value_attr = score1000_gap_data_number(float(overlay["gap_value"]))
    gap_abs_attr = score1000_gap_data_number(float(overlay["gap_abs_value"]))
    human_color = str(overlay["human_color"])
    top_ai_color = str(overlay["top_ai_color"])
    label_x = arrow_x + SCORE1000_BAR_GAP_OVERLAY_LABEL_X_OFFSET
    label_y = arrow_mid_y + 13.0
    arrow_shaft_style = (
        f"stroke:{SCORE1000_BAR_GAP_OVERLAY_ARROW_COLOR};"
        f"stroke-width:{SCORE1000_BAR_GAP_OVERLAY_ARROW_SHAFT_WIDTH:g};"
        "stroke-linecap:round;stroke-linejoin:round;fill:none;opacity:0.96;"
    )
    arrow_head_style = (
        f"stroke:{SCORE1000_BAR_GAP_OVERLAY_ARROW_COLOR};"
        f"stroke-width:{SCORE1000_BAR_GAP_OVERLAY_ARROW_HEAD_WIDTH:g};"
        "stroke-linecap:round;stroke-linejoin:round;fill:none;opacity:0.96;"
    )
    group_extra = (
        'data-score-gap-overlay="true" '
        f'data-human-score="{esc(human_score_attr)}" '
        f'data-human-label="{esc(overlay["human_label"])}" '
        f'data-human-display-label="{esc(overlay["human_display_label"])}" '
        f'data-top-ai-score="{esc(top_ai_score_attr)}" '
        f'data-top-ai-label="{esc(overlay["top_ai_label"])}" '
        f'data-top-ai-display-label="{esc(overlay["top_ai_display_label"])}" '
        f'data-gap-value="{esc(gap_value_attr)}" '
        f'data-gap-abs-value="{esc(gap_abs_attr)}" '
        f'data-gap-rounded="{int(overlay["gap_rounded"])}" '
        f'data-gap-direction="{esc(overlay["gap_direction"])}" '
        f'data-score-gap-date-label="{esc(overlay["date_label"])}" '
        f'data-arrow-head-diagonal-ratio="{SCORE1000_BAR_GAP_OVERLAY_ARROW_DIAGONAL_RATIO:g}" '
        f'data-arrow-line-fraction="{SCORE1000_BAR_GAP_OVERLAY_ARROW_LINE_FRACTION:g}" '
        f'data-human-label-line-fraction="{SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_LINE_FRACTION:g}" '
        f'data-top-ai-label-pre-arrow-fraction="{SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_PRE_ARROW_FRACTION:g}" '
        f'data-human-label-text="{esc(SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL)}" '
        f'data-top-ai-label-text="{esc(SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL)}"'
    )
    parts = [f'<g class="score1000-gap-overlay" {group_extra}>']
    parts.append(
        line(
            line_x1,
            human_y,
            line_x2,
            human_y,
            "score1000-gap-line",
            extra=(
                f'data-score-gap-line="human" data-score2000-value="{esc(human_score_attr)}" '
                f'style="stroke:{human_color};stroke-width:12;stroke-dasharray:34 30;'
                'stroke-linecap:round;fill:none;opacity:0.94;"'
            ),
        )
    )
    parts.append(
        line(
            line_x1,
            top_ai_y,
            line_x2,
            top_ai_y,
            "score1000-gap-line",
            extra=(
                f'data-score-gap-line="top-ai" data-score2000-value="{esc(top_ai_score_attr)}" '
                f'data-reader-label="{esc(overlay["top_ai_label"])}" '
                f'style="stroke:{top_ai_color};stroke-width:12;stroke-dasharray:34 30;'
                'stroke-linecap:round;fill:none;opacity:0.94;"'
            ),
        )
    )
    parts.append(
        rect(
            human_label_x - SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_MASK_W / 2.0,
            human_y - SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_MASK_H / 2.0,
            SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_MASK_W,
            SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_MASK_H,
            "#ffffff",
            "none",
            "score1000-gap-label-mask",
            rx=0,
            extra='data-score-gap-human-label-mask="true"',
        )
    )
    parts.append(
        rect(
            top_ai_label_x - SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_MASK_W / 2.0,
            top_ai_y - SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_MASK_H / 2.0,
            SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_MASK_W,
            SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_MASK_H,
            "#ffffff",
            "none",
            "score1000-gap-label-mask",
            rx=0,
            extra='data-score-gap-top-ai-label-mask="true"',
        )
    )
    parts.append(
        line(
            arrow_x,
            arrow_top_y,
            arrow_x,
            arrow_bottom_y,
            "score1000-gap-arrow",
            extra=f'data-score-gap-arrow="shaft" style="{arrow_shaft_style}"',
        )
    )
    for side in (-1.0, 1.0):
        parts.append(
            line(
                arrow_x,
                arrow_top_y,
                arrow_x + side * arrow_head_w,
                arrow_top_y + arrow_head_h,
                "score1000-gap-arrow",
                extra=f'data-score-gap-arrow="top-head" style="{arrow_head_style}"',
            )
        )
        parts.append(
            line(
                arrow_x,
                arrow_bottom_y,
                arrow_x + side * arrow_head_w,
                arrow_bottom_y - arrow_head_h,
                "score1000-gap-arrow",
                extra=f'data-score-gap-arrow="bottom-head" style="{arrow_head_style}"',
            )
        )
    parts.append(
        text(
            human_label_x,
            human_y + SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL_BASELINE_OFFSET,
            SCORE1000_BAR_GAP_OVERLAY_HUMAN_LABEL,
            "score1000-gap-band-label",
            "middle",
            extra='data-score-gap-human-label="true"',
        )
    )
    parts.append(
        text(
            top_ai_label_x,
            top_ai_y + SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL_BASELINE_OFFSET,
            SCORE1000_BAR_GAP_OVERLAY_TOP_AI_LABEL,
            "score1000-gap-band-label",
            "middle",
            extra='data-score-gap-top-ai-label="true"',
        )
    )
    parts.append(
        text(
            label_x,
            label_y,
            str(overlay["visible_label"]),
            "score1000-gap-value-label",
            "start",
            extra='data-score-gap-label="true"',
        )
    )
    parts.append("</g>")
    return "\n".join(parts)


def panel_5_score1000_bar_chart(
    rows: list[dict[str, str]],
    provenance: dict[str, object],
    *,
    variant_label: str = "5.0 clean confidence-weighted diagnosis vertical bar chart",
    selected_reader_labels: list[str] | None = None,
    text_colors: dict[str, str] | None = None,
    bar_colors: dict[str, str] | None = None,
    y_min: float = SCORE1000_BAR_Y_MIN,
    y_max: float = SCORE1000_BAR_Y_MAX,
    ticks: list[int] | None = None,
    emphasize_humans: bool = False,
    include_model_icons: bool = False,
    top_logo_scale: float = 1.0,
    bar_logo_scale: float = 1.0,
    chart_y: float = SCORE1000_BAR_CHART_Y,
    figure_title_x: float = W / 2,
    figure_title_y: float = FIGURE_TITLE_Y,
    figure_title_font_px: float | None = None,
    panel_title: str = SCORE1000_BAR_PANEL_TITLE,
    panel_title_cls: str = "title",
    panel_title_y: float = 332.0,
    panel_title_font_px: float | None = None,
    axis_title: str = SCORE1000_BAR_AXIS_TITLE,
    tick_label_font_px: float | None = None,
    bar_value_font_scale: float = 1.0,
    use_variant_footer: bool = False,
    show_footer: bool = True,
    footer_lines: list[str] | None = None,
    footer_cls: str = "variant-micro",
    footer_text_y: float = VARIANT_FOOTER_TEXT_Y,
    footer_line_step: float = VARIANT_FOOTER_LINE_STEP,
    footer_divider_y: float = VARIANT_FOOTER_DIVIDER_Y,
    footer_font_px: float | None = None,
    footer_x: float = 80.0,
    footer_right_x: float = 3520.0,
    footer_note: str | None = None,
    x_label_y_offset: float = 78.0,
    chart_h: float = SCORE1000_BAR_CHART_H,
    y_axis_left_shift: float = 0.0,
    x_label_font_px: float | None = None,
    x_label_line_step: float = SCORE1000_BAR_X_LABEL_LINE_STEP,
    logo_position: str = "inside_bar",
    bottom_logo_center_y: float | None = None,
    bar_logo_image_multipliers: dict[str, float] | None = None,
    bar_width: float = SCORE1000_BAR_W,
    axis_break_after: float | None = None,
    axis_break_style: str | None = None,
    axis_break_top_fraction: float = SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION,
    include_barcode_overlay: bool = False,
    barcode_units: int = SCORE1000_BAR_BARCODE_UNITS,
    barcode_capsule_w: float = SCORE1000_BAR_BARCODE_CAPSULE_W,
    barcode_capsule_h: float = SCORE1000_BAR_BARCODE_CAPSULE_H,
    barcode_capsule_gap: float = SCORE1000_BAR_BARCODE_CAPSULE_GAP,
    barcode_outcome_palette_key: str = SCORE1000_BAR_BARCODE_PALETTE,
    include_score_gap_overlay: bool = False,
    score_gap_date_label: str = SCORE1000_BAR_GAP_DATE_LABEL,
    svg_h: float | None = None,
) -> str:
    title = panel_title
    active_bar_colors = bar_colors or SCORE1000_BAR_COLORS
    active_reader_labels = selected_reader_labels or SCORE1000_BAR_READER_LABELS
    desc = (
        "Vertical bar chart of confidence-weighted diagnosis score for the selected human/model comparator set. "
        f"Higher is better; y-axis spans {y_min:g} to {y_max:g}."
    )
    selected_rows = score1000_bar_rows(rows, active_reader_labels)
    selected_labels = [row["reader_label"] for row in selected_rows]
    active_ticks = ticks or SCORE1000_BAR_TICKS
    active_logo_image_multipliers = bar_logo_image_multipliers or {}
    selected_reader_bindings = score1000_bar_reader_bindings(selected_labels, active_bar_colors)
    score_gap_overlay = (
        score1000_bar_gap_overlay_metadata(
            selected_rows,
            active_bar_colors,
            date_label=score_gap_date_label,
        )
        if include_score_gap_overlay
        else None
    )
    parts = svg_open(
        5,
        title,
        desc,
        selected_rows,
        provenance,
        variant=variant_label,
        outcome_palette_key="option_c_teal_green_to_current_red",
        category_colors=SHARED_IMAGE_CATEGORY_COLORS,
        text_colors=text_colors,
        extra_metadata={
                "score1000_bar_chart": {
                    "selected_reader_labels": selected_labels,
                    "selected_reader_set": active_reader_labels,
                    "selected_readers": selected_reader_bindings,
                    "logo_binding_key": "reader_label",
                    "display_score_column": "score2000",
                "baseline": SCORE2000_BASELINE,
                "bar_origin": y_min,
                "reference_line": SCORE2000_BASELINE,
                "score2000_rule": score2000_rule_metadata(),
                "y_min": y_min,
                "y_max": y_max,
                "ticks": active_ticks,
                "bar_colors": active_bar_colors,
                "emphasize_humans": emphasize_humans,
                "include_model_icons": include_model_icons,
                "top_logo_scale": top_logo_scale,
                "bar_logo_scale": bar_logo_scale,
                "bar_logo_image_multipliers": active_logo_image_multipliers,
                "chart_y": chart_y,
                "chart_h": chart_h,
                "y_axis_left_shift": y_axis_left_shift,
                "figure_title_x": figure_title_x,
                "figure_title_y": figure_title_y,
                "figure_title_font_px": figure_title_font_px,
                "panel_title_cls": panel_title_cls,
                "panel_title_y": panel_title_y,
                "panel_title_font_px": panel_title_font_px,
                "axis_title": axis_title,
                "tick_label_font_px": tick_label_font_px,
                "bar_value_font_scale": bar_value_font_scale,
                "x_label_font_px": x_label_font_px,
                "x_label_line_step": x_label_line_step,
                "use_variant_footer": use_variant_footer,
                "show_footer": show_footer,
                "octomed_logo_scale": SCORE1000_BAR_OCTOMED_LOGO_SCALE,
                "footer_lines": footer_lines,
                "footer_cls": footer_cls,
                "footer_text_y": footer_text_y,
                "footer_line_step": footer_line_step,
                "footer_divider_y": footer_divider_y,
                "footer_font_px": footer_font_px,
                "footer_x": footer_x,
                "footer_right_x": footer_right_x,
                "x_label_y_offset": x_label_y_offset,
                "logo_position": logo_position,
                "bottom_logo_center_y": bottom_logo_center_y,
                "bar_width": bar_width,
                "axis_break_after": axis_break_after,
                "axis_break_style": axis_break_style,
                "axis_break_top_fraction": axis_break_top_fraction,
                "include_barcode_overlay": include_barcode_overlay,
                "barcode_units": barcode_units,
                "barcode_capsule_w": barcode_capsule_w,
                "barcode_capsule_h": barcode_capsule_h,
                "barcode_capsule_gap": barcode_capsule_gap,
                "barcode_outcome_palette_key": barcode_outcome_palette_key,
                "barcode_bin_order_bottom_to_top": BIN_ORDER if include_barcode_overlay else None,
                "include_score_gap_overlay": include_score_gap_overlay,
                "score_gap_date_label": score_gap_date_label,
                "score_gap_overlay": score_gap_overlay,
                "svg_h": svg_h,
            }
            | (
                {
                    "bar_logos": score1000_bar_logo_metadata(),
                    "fallback_logo_badges": score1000_bar_fallback_badge_metadata(),
                }
                if include_model_icons
                else {}
            )
        },
        svg_h=svg_h,
    )
    add_top_logos(parts, scale=top_logo_scale)
    figure_title_extra = (
        f'style="font-size:{figure_title_font_px:.1f}px;"' if figure_title_font_px is not None else ""
    )
    panel_title_extra = (
        f'style="font-size:{panel_title_font_px:.1f}px;"' if panel_title_font_px is not None else ""
    )
    parts.append(text(figure_title_x, figure_title_y, FIGURE_TITLE, "figure-title", "middle", extra=figure_title_extra))
    parts.append(text(W / 2, panel_title_y, title, panel_title_cls, "middle", extra=panel_title_extra))

    chart_x = SCORE1000_BAR_CHART_X
    chart_w = SCORE1000_BAR_CHART_W
    axis_x = chart_x - y_axis_left_shift
    chart_bottom = chart_y + chart_h
    bar_origin_y = score1000_bar_scaled_y(
        y_min,
        y_min=y_min,
        y_max=y_max,
        chart_y=chart_y,
        chart_h=chart_h,
        axis_break_after=axis_break_after,
        axis_break_top_fraction=axis_break_top_fraction,
    )
    break_y = (
        score1000_bar_axis_break_y(chart_y, chart_h, axis_break_top_fraction)
        if axis_break_after is not None
        else None
    )
    barcode_colors = outcome_palette_colors(barcode_outcome_palette_key)

    for tick in active_ticks:
        y = score1000_bar_scaled_y(
            float(tick),
            y_min=y_min,
            y_max=y_max,
            chart_y=chart_y,
            chart_h=chart_h,
            axis_break_after=axis_break_after,
            axis_break_top_fraction=axis_break_top_fraction,
        )
        tick_extra = f'data-score1000-tick="{tick}"'
        if tick == SCORE2000_BASELINE:
            tick_extra += ' data-score1000-zero-line="true" data-score2000-baseline="true"'
        parts.append(line(axis_x, y, chart_x + chart_w, y, "score2000-grid", extra=tick_extra))
        parts.append(
            text(
                axis_x - SCORE1000_BAR_TICK_LABEL_X_OFFSET,
                y + 10,
                tick,
                "score1000-tick-label",
                "end",
                extra=(
                    f'style="font-size:{tick_label_font_px:.1f}px;" data-score1000-tick-label="{tick}"'
                    if tick_label_font_px is not None
                    else f'data-score1000-tick-label="{tick}"'
                ),
            )
        )
    if break_y is not None and axis_break_style == "a1_double_slash":
        parts.append(
            line(
                    axis_x,
                    chart_bottom,
                    axis_x,
                    break_y + SCORE1000_BAR_AXIS_BREAK_GAP,
                "axis",
                extra=(
                    'data-score1000-y-axis="true" data-score2000-axis-break-segment="lower" '
                    f'data-score2000-axis-break-after="{axis_break_after:g}"'
                ),
            )
        )
        parts.append(
            line(
                    axis_x,
                    break_y - SCORE1000_BAR_AXIS_BREAK_GAP,
                    axis_x,
                    chart_y,
                "axis",
                extra=(
                    'data-score1000-y-axis="true" data-score2000-axis-break-segment="upper" '
                    f'data-score2000-axis-break-after="{axis_break_after:g}"'
                ),
            )
        )
        for offset in (-13.0, 13.0):
            parts.append(
                line(
                    axis_x - 18.0,
                    break_y + offset + 15.0,
                    axis_x + 18.0,
                    break_y + offset - 15.0,
                    "score2000-axis-break-mark",
                    extra=(
                        f'data-score2000-axis-break-mark="true" data-score2000-axis-break-after="{axis_break_after:g}" '
                        f'style="stroke:#d97757;stroke-width:6;"'
                    ),
                )
            )
    else:
        parts.append(line(axis_x, chart_y, axis_x, chart_bottom, "axis", extra='data-score1000-y-axis="true"'))
    parts.append(line(axis_x, chart_bottom, chart_x + chart_w, chart_bottom, "axis", extra='data-score1000-bottom-axis="true"'))
    parts.append(
        f'<text class="score1000-axis-title" x="0" y="0" text-anchor="middle" '
        f'transform="translate({axis_x - SCORE1000_BAR_AXIS_TITLE_X_OFFSET:.1f} {chart_y + chart_h / 2:.1f}) rotate(-90)">{esc(axis_title)}</text>'
    )
    if score_gap_overlay is not None:
        parts.append(
            score1000_bar_gap_overlay_svg(
                score_gap_overlay,
                chart_x=chart_x,
                chart_w=chart_w,
                y_min=y_min,
                y_max=y_max,
                chart_y=chart_y,
                chart_h=chart_h,
                axis_break_after=axis_break_after,
                axis_break_top_fraction=axis_break_top_fraction,
            )
        )

    slot_w = chart_w / len(selected_rows)
    for idx, row in enumerate(selected_rows):
        label = row["reader_label"]
        reader_key = score1000_bar_reader_key(label)
        logo_asset = SCORE1000_BAR_LOGO_ASSETS.get(label)
        score = score2000_value(row)
        color = active_bar_colors[label]
        bar_x = chart_x + idx * slot_w + (slot_w - bar_width) / 2
        score_y = score1000_bar_scaled_y(
            score,
            y_min=y_min,
            y_max=y_max,
            chart_y=chart_y,
            chart_h=chart_h,
            axis_break_after=axis_break_after,
            axis_break_top_fraction=axis_break_top_fraction,
        )
        bar_y = score_y
        bar_h = max(0.0, bar_origin_y - score_y)
        center_x = bar_x + bar_width / 2
        is_human = row["reader_type"] == "Human comparator"
        if emphasize_humans and is_human:
            parts.append(
                rect(
                    bar_x - 18,
                    bar_y - 22,
                    bar_width + 36,
                    bar_h + 44,
                    "none",
                    color,
                    cls="score1000-human-emphasis",
                    rx=13,
                    extra=f'stroke-width="5" opacity="0.35" data-human-emphasis="{esc(label)}"',
                )
            )
        parts.append(
            rect(
                bar_x,
                bar_y,
                bar_width,
                bar_h,
                color,
                color,
                cls="score1000-bar",
                rx=8,
                extra=(
                    f'data-score1000-bar="true" data-reader-label="{esc(label)}" '
                    f'data-reader-key="{esc(reader_key)}" data-score2000-value="{score_label(row)}" '
                    f'data-score1000-value="{score_label(row)}"'
                    + (f' data-logo-source="{esc(rel(logo_asset))}"' if logo_asset else "")
                ),
            )
        )
        value_y = bar_y - 22
        if include_model_icons and is_human:
            value_y = bar_y - SCORE1000_BAR_HUMAN_SCORE_GAP
        value_fill = color
        if break_y is not None and value_y < chart_y + 10:
            value_y = bar_y + 42
            value_fill = "#ffffff"
        if include_barcode_overlay:
            overlay = score1000_bar_barcode_overlay(
                row,
                center_x=center_x,
                bar_y=bar_y,
                bar_bottom=chart_bottom,
                capsule_w=barcode_capsule_w,
                capsule_h=barcode_capsule_h,
                capsule_gap=barcode_capsule_gap,
                units=barcode_units,
                colors=barcode_colors,
            )
            if overlay:
                parts.append(overlay)
        if include_model_icons and (label in SCORE1000_BAR_LOGO_ASSETS or label in SCORE1000_BAR_FALLBACK_BADGES):
            icon_box = SCORE1000_BAR_LOGO_BOX * bar_logo_scale
            image_size = icon_box if is_human else SCORE1000_BAR_LOGO_IMAGE * bar_logo_scale
            if label == "octomed_7b":
                image_size *= SCORE1000_BAR_OCTOMED_LOGO_SCALE
            image_size *= active_logo_image_multipliers.get(label, 1.0)
            if logo_position == "bottom_under_labels":
                logo_center_y = bottom_logo_center_y or (chart_bottom + x_label_y_offset + 126.0)
                parts.append(
                    score1000_bar_logo_or_badge(
                        label=label,
                        reader_key=reader_key,
                        center_x=center_x,
                        center_y=logo_center_y,
                        icon_box=icon_box,
                        image_size=image_size,
                        color=color,
                        backplate=False,
                        cls_prefix="score1000-bottom",
                    )
                )
            elif is_human:
                icon_y = max(
                    SCORE1000_BAR_HUMAN_LOGO_Y,
                    value_y - SCORE1000_BAR_HUMAN_LOGO_GAP - image_size,
                )
                parts.append(
                    score1000_bar_logo_or_badge(
                        label=label,
                        reader_key=reader_key,
                        center_x=center_x,
                        center_y=icon_y + image_size / 2,
                        icon_box=icon_box,
                        image_size=image_size,
                        color=color,
                        backplate=False,
                    )
                )
            else:
                parts.append(
                    score1000_bar_logo_or_badge(
                        label=label,
                        reader_key=reader_key,
                        center_x=center_x,
                        center_y=bar_y + 30 + icon_box / 2,
                        icon_box=icon_box,
                        image_size=image_size,
                        color=color,
                        backplate=True,
                    )
                )
        if emphasize_humans and is_human:
            parts.append(
                rect(
                    center_x - 55,
                    value_y - 43,
                    110,
                    52,
                    PAPER,
                    color,
                    cls="score1000-human-value-marker",
                    rx=26,
                    extra=f'stroke-width="4" data-human-value-marker="{esc(label)}"',
                )
            )
        parts.append(
            text(
                center_x,
                value_y,
                score_label(row),
                "score1000-bar-value",
                "middle",
                extra=(
                    f'style="fill:{value_fill};font-size:{SCORE1000_BAR_VALUE_FONT_SIZE * bar_value_font_scale:.1f}px;" '
                    f'data-reader-label="{esc(label)}" data-reader-key="{esc(reader_key)}"'
                ),
            )
        )
        parts.append(
            multiline_text(
                center_x,
                chart_bottom + x_label_y_offset,
                SCORE1000_BAR_LABEL_LINES[label],
                "score1000-x-label",
                "middle",
                line_step=x_label_line_step,
                extra=(
                    f'data-score1000-x-label="{esc(label)}"'
                    + (
                        ' style="'
                        + (f"fill:{color};" if is_human else "")
                        + (f"font-size:{x_label_font_px:.1f}px;" if x_label_font_px is not None else "")
                        + '"'
                        if is_human or x_label_font_px is not None
                        else ""
                    )
                ),
            )
        )

    if show_footer:
        if use_variant_footer:
            parts.append(line(footer_x, footer_divider_y, footer_right_x, footer_divider_y, "axis"))
            active_footer_lines = footer_lines or wrap_balanced(FOOTER_SCORE1000_NOTE, VARIANT_FOOTER_WRAP_CHARS)
            for idx, line_text in enumerate(active_footer_lines):
                footer_extra = f'style="font-size:{footer_font_px:.1f}px;"' if footer_font_px is not None else ""
                parts.append(text(footer_x, footer_text_y + idx * footer_line_step, line_text, footer_cls, extra=footer_extra))
        else:
            parts.append(
                text(
                    W / 2,
                    2410,
                    footer_note
                    or f"Higher is better. Axis range shown: {y_min:g} to {y_max:g} Score2000; Score2000 = Score1000 + 1000.",
                    "variant-legend-label",
                    "middle",
                )
            )
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
    title = "Outcome composition per 100 cases"
    subtitle = "Each row rescales one reader group's or model's 200-case outcome counts to 100 marks, one mark per percentage point, apportioned by the largest-remainder method, ranked by Score2000. Score2000 and reader/model name appear at left; exact correct / neutral / incorrect counts (of 200) appear at right."
    parts = svg_open(3, title, subtitle, rows, provenance)
    add_header(parts, title, subtitle)
    unit_w, unit_h, gap = 11.0, 30.0, 13.6
    start_x, y0, row_step = 760, 450, 108
    score_x, name_x = 220, 690
    totals_x = 3500
    parts.append(text(score_x, 398, "Score2000", "axis-label", "end"))
    parts.append(text(name_x, 398, "Reader / model", "axis-label", "end"))
    parts.append(text(totals_x, 398, "correct / I don't know / wrong", "axis-label", "end"))
    for idx, row in enumerate(rows):
        y = y0 + idx * row_step
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


def add_legend(
    parts: list[str],
    y: float,
    x0: float,
    legend_w: float,
    panel_key: str,
    legend_label_cls: str = "legend-label",
    confidence_label_cls: str = "bar-label",
    colors: dict[str, str] | None = None,
) -> None:
    colors = colors or COLORS
    bar_h = 36.0
    segment_w = legend_w / len(BIN_ORDER)
    bar_y = y + 24
    correct_mid = x0 + segment_w * 2.5
    neutral_mid = x0 + segment_w * 5.5
    wrong_mid = x0 + segment_w * 8.5
    parts.append(text(correct_mid, y, "Correct, by confidence", legend_label_cls, "middle"))
    parts.append(text(neutral_mid, y, "I don't know", legend_label_cls, "middle"))
    parts.append(text(wrong_mid, y, "Wrong, by confidence", legend_label_cls, "middle"))
    for idx, key in enumerate(BIN_ORDER):
        parts.append(
            rect(
                x0 + idx * segment_w,
                bar_y,
                segment_w,
                bar_h,
                colors[key],
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
    parts.append(text(x0, left_y, "L4 high confidence", confidence_label_cls, "start"))
    parts.append(text(x0 + segment_w * 5, left_y, "L0 low confidence", confidence_label_cls, "end"))
    parts.append(text(x0 + segment_w * 6, left_y, "L0 low confidence", confidence_label_cls, "start"))
    parts.append(text(x0 + segment_w * 11, left_y, "L4 high confidence", confidence_label_cls, "end"))


def write_contact_sheet(out_dir: Path) -> None:
    cards: list[str] = []
    for filename in PANEL_FILES:
        svg = (out_dir / filename).read_text(encoding="utf-8")
        caption = (
            "Panel 2. Diagnostic outcomes stratified by confidence."
            if filename.startswith("panel_2")
            else "Panel 3. Outcome composition per 100 cases."
        )
        cards.append(f"<figure>{svg}<figcaption>{esc(caption)}</figcaption></figure>")
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>RadLE v2 Score1000 Panels 2 and 3</title>
<style>
{font_face_css()}
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


def write_variant_contact_sheet(out_dir: Path) -> None:
    cards: list[str] = []
    for filename in VARIANT_PANEL_FILES:
        svg = (out_dir / filename).read_text(encoding="utf-8")
        cards.append(f"<figure>{svg}<figcaption>{esc(VARIANT_FILE_SPECS[filename]['caption'])}</figcaption></figure>")
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>RadLE v2 Score1000 Panel 2 group-color final variants</title>
<style>
{font_face_css()}
body {{ margin: 0; padding: 28px; background: #efede7; font-family: {FONT}; color: {INK}; }}
h1 {{ font-size: 26px; margin: 0 0 18px 0; }}
figure {{ margin: 0 0 34px 0; background: white; padding: 12px; border: 1px solid #d7d0c5; }}
svg {{ width: 100%; height: auto; display: block; }}
figcaption {{ font-size: 15px; margin-top: 8px; color: {MUTED}; }}
</style>
</head>
<body>
<h1>RadLE v2 Score1000 Panel 2 group-color final variants</h1>
{''.join(cards)}
</body>
</html>
"""
    write_text(out_dir / "contact_sheet.html", html_doc)


def write_support_files(out_dir: Path, provenance: dict[str, object], rows: list[dict[str, str]]) -> None:
    score_rule = score1000_caption_rule(IDK_SCORE)
    captions = [
        "# Captions",
        "",
        "## Panel 2. Diagnostic outcomes stratified by confidence",
        f"Each row gives correct, neutral, and incorrect response counts out of 200 effective cases for the pooled Human Expert Baseline (12 readers, averaged) or one AI model (single evaluation run), ranked by Score2000. {score_rule}",
        "",
        "## Panel 3. Outcome composition per 100 cases",
        f"Each row rescales 200-case outcome counts to a 100-mark strip, one mark per percentage point, using deterministic largest-remainder apportionment; exact values are preserved in `score1000_panel23_bins.csv` and in SVG metadata, ranked by Score2000. {score_rule} Score2000 and reader/model name appear at left; exact correct / neutral / incorrect totals out of 200 appear at right. The Human Expert Baseline pools 12 readers; model rows are single evaluation runs.",
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
        "- Figure display scale: `Score2000 = Score1000 + 1000`, shifting `-1000..+1000` to `0..2000` without changing rank.",
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
                "score2000_rule": score2000_rule_metadata(),
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
        "- [ ] Visible row identity appears left of the bars as a right-aligned Score2000 value plus formatted reader/model name.",
        "- [ ] Visible model names are publication-formatted, with no raw lowercase underscore identifiers.",
        "- [ ] Human label reads `Human Expert Baseline`.",
        "- [ ] No Panel 4/5 files are present.",
    ]
    write_text(out_dir / "reviewer_checklist.md", "\n".join(checklist) + "\n")
    write_text(out_dir / "handwritten_panels_qa.txt", "Generated; structural audit and visual QA required after generation.\n")
    with (out_dir / "font_sizes.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["name", "selector", "surface", "size_px", "purpose"])
        writer.writerows(FONT_SIZE_ROWS)


def write_variant_support_files(out_dir: Path, provenance: dict[str, object]) -> None:
    score_rule = score1000_caption_rule(IDK_SCORE)
    captions = [
        "# Captions",
        "",
        "## Panel 2. Diagnostic outcomes stratified by confidence",
        f"Each row gives correct, neutral, and incorrect response counts out of 200 effective cases for the pooled Human Expert Baseline (12 readers, averaged) or one AI model (single evaluation run), ranked by Score2000. {score_rule}",
        "",
        "## Panel 5.0. Confidence-weighted diagnosis correctness",
        "A clean vertical bar chart shows confidence-weighted diagnosis scores for the pooled Human Expert Baseline, Claude Fable 5, Grok 4.3, Gemini 3.1 Pro, GPT-5.5, and OctoMed 7B. The y-axis uses the shifted 0..2000 display scale with an A1 kink after 1000; visible ticks are 0, 500, 1000, and 2000.",
        "",
        "## Panel 5.1. Confidence-weighted diagnosis correctness with icons",
        "An icon-enabled companion to Panel 5.0 keeps the same readers/models and shifted 0..2000 y-axis with an A1 kink after 1000 while refreshing the model bar colors to Claude #D97757, Grok #313131, Gemini #4796E3, GPT-5.5 #74AA9C, and OctoMed #F27B73; the Human Expert Baseline color stays unchanged. It uses the public confidence-weighted title and explanatory footer, moves the bar chart body down, scales header logos and reader/model icons, and enlarges the OctoMed icon image by 20%. The Human Expert Baseline uses the renamed human-expert icon.",
        "",
        "## Panel 5.5. Confidence-weighted diagnosis correctness with icons, refreshed palette checkpoint",
        "Panel 5.5 keeps the 5.1 icon geometry, footer, 0..2000 y-axis domain, and A1 kink after 1000, and serves as the checkpoint copy of the refreshed per-model bar palette: Claude #D97757, Grok #313131, Gemini #4796E3, GPT-5.5 #74AA9C, and OctoMed #F27B73; the Human Expert Baseline bar keeps the existing navy fill.",
        "",
        "## Panel 5.6. Open-access models vs 12 radiologists/trainees",
        "Panel 5.6 is a bottom-logo companion for the pooled Human Expert Baseline plus all open-access/open models from the current comparator CSV, including open medical models: OctoMed 7B, Nemotron 3 Omni, MiniMax M3, Gemma 4 31B, Lingshu 32B, MedGemma 1.5 4B, Llama 4 Maverick, InternVL 3.5 8B, and Mistral Large 3 2512. The y-axis uses the shifted 0..2000 display scale with an A1 kink after 1000. Bar colors use Palette A from `model_bar_color_contact_sheet.json`; all reader/model logos are bound from `scripts/assets/radle_score1000_logos`.",
        "",
        "## Panel 6.0. Models through MedGemma vs 12 radiologists/trainees",
        "Panel 6.0 shows the pooled Human Expert Baseline plus all ranked models through MedGemma, excluding Llama, InternVL, and Mistral. Bar fills use exact Palette A colors from `model_bar_color_contact_sheet.json`; fixed-size horizontal barcode capsules are centered inside each vertical bar with green outcomes at the bottom, neutral in the middle, and red outcomes at the top. The y-axis uses the A1 kink after 1000 and labels 0, 500, 1000, and 2000 directly, with no 1500 tick.",
        "",
        "## Panel 6.1. Proprietary Frontier Vision Language Models (VLMs) vs Human Expert Baseline",
        "Panel 6.1 shows the pooled Human Expert Baseline plus all proprietary frontier VLMs from the current comparator CSV: Claude Fable 5, Grok 4.3, Gemini 3.1 Pro, GPT-5.5, Qwen 3.7 Plus, and GLM-5V Turbo. The y-axis uses the shifted 0..2000 display scale with an A1 kink after 1000. Bar colors use Palette A from `model_bar_color_contact_sheet.json`; logos sit below the reader/model names.",
        "",
        "## Panel 6.1.1. Proprietary Frontier Vision Language Models (VLMs) vs Human Expert Baseline, gap overlay",
        "Panel 6.1.1 is a copy of Panel 6.1 with the dynamic Human-AI gap overlay added. The top AI line and label are selected from visible AI model rows, and the label remains inline on the dashed line using the same formula-driven placement as Panel 6.4.",
        "",
        "## Panel 6.2. Open-Weights Vision Language Models (VLMs) vs Human Expert Baseline",
        "Panel 6.2 shows the pooled Human Expert Baseline plus all open-weights VLMs from the current comparator CSV, including open medical models: OctoMed 7B, Nemotron 3 Omni, MiniMax M3, Gemma 4 31B, Lingshu 32B, MedGemma 1.5 4B, Llama 4 Maverick, InternVL 3.5 8B, and Mistral Large 3 2512. The y-axis uses the shifted 0..2000 display scale with an A1 kink after 1000. Bar colors use Palette A from `model_bar_color_contact_sheet.json`; all reader/model logos are bound from `scripts/assets/radle_score1000_logos`.",
        "",
        "## Panel 6.2.1. Open-Weights Vision Language Models (VLMs) vs Human Expert Baseline, gap overlay",
        "Panel 6.2.1 is a copy of Panel 6.2 with the dynamic Human-AI gap overlay added. The top AI line and label are selected from visible AI model rows, and the label remains inline on the dashed line using the same formula-driven placement as Panel 6.4.",
        "",
        "## Panel 6.3. Confidence-Weighted Diagnosis Scores: AI Models vs Human Expert Baseline",
        "Panel 6.3 shows the pooled Human Expert Baseline plus all evaluated AI models through MedGemma from the current comparator CSV: Claude Fable 5, Grok 4.3, Gemini 3.1 Pro, GPT-5.5, Qwen 3.7 Plus, GLM-5V Turbo, OctoMed 7B, Nemotron 3 Omni, MiniMax M3, Gemma 4 31B, Lingshu 32B, and MedGemma 1.5 4B. It excludes later rows after MedGemma: Llama 4 Maverick, InternVL 3.5 8B, and Mistral Large 3 2512. The y-axis uses the shifted 0..2000 display scale with an A1 kink after 1000. Bar colors and bottom logos use Palette A and locked logo assets from `model_bar_color_contact_sheet.json` and `scripts/assets/radle_score1000_logos`.",
        "",
        "## Panel 6.4. Frontier Vision Language Models (VLMs) vs Human Expert Baseline",
        "Panel 6.4 shows the pooled Human Expert Baseline plus all 15 evaluated frontier VLMs from the current comparator CSV: Claude Fable 5, Grok 4.3, Gemini 3.1 Pro, GPT-5.5, Qwen 3.7 Plus, GLM-5V Turbo, OctoMed 7B, Nemotron 3 Omni, MiniMax M3, Gemma 4 31B, Lingshu 32B, MedGemma 1.5 4B, Llama 4 Maverick, InternVL 3.5 8B, and Mistral Large 3 2512. The y-axis uses the shifted 0..2000 display scale with an A1 kink after 1000. Bar colors and bottom logos use Palette A and locked logo assets from `model_bar_color_contact_sheet.json` and `scripts/assets/radle_score1000_logos`.",
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
        "- Figure display scale: `Score2000 = Score1000 + 1000`, shifting `-1000..+1000` to `0..2000` without changing rank; vertical confidence-weighted diagnosis charts use an A1 broken y-axis after 1000 with visible ticks `[0, 500, 1000, 2000]`.",
        "- Variants: `2.1 revised` colors visible reader/model names while preserving rank order; `3.1 revised` groups rows by category.",
        "- New palette variants: `2.2` and `3.2` use Option A blue-to-current-red outcome colors; `2.3`, `3.3`, `2.4`, `3.4`, `2.5`, and `3.5` use Option C teal-green-to-current-red outcome colors.",
        "- The `2.2`, `3.2`, `2.3`, `3.3`, `2.4`, and `3.4` palette variants use balanced horizontal margins: the bar/axis/B3 legend frame is shortened to 2320 px and starts at x=1015, the score anchor moves to x=150, and the top category key shifts left by 75 px.",
        "- The `2.5` and `3.5` score-colored variants keep the score anchor at x=170, move the reader/model anchor to x=790, and expand the bar/axis/B3 legend frame left to x=935 with width 2400 px.",
        "- Variant `5.0` is a clean vertical confidence-weighted diagnosis chart using the pooled Human Expert Baseline, Claude Fable 5, Grok 4.3, Gemini 3.1 Pro, GPT-5.5, and OctoMed 7B, with y-axis domain fixed at 0 to 2000 and an A1 kink after 1000.",
        "- Variant `5.1` keeps the `5.0` chart data, uses the same 0 to 2000 shifted y-axis domain with an A1 kink after 1000, updates the model bar palette to Claude `#D97757`, Grok `#313131`, Gemini `#4796E3`, GPT-5.5 `#74AA9C`, and OctoMed `#F27B73`, keeps the Human Expert Baseline bar unchanged, uses the public confidence-weighted title and explanatory footer, moves the chart body down, and adds 1.5x larger header logos plus reader/model icons; the OctoMed icon image is enlarged by 20%. The Human Expert Baseline uses the renamed human-expert icon.",
        "- Variant `5.5` is the palette-refresh checkpoint copy of `5.1`, preserving the same icon layout, footer, 0 to 2000 domain, and A1 kink after 1000 while shipping the refreshed per-model bar colors.",
        "- Variant `5.6` is a bottom-logo open-model companion showing the pooled Human Expert Baseline plus all open-access/open models in the current comparator CSV, including the open medical models, with the same A1 axis kink.",
        "- Variant `6.0` shows the pooled Human Expert Baseline plus all ranked models through MedGemma, excludes Llama, InternVL, and Mistral, uses exact Palette A bar fills, places logos below the x-axis labels, and centers fixed-size horizontal barcode capsules inside each vertical bar.",
        "- Variants `5.0`, `5.1`, `5.4`, `5.5`, `5.6`, `6.0`, `6.1`, `6.1.1`, `6.2`, `6.2.1`, `6.3`, and `6.4` use A1 broken-axis ticks `[0, 500, 1000, 2000]`: after the visible kink above 1000, the next labeled tick is directly 2000, with no 1500 tick.",
        "- Variant `6.1` shows the pooled Human Expert Baseline plus all closed/API generalist models in the current comparator CSV with the same A1 axis kink.",
        "- Variant `6.1.1` is a copy of `6.1` with the dynamic Human-AI gap overlay.",
        "- Variant `6.2` shows the pooled Human Expert Baseline plus all open-access/open models in the current comparator CSV, including the open medical models, with the same A1 axis kink.",
        "- Variant `6.2.1` is a copy of `6.2` with the dynamic Human-AI gap overlay.",
        "- Variant `6.3` shows the pooled Human Expert Baseline plus all evaluated AI model rows through MedGemma, excluding Llama 4 Maverick, InternVL 3.5 8B, and Mistral Large 3 2512.",
        "- Variant `6.4` shows the pooled Human Expert Baseline plus all 15 evaluated AI model rows in the current comparator CSV.",
        "- Variants `5.6`, `6.0`, `6.1`, `6.1.1`, `6.2`, `6.2.1`, `6.3`, and `6.4` use Palette A from `model_bar_color_contact_sheet.json` for locked model colors and place logos below the x-axis reader/model names. Llama 4 Maverick, InternVL 3.5 8B, and Mistral Large 3 2512 use locked PNG assets from `scripts/assets/radle_score1000_logos` in 5.6, 6.2, 6.2.1, and 6.4.",
        "- Variants `2.3` and `3.3` use a custom category palette: Human Expert Baseline `#2f6f9f`, Closed generalist `#3f464c`, Open generalist `#c26a2e`, and Open medical `#bd3f70`.",
        "- Variants `2.4`, `3.4`, `2.5`, and `3.5` use the shared-image category palette: Human Expert Baseline `#131E35`, Closed generalist `#84848e`, Open generalist `#6f9cda`, and Open medical `#1B324D`; non-bar text uses `#131E35`, the figure title uses `#1B324D`, and text inside bars keeps the existing contrast colors.",
        "- Variants `2.5` and `3.5` additionally color the left score labels by the same category color as the corresponding reader/model name.",
        "- The `3.2`, `3.3`, `3.4`, and `3.5` grouped palette variants keep the grouped row order and group gaps, hide the left group headers/rules, and color reader/model names by category.",
        "- Header logos: `scripts/assets/radle_score1000_logos/kcdha_logo.svg` at top left and `scripts/assets/radle_score1000_logos/crash_lab_logo.png` at top right.",
    ]
    write_text(out_dir / "data_provenance.md", "\n".join(data_prov) + "\n")
    write_text(
        out_dir / "data_provenance.json",
        json.dumps(
            {
                **provenance,
                "generated_at": utc_now(),
                "panel_package": rel(out_dir),
                "panels": VARIANT_PANEL_FILES,
                "score2000_rule": score2000_rule_metadata(),
                "category_colors": CATEGORY_COLORS,
                "variant_category_colors": {
                    filename: variant_category_colors(spec) for filename, spec in VARIANT_FILE_SPECS.items()
                },
                "variant_text_colors": {
                    filename: variant_text_colors(spec)
                    for filename, spec in VARIANT_FILE_SPECS.items()
                    if variant_text_colors(spec) is not None
                },
                "outcome_palettes": {
                    key: outcome_palette_metadata(key)
                    for key in sorted({str(spec["palette_key"]) for spec in VARIANT_FILE_SPECS.values()})
                },
                "logos": variant_logo_metadata(),
                "score1000_bar_chart": {
                    "selected_reader_labels": SCORE1000_BAR_READER_LABELS,
                    "display_score_column": "score2000",
                    "baseline": SCORE2000_BASELINE,
                    "score2000_rule": score2000_rule_metadata(),
                    "y_min": SCORE1000_BAR_Y_MIN,
                    "y_max": SCORE1000_BAR_Y_MAX,
                    "ticks": SCORE1000_BAR_TICKS,
                    "bar_colors": SCORE1000_BAR_COLORS,
                    "default_bar_colors": SCORE1000_BAR_COLORS,
                    "variant_bar_colors": {
                        filename: variant_bar_colors(spec)
                        for filename, spec in VARIANT_FILE_SPECS.items()
                        if spec["layout"] == "score1000_bar_chart"
                    },
                    "bar_logo_assets": score1000_bar_logo_metadata(),
                    "fallback_logo_badges": score1000_bar_fallback_badge_metadata(),
                    "bar_logo_box_px": SCORE1000_BAR_LOGO_BOX,
                    "bar_logo_image_px": SCORE1000_BAR_LOGO_IMAGE,
                    "human_logo_min_y": SCORE1000_BAR_HUMAN_LOGO_Y,
                    "human_score_gap_px": SCORE1000_BAR_HUMAN_SCORE_GAP,
                    "human_logo_gap_px": SCORE1000_BAR_HUMAN_LOGO_GAP,
                },
                "mode": "model-group-color-final",
            },
            indent=2,
        )
        + "\n",
    )
    checklist = [
        "# Reviewer Checklist",
        "",
        "- [ ] Variant 2.1 preserves Score2000 rank order.",
        "- [ ] Variant 3.1 groups rows by category and preserves rank order within each category.",
        "- [ ] Variant 2.2 preserves rank order and uses Option A blue-to-current-red outcome colors with balanced horizontal margins and no gray neutral segment.",
        "- [ ] Variant 3.2 preserves grouped row order/gaps, hides left group headers/rules, colors row names, and uses Option A blue-to-current-red outcome colors with balanced horizontal margins and no gray neutral segment.",
        "- [ ] Variant 2.3 preserves rank order and uses Option C teal-green-to-current-red outcome colors with balanced horizontal margins and no gray neutral segment.",
        "- [ ] Variant 3.3 preserves grouped row order/gaps, hides left group headers/rules, colors row names, and uses Option C teal-green-to-current-red outcome colors with balanced horizontal margins and no gray neutral segment.",
        "- [ ] Variant 2.4 preserves rank order, keeps 2.3 geometry/data, uses the shared-image category palette, and applies the dark-blue text theme outside the bars.",
        "- [ ] Variant 3.4 preserves grouped row order/gaps, keeps 3.3 geometry/data, uses the shared-image category palette, and applies the dark-blue text theme outside the bars.",
        "- [ ] Variant 2.5 preserves 2.4 geometry/data and colors each left score label with the corresponding reader/model category color.",
        "- [ ] Variant 3.5 preserves 3.4 geometry/data and colors each left score label with the corresponding reader/model category color.",
        "- [ ] Variant 5.0 shows only the pooled Human Expert Baseline plus Claude Fable 5, Grok 4.3, Gemini 3.1 Pro, GPT-5.5, and OctoMed 7B.",
        "- [ ] Variant 5.0 uses Score2000 on the y-axis with a fixed 0 to 2000 domain and A1 kink after 1000; the shifted Score1000 zero is retained as Score2000 1000 reference metadata.",
        "- [ ] Variant 5.0 remains a clean no-model-icon chart for this first pass.",
        "- [ ] Variant 5.1 keeps the same data as 5.0 while using the fixed 0 to 2000 Score2000 y-axis domain, A1 kink after 1000, and the refreshed model bar palette.",
        "- [ ] Variant 5.1 uses 1.5x larger top logos and 1.5x larger reader/model icons without overlapping the title, bars, labels, or footer.",
        "- [ ] Variant 5.1 places the Human Expert Baseline stack in this order: positive bar, score label, clear gap, unboxed Human Expert Baseline icon.",
        "- [ ] Variant 5.5 matches the 5.1 icon geometry and footer while carrying the same refreshed model bar palette as a checkpoint copy.",
        "- [ ] Variant 5.6 shows one Human Expert Baseline row/bar plus nine open-access/open model bars, including OctoMed, Lingshu, and MedGemma as open medical models.",
        "- [ ] Variant 6.0 shows one Human Expert Baseline bar plus all model bars through MedGemma, excluding Llama, InternVL, and Mistral.",
        "- [ ] Variants 5.0, 5.1, 5.4, 5.5, 5.6, 6.0, 6.1, 6.1.1, 6.2, 6.2.1, 6.3, and 6.4 use the A1 tick grammar: 0, 500, 1000, then 2000 after the kink, with no 1500 label.",
        "- [ ] Variant 6.0 barcode capsules are centered inside each bar, keep fixed width/height/gap, leave the Palette A bar fill visible, and run green at the bottom through neutral to red at the top.",
        "- [ ] Variant 6.1 shows one Human Expert Baseline row/bar plus six closed/API generalist model bars.",
        "- [ ] Variant 6.1.1 matches Variant 6.1 and adds the dynamic Human-AI gap overlay.",
        "- [ ] Variant 6.2 shows one Human Expert Baseline row/bar plus nine open-access/open model bars, including OctoMed, Lingshu, and MedGemma as open medical models.",
        "- [ ] Variant 6.2.1 matches Variant 6.2 and adds the dynamic Human-AI gap overlay.",
        "- [ ] Variant 6.3 shows one Human Expert Baseline row/bar plus all evaluated AI model bars through MedGemma, excluding Llama, InternVL, and Mistral.",
        "- [ ] Variant 6.4 shows one Human Expert Baseline row/bar plus all 15 evaluated AI model bars.",
        "- [ ] Variants 5.6, 6.0, 6.1, 6.1.1, 6.2, 6.2.1, 6.3, and 6.4 use Palette A colors from `model_bar_color_contact_sheet.json` and bind every logo by `reader_label`.",
        "- [ ] Category color appears only on reader/model names, visible 3.1 group headers, and the category key.",
        "- [ ] Outcome bars and B3 legend retain the unchanged Score1000 bin order, data, and single-line legend grammar while displayed ranking uses Score2000.",
        "- [ ] The `Score` / `Reader / model` header area has comfortable vertical spacing.",
        "- [ ] Subtitle, score labels, reader/model names, bar text, legend labels, and footer text use the accessible variant font scale.",
        "- [ ] Variant bars are taller than the production Panel 2 bars while preserving the same row data and x-axis scale.",
        "- [ ] Top-left and top-right logos flank `Radiology's Last Exam 2.0` without overlapping title or panel text.",
        "- [ ] No black human-comparator marker is present.",
    ]
    write_text(out_dir / "reviewer_checklist.md", "\n".join(checklist) + "\n")
    write_text(out_dir / "handwritten_panels_qa.txt", "Generated; structural audit and visual QA required after generation.\n")
    with (out_dir / "font_sizes.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["name", "selector", "surface", "size_px", "purpose"])
        writer.writerows([*FONT_SIZE_ROWS, *VARIANT_FONT_SIZE_ROWS])


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
        "score2000_rule": score2000_rule_metadata(),
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


def write_variant_manifest(out_dir: Path, provenance: dict[str, object]) -> dict[str, object]:
    files = [
        "score1000_panel23_bins.csv",
        "score1000_likert_direction_provenance.json",
        *VARIANT_PANEL_FILES,
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
        "mode": "model-group-color-final",
        "source_master_sha256": provenance["source_master_sha256"],
        "score1000_scored_rows_sha256": provenance["score1000_scored_rows"]["sha256"],
        "score2000_rule": score2000_rule_metadata(),
        "logo_assets": variant_logo_metadata(),
        "outcome_palettes": {
            key: outcome_palette_metadata(key)
            for key in sorted({str(spec["palette_key"]) for spec in VARIANT_FILE_SPECS.values()})
        },
        "panels": [
            {
                "panel_id": spec["panel_id"],
                "file": filename,
                "variant": spec["variant"],
                "layout": spec["layout"],
                "palette_key": spec["palette_key"],
                "category_colors": variant_category_colors(spec),
                **({"text_colors": variant_text_colors(spec)} if variant_text_colors(spec) is not None else {}),
                **({"color_scores": True} if spec.get("color_scores") else {}),
                **(
                    {
                        "selected_reader_labels": spec["selected_reader_labels"],
                        "bar_colors": variant_bar_colors(spec),
                        "score_y_min": spec["score_y_min"],
                        "score_y_max": spec["score_y_max"],
                        "score_ticks": spec.get("score_ticks", SCORE1000_BAR_TICKS),
                        "score_bar_width": float(spec.get("score_bar_width", SCORE1000_BAR_W)),
                        "score_axis_break_after": spec.get("score_axis_break_after"),
                        "score_axis_break_style": spec.get("score_axis_break_style"),
                        "score_axis_break_top_fraction": float(
                            spec.get("score_axis_break_top_fraction", SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION)
                        ),
                        "include_barcode_overlay": bool(spec.get("include_barcode_overlay", False)),
                        "barcode_units": int(spec.get("barcode_units", SCORE1000_BAR_BARCODE_UNITS)),
                        "barcode_capsule_w": float(
                            spec.get("barcode_capsule_w", SCORE1000_BAR_BARCODE_CAPSULE_W)
                        ),
                        "barcode_capsule_h": float(
                            spec.get("barcode_capsule_h", SCORE1000_BAR_BARCODE_CAPSULE_H)
                        ),
                        "barcode_capsule_gap": float(
                            spec.get("barcode_capsule_gap", SCORE1000_BAR_BARCODE_CAPSULE_GAP)
                        ),
                        "barcode_outcome_palette_key": spec.get(
                            "barcode_outcome_palette_key", SCORE1000_BAR_BARCODE_PALETTE
                        ),
                        "include_model_icons": bool(spec.get("include_model_icons", False)),
                        "include_score_gap_overlay": bool(spec.get("include_score_gap_overlay", False)),
                        "score_gap_date_label": spec.get("score_gap_date_label"),
                        "top_logo_scale": float(spec.get("top_logo_scale", 1.0)),
                        "bar_logo_scale": float(spec.get("bar_logo_scale", 1.0)),
                        "bar_logo_image_multipliers": spec.get("bar_logo_image_multipliers", {}),
                        "score_chart_y": float(spec.get("score_chart_y", SCORE1000_BAR_CHART_Y)),
                        "score_chart_h": float(spec.get("score_chart_h", SCORE1000_BAR_CHART_H)),
                        "y_axis_left_shift": float(spec.get("y_axis_left_shift", 0.0)),
                        "figure_title_x": float(spec.get("figure_title_x", W / 2)),
                        "figure_title_y": float(spec.get("figure_title_y", FIGURE_TITLE_Y)),
                        "panel_title": spec.get("panel_title", SCORE1000_BAR_PANEL_TITLE),
                        "panel_title_cls": spec.get("panel_title_cls", "title"),
                        "panel_title_y": float(spec.get("panel_title_y", 332.0)),
                        "axis_title": spec.get("axis_title", SCORE1000_BAR_AXIS_TITLE),
                        "bar_value_font_scale": float(spec.get("bar_value_font_scale", 1.0)),
                        "use_variant_footer": bool(spec.get("use_variant_footer", False)),
                        "show_footer": bool(spec.get("show_footer", True)),
                        "footer_cls": spec.get("footer_cls", "variant-micro"),
                        "logo_position": spec.get("logo_position", "inside_bar"),
                        **(
                            {"bottom_logo_center_y": float(spec["bottom_logo_center_y"])}
                            if "bottom_logo_center_y" in spec
                            else {}
                        ),
                    }
                    if spec["layout"] == "score1000_bar_chart"
                    else {}
                ),
            }
            for filename, spec in VARIANT_FILE_SPECS.items()
        ],
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
        *[name.replace(".svg", ".png") for name in PANEL_FILES],
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


def clean_stale_variant_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    allowed = {
        "score1000_panel23_bins.csv",
        "score1000_likert_direction_provenance.json",
        *VARIANT_PANEL_FILES,
        *[name.replace(".svg", ".png") for name in VARIANT_PANEL_FILES],
        "contact_sheet.html",
        "contact_sheet.png",
        "captions.md",
        "figure_manifest.json",
        "data_provenance.json",
        "data_provenance.md",
        "reviewer_checklist.md",
        "font_sizes.csv",
        "handwritten_panels_qa.txt",
        "score1000_panel2_group_color_audit_report.json",
        "score1000_panel2_group_color_audit_report.md",
    }
    for path in out_dir.iterdir():
        if path.is_file() and path.name not in allowed:
            path.unlink()
    for path in out_dir.glob("panel_*.svg"):
        if path.name not in VARIANT_PANEL_FILES:
            path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["production", "model-group-color-final"], default="production")
    parser.add_argument("--score-root", type=Path, default=DEFAULT_SCORE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--source-panel-dir", type=Path, default=None)
    parser.add_argument("--idk-score", type=int, choices=[0, 1], default=1)
    return parser.parse_args()


def main_variant(args: argparse.Namespace) -> None:
    source_panel_dir = (args.source_panel_dir or DEFAULT_OUT_DIR).resolve()
    out_dir = (args.out_dir if args.out_dir != DEFAULT_OUT_DIR else DEFAULT_VARIANT_OUT_DIR).resolve()
    clean_stale_variant_outputs(out_dir)

    source_csv = source_panel_dir / "score1000_panel23_bins.csv"
    source_provenance = source_panel_dir / "score1000_likert_direction_provenance.json"
    rows = read_csv(source_csv)
    provenance = json.loads(source_provenance.read_text(encoding="utf-8"))
    if str(provenance["source_master_sha256"]).upper() != EXPECTED_SOURCE_SHA256:
        raise ValueError("Unexpected source master SHA in panel provenance")

    shutil.copyfile(source_csv, out_dir / "score1000_panel23_bins.csv")
    shutil.copyfile(source_provenance, out_dir / "score1000_likert_direction_provenance.json")
    for filename in VARIANT_PANEL_FILES:
        spec = VARIANT_FILE_SPECS[filename]
        category_colors = variant_category_colors(spec)
        text_colors = variant_text_colors(spec)
        bar_colors = variant_bar_colors(spec)
        if spec["layout"] == "colored_names":
            svg = panel_2_variant_colored_names(
                rows,
                provenance,
                variant_label=str(spec["variant"]),
                palette_key=str(spec["palette_key"]),
                chart_x=float(spec.get("chart_x", VARIANT_CHART_X)),
                chart_w=float(spec.get("chart_w", VARIANT_CHART_W)),
                score_x=float(spec.get("score_x", VARIANT_SCORE_X)),
                name_x=float(spec.get("name_x", VARIANT_NAME_X)),
                category_key_shift_x=float(spec.get("category_key_shift_x", 0)),
                category_colors=category_colors,
                text_colors=text_colors,
                color_scores=bool(spec.get("color_scores", False)),
            )
        elif spec["layout"] == "grouped_bands":
            svg = panel_2_variant_grouped_bands(
                rows,
                provenance,
                variant_label=str(spec["variant"]),
                palette_key=str(spec["palette_key"]),
                show_group_headers=bool(spec.get("show_group_headers", True)),
                color_row_names=bool(spec.get("color_row_names", False)),
                chart_x=float(spec.get("chart_x", VARIANT_CHART_X)),
                chart_w=float(spec.get("chart_w", VARIANT_CHART_W)),
                score_x=float(spec.get("score_x", VARIANT_SCORE_X)),
                name_x=float(spec.get("name_x", VARIANT_NAME_X)),
                category_key_shift_x=float(spec.get("category_key_shift_x", 0)),
                category_colors=category_colors,
                text_colors=text_colors,
                color_scores=bool(spec.get("color_scores", False)),
            )
        elif spec["layout"] == "score1000_bar_chart":
            svg = panel_5_score1000_bar_chart(
                rows,
                provenance,
                variant_label=str(spec["variant"]),
                selected_reader_labels=list(spec.get("selected_reader_labels", SCORE1000_BAR_READER_LABELS)),  # type: ignore[arg-type]
                text_colors=text_colors,
                bar_colors=bar_colors,
                y_min=float(spec.get("score_y_min", SCORE1000_BAR_Y_MIN)),
                y_max=float(spec.get("score_y_max", SCORE1000_BAR_Y_MAX)),
                ticks=list(spec.get("score_ticks", SCORE1000_BAR_TICKS)),  # type: ignore[arg-type]
                include_model_icons=bool(spec.get("include_model_icons", False)),
                top_logo_scale=float(spec.get("top_logo_scale", 1.0)),
                bar_logo_scale=float(spec.get("bar_logo_scale", 1.0)),
                bar_logo_image_multipliers=dict(spec.get("bar_logo_image_multipliers", {})),
                chart_y=float(spec.get("score_chart_y", SCORE1000_BAR_CHART_Y)),
                chart_h=float(spec.get("score_chart_h", SCORE1000_BAR_CHART_H)),
                y_axis_left_shift=float(spec.get("y_axis_left_shift", 0.0)),
                figure_title_x=float(spec.get("figure_title_x", W / 2)),
                figure_title_y=float(spec.get("figure_title_y", FIGURE_TITLE_Y)),
                figure_title_font_px=float(spec["figure_title_font_px"]) if "figure_title_font_px" in spec else None,
                panel_title=str(spec.get("panel_title", SCORE1000_BAR_PANEL_TITLE)),
                panel_title_cls=str(spec.get("panel_title_cls", "title")),
                panel_title_y=float(spec.get("panel_title_y", 332.0)),
                panel_title_font_px=float(spec["panel_title_font_px"]) if "panel_title_font_px" in spec else None,
                axis_title=str(spec.get("axis_title", SCORE1000_BAR_AXIS_TITLE)),
                tick_label_font_px=float(spec["tick_label_font_px"]) if "tick_label_font_px" in spec else None,
                bar_value_font_scale=float(spec.get("bar_value_font_scale", 1.0)),
                use_variant_footer=bool(spec.get("use_variant_footer", False)),
                show_footer=bool(spec.get("show_footer", True)),
                footer_lines=list(spec.get("footer_lines", [])) or None,  # type: ignore[arg-type]
                footer_cls=str(spec.get("footer_cls", "variant-micro")),
                footer_text_y=float(spec.get("footer_text_y", VARIANT_FOOTER_TEXT_Y)),
                footer_line_step=float(spec.get("footer_line_step", VARIANT_FOOTER_LINE_STEP)),
                footer_divider_y=float(spec.get("footer_divider_y", VARIANT_FOOTER_DIVIDER_Y)),
                footer_font_px=float(spec["footer_font_px"]) if "footer_font_px" in spec else None,
                footer_x=float(spec.get("footer_x", 80.0)),
                footer_right_x=float(spec.get("footer_right_x", 3520.0)),
                x_label_y_offset=float(spec.get("x_label_y_offset", 78.0)),
                x_label_font_px=float(spec["x_label_font_px"]) if "x_label_font_px" in spec else None,
                x_label_line_step=float(spec.get("x_label_line_step", SCORE1000_BAR_X_LABEL_LINE_STEP)),
                logo_position=str(spec.get("logo_position", "inside_bar")),
                bottom_logo_center_y=(
                    float(spec["bottom_logo_center_y"]) if "bottom_logo_center_y" in spec else None
                ),
                bar_width=float(spec.get("score_bar_width", SCORE1000_BAR_W)),
                axis_break_after=(
                    float(spec["score_axis_break_after"]) if "score_axis_break_after" in spec else None
                ),
                axis_break_style=str(spec["score_axis_break_style"]) if "score_axis_break_style" in spec else None,
                axis_break_top_fraction=float(
                    spec.get("score_axis_break_top_fraction", SCORE1000_BAR_AXIS_BREAK_TOP_FRACTION)
                ),
                include_barcode_overlay=bool(spec.get("include_barcode_overlay", False)),
                barcode_units=int(spec.get("barcode_units", SCORE1000_BAR_BARCODE_UNITS)),
                barcode_capsule_w=float(spec.get("barcode_capsule_w", SCORE1000_BAR_BARCODE_CAPSULE_W)),
                barcode_capsule_h=float(spec.get("barcode_capsule_h", SCORE1000_BAR_BARCODE_CAPSULE_H)),
                barcode_capsule_gap=float(spec.get("barcode_capsule_gap", SCORE1000_BAR_BARCODE_CAPSULE_GAP)),
                barcode_outcome_palette_key=str(
                    spec.get("barcode_outcome_palette_key", SCORE1000_BAR_BARCODE_PALETTE)
                ),
                include_score_gap_overlay=bool(spec.get("include_score_gap_overlay", False)),
                score_gap_date_label=str(spec.get("score_gap_date_label", SCORE1000_BAR_GAP_DATE_LABEL)),
                svg_h=float(spec["svg_h"]) if "svg_h" in spec else None,
                footer_note=str(
                    spec.get(
                        "footer_note",
                        "Higher is better. Axis range shown: 0 to 2000 Score2000; Score2000 = Score1000 + 1000.",
                    )
                ),
            )
        else:
            raise ValueError(f"Unsupported variant layout: {spec['layout']}")
        write_text(out_dir / filename, svg)
    write_variant_support_files(out_dir, provenance)
    write_variant_contact_sheet(out_dir)
    write_variant_manifest(out_dir, provenance)
    print(f"[PASS] generated Score1000 Panel 2 group-color variants {out_dir}")


def main() -> None:
    args = parse_args()
    configure_idk_score(args.idk_score)
    if args.mode == "model-group-color-final":
        main_variant(args)
        return
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
