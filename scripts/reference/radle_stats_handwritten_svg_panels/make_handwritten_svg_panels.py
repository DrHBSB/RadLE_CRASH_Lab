from __future__ import annotations

import csv
import hashlib
import html
import itertools
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
RAW_OUTPUTS_DIR = REPO_ROOT / "outputs" / "Raw Outputs"
RESULTS_CSV = RAW_OUTPUTS_DIR / "results_table.csv"
LONG_FORMAT_CSV = RAW_OUTPUTS_DIR / "long_format.csv"
FONT_SIZE_CSV = SCRIPT_DIR / "font_sizes.csv"

W, H = 3600, 2700
FONT = "Inter, Helvetica Neue, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, Menlo, Consolas, monospace"

FONT_SIZE_FIELDS = ["key", "css_selector", "scope", "size_px", "description", "example_where_to_look"]
DEFAULT_FONT_SIZE_ROWS = [
    {"key": "title", "css_selector": ".title", "scope": "svg_panel", "size_px": "88", "description": "", "example_where_to_look": ""},
    {"key": "subtitle", "css_selector": ".subtitle", "scope": "svg_panel", "size_px": "72", "description": "", "example_where_to_look": ""},
    {"key": "section", "css_selector": ".section", "scope": "svg_panel", "size_px": "60", "description": "", "example_where_to_look": ""},
    {"key": "small", "css_selector": ".small", "scope": "svg_panel", "size_px": "46", "description": "", "example_where_to_look": ""},
    {"key": "micro", "css_selector": ".micro", "scope": "svg_panel", "size_px": "36", "description": "", "example_where_to_look": ""},
    {"key": "micro-alert", "css_selector": ".micro-alert", "scope": "svg_panel", "size_px": "36", "description": "", "example_where_to_look": ""},
    {"key": "header", "css_selector": ".header", "scope": "svg_panel", "size_px": "54", "description": "", "example_where_to_look": ""},
    {"key": "axis-label", "css_selector": ".axis-label", "scope": "svg_panel", "size_px": "58", "description": "", "example_where_to_look": ""},
    {"key": "row-label", "css_selector": ".row-label", "scope": "svg_panel", "size_px": "54", "description": "", "example_where_to_look": ""},
    {"key": "row-metric", "css_selector": ".row-metric", "scope": "svg_panel", "size_px": "48", "description": "", "example_where_to_look": ""},
    {"key": "row-metric-muted", "css_selector": ".row-metric-muted", "scope": "svg_panel", "size_px": "48", "description": "", "example_where_to_look": ""},
    {"key": "bar-label", "css_selector": ".bar-label", "scope": "svg_panel", "size_px": "57", "description": "", "example_where_to_look": ""},
    {"key": "bar-label-white", "css_selector": ".bar-label-white", "scope": "svg_panel", "size_px": "57", "description": "", "example_where_to_look": ""},
    {"key": "legend-label", "css_selector": ".legend-label", "scope": "svg_panel", "size_px": "54", "description": "", "example_where_to_look": ""},
    {"key": "footer-title", "css_selector": ".footer-title", "scope": "svg_panel", "size_px": "48", "description": "", "example_where_to_look": ""},
    {"key": "caption", "css_selector": ".caption", "scope": "svg_panel", "size_px": "42", "description": "", "example_where_to_look": ""},
    {"key": "p1-header", "css_selector": ".p1-header", "scope": "svg_panel", "size_px": "50", "description": "", "example_where_to_look": ""},
    {"key": "p1-axis-label", "css_selector": ".p1-axis-label", "scope": "svg_panel", "size_px": "58", "description": "", "example_where_to_look": ""},
    {"key": "p1-value", "css_selector": ".p1-value", "scope": "svg_panel", "size_px": "81", "description": "", "example_where_to_look": ""},
    {"key": "p1-footer-title", "css_selector": ".p1-footer-title", "scope": "svg_panel", "size_px": "52", "description": "", "example_where_to_look": ""},
    {"key": "p1-caption", "css_selector": ".p1-caption", "scope": "svg_panel", "size_px": "46", "description": "", "example_where_to_look": ""},
    {"key": "contact_h1", "css_selector": "h1", "scope": "contact_sheet", "size_px": "30", "description": "", "example_where_to_look": ""},
    {"key": "contact_figcaption", "css_selector": "figcaption", "scope": "contact_sheet", "size_px": "18", "description": "", "example_where_to_look": ""},
]
DEFAULT_FONT_SIZES = {row["key"]: float(row["size_px"]) for row in DEFAULT_FONT_SIZE_ROWS}


def write_default_font_size_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FONT_SIZE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(DEFAULT_FONT_SIZE_ROWS)


def ensure_font_size_csv() -> Path:
    if not FONT_SIZE_CSV.exists():
        write_default_font_size_csv(FONT_SIZE_CSV)
        return FONT_SIZE_CSV

    with FONT_SIZE_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        existing = {str(row.get("key", "")).strip(): row for row in reader if str(row.get("key", "")).strip()}

    sanitized_rows = []
    for default_row in DEFAULT_FONT_SIZE_ROWS:
        key = default_row["key"]
        row = dict(default_row)
        if key in existing and str(existing[key].get("size_px", "")).strip():
            row["size_px"] = str(existing[key]["size_px"]).strip()
        sanitized_rows.append(row)

    with FONT_SIZE_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FONT_SIZE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sanitized_rows)
    return FONT_SIZE_CSV


def load_font_sizes() -> dict[str, float]:
    path = ensure_font_size_csv()
    values = dict(DEFAULT_FONT_SIZES)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{path} is empty; expected columns: {', '.join(FONT_SIZE_FIELDS)}")
        required = {"key", "size_px"}
        missing = required.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"{path} is missing required column(s): {', '.join(sorted(missing))}")
        for line_number, row in enumerate(reader, start=2):
            key = str(row.get("key", "")).strip()
            if not key:
                continue
            if key not in DEFAULT_FONT_SIZES:
                raise ValueError(f"{path}:{line_number} has unknown font key {key!r}")
            raw_size = str(row.get("size_px", "")).strip()
            try:
                size = float(raw_size)
            except ValueError as exc:
                raise ValueError(f"{path}:{line_number} has non-numeric size_px {raw_size!r}") from exc
            if not 6 <= size <= 240:
                raise ValueError(f"{path}:{line_number} size_px must be between 6 and 240, got {size:g}")
            values[key] = size
    return values


FONT_SIZES = load_font_sizes()


def font_size(key: str) -> float:
    return FONT_SIZES[key]


def css_px(key: str) -> str:
    size = font_size(key)
    return f"{size:g}px"


def line_height_for(key: str, ratio: float) -> float:
    return font_size(key) * ratio


def title_max_width() -> float:
    return W - 160


def subtitle_max_width() -> float:
    return min(W - 180, max(2400, W - 700))


def footer_copy_max_width() -> float:
    return W - 680


def title_to_subtitle_gap() -> float:
    # Give subtitle enough room below title cap-height (≈0.72 × size)
    return max(90, font_size("title") * 0.30)


def header_to_body_gap() -> float:
    return max(300, font_size("subtitle") * 3.0)


# Pin chart top to a constant floor so chart bottom (and bottom-aligned
# elements like legends, axis tick row, footer) line up across panels
# regardless of how many lines the title or subtitle wrapped to.
# Set high enough to absorb the longest panel's header (Panel 3: 2-line title +
# 3-line subtitle).
Y0_FLOOR = 900


ROW_LABEL_DY = 24
ROW_MICRO_DY = 82
ROW_METRIC_DY = 24
BAR_LABEL_DY = 44


def header_baseline(axis_y: float, font_key: str = "header") -> float:
    return axis_y - max(44, font_size(font_key) * 1.15)

# # --- Colors Palette (Minimalist Pastel: Soft Fills & Delicate Edges) ---
# C_CAPABILITY_FILL = "#D9E1F2"
# C_CAPABILITY_EDGE = "#1F77B4"

# C_SAFE_VERIFIED_FILL = "#D9E1F2"
# C_SAFE_VERIFIED_EDGE = "#005B96"

# C_RISK_HIGH_FILL = "#FCE4D6"
# C_RISK_HIGH_EDGE = "#D62728"
# C_HAZARD_FILL = "#FCE4D6"
# C_HAZARD_EDGE = "#D62728"

