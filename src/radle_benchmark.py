import base64
import hashlib
import json
import os
import pathlib
import re
import shutil
import time
from collections import defaultdict
from datetime import datetime, timezone

import anthropic
from google import genai as google_genai
from google.genai import types as google_genai_types
import pandas as pd


MAX_OUTPUT_TOKENS = 16384
UNIVERSAL_TEMPERATURE = 0.01
CHECKPOINT_CASE_INTERVAL = 10
MAX_REPAIR_ATTEMPTS_MALFORMED = 2
MAX_REPAIR_ATTEMPTS_API_ERROR = 2
MAX_REPAIR_ATTEMPTS_PROVIDER_BLOCK = 1
EXCLUDED_IMAGE_EXTENSIONS = {".txt", ".csv", ".json", ".docx", ".zip"}

PROVIDER_CONTENT_BLOCK_MARKERS = (
    "input data may contain inappropriate content",
    "inappropriate content",
    "provider returned error",
    "content policy",
    "policy violation",
    "safety",
)

NO_TEMPERATURE_MODELS = {
    "gpt-5.5",
    "claude-fable-5",
}

MODELS = [
    {
        "name": "gpt_5_5",
        "id": "gpt-5.5",
        "provider": "openai",
        "extra": {"reasoning_effort": "high"},
    },
    {
        "name": "claude_fable_5",
        "id": "claude-fable-5",
        "provider": "anthropic",
        "extra": {
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": "high"},
        },
    },
    {
        "name": "gemini_3_1_pro",
        "id": "gemini-3.1-pro-preview",
        "provider": "google",
        "extra": {"thinking_level": "high"},
    },
    {
        "name": "grok_4_20",
        # Vision-only: Grok 4.20 silently drops the image whenever any reasoning
        # parameter is set (effort/enabled, any provider or the -multi-agent slug),
        # producing blind hallucinated diagnoses. Reasoning must stay OFF for it to
        # see images. Verified via OpenRouter probe 2026-06-13.
        "id": "x-ai/grok-4.20",
        "extra": None,
    },
    {
        "name": "qwen_vl_max",
        "id": "qwen/qwen-vl-max",
        "extra": None,
    },
    {
        "name": "gemma_4_31b",
        "id": "google/gemma-4-31b-it",
        "extra": {"reasoning": {"enabled": True}},
    },
    {
        "name": "llama_4_maverick",
        "id": "meta-llama/llama-4-maverick",
        "extra": None,
    },
    {
        "name": "pixtral_large",
        "id": "mistralai/pixtral-large-2411",
        "extra": None,
    },
    {
        "name": "glm_4_6v",
        "id": "z-ai/glm-4.6v",
        "extra": {"reasoning": {"enabled": True}},
    },
    {
        "name": "nemotron_3_omni",
        "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "extra": {"reasoning": {"enabled": True}},
    },
]

PROMPT = """
System prompt:

You are a board-certified diagnostic radiologist. Given a medical image, provide the single most specific final diagnosis.

Rules:
	1.	If you can identify a diagnosis, return it. If you truly cannot, return “I don’t know”.
	2.	No abbreviations, use full words only.
	3.	No verbose descriptions of the diagnosis.
	4.	Use the following Likert confidence scale (only when a diagnosis is given) to tell how confident you are in your diagnosis:
	∙	0 = very low confidence (essentially a guess)
	∙	1 = low confidence (weak leading diagnosis, several alternatives similarly plausible)
	∙	2 = moderate confidence (one diagnosis favored, important alternatives remain)
	∙	3 = high confidence (one diagnosis clearly favored, alternatives unlikely)
	∙	4 = very high confidence (classic appearance, essentially certain)
5. If you return “I don’t know”, then return Likert score as “null”.

Final output format:  Respond with this JSON:

{"diagnosis": "<diagnosis in full words or I don't know>", "likert_score": <0-4 or null>}


Example outputs:

{"diagnosis": "Pulmonary tuberculosis", "likert_score": 3}

{"diagnosis": "Von Hippel-Lindau syndrome", "likert_score": 4}

{"diagnosis": "I don't know", "likert_score": null}
""".strip()


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_mime_type(path):
    with open(path, "rb") as image_file:
        header = image_file.read(8)

    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8"):
        return "image/jpeg"
    return "image/jpeg"


def extract_json_safely(raw_text):
    """Extract diagnosis JSON while ignoring Markdown fences or reasoning text."""
    if raw_text is None:
        return "PARSE_FAILED", "PARSE_FAILED"

    text = str(raw_text).strip()
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            data_lower = {str(k).lower(): v for k, v in data.items()}
            diag = data_lower.get("diagnosis", "JSON_MISSING_KEY")
            likert = data_lower.get("likert_score", data_lower.get("likert", "NULL"))
            return diag, likert
    except Exception:
        pass

    candidates = re.findall(r"\{[^{}]*\}", text, flags=re.DOTALL)
    valid = []

    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                data_lower = {str(k).lower(): v for k, v in data.items()}
                if "diagnosis" in data_lower:
                    valid.append(data_lower)
        except Exception:
            continue

    if valid:
        data_lower = valid[-1]
        diag = data_lower.get("diagnosis", "JSON_MISSING_KEY")
        likert = data_lower.get("likert_score", data_lower.get("likert", "NULL"))
        return diag, likert

    diag_match = re.search(
        r'"diagnosis"\s*:\s*"([^"]+)"',
        text,
        flags=re.IGNORECASE,
    )
    likert_match = re.search(
        r'"(?:likert_score|likert)"\s*:\s*(null|None|[0-4]|"[^"]*")',
        text,
        flags=re.IGNORECASE,
    )

    if diag_match:
        diag = diag_match.group(1).strip()
        if likert_match:
            likert_raw = likert_match.group(1).strip().strip('"')
            if likert_raw.lower() in {"null", "none"}:
                likert = None
            else:
                try:
                    likert = int(likert_raw)
                except Exception:
                    likert = likert_raw
        else:
            likert = "NULL"

        return diag, likert

    return "PARSE_FAILED", "PARSE_FAILED"


def _csv_sibling_path(path, suffix):
    """Return a sibling CSV path by appending suffix to the CSV stem."""
    path_obj = pathlib.Path(path)
    if path_obj.suffix.lower() == ".csv":
        return str(path_obj.with_name(f"{path_obj.stem}{suffix}.csv"))
    return f"{path}{suffix}.csv"


def _slugify_label(value):
    """Return a filesystem-safe run label."""
    text = safe_str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "run"


def build_run_paths(dataset_root, run_label="test_1_case", run_id=None, create_dirs=True):
    """Build intuitive Drive/local paths for one benchmark run.

    No result files are created here. When create_dirs is true, only folders are made.
    """
    dataset_root = pathlib.Path(dataset_root)
    if run_id is None:
        run_id = f"{datetime.now().strftime('%Y-%m-%d')}_{_slugify_label(run_label)}"

    run_root = dataset_root / "Runs" / run_id
    raw_dir = run_root / "raw"
    repair_dir = run_root / "repair"
    final_dir = run_root / "final"
    scorer_dir = run_root / "scorer"
    public_release_dir = run_root / "public_release"

    paths = {
        "run_id": run_id,
        "dataset_root": str(dataset_root),
        "master_images_folder": str(dataset_root / "RadLE v2 Master Data"),
        "runs_root": str(dataset_root / "Runs"),
        "run_root": str(run_root),
        "raw_dir": str(raw_dir),
        "raw_results_csv": str(raw_dir / "results.csv"),
        "raw_backup_dir": str(raw_dir / "backups"),
        "repair_dir": str(repair_dir),
        "repair_results_csv": str(repair_dir / "repaired_results.csv"),
        "repair_backup_dir": str(repair_dir / "backups"),
        "repair_plan_csv": str(repair_dir / "repair_plan.csv"),
        "repair_call_log_csv": str(repair_dir / "repair_call_log.csv"),
        "final_dir": str(final_dir),
        "final_results_csv": str(final_dir / "RadLE_v2_results_final.csv"),
        "final_manifest_json": str(final_dir / "RadLE_v2_results_final_manifest.json"),
        "scorer_dir": str(scorer_dir),
        "scorer_view_csv": str(scorer_dir / "scorer_view.csv"),
        "public_release_dir": str(public_release_dir),
    }

    if create_dirs:
        for key, value in paths.items():
            if key.endswith("_dir") or key in {"runs_root", "run_root"}:
                os.makedirs(value, exist_ok=True)

    return paths


def _backup_csv_path(output_csv, suffix, backup_dir=None):
    """Return a backup CSV path, optionally under a dedicated backup directory."""
    if not backup_dir:
        return _csv_sibling_path(output_csv, suffix)

    output_path = pathlib.Path(output_csv)
    backup_path = pathlib.Path(backup_dir) / f"{output_path.stem}{suffix}.csv"
    return str(backup_path)


def default_latest_backup_path(output_csv, backup_dir=None):
    """Return the rolling latest backup path for a benchmark output CSV."""
    return _backup_csv_path(output_csv, "_BACKUP", backup_dir=backup_dir)


def next_numbered_backup_path(output_csv, backup_dir=None):
    """Return the next available numbered backup path for a benchmark output CSV."""
    for n in range(1, 10000):
        candidate = _backup_csv_path(output_csv, f"_BACKUP_{n:04d}", backup_dir=backup_dir)
        if not os.path.exists(candidate):
            return candidate
    raise RuntimeError(f"Could not find available numbered backup path for {output_csv}")


