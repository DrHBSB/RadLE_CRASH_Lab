from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import tempfile
import unicodedata
from collections import Counter
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any


CASE_KEY = "Master_Case_ID"
KEY_COLUMNS = ["Master_Case_ID", "Associated_Images", "Image_SHA256"]
DIAGNOSIS_PREFIX = "Diagnosis_"
LIKERT_PREFIX = "Likert_"
MODEL_SUFFIXES = [
    "Diagnosis",
    "Likert",
    "Prompt_Tokens",
    "Total_Tokens_Out",
    "Reasoning_Tokens",
    "Latency",
    "Provider",
    "Timestamp_UTC",
    "Reasoning",
    "Reasoning_Raw",
    "Reasoning_Details",
    "Actual_Request_Extra",
    "Grok_Fallback_Used",
    "OpenRouter_Response_Model",
    "Usage_JSON",
    "Raw_Response",
]
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
RADIOLOGIST_QUEUE_FIELDS = ["Master_Case_ID", "model_blinded", "Ground_Truth_Diagnosis", "diagnosis", "likert"]
FINAL_LONG_MASTER_FIELDS = [
    "run_id",
    "Master_Case_ID",
    "Associated_Images",
    "model_blinded",
    "candidate",
    "provider",
    "access",
    "domain",
    "Ground_Truth_Diagnosis",
    "diagnosis",
    "likert",
    "response_valid",
    "abstained",
    "technical_failure",
    "score_required",
    "final_score_authoritative",
    "final_score_source",
    "weighted_score",
    "rater_seniority",
    "rater_seniority_rank",
]
ADJUDICATION_STATE_FIELDS = [
    "Master_Case_ID",
    "model_blinded",
    "candidate",
    "terminal_state",
    "normalized_ground_truth",
    "normalized_diagnosis",
    "package_failure",
    "source_row_sha256",
    "automatic_score",
    "requires_judge",
    "requires_radiologist",
]
ALLOWED_NEW_SCORE_SOURCES = {
    "auto_score_not_required",
    "canonical_exact",
    "previous_authoritative_score",
    "ai_judges",
    "radiologist",
}
PRIOR_SCORE_REUSE_FIELDS = [
    "Master_Case_ID",
    "normalized_diagnosis",
    "score_binary",
    "support_count",
    "score_sources",
    "source_candidates",
    "conflict",
]
BLIND_MAP_FIELDS = ["model_blinded", "model_key", "provider"]
CSV_FIELD_LIMIT_TARGET = 2_147_483_647


class ValidationError(ValueError):
    """Raised when a RadLE incremental-admission contract check fails."""


def model_id_matches_request(requested_model_id: str, returned_model_id: object) -> bool:
    if not isinstance(returned_model_id, str) or not returned_model_id:
        return False
    if returned_model_id == requested_model_id:
        return True
    suffix = returned_model_id.removeprefix(f"{requested_model_id}-")
    return suffix != returned_model_id and bool(re.fullmatch(r"\d{8}", suffix))


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


def set_csv_field_limit(target: int = CSV_FIELD_LIMIT_TARGET) -> int:
    """Raise the process CSV limit, backing off on smaller C long platforms."""
    limit = target
    while limit > 131_072:
        try:
            csv.field_size_limit(limit)
            return limit
        except OverflowError:
            limit //= 10
    csv.field_size_limit(131_072)
    return 131_072


def canonical_text_bytes(path: Path) -> bytes:
    text = path.read_text(encoding="utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def canonical_text_sha256(path: Path) -> str:
    return sha256_bytes(canonical_text_bytes(path))


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
    set_csv_field_limit()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_csv_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    set_csv_field_limit()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    if not fieldnames:
        raise ValidationError(f"CSV has no header: {path}")
    if len(set(fieldnames)) != len(fieldnames):
        raise ValidationError(f"CSV has duplicate header columns: {path}")
    return fieldnames, rows


def serialize_csv_table(fieldnames: list[str], rows: list[dict[str, object]], *, lineterminator: str = "\n", include_header: bool = True) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore", lineterminator=lineterminator)
    if include_header:
        writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fieldnames})
    return output.getvalue().encode("utf-8")