# C_RISK_SAFE_FILL = "#E2EFDA"
# C_RISK_SAFE_EDGE = "#2CA02C"
# C_JUSTIFIED_FILL = "#E2EFDA"
# C_JUSTIFIED_EDGE = "#2CA02C"

# # --- The Fog of Uncertainty (Corrected to neutral receding grays/whites) ---
# C_CAUTIOUS_FILL = "#CFD8DC"
# C_CAUTIOUS_EDGE = "#FFFFFF"
# C_SAFE_UNCERTAIN_FILL = "#CFD8DC"
# C_SAFE_UNCERTAIN_EDGE = "#FFFFFF"

# C_ABSTAIN_FILL = "#FAFAFA"
# C_ABSTAIN_EDGE = "#78909C"

# C_FLAT_NOISE_FILL = "#F8F9FA"
# C_FLAT_NOISE_EDGE = "#9E9E9E"

# --- Colors Palette (Hybrid: Bold Core & Soft Uncertainty) ---

# Core Data: Absolute certainty needs visual weight (Solid, bold fills)
C_CAPABILITY_FILL = "#1F77B4"  # Strong Blue
C_CAPABILITY_EDGE = "#1F77B4"

C_SAFE_VERIFIED_FILL = "#005B96" # Deep Blue
C_SAFE_VERIFIED_EDGE = "#005B96"

C_RISK_HIGH_FILL = "#D62728"   # Strong Red (Demands attention for hazards)
C_RISK_HIGH_EDGE = "#D62728"
C_HAZARD_FILL = "#D62728"
C_HAZARD_EDGE = "#D62728"

C_RISK_SAFE_FILL = "#2CA02C"   # Strong Green (Clear signal for safe/correct)
C_RISK_SAFE_EDGE = "#2CA02C"
C_JUSTIFIED_FILL = "#2CA02C"
C_JUSTIFIED_EDGE = "#2CA02C"

# --- The Fog of Uncertainty (Soft, receding colors to drop into the background) ---
C_CAUTIOUS_FILL = "#CFD8DC"    # Soft blue-gray (Perfect for uncertainty)
C_CAUTIOUS_EDGE = "#CFD8DC"    # Keep edges same as fill to avoid clutter
C_SAFE_UNCERTAIN_FILL = "#CFD8DC"
C_SAFE_UNCERTAIN_EDGE = "#CFD8DC"

C_ABSTAIN_FILL = "#FAFAFA"     # Off-white
C_ABSTAIN_EDGE = "#B0BEC5"     # Slightly darker gray edge to define the boundary against the background

C_FLAT_NOISE_FILL = "#F8F9FA"
C_FLAT_NOISE_EDGE = "#9E9E9E"

C_LINES_TEXT = "#333333"
LINE_WIDTH = 0.25

TEXT = C_LINES_TEXT
MUTED = C_LINES_TEXT
MICRO_TEXT = C_LINES_TEXT
CANVAS = C_ABSTAIN_FILL
SURFACE = C_ABSTAIN_FILL
BORDER = C_ABSTAIN_EDGE
GRID = C_CAUTIOUS_FILL
AXIS = C_LINES_TEXT

CARD = SURFACE
CAPABILITY = C_CAPABILITY_FILL
CAPABILITY_DARK = C_CAPABILITY_EDGE
CORRECT = C_RISK_SAFE_FILL
CORRECT_DARK = C_RISK_SAFE_EDGE
HAZARD = C_HAZARD_FILL
HAZARD_DARK = C_HAZARD_EDGE
SHIELD_BLUE = C_SAFE_VERIFIED_FILL
SHIELD_BLUE_DARK = C_SAFE_VERIFIED_EDGE
TRUST_GREEN = C_JUSTIFIED_FILL
TRUST_GREEN_DARK = C_JUSTIFIED_EDGE
CAUTIOUS = C_CAUTIOUS_FILL
CAUTIOUS_DARK = C_CAUTIOUS_EDGE
SAFE_UNCERTAIN = C_SAFE_UNCERTAIN_FILL
SAFE_UNCERTAIN_DARK = C_SAFE_UNCERTAIN_EDGE
ABSTAIN = C_ABSTAIN_FILL
ABSTAIN_DARK = C_ABSTAIN_EDGE
OTHER = ABSTAIN
FLAT_NOISE = C_FLAT_NOISE_FILL
FLAT_NOISE_DARK = C_FLAT_NOISE_EDGE

PANEL_IDENTITY = {
    1: {
        "key": "capability",
        "primary": CAPABILITY,
        "primary_dark": CAPABILITY_DARK,
        "highlight": SURFACE,
        "wash": SURFACE,
        "border": BORDER,
        "row_even": SURFACE,
        "row_highlight": SURFACE,
        "row_stroke": BORDER,
        "side_metric": "",
    },
    2: {
        "key": "risk",
        "primary": HAZARD,
        "primary_dark": HAZARD_DARK,
        "highlight": SURFACE,
        "wash": SURFACE,
        "border": BORDER,
        "row_even": SURFACE,
        "row_highlight": SURFACE,
        "row_stroke": BORDER,
        "side_metric": "",
    },
    3: {
        "key": "calibration",
        "primary": FLAT_NOISE,
        "primary_dark": FLAT_NOISE_DARK,
        "highlight": SURFACE,
        "wash": SURFACE,
        "border": BORDER,
        "row_even": SURFACE,
        "row_highlight": SURFACE,
        "row_stroke": BORDER,
        "side_metric": "",
    },
    4: {
        "key": "shield",
        "primary": SHIELD_BLUE,
        "primary_dark": SHIELD_BLUE_DARK,
        "highlight": SURFACE,
        "wash": SURFACE,
        "border": BORDER,
        "row_even": SURFACE,
        "row_highlight": SURFACE,
        "row_stroke": BORDER,
        "side_metric": "",
    },
    5: {
        "key": "trust",
        "primary": TRUST_GREEN,
        "primary_dark": TRUST_GREEN_DARK,
        "highlight": SURFACE,
        "wash": SURFACE,
        "border": BORDER,
        "row_even": SURFACE,
        "row_highlight": SURFACE,
        "row_stroke": BORDER,
        "side_metric": "",
    },
    6: {
        "key": "net",
        "primary": SHIELD_BLUE,
        "primary_dark": SHIELD_BLUE_DARK,
        "highlight": SURFACE,
        "wash": SURFACE,
        "border": BORDER,
        "row_even": SURFACE,
        "row_highlight": SURFACE,
        "row_stroke": BORDER,
        "side_metric": "",
    },
}

OUT_FILES = {
    1: "panel_1_handwritten_accuracy.svg",
    2: "panel_2_handwritten_confidence_outcomes.svg",
    3: "panel_3_handwritten_calibration.svg",
    4: "panel_4_handwritten_safety_shield.svg",
    5: "panel_5_handwritten_peak_certainty_ppv.svg",
    6: "panel_6_handwritten_confidence_volume.svg",
}

PANEL_TEXT = {
    1: {
        "title": "The Capability Baseline: Overall Diagnostic Accuracy",
        "subtitle": (
            "Evaluating raw competence: How often does the model provide the correct diagnosis "
            "across all 200 challenging cases, regardless of its confidence level?"
        ),
        "xlabel": "Overall Accuracy (%)",
        "footer": "Note: Abstentions or deferred cases are treated as diagnostic failures.",
    },
    2: {
        "title": "Deployment Risk: Clinical Outcomes by Confidence Level",
        "subtitle": (
            "Mapping the hazard across 200 cases: By grouping answers on a 4-point Likert scale, we separate clinically cautious "
            "responses (Likert ≤ 3) from peak-confidence hallucinations (Likert 4) that could mislead a clinician."
        ),
        "xlabel": "Number of Cases",
        "footer": "",
    },
    3: {
        "title": "The Calibration Trend: Trajectories of Monotonicity (\"Self-Awareness\")",
        "subtitle": (
            "A calibrated model is most accurate when it claims peak confidence (green). "
            "'Non-self-aware' models stay flat and noisy regardless (grey). Dangerously "
            "uncalibrated models drop in accuracy at peak confidence (red)."
        ),
        "xlabel": "Accuracy by Confidence Level (%)",
        "footer": "",
    },
    4: {
        "title": "The Clinical Safety Shield: Protected vs. Unprotected Cases",
        "subtitle": (
            "Evaluating clinical harm: A patient is protected when the model is either definitively correct (blue) or expresses "
            "safe uncertainty (grey) to defer the case to a physician. Unprotected cases are peak-confidence hallucinations "
            "that create a misleading hazard (red)."
        ),
        "xlabel": "Number of Cases",
        "footer": "",
    },
    5: {
        "title": "Positive Predictive Value (PPV) at AI's Claimed Peak Certainty",
        "subtitle": (
            "Evaluating clinical utility and overconfidence by excluding cautious or deferred cases. "
            "When a model claims absolute certainty, what is the probability its diagnosis is correct?"
        ),
        "xlabel": "Proportion of Peak Confidence Answers (%)",
        "footer": "",
    },
    6: {
        "title": "Confidence Volume: Diagnostic Yield vs. Hallucination Volume",
        "subtitle": (
            "Total bar length is the model's \"Confidence Volume\". "
            "This exposes the trade-off between diagnostic yield (right, correct) and hallucination volume (left, misleading)."
        ),
        "xlabel": "Number of Cases",
        "footer": "Analysis isolates absolute certainty by excluding cautious or deferred cases (Likert ≤ 3).",
    },
}