def atomic_to_csv(df, path):
    """Write a dataframe to CSV through a temporary file and atomic replace."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    temp_path = f"{path}.tmp"
    df.to_csv(temp_path, index=False)
    os.replace(temp_path, path)


def save_benchmark_progress(
    df,
    output_csv,
    latest_backup_csv=None,
    numbered=False,
    backup_dir=None,
):
    """Save main output plus rolling/latest backup, optionally with a numbered backup."""
    latest_backup_csv = latest_backup_csv or default_latest_backup_path(
        output_csv,
        backup_dir=backup_dir,
    )

    atomic_to_csv(df, output_csv)
    atomic_to_csv(df, latest_backup_csv)

    numbered_path = None
    if numbered:
        numbered_path = next_numbered_backup_path(output_csv, backup_dir=backup_dir)
        atomic_to_csv(df, numbered_path)

    return numbered_path


def make_json_safe(obj):
    """Convert OpenAI/Pydantic-style objects into JSON-safe structures."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return make_json_safe(obj.model_dump())
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_json_safe(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def model_names_from_models(models=None):
    """Return model names from a model config list or string list."""
    models = models or MODELS
    names = []
    for model in models:
        if isinstance(model, dict):
            names.append(model["name"])
        else:
            names.append(str(model))
    return names


def normalize_case_id(value):
    """Normalize CSV case IDs so 1 and 1.0 compare consistently."""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def numeric_case_sort_key(case_id):
    """Sort numeric case IDs numerically and non-numeric IDs after them."""
    text = normalize_case_id(case_id)
    return (0, int(text)) if text.isdigit() else (1, text)


def case_id_match_mask(df, case_id):
    """Return rows whose stored case ID matches case_id after internal normalization."""
    if "Master_Case_ID" not in df.columns:
        return pd.Series(False, index=df.index)
    target = normalize_case_id(case_id)
    return df["Master_Case_ID"].apply(normalize_case_id) == target


def safe_str(value):
    """Return an empty string for pandas null values, else str(value)."""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)


def compact_text(value):
    """Collapse whitespace for compact audit previews."""
    return re.sub(r"\s+", " ", safe_str(value)).strip()


def normalize_diag_for_abstention(value):
    """Normalize obvious I-don't-know variants for conservative analysis triage."""
    text = safe_str(value).strip().lower()
    text = text.replace("’", "'")
    return re.sub(r"[^a-z0-9]+", "", text)


def is_abstention_variant(value):
    """Return True for narrow no-paid abstention spelling variants."""
    return normalize_diag_for_abstention(value) in {
        "idontknow",
        "idonotknow",
        "dontknow",
        "unknown",
    }


def is_exact_valid_i_dont_know(value):
    """Return True only for the canonical benchmark abstention."""
    return safe_str(value).strip() == "I don't know"


def is_valid_likert_value(value):
    """Return True when value is a valid RadLE Likert confidence score."""
    try:
        if pd.isna(value):
            return False
    except Exception:
        pass

    text = str(value).strip()
    if text == "" or text.lower() in {
        "none",
        "null",
        "nan",
        "na",
        "n/a",
        "error",
        "parse_failed",
    }:
        return False

    try:
        return float(text) in {0.0, 1.0, 2.0, 3.0, 4.0}
    except Exception:
        return False


def is_null_likert_value(value):
    """Return True when a CSV/JSON value represents a null Likert score."""
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass

    return str(value).strip().lower() in {
        "",
        "none",
        "null",
        "nan",
        "na",
        "n/a",
    }


def text_blob(row, model_name):
    """Collect model-specific diagnostic, reasoning, and raw text fields."""
    cols = [
        f"Diagnosis_{model_name}",
        f"Likert_{model_name}",
        f"Raw_Response_{model_name}",
        f"Reasoning_{model_name}",
        f"Reasoning_Raw_{model_name}",
        f"Reasoning_Details_{model_name}",
        f"Usage_JSON_{model_name}",
    ]

    parts = []
    for col in cols:
        if col in row.index:
            value = row.get(col)
            try:
                if pd.isna(value):
                    continue
            except Exception:
                pass
            parts.append(str(value))

    return "\n".join(parts)


def is_provider_content_block_text(text):
    """Detect likely provider/content/safety policy blocks in text."""
    text = safe_str(text).lower()
    return any(marker in text for marker in PROVIDER_CONTENT_BLOCK_MARKERS)


def is_provider_content_block(row, model_name):
    """Detect likely provider/content/safety policy blocks in one model cell."""
    return is_provider_content_block_text(text_blob(row, model_name))


def extract_from_raw_no_write(raw_text):
    """Try to recover diagnosis JSON from raw text without mutating output data."""
    diag, likert = extract_json_safely(raw_text)
    if safe_str(diag).strip() in {"", "PARSE_FAILED", "JSON_MISSING_KEY"}:
        return None, None, ""
    return diag, likert, "extract_json_safely"


def normalize_likert_for_output(value):
    """Return RadLE Likert values as ints and null-like values as None."""
    if is_null_likert_value(value):
        return None

    try:
        numeric = float(str(value).strip())
        if numeric in {0.0, 1.0, 2.0, 3.0, 4.0}:
            return int(numeric)
    except Exception:
        pass

    return value


def no_paid_cleanup_values(info):
    """Return diagnosis/Likert values that can be safely written without an API call."""
    if info.get("bucket") != "no_paid_cleanup":
        return None, None

    rescued_diag = info.get("rescued_diag")
    if safe_str(rescued_diag).strip() == "":
        return None, None

    if is_exact_valid_i_dont_know(rescued_diag) or is_abstention_variant(rescued_diag):
        return "I don't know", None

    rescued_likert = info.get("rescued_likert")
    if is_valid_likert_value(rescued_likert):
        return safe_str(rescued_diag).strip(), normalize_likert_for_output(rescued_likert)

    return None, None


def apply_no_paid_cleanup_to_cell(df, df_idx, model_name, info):
    """Write recovered diagnosis/Likert values for one no-paid cleanup cell."""
    diag_col = f"Diagnosis_{model_name}"
    likert_col = f"Likert_{model_name}"
    if diag_col not in df.columns or likert_col not in df.columns:
        return False

    cleaned_diag, cleaned_likert = no_paid_cleanup_values(info)
    if cleaned_diag is None:
        return False

    df.at[df_idx, diag_col] = cleaned_diag
    df.at[df_idx, likert_col] = cleaned_likert
    return True


def build_no_paid_cleanup_plan(df, models=None):
    """Build a dataframe of cells that can be repaired from raw text without API calls."""
    if "Master_Case_ID" not in df.columns:
        raise ValueError("Benchmark dataframe must contain Master_Case_ID.")

    model_names = model_names_from_models(models)
    rows = []
    for _, row in df.iterrows():
        case_id = normalize_case_id(row["Master_Case_ID"])
        for model_name in model_names:
            info = classify_cell_for_audit(row, model_name, attempts=0)
            if info.get("bucket") != "no_paid_cleanup":
                continue

            cleaned_diag, cleaned_likert = no_paid_cleanup_values(info)
            if cleaned_diag is None:
                continue

            rows.append({
                "Master_Case_ID": case_id,
                "model": model_name,
                "status": info.get("status", ""),
                "reason": info.get("reason", ""),
                "current_diagnosis": safe_str(row.get(f"Diagnosis_{model_name}", "")),
                "current_likert": safe_str(row.get(f"Likert_{model_name}", "")),
                "rescued_diag": info.get("rescued_diag", ""),
                "rescued_likert": info.get("rescued_likert", ""),
                "cleanup_diagnosis": cleaned_diag,
                "cleanup_likert": cleaned_likert,
                "rescue_method": info.get("rescue_method", ""),
            })

    return pd.DataFrame(rows)


def apply_no_paid_cleanups(df, models=None, verbose=False):
    """Apply all no-paid cleanup candidates in-place and return the number changed."""
    model_names = model_names_from_models(models)
    cleanup_count = 0

    for df_idx in df.index:
        row = df.loc[df_idx]
        case_id = normalize_case_id(row["Master_Case_ID"]) if "Master_Case_ID" in row.index else ""
        for model_name in model_names:
            info = classify_cell_for_audit(row, model_name, attempts=0)
            if apply_no_paid_cleanup_to_cell(df, df_idx, model_name, info):
                cleanup_count += 1
                if verbose:
                    print(
                        f"No-API cleanup: case {case_id} | {model_name} | "
                        f"{info.get('reason')}"
                    )
                row = df.loc[df_idx]

    return cleanup_count


def get_token_value(row, model_name, col_prefix):
    """Return numeric token value for a model cell, defaulting to 0."""
    col = f"{col_prefix}_{model_name}"
    if col not in row.index:
        return 0
    value = row.get(col)
    try:
        if pd.isna(value) or str(value).strip() == "":
            return 0
        return float(value)
    except Exception:
        return 0


def _empty_dataframe(columns):
    return pd.DataFrame(columns=columns)


def _normalize_expected_case_ids(expected_case_ids):
    if expected_case_ids is None:
        return []
    if isinstance(expected_case_ids, int):
        return [str(i) for i in range(1, expected_case_ids + 1)]
    return [normalize_case_id(x) for x in expected_case_ids]


def _load_call_log(call_log_csv):
    if not call_log_csv or not os.path.exists(call_log_csv):
        return pd.DataFrame()
    try:
        call_log_df = pd.read_csv(call_log_csv, dtype={"Master_Case_ID": str})
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    if "Master_Case_ID" in call_log_df.columns:
        call_log_df["Master_Case_ID"] = call_log_df["Master_Case_ID"].apply(normalize_case_id)
    return call_log_df


def get_repair_attempts_from_log(repair_log_df, case_id, model_name):
    """Count repair attempts from separate repair log STARTED events."""
    required = {"Master_Case_ID", "model", "event"}
    if repair_log_df is None or not len(repair_log_df) or not required.issubset(repair_log_df.columns):
        return 0

    events = repair_log_df["event"].astype(str).str.upper()
    mask = (
        (repair_log_df["Master_Case_ID"].astype(str).apply(normalize_case_id) == normalize_case_id(case_id))
        & (repair_log_df["model"].astype(str) == str(model_name))
        & (events == "REPAIR_STARTED")
    )
    return int(mask.sum())


def _repair_status(status, bucket, reason, needs_api_repair, max_attempts, **extra):
    result = {
        "status": status,
        "bucket": bucket,
        "reason": reason,
        "needs_api_repair": bool(needs_api_repair),
        "max_attempts": int(max_attempts),
    }
    result.update(extra)
    return result


