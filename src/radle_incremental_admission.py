from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import unicodedata
from collections import Counter
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
    intake_payload = {
        "schema_version": "radle_v2_intake_identity.v1",
        "model_key": model_key,
        "case_count": len(case_ids),
        "input_hashes": input_hashes,
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