RESULT_REQUIRED = {
    "Model",
    "n_correct",
    "n_total",
    "Primary_Accuracy",
    "Abstention_Rate",
    "Mean_Likert",
    "n_very_high_conf",
    "n_very_high_conf_wrong",
    "Very_High_Conf_Error_Rate",
    "Spearman_rho",
}

RESULT_NUMERIC = [
    "n_correct",
    "n_total",
    "Primary_Accuracy",
    "Abstention_Rate",
    "Mean_Likert",
    "n_very_high_conf",
    "n_very_high_conf_wrong",
    "Very_High_Conf_Error_Rate",
    "Spearman_rho",
]


def is_missing(value: object) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def parse_float(value: object) -> float:
    if value is None:
        return math.nan
    value = str(value).strip()
    if value == "":
        return math.nan
    try:
        return float(value)
    except ValueError:
        return math.nan


def required_float(value: object, column: str, model: str) -> float:
    parsed = parse_float(value)
    if is_missing(parsed):
        raise ValueError(f"{model}: {column} is missing or non-numeric")
    return parsed


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fmt_pct(value: float, digits: int = 1) -> str:
    if is_missing(value):
        return "NA"
    return f"{float(value) * 100:.{digits}f}%"


def fmt_pct_plain(value: float, digits: int = 1) -> str:
    if is_missing(value):
        return "NA"
    return f"{float(value):.{digits}f}%"


def nfmt(value: float | int) -> str:
    if is_missing(value):
        return "NA"
    return str(int(round(float(value))))


def mean_score(items: list[dict[str, float]]) -> float:
    scores = [item["score"] for item in items if not is_missing(item["score"])]
    if not scores:
        return math.nan
    return sum(scores) / len(scores) * 100


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def css_sanity_errors(css_text: str) -> list[str]:
    errors: list[str] = []
    depth = 0
    for pos, char in enumerate(css_text):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        if depth < 0:
            errors.append(f"CSS closes more braces than it opens near character {pos}")
            break
    if depth != 0:
        errors.append("CSS has unbalanced braces")

    allowed_keywords = {"normal", "bold", "bolder", "lighter", "inherit", "initial", "unset"}
    for raw_weight in re.findall(r"font-weight\s*:\s*([^;}{]+)", css_text):
        weight = raw_weight.strip().lower()
        if weight in allowed_keywords:
            continue
        if not weight.isdigit():
            errors.append(f"CSS font-weight is not numeric or keyword: {raw_weight.strip()}")
            continue
        numeric_weight = int(weight)
        if numeric_weight < 100 or numeric_weight > 900 or numeric_weight % 100 != 0:
            errors.append(f"CSS font-weight should use 100-step values from 100 to 900: {numeric_weight}")
    return errors


def load_results() -> list[dict[str, object]]:
    rows = read_csv_dicts(RESULTS_CSV)
    if not rows:
        raise ValueError(f"Results CSV is empty: {RESULTS_CSV}")
    missing = sorted(RESULT_REQUIRED - set(rows[0]))
    if missing:
        raise ValueError(f"Results CSV is missing required columns: {missing}")

    parsed: list[dict[str, object]] = []
    for raw in rows:
        model = raw["Model"]
        row: dict[str, object] = {"Model": model}
        for column in RESULT_NUMERIC:
            row[column] = required_float(raw.get(column), column, model)
        row["n_correct"] = int(round(float(row["n_correct"])))
        row["n_total"] = int(round(float(row["n_total"])))
        row["n_very_high_conf"] = int(round(float(row["n_very_high_conf"])))
        row["n_very_high_conf_wrong"] = int(round(float(row["n_very_high_conf_wrong"])))
        expected_acc = row["n_correct"] / row["n_total"]
        if abs(float(row["Primary_Accuracy"]) - expected_acc) > 0.0005:
            raise ValueError(f"{model}: Primary_Accuracy does not match n_correct / n_total")
        if row["n_very_high_conf"]:
            expected_vhc_error = row["n_very_high_conf_wrong"] / row["n_very_high_conf"]
            if abs(float(row["Very_High_Conf_Error_Rate"]) - expected_vhc_error) > 0.0005:
                raise ValueError(f"{model}: Very_High_Conf_Error_Rate does not match Likert-4 wrong / Likert-4 n")
        parsed.append(row)
    return parsed


def merge_long_format(results: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[str]]:
    raw_long = read_csv_dicts(LONG_FORMAT_CSV)
    if not raw_long:
        raise ValueError(f"Long-format CSV is empty: {LONG_FORMAT_CSV}")
    required = {"Model_Name", "Class", "Likert_Raw", "Score"}
    missing = sorted(required - set(raw_long[0]))
    if missing:
        raise ValueError(f"Long-format CSV is missing required columns: {missing}")

    by_model: dict[str, list[dict[str, object]]] = {}
    for raw in raw_long:
        by_model.setdefault(raw["Model_Name"], []).append(
            {
                "class": raw["Class"],
                "likert": parse_float(raw.get("Likert_Raw")),
                "score": parse_float(raw.get("Score")),
            }
        )

    qa_notes = [f"Long-format source: {LONG_FORMAT_CSV}"]
    merged: list[dict[str, object]] = []
    for row in results:
        model = str(row["Model"])
        items = by_model.get(model, [])
        if not items:
            raise ValueError(f"No long-format rows found for {model}")

        valid_answered = [item for item in items if item["class"] == "answered_valid"]
        l4 = [item for item in valid_answered if item["likert"] == 4]
        cautious = [item for item in valid_answered if not is_missing(item["likert"]) and 1 <= item["likert"] <= 3]
        low = [item for item in valid_answered if not is_missing(item["likert"]) and item["likert"] <= 2]
        mid = [item for item in valid_answered if item["likert"] == 3]
        abstain = [item for item in items if item["class"] == "abstention"]
        l4_wrong = [item for item in l4 if item["score"] == 0]
        l4_correct = [item for item in l4 if item["score"] == 1]
        n_correct_long = int(round(sum(item["score"] for item in items if not is_missing(item["score"]))))
        n_total_long = len(items)

        if n_total_long != row["n_total"]:
            raise ValueError(f"{model}: long-format n={n_total_long} does not match results n={row['n_total']}")
        if n_correct_long != row["n_correct"]:
            raise ValueError(f"{model}: long-format correct={n_correct_long} does not match results correct={row['n_correct']}")
        if len(l4) != row["n_very_high_conf"]:
            raise ValueError(f"{model}: long-format Likert-4 n={len(l4)} does not match results table")
        if len(l4_wrong) != row["n_very_high_conf_wrong"]:
            raise ValueError(f"{model}: long-format Likert-4 wrong={len(l4_wrong)} does not match results table")

        shown = len(cautious) + len(l4) + len(abstain)
        other = max(0, n_total_long - shown)
        derived = dict(row)
        derived.update(
            {
                "low_acc": mean_score(low),
                "mid_acc": mean_score(mid),
                "peak_acc": mean_score(l4),
                "cautious_n": len(cautious),
                "abstain_n": len(abstain),
                "other_n": other,
                "deferred_n": len(abstain) + other,
                "peak_correct_n": len(l4_correct),
                "peak_wrong_n": len(l4_wrong),
                "ppv_correct": (len(l4_correct) / len(l4) * 100) if l4 else math.nan,
                "ppv_wrong": (len(l4_wrong) / len(l4) * 100) if l4 else math.nan,
                "vhc_burden_pct": len(l4_wrong) / n_total_long,
                "protected_n": len(l4_correct) + len(cautious) + len(abstain) + other,
                "small_l4_n": len(l4) < 30,
            }
        )
        merged.append(derived)

    qa_notes.append(f"Long-format cross-check: all {len(merged)} model rows matched results_table.csv.")
    return merged, qa_notes