def write_csv_table(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(serialize_csv_table(fieldnames, rows))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require_columns(fieldnames: list[str], required: list[str], label: str) -> None:
    missing = [column for column in required if column not in fieldnames]
    if missing:
        raise ValidationError(f"{label} is missing required columns: {missing}")


def case_sort_key(value: str) -> tuple[int, object]:
    try:
        return (0, int(value))
    except ValueError:
        return (1, value)


def discover_model_keys(fieldnames: list[str]) -> list[str]:
    keys: list[str] = []
    for column in fieldnames:
        if column.startswith(DIAGNOSIS_PREFIX) and len(column) > len(DIAGNOSIS_PREFIX):
            keys.append(column[len(DIAGNOSIS_PREFIX):])
    return keys


def model_result_columns(model_key: str) -> list[str]:
    return [f"{suffix}_{model_key}" for suffix in MODEL_SUFFIXES]


def index_by_case(rows: list[dict[str, str]], label: str) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    duplicates: list[str] = []
    blanks = 0
    for row in rows:
        case_id = str(row.get(CASE_KEY, "")).strip()
        if not case_id:
            blanks += 1
            continue
        if case_id in indexed:
            duplicates.append(case_id)
        indexed[case_id] = row
    if blanks:
        raise ValidationError(f"{label} has {blanks} blank {CASE_KEY} values")
    if duplicates:
        raise ValidationError(f"{label} has duplicate {CASE_KEY} values: {sorted(set(duplicates), key=case_sort_key)[:10]}")
    return indexed


def row_sha256(row: dict[str, str], fieldnames: list[str]) -> str:
    payload = {field: row.get(field, "") for field in fieldnames}
    return sha256_bytes(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def _bool_from_fixture(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def classify_terminal_state(
    row: dict[str, str],
    ground_truth: str,
    policy: dict[str, Any],
    prior_score_reuse: dict[tuple[str, str], dict[str, str]] | None = None,
) -> str:
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
            parsed_likert = Fraction(raw_likert)
        except (ValueError, ZeroDivisionError):
            return "invalid_likert"
        if parsed_likert.denominator != 1 or int(parsed_likert) not in range(5):
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

    if prior_score_reuse is not None and (case_id, normalized) in prior_score_reuse:
        return "previous_authoritative_score"

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
        "previous_authoritative_score",
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
    prompt_hash = canonical_text_sha256(prompt_path)
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


def compute_case_triplet_sha256(rows: list[dict[str, str]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: case_sort_key(str(item.get(CASE_KEY, "")))):
        payload = [
            str(row.get(CASE_KEY, "")),
            str(row.get("Associated_Images", "")),
            str(row.get("Image_SHA256", "")),
        ]
        digest.update(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _authority_path(root: Path, descriptor: dict[str, Any], label: str) -> Path:
    relative = str(descriptor.get("path", "")).strip()
    if not relative:
        raise ValidationError(f"{label} authority path is blank")
    path = (root / Path(relative)).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValidationError(f"{label} authority path escapes authority root: {relative}") from exc
    if not path.is_file():
        raise ValidationError(f"{label} authority file missing: {path}")
    return path


def validate_base_authority(
    *,
    authority_manifest: Path,
    authority_root: Path,
    roster_path: Path | None = None,
) -> dict[str, Any]:
    authority = read_json(authority_manifest)
    if authority.get("schema_version") != "radle_v2_base_authority.v1":
        raise ValidationError("unsupported base-authority schema")

    wide_desc = authority.get("base_combined_wide", {})
    long_desc = authority.get("base_final_long_master", {})
    blind_desc = authority.get("base_blinding_key", {})
    wide_path = _authority_path(authority_root, wide_desc, "base wide")
    long_path = _authority_path(authority_root, long_desc, "base final master")
    blind_path = _authority_path(authority_root, blind_desc, "base blind map")

    for label, path, descriptor in (
        ("base wide", wide_path, wide_desc),
        ("base final master", long_path, long_desc),
        ("base blind map", blind_path, blind_desc),
    ):
        expected = str(descriptor.get("sha256", "")).upper()
        actual = sha256_file(path)
        if not expected or actual != expected:
            raise ValidationError(f"{label} SHA256 mismatch: {actual} != {expected}")

    wide_fields, wide_rows = read_csv_table(wide_path)
    long_fields, long_rows = read_csv_table(long_path)
    blind_fields, blind_rows = read_csv_table(blind_path)
    expected_shapes = (
        ("base wide", wide_fields, wide_rows, wide_desc),
        ("base final master", long_fields, long_rows, long_desc),
        ("base blind map", blind_fields, blind_rows, blind_desc),
    )
    for label, fields, rows, descriptor in expected_shapes:
        if "rows" in descriptor and len(rows) != int(descriptor["rows"]):
            raise ValidationError(f"{label} row count mismatch: {len(rows)} != {descriptor['rows']}")
        if "columns" in descriptor and len(fields) != int(descriptor["columns"]):
            raise ValidationError(f"{label} column count mismatch: {len(fields)} != {descriptor['columns']}")

    if long_fields != FINAL_LONG_MASTER_FIELDS:
        raise ValidationError(f"base final master header mismatch: {long_fields}")
    if blind_fields != BLIND_MAP_FIELDS:
        raise ValidationError(f"base blind map header mismatch: {blind_fields}")
    require_columns(wide_fields, KEY_COLUMNS, "base wide")

    case_ids = validate_case_sets(wide_rows, wide_rows)
    fingerprint = compute_case_triplet_sha256(wide_rows)
    expected_fingerprint = str(authority.get("case_fingerprint", {}).get("case_triplet_sha256", "")).lower()
    if fingerprint != expected_fingerprint:
        raise ValidationError(f"case fingerprint mismatch: {fingerprint} != {expected_fingerprint}")
    image_count = sum(len([part for part in str(row["Associated_Images"]).split(",") if part.strip()]) for row in wide_rows)
    expected_images = int(authority.get("case_fingerprint", {}).get("image_count", -1))
    if image_count != expected_images:
        raise ValidationError(f"image count mismatch: {image_count} != {expected_images}")

    blind_by_label: dict[str, dict[str, str]] = {}
    for row in blind_rows:
        label = str(row.get("model_blinded", "")).strip()
        candidate_label_sort_key(label)
        if label in blind_by_label:
            raise ValidationError(f"duplicate blind-map label: {label}")
        blind_by_label[label] = row
    long_keys: set[tuple[str, str]] = set()
    long_counts: Counter[str] = Counter()
    associated_by_case: dict[str, set[str]] = {case_id: set() for case_id in case_ids}
    for row in long_rows:
        key = (str(row.get(CASE_KEY, "")).strip(), str(row.get("model_blinded", "")).strip())
        if key in long_keys:
            raise ValidationError(f"duplicate final-master key: {key}")
        long_keys.add(key)
        if key[0] not in associated_by_case:
            raise ValidationError(f"final master has unknown case: {key[0]}")
        if key[1] not in blind_by_label:
            raise ValidationError(f"final master label missing from blind map: {key[1]}")
        long_counts[key[1]] += 1
        associated_by_case[key[0]].add(str(row.get("Associated_Images", "")))
        blind = blind_by_label[key[1]]
        if candidate_label_sort_key(key[1]) <= candidate_label_sort_key("Candidate R"):
            expected_candidate = str(blind.get("model_key", ""))
            if str(row.get("candidate", "")) != expected_candidate:
                raise ValidationError(f"candidate identity mismatch for {key}: {row.get('candidate')!r} != {expected_candidate!r}")
        else:
            if str(row.get("candidate", "")) not in {"Radiologist", "Trainee"}:
                raise ValidationError(f"human reader type mismatch for {key}: {row.get('candidate')!r}")
            if str(row.get("provider", "")) != str(blind.get("model_key", "")):
                raise ValidationError(f"human provider identity mismatch for {key}")
    if set(long_counts) != set(blind_by_label):
        raise ValidationError("final-master and blind-map label sets differ")
    bad_counts = {label: count for label, count in long_counts.items() if count != 200}
    if bad_counts:
        raise ValidationError(f"expected 200 rows per blind label: {bad_counts}")
    wide_by_case = index_by_case(wide_rows, "base wide")
    for case_id, values in associated_by_case.items():
        if values != {wide_by_case[case_id]["Associated_Images"]}:
            raise ValidationError(f"Associated_Images mismatch for case {case_id}: {values}")

    roster_path = roster_path or authority_manifest.parent / "radle_v2_model_roster.json"
    if not roster_path.is_file():
        raise ValidationError(f"model roster missing for base authority: {roster_path}")
    roster_hash = canonical_text_sha256(roster_path)
    expected_roster_hash = str(authority.get("model_roster_sha256", "")).upper()
    if roster_hash != expected_roster_hash:
        raise ValidationError(f"model roster hash mismatch: {roster_hash} != {expected_roster_hash}")
    roster = read_json(roster_path)
    validate_roster(roster)
    base_model_keys = set(discover_model_keys(wide_fields))
    pending = {str(model.get("model_key", "")) for model in roster.get("models", []) if model.get("roster_status") == "pending_admission"}
    if base_model_keys & pending:
        raise ValidationError(f"base wide already contains pending arms: {sorted(base_model_keys & pending)}")

    return {
        "result": "PASS",
        "authority_type": "base",
        "authority_manifest_sha256": canonical_text_sha256(authority_manifest),
        "wide": {"path": str(wide_path), "sha256": sha256_file(wide_path), "rows": len(wide_rows), "columns": len(wide_fields)},
        "final_master": {"path": str(long_path), "sha256": sha256_file(long_path), "rows": len(long_rows), "columns": len(long_fields)},
        "blind_map": {"path": str(blind_path), "sha256": sha256_file(blind_path), "rows": len(blind_rows), "columns": len(blind_fields)},
        "case_count": len(case_ids),
        "image_count": image_count,
        "case_triplet_sha256": fingerprint,
        "model_roster_sha256": roster_hash,
    }


def find_incoming_results_csv(incoming_package: Path) -> Path:
    if incoming_package.is_file():
        return incoming_package
    final_csv = incoming_package / "final" / "RadLE_v2_results_final.csv"
    if final_csv.exists():
        return final_csv
    candidates = [
        incoming_package / "results.csv",
        incoming_package / "raw" / "results.csv",
    ]
    existing = [path for path in candidates if path.exists()]
    if len(existing) != 1:
        raise ValidationError(f"incoming package must expose exactly one supported results CSV, found {existing}")
    return existing[0]


def find_model_record(roster: dict[str, Any], model_key: str) -> dict[str, Any]:
    matches = [model for model in roster.get("models", []) if model.get("model_key") == model_key]
    if len(matches) != 1:
        raise ValidationError(f"roster must contain exactly one model record for {model_key!r}")
    record = matches[0]
    if record.get("roster_status") != "pending_admission":
        raise ValidationError(f"{model_key} must be pending_admission for prepare, got {record.get('roster_status')!r}")
    for field in REQUIRED_MODEL_FIELDS:
        if field not in record:
            raise ValidationError(f"{model_key} roster record missing {field}")
    return record


def validate_case_sets(parent_rows: list[dict[str, str]], incoming_rows: list[dict[str, str]]) -> list[str]:
    parent_cases = set(index_by_case(parent_rows, "parent wide"))
    incoming_cases = set(index_by_case(incoming_rows, "incoming wide"))
    missing = sorted(parent_cases - incoming_cases, key=case_sort_key)
    extra = sorted(incoming_cases - parent_cases, key=case_sort_key)
    if missing or extra:
        raise ValidationError(f"case set mismatch: missing={missing[:10]} extra={extra[:10]}")
    ordered = sorted(parent_cases, key=case_sort_key)
    if len(ordered) != 200:
        raise ValidationError(f"expected exactly 200 cases, got {len(ordered)}")
    if ordered != [str(value) for value in range(1, 201)]:
        raise ValidationError("case IDs must be exactly 1..200")
    return ordered


def validate_key_metadata(
    parent_rows: list[dict[str, str]],
    incoming_by_case: dict[str, dict[str, str]],
    key_columns: list[str],
) -> None:
    for parent_row in parent_rows:
        case_id = str(parent_row.get(CASE_KEY, "")).strip()
        incoming_row = incoming_by_case[case_id]
        for column in key_columns:
            if parent_row.get(column, "") != incoming_row.get(column, ""):
                raise ValidationError(
                    f"metadata mismatch case {case_id} column {column}: "
                    f"{parent_row.get(column, '')!r} != {incoming_row.get(column, '')!r}"
                )


def build_ground_truth_snapshot(
    parent_long_rows: list[dict[str, str]],
    case_ids: list[str],
) -> list[dict[str, str]]:
    by_case: dict[str, set[str]] = {case_id: set() for case_id in case_ids}
    for row in parent_long_rows:
        case_id = str(row.get(CASE_KEY, "")).strip()
        if case_id not in by_case:
            continue
        value = str(row.get("Ground_Truth_Diagnosis", "")).strip()
        if value:
            by_case[case_id].add(value)

    snapshot: list[dict[str, str]] = []
    for case_id in case_ids:
        values = by_case[case_id]
        if len(values) != 1:
            raise ValidationError(f"case {case_id} must have exactly one ground truth value, got {sorted(values)}")
        value = next(iter(values))
        snapshot.append({
            CASE_KEY: case_id,
            "Ground_Truth_Diagnosis": value,
            "Ground_Truth_Normalized": normalize_diagnosis(value),
        })
    return snapshot


def validate_parent_wide_long_reconciliation(
    parent_wide_fieldnames: list[str],
    parent_wide_rows: list[dict[str, str]],
    parent_long_fieldnames: list[str],
    parent_long_rows: list[dict[str, str]],
) -> None:
    if parent_long_fieldnames != FINAL_LONG_MASTER_FIELDS:
        raise ValidationError(f"parent final master must use exact production schema: {parent_long_fieldnames}")
    long_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for row in parent_long_rows:
        model_key = str(row.get("candidate", "")).strip()
        case_id = str(row.get(CASE_KEY, "")).strip()
        if model_key and model_key not in {"Radiologist", "Trainee"} and case_id:
            if (case_id, model_key) in long_by_key:
                raise ValidationError(f"duplicate parent final-master key for case {case_id} model {model_key}")
            long_by_key[(case_id, model_key)] = row
    for model_key in discover_model_keys(parent_wide_fieldnames):
        diagnosis_column = f"{DIAGNOSIS_PREFIX}{model_key}"
        likert_column = f"{LIKERT_PREFIX}{model_key}"
        if likert_column not in parent_wide_fieldnames:
            continue
        checked = 0
        for row in parent_wide_rows:
            case_id = str(row.get(CASE_KEY, "")).strip()
            long_row = long_by_key.get((case_id, model_key))
            if long_row is None:
                continue
            checked += 1
            if row.get(diagnosis_column, "") != long_row.get("diagnosis", ""):
                raise ValidationError(f"parent wide/long diagnosis mismatch case {case_id} model {model_key}")
            wide_likert = str(row.get(likert_column, "")).strip()
            long_likert = str(long_row.get("likert", "")).strip()
            try:
                likert_equal = Fraction(wide_likert) == Fraction(long_likert)
            except (ValueError, ZeroDivisionError):
                likert_equal = wide_likert == long_likert
            if not likert_equal:
                raise ValidationError(f"parent wide/long likert mismatch case {case_id} model {model_key}")
        if checked and checked != len(parent_wide_rows):
            raise ValidationError(f"parent wide/long only reconciled {checked} rows for {model_key}")


def build_scorer_view(fieldnames: list[str], rows: list[dict[str, str]]) -> tuple[list[str], list[dict[str, str]]]:
    scorer_keys = [column for column in ("Master_Case_ID", "Associated_Images") if column in fieldnames]
    diag_likert = [
        column for column in fieldnames if column.startswith(DIAGNOSIS_PREFIX) or column.startswith(LIKERT_PREFIX)
    ]
    ordered = scorer_keys + [column for column in diag_likert if column not in scorer_keys]
    return ordered, [{column: row.get(column, "") for column in ordered} for row in rows]


def build_prior_score_reuse_snapshot(
    parent_long_rows: list[dict[str, str]],
) -> tuple[dict[tuple[str, str], dict[str, str]], list[dict[str, object]]]:
    buckets: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in parent_long_rows:
        case_id = str(row.get(CASE_KEY, "")).strip()
        normalized = normalize_diagnosis(row.get("diagnosis", ""))
        score = str(row.get("final_score_authoritative", "")).strip()
        if not case_id or not normalized or score not in {"0", "1"}:
            continue
        buckets.setdefault((case_id, normalized), []).append(row)

    reusable: dict[tuple[str, str], dict[str, str]] = {}
    snapshot_rows: list[dict[str, object]] = []
    for (case_id, normalized), rows in sorted(buckets.items(), key=lambda item: (case_sort_key(item[0][0]), item[0][1])):
        scores = {str(row.get("final_score_authoritative", "")).strip() for row in rows}
        score_sources = sorted({str(row.get("final_score_source", "")).strip() for row in rows if str(row.get("final_score_source", "")).strip()})
        source_candidates = sorted({str(row.get("candidate", "")).strip() for row in rows if str(row.get("candidate", "")).strip()})
        conflict = len(scores) != 1
        score_binary = "" if conflict else next(iter(scores))
        snapshot_row = {
            CASE_KEY: case_id,
            "normalized_diagnosis": normalized,
            "score_binary": score_binary,
            "support_count": str(len(rows)),
            "score_sources": ";".join(score_sources),
            "source_candidates": ";".join(source_candidates),
            "conflict": str(conflict),
        }
        snapshot_rows.append(snapshot_row)
        if not conflict:
            reusable[(case_id, normalized)] = {
                key: str(value)
                for key, value in snapshot_row.items()
            }
    return reusable, snapshot_rows


def build_new_model_long_delta(
    parent_long_fieldnames: list[str],
    incoming_rows: list[dict[str, str]],
    incoming_fieldnames: list[str],
    model_key: str,
    model_record: dict[str, Any],
    ground_truth_by_case: dict[str, str],
    terminal_policy: dict[str, Any],
    prior_score_reuse: dict[tuple[str, str], dict[str, str]],
    *,
    parent_run_id: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]], Counter[str], list[dict[str, object]]]:
    if parent_long_fieldnames != FINAL_LONG_MASTER_FIELDS:
        raise ValidationError("new-model delta requires exact production final-master schema")
    rows: list[dict[str, object]] = []
    state_rows: list[dict[str, object]] = []
    judge_worklist: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    diagnosis_column = f"{DIAGNOSIS_PREFIX}{model_key}"
    likert_column = f"{LIKERT_PREFIX}{model_key}"
    for incoming_row in sorted(incoming_rows, key=lambda row: case_sort_key(str(row[CASE_KEY]))):
        case_id = str(incoming_row[CASE_KEY])
        diagnosis = incoming_row.get(diagnosis_column, "")
        likert = incoming_row.get(likert_column, "")
        ground_truth = ground_truth_by_case[case_id]
        terminal_row = {
            CASE_KEY: case_id,
            "diagnosis": diagnosis,
            "likert": likert,
            "package_failure": "false",
        }
        state = classify_terminal_state(terminal_row, ground_truth, terminal_policy, prior_score_reuse)
        counts[state] += 1

        technical_failure = state == "provider_or_parse_failure"
        abstained = state in {"idk_exact", "idk_approved_typo"}
        response_valid = state not in {"provider_or_parse_failure", "invalid_likert"}
        score_required = state in {"judge_required", "mandatory_radiologist"}
        source_hash = row_sha256(incoming_row, incoming_fieldnames)
        out_row: dict[str, object] = {
            "run_id": parent_run_id,
            CASE_KEY: case_id,
            "Associated_Images": incoming_row.get("Associated_Images", ""),
            "model_blinded": model_record.get("blind_label", ""),
            "candidate": model_key,
            "provider": model_record.get("provider_value", ""),
            "access": model_record.get("access", ""),
            "domain": model_record.get("domain", ""),
            "Ground_Truth_Diagnosis": ground_truth,
            "diagnosis": diagnosis,
            "likert": likert,
            "response_valid": str(response_valid),
            "abstained": str(abstained),
            "technical_failure": str(technical_failure),
            "score_required": str(score_required),
            "final_score_authoritative": "",
            "final_score_source": "",
            "weighted_score": "",
            "rater_seniority": "",
            "rater_seniority_rank": "",
        }
        rows.append(out_row)

        automatic_score: object = ""
        if state == "canonical_exact":
            automatic_score = 1
        elif state == "previous_authoritative_score":
            automatic_score = prior_score_reuse[(case_id, normalize_diagnosis(diagnosis))]["score_binary"]
        elif state in {"provider_or_parse_failure", "invalid_likert", "idk_exact", "idk_approved_typo"}:
            automatic_score = 0
        state_rows.append({
            CASE_KEY: case_id,
            "model_blinded": model_record.get("blind_label", ""),
            "candidate": model_key,
            "terminal_state": state,
            "normalized_ground_truth": normalize_diagnosis(ground_truth),
            "normalized_diagnosis": normalize_diagnosis(diagnosis),
            "package_failure": str(technical_failure),
            "source_row_sha256": source_hash,
            "automatic_score": automatic_score,
            "requires_judge": str(state == "judge_required"),
            "requires_radiologist": str(state == "mandatory_radiologist"),
        })

        if state == "judge_required":
            judge_worklist.append({
                CASE_KEY: case_id,
                "model_blinded": model_record.get("blind_label", ""),
                "Ground_Truth_Diagnosis": ground_truth,
                "diagnosis": diagnosis,
                "likert": likert,
            })
    return rows, state_rows, counts, judge_worklist


def compute_intake_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def canonical_json_sha256(path: Path) -> str:
    payload = read_json(path)
    return sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def write_sha256sums(root: Path, paths: list[Path]) -> None:
    entries = []
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        entries.append(f"{sha256_file(path).lower()}  {relative}")
    (root / "SHA256SUMS").write_text("\n".join(entries) + "\n", encoding="utf-8")


def audit_package_sha256sums(root: Path) -> dict[str, str]:
    checksum_path = root / "SHA256SUMS"
    if not checksum_path.is_file():
        raise ValidationError(f"SHA256SUMS missing under {root}")
    lines = [line for line in checksum_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if lines != sorted(lines, key=lambda line: line.split("  ", 1)[1] if "  " in line else line):
        raise ValidationError("SHA256SUMS must be sorted by relative path")
    entries: dict[str, str] = {}
    for line in lines:
        if "  " not in line:
            raise ValidationError(f"malformed SHA256SUMS line: {line!r}")
        digest, relative = line.split("  ", 1)
        if not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise ValidationError(f"invalid SHA256SUMS digest for {relative!r}")
        normalized = Path(relative).as_posix()
        if relative != normalized or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValidationError(f"unsafe SHA256SUMS path: {relative!r}")
        if relative in entries:
            raise ValidationError(f"duplicate SHA256SUMS path: {relative}")
        path = (root / Path(relative)).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError as exc:
            raise ValidationError(f"SHA256SUMS path escapes root: {relative}") from exc
        if not path.is_file():
            raise ValidationError(f"SHA256SUMS file missing: {relative}")
        actual = sha256_file(path).lower()
        if actual != digest.lower():
            raise ValidationError(f"SHA256SUMS mismatch for {relative}: {actual} != {digest.lower()}")
        entries[relative] = digest.upper()
    actual_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    }
    if actual_files != set(entries):
        raise ValidationError(
            f"SHA256SUMS inventory mismatch: unlisted={sorted(actual_files - set(entries))} missing={sorted(set(entries) - actual_files)}"
        )
    return entries


def _find_package_json(root: Path, names: list[str], label: str) -> Path:
    matches = [root / name for name in names if (root / name).is_file()]
    if len(matches) != 1:
        raise ValidationError(f"incoming package must contain exactly one {label}, found {matches}")
    return matches[0]


def package_content_inventory_sha256(
    *,
    root: Path,
    inventory: dict[str, str],
    json_paths: list[Path],
) -> str:
    normalized = dict(inventory)
    for path in json_paths:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        normalized[relative] = content_only_json_sha256(path)
    return sha256_bytes(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def validate_incoming_package(
    incoming_package: Path,
    incoming_csv: Path,
    incoming_fields: list[str],
    incoming_rows: list[dict[str, str]],
    model_key: str,
    model_record: dict[str, Any],
) -> dict[str, Any]:
    if not incoming_package.is_dir():
        raise ValidationError("prepare requires a sealed incoming package directory, not a bare CSV")
    inventory = audit_package_sha256sums(incoming_package)
    relative_results = incoming_csv.resolve().relative_to(incoming_package.resolve()).as_posix()
    if relative_results not in inventory:
        raise ValidationError("incoming results CSV is not listed in SHA256SUMS")
    manifest_path = _find_package_json(
        incoming_package,
        ["source_manifest.json", "manifest.json", "final_manifest.json", "provenance/source_manifest.json"],
        "source manifest",
    )
    manifest = read_json(manifest_path)
    if str(manifest.get("model_key", "")) != model_key:
        raise ValidationError(f"package model_key mismatch: {manifest.get('model_key')!r} != {model_key!r}")
    if int(manifest.get("row_count", -1)) != 200 or len(incoming_rows) != 200:
        raise ValidationError("incoming package is not a full 200-case run")
    if manifest.get("test_limit", "MISSING") is not None:
        raise ValidationError("incoming package must record TEST_LIMIT=None")
    run_label = str(manifest.get("run_label", "")).strip()
    if not run_label or "smoke" in run_label.casefold() or "5case" in run_label.casefold():
        raise ValidationError(f"incoming run label is missing or smoke-like: {run_label!r}")
    runtime_sha = str(manifest.get("runtime_sha", "")).strip()
    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", runtime_sha):
        raise ValidationError("incoming package runtime_sha is missing or invalid")
    source_wide_sha = str(manifest.get("source_wide_sha256", "")).strip()
    if source_wide_sha and runtime_sha.upper() == source_wide_sha.upper():
        raise ValidationError("incoming package runtime_sha must not be the source wide CSV hash")
    runtime_sha_status = str(manifest.get("runtime_sha_status", "confirmed")).strip()
    if runtime_sha_status not in {"confirmed", "inferred"}:
        raise ValidationError(f"incoming package runtime_sha_status is invalid: {runtime_sha_status!r}")
    runtime_sha_note = str(manifest.get("runtime_sha_note", "")).strip()
    if runtime_sha_status != "confirmed" and not runtime_sha_note:
        raise ValidationError("incoming package inferred runtime_sha requires runtime_sha_note")
    recorded_results = str(manifest.get("results_csv_sha256", "")).upper()
    if recorded_results != sha256_file(incoming_csv):
        raise ValidationError("source manifest final-wide/results hash mismatch")

    promotion_path = _find_package_json(
        incoming_package,
        ["promotion_audit.json", "audit/promotion_audit.json"],
        "promotion audit",
    )
    repair_path = _find_package_json(
        incoming_package,
        ["repair_evidence.json", "audit/repair_evidence.json"],
        "repair evidence",
    )
    promotion = read_json(promotion_path)
    repair = read_json(repair_path)
    if int(promotion.get("case_count", -1)) != 200 or promotion.get("test_limit", "MISSING") is not None:
        raise ValidationError("promotion audit does not prove a full 200-case TEST_LIMIT=None run")
    if int(promotion.get("unresolved_cells", -1)) != 0:
        raise ValidationError("promotion audit reports unresolved cells")
    if repair.get("repair_complete") is not True or int(repair.get("unresolved_cells", -1)) != 0:
        raise ValidationError("repair evidence is incomplete or unresolved")

    provider_column = f"Provider_{model_key}"
    returned_column = f"OpenRouter_Response_Model_{model_key}"
    request_extra_column = f"Actual_Request_Extra_{model_key}"
    require_columns(incoming_fields, [provider_column, returned_column, request_extra_column], "incoming package routing")
    expected_provider = normalize_diagnosis(model_record.get("provider_value", ""))
    expected_returned = str(model_record.get("returned_model_pattern", "")).casefold()
    for row in incoming_rows:
        case_id = str(row.get(CASE_KEY, ""))
        provider = normalize_diagnosis(row.get(provider_column, ""))
        if not provider or (expected_provider and expected_provider not in provider and provider not in expected_provider):
            raise ValidationError(f"provider routing mismatch for case {case_id}: {row.get(provider_column)!r}")
        returned = str(row.get(returned_column, "")).casefold()
        if expected_returned and expected_returned not in returned:
            raise ValidationError(f"returned-model mismatch for case {case_id}: {row.get(returned_column)!r}")
        request_extra_required = bool(model_record.get("required_request_extra"))
        request_extra: Any = None
        if model_record.get("provider_route") == "openrouter_provider_locked" or request_extra_required:
            try:
                request_extra = json.loads(str(row.get(request_extra_column, "{}")) or "{}")
            except json.JSONDecodeError as exc:
                raise ValidationError(f"invalid request-extra JSON for case {case_id}") from exc
        if model_record.get("provider_route") == "openrouter_provider_locked":
            provider_policy = request_extra.get("provider") if isinstance(request_extra, dict) else None
            if not isinstance(provider_policy, dict) or provider_policy.get("allow_fallbacks") is not False:
                raise ValidationError(f"provider lock evidence missing for case {case_id}")
        required_extra = model_record.get("required_request_extra")
        if isinstance(required_extra, dict):
            if not isinstance(request_extra, dict):
                raise ValidationError(f"required request-extra evidence missing for case {case_id}")
            for key, expected in sorted(required_extra.items()):
                if request_extra.get(key) != expected:
                    raise ValidationError(
                        f"required request-extra mismatch for case {case_id}: {key}={request_extra.get(key)!r}"
                    )
    content_inventory_sha = package_content_inventory_sha256(
        root=incoming_package,
        inventory=inventory,
        json_paths=[manifest_path, promotion_path, repair_path],
    )
    return {
        "inventory": inventory,
        "inventory_sha256": sha256_file(incoming_package / "SHA256SUMS"),
        "content_inventory_sha256": content_inventory_sha,
        "source_manifest_path": manifest_path,
        "source_manifest_sha256": sha256_file(manifest_path),
        "promotion_audit_path": promotion_path,
        "promotion_audit_sha256": sha256_file(promotion_path),
        "repair_evidence_path": repair_path,
        "repair_evidence_sha256": sha256_file(repair_path),
        "run_label": run_label,
        "runtime_sha": runtime_sha,
        "runtime_sha_status": runtime_sha_status,
        "runtime_sha_note": runtime_sha_note,
    }


def content_only_payload(value: Any) -> Any:
    """Remove location-only provenance from a nested identity payload."""
    if isinstance(value, dict):
        return {
            key: content_only_payload(item)
            for key, item in value.items()
            if key not in {"path", "source_wide", "incoming_package", "incoming_results_csv", "repo_root", "source_root"}
            and not key.endswith("_path")
            and not key.endswith("_paths")
        }
    if isinstance(value, list):
        return [content_only_payload(item) for item in value]
    return value


def content_only_json_sha256(path: Path) -> str:
    payload = content_only_payload(read_json(path))
    return sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def validate_parent_authority_inputs(
    *,
    parent_wide: Path,
    parent_final_long_master: Path,
    parent_authority_manifest: Path,
    blind_map_path: Path,
) -> dict[str, Any]:
    authority = read_json(parent_authority_manifest)
    schema = str(authority.get("schema_version", ""))
    if schema == "radle_v2_base_authority.v1":
        checks = (
            ("parent wide", parent_wide, authority.get("base_combined_wide", {})),
            ("parent final master", parent_final_long_master, authority.get("base_final_long_master", {})),
            ("parent blind map", blind_map_path, authority.get("base_blinding_key", {})),
        )
        for label, path, descriptor in checks:
            expected = str(descriptor.get("sha256", "")).upper()
            actual = sha256_file(path)
            if actual != expected:
                raise ValidationError(f"{label} does not match base authority: {actual} != {expected}")
        return {
            "authority_type": "base",
            "parent_chain_id": "BASE_V2_20260706",
            "authority_manifest_sha256": content_only_json_sha256(parent_authority_manifest),
        }
    if schema == "radle_v2_committed_marker.v1":
        committed_root = parent_authority_manifest.parent
        audit = audit_finalized_admission(committed_root, require_committed=True)
        append_manifest = read_json(committed_root / "append_manifest.json")
        outputs = append_manifest.get("outputs", {})
        expected_wide = committed_root / str(outputs.get("combined_wide", "combined_wide/RadLE_v2_results_final.csv"))
        expected_long = committed_root / str(outputs.get("final_long_master", "final/radle_v2_final_long_master.csv"))
        expected_blind = committed_root / "roster" / "blind_label_map.csv"
        supplied = [parent_wide.resolve(), parent_final_long_master.resolve(), blind_map_path.resolve()]
        expected = [expected_wide.resolve(), expected_long.resolve(), expected_blind.resolve()]
        if supplied != expected:
            raise ValidationError(f"committed parent inputs do not match committed root: {supplied} != {expected}")
        marker_chain = str(authority.get("finalization_id", ""))
        if marker_chain != str(audit.get("finalization_id", "")):
            raise ValidationError("committed parent chain identity mismatch")
        return {
            "authority_type": "committed",
            "parent_chain_id": marker_chain,
            "authority_manifest_sha256": content_only_json_sha256(parent_authority_manifest),
            "append_manifest_sha256": sha256_file(committed_root / "append_manifest.json"),
            "checksum_inventory_sha256": sha256_file(committed_root / "SHA256SUMS"),
        }
    raise ValidationError(f"unsupported parent authority schema: {schema!r}")


def project_one_model_package(
    *,
    source_wide: Path,
    model_key: str,
    output_package: Path,
    runtime_sha: str,
    runtime_sha_status: str = "confirmed",
    runtime_sha_note: str = "",
    source_manifest_path: Path | None = None,
    source_model_key: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    source_fields, source_rows = read_csv_table(source_wide)
    require_columns(source_fields, KEY_COLUMNS, "source wide")
    source_model_keys = discover_model_keys(source_fields)
    source_model_key = str(source_model_key or model_key).strip()
    if source_model_key not in source_model_keys:
        raise ValidationError(f"source model {source_model_key!r} not found in source families {source_model_keys}")
    source_selected_fields = KEY_COLUMNS + model_result_columns(source_model_key)
    selected_fields = KEY_COLUMNS + model_result_columns(model_key)
    require_columns(source_fields, source_selected_fields, "source wide")
    rows_by_case = index_by_case(source_rows, "source wide")
    if len(rows_by_case) != len(source_rows):
        raise ValidationError("source wide case index mismatch")
    if len(source_rows) != 200:
        raise ValidationError(f"one-model projection requires a full 200-case source, got {len(source_rows)}")
    runtime_sha = runtime_sha.strip()
    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", runtime_sha):
        raise ValidationError("project-one-model requires an explicit 40-64 hex runtime SHA")
    source_wide_sha = sha256_file(source_wide)
    if runtime_sha.upper() == source_wide_sha.upper():
        raise ValidationError("runtime SHA must not be the source wide CSV hash")
    runtime_sha_status = runtime_sha_status.strip()
    if runtime_sha_status not in {"confirmed", "inferred"}:
        raise ValidationError(f"runtime SHA status must be confirmed or inferred, got {runtime_sha_status!r}")
    runtime_sha_note = runtime_sha_note.strip()
    if runtime_sha_status != "confirmed" and not runtime_sha_note:
        raise ValidationError("inferred runtime SHA requires a provenance note")
    source_manifest_evidence: dict[str, Any] = {}
    if source_manifest_path is not None:
        if not source_manifest_path.is_file():
            raise ValidationError(f"source manifest does not exist: {source_manifest_path}")
        source_manifest = read_json(source_manifest_path)
        source_manifest_evidence = {
            "source_manifest_sha256": sha256_file(source_manifest_path),
            "source_manifest_content_sha256": content_only_json_sha256(source_manifest_path),
            "source_manifest_test_limit": source_manifest.get("test_limit", "MISSING"),
            "source_manifest_runtime_sha_present": bool(str(source_manifest.get("runtime_sha", "")).strip()),
        }
    projected_rows: list[dict[str, object]] = []
    for row in sorted(source_rows, key=lambda item: case_sort_key(str(item.get(CASE_KEY, "")))):
        projected: dict[str, object] = {field: row.get(field, "") for field in KEY_COLUMNS}
        for suffix in MODEL_SUFFIXES:
            projected[f"{suffix}_{model_key}"] = row.get(f"{suffix}_{source_model_key}", "")
        projected_rows.append(projected)
    projection_payload = {
        "schema_version": "radle_v2_one_model_projection.v1",
        "model_key": model_key,
        "source_model_key": source_model_key,
        "source_wide_sha256": source_wide_sha,
        "source_model_keys": source_model_keys,
        "source_selected_fields": source_selected_fields,
        "selected_fields": selected_fields,
        "row_count": len(projected_rows),
        "test_limit": None,
        "run_label": f"projected_full_{model_key}",
        "runtime_sha": runtime_sha.lower(),
        "runtime_sha_status": runtime_sha_status,
        "runtime_sha_note": runtime_sha_note,
        "source_manifest_evidence": source_manifest_evidence,
    }
    projection_id = compute_intake_id(projection_payload)
    receipt = {
        "projection_id": projection_id,
        "model_key": model_key,
        "source_model_key": source_model_key,
        "source_model_keys": source_model_keys,
        "selected_field_count": len(selected_fields),
        "row_count": len(projected_rows),
        "source_wide_sha256": projection_payload["source_wide_sha256"],
    }
    if dry_run:
        receipt["projection_state"] = "DRY_RUN_VALIDATED"
        return receipt
    if output_package.exists() and any(output_package.iterdir()):
        raise ValidationError(f"refusing to write into nonempty output package: {output_package}")
    output_package.mkdir(parents=True, exist_ok=True)
    results_path = output_package / "results.csv"
    write_csv_table(results_path, selected_fields, projected_rows)
    source_manifest_path = output_package / "source_manifest.json"
    manifest = dict(projection_payload)
    manifest["projection_id"] = projection_id
    manifest["results_csv_sha256"] = sha256_file(results_path)
    write_json(source_manifest_path, manifest)
    promotion_path = output_package / "promotion_audit.json"
    write_json(promotion_path, {
        "schema_version": "radle_v2_projected_promotion_audit.v1",
        "case_count": len(projected_rows),
        "test_limit": None,
        "unresolved_cells": 0,
        "model_key": model_key,
    })
    repair_path = output_package / "repair_evidence.json"
    write_json(repair_path, {
        "schema_version": "radle_v2_projected_repair_evidence.v1",
        "repair_complete": True,
        "unresolved_cells": 0,
        "model_key": model_key,
    })
    write_sha256sums(output_package, [promotion_path, repair_path, results_path, source_manifest_path])
    receipt["projection_state"] = "PROJECTED"
    receipt["output_package"] = str(output_package.resolve())
    receipt["results_csv_sha256"] = manifest["results_csv_sha256"]
    return receipt


def prepare_incremental_admission(
    *,
    parent_wide: Path,
    parent_final_long_master: Path,
    parent_authority_manifest: Path,
    blind_map_path: Path,
    incoming_package: Path,
    model_key: str,
    roster_path: Path,
    variants_path: Path,
    states_path: Path,
    output_root: Path,
    repo_root: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    parent_wide_fields, parent_wide_rows = read_csv_table(parent_wide)
    parent_long_fields, parent_long_rows = read_csv_table(parent_final_long_master)
    incoming_csv = find_incoming_results_csv(incoming_package)
    incoming_fields, incoming_rows = read_csv_table(incoming_csv)
    blind_fields, blind_rows = read_csv_table(blind_map_path)
    roster = read_json(roster_path)
    terminal_policy = read_json(states_path)

    require_columns(parent_wide_fields, KEY_COLUMNS, "parent wide")
    require_columns(incoming_fields, KEY_COLUMNS, "incoming wide")
    if parent_long_fields != FINAL_LONG_MASTER_FIELDS:
        raise ValidationError(f"parent final master schema mismatch: {parent_long_fields}")
    if blind_fields != BLIND_MAP_FIELDS:
        raise ValidationError(f"parent blind-map schema mismatch: {blind_fields}")
    incoming_model_keys = discover_model_keys(incoming_fields)
    if incoming_model_keys != [model_key]:
        raise ValidationError(f"incoming package must contain exactly {model_key}, got {incoming_model_keys}")
    if model_key in discover_model_keys(parent_wide_fields):
        raise ValidationError(f"parent wide already contains model {model_key}")
    require_columns(incoming_fields, model_result_columns(model_key), "incoming wide")

    case_ids = validate_case_sets(parent_wide_rows, incoming_rows)
    parent_by_case = index_by_case(parent_wide_rows, "parent wide")
    incoming_by_case = index_by_case(incoming_rows, "incoming wide")
    validate_key_metadata(parent_wide_rows, incoming_by_case, KEY_COLUMNS)
    validate_parent_wide_long_reconciliation(parent_wide_fields, parent_wide_rows, parent_long_fields, parent_long_rows)
    ground_truth_snapshot = build_ground_truth_snapshot(parent_long_rows, case_ids)
    ground_truth_by_case = {row[CASE_KEY]: row["Ground_Truth_Diagnosis"] for row in ground_truth_snapshot}
    prior_score_reuse, prior_score_rows = build_prior_score_reuse_snapshot(parent_long_rows)
    model_record = find_model_record(roster, model_key)
    package_evidence = validate_incoming_package(
        incoming_package,
        incoming_csv,
        incoming_fields,
        incoming_rows,
        model_key,
        model_record,
    )
    parent_authority = validate_parent_authority_inputs(
        parent_wide=parent_wide,
        parent_final_long_master=parent_final_long_master,
        parent_authority_manifest=parent_authority_manifest,
        blind_map_path=blind_map_path,
    )
    existing_blind_labels = {str(row.get("model_blinded", "")) for row in blind_rows}
    if str(model_record.get("blind_label", "")) in existing_blind_labels:
        raise ValidationError(f"new model blind label already exists in parent map: {model_record.get('blind_label')}")
    parent_run_ids = {str(row.get("run_id", "")).strip() for row in parent_long_rows}
    if len(parent_run_ids) != 1 or "" in parent_run_ids:
        raise ValidationError(f"parent final master must contain one nonblank run_id, got {sorted(parent_run_ids)}")
    parent_run_id = next(iter(parent_run_ids))

    incoming_model_columns = model_result_columns(model_key)
    one_model_fields = KEY_COLUMNS + incoming_model_columns
    one_model_rows = [
        {field: incoming_by_case[case_id].get(field, "") for field in one_model_fields}
        for case_id in case_ids
    ]
    combined_fields = parent_wide_fields + [field for field in incoming_model_columns if field not in parent_wide_fields]
    combined_rows = []
    for case_id in case_ids:
        combined = dict(parent_by_case[case_id])
        for field in incoming_model_columns:
            combined[field] = incoming_by_case[case_id].get(field, "")
        combined_rows.append(combined)

    long_delta, state_rows, terminal_counts, judge_worklist = build_new_model_long_delta(
        parent_long_fields,
        one_model_rows,
        one_model_fields,
        model_key,
        model_record,
        ground_truth_by_case,
        terminal_policy,
        prior_score_reuse,
        parent_run_id=parent_run_id,
    )
    scorer_fields, scorer_rows = build_scorer_view(combined_fields, combined_rows)
    if not variants_path.is_file():
        raise ValidationError(f"accepted-variants snapshot missing: {variants_path}")

    requirement_paths = [
        repo_root / "Documents" / "requirements_radle_v2_incremental_model_admission.md",
        repo_root / "Documents" / "radle_v2_incremental_model_pipeline_requirements_study.md",
    ]
    missing_requirements = [str(path) for path in requirement_paths if not path.is_file()]
    if missing_requirements:
        raise ValidationError(f"requirements inputs missing: {missing_requirements}")
    requirements_hashes = {path.name: canonical_text_sha256(path) for path in requirement_paths}
    authority_config = read_json(parent_authority_manifest) if read_json(parent_authority_manifest).get("schema_version") == "radle_v2_base_authority.v1" else read_json(repo_root / "config" / "radle_v2_base_authority.json")
    expected_requirements = authority_config.get("requirements", {})
    for name, digest in requirements_hashes.items():
        expected = str(expected_requirements.get(name, "")).upper()
        if digest != expected:
            raise ValidationError(f"requirements hash mismatch for {name}: {digest} != {expected}")

    input_hashes = {
        "parent_wide": sha256_file(parent_wide),
        "parent_final_long_master": sha256_file(parent_final_long_master),
        "parent_blind_map": sha256_file(blind_map_path),
        "parent_authority_manifest": parent_authority["authority_manifest_sha256"],
        "incoming_results_csv": sha256_file(incoming_csv),
        "package_checksum_inventory": package_evidence["content_inventory_sha256"],
        "package_source_manifest": content_only_json_sha256(package_evidence["source_manifest_path"]),
        "package_promotion_audit": content_only_json_sha256(package_evidence["promotion_audit_path"]),
        "package_repair_evidence": content_only_json_sha256(package_evidence["repair_evidence_path"]),
        "roster": canonical_json_sha256(roster_path),
        "terminal_states": canonical_json_sha256(states_path),
        "variants": sha256_file(variants_path),
        "prior_score_reuse_snapshot": sha256_bytes(serialize_csv_table(PRIOR_SCORE_REUSE_FIELDS, prior_score_rows)),
        "ground_truth_snapshot": sha256_bytes(serialize_csv_table([CASE_KEY, "Ground_Truth_Diagnosis", "Ground_Truth_Normalized"], ground_truth_snapshot)),
        "normalizer_code": canonical_text_sha256(Path(__file__)),
        "requirements": requirements_hashes,
    }
    input_paths = {
        "parent_wide": str(parent_wide),
        "parent_final_long_master": str(parent_final_long_master),
        "parent_blind_map": str(blind_map_path),
        "parent_authority_manifest": str(parent_authority_manifest),
        "incoming_results_csv": str(incoming_csv),
        "roster": str(roster_path),
        "terminal_states": str(states_path),
        "variants": str(variants_path),
    }
    intake_payload = {
        "schema_version": "radle_v2_intake_identity.v2",
        "model_key": model_key,
        "case_count": len(case_ids),
        "case_triplet_sha256": compute_case_triplet_sha256(parent_wide_rows),
        "parent_authority": parent_authority,
        "input_hashes": input_hashes,
        "normalizer_version": terminal_policy.get("normalizer_version"),
        "model_blinded": model_record.get("blind_label", ""),
        "package_run_label": package_evidence["run_label"],
        "package_runtime_sha": package_evidence["runtime_sha"],
    }
    intake_id = compute_intake_id(intake_payload)

    receipt = {
        "intake_id": intake_id,
        "model_key": model_key,
        "model_blinded": model_record.get("blind_label", ""),
        "case_count": len(case_ids),
        "incoming_results_csv": str(incoming_csv),
        "terminal_state_counts": dict(sorted(terminal_counts.items())),
        "judge_worklist_rows": len(judge_worklist),
        "input_hashes": input_hashes,
        "input_paths": input_paths,
        "parent_chain_id": parent_authority["parent_chain_id"],
    }
    if dry_run:
        receipt["transaction_state"] = "DRY_RUN_VALIDATED"
        return receipt

    staging_root = output_root / intake_id
    manifest_path = staging_root / "append_input_manifest.json"
    if manifest_path.exists():
        existing = read_json(manifest_path)
        if existing.get("intake_id") == intake_id:
            audit_prepared_staging(staging_root)
            receipt["transaction_state"] = existing.get("transaction_state", "ADJUDICATION_PENDING")
            receipt["staging_root"] = str(staging_root.resolve())
            receipt["already_prepared"] = True
            return receipt
        raise ValidationError(f"staging root collision with different manifest: {staging_root}")

    staged_files: dict[str, Path] = {}

    def staged(label: str, relative: str) -> Path:
        path = staging_root / relative
        staged_files[label] = path
        return path

    write_csv_table(staged("canonical_ground_truth_snapshot", "canonical_ground_truth_snapshot.csv"), [CASE_KEY, "Ground_Truth_Diagnosis", "Ground_Truth_Normalized"], ground_truth_snapshot)
    write_csv_table(staged("prior_score_reuse_snapshot", "prior_score_reuse_snapshot.csv"), PRIOR_SCORE_REUSE_FIELDS, prior_score_rows)
    write_csv_table(staging_root / "one_model_final_wide.csv", one_model_fields, one_model_rows)
    staged_files["one_model_final_wide"] = staging_root / "one_model_final_wide.csv"
    write_csv_table(staging_root / "combined_wide" / "RadLE_v2_results_final.csv", combined_fields, combined_rows)
    staged_files["combined_wide"] = staging_root / "combined_wide" / "RadLE_v2_results_final.csv"
    write_csv_table(staging_root / "scorer" / "scorer_view.csv", scorer_fields, scorer_rows)
    staged_files["scorer_view"] = staging_root / "scorer" / "scorer_view.csv"
    write_csv_table(staged("new_model_long_delta", "new_model_long_delta.csv"), FINAL_LONG_MASTER_FIELDS, long_delta)
    write_csv_table(staged("adjudication_state", "adjudication_state.csv"), ADJUDICATION_STATE_FIELDS, state_rows)
    write_csv_table(staged("judge_worklist", "judge_worklist.csv"), RADIOLOGIST_QUEUE_FIELDS, judge_worklist)
    shutil.copyfile(variants_path, staged("accepted_variants_snapshot", "accepted_variants_snapshot.csv"))
    write_json(staged("requirements_snapshot", "requirements_snapshot.json"), {
        "schema_version": "radle_v2_requirements_snapshot.v1",
        "model_key": model_key,
        "hashes": requirements_hashes,
    })
    write_json(staged("source_manifest", "provenance/source_manifest.json"), {
        "schema_version": "radle_v2_source_manifest.v1",
        "model_key": model_key,
        "incoming_package": str(incoming_package),
        "incoming_results_csv": str(incoming_csv),
        "input_hashes": input_hashes,
        "input_paths": input_paths,
    })
    write_json(staged("promotion_audit", "audit/promotion_audit.json"), {
        "schema_version": "radle_v2_promotion_audit.v1",
        "case_count": len(case_ids),
        "incoming_model_keys": incoming_model_keys,
        "metadata_match": True,
        "parent_wide_long_reconciled": True,
    })
    write_json(staged("terminal_state_audit", "audit/terminal_state_audit.json"), {
        "schema_version": "radle_v2_terminal_state_audit.v1",
        "terminal_state_counts": dict(sorted(terminal_counts.items())),
        "judge_worklist_rows": len(judge_worklist),
    })
    write_json(staged("model_roster", "roster/model_roster.json"), roster)
    extended_blind_rows = list(blind_rows) + [{
        "model_blinded": model_record.get("blind_label", ""),
        "model_key": model_key,
        "provider": model_record.get("provider_value", ""),
    }]
    write_csv_table(staged("blind_label_map", "roster/blind_label_map.csv"), BLIND_MAP_FIELDS, extended_blind_rows)
    package_snapshot = staging_root / "inputs" / "package"
    shutil.copytree(incoming_package, package_snapshot)
    write_json(staged("package_inventory_snapshot", "inputs/package_inventory.json"), {
        "schema_version": "radle_v2_package_inventory_snapshot.v1",
        "content_inventory_sha256": package_evidence["content_inventory_sha256"],
        "raw_sha256sums_sha256": package_evidence["inventory_sha256"],
        "entries": package_evidence["inventory"],
    })
    for label, source, relative in (
        ("parent_wide", parent_wide, "parent/parent_wide.csv"),
        ("parent_final_long_master", parent_final_long_master, "parent/parent_final_long_master.csv"),
        ("parent_blind_label_map", blind_map_path, "parent/blind_label_map.csv"),
        ("parent_authority_manifest", parent_authority_manifest, "parent/parent_authority_manifest.json"),
        ("incoming_results_csv", incoming_csv, "inputs/incoming_results.csv"),
        ("terminal_states", states_path, "inputs/terminal_states.json"),
        ("package_source_manifest", package_evidence["source_manifest_path"], "inputs/package_source_manifest.json"),
        ("package_promotion_audit", package_evidence["promotion_audit_path"], "inputs/package_promotion_audit.json"),
        ("package_repair_evidence", package_evidence["repair_evidence_path"], "inputs/package_repair_evidence.json"),
        ("package_checksum_inventory", incoming_package / "SHA256SUMS", "inputs/package_SHA256SUMS"),
    ):
        destination = staged(label, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    code_snapshot = staged("normalizer_source", "provenance/normalizer_source.py")
    code_snapshot.parent.mkdir(parents=True, exist_ok=True)
    code_snapshot.write_bytes(canonical_text_bytes(Path(__file__)))
    manifest = {
        "schema_version": "radle_v2_append_input_manifest.v2",
        "intake_id": intake_id,
        "transaction_state": "ADJUDICATION_PENDING",
        "model_key": model_key,
        "model_blinded": model_record.get("blind_label", ""),
        "case_count": len(case_ids),
        "input_hashes": input_hashes,
        "input_paths": input_paths,
        "intake_identity": intake_payload,
        "parent_chain_id": parent_authority["parent_chain_id"],
        "terminal_state_counts": dict(sorted(terminal_counts.items())),
        "judge_worklist_rows": len(judge_worklist),
        "outputs": {
            label: {"path": path.relative_to(staging_root).as_posix(), "sha256": sha256_file(path)}
            for label, path in sorted(staged_files.items())
        },
    }
    write_json(manifest_path, manifest)
    receipt["transaction_state"] = "ADJUDICATION_PENDING"
    receipt["staging_root"] = str(staging_root.resolve())
    receipt["already_prepared"] = False
    return receipt


def audit_prepared_staging(staging_root: Path) -> dict[str, Any]:
    manifest_path = staging_root / "append_input_manifest.json"
    if not manifest_path.exists():
        raise ValidationError(f"append_input_manifest.json missing under {staging_root}")
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != "radle_v2_append_input_manifest.v2":
        raise ValidationError(f"unsupported prepared manifest schema: {manifest.get('schema_version')!r}")
    if manifest.get("transaction_state") != "ADJUDICATION_PENDING":
        raise ValidationError(f"prepared staging has wrong transaction_state: {manifest.get('transaction_state')!r}")
    if (staging_root / "COMMITTED.json").exists():
        raise ValidationError("prepared staging must not contain COMMITTED.json")

    outputs = manifest.get("outputs", {})
    required_output_keys = [
        "canonical_ground_truth_snapshot",
        "prior_score_reuse_snapshot",
        "one_model_final_wide",
        "combined_wide",
        "scorer_view",
        "new_model_long_delta",
        "adjudication_state",
        "terminal_state_audit",
        "judge_worklist",
        "accepted_variants_snapshot",
        "requirements_snapshot",
        "model_roster",
        "blind_label_map",
        "parent_wide",
        "parent_final_long_master",
        "parent_blind_label_map",
        "parent_authority_manifest",
        "incoming_results_csv",
        "terminal_states",
        "package_source_manifest",
        "package_promotion_audit",
        "package_repair_evidence",
        "package_checksum_inventory",
        "package_inventory_snapshot",
        "normalizer_source",
    ]
    missing = [key for key in required_output_keys if key not in outputs]
    if missing:
        raise ValidationError(f"manifest missing output keys: {missing}")
    output_paths: dict[str, Path] = {}
    for key in required_output_keys:
        descriptor = outputs[key]
        if not isinstance(descriptor, dict) or not descriptor.get("path") or not descriptor.get("sha256"):
            raise ValidationError(f"invalid prepared output descriptor: {key}")
        path = (staging_root / str(descriptor["path"])).resolve()
        try:
            path.relative_to(staging_root.resolve())
        except ValueError as exc:
            raise ValidationError(f"prepared output escapes staging root: {key}") from exc
        output_paths[key] = path
    missing_paths = [str(path) for path in output_paths.values() if not path.exists()]
    if missing_paths:
        raise ValidationError(f"prepared output files missing: {missing_paths}")
    for key, path in output_paths.items():
        actual = sha256_file(path)
        expected = str(outputs[key]["sha256"]).upper()
        if actual != expected:
            raise ValidationError(f"prepared output SHA mismatch for {key}: {actual} != {expected}")

    identity = manifest.get("intake_identity")
    if not isinstance(identity, dict) or compute_intake_id(identity) != manifest.get("intake_id"):
        raise ValidationError("prepared intake identity does not recompute")

    case_count = int(manifest.get("case_count", 0))
    row_counts = {}
    for key in ["canonical_ground_truth_snapshot", "prior_score_reuse_snapshot", "one_model_final_wide", "combined_wide", "scorer_view", "new_model_long_delta", "adjudication_state", "judge_worklist"]:
        fields, rows = read_csv_table(output_paths[key])
        if key == "prior_score_reuse_snapshot" and fields != PRIOR_SCORE_REUSE_FIELDS:
            raise ValidationError(f"prior-score reuse snapshot schema mismatch: {fields}")
        if key == "new_model_long_delta" and fields != FINAL_LONG_MASTER_FIELDS:
            raise ValidationError(f"prepared delta schema mismatch: {fields}")
        if key == "adjudication_state" and fields != ADJUDICATION_STATE_FIELDS:
            raise ValidationError(f"adjudication-state schema mismatch: {fields}")
        if key == "judge_worklist" and fields != RADIOLOGIST_QUEUE_FIELDS:
            raise ValidationError(f"judge-worklist schema mismatch: {fields}")
        row_counts[key] = len(rows)
    for key in ["canonical_ground_truth_snapshot", "one_model_final_wide", "combined_wide", "scorer_view", "new_model_long_delta", "adjudication_state"]:
        if row_counts[key] != case_count:
            raise ValidationError(f"{key} row count {row_counts[key]} != case_count {case_count}")
    if row_counts["judge_worklist"] != int(manifest.get("judge_worklist_rows", -1)):
        raise ValidationError("judge_worklist row count mismatch")

    terminal_audit = read_json(output_paths["terminal_state_audit"])
    if terminal_audit.get("terminal_state_counts") != manifest.get("terminal_state_counts"):
        raise ValidationError("terminal_state_counts mismatch between manifest and audit")

    parent_long_fields, parent_long_rows = read_csv_table(output_paths["parent_final_long_master"])
    if parent_long_fields != FINAL_LONG_MASTER_FIELDS:
        raise ValidationError("prepared parent final-master schema mismatch")
    _, expected_prior_score_rows = build_prior_score_reuse_snapshot(parent_long_rows)
    prior_score_fields, prior_score_rows = read_csv_table(output_paths["prior_score_reuse_snapshot"])
    if prior_score_fields != PRIOR_SCORE_REUSE_FIELDS:
        raise ValidationError("prior-score reuse snapshot schema mismatch")
    if expected_prior_score_rows != prior_score_rows:
        raise ValidationError("prior-score reuse snapshot does not independently recompute")
    prior_score_reuse, _ = build_prior_score_reuse_snapshot(parent_long_rows)

    delta_fields, delta_rows = read_csv_table(output_paths["new_model_long_delta"])
    state_fields, state_rows = read_csv_table(output_paths["adjudication_state"])
    one_fields, one_rows = read_csv_table(output_paths["one_model_final_wide"])
    _, gt_rows = read_csv_table(output_paths["canonical_ground_truth_snapshot"])
    _, worklist_rows = read_csv_table(output_paths["judge_worklist"])
    policy = read_json(output_paths["terminal_states"])
    model_key = str(manifest.get("model_key", ""))
    diagnosis_column = f"Diagnosis_{model_key}"
    likert_column = f"Likert_{model_key}"
    one_by_case = index_by_case(one_rows, "staged one-model wide")
    gt_by_case = {row[CASE_KEY]: row["Ground_Truth_Diagnosis"] for row in gt_rows}
    delta_by_key = {(row[CASE_KEY], row["model_blinded"]): row for row in delta_rows}
    state_by_key: dict[tuple[str, str], dict[str, str]] = {}
    recomputed_counts: Counter[str] = Counter()
    recomputed_worklist: list[dict[str, str]] = []
    for state_row in state_rows:
        key = (state_row.get(CASE_KEY, ""), state_row.get("model_blinded", ""))
        if key in state_by_key:
            raise ValidationError(f"duplicate adjudication-state key: {key}")
        state_by_key[key] = state_row
        delta = delta_by_key.get(key)
        if delta is None:
            raise ValidationError(f"adjudication-state key missing from delta: {key}")
        incoming = one_by_case.get(key[0])
        if incoming is None:
            raise ValidationError(f"adjudication-state case missing from one-model wide: {key[0]}")
        terminal_row = {
            CASE_KEY: key[0],
            "diagnosis": incoming.get(diagnosis_column, ""),
            "likert": incoming.get(likert_column, ""),
            "package_failure": state_row.get("package_failure", "false"),
        }
        actual_state = classify_terminal_state(terminal_row, gt_by_case[key[0]], policy, prior_score_reuse)
        if state_row.get("terminal_state") != actual_state:
            raise ValidationError(f"adjudication-state classification mismatch for {key}: {state_row.get('terminal_state')} != {actual_state}")
        if state_row.get("candidate") != model_key:
            raise ValidationError(f"adjudication-state candidate mismatch for {key}")
        if state_row.get("normalized_ground_truth") != normalize_diagnosis(gt_by_case[key[0]]):
            raise ValidationError(f"normalized ground truth mismatch for {key}")
        if state_row.get("normalized_diagnosis") != normalize_diagnosis(incoming.get(diagnosis_column, "")):
            raise ValidationError(f"normalized diagnosis mismatch for {key}")
        if state_row.get("source_row_sha256") != row_sha256(incoming, one_fields):
            raise ValidationError(f"source-row hash mismatch for {key}")
        if actual_state == "canonical_exact":
            expected_auto = "1"
        elif actual_state == "previous_authoritative_score":
            expected_auto = prior_score_reuse[(key[0], normalize_diagnosis(incoming.get(diagnosis_column, "")))]["score_binary"]
        elif actual_state in {"provider_or_parse_failure", "invalid_likert", "idk_exact", "idk_approved_typo"}:
            expected_auto = "0"
        else:
            expected_auto = ""
        if state_row.get("automatic_score", "") != expected_auto:
            raise ValidationError(f"automatic score mismatch for {key}")
        expected_judge = str(actual_state == "judge_required")
        expected_rad = str(actual_state == "mandatory_radiologist")
        if state_row.get("requires_judge") != expected_judge or state_row.get("requires_radiologist") != expected_rad:
            raise ValidationError(f"routing flags mismatch for {key}")
        if delta.get("final_score_authoritative") or delta.get("final_score_source"):
            raise ValidationError(f"prepared delta score fields must be blank for {key}")
        recomputed_counts[actual_state] += 1
        if actual_state == "judge_required":
            recomputed_worklist.append({field: delta.get(field, "") for field in RADIOLOGIST_QUEUE_FIELDS})
    if set(state_by_key) != set(delta_by_key) or len(state_by_key) != case_count:
        raise ValidationError("prepared delta and adjudication-state keys differ")
    if dict(sorted(recomputed_counts.items())) != manifest.get("terminal_state_counts"):
        raise ValidationError("terminal-state counts do not independently recompute")
    recomputed_worklist.sort(key=lambda row: case_sort_key(row[CASE_KEY]))
    if recomputed_worklist != worklist_rows:
        raise ValidationError("judge worklist does not independently recompute")

    hashes = manifest.get("input_hashes", {})
    copied_hash_checks = {
        "parent_wide": sha256_file(output_paths["parent_wide"]),
        "parent_final_long_master": sha256_file(output_paths["parent_final_long_master"]),
        "parent_blind_map": sha256_file(output_paths["parent_blind_label_map"]),
        "incoming_results_csv": sha256_file(output_paths["incoming_results_csv"]),
        "terminal_states": canonical_json_sha256(output_paths["terminal_states"]),
        "package_source_manifest": content_only_json_sha256(output_paths["package_source_manifest"]),
        "package_promotion_audit": content_only_json_sha256(output_paths["package_promotion_audit"]),
        "package_repair_evidence": content_only_json_sha256(output_paths["package_repair_evidence"]),
        "normalizer_code": canonical_text_sha256(output_paths["normalizer_source"]),
    }
    for key, actual in copied_hash_checks.items():
        if actual != hashes.get(key):
            raise ValidationError(f"prepared copied-input hash mismatch for {key}: {actual} != {hashes.get(key)}")
    package_root = staging_root / "inputs" / "package"
    package_inventory = audit_package_sha256sums(package_root)
    package_snapshot = read_json(output_paths["package_inventory_snapshot"])
    if package_snapshot.get("entries") != package_inventory:
        raise ValidationError("staged package inventory differs from prepared snapshot")
    if package_snapshot.get("raw_sha256sums_sha256") != sha256_file(package_root / "SHA256SUMS"):
        raise ValidationError("staged package raw checksum inventory hash mismatch")
    package_json_paths = [
        _find_package_json(package_root, ["source_manifest.json", "manifest.json", "final_manifest.json", "provenance/source_manifest.json"], "source manifest"),
        _find_package_json(package_root, ["promotion_audit.json", "audit/promotion_audit.json"], "promotion audit"),
        _find_package_json(package_root, ["repair_evidence.json", "audit/repair_evidence.json"], "repair evidence"),
    ]
    content_inventory = package_content_inventory_sha256(root=package_root, inventory=package_inventory, json_paths=package_json_paths)
    if content_inventory != hashes.get("package_checksum_inventory") or content_inventory != package_snapshot.get("content_inventory_sha256"):
        raise ValidationError("staged package content-only inventory identity mismatch")

    return {
        "result": "PASS",
        "phase": "prepared",
        "intake_id": manifest.get("intake_id"),
        "model_key": manifest.get("model_key"),
        "case_count": case_count,
        "row_counts": row_counts,
        "terminal_state_counts": manifest.get("terminal_state_counts"),
    }


def audit_judge_evidence(staging_root: Path) -> dict[str, Any]:
    audit_prepared_staging(staging_root)
    manifest = read_json(staging_root / "append_input_manifest.json")
    evidence_root = staging_root / "judge_evidence"
    index_path = evidence_root / "judge_evidence_index.json"
    if not index_path.exists():
        raise ValidationError(f"judge_evidence_index.json missing under {evidence_root}")
    index = read_json(index_path)
    required = {
        "request_payloads": evidence_root / "request_payloads.jsonl",
        "judge_cache": evidence_root / "judge_cache.jsonl",
        "judge_results": evidence_root / "judge_results.jsonl",
        "agreement_locks": evidence_root / "agreement_locks.csv",
        "routing_audit": evidence_root / "radiologist_queue_routing_audit.json",
        "radiologist_queue": staging_root / "radiologist_queue.csv",
        "judge_config": evidence_root / "judge_config.json",
        "judge_prompt": evidence_root / "judge_prompt.txt",
    }
    for label, path in required.items():
        if not path.exists():
            raise ValidationError(f"{label} evidence file missing: {path}")
    indexed_files = index.get("files", {})
    for label, path in required.items():
        descriptor = indexed_files.get(label)
        if not isinstance(descriptor, dict):
            raise ValidationError(f"judge evidence index missing descriptor: {label}")
        if sha256_file(path) != str(descriptor.get("sha256", "")).upper():
            raise ValidationError(f"judge evidence SHA mismatch: {label}")
    queue_fields, queue_rows = read_csv_table(staging_root / "radiologist_queue.csv")
    if queue_fields != RADIOLOGIST_QUEUE_FIELDS:
        raise ValidationError(f"radiologist_queue.csv columns mismatch: {queue_fields}")
    lock_fields, lock_rows = read_csv_table(evidence_root / "agreement_locks.csv")
    if lock_fields != [CASE_KEY, "score", "score_source", "judge_count"]:
        raise ValidationError(f"agreement-lock columns mismatch: {lock_fields}")
    judge_result_rows = [
        json.loads(line)
        for line in (evidence_root / "judge_results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    request_rows = [
        json.loads(line)
        for line in (evidence_root / "request_payloads.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    cache_rows = [
        json.loads(line)
        for line in (evidence_root / "judge_cache.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    request_text = (evidence_root / "request_payloads.jsonl").read_text(encoding="utf-8")
    if str(manifest.get("model_key", "")) in request_text or str(manifest.get("model_blinded", "")) in request_text:
        raise ValidationError("judge request payload leaks model key or blind label")
    judge_config = read_json(evidence_root / "judge_config.json")
    configured_ids = [str(judge.get("requested_model_id", "")) for judge in judge_config.get("judges", [])]
    if len(configured_ids) != 2 or len(set(configured_ids)) != 2:
        raise ValidationError("judge evidence must configure two distinct judges")
    config_sha = canonical_json_sha256(evidence_root / "judge_config.json")
    prompt_sha = canonical_text_sha256(evidence_root / "judge_prompt.txt")
    worklist_fields, worklist_rows = read_csv_table(staging_root / "judge_worklist.csv")
    if worklist_fields != RADIOLOGIST_QUEUE_FIELDS:
        raise ValidationError("staged judge worklist schema mismatch")
    worklist_by_case = {row[CASE_KEY]: row for row in worklist_rows}
    if len(worklist_by_case) != len(worklist_rows):
        raise ValidationError("judge worklist has duplicate cases")
    requests_by_case: dict[str, dict[str, Any]] = {}
    for request in request_rows:
        case_id = str(request.get(CASE_KEY, ""))
        if case_id in requests_by_case or case_id not in worklist_by_case:
            raise ValidationError(f"invalid or duplicate judge request case: {case_id}")
        expected_payload = _request_payload(worklist_by_case[case_id])
        expected_sha = sha256_bytes(json.dumps(expected_payload, sort_keys=True).encode("utf-8"))
        if request.get("payload") != expected_payload or request.get("request_payload_sha256") != expected_sha:
            raise ValidationError(f"judge request payload mismatch for case {case_id}")
        requests_by_case[case_id] = request
    if set(requests_by_case) != set(worklist_by_case):
        raise ValidationError("judge request cases differ from worklist")

    results_by_case: dict[str, list[dict[str, Any]]] = {}
    cache_by_key = {str(row.get("cache_key", "")): row for row in cache_rows}
    if len(cache_by_key) != len(cache_rows):
        raise ValidationError("judge cache contains duplicate keys")
    identity = manifest.get("intake_identity", {})
    expected_case_fingerprint = identity.get("case_triplet_sha256", "")
    terminal_sha = canonical_json_sha256(staging_root / "inputs" / "terminal_states.json")
    variants_sha = sha256_file(staging_root / "accepted_variants_snapshot.csv")
    normalizer_sha = canonical_text_sha256(staging_root / "provenance" / "normalizer_source.py")
    for result in judge_result_rows:
        case_id = str(result.get(CASE_KEY, ""))
        if case_id not in worklist_by_case:
            raise ValidationError(f"judge result case not in worklist: {case_id}")
        requested = str(result.get("requested_judge_model_id", ""))
        if requested not in configured_ids or not model_id_matches_request(requested, result.get("returned_judge_model_id")):
            raise ValidationError(f"judge model identity mismatch for case {case_id}")
        if result.get("intake_id") != manifest.get("intake_id") or result.get("case_triplet_sha256") != expected_case_fingerprint:
            raise ValidationError(f"judge result intake/case fingerprint mismatch for case {case_id}")
        expected_row_sha = row_sha256(worklist_by_case[case_id], RADIOLOGIST_QUEUE_FIELDS)
        if result.get("worklist_row_sha256") != expected_row_sha:
            raise ValidationError(f"judge worklist-row hash mismatch for case {case_id}")
        if result.get("case_payload_sha256", result.get("exact_request_payload_sha256")) != requests_by_case[case_id]["request_payload_sha256"]:
            raise ValidationError(f"judge request hash mismatch for case {case_id}")
        evidence_values = {
            "judge_config_sha256": config_sha,
            "prompt_sha256": prompt_sha,
            "normalizer_code_sha256": normalizer_sha,
            "terminal_policy_sha256": terminal_sha,
            "variants_snapshot_sha256": variants_sha,
        }
        for field, expected in evidence_values.items():
            if result.get(field) != expected:
                raise ValidationError(f"judge evidence hash mismatch for {field} case {case_id}")
        cache_key = str(result.get("cache_key", ""))
        cache = cache_by_key.get(cache_key)
        if not cache or cache.get("result") != result:
            raise ValidationError(f"judge cache/result mismatch for case {case_id}")
        results_by_case.setdefault(case_id, []).append(result)

    recomputed_locks: list[dict[str, object]] = []
    recomputed_queue: list[dict[str, object]] = []
    for case_id in sorted(worklist_by_case, key=case_sort_key):
        results = results_by_case.get(case_id, [])
        parsed = [row for row in results if row.get("parse_status") == "parsed" and str(row.get("score")) in {"0", "1"}]
        requested_ids = {str(row.get("requested_judge_model_id", "")) for row in parsed}
        scores = {str(row.get("score")) for row in parsed}
        flags = any(bool(row.get("flag_for_review")) for row in results)
        if len(results) == 2 and len(parsed) == 2 and requested_ids == set(configured_ids) and len(scores) == 1 and not flags:
            recomputed_locks.append({CASE_KEY: case_id, "score": next(iter(scores)), "score_source": "ai_judges", "judge_count": "2"})
        else:
            recomputed_queue.append({field: worklist_by_case[case_id].get(field, "") for field in RADIOLOGIST_QUEUE_FIELDS})
    state_fields, state_rows = read_csv_table(staging_root / "adjudication_state.csv")
    if state_fields != ADJUDICATION_STATE_FIELDS:
        raise ValidationError("adjudication-state schema mismatch during judge audit")
    delta_by_key = {
        (row[CASE_KEY], row["model_blinded"]): row
        for row in read_csv_table(staging_root / "new_model_long_delta.csv")[1]
    }
    for state_row in state_rows:
        if state_row.get("requires_radiologist") == "True":
            delta = delta_by_key[(state_row[CASE_KEY], state_row["model_blinded"])]
            recomputed_queue.append({field: delta.get(field, "") for field in RADIOLOGIST_QUEUE_FIELDS})
    if recomputed_locks != lock_rows:
        raise ValidationError("agreement locks do not derive from valid two-judge evidence")
    if recomputed_queue != queue_rows:
        raise ValidationError("radiologist queue does not independently recompute")
    summary = index.get("summary", {})
    if int(summary.get("judge_result_rows", -1)) != len(judge_result_rows):
        raise ValidationError("judge result row count mismatch")
    if int(summary.get("locked_agreement_rows", -1)) != len(lock_rows):
        raise ValidationError("agreement lock row count mismatch")
    if int(summary.get("radiologist_queue_rows", -1)) != len(queue_rows):
        raise ValidationError("radiologist queue row count mismatch")
    return {
        "result": "PASS",
        "phase": "judge",
        "intake_id": manifest.get("intake_id"),
        "judge_result_rows": len(judge_result_rows),
        "locked_agreement_rows": len(lock_rows),
        "radiologist_queue_rows": len(queue_rows),
        "malformed_cache_line_count": index.get("malformed_cache_line_count", 0),
    }


RADIOLOGIST_DECISION_FIELDS = [
    "Master_Case_ID",
    "model_blinded",
    "score_binary",
    "reviewer_pseudonym",
    "reviewed_utc",
    "rationale",
]
COMBINED_RADIOLOGIST_SCORE_REQUIRED_FIELDS = [CASE_KEY, "model_blinded", "human_score"]
COMBINED_RADIOLOGIST_SCORE_ALIGNMENT_FIELDS = ["Ground_Truth_Diagnosis", "diagnosis", "likert"]
COMBINED_RADIOLOGIST_SCORE_NOTE_FIELDS = ["rationale", "notes", "review_notes", "comment", "comments"]


def validate_radiologist_decisions(queue_rows: list[dict[str, str]], decisions_path: Path) -> dict[tuple[str, str], dict[str, str]]:
    if queue_rows and not decisions_path.exists():
        raise ValidationError("radiologist queue is nonempty but decisions overlay is missing")
    if not queue_rows:
        return {}
    fields, rows = read_csv_table(decisions_path)
    if fields != RADIOLOGIST_DECISION_FIELDS:
        raise ValidationError(
            "radiologist decisions must use the exact ordered schema: "
            f"{RADIOLOGIST_DECISION_FIELDS}"
        )
    queue_keys = {(row[CASE_KEY], row["model_blinded"]) for row in queue_rows}
    decisions: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row.get(CASE_KEY, ""), row.get("model_blinded", ""))
        if key in decisions:
            raise ValidationError(f"duplicate radiologist decision for {key}")
        if key not in queue_keys:
            raise ValidationError(f"radiologist decision not present in queue: {key}")
        score = str(row.get("score_binary", "")).strip()
        if score not in {"0", "1"}:
            raise ValidationError(f"radiologist decision score_binary must be 0 or 1 for {key}")
        reviewed_utc = str(row.get("reviewed_utc", "")).strip()
        if not str(row.get("reviewer_pseudonym", "")).strip() or not reviewed_utc:
            raise ValidationError(f"radiologist decision missing reviewer/time for {key}")
        try:
            parsed_reviewed_utc = datetime.fromisoformat(
                reviewed_utc[:-1] + "+00:00" if reviewed_utc.endswith("Z") else reviewed_utc
            )
        except ValueError as exc:
            raise ValidationError(f"radiologist decision reviewed_utc is not a valid timestamp for {key}") from exc
        offset = parsed_reviewed_utc.utcoffset()
        if parsed_reviewed_utc.tzinfo is None or offset is None or offset.total_seconds() != 0:
            raise ValidationError(f"radiologist decision reviewed_utc must be timezone-aware UTC for {key}")
        decisions[key] = row
    missing = sorted(queue_keys - set(decisions), key=lambda item: (case_sort_key(item[0]), item[1]))
    if missing:
        raise ValidationError(f"radiologist decisions missing queue keys: {missing[:10]}")
    return decisions


def _format_case_model_key(key: tuple[str, str]) -> str:
    return f"{key[0]} / {key[1]}"


def _case_model_key_sort_key(key: tuple[str, str]) -> tuple[tuple[int, object], str]:
    return (case_sort_key(key[0]), key[1])


def _normalize_binary_human_score(value: object, key: tuple[str, str]) -> str:
    raw = "" if value is None else str(value).strip()
    if raw in {"0", "1"}:
        return raw
    if not raw:
        raise ValidationError(f"combined radiologist human_score is blank for {_format_case_model_key(key)}")
    try:
        parsed = Fraction(raw)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValidationError(
            f"combined radiologist human_score must be binary 0 or 1 for {_format_case_model_key(key)}"
        ) from exc
    if parsed.denominator == 1 and parsed.numerator in {0, 1}:
        return str(parsed.numerator)
    raise ValidationError(f"combined radiologist human_score must be binary 0 or 1 for {_format_case_model_key(key)}")


def _likert_values_match(left: object, right: object) -> bool:
    left_text = "" if left is None else str(left).strip()
    right_text = "" if right is None else str(right).strip()
    if left_text == right_text:
        return True
    try:
        return Fraction(left_text) == Fraction(right_text)
    except (ValueError, ZeroDivisionError):
        return False


def _combined_output_name(model_key: str, model_blinded: str) -> str:
    base = model_key.strip() or model_blinded.strip() or "model"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", base).strip("_") or "model"


def split_combined_radiologist_scores(
    *,
    combined_scores: Path,
    staging_roots: list[Path],
    output_root: Path,
    reviewer_pseudonym: str,
    reviewed_utc: str,
    rationale_prefix: str = "combined_human_score",
    allow_extra: bool = False,
) -> dict[str, Any]:
    """Convert one combined long human-score sheet into exact per-model overlays."""
    if not staging_roots:
        raise ValidationError("at least one staging root is required")
    reviewer_pseudonym = str(reviewer_pseudonym).strip()
    reviewed_utc = str(reviewed_utc).strip()
    if not reviewer_pseudonym:
        raise ValidationError("reviewer_pseudonym is required")
    if not reviewed_utc:
        raise ValidationError("reviewed_utc is required")

    combined_fields, combined_rows = read_csv_table(combined_scores)
    require_columns(combined_fields, COMBINED_RADIOLOGIST_SCORE_REQUIRED_FIELDS, "combined radiologist scores")

    stage_specs: list[dict[str, Any]] = []
    expected_rows: dict[tuple[str, str], dict[str, str]] = {}
    expected_stage_index: dict[tuple[str, str], int] = {}
    output_names: set[str] = set()
    for raw_root in staging_roots:
        staging_root = Path(raw_root)
        manifest = read_json(staging_root / "append_input_manifest.json")
        model_key = str(manifest.get("model_key", "")).strip()
        model_blinded = str(manifest.get("model_blinded", "")).strip()
        if not model_key or not model_blinded:
            raise ValidationError(f"staging root manifest missing model identity: {staging_root}")
        output_name = _combined_output_name(model_key, model_blinded)
        if output_name in output_names:
            raise ValidationError(f"duplicate combined split output name: {output_name}")
        output_names.add(output_name)
        queue_fields, queue_rows = read_csv_table(staging_root / "radiologist_queue.csv")
        if queue_fields != RADIOLOGIST_QUEUE_FIELDS:
            raise ValidationError(f"radiologist queue columns mismatch under {staging_root}")
        stage_index = len(stage_specs)
        for queue_row in queue_rows:
            key = (queue_row.get(CASE_KEY, ""), queue_row.get("model_blinded", ""))
            if key in expected_rows:
                raise ValidationError(f"duplicate expected radiologist queue key: {_format_case_model_key(key)}")
            expected_rows[key] = queue_row
            expected_stage_index[key] = stage_index
        stage_specs.append({
            "staging_root": staging_root,
            "model_key": model_key,
            "model_blinded": model_blinded,
            "output_name": output_name,
            "queue_rows": queue_rows,
        })

    combined_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for row_number, row in enumerate(combined_rows, start=2):
        key = (str(row.get(CASE_KEY, "")).strip(), str(row.get("model_blinded", "")).strip())
        if key in combined_by_key:
            raise ValidationError(f"duplicate combined radiologist row for {_format_case_model_key(key)}")
        if not key[0] or not key[1]:
            raise ValidationError(f"combined radiologist row {row_number} is missing case/model key")
        combined_by_key[key] = row

    expected_keys = set(expected_rows)
    combined_keys = set(combined_by_key)
    missing = sorted(expected_keys - combined_keys, key=_case_model_key_sort_key)
    if missing:
        preview = ", ".join(_format_case_model_key(key) for key in missing[:10])
        raise ValidationError(f"combined radiologist scores missing expected queue keys: {preview}")
    unexpected = sorted(combined_keys - expected_keys, key=_case_model_key_sort_key)
    if unexpected and not allow_extra:
        preview = ", ".join(_format_case_model_key(key) for key in unexpected[:10])
        raise ValidationError(f"combined radiologist scores contain unexpected keys: {preview}")

    decisions_by_stage: list[list[dict[str, object]]] = [[] for _ in stage_specs]
    for key in sorted(expected_keys, key=_case_model_key_sort_key):
        combined_row = combined_by_key[key]
        queue_row = expected_rows[key]
        for field in COMBINED_RADIOLOGIST_SCORE_ALIGNMENT_FIELDS:
            if field not in combined_fields:
                continue
            combined_value = combined_row.get(field, "")
            queue_value = queue_row.get(field, "")
            matches = _likert_values_match(combined_value, queue_value) if field == "likert" else str(combined_value) == str(queue_value)
            if not matches:
                raise ValidationError(
                    "combined radiologist scores do not match queue evidence for "
                    f"{_format_case_model_key(key)} field {field!r}"
                )
        score = _normalize_binary_human_score(combined_row.get("human_score", ""), key)
        note = next((str(combined_row.get(field, "")).strip() for field in COMBINED_RADIOLOGIST_SCORE_NOTE_FIELDS if str(combined_row.get(field, "")).strip()), "")
        rationale = str(rationale_prefix).strip()
        if note:
            rationale = f"{rationale}: {note}" if rationale else note
        decisions_by_stage[expected_stage_index[key]].append({
            CASE_KEY: key[0],
            "model_blinded": key[1],
            "score_binary": score,
            "reviewer_pseudonym": reviewer_pseudonym,
            "reviewed_utc": reviewed_utc,
            "rationale": rationale,
        })

    output_root.mkdir(parents=True, exist_ok=True)
    per_model: list[dict[str, Any]] = []
    for spec, decision_rows in zip(stage_specs, decisions_by_stage):
        decision_rows.sort(key=lambda row: case_sort_key(str(row[CASE_KEY])))
        decisions_path = output_root / str(spec["output_name"]) / "radiologist_decisions.csv"
        write_csv_table(decisions_path, RADIOLOGIST_DECISION_FIELDS, decision_rows)
        validate_radiologist_decisions(spec["queue_rows"], decisions_path)
        per_model.append({
            "model_key": spec["model_key"],
            "model_blinded": spec["model_blinded"],
            "staging_root": str(spec["staging_root"].resolve()),
            "radiologist_queue_rows": len(spec["queue_rows"]),
            "decisions_path": str(decisions_path.resolve()),
            "decisions_sha256": sha256_file(decisions_path),
        })

    receipt = {
        "schema_version": "radle_v2_combined_radiologist_split.v1",
        "combined_scores": str(combined_scores.resolve()),
        "combined_scores_sha256": sha256_file(combined_scores),
        "combined_rows": len(combined_rows),
        "expected_rows": len(expected_rows),
        "ignored_extra_rows": len(unexpected) if allow_extra else 0,
        "reviewer_pseudonym": reviewer_pseudonym,
        "reviewed_utc": reviewed_utc,
        "output_root": str(output_root.resolve()),
        "per_model": per_model,
    }
    summary_path = output_root / "split_summary.json"
    write_json(summary_path, receipt)
    receipt["split_summary_path"] = str(summary_path.resolve())
    receipt["split_summary_sha256"] = sha256_file(summary_path)
    return receipt


def read_agreement_locks(path: Path) -> dict[str, dict[str, str]]:
    fields, rows = read_csv_table(path)
    require_columns(fields, [CASE_KEY, "score", "score_source", "judge_count"], "agreement locks")
    locks: dict[str, dict[str, str]] = {}
    for row in rows:
        case_id = row[CASE_KEY]
        if case_id in locks:
            raise ValidationError(f"duplicate agreement lock for case {case_id}")
        if str(row.get("score", "")).strip() not in {"0", "1"}:
            raise ValidationError(f"agreement lock score must be 0 or 1 for case {case_id}")
        locks[case_id] = row
    return locks


def detect_line_terminator(data: bytes) -> str:
    return "\r\n" if b"\r\n" in data.splitlines(keepends=True)[:5] else "\n"


def serialize_delta_without_header(fieldnames: list[str], rows: list[dict[str, object]], lineterminator: str) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore", lineterminator=lineterminator)
    writer.writeheader()
    writer.writerows(rows)
    text = buffer.getvalue()
    first_break = text.find(lineterminator)
    if first_break < 0:
        raise ValidationError("failed to serialize scored delta")
    return text[first_break + len(lineterminator):].encode("utf-8")


def serialize_csv_with_header(fieldnames: list[str], rows: list[dict[str, object]], lineterminator: str = "\n") -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore", lineterminator=lineterminator)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def finalize_incremental_admission(
    *,
    intake_root: Path,
    radiologist_decisions: Path,
) -> dict[str, Any]:
    prepared = audit_prepared_staging(intake_root)
    judge_audit = audit_judge_evidence(intake_root)
    manifest = read_json(intake_root / "append_input_manifest.json")
    parent_master = intake_root / "parent" / "parent_final_long_master.csv"
    parent_fields, parent_rows = read_csv_table(parent_master)
    delta_fields, delta_rows = read_csv_table(intake_root / "new_model_long_delta.csv")
    state_fields, state_rows = read_csv_table(intake_root / "adjudication_state.csv")
    if parent_fields != FINAL_LONG_MASTER_FIELDS or delta_fields != FINAL_LONG_MASTER_FIELDS:
        raise ValidationError("new_model_long_delta.csv header does not match parent final long master")
    if state_fields != ADJUDICATION_STATE_FIELDS:
        raise ValidationError("adjudication_state.csv header mismatch")
    queue_fields, queue_rows = read_csv_table(intake_root / "radiologist_queue.csv")
    if queue_fields != RADIOLOGIST_QUEUE_FIELDS:
        raise ValidationError("radiologist queue columns mismatch")
    decisions = validate_radiologist_decisions(queue_rows, radiologist_decisions)
    agreement_locks = read_agreement_locks(intake_root / "judge_evidence" / "agreement_locks.csv")
    state_by_key = {(row[CASE_KEY], row["model_blinded"]): row for row in state_rows}
    if len(state_by_key) != len(state_rows):
        raise ValidationError("duplicate adjudication-state keys during finalization")

    scored_rows: list[dict[str, object]] = []
    source_counts: Counter[str] = Counter()
    for row in sorted(delta_rows, key=lambda item: case_sort_key(item[CASE_KEY])):
        case_id = row[CASE_KEY]
        model_blinded = row.get("model_blinded", "")
        key = (case_id, model_blinded)
        state_row = state_by_key.get(key)
        if state_row is None:
            raise ValidationError(f"missing adjudication state for {key}")
        state = state_row.get("terminal_state", "")
        scored = dict(row)
        score: str
        source: str
        if state in {"provider_or_parse_failure", "invalid_likert", "idk_exact", "idk_approved_typo"}:
            score, source = "0", "auto_score_not_required"
        elif state == "canonical_exact":
            score, source = "1", "canonical_exact"
        elif state == "previous_authoritative_score":
            score, source = str(state_row.get("automatic_score", "")).strip(), "previous_authoritative_score"
        elif key in decisions:
            decision = decisions[key]
            score, source = str(decision["score_binary"]).strip(), "radiologist"
        elif case_id in agreement_locks:
            score, source = str(agreement_locks[case_id]["score"]).strip(), "ai_judges"
        else:
            raise ValidationError(f"case {case_id} has no finalization source")
        if source not in ALLOWED_NEW_SCORE_SOURCES:
            raise ValidationError(f"unapproved final score source for case {case_id}: {source}")
        if score not in {"0", "1"}:
            raise ValidationError(f"non-binary final score for case {case_id}: {score!r}")
        scored["final_score_authoritative"] = score
        scored["final_score_source"] = source
        source_counts[source] += 1
        scored_rows.append(scored)

    if len(scored_rows) != int(manifest.get("case_count", 0)):
        raise ValidationError("scored delta row count mismatch")

    scored_delta_bytes = serialize_csv_table(FINAL_LONG_MASTER_FIELDS, scored_rows)
    scored_delta_sha256 = sha256_bytes(scored_delta_bytes)
    judge_index = read_json(intake_root / "judge_evidence" / "judge_evidence_index.json")
    authorization_identity: object = judge_index.get("authorization", "MISSING")
    paid_auth = intake_root / "judge_evidence" / "paid_judge_authorization.json"
    if paid_auth.is_file():
        authorization_identity = {"sha256": sha256_file(paid_auth), "content_sha256": content_only_json_sha256(paid_auth)}
    finalizer_code_sha = canonical_text_sha256(Path(__file__))
    evidence_hashes = {
        "adjudication_state": sha256_file(intake_root / "adjudication_state.csv"),
        "judge_worklist": sha256_file(intake_root / "judge_worklist.csv"),
        "judge_config": canonical_json_sha256(intake_root / "judge_evidence" / "judge_config.json"),
        "judge_prompt": canonical_text_sha256(intake_root / "judge_evidence" / "judge_prompt.txt"),
        "judge_results": sha256_file(intake_root / "judge_evidence" / "judge_results.jsonl"),
        "judge_index": sha256_file(intake_root / "judge_evidence" / "judge_evidence_index.json"),
        "agreement_locks": sha256_file(intake_root / "judge_evidence" / "agreement_locks.csv"),
        "radiologist_queue": sha256_file(intake_root / "radiologist_queue.csv"),
        "radiologist_decisions": sha256_file(radiologist_decisions),
        "scored_append_delta": scored_delta_sha256,
        "roster": canonical_json_sha256(intake_root / "roster" / "model_roster.json"),
        "blind_map": sha256_file(intake_root / "roster" / "blind_label_map.csv"),
        "finalizer_code": finalizer_code_sha,
    }
    finalization_payload = {
        "schema_version": "radle_v2_finalization_identity.v2",
        "intake_id": manifest.get("intake_id"),
        "parent_chain_id": manifest.get("parent_chain_id"),
        "parent_master_sha256": sha256_file(parent_master),
        "evidence_hashes": evidence_hashes,
        "authorization": authorization_identity,
        "source_counts": dict(sorted(source_counts.items())),
    }
    finalization_id = compute_intake_id(finalization_payload)
    # Keep content IDs in sibling path components so Windows paths stay below
    # legacy MAX_PATH even when evidence filenames are descriptive.
    final_root = intake_root.parent / "finalized" / finalization_id
    if final_root.exists():
        existing_manifest = final_root / "append_manifest.json"
        if existing_manifest.exists() and read_json(existing_manifest).get("finalization_id") == finalization_id:
            audit_finalized_admission(final_root, require_committed=(final_root / "COMMITTED.json").is_file())
            return {
                "finalization_id": finalization_id,
                "final_staging_root": str(final_root.resolve()),
                "transaction_state": "PRECOMMIT_VALIDATED",
                "already_finalized": True,
            }
        raise ValidationError(f"finalization root collision: {final_root}")

    scored_delta_path = final_root / "scored_append_delta.csv"
    scored_delta_path.parent.mkdir(parents=True, exist_ok=True)
    scored_delta_path.write_bytes(scored_delta_bytes)
    parent_bytes = parent_master.read_bytes()
    line_terminator = detect_line_terminator(parent_bytes)
    delta_bytes = serialize_csv_table(FINAL_LONG_MASTER_FIELDS, scored_rows, lineterminator=line_terminator, include_header=False)
    final_master_path = final_root / "final" / "radle_v2_final_long_master.csv"
    final_master_path.parent.mkdir(parents=True, exist_ok=True)
    needs_break = parent_bytes and not parent_bytes.endswith((b"\n", b"\r"))
    final_master_path.write_bytes(parent_bytes + (line_terminator.encode("utf-8") if needs_break else b"") + delta_bytes)
    if radiologist_decisions.exists():
        shutil.copyfile(radiologist_decisions, final_root / "radiologist_decisions.csv")
    else:
        write_csv_table(final_root / "radiologist_decisions.csv", RADIOLOGIST_DECISION_FIELDS, [])
    snapshot_root = final_root / "intake_snapshot"
    shutil.copytree(intake_root, snapshot_root, ignore=shutil.ignore_patterns("finalized"))
    finalizer_source = final_root / "provenance" / "finalizer_source.py"
    finalizer_source.parent.mkdir(parents=True, exist_ok=True)
    finalizer_source.write_bytes(canonical_text_bytes(Path(__file__)))
    roster_out = final_root / "roster"
    roster_out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(intake_root / "roster" / "model_roster.json", roster_out / "model_roster.json")
    shutil.copyfile(intake_root / "roster" / "blind_label_map.csv", roster_out / "blind_label_map.csv")
    combined_out = final_root / "combined_wide" / "RadLE_v2_results_final.csv"
    combined_out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(intake_root / "combined_wide" / "RadLE_v2_results_final.csv", combined_out)
    parent_out = final_root / "parent" / "parent_final_long_master.csv"
    parent_out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(parent_master, parent_out)

    parent_semantic_hash = sha256_bytes(json.dumps(parent_rows, sort_keys=True).encode("utf-8"))
    append_manifest = {
        "schema_version": "radle_v2_append_manifest.v2",
        "intake_id": manifest.get("intake_id"),
        "finalization_id": finalization_id,
        "transaction_state": "PRECOMMIT_VALIDATED",
        "case_count": len(scored_rows),
        "parent_row_count": len(parent_rows),
        "output_row_count": len(parent_rows) + len(scored_rows),
        "parent_chain_id": manifest.get("parent_chain_id"),
        "parent_master_path": "parent/parent_final_long_master.csv",
        "parent_master_sha256": sha256_file(parent_master),
        "parent_semantic_sha256": parent_semantic_hash,
        "scored_append_delta_sha256": sha256_file(scored_delta_path),
        "output_master_sha256": sha256_file(final_master_path),
        "judge_evidence_index_sha256": sha256_file(intake_root / "judge_evidence" / "judge_evidence_index.json"),
        "radiologist_decisions_sha256": sha256_file(final_root / "radiologist_decisions.csv"),
        "roster_sha256": sha256_file(final_root / "roster" / "model_roster.json") if (final_root / "roster" / "model_roster.json").exists() else None,
        "source_counts": dict(sorted(source_counts.items())),
        "finalization_identity": finalization_payload,
        "line_terminator": "\\r\\n" if line_terminator == "\r\n" else "\\n",
        "checksum_exclusions": ["SHA256SUMS", "COMMITTED.json"],
        "outputs": {
            "scored_append_delta": "scored_append_delta.csv",
            "final_long_master": "final/radle_v2_final_long_master.csv",
            "combined_wide": "combined_wide/RadLE_v2_results_final.csv",
            "blind_label_map": "roster/blind_label_map.csv",
            "model_roster": "roster/model_roster.json",
            "intake_snapshot": "intake_snapshot",
        },
        "output_hashes": {
            "scored_append_delta": sha256_file(scored_delta_path),
            "final_long_master": sha256_file(final_master_path),
            "combined_wide": sha256_file(combined_out),
            "blind_label_map": sha256_file(roster_out / "blind_label_map.csv"),
            "model_roster": sha256_file(roster_out / "model_roster.json"),
            "parent_final_long_master": sha256_file(parent_out),
            "finalizer_source": sha256_file(finalizer_source),
        },
        "prepared_audit": prepared,
        "judge_audit": judge_audit,
    }
    write_json(final_root / "append_manifest.json", append_manifest)
    return {
        "finalization_id": finalization_id,
        "final_staging_root": str(final_root.resolve()),
        "transaction_state": "PRECOMMIT_VALIDATED",
        "already_finalized": False,
        "source_counts": dict(sorted(source_counts.items())),
    }


def finalized_payload_files(final_root: Path) -> list[Path]:
    excluded = {"SHA256SUMS", "COMMITTED.json"}
    files: list[Path] = []
    for path in final_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(final_root).as_posix()
        if relative in excluded:
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(final_root).as_posix())


def audit_sha256sums(root: Path) -> dict[str, str]:
    sums_path = root / "SHA256SUMS"
    if not sums_path.exists():
        raise ValidationError("SHA256SUMS missing for committed readback")
    expected = [path.relative_to(root).as_posix() for path in finalized_payload_files(root)]
    observed: dict[str, str] = {}
    lines = [line for line in sums_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if lines != sorted(lines, key=lambda line: line.split("  ", 1)[1] if "  " in line else line):
        raise ValidationError("committed SHA256SUMS must be sorted by relative path")
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if "  " not in line:
            raise ValidationError(f"malformed SHA256SUMS line {line_number}")
        digest, relative = line.split("  ", 1)
        if relative in {"SHA256SUMS", "COMMITTED.json"}:
            raise ValidationError(f"SHA256SUMS must not include mutable marker {relative}")
        normalized = Path(relative).as_posix()
        if relative != normalized or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValidationError(f"unsafe SHA256SUMS path {relative!r}")
        if relative in observed:
            raise ValidationError(f"duplicate SHA256SUMS entry for {relative}")
        path = (root / Path(relative)).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError as exc:
            raise ValidationError(f"SHA256SUMS path escapes root: {relative}") from exc
        if not path.exists() or not path.is_file():
            raise ValidationError(f"SHA256SUMS references missing file {relative}")
        actual = sha256_file(path).lower()
        if digest.lower() != actual:
            raise ValidationError(f"SHA256SUMS digest mismatch for {relative}")
        observed[relative] = digest.lower()
    if sorted(observed) != sorted(expected):
        raise ValidationError("SHA256SUMS file set does not match finalized payload files")
    return observed


def audit_finalized_admission(final_root: Path, *, require_committed: bool = False) -> dict[str, Any]:
    append_manifest_path = final_root / "append_manifest.json"
    if not append_manifest_path.exists():
        raise ValidationError(f"append_manifest.json missing under {final_root}")
    manifest = read_json(append_manifest_path)
    if manifest.get("schema_version") != "radle_v2_append_manifest.v2":
        raise ValidationError(f"unsupported append manifest schema: {manifest.get('schema_version')!r}")
    if require_committed and not (final_root / "COMMITTED.json").exists():
        raise ValidationError("COMMITTED.json missing for committed readback")
    parent_master = final_root / str(manifest.get("parent_master_path", ""))
    final_master = final_root / str(manifest.get("outputs", {}).get("final_long_master", ""))
    scored_delta = final_root / str(manifest.get("outputs", {}).get("scored_append_delta", ""))
    if not parent_master.exists() or not final_master.exists() or not scored_delta.exists():
        raise ValidationError("finalized admission missing parent/final/scored files")
    parent_bytes = parent_master.read_bytes()
    final_bytes = final_master.read_bytes()
    scored_fields, scored_rows = read_csv_table(scored_delta)
    if scored_fields != FINAL_LONG_MASTER_FIELDS:
        raise ValidationError(f"scored delta schema mismatch: {scored_fields}")
    if len(scored_rows) != int(manifest.get("case_count", -1)):
        raise ValidationError("scored delta row count mismatch in audit")
    keys = [(row.get(CASE_KEY, ""), row.get("model_blinded", "")) for row in scored_rows]
    if len(set(keys)) != len(keys):
        raise ValidationError("duplicate scored delta keys")
    for row in scored_rows:
        if row.get("final_score_authoritative") not in {"0", "1"}:
            raise ValidationError("non-binary final_score_authoritative in scored delta")
        if row.get("final_score_source") not in ALLOWED_NEW_SCORE_SOURCES:
            raise ValidationError("missing or unapproved final_score_source in scored delta")
    if sha256_file(scored_delta) != manifest.get("scored_append_delta_sha256"):
        raise ValidationError("scored delta SHA mismatch")
    if sha256_file(final_master) != manifest.get("output_master_sha256"):
        raise ValidationError("final master SHA mismatch")
    output_hashes = manifest.get("output_hashes", {})
    for label, relative in {
        "scored_append_delta": "scored_append_delta.csv",
        "final_long_master": "final/radle_v2_final_long_master.csv",
        "combined_wide": "combined_wide/RadLE_v2_results_final.csv",
        "blind_label_map": "roster/blind_label_map.csv",
        "model_roster": "roster/model_roster.json",
        "parent_final_long_master": "parent/parent_final_long_master.csv",
        "finalizer_source": "provenance/finalizer_source.py",
    }.items():
        path = final_root / relative
        if not path.is_file() or sha256_file(path) != str(output_hashes.get(label, "")).upper():
            raise ValidationError(f"finalized output hash mismatch: {label}")

    line_terminator = "\r\n" if manifest.get("line_terminator") == "\\r\\n" else "\n"
    expected_final_bytes = parent_bytes
    if expected_final_bytes and not expected_final_bytes.endswith((b"\n", b"\r")):
        expected_final_bytes += line_terminator.encode("utf-8")
    expected_final_bytes += serialize_csv_table(FINAL_LONG_MASTER_FIELDS, scored_rows, lineterminator=line_terminator, include_header=False)
    if final_bytes != expected_final_bytes:
        raise ValidationError("final master bytes are not exact parent bytes plus serialized scored delta")
    if not final_bytes.startswith(parent_bytes):
        raise ValidationError("final master does not preserve parent bytes as prefix")
    parent_fields, parent_rows = read_csv_table(parent_master)
    final_fields, final_rows = read_csv_table(final_master)
    if parent_fields != FINAL_LONG_MASTER_FIELDS or final_fields != FINAL_LONG_MASTER_FIELDS:
        raise ValidationError("parent/final master schema mismatch")
    if len(final_rows) != len(parent_rows) + 200 or final_rows[:len(parent_rows)] != parent_rows or final_rows[len(parent_rows):] != scored_rows:
        raise ValidationError("final master parsed records are not exact parent records plus 200 scored rows")

    snapshot = final_root / "intake_snapshot"
    prepared_audit = audit_prepared_staging(snapshot)
    judge_audit = audit_judge_evidence(snapshot)
    snapshot_manifest = read_json(snapshot / "append_input_manifest.json")
    if snapshot_manifest.get("intake_id") != manifest.get("intake_id"):
        raise ValidationError("finalized intake snapshot ID mismatch")
    state_rows = read_csv_table(snapshot / "adjudication_state.csv")[1]
    state_by_key = {(row[CASE_KEY], row["model_blinded"]): row for row in state_rows}
    locks = read_agreement_locks(snapshot / "judge_evidence" / "agreement_locks.csv")
    decisions_path = final_root / "radiologist_decisions.csv"
    queue_rows = read_csv_table(snapshot / "radiologist_queue.csv")[1]
    decisions = validate_radiologist_decisions(queue_rows, decisions_path)
    recomputed_counts: Counter[str] = Counter()
    for row in scored_rows:
        key = (row[CASE_KEY], row["model_blinded"])
        state = state_by_key.get(key, {}).get("terminal_state")
        if state in {"provider_or_parse_failure", "invalid_likert", "idk_exact", "idk_approved_typo"}:
            expected_score, expected_source = "0", "auto_score_not_required"
        elif state == "canonical_exact":
            expected_score, expected_source = "1", "canonical_exact"
        elif state == "previous_authoritative_score":
            expected_score, expected_source = str(state_by_key[key].get("automatic_score", "")).strip(), "previous_authoritative_score"
        elif key in decisions:
            expected_score, expected_source = decisions[key]["score_binary"], "radiologist"
        elif row[CASE_KEY] in locks:
            expected_score, expected_source = locks[row[CASE_KEY]]["score"], "ai_judges"
        else:
            raise ValidationError(f"scored row has no recomputable authority: {key}")
        if row["final_score_authoritative"] != expected_score or row["final_score_source"] != expected_source:
            raise ValidationError(f"scored row does not match adjudication evidence: {key}")
        recomputed_counts[expected_source] += 1
    if dict(sorted(recomputed_counts.items())) != manifest.get("source_counts"):
        raise ValidationError("final score-source counts do not recompute")

    judge_index = read_json(snapshot / "judge_evidence" / "judge_evidence_index.json")
    authorization_identity: object = judge_index.get("authorization", "MISSING")
    paid_auth = snapshot / "judge_evidence" / "paid_judge_authorization.json"
    if paid_auth.is_file():
        authorization_identity = {"sha256": sha256_file(paid_auth), "content_sha256": content_only_json_sha256(paid_auth)}
    evidence_hashes = {
        "adjudication_state": sha256_file(snapshot / "adjudication_state.csv"),
        "judge_worklist": sha256_file(snapshot / "judge_worklist.csv"),
        "judge_config": canonical_json_sha256(snapshot / "judge_evidence" / "judge_config.json"),
        "judge_prompt": canonical_text_sha256(snapshot / "judge_evidence" / "judge_prompt.txt"),
        "judge_results": sha256_file(snapshot / "judge_evidence" / "judge_results.jsonl"),
        "judge_index": sha256_file(snapshot / "judge_evidence" / "judge_evidence_index.json"),
        "agreement_locks": sha256_file(snapshot / "judge_evidence" / "agreement_locks.csv"),
        "radiologist_queue": sha256_file(snapshot / "radiologist_queue.csv"),
        "radiologist_decisions": sha256_file(decisions_path),
        "scored_append_delta": sha256_file(scored_delta),
        "roster": canonical_json_sha256(final_root / "roster" / "model_roster.json"),
        "blind_map": sha256_file(final_root / "roster" / "blind_label_map.csv"),
        "finalizer_code": canonical_text_sha256(final_root / "provenance" / "finalizer_source.py"),
    }
    recomputed_identity = {
        "schema_version": "radle_v2_finalization_identity.v2",
        "intake_id": manifest.get("intake_id"),
        "parent_chain_id": manifest.get("parent_chain_id"),
        "parent_master_sha256": sha256_file(parent_master),
        "evidence_hashes": evidence_hashes,
        "authorization": authorization_identity,
        "source_counts": dict(sorted(recomputed_counts.items())),
    }
    if recomputed_identity != manifest.get("finalization_identity"):
        raise ValidationError("finalization identity payload does not independently recompute")
    if compute_intake_id(recomputed_identity) != manifest.get("finalization_id"):
        raise ValidationError("finalization ID does not independently recompute")
    checksum_rows: dict[str, str] | None = None
    if require_committed:
        committed_path = final_root / "COMMITTED.json"
        committed = read_json(committed_path)
        if committed.get("append_manifest_sha256") != sha256_file(append_manifest_path):
            raise ValidationError("COMMITTED.json append_manifest_sha256 mismatch")
        checksum_rows = audit_sha256sums(final_root)
        if committed.get("sha256sums_sha256") != sha256_file(final_root / "SHA256SUMS"):
            raise ValidationError("COMMITTED.json sha256sums_sha256 mismatch")
        if committed.get("parent_chain_id") != manifest.get("parent_chain_id"):
            raise ValidationError("COMMITTED.json parent-chain mismatch")
    return {
        "result": "PASS",
        "phase": "committed-readback" if require_committed else "precommit",
        "finalization_id": manifest.get("finalization_id"),
        "scored_delta_rows": len(scored_rows),
        "output_row_count": manifest.get("output_row_count"),
        "source_counts": manifest.get("source_counts"),
        "checksum_rows": len(checksum_rows) if checksum_rows is not None else None,
        "prepared_audit": prepared_audit,
        "judge_audit": judge_audit,
    }


def commit_finalized_admission(final_staging_root: Path) -> dict[str, Any]:
    audit = audit_finalized_admission(final_staging_root)
    committed_path = final_staging_root / "COMMITTED.json"
    if committed_path.exists():
        committed_audit = audit_finalized_admission(final_staging_root, require_committed=True)
        committed = read_json(committed_path)
        return {
            "committed_root": str(final_staging_root.resolve()),
            "transaction_state": "ALREADY_ADMITTED",
            "finalization_id": committed.get("finalization_id"),
            "checksum_rows": committed_audit.get("checksum_rows"),
        }
    write_sha256sums(final_staging_root, finalized_payload_files(final_staging_root))
    payload = {
        "schema_version": "radle_v2_committed_marker.v1",
        "transaction_state": "FINAL_MASTER_COMMITTED",
        "finalization_id": audit["finalization_id"],
        "parent_chain_id": read_json(final_staging_root / "append_manifest.json").get("parent_chain_id"),
        "append_manifest_sha256": sha256_file(final_staging_root / "append_manifest.json"),
        "sha256sums_sha256": sha256_file(final_staging_root / "SHA256SUMS"),
    }
    write_json(committed_path, payload)
    committed_audit = audit_finalized_admission(final_staging_root, require_committed=True)
    return {
        "committed_root": str(final_staging_root.resolve()),
        "transaction_state": "FINAL_MASTER_COMMITTED",
        "finalization_id": audit["finalization_id"],
        "checksum_rows": committed_audit.get("checksum_rows"),
    }


IDK0_SCORE_ROW_FIELDS = [
    "Master_Case_ID",
    "model_blinded",
    "model_key",
    "display_name",
    "reader_type",
    "roster_status",
    "effective_roster_status",
    "excluded",
    "is_active",
    "human_panel_group",
    "likert",
    "final_score",
    "final_score_source",
    "terminal_state",
    "score1000_component",
    "admission_id",
]
IDK0_SUMMARY_FIELDS = [
    "display_order",
    "comparator_key",
    "display_name",
    "reader_type",
    "presentation_type",
    "roster_status",
    "effective_roster_status",
    "excluded",
    "is_active",
    "case_rows",
    "effective_n",
    "score1000",
    "score2000",
    "correct_rows",
    "incorrect_rows",
    "zero_rows",
]
IDK0_GROUP_FIELDS = [
    "group",
    "comparator_count",
    "row_count",
    "active_count",
    "excluded_count",
    "score1000_mean",
    "score2000_mean",
]
IDK0_PANEL_BIN_FIELDS = [
    "bin",
    "lower_inclusive",
    "upper_inclusive",
    "comparator_count",
    "active_count",
    "excluded_count",
]


def format_fraction(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    text = f"{float(value):.6f}".rstrip("0").rstrip(".")
    return text if text else "0"


def parse_score_fraction(value: str) -> Fraction:
    text = str(value).strip()
    if not text:
        raise ValidationError("blank score value")
    return Fraction(text)


def terminal_zero_states(states_path: Path) -> set[str]:
    policy = read_json(states_path)
    states = {
        str(row.get("state", ""))
        for row in policy.get("states", [])
        if row.get("correctness_action") == "zero"
    }
    states.update({"ERROR", "error", "provider_error", "parse_error", "retry_exhausted"})
    return states


def score1000_component(row: dict[str, str], zero_states: set[str]) -> int:
    likert_text = str(row.get("likert", "")).strip()
    final_score = str(row.get("final_score_authoritative", row.get("final_score", ""))).strip()
    normalized_diagnosis = normalize_diagnosis(row.get("diagnosis", ""))
    if normalized_diagnosis in {"i don t know", "idon t know"}:
        return 0
    if str(row.get("technical_failure", "")).strip().lower() == "true":
        return 0
    if str(row.get("response_valid", "")).strip().lower() == "false":
        return 0
    try:
        likert_fraction = Fraction(likert_text)
    except (ValueError, ZeroDivisionError):
        return 0
    if likert_fraction.denominator != 1:
        return 0
    likert = int(likert_fraction)
    if likert < 0 or likert > 4:
        return 0
    if final_score == "1":
        return likert + 1
    if final_score == "0":
        return -(likert + 1)
    raise ValidationError(f"final_score_authoritative must be binary for case {row.get(CASE_KEY)} candidate {row.get('candidate')}")


def derive_score_terminal_state(row: dict[str, str]) -> str:
    normalized = normalize_diagnosis(row.get("diagnosis", ""))
    if str(row.get("technical_failure", "")).strip().lower() == "true":
        return "technical_failure"
    if normalized == "i don t know":
        return "idk_exact"
    if normalized == "idon t know":
        return "idk_approved_typo"
    likert_text = str(row.get("likert", "")).strip()
    try:
        value = Fraction(likert_text)
    except (ValueError, ZeroDivisionError):
        return "invalid_likert"
    if value.denominator != 1 or int(value) not in range(0, 5):
        return "invalid_likert"
    if str(row.get("response_valid", "")).strip().lower() == "false":
        return "invalid_response"
    return "scored"


def human_label_order(roster: dict[str, Any]) -> list[str]:
    humans = [entry for entry in roster.get("blind_label_map", []) if entry.get("entry_type") == "human"]
    return [str(entry.get("blind_label", "")) for entry in sorted(humans, key=lambda item: candidate_label_sort_key(str(item.get("blind_label", ""))))]


def build_effective_model_roster(roster: dict[str, Any], present_model_keys: set[str]) -> dict[str, dict[str, Any]]:
    effective: dict[str, dict[str, Any]] = {}
    for model in roster.get("models", []):
        model_key = str(model.get("model_key", ""))
        if model_key not in present_model_keys:
            continue
        record = dict(model)
        original_status = str(record.get("roster_status", ""))
        effective_status = original_status
        if original_status == "pending_admission":
            effective_status = "complete_master_active"
        record["original_roster_status"] = original_status
        record["effective_roster_status"] = effective_status
        effective[model_key] = record

    for record in list(effective.values()):
        if record.get("original_roster_status") == "pending_admission" and record.get("effective_roster_status") == "complete_master_active":
            replaced = str(record.get("replaces_model_key", "")).strip()
            if replaced and replaced in effective:
                effective[replaced]["effective_roster_status"] = "complete_master_excluded"
    return effective


def summary_sort_key(row: dict[str, object]) -> tuple[int, float, str]:
    reader_type = str(row.get("reader_type", ""))
    excluded = str(row.get("excluded", "")).lower() == "true"
    score = float(parse_score_fraction(str(row.get("score2000", "0"))))
    if reader_type == "human":
        return (0, 0.0, str(row.get("display_name", "")))
    if not excluded:
        return (1, -score, str(row.get("display_name", "")))
    return (2, -score, str(row.get("display_name", "")))


def summarize_score_rows(score_rows: list[dict[str, object]], human_presentation: str, human_order: list[str]) -> list[dict[str, object]]:
    model_groups: dict[str, list[dict[str, object]]] = {}
    human_rows: list[dict[str, object]] = []
    for row in score_rows:
        if row.get("reader_type") == "human":
            human_rows.append(row)
        else:
            model_groups.setdefault(str(row.get("model_key", "")), []).append(row)

    summaries: list[dict[str, object]] = []
    for model_key, rows in sorted(model_groups.items(), key=lambda item: str(item[1][0].get("display_name", ""))):
        score = sum(Fraction(int(row["score1000_component"])) for row in rows)
        first = rows[0]
        summaries.append({
            "comparator_key": model_key,
            "display_name": first.get("display_name", model_key),
            "reader_type": "model",
            "presentation_type": "model",
            "roster_status": first.get("roster_status", ""),
            "effective_roster_status": first.get("effective_roster_status", ""),
            "excluded": first.get("excluded", ""),
            "is_active": first.get("is_active", ""),
            "case_rows": len(rows),
            "effective_n": len({str(row.get(CASE_KEY, "")) for row in rows}),
            "score1000": format_fraction(score),
            "score2000": format_fraction(score + 1000),
            "correct_rows": sum(1 for row in rows if int(row["score1000_component"]) > 0),
            "incorrect_rows": sum(1 for row in rows if int(row["score1000_component"]) < 0),
            "zero_rows": sum(1 for row in rows if int(row["score1000_component"]) == 0),
        })

    if human_rows:
        by_label: dict[str, list[dict[str, object]]] = {}
        for row in human_rows:
            by_label.setdefault(str(row.get("model_blinded", "")), []).append(row)
        labels = [label for label in human_order if label in by_label]
        extra_labels = sorted(set(by_label) - set(labels), key=candidate_label_sort_key)
        labels.extend(extra_labels)
        if len(labels) != 12:
            raise ValidationError(f"human projection requires 12 human readers, got {len(labels)}")
        groups: list[tuple[str, str, list[str], int]]
        if human_presentation == "pooled12":
            groups = [("human_pooled12", "Human Expert Baseline", labels, 12)]
        elif human_presentation == "split6x6":
            groups = [
                ("human_group_1", "Human Expert Group 1", labels[:6], 6),
                ("human_group_2", "Human Expert Group 2", labels[6:], 6),
            ]
        else:
            raise ValidationError(f"unsupported human presentation: {human_presentation}")
        for comparator_key, display_name, group_labels, divisor in groups:
            rows = [row for label in group_labels for row in by_label[label]]
            score = sum(Fraction(int(row["score1000_component"])) for row in rows) / divisor
            summaries.append({
                "comparator_key": comparator_key,
                "display_name": display_name,
                "reader_type": "human",
                "presentation_type": human_presentation,
                "roster_status": "human_reader",
                "effective_roster_status": "human_reader",
                "excluded": "false",
                "is_active": "true",
                "case_rows": len(rows),
                "effective_n": len({str(row.get(CASE_KEY, "")) for row in rows}),
                "score1000": format_fraction(score),
                "score2000": format_fraction(score + 1000),
                "correct_rows": sum(1 for row in rows if int(row["score1000_component"]) > 0),
                "incorrect_rows": sum(1 for row in rows if int(row["score1000_component"]) < 0),
                "zero_rows": sum(1 for row in rows if int(row["score1000_component"]) == 0),
            })

    ordered = sorted(summaries, key=summary_sort_key)
    for index, row in enumerate(ordered, start=1):
        row["display_order"] = index
    return ordered


def build_group_summary(summary_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[str, list[dict[str, object]]] = {}
    for row in summary_rows:
        if row.get("reader_type") == "human":
            key = "human"
        elif str(row.get("excluded", "")).lower() == "true":
            key = "excluded_model"
        else:
            key = "active_model"
        groups.setdefault(key, []).append(row)
    out: list[dict[str, object]] = []
    for key in ["human", "active_model", "excluded_model"]:
        rows = groups.get(key, [])
        if rows:
            score1000_mean = sum(parse_score_fraction(str(row["score1000"])) for row in rows) / len(rows)
            score2000_mean = sum(parse_score_fraction(str(row["score2000"])) for row in rows) / len(rows)
        else:
            score1000_mean = Fraction(0)
            score2000_mean = Fraction(0)
        out.append({
            "group": key,
            "comparator_count": len(rows),
            "row_count": sum(int(row.get("case_rows", 0)) for row in rows),
            "active_count": sum(1 for row in rows if str(row.get("is_active", "")).lower() == "true"),
            "excluded_count": sum(1 for row in rows if str(row.get("excluded", "")).lower() == "true"),
            "score1000_mean": format_fraction(score1000_mean),
            "score2000_mean": format_fraction(score2000_mean),
        })
    return out


def build_panel_bins(summary_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    bins = [
        ("negative", None, -1),
        ("zero", 0, 0),
        ("1_to_250", 1, 250),
        ("251_to_500", 251, 500),
        ("501_to_750", 501, 750),
        ("751_to_1000", 751, 1000),
    ]
    out: list[dict[str, object]] = []
    for name, lower, upper in bins:
        rows: list[dict[str, object]] = []
        for row in summary_rows:
            score = parse_score_fraction(str(row["score1000"]))
            if lower is None:
                in_bin = score < 0
            else:
                in_bin = Fraction(lower) <= score <= Fraction(upper)
            if in_bin:
                rows.append(row)
        out.append({
            "bin": name,
            "lower_inclusive": "" if lower is None else lower,
            "upper_inclusive": upper,
            "comparator_count": len(rows),
            "active_count": sum(1 for row in rows if str(row.get("is_active", "")).lower() == "true"),
            "excluded_count": sum(1 for row in rows if str(row.get("excluded", "")).lower() == "true"),
        })
    return out


def build_idk0_score_lane(
    *,
    committed_root: Path,
    output_root: Path,
    human_presentation: str,
    roster_path: Path | None = None,
    states_path: Path | None = None,
) -> dict[str, Any]:
    if output_root.exists() and any(output_root.iterdir()):
        raise ValidationError(f"IDK0 lane output root already exists and is not empty: {output_root}")
    committed_audit = audit_finalized_admission(committed_root, require_committed=True)
    append_manifest = read_json(committed_root / "append_manifest.json")
    final_master = committed_root / str(append_manifest.get("outputs", {}).get("final_long_master", ""))
    if not final_master.exists():
        raise ValidationError("committed final master missing for IDK0 lane")
    roster_source = roster_path or (committed_root / "roster" / "model_roster.json")
    if not roster_source.exists():
        raise ValidationError(f"roster missing for IDK0 lane: {roster_source}")
    states_source = states_path or (committed_root / "intake_snapshot" / "inputs" / "terminal_states.json")
    fields, rows = read_csv_table(final_master)
    if fields != FINAL_LONG_MASTER_FIELDS:
        raise ValidationError(f"IDK0 final-master schema mismatch: {fields}")
    roster = read_json(roster_source)
    zero_states = terminal_zero_states(states_source)
    blind_source = committed_root / "roster" / "blind_label_map.csv"
    blind_fields, blind_rows = read_csv_table(blind_source)
    if blind_fields != BLIND_MAP_FIELDS:
        raise ValidationError(f"committed blind-map schema mismatch: {blind_fields}")
    blind_by_label = {row["model_blinded"]: row for row in blind_rows}
    if len(blind_by_label) != len(blind_rows):
        raise ValidationError("committed blind map has duplicate labels")
    roster_model_keys = {str(model.get("model_key", "")) for model in roster.get("models", [])}
    present_model_keys = {
        str(row.get("candidate", ""))
        for row in rows
        if str(row.get("model_blinded", "")) in blind_by_label
        and blind_by_label[str(row.get("model_blinded", ""))].get("model_key") in roster_model_keys
    }
    effective_roster = build_effective_model_roster(roster, present_model_keys)
    missing_models = sorted(present_model_keys - set(effective_roster))
    if missing_models:
        raise ValidationError(f"model rows missing from roster: {missing_models}")
    human_order = [
        label for label in sorted(blind_by_label, key=candidate_label_sort_key)
        if blind_by_label[label].get("model_key") not in roster_model_keys
    ]

    score_rows: list[dict[str, object]] = []
    for row in sorted(rows, key=lambda item: (case_sort_key(item.get(CASE_KEY, "")), candidate_label_sort_key(item.get("model_blinded", "Candidate ZZ")))):
        model_blinded = str(row.get("model_blinded", "")).strip()
        blind_entry = blind_by_label.get(model_blinded)
        if blind_entry is None:
            raise ValidationError(f"final-master label missing from committed blind map: {model_blinded}")
        reader_type = "model" if blind_entry.get("model_key") in roster_model_keys else "human"
        model_key = str(row.get("candidate", "")).strip() if reader_type == "model" else str(blind_entry.get("model_key", "")).strip()
        display_name = model_key or model_blinded
        roster_status = ""
        effective_status = ""
        excluded = False
        active = False
        human_group = ""
        if reader_type == "human":
            display_name = str(row.get("provider", "")) or model_key
            roster_status = "human_reader"
            effective_status = "human_reader"
            active = True
            if human_order and model_blinded in human_order:
                index = human_order.index(model_blinded)
                human_group = "human_group_1" if index < 6 else "human_group_2"
        else:
            record = effective_roster[model_key]
            display_name = str(record.get("display_name", display_name))
            roster_status = str(record.get("original_roster_status", record.get("roster_status", "")))
            effective_status = str(record.get("effective_roster_status", roster_status))
            excluded = effective_status != "complete_master_active"
            active = not excluded
        score_rows.append({
            "Master_Case_ID": row.get(CASE_KEY, ""),
            "model_blinded": model_blinded,
            "model_key": model_key,
            "display_name": display_name,
            "reader_type": reader_type,
            "roster_status": roster_status,
            "effective_roster_status": effective_status,
            "excluded": str(excluded).lower(),
            "is_active": str(active).lower(),
            "human_panel_group": human_group,
            "likert": row.get("likert", ""),
            "final_score": row.get("final_score_authoritative", ""),
            "final_score_source": row.get("final_score_source", ""),
            "terminal_state": derive_score_terminal_state(row),
            "score1000_component": score1000_component(row, zero_states),
            "admission_id": committed_audit.get("finalization_id", ""),
        })

    summary_rows = summarize_score_rows(score_rows, human_presentation, human_order)
    panel_order = [row for row in summary_rows if str(row.get("excluded", "")).lower() != "true"]
    for row in panel_order:
        if str(row.get("is_active", "")).lower() != "true":
            raise ValidationError("panel order contains inactive comparator")
    group_summary = build_group_summary(summary_rows)
    panel_bins = build_panel_bins(summary_rows)

    output_root.mkdir(parents=True, exist_ok=True)
    write_csv_table(output_root / "score_rows.csv", IDK0_SCORE_ROW_FIELDS, score_rows)
    write_csv_table(output_root / "source1000.csv", IDK0_SUMMARY_FIELDS, summary_rows)
    write_csv_table(output_root / "public_candidate_summary.csv", IDK0_SUMMARY_FIELDS, summary_rows)
    write_csv_table(output_root / "panel_order.csv", IDK0_SUMMARY_FIELDS, panel_order)
    write_csv_table(output_root / "group_summary.csv", IDK0_GROUP_FIELDS, group_summary)
    write_csv_table(output_root / "panel_bins.csv", IDK0_PANEL_BIN_FIELDS, panel_bins)

    manifest = {
        "schema_version": "radle_v2_idk0_score_lane.v1",
        "committed_root": str(committed_root.resolve()),
        "finalization_id": committed_audit.get("finalization_id"),
        "human_presentation": human_presentation,
        "inputs": {
            "append_manifest_sha256": sha256_file(committed_root / "append_manifest.json"),
            "committed_sha256": sha256_file(committed_root / "COMMITTED.json"),
            "final_master_sha256": sha256_file(final_master),
            "roster_sha256": sha256_file(roster_source),
            "blind_map_sha256": sha256_file(blind_source),
            "terminal_states_sha256": sha256_file(states_source),
        },
        "counts": {
            "final_master_rows": len(rows),
            "score_rows": len(score_rows),
            "complete_model_count": len(present_model_keys),
            "active_model_count": sum(1 for row in summary_rows if row.get("reader_type") == "model" and str(row.get("excluded", "")).lower() != "true"),
            "excluded_model_count": sum(1 for row in summary_rows if row.get("reader_type") == "model" and str(row.get("excluded", "")).lower() == "true"),
            "human_backend_readers": len({row["model_blinded"] for row in score_rows if row.get("reader_type") == "human"}),
            "presentation_comparators": len(summary_rows),
            "panel_comparators": len(panel_order),
            "active_score_rows": sum(1 for row in score_rows if str(row.get("is_active", "")).lower() == "true"),
        },
        "outputs": {
            "score_rows": {"path": "score_rows.csv", "sha256": sha256_file(output_root / "score_rows.csv")},
            "source1000": {"path": "source1000.csv", "sha256": sha256_file(output_root / "source1000.csv")},
            "public_candidate_summary": {"path": "public_candidate_summary.csv", "sha256": sha256_file(output_root / "public_candidate_summary.csv")},
            "panel_order": {"path": "panel_order.csv", "sha256": sha256_file(output_root / "panel_order.csv")},
            "group_summary": {"path": "group_summary.csv", "sha256": sha256_file(output_root / "group_summary.csv")},
            "panel_bins": {"path": "panel_bins.csv", "sha256": sha256_file(output_root / "panel_bins.csv")},
        },
    }
    write_json(output_root / "score_lane_manifest.json", manifest)
    return {
        "result": "PASS",
        "lane_root": str(output_root.resolve()),
        "finalization_id": committed_audit.get("finalization_id"),
        "counts": manifest["counts"],
    }


def audit_idk0_score_lane(lane_root: Path) -> dict[str, Any]:
    manifest_path = lane_root / "score_lane_manifest.json"
    if not manifest_path.exists():
        raise ValidationError("score_lane_manifest.json missing")
    manifest = read_json(manifest_path)
    expected_output_paths = {
        "score_rows": "score_rows.csv",
        "source1000": "source1000.csv",
        "public_candidate_summary": "public_candidate_summary.csv",
        "panel_order": "panel_order.csv",
        "group_summary": "group_summary.csv",
        "panel_bins": "panel_bins.csv",
    }
    outputs = manifest.get("outputs", {})
    if not isinstance(outputs, dict) or set(outputs) != set(expected_output_paths):
        raise ValidationError("IDK0 lane output inventory mismatch")
    actual_files = sorted(path.relative_to(lane_root).as_posix() for path in lane_root.rglob("*") if path.is_file())
    expected_files = sorted(["score_lane_manifest.json", *expected_output_paths.values()])
    if actual_files != expected_files:
        raise ValidationError("IDK0 lane contains missing or undeclared files")
    for name, expected_relative_path in expected_output_paths.items():
        descriptor = outputs[name]
        if not isinstance(descriptor, dict) or descriptor.get("path") != expected_relative_path:
            raise ValidationError(f"IDK0 lane output path mismatch: {name}")
        path = lane_root / expected_relative_path
        if not path.exists():
            raise ValidationError(f"IDK0 lane output missing: {name}")
        if sha256_file(path) != descriptor.get("sha256"):
            raise ValidationError(f"IDK0 lane output SHA mismatch: {name}")
    committed_root_value = str(manifest.get("committed_root", "")).strip()
    if not committed_root_value:
        raise ValidationError("IDK0 lane committed_root provenance is missing")
    committed_root = Path(committed_root_value)
    if not committed_root.is_dir():
        raise ValidationError(f"IDK0 lane committed_root is unavailable: {committed_root}")
    human_presentation = str(manifest.get("human_presentation", ""))
    with tempfile.TemporaryDirectory(prefix="radle_idk0_audit_") as temp_dir:
        rederived_root = Path(temp_dir) / "lane"
        build_idk0_score_lane(
            committed_root=committed_root,
            output_root=rederived_root,
            human_presentation=human_presentation,
        )
        rederived_manifest = read_json(rederived_root / "score_lane_manifest.json")
        if manifest != rederived_manifest:
            raise ValidationError("IDK0 lane manifest does not independently rederive from committed inputs")
        for relative_path in expected_output_paths.values():
            if (lane_root / relative_path).read_bytes() != (rederived_root / relative_path).read_bytes():
                raise ValidationError(f"IDK0 lane output does not independently rederive: {relative_path}")
    summary_fields, summary_rows = read_csv_table(lane_root / "public_candidate_summary.csv")
    if summary_fields != IDK0_SUMMARY_FIELDS:
        raise ValidationError("public candidate summary schema mismatch")
    prohibited_public = {"diagnosis", "Ground_Truth_Diagnosis", "Reasoning", "Raw_Response", "Associated_Images", "Image_SHA256", "source_file"}
    if prohibited_public & set(summary_fields):
        raise ValidationError(f"public candidate summary leaks prohibited columns: {sorted(prohibited_public & set(summary_fields))}")
    orders = [int(row["display_order"]) for row in summary_rows]
    if orders != list(range(1, len(summary_rows) + 1)):
        raise ValidationError("public candidate summary display_order is not contiguous")
    for row in summary_rows:
        score1000 = parse_score_fraction(row["score1000"])
        score2000 = parse_score_fraction(row["score2000"])
        if score2000 != score1000 + 1000:
            raise ValidationError(f"score2000 shift mismatch for {row.get('comparator_key')}")
    panel_fields, panel_rows = read_csv_table(lane_root / "panel_order.csv")
    if panel_fields != IDK0_SUMMARY_FIELDS:
        raise ValidationError("panel order schema mismatch")
    for row in panel_rows:
        if row.get("excluded") == "true":
            raise ValidationError("panel_order contains excluded comparator")
    counts = manifest.get("counts", {})
    if int(counts.get("score_rows", -1)) != sum(1 for _ in read_csv_table(lane_root / "score_rows.csv")[1]):
        raise ValidationError("manifest score_rows count mismatch")
    if int(counts.get("presentation_comparators", -1)) != len(summary_rows):
        raise ValidationError("manifest presentation comparator count mismatch")
    if int(counts.get("panel_comparators", -1)) != len(panel_rows):
        raise ValidationError("manifest panel comparator count mismatch")
    return {
        "result": "PASS",
        "phase": "idk0-lane",
        "finalization_id": manifest.get("finalization_id"),
        "counts": counts,
    }


def _judge_score_for_case(case_id: str, judge_key: str) -> tuple[int, bool, str]:
    if case_id == "9":
        return 1, False, "synthetic_agreement_correct"
    if case_id == "7":
        return (1 if judge_key == "gemini" else 0), False, "synthetic_disagreement"
    if case_id == "8":
        return 0, judge_key == "gemini", "synthetic_review_flag"
    return 0, False, "synthetic_agreement_incorrect"


def _request_payload(row: dict[str, str]) -> dict[str, str]:
    return {
        "reference_diagnosis": row.get("Ground_Truth_Diagnosis", ""),
        "candidate_diagnosis": row.get("diagnosis", ""),
    }


def run_synthetic_dual_judge_delta(
    *,
    staging_root: Path,
    judges_path: Path,
    out_dir: Path,
    repo_root: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    manifest = read_json(staging_root / "append_input_manifest.json")
    judges_config = read_json(judges_path)
    validate_judges(judges_config, repo_root)
    prompt_path = repo_root / str(judges_config.get("prompt_file", ""))
    prompt_sha = canonical_text_sha256(prompt_path)
    judge_config_sha = canonical_json_sha256(judges_path)
    terminal_policy_sha = canonical_json_sha256(staging_root / "inputs" / "terminal_states.json")
    variants_sha = sha256_file(staging_root / "accepted_variants_snapshot.csv")
    normalizer_code_sha = canonical_text_sha256(staging_root / "provenance" / "normalizer_source.py")
    worklist_fields, worklist_rows = read_csv_table(staging_root / "judge_worklist.csv")
    require_columns(worklist_fields, RADIOLOGIST_QUEUE_FIELDS, "judge worklist")
    max_retries = int(judges_config.get("max_retries", 1))
    judge_count = len(judges_config.get("judges", []))
    base_calls = len(worklist_rows) * judge_count
    receipt: dict[str, Any] = {
        "phase": "dual_judge_delta",
        "mode": "synthetic",
        "intake_id": manifest.get("intake_id"),
        "worklist_rows": len(worklist_rows),
        "judge_count": judge_count,
        "base_calls": base_calls,
        "worst_case_http_requests": base_calls * max_retries,
        "prompt_sha256": prompt_sha,
    }
    if dry_run:
        receipt["result"] = "DRY_RUN_VALIDATED"
        return receipt

    out_dir.mkdir(parents=True, exist_ok=True)
    request_payloads: list[dict[str, object]] = []
    judge_cache_rows: list[dict[str, object]] = []
    judge_results: list[dict[str, object]] = []
    by_case: dict[str, list[dict[str, object]]] = {}
    for row in worklist_rows:
        case_id = row[CASE_KEY]
        payload = _request_payload(row)
        payload_sha = sha256_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))
        worklist_row_sha = row_sha256(row, RADIOLOGIST_QUEUE_FIELDS)
        request_payloads.append({
            "schema_version": "radle_v2_judge_request.v1",
            CASE_KEY: case_id,
            "request_payload_sha256": payload_sha,
            "payload": payload,
        })
        for judge in judges_config.get("judges", []):
            judge_key = str(judge.get("judge_key", ""))
            score, flag, reason = _judge_score_for_case(case_id, judge_key)
            raw_response = {
                "score": score,
                "matched_entity": row.get("diagnosis", ""),
                "reason": reason,
                "confidence": "medium",
                "flag_for_review": flag,
            }
            raw_response_sha = sha256_bytes(json.dumps(raw_response, sort_keys=True).encode("utf-8"))
            cache_key = sha256_bytes(json.dumps({
                "requested_model_id": judge.get("requested_model_id", ""),
                "returned_model_id": judge.get("requested_model_id", ""),
                "request_payload_sha256": payload_sha,
                "worklist_row_sha256": worklist_row_sha,
                "case_triplet_sha256": manifest.get("intake_identity", {}).get("case_triplet_sha256", ""),
                "judge_config_sha256": judge_config_sha,
                "prompt_sha256": prompt_sha,
                "normalizer_code_sha256": normalizer_code_sha,
                "terminal_policy_sha256": terminal_policy_sha,
                "variants_snapshot_sha256": variants_sha,
            }, sort_keys=True).encode("utf-8"))
            result = {
                "schema_version": "radle_v2_judge_result.v1",
                "intake_id": manifest.get("intake_id"),
                CASE_KEY: case_id,
                "case_triplet_sha256": manifest.get("intake_identity", {}).get("case_triplet_sha256", ""),
                "worklist_row_sha256": worklist_row_sha,
                "judge_key": judge_key,
                "requested_judge_model_id": judge.get("requested_model_id", ""),
                "returned_judge_model_id": judge.get("requested_model_id", ""),
                "exact_request_payload_sha256": payload_sha,
                "judge_config_sha256": judge_config_sha,
                "prompt_sha256": prompt_sha,
                "normalizer_code_sha256": normalizer_code_sha,
                "terminal_policy_sha256": terminal_policy_sha,
                "variants_snapshot_sha256": variants_sha,
                "cache_key": cache_key,
                "started_utc": "2026-01-01T00:00:00+00:00",
                "completed_utc": "2026-01-01T00:00:00+00:00",
                "terminal_api_status": "synthetic",
                "retry_count": 0,
                "raw_response_sha256": raw_response_sha,
                "score": score,
                "matched_entity": row.get("diagnosis", ""),
                "reason": reason,
                "confidence": "medium",
                "flag_for_review": flag,
                "parse_status": "parsed",
                "api_status": "synthetic",
                "parse_error": "",
                "api_error": "",
                "synthetic_fixture_id": "radle_v2_milestone4_synthetic",
            }
            judge_cache_rows.append({
                "schema_version": "radle_v2_judge_cache_entry.v1",
                "cache_key": cache_key,
                "raw_response_sha256": raw_response_sha,
                "raw_response": raw_response,
                "result": result,
            })
            judge_results.append(result)
            by_case.setdefault(case_id, []).append(result)

    locked_rows: list[dict[str, object]] = []
    queue_rows: list[dict[str, object]] = []
    routing_rows: list[dict[str, object]] = []
    worklist_by_case = {row[CASE_KEY]: row for row in worklist_rows}
    for case_id, results in sorted(by_case.items(), key=lambda item: case_sort_key(item[0])):
        parsed = [
            result for result in results
            if result.get("parse_status") == "parsed" and str(result.get("score")) in {"0", "1"}
        ]
        scores = {int(result["score"]) for result in parsed}
        any_flag = any(bool(result.get("flag_for_review")) for result in results)
        judge_ids = {str(result.get("requested_judge_model_id", "")) for result in parsed}
        configured_ids = {str(judge.get("requested_model_id", "")) for judge in judges_config.get("judges", [])}
        evidence_matches = all(
            result.get("exact_request_payload_sha256") == request_payloads[[item[CASE_KEY] for item in request_payloads].index(case_id)]["request_payload_sha256"]
            and result.get("judge_config_sha256") == judge_config_sha
            and result.get("prompt_sha256") == prompt_sha
            for result in parsed
        )
        if len(results) == judge_count and len(parsed) == judge_count and judge_ids == configured_ids and len(scores) == 1 and not any_flag and evidence_matches:
            locked_rows.append({
                CASE_KEY: case_id,
                "score": next(iter(scores)),
                "score_source": "ai_judges",
                "judge_count": len(results),
            })
            routing_rows.append({
                CASE_KEY: case_id,
                "route": "dual_judge_agreement",
                "reason": "equal_unflagged_binary_verdicts",
            })
        else:
            queue_rows.append({field: worklist_by_case[case_id].get(field, "") for field in RADIOLOGIST_QUEUE_FIELDS})
            routing_rows.append({
                CASE_KEY: case_id,
                "route": "radiologist_queue",
                "reason": "review_flag_or_disagreement",
            })

    _, delta_rows = read_csv_table(staging_root / "new_model_long_delta.csv")
    _, state_rows = read_csv_table(staging_root / "adjudication_state.csv")
    delta_by_key = {(row[CASE_KEY], row["model_blinded"]): row for row in delta_rows}
    for state_row in state_rows:
        if state_row.get("requires_radiologist") == "True":
            row = delta_by_key[(state_row[CASE_KEY], state_row["model_blinded"])]
            queue_rows.append({field: row.get(field, "") for field in RADIOLOGIST_QUEUE_FIELDS})
            routing_rows.append({
                CASE_KEY: row.get(CASE_KEY, ""),
                "route": "radiologist_queue",
                "reason": "mandatory_radiologist",
            })

    request_path = out_dir / "request_payloads.jsonl"
    request_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in request_payloads) + "\n", encoding="utf-8")
    (out_dir / "judge_request_payloads.jsonl").write_text(request_path.read_text(encoding="utf-8"), encoding="utf-8")
    cache_path = out_dir / "judge_cache.jsonl"
    cache_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in judge_cache_rows) + "\n", encoding="utf-8")
    results_path = out_dir / "judge_results.jsonl"
    results_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in judge_results) + "\n", encoding="utf-8")
    write_csv_table(out_dir / "agreement_locks.csv", ["Master_Case_ID", "score", "score_source", "judge_count"], locked_rows)
    write_csv_table(out_dir / "dual_judge_agreements.csv", ["Master_Case_ID", "score", "score_source", "judge_count"], locked_rows)
    write_csv_table(staging_root / "radiologist_queue.csv", RADIOLOGIST_QUEUE_FIELDS, queue_rows)
    write_json(out_dir / "radiologist_queue_routing_audit.json", {
        "schema_version": "radle_v2_radiologist_queue_routing_audit.v1",
        "routing_rows": routing_rows,
    })
    summary = {
        "schema_version": "radle_v2_dual_judge_summary.v1",
        "intake_id": manifest.get("intake_id"),
        "worklist_rows": len(worklist_rows),
        "judge_result_rows": len(judge_results),
        "locked_agreement_rows": len(locked_rows),
        "radiologist_queue_rows": len(queue_rows),
        "prompt_sha256": prompt_sha,
        "request_payloads_sha256": sha256_file(request_path),
        "judge_cache_sha256": sha256_file(cache_path),
        "judge_results_sha256": sha256_file(results_path),
    }
    write_json(out_dir / "judge_summary.json", summary)
    config_snapshot = out_dir / "judge_config.json"
    write_json(config_snapshot, judges_config)
    prompt_snapshot = out_dir / "judge_prompt.txt"
    prompt_snapshot.write_bytes(canonical_text_bytes(prompt_path))
    write_json(out_dir / "judge_evidence_index.json", {
        "schema_version": "radle_v2_judge_evidence_index.v1",
        "summary": summary,
        "files": {
            "request_payloads": {"path": "request_payloads.jsonl", "sha256": sha256_file(request_path)},
            "judge_cache": {"path": "judge_cache.jsonl", "sha256": sha256_file(cache_path)},
            "judge_results": {"path": "judge_results.jsonl", "sha256": sha256_file(results_path)},
            "agreement_locks": {"path": "agreement_locks.csv", "sha256": sha256_file(out_dir / "agreement_locks.csv")},
            "radiologist_queue": {"path": "../radiologist_queue.csv", "sha256": sha256_file(staging_root / "radiologist_queue.csv")},
            "routing_audit": {
                "path": "radiologist_queue_routing_audit.json",
                "sha256": sha256_file(out_dir / "radiologist_queue_routing_audit.json"),
            },
            "judge_config": {"path": "judge_config.json", "sha256": sha256_file(config_snapshot)},
            "judge_prompt": {"path": "judge_prompt.txt", "sha256": sha256_file(prompt_snapshot)},
        },
        "malformed_cache_line_count": 0,
        "authorization": "SYNTHETIC_NO_PAID_AUTHORIZATION",
    })
    receipt.update(summary)
    receipt["result"] = "PASS"
    return receipt