def classify_cell_for_audit(row, model_name, attempts=0, max_output_tokens=MAX_OUTPUT_TOKENS):
    """Classify one case-model cell for audit and targeted repair planning."""
    diag_col = f"Diagnosis_{model_name}"
    likert_col = f"Likert_{model_name}"
    raw_col = f"Raw_Response_{model_name}"

    diagnosis = safe_str(row.get(diag_col, "")) if diag_col in row.index else ""
    likert = row.get(likert_col, "") if likert_col in row.index else ""
    raw = safe_str(row.get(raw_col, "")) if raw_col in row.index else ""
    completion_tokens = get_token_value(row, model_name, "Total_Tokens_Out")
    hit_max_tokens = completion_tokens >= max_output_tokens

    if diag_col not in row.index:
        return _repair_status(
            "repair_target_missing_diagnosis_column",
            "paid_repair",
            "missing_diagnosis_column",
            attempts < MAX_REPAIR_ATTEMPTS_MALFORMED,
            MAX_REPAIR_ATTEMPTS_MALFORMED,
        )

    if diagnosis.strip() == "":
        return _repair_status(
            "repair_target_missing_or_empty_diagnosis",
            "paid_repair",
            "missing_or_empty_diagnosis",
            attempts < MAX_REPAIR_ATTEMPTS_MALFORMED,
            MAX_REPAIR_ATTEMPTS_MALFORMED,
        )

    if is_exact_valid_i_dont_know(diagnosis):
        if not is_null_likert_value(likert):
            return _repair_status(
                "analysis_flag_i_dont_know_non_null_likert",
                "analysis_flag",
                "abstention_likert_ignored_in_analysis",
                False,
                0,
            )

        return _repair_status(
            "accepted_i_dont_know",
            "accepted",
            "accepted_i_dont_know",
            False,
            0,
        )

    if is_abstention_variant(diagnosis):
        return _repair_status(
            "analysis_flag_abstention_variant",
            "analysis_flag",
            "abstention_variant_preserve_raw",
            False,
            0,
        )

    if diagnosis in {"API_ERROR", "ERROR", "NULL_ERROR"}:
        if is_provider_content_block(row, model_name):
            needs = attempts < MAX_REPAIR_ATTEMPTS_PROVIDER_BLOCK
            return _repair_status(
                "repair_target_provider_content_block_once" if needs else "terminal_provider_content_block",
                "limited_provider_retry" if needs else "terminal",
                "provider_content_block_retry_once" if needs else "terminal_provider_content_block",
                needs,
                MAX_REPAIR_ATTEMPTS_PROVIDER_BLOCK,
            )

        needs = attempts < MAX_REPAIR_ATTEMPTS_API_ERROR
        return _repair_status(
            "repair_target_api_error_non_content" if needs else "repair_exhausted_api_error_non_content",
            "paid_repair" if needs else "terminal",
            "api_error_non_content" if needs else "repair_exhausted_api_error_non_content",
            needs,
            MAX_REPAIR_ATTEMPTS_API_ERROR,
        )

    if diagnosis in {"PARSE_FAILED", "JSON_MISSING_KEY"}:
        rescued_diag, rescued_likert, rescue_method = extract_from_raw_no_write(raw)

        if rescued_diag is not None:
            if is_exact_valid_i_dont_know(rescued_diag) or is_abstention_variant(rescued_diag):
                return _repair_status(
                    "cleanup_target_parse_to_abstention",
                    "no_paid_cleanup",
                    f"{diagnosis.lower()}_raw_reparse_to_abstention",
                    False,
                    0,
                    rescued_diag=rescued_diag,
                    rescued_likert=rescued_likert,
                    rescue_method=rescue_method,
                )

            if is_valid_likert_value(rescued_likert):
                return _repair_status(
                    "cleanup_target_parse_to_clean_diagnosis",
                    "no_paid_cleanup",
                    f"{diagnosis.lower()}_raw_reparse_to_clean_json",
                    False,
                    0,
                    rescued_diag=rescued_diag,
                    rescued_likert=rescued_likert,
                    rescue_method=rescue_method,
                )

            needs = attempts < MAX_REPAIR_ATTEMPTS_MALFORMED
            return _repair_status(
                "repair_target_parse_recovered_diag_bad_likert"
                if needs
                else "repair_exhausted_parse_recovered_diag_bad_likert",
                "paid_repair" if needs else "terminal",
                f"{diagnosis.lower()}_raw_has_diag_but_bad_likert",
                needs,
                MAX_REPAIR_ATTEMPTS_MALFORMED,
                rescued_diag=rescued_diag,
                rescued_likert=rescued_likert,
                rescue_method=rescue_method,
            )

        if raw.strip() == "":
            detail = "parse_failed_empty_raw"
        elif hit_max_tokens:
            detail = "parse_failed_hit_max_tokens"
        else:
            detail = "parse_failed_raw_not_recoverable"

        needs = attempts < MAX_REPAIR_ATTEMPTS_MALFORMED
        return _repair_status(
            f"repair_target_{detail}" if needs else f"repair_exhausted_{detail}",
            "paid_repair" if needs else "terminal",
            detail if needs else f"repair_exhausted_{detail}",
            needs,
            MAX_REPAIR_ATTEMPTS_MALFORMED,
        )

    if not is_valid_likert_value(likert):
        needs = attempts < MAX_REPAIR_ATTEMPTS_MALFORMED
        return _repair_status(
            "repair_target_invalid_or_missing_likert"
            if needs
            else "repair_exhausted_invalid_or_missing_likert",
            "paid_repair" if needs else "terminal",
            "invalid_or_missing_likert_with_diagnosis"
            if needs
            else "repair_exhausted_invalid_or_missing_likert",
            needs,
            MAX_REPAIR_ATTEMPTS_MALFORMED,
        )

    return _repair_status(
        "accepted_clean_diagnosis",
        "accepted",
        "accepted_clean_diagnosis",
        False,
        0,
    )


def _dataset_integrity_table(df, expected_case_ids, model_names):
    case_ids = df["Master_Case_ID"].astype(str) if "Master_Case_ID" in df.columns else pd.Series([], dtype=str)
    counts = case_ids.value_counts()
    duplicates = sorted(counts[counts > 1].index.tolist(), key=numeric_case_sort_key)
    expected = _normalize_expected_case_ids(expected_case_ids)
    actual = set(case_ids.tolist())
    missing = sorted(set(expected) - actual, key=numeric_case_sort_key) if expected else []
    extra = sorted(actual - set(expected), key=numeric_case_sort_key) if expected else []

    return pd.DataFrame([
        {"metric": "rows", "value": len(df)},
        {"metric": "unique_cases", "value": len(actual)},
        {"metric": "columns", "value": len(df.columns)},
        {"metric": "models_audited", "value": len(model_names)},
        {"metric": "expected_case_model_cells", "value": len(actual) * len(model_names)},
        {"metric": "duplicate_case_ids", "value": ", ".join(duplicates) if duplicates else "none"},
        {"metric": "missing_expected_case_ids", "value": ", ".join(missing) if missing else "none"},
        {"metric": "extra_case_ids", "value": ", ".join(extra) if extra else "none"},
    ])


def _audit_call_log_tables(call_log_df, audit_df):
    result = {
        "call_log_event_status": _empty_dataframe(["event", "status", "rows"]),
        "call_log_last_started": _empty_dataframe(["Master_Case_ID", "model", "timestamp_utc", "event", "status", "error"]),
        "call_log_imbalances": _empty_dataframe([]),
        "call_log_repeated": _empty_dataframe([]),
        "call_log_failed_cells": _empty_dataframe([]),
        "call_log_failed_but_now_ok": _empty_dataframe(["Master_Case_ID", "model"]),
        "call_log_current_problem_no_failed_log": _empty_dataframe(["Master_Case_ID", "model"]),
        "call_log_tail": _empty_dataframe([]),
    }
    required = {"Master_Case_ID", "model", "event", "status"}
    if call_log_df is None or not len(call_log_df) or not required.issubset(call_log_df.columns):
        return result

    calls = call_log_df.copy()
    calls["Master_Case_ID"] = calls["Master_Case_ID"].apply(normalize_case_id)
    calls["_event_upper"] = calls["event"].astype(str).str.upper()
    calls["_status_upper"] = calls["status"].astype(str).str.upper()

    result["call_log_event_status"] = (
        calls.groupby(["event", "status"], dropna=False)
        .size()
        .reset_index(name="rows")
    )

    if "timestamp_utc" in calls.columns:
        calls["_ts"] = pd.to_datetime(calls["timestamp_utc"], errors="coerce", utc=True)
        calls_sorted = calls.sort_values("_ts")
    else:
        calls["_ts"] = pd.NaT
        calls_sorted = calls.copy()

    last_events = calls_sorted.groupby(["Master_Case_ID", "model"], as_index=False).tail(1).copy()
    result["call_log_last_started"] = last_events[
        last_events["_event_upper"].str.endswith("STARTED")
    ].drop(columns=[c for c in ["_event_upper", "_status_upper", "_ts"] if c in last_events.columns], errors="ignore")

    grouped = calls.groupby(["Master_Case_ID", "model"]).agg(
        started_count=("_event_upper", lambda x: int(x.str.endswith("STARTED").sum())),
        finished_count=("_event_upper", lambda x: int(x.str.endswith("FINISHED").sum())),
        ok_count=("_status_upper", lambda x: int((x == "OK").sum())),
        failed_count=("_status_upper", lambda x: int((x == "FAILED").sum())),
        first_ts=("_ts", "min"),
        last_ts=("_ts", "max"),
    ).reset_index()
    grouped["started_minus_finished"] = grouped["started_count"] - grouped["finished_count"]

    result["call_log_imbalances"] = grouped[grouped["started_minus_finished"] != 0].copy()
    result["call_log_repeated"] = grouped[grouped["started_count"] > 1].copy()
    failed_cells = grouped[grouped["failed_count"] > 0].copy()
    result["call_log_failed_cells"] = failed_cells

    failed_pairs = set(zip(failed_cells["Master_Case_ID"].astype(str), failed_cells["model"].astype(str)))
    current_problem = audit_df[audit_df["bucket"].isin(["paid_repair", "limited_provider_retry", "terminal"])].copy()
    current_problem_pairs = set(zip(current_problem["Master_Case_ID"].astype(str), current_problem["model"].astype(str)))

    result["call_log_failed_but_now_ok"] = pd.DataFrame(
        sorted(failed_pairs - current_problem_pairs, key=lambda x: (numeric_case_sort_key(x[0]), x[1])),
        columns=["Master_Case_ID", "model"],
    )
    result["call_log_current_problem_no_failed_log"] = pd.DataFrame(
        sorted(current_problem_pairs - failed_pairs, key=lambda x: (numeric_case_sort_key(x[0]), x[1])),
        columns=["Master_Case_ID", "model"],
    )
    result["call_log_tail"] = calls.tail(30).drop(
        columns=[c for c in ["_event_upper", "_status_upper", "_ts"] if c in calls.columns],
        errors="ignore",
    )
    return result


