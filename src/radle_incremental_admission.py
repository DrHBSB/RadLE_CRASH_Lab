from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import unicodedata
from collections import Counter
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


def read_csv_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    if not fieldnames:
        raise ValidationError(f"CSV has no header: {path}")
    if len(set(fieldnames)) != len(fieldnames):
        raise ValidationError(f"CSV has duplicate header columns: {path}")
    return fieldnames, rows


def write_csv_table(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


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
    required_long = [CASE_KEY, "model_key", "diagnosis", "likert"]
    if not all(field in parent_long_fieldnames for field in required_long):
        return
    long_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for row in parent_long_rows:
        model_key = str(row.get("model_key", "")).strip()
        case_id = str(row.get(CASE_KEY, "")).strip()
        if model_key and case_id:
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
            if row.get(likert_column, "") != long_row.get("likert", ""):
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


def _set_if_present(row: dict[str, object], fieldnames: list[str], field: str, value: object) -> None:
    if field in fieldnames:
        row[field] = value


def build_new_model_long_delta(
    parent_long_fieldnames: list[str],
    incoming_rows: list[dict[str, str]],
    incoming_fieldnames: list[str],
    model_key: str,
    model_record: dict[str, Any],
    ground_truth_by_case: dict[str, str],
    terminal_policy: dict[str, Any],
) -> tuple[list[dict[str, object]], Counter[str], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
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
        state = classify_terminal_state(terminal_row, ground_truth, terminal_policy)
        counts[state] += 1

        out_row: dict[str, object] = {field: "" for field in parent_long_fieldnames}
        _set_if_present(out_row, parent_long_fieldnames, CASE_KEY, case_id)
        _set_if_present(out_row, parent_long_fieldnames, "model_blinded", model_record.get("blind_label", ""))
        _set_if_present(out_row, parent_long_fieldnames, "model_key", model_key)
        _set_if_present(out_row, parent_long_fieldnames, "model_name", model_record.get("display_name", ""))
        _set_if_present(out_row, parent_long_fieldnames, "reader_type", "model")
        _set_if_present(out_row, parent_long_fieldnames, "access", model_record.get("access", ""))
        _set_if_present(out_row, parent_long_fieldnames, "domain", model_record.get("domain", ""))
        _set_if_present(out_row, parent_long_fieldnames, "Ground_Truth_Diagnosis", ground_truth)
        _set_if_present(out_row, parent_long_fieldnames, "diagnosis", diagnosis)
        _set_if_present(out_row, parent_long_fieldnames, "likert", likert)
        _set_if_present(out_row, parent_long_fieldnames, "terminal_state", state)
        _set_if_present(out_row, parent_long_fieldnames, "source_file", "one_model_final_wide.csv")
        _set_if_present(out_row, parent_long_fieldnames, "source_row_sha256", row_sha256(incoming_row, incoming_fieldnames))
        rows.append(out_row)

        if state == "judge_required":
            judge_worklist.append({
                CASE_KEY: case_id,
                "model_blinded": model_record.get("blind_label", ""),
                "Ground_Truth_Diagnosis": ground_truth,
                "diagnosis": diagnosis,
                "likert": likert,
            })
    return rows, counts, judge_worklist


def compute_intake_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def write_sha256sums(root: Path, paths: list[Path]) -> None:
    entries = []
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        entries.append(f"{sha256_file(path).lower()}  {relative}")
    (root / "SHA256SUMS").write_text("\n".join(entries) + "\n", encoding="utf-8")


def project_one_model_package(
    *,
    source_wide: Path,
    model_key: str,
    output_package: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    source_fields, source_rows = read_csv_table(source_wide)
    require_columns(source_fields, KEY_COLUMNS, "source wide")
    source_model_keys = discover_model_keys(source_fields)
    if model_key not in source_model_keys:
        raise ValidationError(f"model {model_key!r} not found in source families {source_model_keys}")
    selected_fields = KEY_COLUMNS + model_result_columns(model_key)
    require_columns(source_fields, selected_fields, "source wide")
    rows_by_case = index_by_case(source_rows, "source wide")
    if len(rows_by_case) != len(source_rows):
        raise ValidationError("source wide case index mismatch")
    projected_rows = [
        {field: row.get(field, "") for field in selected_fields}
        for row in sorted(source_rows, key=lambda item: case_sort_key(str(item.get(CASE_KEY, ""))))
    ]
    projection_payload = {
        "schema_version": "radle_v2_one_model_projection.v1",
        "model_key": model_key,
        "source_wide_sha256": sha256_file(source_wide),
        "source_model_keys": source_model_keys,
        "selected_fields": selected_fields,
        "row_count": len(projected_rows),
    }
    projection_id = compute_intake_id(projection_payload)
    receipt = {
        "projection_id": projection_id,
        "model_key": model_key,
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
    manifest["source_wide"] = str(source_wide)
    manifest["results_csv_sha256"] = sha256_file(results_path)
    write_json(source_manifest_path, manifest)
    write_sha256sums(output_package, [results_path, source_manifest_path])
    receipt["projection_state"] = "PROJECTED"
    receipt["output_package"] = str(output_package.resolve())
    receipt["results_csv_sha256"] = manifest["results_csv_sha256"]
    return receipt


def prepare_incremental_admission(
    *,
    parent_wide: Path,
    parent_final_long_master: Path,
    parent_authority_manifest: Path,
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
    roster = read_json(roster_path)
    terminal_policy = read_json(states_path)

    require_columns(parent_wide_fields, KEY_COLUMNS, "parent wide")
    require_columns(incoming_fields, KEY_COLUMNS, "incoming wide")
    require_columns(parent_long_fields, [CASE_KEY, "Ground_Truth_Diagnosis"], "parent final long master")
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
    model_record = find_model_record(roster, model_key)

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

    long_delta, terminal_counts, judge_worklist = build_new_model_long_delta(
        parent_long_fields,
        one_model_rows,
        one_model_fields,
        model_key,
        model_record,
        ground_truth_by_case,
        terminal_policy,
    )
    scorer_fields, scorer_rows = build_scorer_view(combined_fields, combined_rows)

    input_hashes = {
        "parent_wide": sha256_file(parent_wide),
        "parent_final_long_master": sha256_file(parent_final_long_master),
        "parent_authority_manifest": sha256_file(parent_authority_manifest),
        "incoming_results_csv": sha256_file(incoming_csv),
        "roster": sha256_file(roster_path),
        "terminal_states": sha256_file(states_path),
        "variants": sha256_file(variants_path) if variants_path.exists() else None,
    }
    input_paths = {
        "parent_wide": str(parent_wide),
        "parent_final_long_master": str(parent_final_long_master),
        "parent_authority_manifest": str(parent_authority_manifest),
        "incoming_results_csv": str(incoming_csv),
        "roster": str(roster_path),
        "terminal_states": str(states_path),
        "variants": str(variants_path),
    }
    intake_payload = {
        "schema_version": "radle_v2_intake_identity.v1",
        "model_key": model_key,
        "case_count": len(case_ids),
        "input_hashes": input_hashes,
        "input_paths": input_paths,
        "normalizer_version": terminal_policy.get("normalizer_version"),
        "model_blinded": model_record.get("blind_label", ""),
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

    write_csv_table(staging_root / "canonical_ground_truth_snapshot.csv", [CASE_KEY, "Ground_Truth_Diagnosis", "Ground_Truth_Normalized"], ground_truth_snapshot)
    write_csv_table(staging_root / "one_model_final_wide.csv", one_model_fields, one_model_rows)
    write_csv_table(staging_root / "combined_wide" / "RadLE_v2_results_final.csv", combined_fields, combined_rows)
    write_csv_table(staging_root / "scorer" / "scorer_view.csv", scorer_fields, scorer_rows)
    write_csv_table(staging_root / "new_model_long_delta.csv", parent_long_fields, long_delta)
    write_csv_table(staging_root / "judge_worklist.csv", [CASE_KEY, "model_blinded", "Ground_Truth_Diagnosis", "diagnosis", "likert"], judge_worklist)
    if variants_path.exists():
        (staging_root / "accepted_variants_snapshot.csv").parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(variants_path, staging_root / "accepted_variants_snapshot.csv")
    else:
        write_csv_table(staging_root / "accepted_variants_snapshot.csv", ["Master_Case_ID", "diagnosis", "decision"], [])
    write_json(staging_root / "requirements_snapshot.json", {
        "schema_version": "radle_v2_requirements_snapshot.v1",
        "repo_root": str(repo_root),
        "model_key": model_key,
    })
    write_json(staging_root / "provenance" / "source_manifest.json", {
        "schema_version": "radle_v2_source_manifest.v1",
        "model_key": model_key,
        "incoming_package": str(incoming_package),
        "incoming_results_csv": str(incoming_csv),
        "input_hashes": input_hashes,
        "input_paths": input_paths,
    })
    write_json(staging_root / "audit" / "promotion_audit.json", {
        "schema_version": "radle_v2_promotion_audit.v1",
        "case_count": len(case_ids),
        "incoming_model_keys": incoming_model_keys,
        "metadata_match": True,
        "parent_wide_long_reconciled": True,
    })
    write_json(staging_root / "audit" / "terminal_state_audit.json", {
        "schema_version": "radle_v2_terminal_state_audit.v1",
        "terminal_state_counts": dict(sorted(terminal_counts.items())),
        "judge_worklist_rows": len(judge_worklist),
    })
    write_json(staging_root / "roster" / "model_roster.json", roster)
    write_json(staging_root / "roster" / "blind_label_map.json", {"blind_label_map": roster.get("blind_label_map", [])})
    manifest = {
        "schema_version": "radle_v2_append_input_manifest.v1",
        "intake_id": intake_id,
        "transaction_state": "ADJUDICATION_PENDING",
        "model_key": model_key,
        "model_blinded": model_record.get("blind_label", ""),
        "case_count": len(case_ids),
        "input_hashes": input_hashes,
        "input_paths": input_paths,
        "terminal_state_counts": dict(sorted(terminal_counts.items())),
        "judge_worklist_rows": len(judge_worklist),
        "outputs": {
            "canonical_ground_truth_snapshot": "canonical_ground_truth_snapshot.csv",
            "one_model_final_wide": "one_model_final_wide.csv",
            "combined_wide": "combined_wide/RadLE_v2_results_final.csv",
            "scorer_view": "scorer/scorer_view.csv",
            "new_model_long_delta": "new_model_long_delta.csv",
            "terminal_state_audit": "audit/terminal_state_audit.json",
            "judge_worklist": "judge_worklist.csv",
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
    if manifest.get("transaction_state") != "ADJUDICATION_PENDING":
        raise ValidationError(f"prepared staging has wrong transaction_state: {manifest.get('transaction_state')!r}")
    if (staging_root / "COMMITTED.json").exists():
        raise ValidationError("prepared staging must not contain COMMITTED.json")

    outputs = manifest.get("outputs", {})
    required_output_keys = [
        "canonical_ground_truth_snapshot",
        "one_model_final_wide",
        "combined_wide",
        "scorer_view",
        "new_model_long_delta",
        "terminal_state_audit",
        "judge_worklist",
    ]
    missing = [key for key in required_output_keys if key not in outputs]
    if missing:
        raise ValidationError(f"manifest missing output keys: {missing}")
    output_paths = {key: staging_root / str(outputs[key]) for key in required_output_keys}
    missing_paths = [str(path) for path in output_paths.values() if not path.exists()]
    if missing_paths:
        raise ValidationError(f"prepared output files missing: {missing_paths}")

    case_count = int(manifest.get("case_count", 0))
    row_counts = {}
    for key in ["canonical_ground_truth_snapshot", "one_model_final_wide", "combined_wide", "scorer_view", "new_model_long_delta", "judge_worklist"]:
        _, rows = read_csv_table(output_paths[key])
        row_counts[key] = len(rows)
    for key in ["canonical_ground_truth_snapshot", "one_model_final_wide", "combined_wide", "scorer_view", "new_model_long_delta"]:
        if row_counts[key] != case_count:
            raise ValidationError(f"{key} row count {row_counts[key]} != case_count {case_count}")
    if row_counts["judge_worklist"] != int(manifest.get("judge_worklist_rows", -1)):
        raise ValidationError("judge_worklist row count mismatch")

    terminal_audit = read_json(output_paths["terminal_state_audit"])
    if terminal_audit.get("terminal_state_counts") != manifest.get("terminal_state_counts"):
        raise ValidationError("terminal_state_counts mismatch between manifest and audit")

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
    }
    for label, path in required.items():
        if not path.exists():
            raise ValidationError(f"{label} evidence file missing: {path}")
    with (staging_root / "radiologist_queue.csv").open("r", encoding="utf-8", newline="") as handle:
        queue_reader = csv.DictReader(handle)
        if queue_reader.fieldnames != RADIOLOGIST_QUEUE_FIELDS:
            raise ValidationError(f"radiologist_queue.csv columns mismatch: {queue_reader.fieldnames}")
        queue_rows = list(queue_reader)
    with (evidence_root / "agreement_locks.csv").open("r", encoding="utf-8", newline="") as handle:
        lock_rows = list(csv.DictReader(handle))
    judge_result_rows = [
        json.loads(line)
        for line in (evidence_root / "judge_results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    request_text = (evidence_root / "request_payloads.jsonl").read_text(encoding="utf-8")
    if str(manifest.get("model_key", "")) in request_text or str(manifest.get("model_blinded", "")) in request_text:
        raise ValidationError("judge request payload leaks model key or blind label")
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


def validate_radiologist_decisions(queue_rows: list[dict[str, str]], decisions_path: Path) -> dict[tuple[str, str], dict[str, str]]:
    if queue_rows and not decisions_path.exists():
        raise ValidationError("radiologist queue is nonempty but decisions overlay is missing")
    if not queue_rows:
        return {}
    fields, rows = read_csv_table(decisions_path)
    require_columns(fields, RADIOLOGIST_DECISION_FIELDS, "radiologist decisions")
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
        if not str(row.get("reviewer_pseudonym", "")).strip() or not str(row.get("reviewed_utc", "")).strip():
            raise ValidationError(f"radiologist decision missing reviewer/time for {key}")
        decisions[key] = row
    missing = sorted(queue_keys - set(decisions), key=lambda item: (case_sort_key(item[0]), item[1]))
    if missing:
        raise ValidationError(f"radiologist decisions missing queue keys: {missing[:10]}")
    return decisions


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
    parent_master = Path(str(manifest.get("input_paths", {}).get("parent_final_long_master", "")))
    if not parent_master.exists():
        raise ValidationError(f"parent final long master path missing or not found: {parent_master}")
    parent_fields, parent_rows = read_csv_table(parent_master)
    delta_fields, delta_rows = read_csv_table(intake_root / "new_model_long_delta.csv")
    if parent_fields != delta_fields:
        raise ValidationError("new_model_long_delta.csv header does not match parent final long master")
    queue_fields, queue_rows = read_csv_table(intake_root / "radiologist_queue.csv")
    if queue_fields != RADIOLOGIST_QUEUE_FIELDS:
        raise ValidationError("radiologist queue columns mismatch")
    decisions = validate_radiologist_decisions(queue_rows, radiologist_decisions)
    agreement_locks = read_agreement_locks(intake_root / "judge_evidence" / "agreement_locks.csv")

    scored_rows: list[dict[str, object]] = []
    source_counts: Counter[str] = Counter()
    for row in sorted(delta_rows, key=lambda item: case_sort_key(item[CASE_KEY])):
        case_id = row[CASE_KEY]
        model_blinded = row.get("model_blinded", "")
        state = row.get("terminal_state", "")
        scored = dict(row)
        score: str
        source: str
        if state in {"provider_or_parse_failure", "invalid_likert", "idk_exact", "idk_approved_typo"}:
            score, source = "0", state
        elif state == "canonical_exact":
            score, source = "1", "canonical_exact"
        elif (case_id, model_blinded) in decisions:
            decision = decisions[(case_id, model_blinded)]
            score, source = str(decision["score_binary"]).strip(), "radiologist"
        elif case_id in agreement_locks:
            score, source = str(agreement_locks[case_id]["score"]).strip(), "dual_judge_agreement"
        else:
            raise ValidationError(f"case {case_id} has no finalization source")
        scored["final_score"] = score
        scored["final_score_source"] = source
        source_counts[source] += 1
        scored_rows.append(scored)

    if len(scored_rows) != int(manifest.get("case_count", 0)):
        raise ValidationError("scored delta row count mismatch")

    scored_delta_bytes = serialize_csv_with_header(parent_fields, scored_rows)
    scored_delta_sha256 = sha256_bytes(scored_delta_bytes)
    finalization_payload = {
        "schema_version": "radle_v2_finalization_identity.v1",
        "intake_id": manifest.get("intake_id"),
        "parent_master_sha256": sha256_file(parent_master),
        "radiologist_decisions_sha256": sha256_file(radiologist_decisions) if radiologist_decisions.exists() else None,
        "judge_summary_sha256": sha256_file(intake_root / "judge_evidence" / "judge_summary.json"),
        "scored_append_delta_sha256": scored_delta_sha256,
        "source_counts": dict(sorted(source_counts.items())),
    }
    finalization_id = compute_intake_id(finalization_payload)
    final_root = intake_root / "finalized" / finalization_id
    if final_root.exists():
        existing_manifest = final_root / "append_manifest.json"
        if existing_manifest.exists() and read_json(existing_manifest).get("finalization_id") == finalization_id:
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
    delta_bytes = serialize_delta_without_header(parent_fields, scored_rows, line_terminator)
    final_master_path = final_root / "final" / "radle_v2_final_long_master.csv"
    final_master_path.parent.mkdir(parents=True, exist_ok=True)
    needs_break = parent_bytes and not parent_bytes.endswith((b"\n", b"\r"))
    final_master_path.write_bytes(parent_bytes + (line_terminator.encode("utf-8") if needs_break else b"") + delta_bytes)
    if radiologist_decisions.exists():
        shutil.copyfile(radiologist_decisions, final_root / "radiologist_decisions.csv")
    else:
        write_csv_table(final_root / "radiologist_decisions.csv", RADIOLOGIST_DECISION_FIELDS, [])
    roster_out = final_root / "roster"
    roster_out.mkdir(parents=True, exist_ok=True)
    for roster_file in ["model_roster.json", "blind_label_map.json"]:
        source = intake_root / "roster" / roster_file
        if source.exists():
            shutil.copyfile(source, roster_out / roster_file)

    parent_semantic_hash = sha256_bytes(json.dumps(parent_rows, sort_keys=True).encode("utf-8"))
    append_manifest = {
        "schema_version": "radle_v2_append_manifest.v1",
        "intake_id": manifest.get("intake_id"),
        "finalization_id": finalization_id,
        "transaction_state": "PRECOMMIT_VALIDATED",
        "case_count": len(scored_rows),
        "parent_row_count": len(parent_rows),
        "output_row_count": len(parent_rows) + len(scored_rows),
        "parent_master_path": str(parent_master),
        "parent_master_sha256": sha256_file(parent_master),
        "parent_semantic_sha256": parent_semantic_hash,
        "scored_append_delta_sha256": sha256_file(scored_delta_path),
        "output_master_sha256": sha256_file(final_master_path),
        "judge_evidence_index_sha256": sha256_file(intake_root / "judge_evidence" / "judge_evidence_index.json"),
        "radiologist_decisions_sha256": sha256_file(final_root / "radiologist_decisions.csv"),
        "roster_sha256": sha256_file(final_root / "roster" / "model_roster.json") if (final_root / "roster" / "model_roster.json").exists() else None,
        "source_counts": dict(sorted(source_counts.items())),
        "line_terminator": "\\r\\n" if line_terminator == "\r\n" else "\\n",
        "checksum_exclusions": ["SHA256SUMS", "COMMITTED.json"],
        "outputs": {
            "scored_append_delta": "scored_append_delta.csv",
            "final_long_master": "final/radle_v2_final_long_master.csv",
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
    for line_number, line in enumerate(sums_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        if "  " not in line:
            raise ValidationError(f"malformed SHA256SUMS line {line_number}")
        digest, relative = line.split("  ", 1)
        if relative in {"SHA256SUMS", "COMMITTED.json"}:
            raise ValidationError(f"SHA256SUMS must not include mutable marker {relative}")
        if relative in observed:
            raise ValidationError(f"duplicate SHA256SUMS entry for {relative}")
        path = root / Path(relative)
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
    if require_committed and not (final_root / "COMMITTED.json").exists():
        raise ValidationError("COMMITTED.json missing for committed readback")
    parent_master = Path(str(manifest.get("parent_master_path", "")))
    final_master = final_root / str(manifest.get("outputs", {}).get("final_long_master", ""))
    scored_delta = final_root / str(manifest.get("outputs", {}).get("scored_append_delta", ""))
    if not parent_master.exists() or not final_master.exists() or not scored_delta.exists():
        raise ValidationError("finalized admission missing parent/final/scored files")
    parent_bytes = parent_master.read_bytes()
    final_bytes = final_master.read_bytes()
    if not final_bytes.startswith(parent_bytes):
        raise ValidationError("final master does not preserve parent bytes as prefix")
    _, scored_rows = read_csv_table(scored_delta)
    if len(scored_rows) != int(manifest.get("case_count", -1)):
        raise ValidationError("scored delta row count mismatch in audit")
    keys = [(row.get(CASE_KEY, ""), row.get("model_blinded", "")) for row in scored_rows]
    if len(set(keys)) != len(keys):
        raise ValidationError("duplicate scored delta keys")
    for row in scored_rows:
        if row.get("final_score") not in {"0", "1"}:
            raise ValidationError("non-binary final_score in scored delta")
        if not row.get("final_score_source"):
            raise ValidationError("missing final_score_source in scored delta")
    if sha256_file(scored_delta) != manifest.get("scored_append_delta_sha256"):
        raise ValidationError("scored delta SHA mismatch")
    if sha256_file(final_master) != manifest.get("output_master_sha256"):
        raise ValidationError("final master SHA mismatch")
    checksum_rows: dict[str, str] | None = None
    if require_committed:
        committed_path = final_root / "COMMITTED.json"
        committed = read_json(committed_path)
        if committed.get("append_manifest_sha256") != sha256_file(append_manifest_path):
            raise ValidationError("COMMITTED.json append_manifest_sha256 mismatch")
        checksum_rows = audit_sha256sums(final_root)
        if committed.get("sha256sums_sha256") != sha256_file(final_root / "SHA256SUMS"):
            raise ValidationError("COMMITTED.json sha256sums_sha256 mismatch")
    return {
        "result": "PASS",
        "phase": "committed-readback" if require_committed else "precommit",
        "finalization_id": manifest.get("finalization_id"),
        "scored_delta_rows": len(scored_rows),
        "output_row_count": manifest.get("output_row_count"),
        "source_counts": manifest.get("source_counts"),
        "checksum_rows": len(checksum_rows) if checksum_rows is not None else None,
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
    terminal_state = str(row.get("terminal_state", "")).strip()
    likert_text = str(row.get("likert", "")).strip()
    final_score = str(row.get("final_score", "")).strip()
    if terminal_state in zero_states:
        return 0
    try:
        likert = int(likert_text)
    except ValueError:
        return 0
    if likert < 0 or likert > 4:
        return 0
    if final_score == "1":
        return likert + 1
    if final_score == "0":
        return -(likert + 1)
    raise ValidationError(f"final_score must be binary for case {row.get(CASE_KEY)} model {row.get('model_key')}")


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
    states_source = states_path or Path("config/radle_v2_terminal_states.json")
    fields, rows = read_csv_table(final_master)
    require_columns(fields, [CASE_KEY, "model_blinded", "model_key", "reader_type", "likert", "final_score", "terminal_state"], "final master")
    roster = read_json(roster_source)
    zero_states = terminal_zero_states(states_source)
    present_model_keys = {str(row.get("model_key", "")) for row in rows if str(row.get("reader_type", "")).strip() == "model"}
    effective_roster = build_effective_model_roster(roster, present_model_keys)
    missing_models = sorted(present_model_keys - set(effective_roster))
    if missing_models:
        raise ValidationError(f"model rows missing from roster: {missing_models}")
    human_order = human_label_order(roster)

    score_rows: list[dict[str, object]] = []
    for row in sorted(rows, key=lambda item: (case_sort_key(item.get(CASE_KEY, "")), candidate_label_sort_key(item.get("model_blinded", "Candidate ZZ")))):
        reader_type = str(row.get("reader_type", "")).strip() or "model"
        model_key = str(row.get("model_key", "")).strip()
        model_blinded = str(row.get("model_blinded", "")).strip()
        display_name = row.get("model_name", "") or model_key or model_blinded
        roster_status = ""
        effective_status = ""
        excluded = False
        active = False
        human_group = ""
        if reader_type == "human":
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
            "final_score": row.get("final_score", ""),
            "final_score_source": row.get("final_score_source", ""),
            "terminal_state": row.get("terminal_state", ""),
            "score1000_component": score1000_component(row, zero_states),
            "admission_id": row.get("admission_id", ""),
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
    outputs = manifest.get("outputs", {})
    for name, descriptor in outputs.items():
        path = lane_root / str(descriptor.get("path", ""))
        if not path.exists():
            raise ValidationError(f"IDK0 lane output missing: {name}")
        if sha256_file(path) != descriptor.get("sha256"):
            raise ValidationError(f"IDK0 lane output SHA mismatch: {name}")
    summary_fields, summary_rows = read_csv_table(lane_root / "public_candidate_summary.csv")
    require_columns(summary_fields, IDK0_SUMMARY_FIELDS, "public candidate summary")
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
    require_columns(panel_fields, IDK0_SUMMARY_FIELDS, "panel order")
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
    if case_id == "5":
        return 1, False, "synthetic_agreement_correct"
    if case_id == "6":
        return (1 if judge_key == "gemini" else 0), False, "synthetic_disagreement"
    if case_id == "7":
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
    prompt_sha = sha256_file(prompt_path)
    judge_config_sha = sha256_file(judges_path)
    terminal_policy_sha = sha256_file(repo_root / "config/radle_v2_terminal_states.json")
    variants_sha = sha256_file(staging_root / "accepted_variants_snapshot.csv")
    normalizer_code_sha = sha256_file(Path(__file__))
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
                "case_triplet_sha256": "",
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
        scores = {int(result["score"]) for result in results if result.get("parse_status") == "parsed"}
        any_flag = any(bool(result.get("flag_for_review")) for result in results)
        if len(results) == judge_count and len(scores) == 1 and not any_flag:
            locked_rows.append({
                CASE_KEY: case_id,
                "score": next(iter(scores)),
                "score_source": "dual_judge_agreement",
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
    for row in delta_rows:
        if row.get("terminal_state") == "mandatory_radiologist":
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
        },
        "malformed_cache_line_count": 0,
    })
    receipt.update(summary)
    receipt["result"] = "PASS"
    return receipt