def nice_count_axis(max_count: float, step: int = 40) -> tuple[int, list[int]]:
    max_count = max(0, float(max_count))
    scale_max = max(step, int(math.ceil(max_count / step) * step))
    return scale_max, list(range(0, scale_max + 1, step))


def nice_pct_axis(max_pct: float = 100) -> tuple[int, list[int]]:
    max_pct = max(40, int(math.ceil(max_pct / 20) * 20))
    return max_pct, list(range(0, max_pct + 1, 20))


def text(x: float, y: float, value: object, cls: str = "", anchor: str = "start", extra: str = "") -> str:
    attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'text-anchor="{anchor}"']
    if cls:
        attrs.append(f'class="{cls}"')
    if extra:
        attrs.append(extra)
    return "<text " + " ".join(attrs) + f">{esc(value)}</text>"


BOLD_KEYS = {
    "title", "section", "micro-alert", "header", "legend-label",
    "row-label", "bar-label", "bar-label-white", "footer-title",
    "p1-header", "p1-value", "p1-footer-title",
}
# Empirical: rendered Inter/DejaVu Bold is ~1.28x the regular-weight estimate.
BOLD_WIDTH_FACTOR = 1.28


def estimate_text_width(value: str, size_px: float, *, bold: bool = False) -> float:
    width = 0.0
    narrow = set(".,:;!|'`ilIjrtf[]()")
    wide = set("MWmw@%&#")
    for char in value:
        if char.isspace():
            factor = 0.32
        elif char in wide:
            factor = 0.82
        elif char in narrow:
            factor = 0.30
        elif char.isupper():
            factor = 0.62
        elif char.isdigit():
            factor = 0.56
        else:
            factor = 0.52
        width += factor * size_px
    if bold:
        width *= BOLD_WIDTH_FACTOR
    return width


def text_width_for(value: str, font_key: str) -> float:
    """Layout-aware width: looks up boldness from font_key automatically."""
    return estimate_text_width(value, font_size(font_key), bold=font_key in BOLD_KEYS)


def inside_bar_label_fits(value: object, width: float, font_key: str = "bar-label-white") -> bool:
    padding = max(10, font_size(font_key) * 0.25)
    return width >= text_width_for(str(value), font_key) + padding * 2


def clipped_bar_label(label_x: float, chart_x: float, chart_right: float) -> tuple[float, str]:
    """Adjust label x position if it falls outside chart bounds. Returns (adjusted_x, anchor)."""
    if label_x < chart_x - 20:
        return chart_x + 14, "start"
    elif label_x > chart_right + 20:
        return chart_right - 14, "end"
    else:
        return label_x, "start" if label_x < (chart_x + chart_right) / 2 else "end"


def wrap_text_to_width(value: str, font_key: str, max_width_px: float, max_lines: int | None = None) -> list[str]:
    words = value.split()
    if not words:
        return [""]

    size_px = font_size(font_key)
    bold = font_key in BOLD_KEYS
    whole = " ".join(words)
    if estimate_text_width(whole, size_px, bold=bold) <= max_width_px:
        return [whole]

    n = len(words)
    max_line_count = min(max_lines or n, n)
    bad_endings = {"a", "an", "and", "at", "by", "for", "in", "of", "or", "the", "to", "vs", "vs."}
    best: tuple[float, list[str]] | None = None

    for line_count in range(2, max_line_count + 1):
        # Prevent combinatorial explosion for long text inputs
        if math.comb(n - 1, line_count - 1) > 2000:
            continue
        for breaks in itertools.combinations(range(1, n), line_count - 1):
            starts = (0,) + breaks
            stops = breaks + (n,)
            lines = [" ".join(words[start:stop]) for start, stop in zip(starts, stops)]
            widths = [estimate_text_width(line_value, size_px, bold=bold) for line_value in lines]
            if any(width > max_width_px for width in widths):
                continue

            raggedness = (max(widths) - min(widths)) / max_width_px
            score = (line_count - 1) * 0.35 + raggedness * raggedness * 3.0
            if len(lines[-1].split()) == 1:
                score += 8.0
            if widths[-1] < max_width_px * 0.30:
                score += 2.0
            for line_value in lines[:-1]:
                ending = line_value.split()[-1].lower().rstrip(",;:")
                if ending in bad_endings:
                    score += 1.5
            if best is None or score < best[0]:
                best = (score, lines)

    if best is not None:
        return best[1]

    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if current and estimate_text_width(candidate, size_px, bold=bold) > max_width_px:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
    return lines


def multiline_text_from_lines(
    x: float,
    y: float,
    lines: list[str],
    cls: str,
    line_h: float,
    anchor: str = "start",
) -> tuple[str, float]:
    attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'text-anchor="{anchor}"', f'class="{cls}"']
    parts = ["<text " + " ".join(attrs) + ">"]
    for i, line_value in enumerate(lines or [""]):
        dy = 0 if i == 0 else line_h
        parts.append(f'<tspan x="{x:.1f}" dy="{dy:.1f}">{esc(line_value)}</tspan>')
    parts.append("</text>")
    return "\n".join(parts), y + (len(lines or [""]) - 1) * line_h


def multiline_text_to_width(
    x: float,
    y: float,
    value: str,
    cls: str,
    font_key: str,
    max_width_px: float,
    line_h: float,
    max_lines: int | None = None,
    anchor: str = "start",
) -> tuple[str, float]:
    lines = wrap_text_to_width(value, font_key, max_width_px, max_lines=max_lines)
    return multiline_text_from_lines(x, y, lines, cls, line_h, anchor)


def multiline_text_verbatim(
    x: float,
    y: float,
    value: str,
    cls: str,
    line_h: float,
    anchor: str = "start",
) -> str:
    block, _ = multiline_text_from_lines(x, y, value.splitlines(), cls, line_h, anchor)
    return block


def rect(
    x: float,
    y: float,
    w: float,
    h: float,
    cls: str = "",
    fill: str | None = None,
    stroke: str | None = None,
    rx: float = 0,
    extra: str = "",
) -> str:
    attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'width="{max(0, w):.1f}"', f'height="{max(0, h):.1f}"']
    if rx:
        attrs.append(f'rx="{rx:.1f}"')
        attrs.append(f'ry="{rx:.1f}"')
    if cls:
        attrs.append(f'class="{cls}"')
    if fill:
        attrs.append(f'fill="{fill}"')
    if stroke:
        attrs.append(f'stroke="{stroke}"')
    if extra:
        attrs.append(extra)
    return "<rect " + " ".join(attrs) + "/>"


def line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    cls: str = "",
    stroke: str | None = None,
    sw: float | None = None,
    extra: str = "",
) -> str:
    attrs = [f'x1="{x1:.1f}"', f'y1="{y1:.1f}"', f'x2="{x2:.1f}"', f'y2="{y2:.1f}"']
    if cls:
        attrs.append(f'class="{cls}"')
    if stroke:
        attrs.append(f'stroke="{stroke}"')
    if sw is not None:
        attrs.append(f'stroke-width="{sw:.1f}"')
    if extra:
        attrs.append(extra)
    return "<line " + " ".join(attrs) + "/>"


def circle(cx: float, cy: float, r: float, cls: str = "", fill: str | None = None, stroke: str | None = None, sw: float = 1.2) -> str:
    attrs = [f'cx="{cx:.1f}"', f'cy="{cy:.1f}"', f'r="{r:.1f}"']
    if cls:
        attrs.append(f'class="{cls}"')
    if fill:
        attrs.append(f'fill="{fill}"')
    if stroke:
        attrs.append(f'stroke="{stroke}"')
        attrs.append(f'stroke-width="{sw:.1f}"')
    return "<circle " + " ".join(attrs) + "/>"