def audit_benchmark_output(raw_csv, models=None, call_log_csv=None, expected_case_ids=None):
    """Read-only audit of benchmark output quality. Performs no writes or API calls."""
    if not os.path.exists(raw_csv):
        raise FileNotFoundError(f"Raw CSV not found: {raw_csv}")

    df = pd.read_csv(raw_csv, dtype={"Master_Case_ID": str})
    if "Master_Case_ID" not in df.columns:
        raise ValueError("Benchmark CSV must contain Master_Case_ID.")

    df["Master_Case_ID"] = df["Master_Case_ID"].apply(normalize_case_id)
    model_names = model_names_from_models(models)
    call_log_df = _load_call_log(call_log_csv)

    records = []
    for _, row in df.iterrows():
        case_id = str(row["Master_Case_ID"])
        associated = safe_str(row.get("Associated_Images", ""))
        image_sha = safe_str(row.get("Image_SHA256", ""))

        for model_name in model_names:
            attempts = get_repair_attempts_from_log(call_log_df, case_id, model_name)
            info = classify_cell_for_audit(row, model_name, attempts=attempts)

            raw = safe_str(row.get(f"Raw_Response_{model_name}", ""))
            completion_tokens = get_token_value(row, model_name, "Total_Tokens_Out")
            max_attempts = info.get("max_attempts", 0)

            records.append({
                "Master_Case_ID": case_id,
                "Associated_Images": associated,
                "Image_SHA256": image_sha,
                "model": model_name,
                "bucket": info.get("bucket", ""),
                "status": info.get("status", ""),
                "reason": info.get("reason", ""),
                "needs_api_repair": bool(info.get("needs_api_repair", False)),
                "repair_attempts_so_far": attempts,
                "max_attempts": max_attempts,
                "remaining_attempts": max(0, int(max_attempts) - int(attempts)),
                "diagnosis": safe_str(row.get(f"Diagnosis_{model_name}", "")),
                "likert": safe_str(row.get(f"Likert_{model_name}", "")),
                "provider": safe_str(row.get(f"Provider_{model_name}", "")),
                "timestamp_utc": safe_str(row.get(f"Timestamp_UTC_{model_name}", "")),
                "completion_tokens": completion_tokens,
                "prompt_tokens": get_token_value(row, model_name, "Prompt_Tokens"),
                "reasoning_tokens": get_token_value(row, model_name, "Reasoning_Tokens"),
                "raw_len": len(raw.strip()),
                "hit_max_tokens": completion_tokens >= MAX_OUTPUT_TOKENS,
                "raw_preview": compact_text(raw)[:300],
                "rescued_diag": info.get("rescued_diag", ""),
                "rescued_likert": info.get("rescued_likert", ""),
                "rescue_method": info.get("rescue_method", ""),
            })

    audit_df = pd.DataFrame(records)
    if audit_df.empty:
        audit_df = _empty_dataframe([
            "Master_Case_ID",
            "model",
            "bucket",
            "status",
            "reason",
            "needs_api_repair",
        ])

    repair_targets = audit_df[audit_df["needs_api_repair"] == True].copy()
    no_paid_cleanup = audit_df[audit_df["bucket"] == "no_paid_cleanup"].copy()
    analysis_flags = audit_df[audit_df["bucket"] == "analysis_flag"].copy()
    provider_blocks = audit_df[
        audit_df["reason"].astype(str).str.contains("provider_content_block", na=False)
    ].copy()

    problem = audit_df[
        audit_df["bucket"].isin([
            "no_paid_cleanup",
            "paid_repair",
            "limited_provider_retry",
            "analysis_flag",
            "terminal",
        ])
    ].copy()
    if problem.empty:
        problem_flags = _empty_dataframe([
            "model",
            "problem_cells",
            "empty_raw_cells",
            "max_token_cells",
            "mean_completion_tokens",
        ])
    else:
        problem_flags = problem.groupby("model").agg(
            problem_cells=("model", "size"),
            empty_raw_cells=("raw_len", lambda x: int((x == 0).sum())),
            max_token_cells=("hit_max_tokens", lambda x: int(x.sum())),
            mean_completion_tokens=("completion_tokens", "mean"),
        ).reset_index()

    abstentions = audit_df[
        audit_df["status"].isin([
            "accepted_i_dont_know",
            "analysis_flag_i_dont_know_non_null_likert",
            "analysis_flag_abstention_variant",
            "cleanup_target_parse_to_abstention",
        ])
    ].copy()
    abstention_summary = (
        abstentions["model"].value_counts().reset_index(name="abstention_like_cells")
        if len(abstentions)
        else _empty_dataframe(["model", "abstention_like_cells"])
    )
    if len(abstentions):
        abstention_summary = abstention_summary.rename(columns={"index": "model"})

    result = {
        "dataset_integrity": _dataset_integrity_table(df, expected_case_ids, model_names),
        "audit": audit_df,
        "bucket_summary": audit_df["bucket"].value_counts().reset_index(name="cells"),
        "status_summary": audit_df["status"].value_counts().reset_index(name="cells"),
        "repair_targets": repair_targets,
        "no_paid_cleanup": no_paid_cleanup,
        "analysis_flags": analysis_flags,
        "provider_content_blocks": provider_blocks,
        "problem_flags_by_model": problem_flags,
        "abstention_summary": abstention_summary,
    }
    result.update(_audit_call_log_tables(call_log_df, audit_df))
    return result


def is_grok_xhigh_rejection(model, error_text):
    """Detect likely rejection of reasoning.effort='xhigh' on base Grok 4.20."""
    text = str(error_text).lower()
    return (
        model["name"] == "grok_4_20"
        and "error code: 400" in text
        and (
            "reasoning" in text
            or "effort" in text
            or "unsupported" in text
            or "parameter" in text
        )
    )


def uses_native_openai(model):
    """Return True for models that should bypass OpenRouter."""
    return model.get("provider") == "openai"


def uses_native_anthropic(model):
    """Return True for models that should use the native Anthropic Messages API."""
    return model.get("provider") == "anthropic"


def _convert_content_for_anthropic(content_array):
    """Convert OpenAI-style content array to Anthropic Messages API format."""
    result = []
    for item in content_array:
        if item["type"] == "text":
            result.append({"type": "text", "text": item["text"]})
        elif item["type"] == "image_url":
            url = item["image_url"]["url"]
            header, data = url.split(",", 1)
            media_type = header.split(":")[1].split(";")[0]
            result.append({
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": data},
            })
    return result


def uses_native_google(model):
    """Return True for models that should use the native Google GenAI API."""
    return model.get("provider") == "google"


def _convert_content_for_gemini(content_array):
    """Convert OpenAI-style content array to google-genai Parts list."""
    parts = []
    for item in content_array:
        if item["type"] == "text":
            parts.append(item["text"])
        elif item["type"] == "image_url":
            url = item["image_url"]["url"]
            header, data = url.split(",", 1)
            mime_type = header.split(":")[1].split(";")[0]
            parts.append(
                google_genai_types.Part.from_bytes(
                    data=base64.b64decode(data),
                    mime_type=mime_type,
                )
            )
    return parts


def build_api_params(model, content_array, max_output_tokens, universal_temperature):
    """Build provider-specific request params for one model request."""
    if uses_native_anthropic(model):
        extra = model.get("extra") or {}
        params = {
            "model": model["id"],
            "max_tokens": max_output_tokens,
            "messages": [{"role": "user", "content": _convert_content_for_anthropic(content_array)}],
        }
        if "thinking" in extra:
            params["thinking"] = extra["thinking"]
            if "output_config" in extra:
                params["output_config"] = extra["output_config"]
            # temperature is incompatible with extended thinking
        else:
            params["temperature"] = universal_temperature
        return params

    if uses_native_google(model):
        extra = model.get("extra") or {}
        thinking_level = extra.get("thinking_level", "high")
        config = google_genai_types.GenerateContentConfig(
            max_output_tokens=max_output_tokens,
            temperature=universal_temperature,
            thinking_config=google_genai_types.ThinkingConfig(
                include_thoughts=True,
                thinking_level=thinking_level,
            ),
        )
        return {
            "model": model["id"],
            "contents": _convert_content_for_gemini(content_array),
            "config": config,
        }

    if uses_native_openai(model):
        api_params = {
            "model": model["id"],
            "messages": [{"role": "user", "content": content_array}],
            "max_completion_tokens": max_output_tokens,
        }

        extra = model.get("extra") or {}
        if extra.get("reasoning_effort"):
            api_params["reasoning_effort"] = extra["reasoning_effort"]

        return api_params

    api_params = {
        "model": model["id"],
        "messages": [{"role": "user", "content": content_array}],
        "max_tokens": max_output_tokens,
    }

    if model["id"] not in NO_TEMPERATURE_MODELS:
        api_params["temperature"] = universal_temperature

    if model.get("extra"):
        api_params["extra_body"] = model.get("extra")

    return api_params


def get_api_client(model, client, openai_client, anthropic_client=None, gemini_client=None):
    """Select the appropriate provider client for the given model."""
    if uses_native_anthropic(model):
        if anthropic_client is None:
            raise ValueError("anthropic_client is required for native Anthropic models.")
        return anthropic_client
    if uses_native_google(model):
        if gemini_client is None:
            raise ValueError("gemini_client is required for native Google models.")
        return gemini_client
    if uses_native_openai(model):
        if openai_client is None:
            raise ValueError("openai_client is required for native OpenAI models.")
        return openai_client
    return client


def build_image_index(image_folder):
    """Index benchmark image paths by normalized case ID."""
    image_paths = [
        str(p)
        for p in pathlib.Path(image_folder).rglob("*")
        if p.is_file() and p.suffix.lower() not in EXCLUDED_IMAGE_EXTENSIONS
    ]

    grouped = defaultdict(list)
    for path in image_paths:
        base_key = os.path.basename(path).split(".")[0]
        grouped[normalize_case_id(base_key)].append(path)

    for case_id in grouped:
        grouped[case_id].sort()

    return grouped


def rebuild_base_row(case_id, paths):
    """Build the non-model metadata columns for one benchmark case."""
    return {
        "Master_Case_ID": str(case_id),
        "Associated_Images": ", ".join(os.path.basename(p) for p in paths),
        "Image_SHA256": ", ".join(
            hashlib.sha256(open(p, "rb").read()).hexdigest()[:16] for p in paths
        ),
    }


