#!/usr/bin/env python3
"""Build and verify the locked RadLE v2 Excel-safe reasoning review export."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
REQUIREMENTS_PATH = (
    REPO_ROOT
    / "Documents"
    / "requirements_radle_v2_excel_safe_reasoning_review_export.md"
)

LOCKED_PACKAGE_ROOT = Path(
    r"C:\tmp\radle_v2_muse_high_carry_forward_after_gpt_20260711"
    r"\muse_spark_1_1\finalized"
    r"\18e1d292e1fe1f8d654be09aa2f65f65c6cc951be4b5d37d3c6649645e127df4"
)
LONG_MASTER_PATH = LOCKED_PACKAGE_ROOT / "final" / "radle_v2_final_long_master.csv"
WIDE_PATH = LOCKED_PACKAGE_ROOT / "combined_wide" / "RadLE_v2_results_final.csv"
ROSTER_PATH = LOCKED_PACKAGE_ROOT / "roster" / "model_roster.json"
REPO_LONG_COPY_PATH = (
    OUTPUTS_ROOT
    / "radle_v2_stats"
    / "final_scoring_radiologist_20260711_muse_head_IDK0_review"
    / "radle_v2_final_long_master.csv"
)

LONG_SHA256 = "D539A42AA04AA9A9A76FF4210B0FC74DE40B27DCED54E1A3887C9C911016AB9F"
WIDE_SHA256 = "5DD4C87E74E3124ACBF87B44A3CA7D1F89795C065AF55EE958FBC3A70AF786DD"

LONG_HEADER = (
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
)
REASONING_HEADER = ("reasoning_text_1", "reasoning_text_2", "reasoning_text_3")
OUTPUT_HEADER = LONG_HEADER + REASONING_HEADER

MODEL_KEYS = (
    "gpt_5_5",
    "claude_4_8_opus",
    "gemini_3_1_pro",
    "grok_4_20",
    "qwen_3_7_plus",
    "gemma_4_31b",
    "llama_4_maverick",
    "mistral_large_3_2512",
    "glm_4_6v",
    "nemotron_3_omni",
    "grok_4_3",
    "minimax_m3",
    "glm_5v_turbo",
    "claude_fable_5",
    "medgemma_1_5_4b",
    "octomed_7b",
    "internvl3_5_8b",
    "lingshu_32b",
    "grok_4_5",
    "gpt_5_6_sol_pro",
    "muse_spark_1_1",
)

EXPECTED_EXTRACTION_BY_MODEL = {
    key: {
        "raw": (
            200
            if key
            in {
                "gemini_3_1_pro",
                "qwen_3_7_plus",
                "gemma_4_31b",
                "glm_4_6v",
                "nemotron_3_omni",
                "grok_4_3",
                "minimax_m3",
                "glm_5v_turbo",
                "grok_4_5",
            }
            else 83
            if key == "gpt_5_6_sol_pro"
            else 0
        ),
        "details_fallback": 27 if key == "gpt_5_6_sol_pro" else 0,
    }
    for key in MODEL_KEYS
}
for _model_key, _counts in EXPECTED_EXTRACTION_BY_MODEL.items():
    _counts["unavailable"] = 200 - _counts["raw"] - _counts["details_fallback"]

EXPECTED_ROWS = 6600
EXPECTED_LONG_COLUMNS = 20
EXPECTED_WIDE_ROWS = 200
EXPECTED_WIDE_COLUMNS = 339
EXPECTED_MODEL_ROWS = 4200
EXPECTED_HUMAN_ROWS = 2400
EXPECTED_READABLE_ROWS = 1910
EXPECTED_UNAVAILABLE_MODEL_ROWS = 2290
EXPECTED_BLANK_REASONING_ROWS = 4690
EXPECTED_PRE_NEWLINE_ROWS = 1435
EXPECTED_CHUNK_DISTRIBUTION = {"0": 4690, "1": 1887, "2": 19, "3": 4}

CHUNK_LIMIT_UTF16 = 30000
MAX_CHUNKS = 3
OUTPUT_FILENAME = "radle_v2_final_long_master_reasoning_review_excel_safe.csv"
RECEIPT_FILENAME = "reasoning_review_export_receipt.json"
PENDING_PATTERN = re.compile(
    r"^\.radle_v2_reasoning_review_(\d{8}T\d{6}Z)\.pending$"
)
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")
AUTHORIZED_EXISTING_FIELD_NORMALIZATION = {
    "output_row_number": 4364,
    "run_id": "radle_v2_blinded_combined",
    "Master_Case_ID": "156",
    "candidate": "Trainee",
    "provider": "Prathamesh Tadage",
    "column": "diagnosis",
    "source_value": "CLIDEOCRANIAL DYSPLASIA \nHOLT ORAM SYNDROME",
    "output_value": "CLIDEOCRANIAL DYSPLASIA HOLT ORAM SYNDROME",
    "authorization": "User-authorized in Codex task on 2026-07-28",
}


class ExportError(RuntimeError):
    """A contract failure that must stop publication."""


@dataclass(frozen=True)
class SourceBundle:
    long_rows: list[dict[str, str]]
    wide_by_case: dict[str, dict[str, str]]
    roster: list[dict[str, Any]]
    source_facts: dict[str, Any]
    preflight_counts: dict[str, int]


@dataclass(frozen=True)
class DerivedReasoning:
    chunks: tuple[str, str, str]
    source_kind: str
    canonical_text: str
    sanitized_text: str
    pre_counts: dict[str, int]
    post_counts: dict[str, int]


@dataclass(frozen=True)
class ExpectedExport:
    bundle: SourceBundle
    rows: list[list[str]]
    metrics: dict[str, Any]
    representative_rows: dict[str, dict[str, Any]]


def fail(message: str) -> None:
    raise ExportError(message)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def utc_token() -> str:
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def set_csv_field_limit() -> int:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return limit
        except OverflowError:
            limit //= 10


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        fail(f"Missing {label}: {path}")


def canonical_case_id(value: str) -> str:
    text = value.strip()
    if not text:
        fail("Blank Master_Case_ID cannot be canonicalized")
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ExportError(f"Invalid Master_Case_ID {value!r}") from exc
    if not number.is_finite() or number != number.to_integral_value():
        fail(f"Master_Case_ID is not a finite integer: {value!r}")
    integer = int(number)
    if not 1 <= integer <= 200:
        fail(f"Master_Case_ID is outside 1..200: {value!r}")
    return str(integer)


def numeric_value(value: str) -> Decimal | None:
    text = value.strip()
    if not text:
        return None
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ExportError(f"Invalid numeric value {value!r}") from exc
    if not number.is_finite():
        fail(f"Non-finite numeric value {value!r}")
    return number


def numeric_equal(left: str, right: str) -> bool:
    left_text = left.strip()
    right_text = right.strip()
    if not left_text or not right_text:
        return left_text == right_text
    if left_text == right_text == "PARSE_FAILED":
        return True
    try:
        return numeric_value(left_text) == numeric_value(right_text)
    except ExportError:
        return False


def read_csv_projected(
    path: Path,
    *,
    required_columns: Sequence[str] | None = None,
    expected_column_count: int | None = None,
) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    set_csv_field_limit()
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header_list = next(reader)
        except StopIteration:
            fail(f"CSV is empty: {path}")
        header = tuple(header_list)
        if len(set(header)) != len(header):
            fail(f"CSV has duplicate columns: {path}")
        if expected_column_count is not None and len(header) != expected_column_count:
            fail(
                f"Unexpected column count for {path}: "
                f"{len(header)} != {expected_column_count}"
            )
        selected = tuple(required_columns) if required_columns is not None else header
        missing = [name for name in selected if name not in header]
        if missing:
            fail(f"CSV is missing required columns in {path}: {missing}")
        indexes = [(name, header.index(name)) for name in selected]
        for physical_row, values in enumerate(reader, start=2):
            if len(values) != len(header):
                fail(
                    f"CSV row {physical_row} in {path} has {len(values)} "
                    f"fields; expected {len(header)}"
                )
            rows.append({name: values[index] for name, index in indexes})
    return header, rows


def load_roster() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    require_file(ROSTER_PATH, "roster")
    try:
        payload = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportError(f"Invalid roster JSON: {ROSTER_PATH}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        fail("Roster JSON must contain a models array")
    models = payload["models"]
    if len(models) != len(MODEL_KEYS):
        fail(f"Roster has {len(models)} models; expected {len(MODEL_KEYS)}")
    keys = tuple(item.get("model_key") for item in models if isinstance(item, dict))
    if keys != MODEL_KEYS:
        fail(f"Roster model order or keys changed: {keys}")
    fact = {
        "path": str(ROSTER_PATH.resolve()),
        "sha256": sha256_file(ROSTER_PATH),
        "bytes": ROSTER_PATH.stat().st_size,
        "models": len(models),
    }
    return models, fact


def source_file_fact(
    path: Path,
    *,
    sha256: str,
    rows: int,
    columns: int,
) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "sha256": sha256,
        "bytes": path.stat().st_size,
        "rows": rows,
        "columns": columns,
    }


def preflight_sources() -> SourceBundle:
    for path, label in (
        (LONG_MASTER_PATH, "authoritative final-long source"),
        (WIDE_PATH, "combined-wide source"),
        (ROSTER_PATH, "roster source"),
        (REPO_LONG_COPY_PATH, "repo-side final-long copy"),
        (REQUIREMENTS_PATH, "requirements document"),
    ):
        require_file(path, label)

    long_sha = sha256_file(LONG_MASTER_PATH)
    wide_sha = sha256_file(WIDE_PATH)
    repo_copy_sha = sha256_file(REPO_LONG_COPY_PATH)
    if long_sha != LONG_SHA256:
        fail(f"Final-long SHA-256 changed: {long_sha} != {LONG_SHA256}")
    if wide_sha != WIDE_SHA256:
        fail(f"Combined-wide SHA-256 changed: {wide_sha} != {WIDE_SHA256}")
    if repo_copy_sha != LONG_SHA256:
        fail(
            "Repo-side final-long copy is not byte-identical to the locked source: "
            f"{repo_copy_sha} != {LONG_SHA256}"
        )

    roster, roster_fact = load_roster()
    wide_required = ["Master_Case_ID"]
    for model in MODEL_KEYS:
        wide_required.extend(
            (
                f"Diagnosis_{model}",
                f"Likert_{model}",
                f"Reasoning_Raw_{model}",
                f"Reasoning_Details_{model}",
            )
        )

    long_header, long_rows = read_csv_projected(
        LONG_MASTER_PATH,
        required_columns=LONG_HEADER,
        expected_column_count=EXPECTED_LONG_COLUMNS,
    )
    if long_header != LONG_HEADER:
        fail(f"Final-long header changed: {long_header}")
    if len(long_rows) != EXPECTED_ROWS:
        fail(f"Final-long row count changed: {len(long_rows)} != {EXPECTED_ROWS}")

    wide_header, wide_rows = read_csv_projected(
        WIDE_PATH,
        required_columns=wide_required,
        expected_column_count=EXPECTED_WIDE_COLUMNS,
    )
    if len(wide_rows) != EXPECTED_WIDE_ROWS:
        fail(f"Wide row count changed: {len(wide_rows)} != {EXPECTED_WIDE_ROWS}")

    diagnosis_families = {
        name.removeprefix("Diagnosis_")
        for name in wide_header
        if name.startswith("Diagnosis_")
    }
    if set(MODEL_KEYS) != diagnosis_families:
        fail(
            "Combined-wide model families changed: "
            f"{sorted(diagnosis_families)}"
        )

    wide_by_case: dict[str, dict[str, str]] = {}
    for row in wide_rows:
        case_id = canonical_case_id(row["Master_Case_ID"])
        if case_id in wide_by_case:
            fail(f"Duplicate wide Master_Case_ID: {case_id}")
        wide_by_case[case_id] = row
    expected_cases = {str(value) for value in range(1, 201)}
    if set(wide_by_case) != expected_cases:
        fail("Combined-wide case IDs are not exactly 1 through 200")

    model_key_set = set(MODEL_KEYS)
    joined_keys: set[tuple[str, str]] = set()
    model_counts: Counter[str] = Counter()
    human_candidates: Counter[str] = Counter()
    diagnosis_mismatches = 0
    likert_mismatches = 0
    model_rows = 0
    human_rows = 0
    for row in long_rows:
        candidate = row["candidate"].strip()
        case_id = canonical_case_id(row["Master_Case_ID"])
        if candidate in model_key_set:
            model_rows += 1
            model_counts[candidate] += 1
            join_key = (case_id, candidate)
            if join_key in joined_keys:
                fail(f"Duplicate final-long model join key: {join_key}")
            joined_keys.add(join_key)
            wide_row = wide_by_case.get(case_id)
            if wide_row is None:
                fail(f"Missing wide case for final-long row: {case_id}")
            if row["diagnosis"].strip() != wide_row[f"Diagnosis_{candidate}"].strip():
                diagnosis_mismatches += 1
            if not numeric_equal(row["likert"], wide_row[f"Likert_{candidate}"]):
                likert_mismatches += 1
        else:
            human_rows += 1
            human_candidates[candidate] += 1

    if model_rows != EXPECTED_MODEL_ROWS:
        fail(f"Model row count changed: {model_rows} != {EXPECTED_MODEL_ROWS}")
    if human_rows != EXPECTED_HUMAN_ROWS:
        fail(f"Human row count changed: {human_rows} != {EXPECTED_HUMAN_ROWS}")
    if len(joined_keys) != EXPECTED_MODEL_ROWS:
        fail(f"Unique join count changed: {len(joined_keys)}")
    if model_counts != Counter({key: 200 for key in MODEL_KEYS}):
        fail(f"Per-model final-long counts changed: {dict(model_counts)}")
    if human_candidates != Counter({"Radiologist": 1200, "Trainee": 1200}):
        fail(f"Human candidate counts changed: {dict(human_candidates)}")
    if diagnosis_mismatches:
        fail(f"Diagnosis parity failed for {diagnosis_mismatches} model rows")
    if likert_mismatches:
        fail(f"Likert parity failed for {likert_mismatches} model rows")

    source_facts = {
        "authoritative_final_long": source_file_fact(
            LONG_MASTER_PATH,
            sha256=long_sha,
            rows=len(long_rows),
            columns=len(long_header),
        ),
        "repo_final_long_copy": source_file_fact(
            REPO_LONG_COPY_PATH,
            sha256=repo_copy_sha,
            rows=len(long_rows),
            columns=len(long_header),
        ),
        "combined_wide": source_file_fact(
            WIDE_PATH,
            sha256=wide_sha,
            rows=len(wide_rows),
            columns=len(wide_header),
        ),
        "roster": roster_fact,
        "requirements": {
            "path": str(REQUIREMENTS_PATH.resolve()),
            "sha256": sha256_file(REQUIREMENTS_PATH),
            "bytes": REQUIREMENTS_PATH.stat().st_size,
        },
    }
    return SourceBundle(
        long_rows=long_rows,
        wide_by_case=wide_by_case,
        roster=roster,
        source_facts=source_facts,
        preflight_counts={
            "model_rows": model_rows,
            "human_rows": human_rows,
            "unique_model_joins": len(joined_keys),
            "diagnosis_mismatches": diagnosis_mismatches,
            "likert_mismatches": likert_mismatches,
        },
    )


def collect_readable_nodes(value: Any, selected: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if (
                isinstance(key, str)
                and key.casefold() in {"text", "summary"}
                and isinstance(child, str)
                and child.strip()
            ):
                selected.append(child)
            collect_readable_nodes(child, selected)
    elif isinstance(value, list):
        for child in value:
            collect_readable_nodes(child, selected)


def extract_readable_reasoning(
    wide_row: dict[str, str],
    model: str,
    *,
    case_id: str = "<unknown>",
) -> tuple[str, str]:
    raw = wide_row[f"Reasoning_Raw_{model}"]
    if raw.strip():
        return raw, "raw"

    details = wide_row[f"Reasoning_Details_{model}"]
    if not details.strip():
        return "", "unavailable"
    try:
        parsed = json.loads(details)
    except json.JSONDecodeError as exc:
        raise ExportError(
            f"Malformed nonblank Reasoning_Details for {model}, case {case_id}"
        ) from exc

    selected: list[str] = []
    collect_readable_nodes(parsed, selected)
    deduplicated: list[str] = []
    seen: set[str] = set()
    for item in selected:
        if item not in seen:
            seen.add(item)
            deduplicated.append(item)
    if not deduplicated:
        return "", "unavailable"
    return "\n\n".join(deduplicated), "details_fallback"


def character_counts(text: str) -> dict[str, int]:
    actual_crlf = text.count("\r\n")
    c0_other = sum(
        1
        for character in text
        if ord(character) <= 0x1F and character not in {"\r", "\n", "\t"}
    )
    return {
        "literal_crlf": text.count(r"\r\n"),
        "literal_lf": text.count(r"\n"),
        "literal_cr": text.count(r"\r"),
        "actual_crlf": actual_crlf,
        "actual_cr": text.count("\r"),
        "actual_lf": text.count("\n"),
        "tabs": text.count("\t"),
        "u2028": text.count("\u2028"),
        "u2029": text.count("\u2029"),
        "c0_other": c0_other,
        "del": text.count("\x7f"),
    }


def add_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0) + value


def sanitize_reasoning(text: str) -> str:
    sanitized = text.replace(r"\r\n", " ")
    sanitized = sanitized.replace(r"\n", " ")
    sanitized = sanitized.replace(r"\r", " ")
    sanitized = sanitized.replace("\r\n", " ")
    sanitized = sanitized.replace("\r", " ")
    sanitized = sanitized.replace("\n", " ")
    sanitized = sanitized.replace("\t", " ")
    sanitized = sanitized.replace("\u2028", " ")
    sanitized = sanitized.replace("\u2029", " ")
    sanitized = "".join(
        " " if ord(character) <= 0x1F or ord(character) == 0x7F else character
        for character in sanitized
    )
    return re.sub(r"\s+", " ", sanitized).strip()


def forbidden_character_count(text: str) -> int:
    counts = character_counts(text)
    return sum(counts.values())


def utf16_units(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def formula_triggered(text: str) -> bool:
    return bool(text) and text.startswith(FORMULA_PREFIXES)


def chunk_excel_safe(
    text: str,
    *,
    max_units: int = CHUNK_LIMIT_UTF16,
    max_chunks: int = MAX_CHUNKS,
) -> tuple[str, ...]:
    if not text:
        return ()
    chunks: list[str] = []
    remaining = text
    while remaining:
        if utf16_units(remaining) <= max_units:
            chunks.append(remaining)
            break

        units = 0
        prefix_end = 0
        for index, character in enumerate(remaining):
            character_units = 2 if ord(character) > 0xFFFF else 1
            if units + character_units > max_units:
                break
            units += character_units
            prefix_end = index + 1
        boundary = remaining.rfind(" ", 0, prefix_end + 1)
        if boundary <= 0:
            fail(
                "Readable reasoning contains a token longer than the "
                f"{max_units}-UTF-16-unit chunk ceiling"
            )
        chunks.append(remaining[:boundary])
        remaining = remaining[boundary + 1 :]
        if len(chunks) >= max_chunks and remaining:
            fail(f"Readable reasoning requires more than {max_chunks} chunks")

    if len(chunks) > max_chunks:
        fail(f"Readable reasoning requires more than {max_chunks} chunks")
    for chunk in chunks:
        if utf16_units(chunk) > max_units:
            fail("Chunk exceeds the UTF-16 length ceiling")
        if formula_triggered(chunk):
            fail(f"Reasoning chunk begins with an Excel formula trigger: {chunk[:20]!r}")
    if " ".join(chunks) != text:
        fail("Reasoning chunk reconstruction is not lossless")
    return tuple(chunks)


def derive_reasoning_for_candidate(
    candidate: str,
    wide_row: dict[str, str] | None,
    *,
    model_keys: Iterable[str] = MODEL_KEYS,
    case_id: str = "<unknown>",
) -> DerivedReasoning:
    if candidate not in set(model_keys):
        return DerivedReasoning(
            chunks=("", "", ""),
            source_kind="human",
            canonical_text="",
            sanitized_text="",
            pre_counts=character_counts(""),
            post_counts=character_counts(""),
        )
    if wide_row is None:
        fail(f"Missing wide row for model candidate {candidate}, case {case_id}")
    canonical, source_kind = extract_readable_reasoning(
        wide_row, candidate, case_id=case_id
    )
    if not canonical:
        return DerivedReasoning(
            chunks=("", "", ""),
            source_kind="unavailable",
            canonical_text="",
            sanitized_text="",
            pre_counts=character_counts(""),
            post_counts=character_counts(""),
        )
    pre_counts = character_counts(canonical)
    sanitized = sanitize_reasoning(canonical)
    if not sanitized:
        fail(f"Readable reasoning became blank after sanitization: {candidate}/{case_id}")
    post_counts = character_counts(sanitized)
    if forbidden_character_count(sanitized):
        fail(f"Forbidden character survived sanitization: {candidate}/{case_id}")
    chunks = chunk_excel_safe(sanitized)
    padded = tuple(chunks) + ("",) * (MAX_CHUNKS - len(chunks))
    if " ".join(item for item in padded if item) != sanitized:
        fail(f"Reasoning reconstruction failed: {candidate}/{case_id}")
    return DerivedReasoning(
        chunks=(padded[0], padded[1], padded[2]),
        source_kind=source_kind,
        canonical_text=canonical,
        sanitized_text=sanitized,
        pre_counts=pre_counts,
        post_counts=post_counts,
    )


def row_reference(
    source_row: dict[str, str], *, output_row_number: int
) -> dict[str, Any]:
    return {
        "output_row_number": output_row_number,
        "run_id": source_row["run_id"],
        "Master_Case_ID": source_row["Master_Case_ID"],
        "candidate": source_row["candidate"],
        "provider": source_row["provider"],
        "rater_seniority": source_row["rater_seniority"],
    }


def prepare_existing_values(
    source_row: dict[str, str], *, output_row_number: int
) -> tuple[list[str], bool]:
    values = [source_row[name] for name in LONG_HEADER]
    newline_columns = [
        name
        for name in LONG_HEADER
        if "\r" in source_row[name] or "\n" in source_row[name]
    ]
    if not newline_columns:
        return values, False

    exception = AUTHORIZED_EXISTING_FIELD_NORMALIZATION
    identity_matches = (
        output_row_number == exception["output_row_number"]
        and source_row["run_id"] == exception["run_id"]
        and canonical_case_id(source_row["Master_Case_ID"])
        == exception["Master_Case_ID"]
        and source_row["candidate"] == exception["candidate"]
        and source_row["provider"] == exception["provider"]
        and newline_columns == [exception["column"]]
        and source_row[exception["column"]] == exception["source_value"]
    )
    if not identity_matches:
        fail(
            "An unauthorized original final-long field contains a physical "
            f"newline at output row {output_row_number}: {newline_columns}"
        )

    output_index = LONG_HEADER.index(exception["column"])
    values[output_index] = exception["output_value"]
    if any("\r" in value or "\n" in value for value in values):
        fail("The authorized existing-field normalization did not remove the LF")
    return values, True


def build_expected_export() -> ExpectedExport:
    bundle = preflight_sources()
    model_key_set = set(MODEL_KEYS)
    output_rows: list[list[str]] = []
    extraction_totals: Counter[str] = Counter()
    per_model = {
        key: {"raw": 0, "details_fallback": 0, "unavailable": 0}
        for key in MODEL_KEYS
    }
    chunk_distribution: Counter[int] = Counter()
    pre_counts: dict[str, int] = {}
    post_counts: dict[str, int] = {}
    readable_rows = 0
    unavailable_model_rows = 0
    human_rows = 0
    pre_newline_rows = 0
    reconstruction_failures = 0
    formula_triggers = 0
    max_chunk_length = 0
    authorized_existing_field_normalizations = 0
    representative_rows: dict[str, dict[str, Any]] = {}

    for zero_index, source_row in enumerate(bundle.long_rows):
        output_row_number = zero_index + 2
        original_values, normalized_existing_field = prepare_existing_values(
            source_row, output_row_number=output_row_number
        )
        authorized_existing_field_normalizations += int(
            normalized_existing_field
        )

        candidate = source_row["candidate"].strip()
        case_id = canonical_case_id(source_row["Master_Case_ID"])
        wide_row = bundle.wide_by_case.get(case_id) if candidate in model_key_set else None
        derived = derive_reasoning_for_candidate(
            candidate,
            wide_row,
            model_keys=MODEL_KEYS,
            case_id=case_id,
        )
        extraction_totals[derived.source_kind] += 1

        if candidate in model_key_set:
            per_model[candidate][derived.source_kind] += 1
            if derived.source_kind == "unavailable":
                unavailable_model_rows += 1
                representative_rows.setdefault(
                    "unavailable_model",
                    row_reference(source_row, output_row_number=output_row_number),
                )
            else:
                readable_rows += 1
                if "\r" in derived.canonical_text or "\n" in derived.canonical_text:
                    pre_newline_rows += 1
        else:
            human_rows += 1
            if candidate == "Radiologist":
                representative_rows.setdefault(
                    "radiologist",
                    row_reference(source_row, output_row_number=output_row_number),
                )
            elif candidate == "Trainee":
                representative_rows.setdefault(
                    "trainee",
                    row_reference(source_row, output_row_number=output_row_number),
                )

        populated_chunks = [chunk for chunk in derived.chunks if chunk]
        chunk_count = len(populated_chunks)
        chunk_distribution[chunk_count] += 1
        if chunk_count:
            representative_rows.setdefault(
                f"{chunk_count}_chunk",
                row_reference(source_row, output_row_number=output_row_number),
            )
        add_counts(pre_counts, derived.pre_counts)
        add_counts(post_counts, derived.post_counts)
        for chunk in populated_chunks:
            max_chunk_length = max(max_chunk_length, utf16_units(chunk))
            formula_triggers += int(formula_triggered(chunk))
        if populated_chunks and " ".join(populated_chunks) != derived.sanitized_text:
            reconstruction_failures += 1

        output_rows.append(original_values + list(derived.chunks))

    metrics: dict[str, Any] = {
        "output_rows": len(output_rows),
        "output_columns": len(OUTPUT_HEADER),
        "model_rows_joined": bundle.preflight_counts["unique_model_joins"],
        "human_rows_blank": human_rows,
        "readable_model_reasoning_rows": readable_rows,
        "model_rows_without_readable_reasoning": unavailable_model_rows,
        "all_reasoning_chunks_blank_rows": chunk_distribution[0],
        "readable_rows_with_actual_cr_or_lf_before_sanitization": pre_newline_rows,
        "readable_rows_with_actual_cr_or_lf_after_sanitization": 0,
        "extraction_source_counts": {
            "raw": extraction_totals["raw"],
            "details_fallback": extraction_totals["details_fallback"],
            "unavailable": extraction_totals["unavailable"],
            "human": extraction_totals["human"],
        },
        "extraction_by_model": per_model,
        "pre_sanitization_character_counts": pre_counts,
        "post_sanitization_forbidden_character_counts": post_counts,
        "chunk_count_distribution": {
            str(index): chunk_distribution[index] for index in range(4)
        },
        "maximum_chunks_used": max(
            (count for count, rows in chunk_distribution.items() if rows), default=0
        ),
        "maximum_utf16_chunk_length": max_chunk_length,
        "reconstruction_failures": reconstruction_failures,
        "formula_triggering_chunks": formula_triggers,
        "diagnosis_mismatches": bundle.preflight_counts["diagnosis_mismatches"],
        "likert_mismatches": bundle.preflight_counts["likert_mismatches"],
        "authorized_existing_field_normalizations": (
            authorized_existing_field_normalizations
        ),
    }
    assert_locked_acceptance(metrics)
    required_representatives = {
        "1_chunk",
        "2_chunk",
        "3_chunk",
        "unavailable_model",
        "radiologist",
        "trainee",
    }
    if set(representative_rows) != required_representatives:
        fail(
            "Could not identify all required Excel representative rows: "
            f"{sorted(representative_rows)}"
        )
    return ExpectedExport(
        bundle=bundle,
        rows=output_rows,
        metrics=metrics,
        representative_rows=representative_rows,
    )


def assert_locked_acceptance(metrics: dict[str, Any]) -> None:
    exact = {
        "output_rows": EXPECTED_ROWS,
        "output_columns": len(OUTPUT_HEADER),
        "model_rows_joined": EXPECTED_MODEL_ROWS,
        "human_rows_blank": EXPECTED_HUMAN_ROWS,
        "readable_model_reasoning_rows": EXPECTED_READABLE_ROWS,
        "model_rows_without_readable_reasoning": EXPECTED_UNAVAILABLE_MODEL_ROWS,
        "all_reasoning_chunks_blank_rows": EXPECTED_BLANK_REASONING_ROWS,
        "readable_rows_with_actual_cr_or_lf_before_sanitization": (
            EXPECTED_PRE_NEWLINE_ROWS
        ),
        "readable_rows_with_actual_cr_or_lf_after_sanitization": 0,
        "maximum_chunks_used": 3,
        "reconstruction_failures": 0,
        "formula_triggering_chunks": 0,
        "diagnosis_mismatches": 0,
        "likert_mismatches": 0,
        "authorized_existing_field_normalizations": 1,
    }
    for key, expected in exact.items():
        if metrics.get(key) != expected:
            fail(f"Locked acceptance drift for {key}: {metrics.get(key)} != {expected}")
    if metrics["chunk_count_distribution"] != EXPECTED_CHUNK_DISTRIBUTION:
        fail(
            "Locked chunk distribution changed: "
            f"{metrics['chunk_count_distribution']} != {EXPECTED_CHUNK_DISTRIBUTION}"
        )
    expected_sources = {
        "raw": 1883,
        "details_fallback": 27,
        "unavailable": EXPECTED_UNAVAILABLE_MODEL_ROWS,
        "human": EXPECTED_HUMAN_ROWS,
    }
    if metrics["extraction_source_counts"] != expected_sources:
        fail(
            "Locked extraction-source counts changed: "
            f"{metrics['extraction_source_counts']} != {expected_sources}"
        )
    if metrics["extraction_by_model"] != EXPECTED_EXTRACTION_BY_MODEL:
        fail("Per-model reasoning availability changed from the requirements table")
    if metrics["maximum_utf16_chunk_length"] > CHUNK_LIMIT_UTF16:
        fail("Maximum UTF-16 chunk length exceeds the locked ceiling")
    if sum(metrics["post_sanitization_forbidden_character_counts"].values()) != 0:
        fail("Post-sanitization forbidden-character count is nonzero")


def write_quote_all_csv(path: Path, rows: Sequence[Sequence[str]]) -> None:
    if path.exists():
        fail(f"Refusing to overwrite existing candidate CSV: {path}")
    part = path.with_name(path.name + ".part")
    if part.exists():
        fail(f"Refusing to overwrite existing partial CSV: {part}")
    with part.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(
            handle,
            delimiter=",",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
            doublequote=True,
            lineterminator="\r\n",
        )
        writer.writerow(OUTPUT_HEADER)
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(part, path)


def quoted_field_count(record: str) -> int:
    if not record:
        fail("CSV contains an empty physical record")
    index = 0
    fields = 0
    while True:
        if index >= len(record) or record[index] != '"':
            fail("CSV field is not double-quote delimited")
        index += 1
        while True:
            if index >= len(record):
                fail("CSV record has an unterminated quoted field")
            if record[index] == '"':
                if index + 1 < len(record) and record[index + 1] == '"':
                    index += 2
                    continue
                index += 1
                break
            index += 1
        fields += 1
        if index == len(record):
            return fields
        if record[index] != ",":
            fail("CSV has content outside a quoted field")
        index += 1


def inspect_csv_wire(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    bom = b"\xef\xbb\xbf"
    if not data.startswith(bom):
        fail("Output CSV is missing the UTF-8 byte-order mark")
    payload = data[len(bom) :]
    if not payload.endswith(b"\r\n"):
        fail("Output CSV does not end with a CRLF record terminator")
    physical_lines = payload.count(b"\r\n")
    remainder = payload.replace(b"\r\n", b"")
    if b"\r" in remainder or b"\n" in remainder:
        fail("Output CSV contains a bare CR or LF")
    encoded_records = payload.split(b"\r\n")
    if encoded_records[-1] != b"":
        fail("Output CSV has unexpected bytes after the final record")
    records = encoded_records[:-1]
    for record_number, encoded in enumerate(records, start=1):
        try:
            record = encoded.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ExportError(f"Output record {record_number} is not UTF-8") from exc
        fields = quoted_field_count(record)
        if fields != len(OUTPUT_HEADER):
            fail(
                f"Output record {record_number} has {fields} quoted fields; "
                f"expected {len(OUTPUT_HEADER)}"
            )
    return {
        "bytes": len(data),
        "physical_lines": physical_lines,
        "bom": "UTF-8-SIG",
        "record_terminator": "CRLF",
        "quoting": "QUOTE_ALL",
    }


def verify_candidate_csv(path: Path, expected: ExpectedExport) -> dict[str, Any]:
    require_file(path, "candidate CSV")
    wire = inspect_csv_wire(path)
    header, parsed_rows = read_csv_projected(
        path,
        required_columns=OUTPUT_HEADER,
        expected_column_count=len(OUTPUT_HEADER),
    )
    if header != OUTPUT_HEADER:
        fail(f"Output header changed: {header}")
    if len(parsed_rows) != EXPECTED_ROWS:
        fail(f"Output row count changed: {len(parsed_rows)}")
    for index, parsed in enumerate(parsed_rows):
        actual = [parsed[name] for name in OUTPUT_HEADER]
        wanted = expected.rows[index]
        if actual != wanted:
            fail(f"Output differs from expected parsed values at data row {index + 1}")
        expected_existing, _ = prepare_existing_values(
            expected.bundle.long_rows[index], output_row_number=index + 2
        )
        if actual[: len(LONG_HEADER)] != expected_existing:
            fail(
                "First 20 source values changed outside the one authorized "
                f"normalization at data row {index + 1}"
            )
        chunks = actual[len(LONG_HEADER) :]
        if any(forbidden_character_count(chunk) for chunk in chunks):
            fail(f"Forbidden reasoning character at data row {index + 1}")
        if any(formula_triggered(chunk) for chunk in chunks if chunk):
            fail(f"Formula-triggering reasoning chunk at data row {index + 1}")
        if any(utf16_units(chunk) > CHUNK_LIMIT_UTF16 for chunk in chunks):
            fail(f"Oversized reasoning chunk at data row {index + 1}")

    if wire["physical_lines"] != EXPECTED_ROWS + 1:
        fail(
            f"Output physical-line count changed: "
            f"{wire['physical_lines']} != {EXPECTED_ROWS + 1}"
        )
    return {
        "path": str(path.resolve()),
        "repo_relative_path": str(path.resolve().relative_to(REPO_ROOT.resolve())),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "rows": len(parsed_rows),
        "columns": len(header),
        "physical_lines": wire["physical_lines"],
        "encoding": wire["bom"],
        "record_terminator": wire["record_terminator"],
        "quoting": wire["quoting"],
        "header": list(header),
    }


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        fail(f"Git command failed: git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def git_state() -> dict[str, Any]:
    status = run_git("status", "--porcelain=v1", "-uall")
    lines = status.splitlines() if status else []
    staged = 0
    tracked_dirty = 0
    untracked = 0
    for line in lines:
        code = line[:2]
        if code == "??":
            untracked += 1
            continue
        if code and code[0] != " ":
            staged += 1
        if len(code) > 1 and code[1] != " ":
            tracked_dirty += 1
    return {
        "root": str(REPO_ROOT),
        "branch": run_git("branch", "--show-current"),
        "head": run_git("rev-parse", "HEAD"),
        "dirty": bool(lines),
        "status_line_count": len(lines),
        "staged_path_count": staged,
        "tracked_dirty_path_count": tracked_dirty,
        "untracked_path_count": untracked,
        "porcelain_sha256": hashlib.sha256(status.encode("utf-8")).hexdigest().upper(),
    }


def receipt_roster(roster: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = (
        "model_key",
        "display_name",
        "provider_value",
        "access",
        "domain",
        "roster_status",
    )
    return [{key: item.get(key) for key in keys} for item in roster]


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    part = path.with_name(path.name + ".part")
    with part.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(part, path)


def read_receipt(path: Path) -> dict[str, Any]:
    require_file(path, "export receipt")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportError(f"Invalid receipt JSON: {path}") from exc
    if not isinstance(payload, dict):
        fail("Receipt JSON must be an object")
    return payload


def staging_paths(staging_argument: str | Path) -> tuple[Path, Path]:
    path = Path(staging_argument)
    if not path.is_absolute():
        path = REPO_ROOT / path
    try:
        staging = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ExportError(f"Pending export directory does not exist: {path}") from exc
    if not staging.is_dir():
        fail(f"Pending export path is not a directory: {staging}")
    if staging.parent != OUTPUTS_ROOT.resolve():
        fail(f"Pending export directory must be directly under {OUTPUTS_ROOT}")
    match = PENDING_PATTERN.fullmatch(staging.name)
    if not match:
        fail(f"Invalid pending export directory name: {staging.name}")
    final = OUTPUTS_ROOT.resolve() / f"radle_v2_reasoning_review_{match.group(1)}"
    return staging, final


def atomic_promote_directory(staging: Path, final: Path) -> None:
    if final.exists():
        fail(f"Refusing to overwrite existing final export directory: {final}")
    staging.rename(final)


def build_receipt(
    *,
    expected: ExpectedExport,
    staging: Path,
    intended_final: Path,
    output_fact: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "radle-v2-reasoning-review-receipt-v1",
        "status": "built_pending_verification",
        "generated_at_utc": utc_iso(),
        "generator": {
            "identity": "scripts/build_radle_v2_reasoning_review_export.py",
            "path": str(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__).resolve()),
            "python": sys.version,
        },
        "repository": git_state(),
        "sources": expected.bundle.source_facts,
        "model_roster": receipt_roster(expected.bundle.roster),
        "preflight": expected.bundle.preflight_counts,
        "metrics": expected.metrics,
        "representative_rows": expected.representative_rows,
        "authorized_existing_field_normalization": (
            AUTHORIZED_EXISTING_FIELD_NORMALIZATION
        ),
        "output": {
            **output_fact,
            "staging_directory": str(staging),
            "intended_final_directory": str(intended_final),
        },
        "programmatic_verification": {
            "status": "pending",
            "verified_at_utc": None,
        },
        "excel_smoke_test": {
            "status": "pending",
            "observed_at_utc": None,
            "checks": {},
        },
    }


def validate_receipt_sources(
    receipt: dict[str, Any], expected: ExpectedExport
) -> None:
    recorded_sources = receipt.get("sources")
    if recorded_sources != expected.bundle.source_facts:
        fail("Receipt source facts do not match the current locked sources")
    if receipt.get("metrics") != expected.metrics:
        fail("Receipt metrics do not match the recomputed locked metrics")
    if receipt.get("representative_rows") != expected.representative_rows:
        fail("Receipt representative rows do not match recomputed rows")


def perform_verification(
    staging_argument: str | Path, *, update_receipt: bool
) -> tuple[dict[str, Any], Path, Path]:
    staging, final = staging_paths(staging_argument)
    candidate = staging / OUTPUT_FILENAME
    receipt_path = staging / RECEIPT_FILENAME
    receipt = read_receipt(receipt_path)
    if receipt.get("status") not in {
        "built_pending_verification",
        "verified_pending_excel",
    }:
        fail(f"Receipt is not in a verifiable pending state: {receipt.get('status')}")

    expected = build_expected_export()
    validate_receipt_sources(receipt, expected)
    output_fact = verify_candidate_csv(candidate, expected)
    recorded_output = receipt.get("output")
    if not isinstance(recorded_output, dict):
        fail("Receipt output section is missing")
    for key in ("sha256", "bytes", "rows", "columns", "physical_lines", "header"):
        if recorded_output.get(key) != output_fact.get(key):
            fail(
                f"Receipt output {key} does not match candidate: "
                f"{recorded_output.get(key)} != {output_fact.get(key)}"
            )

    receipt["status"] = "verified_pending_excel"
    receipt["programmatic_verification"] = {
        "status": "pass",
        "verified_at_utc": utc_iso(),
        "method": "fresh on-disk source reconstruction and strict CSV read-back",
    }
    receipt["output"].update(output_fact)
    receipt["output"]["staging_directory"] = str(staging)
    receipt["output"]["intended_final_directory"] = str(final)
    if update_receipt:
        write_json_atomic(receipt_path, receipt)
    return receipt, staging, final


def command_build() -> dict[str, Any]:
    expected = build_expected_export()
    token = utc_token()
    staging = OUTPUTS_ROOT / f".radle_v2_reasoning_review_{token}.pending"
    final = OUTPUTS_ROOT / f"radle_v2_reasoning_review_{token}"
    if staging.exists() or final.exists():
        fail(f"Timestamped output path already exists for token {token}")
    OUTPUTS_ROOT.mkdir(parents=True, exist_ok=True)
    staging.mkdir(exist_ok=False)
    candidate = staging / OUTPUT_FILENAME
    write_quote_all_csv(candidate, expected.rows)
    output_fact = verify_candidate_csv(candidate, expected)
    receipt = build_receipt(
        expected=expected,
        staging=staging.resolve(),
        intended_final=final.resolve(),
        output_fact=output_fact,
    )
    write_json_atomic(staging / RECEIPT_FILENAME, receipt)
    return {
        "status": receipt["status"],
        "staging_directory": str(staging.resolve()),
        "candidate_csv": str(candidate.resolve()),
        "receipt": str((staging / RECEIPT_FILENAME).resolve()),
        "intended_final_directory": str(final.resolve()),
        "metrics": expected.metrics,
    }


def command_verify(staging_argument: str) -> dict[str, Any]:
    receipt, staging, final = perform_verification(
        staging_argument, update_receipt=True
    )
    return {
        "status": receipt["programmatic_verification"]["status"],
        "receipt_status": receipt["status"],
        "staging_directory": str(staging),
        "candidate_csv": str(staging / OUTPUT_FILENAME),
        "intended_final_directory": str(final),
        "metrics": receipt["metrics"],
        "representative_rows": receipt["representative_rows"],
    }


def command_finalize(staging_argument: str, excel_result: str) -> dict[str, Any]:
    if excel_result != "pass":
        fail("Only an observed Excel result of 'pass' can promote an export")
    staging, final = staging_paths(staging_argument)
    receipt_path = staging / RECEIPT_FILENAME
    prior_receipt = read_receipt(receipt_path)
    if prior_receipt.get("programmatic_verification", {}).get("status") != "pass":
        fail("Finalization requires a prior successful verify command")

    receipt, staging, final = perform_verification(
        staging_argument, update_receipt=False
    )
    final_candidate = final / OUTPUT_FILENAME
    receipt["status"] = "complete"
    receipt["finalized_at_utc"] = utc_iso()
    receipt["output"]["path"] = str(final_candidate)
    receipt["output"]["repo_relative_path"] = str(
        final_candidate.relative_to(REPO_ROOT)
    )
    receipt["output"]["staging_directory"] = None
    receipt["output"]["final_directory"] = str(final)
    receipt["excel_smoke_test"] = {
        "status": "pass",
        "observed_at_utc": utc_iso(),
        "witnessed_candidate_sha256": receipt["output"]["sha256"],
        "checks": {
            "one_worksheet_no_import_repair_warning": True,
            "header_at_row_1": True,
            "final_data_at_row_6601": True,
            "columns_a_through_w_aligned": True,
            "no_reasoning_spill_into_adjacent_columns": True,
            "no_additional_rows_from_reasoning": True,
            "no_formula_interpretation": True,
            "utf8_characters_readable": True,
            "filters_enabled_across_23_columns": True,
            "one_chunk_row_readable": True,
            "two_chunk_row_readable": True,
            "three_chunk_row_readable": True,
            "unavailable_model_row_blank": True,
            "radiologist_row_blank": True,
            "trainee_row_blank": True,
            "closed_without_saving": True,
        },
    }

    write_json_atomic(receipt_path, receipt)
    try:
        atomic_promote_directory(staging, final)
    except Exception:
        write_json_atomic(receipt_path, prior_receipt)
        raise
    return {
        "status": "complete",
        "final_directory": str(final),
        "csv": str(final / OUTPUT_FILENAME),
        "receipt": str(final / RECEIPT_FILENAME),
        "output_sha256": receipt["output"]["sha256"],
        "metrics": receipt["metrics"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build, verify, and Excel-witness the locked RadLE v2 reasoning "
            "review export."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build", help="Build a new pending candidate and receipt")

    verify_parser = subparsers.add_parser(
        "verify", help="Reconstruct and verify a pending candidate from disk"
    )
    verify_parser.add_argument("--staging-dir", required=True)

    finalize_parser = subparsers.add_parser(
        "finalize", help="Promote an Excel-witnessed pending candidate"
    )
    finalize_parser.add_argument("--staging-dir", required=True)
    finalize_parser.add_argument("--excel-result", required=True, choices=("pass",))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            result = command_build()
        elif args.command == "verify":
            result = command_verify(args.staging_dir)
        elif args.command == "finalize":
            result = command_finalize(args.staging_dir, args.excel_result)
        else:
            parser.error(f"Unsupported command: {args.command}")
            return 2
    except ExportError as exc:
        print(
            json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