def polygon(points: list[tuple[float, float]], cls: str = "", fill: str | None = None, stroke: str | None = None) -> str:
    point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    attrs = [f'points="{point_text}"']
    if cls:
        attrs.append(f'class="{cls}"')
    if fill:
        attrs.append(f'fill="{fill}"')
    if stroke:
        attrs.append(f'stroke="{stroke}"')
    return "<polygon " + " ".join(attrs) + "/>"


OUTCOME_EDGES = {
    CORRECT: CORRECT_DARK,
    HAZARD: HAZARD_DARK,
    CAUTIOUS: CAUTIOUS_DARK,
    ABSTAIN: ABSTAIN_DARK,
    SAFE_UNCERTAIN: SAFE_UNCERTAIN_DARK,
    FLAT_NOISE: FLAT_NOISE_DARK,
    SHIELD_BLUE: SHIELD_BLUE_DARK,
}


def outcome_fill(color: str) -> str:
    if color == HAZARD:
        return "url(#hazard-stripe)"
    if color == ABSTAIN:
        return "url(#abstain-hatch)"
    return color


def outcome_stroke(color: str) -> str:
    return OUTCOME_EDGES.get(color, color)


def bar_edge_extra() -> str:
    return f'stroke-width="{LINE_WIDTH:g}"'


CSS = f"""
    svg {{ background: {CANVAS}; }}
    text {{ font-family: {FONT}; fill: {TEXT}; }}
    .title {{ font-size: {css_px("title")}; font-weight: 700; }}
    .subtitle {{ font-size: {css_px("subtitle")}; fill: {MUTED}; }}
    .section {{ font-size: {css_px("section")}; font-weight: 700; }}
    .small {{ font-size: {css_px("small")}; fill: {MUTED}; }}
    .micro {{ font-size: {css_px("micro")}; fill: {MICRO_TEXT}; }}
    .micro-alert {{ font-size: {css_px("micro-alert")}; fill: {HAZARD_DARK}; font-weight: 700; }}
    .header {{ font-size: {css_px("header")}; fill: {MUTED}; font-weight: 700; }}
    .legend-label {{ font-size: {css_px("legend-label")}; fill: {MICRO_TEXT}; font-weight: 700; }}
    .axis-label {{ font-size: {css_px("axis-label")}; fill: {MUTED}; font-family: {MONO}; }}
    .row-label {{ font-size: {css_px("row-label")}; font-weight: 700; }}
    .row-metric {{ font-size: {css_px("row-metric")}; font-family: {MONO}; fill: {TEXT}; }}
    .row-metric-muted {{ font-size: {css_px("row-metric-muted")}; font-family: {MONO}; fill: {MUTED}; }}
    .bar-label {{ font-size: {css_px("bar-label")}; font-family: {MONO}; font-weight: 700; fill: {TEXT}; }}
    .bar-label-white {{ font-size: {css_px("bar-label-white")}; font-family: {MONO}; font-weight: 700; fill: #FFFFFF; }}
    .footer-title {{ font-size: {css_px("footer-title")}; font-weight: 700; }}
    .caption {{ font-size: {css_px("caption")}; fill: {MUTED}; }}
    .p1-header {{ font-size: {css_px("p1-header")}; fill: {MUTED}; font-weight: 700; }}
    .p1-axis-label {{ font-size: {css_px("p1-axis-label")}; fill: {MUTED}; font-family: {MONO}; }}
    .p1-value {{ font-size: {css_px("p1-value")}; font-family: {MONO}; font-weight: 700; fill: {TEXT}; }}
    .p1-footer-title {{ font-size: {css_px("p1-footer-title")}; font-weight: 700; }}
    .p1-caption {{ font-size: {css_px("p1-caption")}; fill: {MUTED}; }}
    .plot-line {{ stroke-width: 4.4; fill: none; stroke-linecap: round; }}
"""


def svg_open(title_value: str, desc_value: str, panel_id: int) -> list[str]:
    css_errors = css_sanity_errors(CSS)
    if css_errors:
        raise ValueError("Embedded CSS sanity check failed:\n- " + "\n- ".join(css_errors))
    style = PANEL_IDENTITY[panel_id]
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{esc(title_value)}</title>',
        f'<desc id="desc">{esc(desc_value)}</desc>',
        "<defs>",
        f"<style><![CDATA[{CSS}]]></style>",
        f'<pattern id="hazard-stripe" patternUnits="userSpaceOnUse" width="20" height="20" patternTransform="rotate(45)">',
        f'<rect width="20" height="20" fill="{HAZARD}"/>',
        f'<line x1="0" y1="0" x2="0" y2="20" stroke="{HAZARD_DARK}" stroke-width="5" opacity="0.22"/>',
        "</pattern>",
        f'<pattern id="abstain-hatch" patternUnits="userSpaceOnUse" width="18" height="18" patternTransform="rotate(45)">',
        f'<rect width="18" height="18" fill="{ABSTAIN}"/>',
        f'<line x1="0" y1="0" x2="0" y2="18" stroke="{ABSTAIN_DARK}" stroke-width="3" opacity="0.34"/>',
        "</pattern>",
        "</defs>",
        rect(0, 0, W, H, fill=CANVAS),
        rect(34, 50, W - 68, H - 84, fill=str(style["wash"]), stroke=str(style["border"]), rx=16, extra=bar_edge_extra()),
    ]


def add_row_band(parts: list[str], panel_id: int, index: int, y: float, row_h: float, highlight: bool = False) -> None:
    return


def add_header(
    parts: list[str],
    panel_id: int,
    title_subtitle_gap: float | None = None,
    subtitle_width: float | None = None,
) -> float:
    copy = PANEL_TEXT[panel_id]
    title_block, title_bottom = multiline_text_to_width(
        80,
        220,
        copy["title"],
        "title",
        "title",
        title_max_width(),
        line_height_for("title", 1.15),
        max_lines=3,
    )
    parts.append(title_block)
    gap = title_to_subtitle_gap() if title_subtitle_gap is None else title_subtitle_gap
    subtitle_block, subtitle_bottom = multiline_text_to_width(
        80,
        title_bottom + gap,
        copy["subtitle"],
        "subtitle",
        "subtitle",
        subtitle_max_width() if subtitle_width is None else subtitle_width,
        line_height_for("subtitle", 1.32),
        max_lines=3,
    )
    parts.append(subtitle_block)
    return max(700, subtitle_bottom + header_to_body_gap())


def add_footer(
    parts: list[str],
    panel_id: int,
    title_cls: str = "footer-title",
    caption_cls: str = "caption",
    y: float | None = None,
    legend_y: float | None = None,
) -> None:
    footer_value = PANEL_TEXT[panel_id]["footer"]
    if not footer_value.strip():
        return
    caption_key = caption_cls if caption_cls in FONT_SIZES else "caption"
    line_h = line_height_for(caption_key, 1.28)
    caption_lines = wrap_text_to_width(
        footer_value,
        caption_key,
        W - 220,
        max_lines=2,
    )
    if y is None:
        frame_bottom = H - 84
        text_descent = font_size(caption_key) * 0.30
        y = min(H - 155, frame_bottom - text_descent - (len(caption_lines) - 1) * line_h)
        if legend_y is not None:
            min_y_from_legend = legend_y + font_size("legend-label") * 1.5
            y = max(y, min_y_from_legend)
    parts.append(line(80, y - 70, W - 80, y - 70, stroke=BORDER, sw=LINE_WIDTH))
    footer_block, _ = multiline_text_from_lines(80, y, caption_lines, caption_cls, line_h)
    parts.append(footer_block)


def add_axis(
    parts: list[str],
    x: float,
    y: float,
    w: float,
    bottom: float,
    ticks: list[int],
    scale: float,
    suffix: str = "",
    label_cls: str = "axis-label",
) -> None:
    tick_y = bottom + max(68, font_size(label_cls) * 1.28)
    parts.append(line(x, y, x + w, y, stroke=AXIS, sw=LINE_WIDTH))
    parts.append(line(x, bottom, x + w, bottom, stroke=BORDER, sw=LINE_WIDTH))
    for tick in ticks:
        tx = x + tick * scale
        parts.append(line(tx, y - 6, tx, bottom, stroke=GRID, sw=LINE_WIDTH, extra='stroke-dasharray="6 10" stroke-linecap="round"'))
        parts.append(text(tx, tick_y, f"{tick}{suffix}", label_cls, anchor="middle"))