def build_content_array(case_id, image_index, prompt=PROMPT):
    """Build the OpenAI-style multimodal content array for one case."""
    paths = image_index.get(str(case_id), [])
    if not paths:
        raise RuntimeError(f"No image paths found for case {case_id}")

    content_array = [{"type": "text", "text": prompt}]
    for path in paths:
        content_array.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{get_mime_type(path)};base64,{encode_image(path)}"
                },
            }
        )
    return content_array


def call_model(
    model,
    content_array,
    client,
    openai_client=None,
    anthropic_client=None,
    gemini_client=None,
    max_output_tokens=MAX_OUTPUT_TOKENS,
    universal_temperature=UNIVERSAL_TEMPERATURE,
    max_retries=3,
):
    """Call one model with transport retries and Grok xhigh fallback."""
    api_params = build_api_params(
        model,
        content_array,
        max_output_tokens,
        universal_temperature,
    )
    api_client = get_api_client(model, client, openai_client, anthropic_client, gemini_client)

    response = None
    last_error = "Unknown error occurred before execution"
    grok_fallback_used = False
    latency = 0

    for attempt in range(max_retries):
        try:
            t0 = time.time()
            if uses_native_anthropic(model):
                response = api_client.messages.create(**api_params)
            elif uses_native_google(model):
                response = api_client.models.generate_content(**api_params)
            else:
                response = api_client.chat.completions.create(**api_params)
            latency = round(time.time() - t0, 1)
            break
        except Exception as exc:
            last_error = str(exc)

            if is_grok_xhigh_rejection(model, last_error) and not grok_fallback_used:
                print("    Grok xhigh rejected; falling back to reasoning.enabled=True.")
                api_params["extra_body"] = {"reasoning": {"enabled": True}}
                grok_fallback_used = True
                response = None
                continue

            fatal_patterns = [
                "error code: 404",
                "error code: 400",
                "http 404",
                "http 400",
                "balance",
                "quota",
                "insufficient_quota",
            ]
            if any(pattern in last_error.lower() for pattern in fatal_patterns):
                break

            if attempt < max_retries - 1:
                delay = 5 * (2**attempt)
                print(f"    Attempt {attempt + 1} failed. Retrying in {delay}s.")
                time.sleep(delay)

    if response is None:
        raise RuntimeError(last_error)

    return response, latency, api_params, grok_fallback_used


def _logged_request_extra(model, api_params):
    if uses_native_anthropic(model):
        return {k: api_params[k] for k in ("thinking", "output_config") if k in api_params}
    if uses_native_google(model):
        return model.get("extra")
    return api_params.get("extra_body", None) if api_params else None


def extract_result(response, latency, api_params, grok_fallback_used, model):
    """Extract benchmark CSV fields from one provider response."""
    if uses_native_anthropic(model):
        raw_answer = ""
        raw_reasoning_text = ""
        for block in response.content:
            if block.type == "text":
                raw_answer = block.text.strip()
            elif block.type == "thinking":
                raw_reasoning_text = (raw_reasoning_text + block.thinking).strip()
        thoughts = raw_reasoning_text
        reasoning_details_text = ""
        reasoning_tokens = 0
        completion_tokens = getattr(response.usage, "output_tokens", 0) if response.usage else 0
        prompt_tokens = getattr(response.usage, "input_tokens", 0) if response.usage else 0
        provider_used = "Anthropic"
    elif uses_native_google(model):
        raw_answer = (response.text or "").strip()
        raw_reasoning_text = ""
        try:
            for part in response.candidates[0].content.parts:
                if getattr(part, "thought", False) and part.text:
                    raw_reasoning_text += part.text
            raw_reasoning_text = raw_reasoning_text.strip()
        except (AttributeError, IndexError):
            pass
        thoughts = raw_reasoning_text
        reasoning_details_text = ""
        usage_meta = response.usage_metadata
        prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) if usage_meta else 0
        completion_tokens = getattr(usage_meta, "candidates_token_count", 0) if usage_meta else 0
        reasoning_tokens = getattr(usage_meta, "thoughts_token_count", 0) if usage_meta else 0
        provider_used = "Google"
    else:
        msg = response.choices[0].message
        raw_answer = msg.content.strip() if getattr(msg, "content", None) else ""

        raw_reasoning_text = ""
        raw_reasoning = getattr(msg, "reasoning", None)
        if raw_reasoning is not None:
            raw_reasoning_text = str(raw_reasoning).strip()
        elif hasattr(msg, "model_extra") and msg.model_extra and "reasoning" in msg.model_extra:
            ext_reasoning = msg.model_extra["reasoning"]
            if ext_reasoning is not None:
                raw_reasoning_text = str(ext_reasoning).strip()

        reasoning_details_obj = getattr(msg, "reasoning_details", None)
        if reasoning_details_obj is None and hasattr(msg, "model_extra") and msg.model_extra:
            reasoning_details_obj = msg.model_extra.get("reasoning_details")

        reasoning_details_text = ""
        if reasoning_details_obj:
            reasoning_details_text = json.dumps(
                make_json_safe(reasoning_details_obj),
                ensure_ascii=False,
            )

        if raw_reasoning_text and reasoning_details_text:
            thoughts = raw_reasoning_text + "\n\n[reasoning_details]\n" + reasoning_details_text
        elif reasoning_details_text:
            thoughts = reasoning_details_text
        else:
            thoughts = raw_reasoning_text

        reasoning_tokens = 0
        completion_tokens = 0
        prompt_tokens = 0
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            completion_tokens = getattr(usage, "completion_tokens", 0)
            prompt_tokens = getattr(usage, "prompt_tokens", 0)

            if hasattr(usage, "completion_tokens_details") and usage.completion_tokens_details:
                details = usage.completion_tokens_details
                if hasattr(details, "reasoning_tokens"):
                    reasoning_tokens = details.reasoning_tokens
                elif isinstance(details, dict):
                    reasoning_tokens = details.get("reasoning_tokens", 0)
                elif hasattr(details, "__dict__"):
                    reasoning_tokens = vars(details).get("reasoning_tokens", 0)

        provider_used = "OpenAI" if uses_native_openai(model) else "UNKNOWN"
        if (
            not uses_native_openai(model)
            and hasattr(response, "model_extra")
            and response.model_extra
        ):
            provider_used = response.model_extra.get("provider", "UNKNOWN")

    diag, likert = extract_json_safely(raw_answer)
    name = model["name"]

    return {
        f"Diagnosis_{name}": diag,
        f"Likert_{name}": likert,
        f"Prompt_Tokens_{name}": prompt_tokens,
        f"Total_Tokens_Out_{name}": completion_tokens,
        f"Reasoning_Tokens_{name}": reasoning_tokens,
        f"Latency_{name}": latency,
        f"Provider_{name}": provider_used,
        f"Timestamp_UTC_{name}": datetime.now(timezone.utc).isoformat(),
        f"Reasoning_{name}": thoughts,
        f"Reasoning_Raw_{name}": raw_reasoning_text,
        f"Reasoning_Details_{name}": reasoning_details_text,
        f"Actual_Request_Extra_{name}": json.dumps(
            _logged_request_extra(model, api_params),
            ensure_ascii=False,
        ),
        f"Grok_Fallback_Used_{name}": grok_fallback_used if name == "grok_4_20" else "",
        f"OpenRouter_Response_Model_{name}": getattr(response, "model", ""),
        f"Usage_JSON_{name}": json.dumps(
            make_json_safe(getattr(response, "usage", None)),
            ensure_ascii=False,
        ),
        f"Raw_Response_{name}": raw_answer[:2000],
    }


def failed_result(error, model, api_params=None, grok_fallback_used=False):
    """Build benchmark CSV fields for one failed model call."""
    name = model["name"]
    full_error = str(error)

    return {
        f"Diagnosis_{name}": "API_ERROR",
        f"Likert_{name}": "ERROR",
        f"Prompt_Tokens_{name}": 0,
        f"Total_Tokens_Out_{name}": 0,
        f"Reasoning_Tokens_{name}": 0,
        f"Latency_{name}": 0,
        f"Provider_{name}": "ERROR",
        f"Timestamp_UTC_{name}": datetime.now(timezone.utc).isoformat(),
        f"Reasoning_{name}": full_error,
        f"Reasoning_Raw_{name}": "",
        f"Reasoning_Details_{name}": "",
        f"Actual_Request_Extra_{name}": json.dumps(
            _logged_request_extra(model, api_params) if api_params else None,
            ensure_ascii=False,
        ),
        f"Grok_Fallback_Used_{name}": grok_fallback_used if name == "grok_4_20" else "",
        f"OpenRouter_Response_Model_{name}": "",
        f"Usage_JSON_{name}": "",
        f"Raw_Response_{name}": full_error[:2000],
    }


def assert_schema_stable(df, reference_columns, context=""):
    """Raise if dataframe columns differ from the reference schema."""
    current_columns = list(df.columns)
    if current_columns != list(reference_columns):
        prefix = f"{context}: " if context else ""
        raise ValueError(
            f"{prefix}benchmark schema changed. "
            f"Expected {len(reference_columns)} columns, got {len(current_columns)}."
        )


def build_repair_plan(df, models=None, repair_log_df=None, image_index=None):
    """Build a dataframe of case-model cells eligible for targeted repair."""
    if "Master_Case_ID" not in df.columns:
        raise ValueError("Benchmark dataframe must contain Master_Case_ID.")

    work_df = df.copy()
    work_df["Master_Case_ID"] = work_df["Master_Case_ID"].apply(normalize_case_id)
    repair_log_df = repair_log_df if repair_log_df is not None else pd.DataFrame()
    model_by_name = {m["name"]: m for m in (models or MODELS)}
    rows = []

    for _, row in work_df.iterrows():
        case_id = str(row["Master_Case_ID"])
        for model_name, model in model_by_name.items():
            attempts = get_repair_attempts_from_log(repair_log_df, case_id, model_name)
            info = classify_cell_for_audit(row, model_name, attempts=attempts)
            if not info.get("needs_api_repair"):
                continue

            paths = image_index.get(case_id, []) if image_index is not None else []
            rows.append({
                "Master_Case_ID": case_id,
                "model": model_name,
                "model_id": model["id"],
                "status": info.get("status", ""),
                "reason": info.get("reason", ""),
                "repair_attempts_so_far": attempts,
                "max_attempts": info.get("max_attempts", 0),
                "remaining_attempts": max(0, int(info.get("max_attempts", 0)) - attempts),
                "has_images": bool(paths) if image_index is not None else "",
            })

    return pd.DataFrame(rows)


