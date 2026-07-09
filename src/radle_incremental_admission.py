from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


ALLOWED_ROSTER_STATUSES = {
    "complete_master_active",
    "complete_master_excluded",
    "pending_admission",
    "rejected_or_incomplete",
}
REQUIRED_MODEL_FIELDS = {
    "model_key",
    "display_name",
    "requested_model_id",
    "returned_model_pattern",
    "runtime_path",
    "provider_route",
    "provider_value",
    "access",
    "domain",
    "blind_label",
    "roster_status",
}
PROHIBITED_LIVE_STATS_PATH = "C:/Users/thehb/Documents/" + "RadLE Stats"


class ValidationError(ValueError):
    """Raised when a RadLE incremental-admission contract check fails."""


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normalize_diagnosis(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text).casefold()
    chars: list[str] = []
    for char in text:
        category = unicodedata.category(char)
        if category.startswith("P") or char in {"'", "\u2019", "\u2018", "-", "\u2010", "\u2011", "\u2012", "\u2013", "\u2014"}:
            chars.append(" ")
        else:
            chars.append(char)
    return re.sub(r"\s+", " ", "".join(chars)).strip()


def label_suffix_to_number(suffix: str) -> int:
    if not suffix or not re.fullmatch(r"[A-Z]+", suffix):
        raise ValidationError(f"Invalid candidate suffix: {suffix!r}")
    value = 0
    for char in suffix:
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value


def label_number_to_suffix(value: int) -> str:
    if value < 1:
        raise ValidationError(f"Invalid candidate label number: {value}")
    chars: list[str] = []
    while value:
        value -= 1
        chars.append(chr(ord("A") + (value % 26)))
        value //= 26
    return "".join(reversed(chars))


def candidate_label_sort_key(label: str) -> int:
    match = re.fullmatch(r"Candidate ([A-Z]+)", str(label).strip())
    if not match:
        raise ValidationError(f"Invalid candidate label: {label!r}")
    return label_suffix_to_number(match.group(1))


def allocate_next_candidate_label(existing_labels: list[str]) -> str:
    if not existing_labels:
        return "Candidate A"
    next_number = max(candidate_label_sort_key(label) for label in existing_labels) + 1
    return f"Candidate {label_number_to_suffix(next_number)}"