def add_horizontal_legend(parts: list[str], x: float, y: float, items: list[tuple[str, str]]) -> None:
    cursor = x
    swatch_w = 52
    swatch_h = 38
    gap = 28
    item_gap = 80
    for label, color in items:
        parts.append(rect(cursor, y - swatch_h + 4, swatch_w, swatch_h, fill=outcome_fill(color), stroke=outcome_stroke(color), rx=6, extra=bar_edge_extra()))
        label_x = cursor + swatch_w + gap
        parts.append(text(label_x, y, label, "legend-label"))
        cursor = label_x + text_width_for(label, "legend-label") + item_gap


def horizontal_legend_width(items: list[tuple[str, str]]) -> float:
    swatch_w = 52
    gap = 28
    item_gap = 80
    total = 0.0
    for index, (label, _) in enumerate(items):
        total += swatch_w + gap + text_width_for(label, "legend-label")
        if index < len(items) - 1:
            total += item_gap
    return total


def add_centered_legend(parts: list[str], center_x: float, y: float, items: list[tuple[str, str]]) -> None:
    add_horizontal_legend(parts, center_x - horizontal_legend_width(items) / 2, y, items)


def add_bar_label(parts: list[str], x: float, y: float, width: float, value: object, color_mode: str = "inside", chart_x: float = 0, chart_right: float = 3600) -> None:
    if width > 42 and color_mode == "inside":
        parts.append(text(x + width - 16, y + BAR_LABEL_DY, value, "bar-label-white", anchor="end"))
    else:
        label_x = x + width + 14
        if label_x > chart_right:
            label_x = x - 16
            anchor = "end"
        else:
            anchor = "start"
        parts.append(text(label_x, y + BAR_LABEL_DY, value, "bar-label", anchor=anchor))


def text_class_for(color: str) -> str:
    """Returns white text class for dark backgrounds, dark text for light backgrounds."""
    dark_colors = {CAPABILITY, CORRECT, HAZARD, SHIELD_BLUE, TRUST_GREEN}
    return "bar-label-white" if color in dark_colors else "bar-label"


def document(parts: list[str]) -> str:
    parts.append("</svg>")
    svg = "\n".join(parts)
    ET.fromstring(svg)
    return svg


def panel1(data: list[dict[str, object]]) -> str:
    style = PANEL_IDENTITY[1]
    rows = accuracy_order(data)
    parts = svg_open(PANEL_TEXT[1]["title"], PANEL_TEXT[1]["title"], 1)
    y0 = max(Y0_FLOOR, add_header(parts, 1) - 10)
    chart_x, chart_w = 760, 2100
    row_h = 140
    axis_y = y0 - 46
    bottom = y0 + row_h * len(rows)
    scale_max, ticks = 50, [0, 10, 20, 30, 40, 50]
    scale = chart_w / scale_max
    header_y = header_baseline(axis_y, "p1-header")

    parts.append(text(chart_x + chart_w / 2, header_y, PANEL_TEXT[1]["xlabel"], "p1-header", anchor="middle"))
    add_axis(parts, chart_x, axis_y, chart_w, bottom, ticks, scale, "%", label_cls="p1-axis-label")

    for i, row in enumerate(rows):
        y = y0 + i * row_h
        add_row_band(parts, 1, i, y, row_h)
        parts.append(text(80, y + ROW_LABEL_DY, row["Model"], "row-label"))
        pct = float(row["Primary_Accuracy"]) * 100
        bar_w = pct * scale
        parts.append(rect(chart_x, y - 6, bar_w, 68, fill=str(style["primary"]), stroke=str(style["primary_dark"]), rx=8, extra=bar_edge_extra()))
        # Place value just right of the bar (with min offset so tiny bars don't crowd) —
        # avoids the dead zone between short bars and a far-right value column.
        value_x = chart_x + max(bar_w + 30, 200)
        parts.append(text(value_x, y + 44, f"{pct:.1f}%", "p1-value", anchor="start"))
    add_footer(parts, 1, title_cls="p1-footer-title", caption_cls="p1-caption")
    return document(parts)


def panel2(data: list[dict[str, object]]) -> str:
    rows = accuracy_order(data)
    parts = svg_open(PANEL_TEXT[2]["title"], PANEL_TEXT[2]["title"], 2)
    y0 = max(Y0_FLOOR, add_header(parts, 2, subtitle_width=3180) - 10)
    chart_x, chart_w = 700, 2800
    row_h = 140
    axis_y = y0 - 46
    bottom = y0 + row_h * len(rows)
    scale_max, ticks = nice_count_axis(200, 40)
    scale = chart_w / scale_max
    header_y = header_baseline(axis_y)

    parts.append(text(chart_x + chart_w / 2, header_y, PANEL_TEXT[2]["xlabel"], "header", anchor="middle"))
    add_axis(parts, chart_x, axis_y, chart_w, bottom, ticks, scale)

    for i, row in enumerate(rows):
        y = y0 + i * row_h
        add_row_band(parts, 2, i, y, row_h)
        parts.append(text(80, y + ROW_LABEL_DY, row["Model"], "row-label"))

        x = chart_x
        segments = [
            ("hazard", int(row["peak_wrong_n"]), HAZARD),
            ("correct", int(row["peak_correct_n"]), CORRECT),
            ("cautious", int(row["cautious_n"]), CAUTIOUS),
            ("deferred", int(row["deferred_n"]), OTHER),
        ]
        for _, value, color in segments:
            w = value * scale
            if value:
                parts.append(rect(x, y - 6, w, 68, fill=outcome_fill(color), stroke=outcome_stroke(color), rx=8, extra=bar_edge_extra()))
                if inside_bar_label_fits(value, w):
                    parts.append(text(x + w / 2, y + BAR_LABEL_DY, value, text_class_for(color), anchor="middle"))
            x += w
    legend_y = bottom + max(158, font_size("axis-label") * 2.45)
    add_centered_legend(
        parts,
        chart_x + chart_w / 2,
        legend_y,
        [
            ("Confident Hallucination", HAZARD),
            ("Confident & Correct", CORRECT),
            ("Clinically Cautious", CAUTIOUS),
            ("Abstention", OTHER),
        ],
    )
    add_footer(parts, 2, legend_y=legend_y)
    return document(parts)


def calibration_class(row: dict[str, object]) -> tuple[str, str]:
    lower = [float(row[key]) for key in ("low_acc", "mid_acc") if not is_missing(row[key])]
    peak = float(row["peak_acc"]) if not is_missing(row["peak_acc"]) else math.nan
    if is_missing(peak) or not lower:
        return "", MUTED
    if peak >= max(lower) and peak >= 20:
        return "", TRUST_GREEN_DARK
    if peak < max(lower):
        return "Anti-calibrated", HAZARD_DARK
    return "", MUTED