def _default_repair_path(input_csv):
    return _csv_sibling_path(input_csv, "_REPAIRED")


def _default_repair_log_path(output_csv):
    return _csv_sibling_path(output_csv, "_REPAIR_CALL_LOG")


def _default_repair_plan_path(output_csv):
    return _csv_sibling_path(output_csv, "_REPAIR_PLAN")


def _append_log_row(log_df, row):
    return pd.concat([log_df, pd.DataFrame([row])], ignore_index=True, sort=False)


def _write_repair_progress(
    df,
    reference_columns,
    output_csv,
    repair_log_df,
    repair_call_log_csv,
    numbered=False,
    backup_dir=None,
):
    assert_schema_stable(df, reference_columns, context="before repair save")
    numbered_path = save_benchmark_progress(
        df[reference_columns].copy(),
        output_csv,
        numbered=numbered,
        backup_dir=backup_dir,
    )
    if repair_call_log_csv:
        atomic_to_csv(repair_log_df, repair_call_log_csv)
    return numbered_path


def run_targeted_repair(
    client,
    image_folder,
    input_csv,
    output_csv=None,
    repair_call_log_csv=None,
    repair_plan_csv=None,
    confirmation="NO",
    models=None,
    prompt=PROMPT,
    max_output_tokens=MAX_OUTPUT_TOKENS,
    universal_temperature=UNIVERSAL_TEMPERATURE,
    openai_client=None,
    anthropic_client=None,
    gemini_client=None,
    repair_backup_interval=CHECKPOINT_CASE_INTERVAL,
    backup_dir=None,
):
    """Run schema-stable targeted repair for invalid or failed case-model cells."""
    if confirmation not in {"NO", "YES_REPAIR_10", "YES_REPAIR_ALL"}:
        raise ValueError("confirmation must be one of: NO, YES_REPAIR_10, YES_REPAIR_ALL")

    output_csv = output_csv or _default_repair_path(input_csv)
    repair_call_log_csv = repair_call_log_csv or _default_repair_log_path(output_csv)
    repair_plan_csv = repair_plan_csv or _default_repair_plan_path(output_csv)
    max_api_calls = {
        "NO": 0,
        "YES_REPAIR_10": 10,
        "YES_REPAIR_ALL": None,
    }[confirmation]

    if not os.path.exists(input_csv):
        raise FileNotFoundError(f"Repair input CSV not found: {input_csv}")

    image_index = build_image_index(image_folder)
    df_repair = pd.read_csv(input_csv, dtype={"Master_Case_ID": str}).astype("object")
    if "Master_Case_ID" not in df_repair.columns:
        raise ValueError("Repair input CSV must contain Master_Case_ID.")
    reference_columns = list(df_repair.columns)
    repair_log_df = _load_call_log(repair_call_log_csv)
    models = models or MODELS
    model_by_name = {m["name"]: m for m in models}

    no_paid_cleanup_plan_df = build_no_paid_cleanup_plan(df_repair, models=models)
    repair_plan_df = build_repair_plan(
        df_repair,
        models=models,
        repair_log_df=repair_log_df,
        image_index=image_index,
    )

    print("")
    print("=== TARGETED REPAIR PLAN ===")
    print(f"Input CSV: {input_csv}")
    print(f"Output CSV: {output_csv}")
    print(f"Repair call log: {repair_call_log_csv}")
    print(f"No-API cleanup rows / affected cells: {len(no_paid_cleanup_plan_df)}")
    if len(no_paid_cleanup_plan_df):
        print("No-API cleanup reasons:")
        print(no_paid_cleanup_plan_df["reason"].value_counts().to_string())
    print(f"Repair plan rows / affected cells: {len(repair_plan_df)}")
    if len(repair_plan_df):
        print("Repair reasons:")
        print(repair_plan_df["reason"].value_counts().to_string())

    if max_api_calls == 0:
        print("confirmation was NO. No API calls were made, no cleanups were applied, and no files were written.")
        return {
            "df": df_repair,
            "repair_plan": repair_plan_df,
            "no_paid_cleanup_plan": no_paid_cleanup_plan_df,
            "repair_log": repair_log_df,
            "remaining_repair_plan": repair_plan_df,
            "remaining_no_paid_cleanup_plan": no_paid_cleanup_plan_df,
            "api_calls_this_run": 0,
            "no_paid_cleanups_applied": 0,
            "output_csv": output_csv,
            "repair_call_log_csv": repair_call_log_csv,
            "repair_plan_csv": repair_plan_csv,
        }

    no_paid_cleanups_applied = apply_no_paid_cleanups(df_repair, models=models, verbose=True)
    if no_paid_cleanups_applied:
        print(f"No-API cleanups applied: {no_paid_cleanups_applied}")
        repair_plan_df = build_repair_plan(
            df_repair,
            models=models,
            repair_log_df=repair_log_df,
            image_index=image_index,
        )

    atomic_to_csv(repair_plan_df, repair_plan_csv)
    _write_repair_progress(
        df_repair,
        reference_columns,
        output_csv,
        repair_log_df,
        repair_call_log_csv,
        numbered=False,
        backup_dir=backup_dir,
    )

    api_calls_this_run = 0
    stop_due_to_limit = False

    for _, target in repair_plan_df.iterrows():
        if stop_due_to_limit:
            break

        case_id = str(target["Master_Case_ID"])
        model_name = str(target["model"])
        model = model_by_name[model_name]
        matches = df_repair.index[case_id_match_mask(df_repair, case_id)].tolist()
        if not matches:
            print(f"SKIP missing case row: case {case_id} | {model_name}")
            continue
        df_idx = matches[0]
        paths_for_case = image_index.get(case_id, [])
        if not paths_for_case:
            print(f"SKIP no image paths found: case {case_id} | {model_name}")
            continue

        while True:
            current_row = df_repair.loc[df_idx]
            attempts = get_repair_attempts_from_log(repair_log_df, case_id, model_name)
            info = classify_cell_for_audit(current_row, model_name, attempts=attempts)
            if not info.get("needs_api_repair"):
                print(f"SKIP already acceptable/exhausted: case {case_id} | {model_name} | {info.get('reason')}")
                break

            if f"Diagnosis_{model_name}" not in df_repair.columns:
                print(f"SKIP schema missing Diagnosis_{model_name}; repair would change schema.")
                break

            if max_api_calls is not None and api_calls_this_run >= max_api_calls:
                stop_due_to_limit = True
                break

            try:
                content_array = build_content_array(case_id, image_index, prompt=prompt)
            except Exception as exc:
                print(f"SKIP unable to build content: case {case_id} | {model_name} | {exc}")
                break

            repair_attempt_number = attempts + 1
            reason = info.get("reason", "")
            print(
                f"[repair API {api_calls_this_run + 1}] "
                f"case {case_id} | {model_name} | "
                f"reason={reason} | attempt {repair_attempt_number}/{info.get('max_attempts')}...",
                end="",
            )

            start_log = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "Master_Case_ID": case_id,
                "model": model_name,
                "event": "REPAIR_STARTED",
                "reason": reason,
                "repair_attempt_number": repair_attempt_number,
                "status": "",
                "post_repair_status": "",
                "latency": "",
                "completion_tokens": "",
                "prompt_tokens": "",
                "error": "",
            }
            repair_log_df = _append_log_row(repair_log_df, start_log)
            _write_repair_progress(
                df_repair,
                reference_columns,
                output_csv,
                repair_log_df,
                repair_call_log_csv,
                numbered=False,
                backup_dir=backup_dir,
            )

            api_params_for_error = None
            grok_fallback_used_for_error = False
            finish_status = "OK"

            try:
                response, latency, api_params, grok_fallback_used = call_model(
                    model,
                    content_array,
                    client=client,
                    openai_client=openai_client,
                    anthropic_client=anthropic_client,
                    gemini_client=gemini_client,
                    max_output_tokens=max_output_tokens,
                    universal_temperature=universal_temperature,
                )
                api_params_for_error = api_params
                grok_fallback_used_for_error = grok_fallback_used
                result = extract_result(response, latency, api_params, grok_fallback_used, model)

                for key, value in result.items():
                    if key in df_repair.columns:
                        df_repair.at[df_idx, key] = value

                print(
                    f" OK ({result.get(f'Latency_{model_name}', '')}s | "
                    f"{result.get(f'Total_Tokens_Out_{model_name}', '')} out / "
                    f"{result.get(f'Prompt_Tokens_{model_name}', '')} in | "
                    f"diag={result.get(f'Diagnosis_{model_name}', '')} | "
                    f"likert={result.get(f'Likert_{model_name}', '')})"
                )

            except KeyboardInterrupt:
                interrupt_log = {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "Master_Case_ID": case_id,
                    "model": model_name,
                    "event": "REPAIR_INTERRUPTED",
                    "reason": reason,
                    "repair_attempt_number": repair_attempt_number,
                    "status": "UNKNOWN_IF_CHARGED",
                    "post_repair_status": "interrupted",
                    "latency": "",
                    "completion_tokens": "",
                    "prompt_tokens": "",
                    "error": "KeyboardInterrupt during repair API call",
                }
                repair_log_df = _append_log_row(repair_log_df, interrupt_log)
                _write_repair_progress(
                    df_repair,
                    reference_columns,
                    output_csv,
                    repair_log_df,
                    repair_call_log_csv,
                    numbered=True,
                    backup_dir=backup_dir,
                )
                print(" INTERRUPTED. Progress saved.")
                raise

            except Exception as exc:
                result = failed_result(
                    error=exc,
                    model=model,
                    api_params=api_params_for_error,
                    grok_fallback_used=grok_fallback_used_for_error,
                )
                for key, value in result.items():
                    if key in df_repair.columns:
                        df_repair.at[df_idx, key] = value
                finish_status = "FAILED"
                print(f" FAILED: {str(exc)[:200]}")

            attempts_after = get_repair_attempts_from_log(repair_log_df, case_id, model_name)
            post_info = classify_cell_for_audit(
                df_repair.loc[df_idx],
                model_name,
                attempts=attempts_after,
            )
            if apply_no_paid_cleanup_to_cell(df_repair, df_idx, model_name, post_info):
                no_paid_cleanups_applied += 1
                post_info = classify_cell_for_audit(
                    df_repair.loc[df_idx],
                    model_name,
                    attempts=attempts_after,
                )
            post_repair_status = post_info.get("reason", "")

            finish_log = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "Master_Case_ID": case_id,
                "model": model_name,
                "event": "REPAIR_FINISHED",
                "reason": reason,
                "repair_attempt_number": repair_attempt_number,
                "status": finish_status,
                "post_repair_status": post_repair_status,
                "latency": result.get(f"Latency_{model_name}", "") if isinstance(result, dict) else "",
                "completion_tokens": result.get(f"Total_Tokens_Out_{model_name}", "") if isinstance(result, dict) else "",
                "prompt_tokens": result.get(f"Prompt_Tokens_{model_name}", "") if isinstance(result, dict) else "",
                "error": "" if finish_status == "OK" else safe_str(result.get(f"Raw_Response_{model_name}", ""))[:1000],
            }
            repair_log_df = _append_log_row(repair_log_df, finish_log)
            api_calls_this_run += 1

            make_numbered = (
                repair_backup_interval > 0
                and api_calls_this_run % repair_backup_interval == 0
            )
            _write_repair_progress(
                df_repair,
                reference_columns,
                output_csv,
                repair_log_df,
                repair_call_log_csv,
                numbered=make_numbered,
                backup_dir=backup_dir,
            )

            if not post_info.get("needs_api_repair"):
                break

    final_backup = _write_repair_progress(
        df_repair,
        reference_columns,
        output_csv,
        repair_log_df,
        repair_call_log_csv,
        numbered=True,
        backup_dir=backup_dir,
    )
    remaining_repair_plan = build_repair_plan(
        df_repair,
        models=models,
        repair_log_df=repair_log_df,
        image_index=image_index,
    )
    remaining_no_paid_cleanup_plan = build_no_paid_cleanup_plan(df_repair, models=models)

    print("")
    print("Targeted repair chunk complete.")
    print(f"Output CSV: {output_csv}")
    print(f"Repair call log: {repair_call_log_csv}")
    print(f"Final numbered backup: {final_backup}")
    print(f"No-API cleanups applied: {no_paid_cleanups_applied}")
    print(f"Remaining no-API cleanup targets: {len(remaining_no_paid_cleanup_plan)}")
    print(f"Remaining repair targets: {len(remaining_repair_plan)}")
    assert_schema_stable(df_repair, reference_columns, context="final repair")

    return {
        "df": df_repair,
        "repair_plan": repair_plan_df,
        "no_paid_cleanup_plan": no_paid_cleanup_plan_df,
        "repair_log": repair_log_df,
        "remaining_repair_plan": remaining_repair_plan,
        "remaining_no_paid_cleanup_plan": remaining_no_paid_cleanup_plan,
        "api_calls_this_run": api_calls_this_run,
        "no_paid_cleanups_applied": no_paid_cleanups_applied,
        "output_csv": output_csv,
        "repair_call_log_csv": repair_call_log_csv,
        "repair_plan_csv": repair_plan_csv,
    }


