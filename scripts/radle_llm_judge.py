"""LLM-as-judge scoring and score propagation for RadLE v2.

This script owns the text-only correctness-judging path. It reads a dynamic
RadLE scoring worklist, calls an OpenAI-compatible judge model when requested,
and writes score-updated companion files for downstream stats/public release
work. It does not inspect images.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from radle_v2_stats import (
    CASE_KEY,
    GROUND_TRUTH_COLUMN,
    SCORING_COLUMNS,
    bool_text,
    clean,
    read_csv,
    require_columns,
    sha256_file,
    write_csv,
    write_json,
)


DEFAULT_JUDGE_MODEL = "z-ai/glm-5.2"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_PUBLIC_MODEL_RESULTS = Path("results/radle_v2_combined/public_release/RadLE_v2_public_model_results.csv")
DEFAULT_PUBLIC_MODEL_SUMMARY = Path("results/radle_v2_combined/public_release/RadLE_v2_public_model_summary.csv")

SCORE_UPDATE_COLUMNS = [
    "score_binary",
    "score_likert",
    "judge_verdict",
    "judge_confidence",
    "judge_match_type",
    "needs_human_review",
    "likert_weight",
    "weighted_score",
    "weighted_score_rule",
    "judge_rationale",
    "judge_model",
    "judge_status",
    "judged_utc",
]


def load_env_file(path: Path | None) -> None:
    if not path or not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_api_key(env_names: list[str]) -> str:
    for name in env_names:
        value = os.environ.get(name)
        if value:
            return value
    raise ValueError(f"API key not found in environment variable(s): {env_names}")


def build_judge_prompt(row: dict[str, str]) -> str:
    return (
        "Text-only RadLE scoring task. Compare the ground-truth diagnosis with "
        "one model's final diagnosis. Do not infer from images, reasoning text, "
        "or outside case details.\n\n"
        "Binary correctness rubric:\n"
        "- score_binary=1 when the model diagnosis names the same clinical entity "
        "as the ground truth, including accepted synonyms, eponyms, spelling "
        "variants, or acronym/full-name equivalents.\n"
        "- score_binary=0 when the model diagnosis is a different disease, wrong "
        "anatomy, wrong etiology, only a vague non-equivalent category, or a "
        "materially incomplete answer.\n"
        "- If text alone is insufficient to judge safely, set score_binary=null "
        "and needs_human_review=true.\n"
        "- Do not give credit just because words overlap.\n"
        "- Do not penalize capitalization, punctuation, or abbreviation/full-name "
        "differences.\n\n"
        "Important: do not calculate the confidence-weighted score. The pipeline "
        "will apply negative marking deterministically from the model's own "
        "Likert confidence: correct=+Likert, wrong=-Likert, uncertain=blank.\n\n"
        "Return JSON only with these keys:\n"
        "score_binary, verdict, confidence, match_type, needs_human_review, rationale\n\n"
        "Allowed values:\n"
        "- score_binary: 1, 0, or null\n"
        "- verdict: correct, incorrect, uncertain\n"
        "- confidence: high, medium, low\n"
        "- match_type: exact, synonym, acronym_or_expansion, eponym_or_variant, "
        "broader_equivalent, not_match, uncertain\n"
        "- needs_human_review: true or false\n"
        "- rationale: one concise sentence\n\n"
        f"Ground truth diagnosis: {row.get(GROUND_TRUTH_COLUMN, '')}\n"
        f"Model diagnosis: {row.get('diagnosis', '')}\n"
        f"Model confidence Likert for later negative marking: {row.get('likert', '')}\n"
    )


def extract_json_object(text: str) -> dict[str, object]:
    stripped = text.strip()
    stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
    stripped = re.sub(r"```$", "", stripped).strip()
    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match:
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return data
    raise ValueError(f"Judge response did not contain a JSON object: {text[:300]}")


def openai_compatible_chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    timeout: int,
    max_tokens: int,
) -> tuple[dict[str, object], dict[str, object]]:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a careful diagnostic-radiology scoring judge. "
                    "You compare text diagnoses and return strict JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/openai/codex",
            "X-Title": "RadLE v2 LLM Judge",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response_payload = json.loads(response.read().decode("utf-8"))

    content = response_payload["choices"][0]["message"]["content"]
    return extract_json_object(content), response_payload


def normalize_judge_result(result: dict[str, object]) -> dict[str, str]:
    score_binary_raw = result.get("score_binary")
    if score_binary_raw is None or score_binary_raw == "":
        score_binary = ""
    elif str(score_binary_raw).strip() in {"0", "0.0", "false", "False"}:
        score_binary = "0"
    elif str(score_binary_raw).strip() in {"1", "1.0", "true", "True"}:
        score_binary = "1"
    else:
        score_binary = ""

    needs_review_raw = result.get("needs_human_review", "")
    if isinstance(needs_review_raw, bool):
        needs_human_review = bool_text(needs_review_raw)
    else:
        needs_human_review = bool_text(str(needs_review_raw).strip().lower() == "true")
    if score_binary == "":
        needs_human_review = "true"

    return {
        "score_binary": score_binary,
        "score_likert": "",
        "judge_verdict": clean(result.get("verdict", "")),
        "judge_confidence": clean(result.get("confidence", "")),
        "judge_match_type": clean(result.get("match_type", "")),
        "needs_human_review": needs_human_review,
        "judge_rationale": clean(result.get("rationale", "")),
    }


def likert_weight(likert: object) -> str:
    raw = clean(likert)
    if raw == "":
        return ""
    try:
        value = int(float(raw))
    except ValueError:
        return ""
    if value < 0 or value > 4:
        return ""
    return str(value)


def weighted_score(score_binary: str, likert: object) -> str:
    weight = likert_weight(likert)
    if weight == "" or score_binary == "":
        return ""
    signed = int(weight) if score_binary == "1" else -int(weight)
    return str(signed)


def row_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        clean(row.get("run_id", "")),
        clean(row.get(CASE_KEY, "")),
        clean(row.get("model_key", "")),
    )


def row_needs_judge(row: dict[str, str], selected_models: set[str] | None) -> bool:
    if selected_models is not None and row.get("model_key", "") not in selected_models:
        return False
    if clean(row.get("score_required", "")).lower() != "true":
        return False
    return clean(row.get("score_binary", "")) == ""


def selected_model_set(models: str | None) -> set[str] | None:
    if not models:
        return None
    return {part.strip() for part in models.split(",") if part.strip()}


def ensure_scoring_columns(fieldnames: list[str]) -> list[str]:
    out = list(fieldnames)
    for column in SCORING_COLUMNS:
        if column not in out:
            out.append(column)
    return out


def ensure_score_update_columns(fieldnames: list[str]) -> list[str]:
    out = list(fieldnames)
    for column in SCORE_UPDATE_COLUMNS:
        if column not in out:
            out.append(column)
    return out


def read_score_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    fieldnames, rows = read_csv(path)
    require_columns(fieldnames, SCORING_COLUMNS[:12], "scoring CSV")
    return ensure_scoring_columns(fieldnames), rows


def judge_score_rows(args: argparse.Namespace) -> tuple[list[dict[str, str]], dict[str, int]]:
    input_path = args.worklist.resolve()
    load_env_file(args.env_file)
    _, rows = read_score_rows(input_path)

    selected_models = selected_model_set(args.models)
    candidates = [row for row in rows if row_needs_judge(row, selected_models)]
    if args.limit is not None:
        candidates = candidates[:args.limit]

    print(f"worklist={input_path}")
    print(f"judge_model={args.judge_model}")
    print(f"candidate_rows={len(candidates)}")

    if args.dry_run:
        for row in candidates[: max(1, min(args.limit or 1, 3))]:
            print("=" * 72)
            print(f"row_uid={row.get('row_uid')}")
            print(build_judge_prompt(row))
        print("dry_run=true; no API calls or files written")
        return rows, {"judged": 0, "errors": 0, "skipped_existing": 0}

    api_key = get_api_key(args.api_key_env)
    judged_by_uid: dict[str, dict[str, str]] = {}
    scored_output_path = resolved_scored_worklist_path(args)
    if args.resume and scored_output_path.exists():
        _, existing_rows = read_score_rows(scored_output_path)
        judged_by_uid = {
            row.get("row_uid", ""): row
            for row in existing_rows
            if clean(row.get("score_binary", "")) != ""
            or clean(row.get("judge_status", "")) == "skipped_non_scoreable"
        }

    output_rows: list[dict[str, str]] = []
    audit_log_path = args.audit_log.resolve() if args.audit_log else None
    audit_log_handle = None
    if audit_log_path:
        audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        audit_log_handle = audit_log_path.open("a", encoding="utf-8")

    judged_count = 0
    error_count = 0
    skipped_existing = 0
    try:
        for row in rows:
            row_uid = row.get("row_uid", "")
            if row_uid in judged_by_uid and args.resume:
                output_rows.append(judged_by_uid[row_uid])
                skipped_existing += 1
                continue

            if not row_needs_judge(row, selected_models):
                out = dict(row)
                if clean(out.get("score_required", "")).lower() != "true":
                    out["judge_status"] = out.get("judge_status") or "skipped_non_scoreable"
                output_rows.append(out)
                continue

            if args.limit is not None and judged_count >= args.limit:
                output_rows.append(row)
                continue

            prompt = build_judge_prompt(row)
            last_error = ""
            result: dict[str, object] | None = None
            raw_response: dict[str, object] | None = None
            for attempt in range(args.max_retries + 1):
                try:
                    result, raw_response = openai_compatible_chat_completion(
                        base_url=args.base_url,
                        api_key=api_key,
                        model=args.judge_model,
                        prompt=prompt,
                        timeout=args.timeout,
                        max_tokens=args.max_tokens,
                    )
                    break
                except (
                    urllib.error.URLError,
                    urllib.error.HTTPError,
                    ValueError,
                    KeyError,
                    json.JSONDecodeError,
                ) as exc:
                    last_error = str(exc)
                    if attempt >= args.max_retries:
                        break
                    time.sleep(args.retry_sleep * (attempt + 1))

            out = dict(row)
            out["judge_model"] = args.judge_model
            out["judged_utc"] = datetime.now(timezone.utc).isoformat()
            if result is None:
                out["judge_status"] = "error"
                out["needs_human_review"] = "true"
                out["likert_weight"] = likert_weight(out.get("likert", ""))
                out["weighted_score"] = ""
                out["judge_rationale"] = f"Judge API/error: {last_error[:300]}"
                error_count += 1
            else:
                normalized = normalize_judge_result(result)
                out.update(normalized)
                out["likert_weight"] = likert_weight(out.get("likert", ""))
                out["weighted_score"] = weighted_score(normalized["score_binary"], out.get("likert", ""))
                out["weighted_score_rule"] = "correct=+Likert, wrong=-Likert, uncertain=blank"
                out["judge_status"] = "judged"
                judged_count += 1

            output_rows.append(out)
            if audit_log_handle:
                audit_log_handle.write(json.dumps({
                    "row_uid": row_uid,
                    "judge_model": args.judge_model,
                    "prompt": prompt,
                    "result": result,
                    "api_model": (raw_response or {}).get("model", ""),
                    "usage": (raw_response or {}).get("usage", {}),
                    "error": last_error if result is None else "",
                    "judged_utc": out["judged_utc"],
                }, sort_keys=True) + "\n")
                audit_log_handle.flush()
    finally:
        if audit_log_handle:
            audit_log_handle.close()

    return output_rows, {
        "judged": judged_count,
        "errors": error_count,
        "skipped_existing": skipped_existing,
    }


def score_map(score_rows: list[dict[str, str]]) -> dict[tuple[str, str, str], dict[str, str]]:
    mapped: dict[tuple[str, str, str], dict[str, str]] = {}
    duplicates: list[tuple[str, str, str]] = []
    for row in score_rows:
        key = row_key(row)
        if not all(key):
            continue
        if key in mapped:
            duplicates.append(key)
        mapped[key] = row
    if duplicates:
        raise ValueError(f"Duplicate score keys, sample: {duplicates[:10]}")
    return mapped


def prepare_score_rows_for_output(score_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    prepared: list[dict[str, str]] = []
    for row in score_rows:
        out = dict(row)
        score_binary = clean(out.get("score_binary", ""))
        if score_binary in {"0", "0.0"}:
            score_binary = "0"
        elif score_binary in {"1", "1.0"}:
            score_binary = "1"
        elif score_binary.lower() == "nan":
            score_binary = ""
        out["score_binary"] = score_binary
        out["likert_weight"] = likert_weight(out.get("likert", ""))
        if score_binary in {"0", "1"}:
            out["weighted_score"] = weighted_score(score_binary, out.get("likert", ""))
            out["weighted_score_rule"] = "correct=+Likert, wrong=-Likert, uncertain=blank"
        elif clean(out.get("weighted_score", "")).lower() == "nan":
            out["weighted_score"] = ""
        # The LLM is only a binary/equivalence judge. Do not propagate an
        # LLM-provided Likert-style correctness score.
        out["score_likert"] = ""
        prepared.append(out)
    return prepared


def score_coverage(score_rows: list[dict[str, str]]) -> dict[str, object]:
    required_rows = [row for row in score_rows if clean(row.get("score_required", "")).lower() == "true"]
    scored_rows = [row for row in required_rows if clean(row.get("score_binary", "")) != ""]
    human_review_rows = [
        row for row in score_rows
        if clean(row.get("needs_human_review", "")).lower() == "true"
    ]
    by_model: dict[str, dict[str, int]] = {}
    for row in score_rows:
        model = clean(row.get("model_key", ""))
        if model not in by_model:
            by_model[model] = {
                "rows": 0,
                "score_required": 0,
                "scored": 0,
                "needs_human_review": 0,
            }
        by_model[model]["rows"] += 1
        if clean(row.get("score_required", "")).lower() == "true":
            by_model[model]["score_required"] += 1
            if clean(row.get("score_binary", "")) != "":
                by_model[model]["scored"] += 1
        if clean(row.get("needs_human_review", "")).lower() == "true":
            by_model[model]["needs_human_review"] += 1

    return {
        "rows": len(score_rows),
        "score_required": len(required_rows),
        "scored": len(scored_rows),
        "unscored_score_required": len(required_rows) - len(scored_rows),
        "needs_human_review": len(human_review_rows),
        "by_model": by_model,
    }


def apply_scores_to_long(
    *,
    long_path: Path,
    output_path: Path,
    score_rows: list[dict[str, str]],
    overwrite: bool,
) -> dict[str, object]:
    long_fieldnames, long_rows = read_csv(long_path)
    require_columns(long_fieldnames, ["run_id", CASE_KEY, "model_key"], "long-format CSV")
    scores = score_map(score_rows)
    output_fieldnames = ensure_score_update_columns(long_fieldnames)

    updated_rows: list[dict[str, str]] = []
    matched = 0
    scored = 0
    for row in long_rows:
        out = dict(row)
        score_row = scores.get(row_key(row))
        if score_row:
            matched += 1
            for column in SCORE_UPDATE_COLUMNS:
                out[column] = score_row.get(column, "")
            if clean(score_row.get("score_binary", "")) != "":
                scored += 1
        else:
            for column in SCORE_UPDATE_COLUMNS:
                out.setdefault(column, "")
        updated_rows.append(out)

    write_csv(output_path, output_fieldnames, updated_rows, overwrite)
    return {
        "path": str(output_path),
        "sha256": sha256_file(output_path),
        "rows": len(updated_rows),
        "matched_score_rows": matched,
        "rows_with_score_binary": scored,
    }


def public_case_id(case_uid: str) -> str:
    text = clean(case_uid)
    match = re.search(r"(\d+)$", text)
    if match:
        return str(int(match.group(1)))
    return text


def public_row_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        clean(row.get("run_id", "")),
        public_case_id(row.get("case_uid", "")),
        clean(row.get("model", "")),
    )


def apply_scores_to_public_results(
    *,
    public_path: Path,
    output_path: Path,
    score_rows: list[dict[str, str]],
    overwrite: bool,
) -> dict[str, object]:
    fieldnames, rows = read_csv(public_path)
    require_columns(fieldnames, ["run_id", "case_uid", "model"], "public model results CSV")
    output_fieldnames = list(fieldnames)
    for column in ("score_binary", "score_likert"):
        if column not in output_fieldnames:
            output_fieldnames.append(column)
    for column in ("weighted_score", "weighted_score_rule", "judge_status"):
        if column not in output_fieldnames:
            output_fieldnames.append(column)

    scores = score_map(score_rows)
    updated_rows: list[dict[str, str]] = []
    matched = 0
    scored = 0
    for row in rows:
        out = dict(row)
        score_row = scores.get(public_row_key(row))
        if score_row:
            matched += 1
            out["score_binary"] = score_row.get("score_binary", "")
            out["score_likert"] = ""
            out["weighted_score"] = score_row.get("weighted_score", "")
            out["weighted_score_rule"] = score_row.get("weighted_score_rule", "")
            out["judge_status"] = score_row.get("judge_status", "")
            if clean(out.get("score_binary", "")) != "":
                scored += 1
        updated_rows.append(out)

    write_csv(output_path, output_fieldnames, updated_rows, overwrite)
    return {
        "path": str(output_path),
        "sha256": sha256_file(output_path),
        "rows": len(updated_rows),
        "matched_score_rows": matched,
        "rows_with_score_binary": scored,
    }


def numeric_value(value: object) -> float | None:
    raw = clean(value)
    if raw == "" or raw.lower() == "nan":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def mean_text(values: list[float]) -> str:
    if not values:
        return ""
    text = f"{sum(values) / len(values):.6f}".rstrip("0").rstrip(".")
    return text or "0"


def summary_coverage_by_group(
    public_rows: list[dict[str, str]],
    score_rows: list[dict[str, str]],
) -> dict[tuple[str, str, str], dict[str, object]]:
    scores = score_map(score_rows)
    coverage: dict[tuple[str, str, str], dict[str, object]] = {}
    for public_row in public_rows:
        group_key = (
            clean(public_row.get("run_id", "")),
            clean(public_row.get("model", "")),
            clean(public_row.get("provider", "")),
        )
        if group_key not in coverage:
            coverage[group_key] = {
                "score_required": 0,
                "scored": 0,
                "score_binary_values": [],
                "score_likert_values": [],
                "weighted_score_values": [],
            }
        score_row = scores.get(public_row_key(public_row))
        if not score_row:
            continue
        if clean(score_row.get("score_required", "")).lower() != "true":
            continue
        coverage[group_key]["score_required"] = int(coverage[group_key]["score_required"]) + 1
        score_binary = numeric_value(score_row.get("score_binary", ""))
        score_likert = numeric_value(score_row.get("score_likert", ""))
        weighted = numeric_value(score_row.get("weighted_score", ""))
        if score_binary is not None:
            coverage[group_key]["scored"] = int(coverage[group_key]["scored"]) + 1
            coverage[group_key]["score_binary_values"].append(score_binary)  # type: ignore[union-attr]
        if score_likert is not None:
            coverage[group_key]["score_likert_values"].append(score_likert)  # type: ignore[union-attr]
        if weighted is not None:
            coverage[group_key]["weighted_score_values"].append(weighted)  # type: ignore[union-attr]
    return coverage


def apply_scores_to_public_summary(
    *,
    summary_path: Path,
    public_results_path: Path,
    output_path: Path,
    score_rows: list[dict[str, str]],
    overwrite: bool,
    allow_partial_summary: bool,
) -> dict[str, object]:
    summary_fieldnames, summary_rows = read_csv(summary_path)
    public_fieldnames, public_rows = read_csv(public_results_path)
    require_columns(summary_fieldnames, ["run_id", "model", "provider"], "public model summary CSV")
    require_columns(public_fieldnames, ["run_id", "case_uid", "model", "provider"], "public model results CSV")

    output_fieldnames = list(summary_fieldnames)
    for column in ("mean_score_binary", "mean_score_likert"):
        if column not in output_fieldnames:
            output_fieldnames.append(column)
    if "mean_weighted_score" not in output_fieldnames:
        output_fieldnames.append("mean_weighted_score")

    coverage = summary_coverage_by_group(public_rows, score_rows)
    complete_groups = 0
    partial_groups = 0
    output_rows: list[dict[str, str]] = []
    for row in summary_rows:
        out = dict(row)
        group_key = (
            clean(row.get("run_id", "")),
            clean(row.get("model", "")),
            clean(row.get("provider", "")),
        )
        group = coverage.get(group_key, {})
        required = int(group.get("score_required", 0) or 0)
        scored = int(group.get("scored", 0) or 0)
        is_complete = required > 0 and scored == required
        if is_complete:
            complete_groups += 1
        elif scored > 0:
            partial_groups += 1

        if is_complete or (allow_partial_summary and scored > 0):
            out["mean_score_binary"] = mean_text(group.get("score_binary_values", []))  # type: ignore[arg-type]
            out["mean_score_likert"] = mean_text(group.get("score_likert_values", []))  # type: ignore[arg-type]
            out["mean_weighted_score"] = mean_text(group.get("weighted_score_values", []))  # type: ignore[arg-type]
        else:
            out["mean_score_binary"] = ""
            out["mean_score_likert"] = ""
            out["mean_weighted_score"] = ""
        output_rows.append(out)

    write_csv(output_path, output_fieldnames, output_rows, overwrite)
    return {
        "path": str(output_path),
        "sha256": sha256_file(output_path),
        "rows": len(output_rows),
        "complete_score_groups": complete_groups,
        "partial_score_groups_left_blank": 0 if allow_partial_summary else partial_groups,
        "allow_partial_summary": allow_partial_summary,
    }


def default_scored_name(path: Path) -> Path:
    return path.with_name(path.stem + "_scored" + path.suffix)


def resolve_optional_existing(path: Path | None) -> Path | None:
    if path is not None:
        return path
    return None


def resolved_out_dir(args: argparse.Namespace) -> Path:
    if args.out_dir:
        return args.out_dir.resolve()
    source = getattr(args, "worklist", None) or getattr(args, "scores", None)
    if source:
        return source.resolve().parent
    return Path("outputs/radle_v2_stats").resolve()


def resolved_scored_worklist_path(args: argparse.Namespace) -> Path:
    if args.scored_worklist:
        return args.scored_worklist.resolve()
    if args.update_in_place:
        source = getattr(args, "worklist", None) or getattr(args, "scores", None)
        if source:
            return source.resolve()
    return resolved_out_dir(args) / "scoring_judged.csv"


def resolved_long_input(args: argparse.Namespace) -> Path | None:
    if args.long:
        return args.long.resolve()
    candidate = resolved_out_dir(args) / "long_format.csv"
    if candidate.exists():
        return candidate
    return None


def resolved_long_output(args: argparse.Namespace, long_input: Path | None) -> Path | None:
    if not long_input:
        return None
    if args.long_output:
        return args.long_output.resolve()
    if args.update_in_place:
        return long_input
    return resolved_out_dir(args) / "long_format_scored.csv"


def resolved_public_results_input(args: argparse.Namespace) -> Path | None:
    path = resolve_optional_existing(args.public_model_results)
    if path:
        return path.resolve()
    if DEFAULT_PUBLIC_MODEL_RESULTS.exists():
        return DEFAULT_PUBLIC_MODEL_RESULTS.resolve()
    return None


def resolved_public_results_output(args: argparse.Namespace, public_input: Path | None) -> Path | None:
    if not public_input:
        return None
    if args.public_model_results_output:
        return args.public_model_results_output.resolve()
    if args.update_in_place:
        return public_input
    return resolved_out_dir(args) / "public_release" / public_input.name


def resolved_public_summary_input(args: argparse.Namespace) -> Path | None:
    path = resolve_optional_existing(args.public_model_summary)
    if path:
        return path.resolve()
    if DEFAULT_PUBLIC_MODEL_SUMMARY.exists():
        return DEFAULT_PUBLIC_MODEL_SUMMARY.resolve()
    return None


def resolved_public_summary_output(args: argparse.Namespace, summary_input: Path | None) -> Path | None:
    if not summary_input:
        return None
    if args.public_model_summary_output:
        return args.public_model_summary_output.resolve()
    if args.update_in_place:
        return summary_input
    return resolved_out_dir(args) / "public_release" / summary_input.name


def resolved_summary_json(args: argparse.Namespace) -> Path:
    if args.summary_json:
        return args.summary_json.resolve()
    return resolved_out_dir(args) / "score_update_summary.json"


def require_overwrite_for_in_place(args: argparse.Namespace) -> None:
    if args.update_in_place and not args.overwrite:
        raise ValueError("--update-in-place requires --overwrite")
    if args.update_in_place:
        print("update_in_place=true; existing score-bearing files may be overwritten")
    else:
        print("safe_copy_mode=true; original combined/public files will not be overwritten")


def write_score_artifacts(
    *,
    args: argparse.Namespace,
    score_rows: list[dict[str, str]],
    judge_counts: dict[str, int],
) -> dict[str, object]:
    require_overwrite_for_in_place(args)
    score_rows = prepare_score_rows_for_output(score_rows)
    out_dir = resolved_out_dir(args)
    out_dir.mkdir(parents=True, exist_ok=True)

    artifacts: dict[str, object] = {}
    scored_worklist = resolved_scored_worklist_path(args)
    write_csv(scored_worklist, SCORING_COLUMNS, score_rows, args.overwrite or args.resume)
    artifacts["scored_worklist"] = {
        "path": str(scored_worklist),
        "sha256": sha256_file(scored_worklist),
        "rows": len(score_rows),
    }

    long_input = resolved_long_input(args)
    long_output = resolved_long_output(args, long_input)
    if long_input and long_output:
        artifacts["long_format"] = apply_scores_to_long(
            long_path=long_input,
            output_path=long_output,
            score_rows=score_rows,
            overwrite=args.overwrite,
        )

    public_input = resolved_public_results_input(args)
    public_output = resolved_public_results_output(args, public_input)
    if public_input and public_output:
        artifacts["public_model_results"] = apply_scores_to_public_results(
            public_path=public_input,
            output_path=public_output,
            score_rows=score_rows,
            overwrite=args.overwrite,
        )

    summary_input = resolved_public_summary_input(args)
    summary_output = resolved_public_summary_output(args, summary_input)
    summary_public_source = public_output or public_input
    if summary_input and summary_output and summary_public_source:
        artifacts["public_model_summary"] = apply_scores_to_public_summary(
            summary_path=summary_input,
            public_results_path=summary_public_source,
            output_path=summary_output,
            score_rows=score_rows,
            overwrite=args.overwrite,
            allow_partial_summary=args.allow_partial_summary,
        )

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.command,
        "judge_counts": judge_counts,
        "coverage": score_coverage(score_rows),
        "artifacts": artifacts,
    }
    summary_json = resolved_summary_json(args)
    write_json(summary_json, summary, args.overwrite)
    artifacts["summary_json"] = {
        "path": str(summary_json),
        "sha256": sha256_file(summary_json),
    }
    return summary


def print_artifact_summary(summary: dict[str, object]) -> None:
    coverage = summary["coverage"]  # type: ignore[index]
    print(f"score_required={coverage['score_required']} scored={coverage['scored']} unscored={coverage['unscored_score_required']}")  # type: ignore[index]
    artifacts = summary.get("artifacts", {})
    if isinstance(artifacts, dict):
        for name, artifact in artifacts.items():
            if isinstance(artifact, dict) and "path" in artifact:
                print(f"{name}={artifact['path']}")


def command_score(args: argparse.Namespace) -> int:
    if getattr(args, "api_key_env", None) == []:
        args.api_key_env = ["OPENROUTER_API_KEY", "TEST_OPENROUTER_API_KEY"]
    score_rows, judge_counts = judge_score_rows(args)
    if args.dry_run:
        return 0
    summary = write_score_artifacts(args=args, score_rows=score_rows, judge_counts=judge_counts)
    print(f"judged={judge_counts['judged']} errors={judge_counts['errors']} skipped_existing={judge_counts['skipped_existing']}")
    print_artifact_summary(summary)
    return 0


def command_apply(args: argparse.Namespace) -> int:
    _, score_rows = read_score_rows(args.scores.resolve())
    summary = write_score_artifacts(
        args=args,
        score_rows=score_rows,
        judge_counts={"judged": 0, "errors": 0, "skipped_existing": 0},
    )
    print_artifact_summary(summary)
    return 0


def add_update_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--out-dir", type=Path, help="Directory for scored worklist, long-format output, and summary JSON.")
    parser.add_argument("--scored-worklist", type=Path, help="Output scored worklist CSV. Defaults to <out-dir>/scoring_judged.csv.")
    parser.add_argument("--long", type=Path, help="long_format.csv to update with score columns. Defaults to <out-dir>/long_format.csv if present.")
    parser.add_argument("--long-output", type=Path, help="Score-updated long-format output path.")
    parser.add_argument("--public-model-results", type=Path, help="Public case-model CSV to update with score_binary/score_likert.")
    parser.add_argument("--public-model-results-output", type=Path, help="Score-updated public case-model output path.")
    parser.add_argument("--public-model-summary", type=Path, help="Public model summary CSV to update when score coverage is complete.")
    parser.add_argument("--public-model-summary-output", type=Path, help="Score-updated public model summary output path.")
    parser.add_argument("--summary-json", type=Path, help="Score update summary JSON path.")
    parser.add_argument("--allow-partial-summary", action="store_true", help="Fill summary mean scores even when a model/provider group is partially scored.")
    parser.add_argument("--update-in-place", action="store_true", help="Overwrite provided/default score-bearing files in place. Requires --overwrite.")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting output files.")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Text-only LLM-as-judge scoring for RadLE v2.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    score_parser = subparsers.add_parser("score", help="Call the LLM judge, then write score-updated files.")
    score_parser.add_argument("--worklist", type=Path, required=True, help="scoring_worklist.csv or prior judged scoring CSV.")
    score_parser.add_argument("--audit-log", type=Path, help="Append-only JSONL with prompts, judge outputs, and usage.")
    score_parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    score_parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    score_parser.add_argument(
        "--api-key-env",
        action="append",
        default=[],
        help="Environment variable containing the API key. Can be repeated.",
    )
    score_parser.add_argument("--env-file", type=Path, default=Path("radle_api_keys.env"))
    score_parser.add_argument("--models", help="Comma-separated model_key allowlist.")
    score_parser.add_argument("--limit", type=int)
    score_parser.add_argument("--dry-run", action="store_true")
    score_parser.add_argument("--resume", action="store_true")
    score_parser.add_argument("--timeout", type=int, default=90)
    score_parser.add_argument("--max-tokens", type=int, default=500)
    score_parser.add_argument("--max-retries", type=int, default=2)
    score_parser.add_argument("--retry-sleep", type=float, default=2.0)
    add_update_args(score_parser)
    score_parser.set_defaults(func=command_score)

    apply_parser = subparsers.add_parser("apply", help="Apply an existing judged scoring CSV to companion files without API calls.")
    apply_parser.add_argument("--scores", type=Path, required=True, help="Judged scoring CSV.")
    apply_parser.set_defaults(resume=False)
    add_update_args(apply_parser)
    apply_parser.set_defaults(func=command_apply)

    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