def accuracy_order(data: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(data, key=lambda r: (-float(r["Primary_Accuracy"]), str(r["Model"])))


def panel3(data: list[dict[str, object]]) -> str:
    rows = accuracy_order(data)
    def rise(row: dict[str, object]) -> float:
        if is_missing(row["low_acc"]) or is_missing(row["peak_acc"]):
            return -999
        return float(row["peak_acc"]) - float(row["low_acc"])

    def drop(row: dict[str, object]) -> float:
        peak = float(row["peak_acc"]) if not is_missing(row["peak_acc"]) else math.nan
        lower = [float(row[key]) for key in ("low_acc", "mid_acc") if not is_missing(row[key])]
        if is_missing(peak) or not lower:
            return -999
        lower_max = max(lower)
        return lower_max - peak if peak < lower_max else -999

    best_calibrated = max(rows, key=rise)
    worst_calibrated = max(rows, key=drop)
    parts = svg_open(PANEL_TEXT[3]["title"], PANEL_TEXT[3]["title"], 3)
    y0 = max(Y0_FLOOR, add_header(parts, 3) - 10)
    chart_x, chart_w = 700, 2800
    row_h = 140
    axis_y = y0 - 46
    bottom = y0 + row_h * len(rows)
    scale_max, ticks = nice_pct_axis(100)
    scale = chart_w / scale_max
    header_y = header_baseline(axis_y)

    parts.append(text(chart_x + chart_w / 2, header_y, PANEL_TEXT[3]["xlabel"], "header", anchor="middle"))
    add_axis(parts, chart_x, axis_y, chart_w, bottom, ticks, scale, "%")
    legend_y = bottom + max(158, font_size("axis-label") * 2.45)
    add_centered_legend(
        parts,
        chart_x + chart_w / 2,
        legend_y,
        [
            ("Low Conf. (Likert ≤2)", FLAT_NOISE),
            ("High Conf. (Likert 3)", SAFE_UNCERTAIN),
            ("Peak Conf. (Likert 4)", TRUST_GREEN),
        ],
    )

    for i, row in enumerate(rows):
        y = y0 + i * row_h
        trend, color = calibration_class(row)
        add_row_band(parts, 3, i, y, row_h, highlight=trend == "Anti-calibrated")
        parts.append(text(80, y + ROW_LABEL_DY, row["Model"], "row-label"))

        vals = [row["low_acc"], row["mid_acc"], row["peak_acc"]]
        xs = [chart_x + float(v) * scale for v in vals if not is_missing(v)]
        mark_y = y - 8
        if len(xs) >= 2:
            parts.append(line(min(xs), mark_y, max(xs), mark_y, stroke=color, sw=4.4))
        if not is_missing(row["low_acc"]):
            x = chart_x + float(row["low_acc"]) * scale
            parts.append(circle(x, mark_y, 12, fill=FLAT_NOISE, stroke=FLAT_NOISE_DARK, sw=LINE_WIDTH))
        if not is_missing(row["mid_acc"]):
            x = chart_x + float(row["mid_acc"]) * scale
            parts.append(rect(x - 12, mark_y - 12, 24, 24, fill=SAFE_UNCERTAIN, stroke=SAFE_UNCERTAIN_DARK, rx=3, extra=bar_edge_extra()))
        if not is_missing(row["peak_acc"]):
            x = chart_x + float(row["peak_acc"]) * scale
            peak_fill = HAZARD if trend == "Anti-calibrated" else TRUST_GREEN if color == TRUST_GREEN_DARK else FLAT_NOISE
            peak_edge = HAZARD_DARK if trend == "Anti-calibrated" else TRUST_GREEN_DARK if color == TRUST_GREEN_DARK else FLAT_NOISE_DARK
            parts.append(polygon([(x, mark_y), (x + 16, mark_y - 16), (x + 32, mark_y), (x + 16, mark_y + 16)], fill=peak_fill, stroke=peak_edge))
        if row["Model"] == best_calibrated["Model"] and not is_missing(row["low_acc"]) and not is_missing(row["peak_acc"]):
            x = chart_x + float(row["peak_acc"]) * scale
            parts.append(
                multiline_text_verbatim(
                    min(x + 430, W - 390),
                    y - 58,
                    f"Strong monotonic rise\n({float(row['low_acc']):.1f}% → {float(row['peak_acc']):.1f}%)",
                    "small",
                    line_height_for("small", 1.18),
                    anchor="middle",
                )
            )
        if row["Model"] == worst_calibrated["Model"] and drop(row) > 0 and not is_missing(row["peak_acc"]):
            x = chart_x + float(row["peak_acc"]) * scale
            # Position above the row's mark line rather than on top of it.
            parts.append(text(x + 60, mark_y - 28, "Anti-calibrated", "micro-alert", anchor="start"))
    add_footer(parts, 3, legend_y=legend_y)
    return document(parts)


def panel4(data: list[dict[str, object]]) -> str:
    rows = accuracy_order(data)
    max_risk = max(rows, key=lambda r: int(r["peak_wrong_n"]))
    parts = svg_open(PANEL_TEXT[4]["title"], PANEL_TEXT[4]["title"], 4)
    y0 = max(Y0_FLOOR, add_header(parts, 4) - 10)
    chart_x, chart_w = 700, 2800
    row_h = 140
    axis_y = y0 - 46
    bottom = y0 + row_h * len(rows)
    scale_max, ticks = nice_count_axis(200, 40)
    scale = chart_w / scale_max
    header_y = header_baseline(axis_y)

    parts.append(text(chart_x + chart_w / 2, header_y, PANEL_TEXT[4]["xlabel"], "header", anchor="middle"))
    add_axis(parts, chart_x, axis_y, chart_w, bottom, ticks, scale)
    legend_y = bottom + max(158, font_size("axis-label") * 2.45)
    add_centered_legend(
        parts,
        chart_x + chart_w / 2,
        legend_y,
        [
            ("Verified Safe", SHIELD_BLUE),
            ("Safe Uncertainty", CAUTIOUS),
            ("Misleading Hazard", HAZARD),
        ],
    )

    for i, row in enumerate(rows):
        y = y0 + i * row_h
        add_row_band(parts, 4, i, y, row_h, highlight=row["Model"] == max_risk["Model"])
        parts.append(text(80, y + ROW_LABEL_DY, row["Model"], "row-label"))
        x = chart_x
        segments = [
            (int(row["peak_correct_n"]), SHIELD_BLUE),
            (int(row["cautious_n"]) + int(row["deferred_n"]), CAUTIOUS),
            (int(row["peak_wrong_n"]), HAZARD),
        ]
        for value, color in segments:
            w = value * scale
            if value:
                parts.append(rect(x, y - 6, w, 68, fill=outcome_fill(color), stroke=outcome_stroke(color), rx=8, extra=bar_edge_extra()))
                if inside_bar_label_fits(value, w):
                    parts.append(text(x + w / 2, y + BAR_LABEL_DY, value, text_class_for(color), anchor="middle"))
            x += w
    add_footer(parts, 4, legend_y=legend_y)
    return document(parts)


def panel5(data: list[dict[str, object]]) -> str:
    rows = accuracy_order(data)
    best = max(rows, key=lambda r: float(r["ppv_correct"]))
    parts = svg_open(PANEL_TEXT[5]["title"], PANEL_TEXT[5]["title"], 5)
    y0 = max(Y0_FLOOR, add_header(parts, 5) - 10)
    chart_x, chart_w = 760, 2500
    row_h = 140
    axis_y = y0 - 46
    bottom = y0 + row_h * len(rows)
    scale_max, ticks = nice_pct_axis(100)
    scale = chart_w / scale_max
    metric_x = chart_x + chart_w + 90
    header_y = header_baseline(axis_y)

    parts.append(text(chart_x + chart_w / 2, header_y, PANEL_TEXT[5]["xlabel"], "header", anchor="middle"))
    legend_y = bottom + max(158, font_size("axis-label") * 2.45)
    add_centered_legend(
        parts,
        chart_x + chart_w / 2,
        legend_y,
        [
            ("Actionable & Correct", TRUST_GREEN),
            ("Misleading Hallucination", HAZARD),
        ],
    )
    add_axis(parts, chart_x, axis_y, chart_w, bottom, ticks, scale, "%")

    for i, row in enumerate(rows):
        y = y0 + i * row_h
        add_row_band(parts, 5, i, y, row_h, highlight=row["Model"] == best["Model"])
        parts.append(text(80, y + ROW_LABEL_DY, row["Model"], "row-label"))
        correct_pct = float(row["ppv_correct"])
        wrong_pct = float(row["ppv_wrong"])
        correct_w = correct_pct * scale
        wrong_w = wrong_pct * scale
        parts.append(rect(chart_x, y - 6, correct_w, 68, fill=TRUST_GREEN, stroke=outcome_stroke(TRUST_GREEN), rx=8, extra=bar_edge_extra()))
        parts.append(rect(chart_x + correct_w, y - 6, wrong_w, 68, fill=outcome_fill(HAZARD), stroke=outcome_stroke(HAZARD), rx=8, extra=bar_edge_extra()))
        correct_label = f"{correct_pct:.0f}%"
        wrong_label = f"{wrong_pct:.0f}%"
        if inside_bar_label_fits(correct_label, correct_w):
            parts.append(text(chart_x + correct_w / 2, y + BAR_LABEL_DY, correct_label, text_class_for(TRUST_GREEN), anchor="middle"))
        elif correct_w > 0:
            label_x, anchor = clipped_bar_label(chart_x - 16, chart_x, chart_x + chart_w)
            parts.append(text(label_x, y + BAR_LABEL_DY, correct_label, "bar-label", anchor=anchor))
        if inside_bar_label_fits(wrong_label, wrong_w):
            parts.append(text(chart_x + correct_w + wrong_w / 2, y + BAR_LABEL_DY, wrong_label, text_class_for(HAZARD), anchor="middle"))
        elif wrong_w > 0:
            label_x, anchor = clipped_bar_label(chart_x + correct_w + wrong_w + 16, chart_x, chart_x + chart_w)
            parts.append(text(label_x, y + BAR_LABEL_DY, wrong_label, "bar-label", anchor=anchor))
        parts.append(text(metric_x, y + ROW_METRIC_DY, f"(n={nfmt(row['n_very_high_conf'])})", "row-metric-muted", anchor="middle"))
    add_footer(parts, 5, legend_y=legend_y)
    return document(parts)


def panel6(data: list[dict[str, object]]) -> str:
    rows = accuracy_order(data)
    worst = min(rows, key=lambda r: int(r["peak_correct_n"]) - int(r["peak_wrong_n"]))
    parts = svg_open(PANEL_TEXT[6]["title"], PANEL_TEXT[6]["title"], 6)
    y0 = max(Y0_FLOOR, add_header(parts, 6) - 10)
    chart_x, chart_w = 700, 2800
    row_h = 140
    axis_y = y0 - 46
    bottom = y0 + row_h * len(rows)
    left_w = 1680
    right_w = chart_w - left_w
    max_wrong = max(int(r["peak_wrong_n"]) for r in data)
    max_correct = max(int(r["peak_correct_n"]) for r in data)
    wrong_axis, wrong_ticks = nice_count_axis(max_wrong, 40)
    correct_axis, correct_ticks = nice_count_axis(max_correct, 40)
    scale_left = left_w / wrong_axis
    scale_right = right_w / correct_axis
    zero_x = chart_x + left_w
    header_y = header_baseline(axis_y)

    parts.append(text(chart_x + chart_w / 2, header_y, PANEL_TEXT[6]["xlabel"], "header", anchor="middle"))
    legend_y = bottom + max(158, font_size("axis-label") * 2.45)
    add_centered_legend(
        parts,
        chart_x + chart_w / 2,
        legend_y,
        [
            ("Actionable & Correct", TRUST_GREEN),
            ("Misleading Hallucination", HAZARD),
        ],
    )
    parts.append(line(chart_x, axis_y, chart_x + chart_w, axis_y, stroke=AXIS, sw=LINE_WIDTH))
    parts.append(line(chart_x, bottom, chart_x + chart_w, bottom, stroke=BORDER, sw=LINE_WIDTH))
    tick_y = bottom + max(68, font_size("axis-label") * 1.28)
    for tick in wrong_ticks:
        tx = zero_x - tick * scale_left
        parts.append(line(tx, axis_y - 6, tx, bottom, stroke=GRID, sw=LINE_WIDTH, extra='stroke-dasharray="6 10" stroke-linecap="round"'))
        parts.append(text(tx, tick_y, f"-{tick}" if tick else "0", "axis-label", anchor="middle"))
    for tick in correct_ticks[1:]:
        tx = zero_x + tick * scale_right
        parts.append(line(tx, axis_y - 6, tx, bottom, stroke=GRID, sw=LINE_WIDTH, extra='stroke-dasharray="6 10" stroke-linecap="round"'))
        parts.append(text(tx, tick_y, nfmt(tick), "axis-label", anchor="middle"))
    parts.append(line(zero_x, axis_y - 8, zero_x, bottom, stroke=TEXT, sw=LINE_WIDTH))

    for i, row in enumerate(rows):
        y = y0 + i * row_h
        add_row_band(parts, 6, i, y, row_h, highlight=row["Model"] == worst["Model"])
        parts.append(text(80, y + ROW_LABEL_DY, row["Model"], "row-label"))
        wrong = int(row["peak_wrong_n"])
        correct = int(row["peak_correct_n"])
        wrong_w = wrong * scale_left
        correct_w = correct * scale_right
        if wrong:
            parts.append(rect(zero_x - wrong_w, y - 6, wrong_w, 68, fill=outcome_fill(HAZARD), stroke=outcome_stroke(HAZARD), rx=8, extra=bar_edge_extra()))
            parts.append(text(zero_x - max(wrong_w + 16, 84), y + BAR_LABEL_DY, wrong, "bar-label", anchor="end"))
        if correct:
            parts.append(rect(zero_x, y - 6, correct_w, 68, fill=TRUST_GREEN, stroke=outcome_stroke(TRUST_GREEN), rx=8, extra=bar_edge_extra()))
            parts.append(text(zero_x + max(correct_w + 16, 84), y + BAR_LABEL_DY, correct, "bar-label"))
    add_footer(parts, 6, legend_y=legend_y)
    return document(parts)


def write_contact_sheet() -> Path:
    cards = []
    for panel_id, filename in OUT_FILES.items():
        title_value = PANEL_TEXT[panel_id]["title"]
        svg_path = SCRIPT_DIR / filename
        cache_key = hashlib.sha1(svg_path.read_bytes()).hexdigest()[:12] if svg_path.exists() else "pending"
        cards.append(
            f'<figure><img src="{esc(filename)}?v={cache_key}" alt="{esc(title_value)}"></figure>'
        )
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(PANEL_TEXT[1]["title"])}</title>
<style>
  body {{ margin: 24px; background: {CANVAS}; color: {TEXT}; font-family: {FONT}; }}
  .grid {{ display: grid; grid-template-columns: minmax(0, 3600px); gap: 28px; align-items: start; }}
  figure {{ margin: 0; background: {SURFACE}; border: 1px solid {BORDER}; padding: 12px; }}
  img {{ display: block; width: 100%; height: auto; }}
  @media (max-width: 3650px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="grid">
{''.join(cards)}
</div>
</body>
</html>
"""
    path = SCRIPT_DIR / "contact_sheet.html"
    path.write_text(html_doc, encoding="utf-8", newline="\n")
    return path


def write_manifest() -> Path:
    figures = []
    for panel_id, filename in OUT_FILES.items():
        figures.append(
            {
                "claim": PANEL_TEXT[panel_id]["title"],
                "x": PANEL_TEXT[panel_id]["xlabel"],
                "caption_role": PANEL_TEXT[panel_id]["footer"],
                "outputs": [filename],
            }
        )
    manifest = {"figures": figures}
    path = SCRIPT_DIR / "figure_manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def write_captions() -> Path:
    lines = []
    for panel_id in range(1, 7):
        for field in ("title", "subtitle", "footer"):
            value = PANEL_TEXT[panel_id][field]
            if value.strip():
                lines.append(value)
                lines.append("")
    path = SCRIPT_DIR / "captions.md"
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def write_provenance(data: list[dict[str, object]], qa_notes: list[str]) -> Path:
    path = SCRIPT_DIR / "data_provenance.md"
    path.write_text("", encoding="utf-8", newline="\n")
    return path


def write_reviewer_checklist() -> Path:
    path = SCRIPT_DIR / "reviewer_checklist.md"
    path.write_text("", encoding="utf-8", newline="\n")
    return path


def write_qa(data: list[dict[str, object]], qa_notes: list[str], written: list[Path]) -> Path:
    path = SCRIPT_DIR / "handwritten_panels_qa.txt"
    path.write_text("", encoding="utf-8", newline="\n")
    return path


def build() -> tuple[dict[int, str], list[dict[str, object]], list[str]]:
    results = load_results()
    data, qa_notes = merge_long_format(results)
    panels = {
        1: panel1(data),
        2: panel2(data),
        3: panel3(data),
        4: panel4(data),
        5: panel5(data),
        6: panel6(data),
    }
    return panels, data, qa_notes


def main() -> None:
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    font_config_path = ensure_font_size_csv()
    panels, data, qa_notes = build()

    written: list[Path] = []
    written.append(font_config_path)
    print(f"Using {font_config_path}")
    for panel_id, svg in panels.items():
        path = SCRIPT_DIR / OUT_FILES[panel_id]
        path.write_text(svg, encoding="utf-8", newline="\n")
        written.append(path)
        print(f"Wrote {path}")

    for path in [
        write_contact_sheet(),
        write_manifest(),
        write_captions(),
        write_provenance(data, qa_notes),
        write_reviewer_checklist(),
    ]:
        written.append(path)
        print(f"Wrote {path}")

    qa_path = write_qa(data, qa_notes, written)
    print(f"Wrote {qa_path}")


if __name__ == "__main__":
    main()