def _sort_benchmark_df(df):
    if not len(df) or "Master_Case_ID" not in df.columns:
        return df
    return df.sort_values(
        by="Master_Case_ID",
        key=lambda s: s.map(numeric_case_sort_key),
    ).reset_index(drop=True)


def _load_or_initialize_benchmark_output(output_csv, resume=True):
    if resume and os.path.exists(output_csv):
        df = pd.read_csv(output_csv, dtype={"Master_Case_ID": str}).astype("object")
        if "Master_Case_ID" not in df.columns:
            raise ValueError(f"Existing output CSV lacks Master_Case_ID: {output_csv}")
        print(f"Resuming existing benchmark output: {output_csv} | rows={len(df)}")
        return _sort_benchmark_df(df)

    return pd.DataFrame(columns=["Master_Case_ID", "Associated_Images", "Image_SHA256"]).astype("object")


def _get_or_create_case_row(df, case_id):
    case_id = normalize_case_id(case_id)
    if "Master_Case_ID" not in df.columns:
        df["Master_Case_ID"] = ""

    matches = df.index[case_id_match_mask(df, case_id)].tolist()
    if matches:
        return df, matches[0]

    df = pd.concat(
        [df, pd.DataFrame([{"Master_Case_ID": str(case_id)}])],
        ignore_index=True,
        sort=False,
    ).astype("object")
    return df, df.index[-1]


def run_benchmark(
    client,
    image_folder,
    output_csv,
    test_limit=None,
    models=None,
    prompt=PROMPT,
    max_output_tokens=MAX_OUTPUT_TOKENS,
    universal_temperature=UNIVERSAL_TEMPERATURE,
    openai_client=None,
    anthropic_client=None,
    gemini_client=None,
    resume=True,
    backup_dir=None,
):
    """Run the RadLE benchmark, resuming existing clean cells when possible."""
    models = models or MODELS
    image_index = build_image_index(image_folder)
    items = sorted(image_index.items(), key=lambda x: numeric_case_sort_key(x[0]))

    if test_limit:
        print(f"TEST MODE: Running on first {test_limit} cases only.")
        items = items[:test_limit]

    df = _load_or_initialize_benchmark_output(output_csv, resume=resume)
    api_calls_this_run = 0
    print(f"Processing {len(items)} unique cases across {len(models)} models...\n")

    for idx, (case_id, paths) in enumerate(items, 1):
        print(f"[{idx}/{len(items)}] Case ID: {case_id} ({len(paths)} images)")

        df, df_idx = _get_or_create_case_row(df, case_id)
        base_row = rebuild_base_row(case_id, paths)
        for key, value in base_row.items():
            if key == "Master_Case_ID" and safe_str(df.at[df_idx, key]).strip():
                continue
            df.at[df_idx, key] = value

        content_array = None

        for model in models:
            model_name = model["name"]
            row = df.loc[df_idx]
            info = classify_cell_for_audit(row, model_name, attempts=0)

            if info.get("bucket") == "no_paid_cleanup":
                if apply_no_paid_cleanup_to_cell(df, df_idx, model_name, info):
                    print(f"  -> {model_name}... CLEANUP ({info.get('reason')})")
                    continue
                print(f"  -> {model_name}... CLEANUP_UNAVAILABLE; rerunning")
            elif not info.get("needs_api_repair"):
                print(f"  -> {model_name}... SKIP ({info.get('reason')})")
                continue

            print(f"  -> {model_name}...", end="")
            api_params_for_error = None
            grok_fallback_used_for_error = False
            try:
                if content_array is None:
                    content_array = build_content_array(case_id, image_index, prompt=prompt)

                response, latency, api_params, grok_fallback_used = call_model(
                    model,
                    content_array,
                    client=client,
                    openai_client=openai_client,
                    anthropic_client=anthropic_client,
                    gemini_client=gemini_client,
                    max_output_tokens=max_output_tokens,
                    universal_temperature=universal_temperature,
                )
                api_params_for_error = api_params
                grok_fallback_used_for_error = grok_fallback_used
                result = extract_result(response, latency, api_params, grok_fallback_used, model)

                for key, value in result.items():
                    df.at[df_idx, key] = value

                completion_tokens = result.get(f"Total_Tokens_Out_{model_name}", 0)
                prompt_tokens = result.get(f"Prompt_Tokens_{model_name}", 0)
                latency = result.get(f"Latency_{model_name}", 0)
                tps = round(completion_tokens / latency, 1) if latency > 0 else 0
                print(
                    f" OK ({latency}s | {completion_tokens} out / "
                    f"{prompt_tokens} in | {tps} tok/sec)"
                )

            except Exception as exc:
                result = failed_result(
                    error=exc,
                    model=model,
                    api_params=api_params_for_error,
                    grok_fallback_used=grok_fallback_used_for_error,
                )
                for key, value in result.items():
                    df.at[df_idx, key] = value
                print(f" Failed! API Response: {str(exc)}")

            api_calls_this_run += 1

        df = _sort_benchmark_df(df)

        if idx % CHECKPOINT_CASE_INTERVAL == 0:
            numbered_path = save_benchmark_progress(
                df,
                output_csv,
                numbered=True,
                backup_dir=backup_dir,
            )
            print(f"  Checkpoint saved after {idx} cases: {numbered_path}")

    df = _sort_benchmark_df(df)
    final_backup = save_benchmark_progress(
        df,
        output_csv,
        numbered=True,
        backup_dir=backup_dir,
    )
    print(f"\nComplete! Data saved to {output_csv}")
    print(f"Final numbered backup: {final_backup}")
    print(f"API calls made this run: {api_calls_this_run}")
    return df