def _find_duplicate(values: list[str]) -> str | None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            return value
        seen.add(value)
    return None


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _bool_from_fixture(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def classify_terminal_state(row: dict[str, str], ground_truth: str, policy: dict[str, Any]) -> str:
    diagnosis = row.get("diagnosis", "")
    likert = row.get("likert", "")
    normalized = normalize_diagnosis(diagnosis)
    normalized_ground_truth = normalize_diagnosis(ground_truth)
    package_failure = _bool_from_fixture(row.get("package_failure", "false"))

    failure_markers = set(policy.get("failure_markers_normalized", []))
    if normalized in failure_markers or package_failure:
        return "provider_or_parse_failure"

    raw_likert = str(likert).strip()
    if raw_likert:
        try:
            parsed_likert = int(raw_likert)
        except ValueError:
            return "invalid_likert"
        if parsed_likert not in range(5):
            return "invalid_likert"

    if not normalized:
        raise ValidationError("Blank diagnosis without package failure provenance")

    if normalized in set(policy.get("idk_exact_normalized", [])):
        return "idk_exact"
    if normalized in set(policy.get("idk_approved_typo_normalized", [])):
        return "idk_approved_typo"
    if not raw_likert:
        return "invalid_likert"
    if normalized == normalized_ground_truth:
        return "canonical_exact"

    case_id = str(row.get("Master_Case_ID", "")).strip()
    for rule in policy.get("mandatory_radiologist_rules", []):
        if (
            str(rule.get("Master_Case_ID", "")).strip() == case_id
            and str(rule.get("diagnosis_normalized", "")).strip() == normalized
        ):
            return "mandatory_radiologist"

    return "judge_required"


def validate_terminal_policy(policy: dict[str, Any], fixture_csv: Path | None = None) -> dict[str, Any]:
    states = policy.get("states", [])
    if not isinstance(states, list) or not states:
        raise ValidationError("terminal policy must define states")
    names = [str(state.get("state", "")) for state in states]
    expected = [
        "provider_or_parse_failure",
        "invalid_likert",
        "idk_exact",
        "idk_approved_typo",
        "canonical_exact",
        "mandatory_radiologist",
        "judge_required",
    ]
    if names != expected:
        raise ValidationError(f"terminal state order mismatch: {names}")
    if policy.get("normalizer_version") != "radle_exact_v1":
        raise ValidationError("normalizer_version must be radle_exact_v1")
    expected_likert_rules = [
        "valid committed Likert values are integral 0 through 4",
        "Likert 8 is invalid and scores zero",
        "blank Likert is allowed only for exact or approved-typo IDK terminal states",
        "blank Likert on any non-IDK committed diagnosis is invalid_likert",
    ]
    if policy.get("invalid_likert_rules") != expected_likert_rules:
        raise ValidationError("invalid_likert_rules mismatch")

    result: dict[str, Any] = {"states": names}
    if fixture_csv is not None:
        rows = _read_csv_rows(fixture_csv)
        fixture_results = []
        for row in rows:
            expected_state = row.get("expected_state", "")
            try:
                actual_state = classify_terminal_state(row, row.get("ground_truth", ""), policy)
            except ValidationError:
                actual_state = "ERROR"
            if expected_state != actual_state:
                raise ValidationError(
                    f"fixture case {row.get('Master_Case_ID')} expected {expected_state}, got {actual_state}"
                )
            fixture_results.append(actual_state)
        result["fixture_rows"] = len(rows)
        result["fixture_states"] = fixture_results
    return result


def validate_roster(roster: dict[str, Any]) -> dict[str, Any]:
    models = roster.get("models", [])
    blind_map = roster.get("blind_label_map", [])
    if not isinstance(models, list) or not models:
        raise ValidationError("roster must contain models")
    if not isinstance(blind_map, list) or not blind_map:
        raise ValidationError("roster must contain blind_label_map")

    model_keys = [str(model.get("model_key", "")) for model in models]
    duplicate = _find_duplicate(model_keys)
    if duplicate:
        raise ValidationError(f"duplicate model_key: {duplicate}")

    labels = [str(model.get("blind_label", "")) for model in models]
    duplicate = _find_duplicate(labels)
    if duplicate:
        raise ValidationError(f"duplicate model blind_label: {duplicate}")
    for model in models:
        missing = sorted(REQUIRED_MODEL_FIELDS - set(model))
        if missing:
            raise ValidationError(f"{model.get('model_key')} missing required fields: {missing}")
        status = model.get("roster_status")
        if status not in ALLOWED_ROSTER_STATUSES:
            raise ValidationError(f"{model.get('model_key')} has invalid roster_status {status!r}")
        candidate_label_sort_key(str(model["blind_label"]))

    map_labels = [str(entry.get("blind_label", "")) for entry in blind_map]
    duplicate = _find_duplicate(map_labels)
    if duplicate:
        raise ValidationError(f"duplicate blind_label_map label: {duplicate}")
    for label in map_labels:
        candidate_label_sort_key(label)

    human_labels = [entry for entry in blind_map if entry.get("entry_type") == "human"]
    if len(human_labels) != 12:
        raise ValidationError(f"expected exactly 12 human blind labels, got {len(human_labels)}")
    human_suffixes = [str(entry["blind_label"]).replace("Candidate ", "") for entry in human_labels]
    if human_suffixes != ["S", "T", "U", "V", "W", "X", "Y", "Z", "AA", "AB", "AC", "AD"]:
        raise ValidationError(f"unexpected human label sequence: {human_suffixes}")

    active = {m["model_key"] for m in models if m["roster_status"] == "complete_master_active"}
    excluded = {m["model_key"] for m in models if m["roster_status"] == "complete_master_excluded"}
    if active & excluded:
        raise ValidationError(f"active/excluded overlap: {sorted(active & excluded)}")

    for required in ("grok_4_5", "gpt_5_6_sol_pro", "muse_spark_1_1"):
        match = [m for m in models if m["model_key"] == required]
        if not match or match[0]["roster_status"] != "pending_admission":
            raise ValidationError(f"{required} must be pending_admission")

    next_after_ad = allocate_next_candidate_label([f"Candidate {suffix}" for suffix in ["A", "Z", "AA", "AD"]])
    if next_after_ad != "Candidate AE":
        raise ValidationError(f"candidate label allocation failed: {next_after_ad}")

    return {
        "model_count": len(models),
        "active_count": len(active),
        "excluded_count": len(excluded),
        "pending_count": sum(1 for m in models if m["roster_status"] == "pending_admission"),
        "human_label_count": len(human_labels),
        "next_after_ad": next_after_ad,
    }


def validate_judges(judges: dict[str, Any], config_root: Path) -> dict[str, Any]:
    expected_ids = ["google/gemini-3.1-pro-preview", "z-ai/glm-5.2"]
    ids = [judge.get("requested_model_id") for judge in judges.get("judges", [])]
    if ids != expected_ids:
        raise ValidationError(f"judge model IDs mismatch: {ids}")
    if judges.get("base_url") != "https://openrouter.ai/api/v1":
        raise ValidationError("judge base_url mismatch")
    if judges.get("temperature") != 0:
        raise ValidationError("judge temperature must be 0")
    if judges.get("max_retries") != 6 or judges.get("timeout_seconds") != 90:
        raise ValidationError("judge retry/timeout mismatch")
    prompt_path = config_root / str(judges.get("prompt_file", ""))
    if not prompt_path.exists():
        raise ValidationError(f"judge prompt file missing: {prompt_path}")
    prompt_hash = sha256_file(prompt_path)
    evidence = judges.get("source_evidence", {})
    if evidence.get("source_script_git_blob") != "930ae988f1e0a33c068053e75bd4abe1b644fb7a":
        raise ValidationError("judge source_script_git_blob mismatch")
    if evidence.get("source_script_sha256") != "C1017B55826D6842E22D443B14FAECD5E4978CCE612D973DBEBD628AD2FF0A60":
        raise ValidationError("judge source_script_sha256 mismatch")
    recorded = evidence.get("prompt_file_sha256")
    if recorded != prompt_hash:
        raise ValidationError(f"prompt_file_sha256 mismatch: {recorded} != {prompt_hash}")
    return {"judge_count": len(ids), "prompt_sha256": prompt_hash}


def scan_for_prohibited_path(paths: list[Path]) -> list[str]:
    hits: list[str] = []
    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if PROHIBITED_LIVE_STATS_PATH in text:
            hits.append(str(path))
    return hits


def validate_configs(
    roster_path: Path,
    judges_path: Path,
    states_path: Path,
    fixture_csv: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root or Path.cwd()
    roster = read_json(roster_path)
    judges = read_json(judges_path)
    states = read_json(states_path)
    prompt_path = repo_root / str(judges.get("prompt_file", ""))
    prohibited_hits = scan_for_prohibited_path([roster_path, judges_path, states_path, prompt_path])
    if prohibited_hits:
        raise ValidationError(f"prohibited legacy stats path found: {prohibited_hits}")
    receipt = {
        "roster": validate_roster(roster),
        "judges": validate_judges(judges, repo_root),
        "terminal_policy": validate_terminal_policy(states, fixture_csv),
    }
    return receipt