def file_sha256(path):
    """Return SHA256 for a file."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def promote_final_results(
    source_csv,
    final_csv,
    manifest_json=None,
    run_id=None,
    source_label=None,
    metadata=None,
):
    """Copy the chosen raw/repaired CSV to the private final file and write a manifest."""
    if not os.path.exists(source_csv):
        raise FileNotFoundError(f"Final source CSV not found: {source_csv}")

    final_dir = os.path.dirname(final_csv)
    if final_dir:
        os.makedirs(final_dir, exist_ok=True)
    shutil.copy2(source_csv, final_csv)

    df = pd.read_csv(final_csv, dtype={"Master_Case_ID": str})
    manifest = {
        "run_id": run_id or "",
        "source_label": source_label or "",
        "source_csv": str(source_csv),
        "final_csv": str(final_csv),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "case_count": int(df["Master_Case_ID"].nunique()) if "Master_Case_ID" in df.columns else None,
        "sha256": file_sha256(final_csv),
    }
    if metadata:
        manifest.update(metadata)

    if manifest_json:
        manifest_dir = os.path.dirname(manifest_json)
        if manifest_dir:
            os.makedirs(manifest_dir, exist_ok=True)
        with open(manifest_json, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=False)

    return manifest


def _case_uid_map(case_ids, prefix="case_"):
    unique_case_ids = sorted(
        {normalize_case_id(case_id) for case_id in case_ids},
        key=numeric_case_sort_key,
    )
    width = max(3, len(str(len(unique_case_ids))))
    return {
        case_id: f"{prefix}{idx:0{width}d}"
        for idx, case_id in enumerate(unique_case_ids, 1)
    }


def _first_present_value(row, columns):
    for col in columns:
        if col in row.index:
            value = row.get(col)
            try:
                if pd.isna(value):
                    continue
            except Exception:
                pass
            if safe_str(value).strip() != "":
                return value
    return ""


def public_error_class_from_reason(reason):
    """Return a coarse public error class without exposing provider error text."""
    text = safe_str(reason).lower()
    if text == "" or text.startswith("accepted"):
        return ""
    if "provider_content_block" in text or "content_block" in text:
        return "PROVIDER_CONTENT_BLOCK"
    if "no endpoints found" in text or "404" in text or "model unavailable" in text:
        return "MODEL_UNAVAILABLE"
    if "400" in text or "bad request" in text:
        return "BAD_REQUEST"
    if "quota" in text or "balance" in text or "insufficient" in text:
        return "QUOTA_OR_BALANCE"
    if "api_error" in text or "error code" in text or "http" in text:
        return "API_ERROR"
    if "parse_failed" in text or "json_missing_key" in text or "malformed" in text:
        return "MALFORMED_JSON"
    if "invalid_or_missing_likert" in text or "bad_likert" in text:
        return "INVALID_LIKERT"
    if "missing" in text or "empty" in text:
        return "MISSING_OUTPUT"
    if "exhausted" in text or "terminal" in text:
        return "REPAIR_EXHAUSTED"
    return "OTHER_ERROR"


def build_public_case_model_table(
    results_csv,
    models=None,
    run_id=None,
    case_prefix="case_",
    case_uid_map=None,
):
    """Build a public case-model table without diagnoses, raw responses, or image names."""
    if not os.path.exists(results_csv):
        raise FileNotFoundError(f"Results CSV not found: {results_csv}")

    df = pd.read_csv(results_csv, dtype={"Master_Case_ID": str})
    if "Master_Case_ID" not in df.columns:
        raise ValueError("Results CSV must contain Master_Case_ID.")

    model_names = model_names_from_models(models)
    uid_map = case_uid_map or _case_uid_map(df["Master_Case_ID"], prefix=case_prefix)
    uid_map = {normalize_case_id(k): v for k, v in uid_map.items()}
    records = []

    for _, row in df.iterrows():
        case_id = normalize_case_id(row["Master_Case_ID"])
        for model_name in model_names:
            info = classify_cell_for_audit(row, model_name, attempts=0)
            reason = info.get("reason", "")
            diagnosis = safe_str(row.get(f"Diagnosis_{model_name}", ""))
            likert = row.get(f"Likert_{model_name}", "")
            response_valid = info.get("bucket") == "accepted"
            abstained = is_exact_valid_i_dont_know(diagnosis) or is_abstention_variant(diagnosis)

            records.append({
                "run_id": run_id or "",
                "case_uid": uid_map.get(case_id, ""),
                "model": model_name,
                "provider": safe_str(row.get(f"Provider_{model_name}", "")),
                "response_valid": bool(response_valid),
                "abstained": bool(abstained),
                "likert_score": normalize_likert_for_output(likert) if is_valid_likert_value(likert) else "",
                "prompt_tokens": get_token_value(row, model_name, "Prompt_Tokens"),
                "completion_tokens": get_token_value(row, model_name, "Total_Tokens_Out"),
                "reasoning_tokens": get_token_value(row, model_name, "Reasoning_Tokens"),
                "latency_seconds": get_token_value(row, model_name, "Latency"),
                "score_binary": _first_present_value(row, [
                    f"Score_Binary_{model_name}",
                    f"Binary_Score_{model_name}",
                    f"Correct_{model_name}",
                    f"Accuracy_{model_name}",
                ]),
                "score_likert": _first_present_value(row, [
                    f"Score_Likert_{model_name}",
                    f"Human_Score_{model_name}",
                    f"Scoring_Likert_{model_name}",
                ]),
                "error_class": public_error_class_from_reason(reason),
            })

    return pd.DataFrame(records)


def build_public_model_summary(public_case_model_df):
    """Summarize sanitized public case-model rows by model/provider."""
    if public_case_model_df.empty:
        return pd.DataFrame()

    df = public_case_model_df.copy()
    for col in [
        "likert_score",
        "prompt_tokens",
        "completion_tokens",
        "reasoning_tokens",
        "latency_seconds",
        "score_binary",
        "score_likert",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    summary = df.groupby(["run_id", "model", "provider"], dropna=False).agg(
        n_cases=("case_uid", "nunique"),
        valid_response_rate=("response_valid", "mean"),
        abstention_rate=("abstained", "mean"),
        mean_likert_score=("likert_score", "mean"),
        mean_latency_seconds=("latency_seconds", "mean"),
        mean_prompt_tokens=("prompt_tokens", "mean"),
        mean_completion_tokens=("completion_tokens", "mean"),
        mean_reasoning_tokens=("reasoning_tokens", "mean"),
        mean_score_binary=("score_binary", "mean"),
        mean_score_likert=("score_likert", "mean"),
    ).reset_index()

    return summary


def build_public_sanitized_call_log(
    call_log_csv,
    run_id=None,
    case_prefix="case_",
    case_uid_map=None,
):
    """Build a public call log without raw provider errors or image identifiers."""
    if not call_log_csv or not os.path.exists(call_log_csv):
        return pd.DataFrame()

    call_log_df = _load_call_log(call_log_csv)
    if call_log_df.empty:
        return pd.DataFrame()

    if case_uid_map:
        uid_map = {normalize_case_id(k): v for k, v in case_uid_map.items()}
    elif "Master_Case_ID" in call_log_df.columns:
        uid_map = _case_uid_map(call_log_df["Master_Case_ID"], prefix=case_prefix)
    else:
        uid_map = {}

    records = []
    for _, row in call_log_df.iterrows():
        case_id = normalize_case_id(row.get("Master_Case_ID", ""))
        error_text = safe_str(row.get("error", ""))
        reason = safe_str(row.get("reason", ""))
        records.append({
            "run_id": run_id or "",
            "case_uid": uid_map.get(case_id, ""),
            "model": safe_str(row.get("model", "")),
            "event": safe_str(row.get("event", "")),
            "status": safe_str(row.get("status", "")),
            "repair_reason_class": public_error_class_from_reason(reason),
            "post_repair_status": safe_str(row.get("post_repair_status", "")),
            "error_class": public_error_class_from_reason(error_text or reason),
            "repair_attempt_number": safe_str(row.get("repair_attempt_number", "")),
            "latency_seconds": safe_str(row.get("latency", "")),
            "prompt_tokens": safe_str(row.get("prompt_tokens", "")),
            "completion_tokens": safe_str(row.get("completion_tokens", "")),
            "timestamp_utc": safe_str(row.get("timestamp_utc", "")),
        })

    return pd.DataFrame(records)


def export_public_release_tables(
    results_csv,
    output_dir,
    models=None,
    call_log_csv=None,
    run_id=None,
    case_prefix="case_",
):
    """Write sanitized public release tables without answers or raw model text."""
    os.makedirs(output_dir, exist_ok=True)
    source_df = pd.read_csv(results_csv, dtype={"Master_Case_ID": str})
    if "Master_Case_ID" not in source_df.columns:
        raise ValueError("Results CSV must contain Master_Case_ID.")
    case_uid_map = _case_uid_map(source_df["Master_Case_ID"], prefix=case_prefix)

    case_model_df = build_public_case_model_table(
        results_csv,
        models=models,
        run_id=run_id,
        case_prefix=case_prefix,
        case_uid_map=case_uid_map,
    )
    summary_df = build_public_model_summary(case_model_df)
    call_log_df = build_public_sanitized_call_log(
        call_log_csv,
        run_id=run_id,
        case_prefix=case_prefix,
        case_uid_map=case_uid_map,
    )

    case_model_csv = os.path.join(output_dir, "RadLE_v2_public_model_results.csv")
    summary_csv = os.path.join(output_dir, "RadLE_v2_public_model_summary.csv")
    call_log_public_csv = os.path.join(output_dir, "RadLE_v2_public_sanitized_call_log.csv")
    manifest_json = os.path.join(output_dir, "RadLE_v2_public_manifest.json")

    atomic_to_csv(case_model_df, case_model_csv)
    atomic_to_csv(summary_df, summary_csv)
    if not call_log_df.empty:
        atomic_to_csv(call_log_df, call_log_public_csv)

    manifest = {
        "run_id": run_id or "",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_results_file": os.path.basename(results_csv),
        "source_call_log_file": os.path.basename(call_log_csv) if call_log_csv else "",
        "public_files": {
            "case_model": os.path.basename(case_model_csv),
            "model_summary": os.path.basename(summary_csv),
            "sanitized_call_log": os.path.basename(call_log_public_csv) if not call_log_df.empty else "",
        },
        "privacy_notes": [
            "No diagnosis columns are exported.",
            "No raw responses or reasoning text are exported.",
            "No image filenames or image hashes are exported.",
            "Case identifiers are replaced with sequential public case_uid values.",
            "Provider error and repair reason text are reduced to coarse class values.",
        ],
    }
    with open(manifest_json, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)

    return {
        "case_model_csv": case_model_csv,
        "summary_csv": summary_csv,
        "sanitized_call_log_csv": call_log_public_csv if not call_log_df.empty else "",
        "manifest_json": manifest_json,
    }


def create_scorer_view(raw_csv, scorer_csv=None):
    """Create the human-friendly scorer CSV and transposed display dataframe."""
    scorer_csv = scorer_csv or raw_csv.replace(".csv", "_SCORER_VIEW.csv")

    if not os.path.exists(raw_csv):
        raise FileNotFoundError(f"Raw CSV not found: {raw_csv}")

    df = pd.read_csv(raw_csv)
    cols = df.columns.tolist()
    id_cols = ["Master_Case_ID", "Associated_Images"]
    diag_cols = [c for c in cols if "Diagnosis_" in c]
    likert_cols = [c for c in cols if "Likert_" in c]

    df_scorer = df[id_cols + diag_cols + likert_cols]
    df_scorer.to_csv(scorer_csv, index=False)

    display_df = df_scorer.set_index("Master_Case_ID").T
    return df_scorer, display_df, scorer_csv
