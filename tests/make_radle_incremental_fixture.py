from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
KEY_FIELDS = ["Master_Case_ID", "Associated_Images", "Image_SHA256"]
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
BASE_MODEL_KEYS = [
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
]
HUMAN_LABELS = ["S", "T", "U", "V", "W", "X", "Y", "Z", "AA", "AB", "AC", "AD"]
INCOMING_MODEL = "grok_4_5"


def model_fields(model_key: str) -> list[str]:
    return [f"{suffix}_{model_key}" for suffix in MODEL_SUFFIXES]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]], *, lineterminator: str = "\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator=lineterminator)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fieldnames} for row in rows)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def canonical_text_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def associated_images(case_id: int) -> tuple[str, str]:
    # 150x1 + 41x2 + 6x3 + 2x4 + 1x5 = 263 image references.
    if case_id <= 150:
        count = 1
    elif case_id <= 191:
        count = 2
    elif case_id <= 197:
        count = 3
    elif case_id <= 199:
        count = 4
    else:
        count = 5
    images = [f"{case_id}.{index}.png" for index in range(1, count + 1)]
    hashes = [hashlib.sha256(image.encode("utf-8")).hexdigest()[:16] for image in images]
    return ", ".join(images), ", ".join(hashes)


def ground_truth(case_id: int) -> str:
    return "Achalasia" if case_id == 164 else "Synthetic condition"


def incoming_answer(case_id: int) -> tuple[str, str]:
    if case_id == 1:
        return "Synthetic condition", "4"
    if case_id == 2:
        return "I don't know", ""
    if case_id == 3:
        return "Idon't know", ""
    if case_id == 4:
        return "API_ERROR", "PARSE_FAILED"
    if case_id == 5:
        return "Candidate alternate", "8"
    if case_id == 6:
        return "Candidate alternate", ""
    if case_id == 164:
        return "Diffuse esophageal spasm", "3"
    return "Candidate alternate", "3"


def model_wide_values(model_key: str, diagnosis: str, likert: str, provider: str, returned: str, raw: str) -> dict[str, object]:
    return {
        f"Diagnosis_{model_key}": diagnosis,
        f"Likert_{model_key}": likert,
        f"Prompt_Tokens_{model_key}": "10",
        f"Total_Tokens_Out_{model_key}": "20",
        f"Reasoning_Tokens_{model_key}": "0",
        f"Latency_{model_key}": "1.0",
        f"Provider_{model_key}": provider,
        f"Timestamp_UTC_{model_key}": "2026-01-01T00:00:00+00:00",
        f"Reasoning_{model_key}": "",
        f"Reasoning_Raw_{model_key}": "",
        f"Reasoning_Details_{model_key}": "",
        f"Actual_Request_Extra_{model_key}": json.dumps({"provider": {"only": [provider], "allow_fallbacks": False}}, sort_keys=True),
        f"Grok_Fallback_Used_{model_key}": "False",
        f"OpenRouter_Response_Model_{model_key}": returned,
        f"Usage_JSON_{model_key}": "{}",
        f"Raw_Response_{model_key}": raw,
    }


def make_fixture(out: Path) -> dict[str, object]:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    roster = json.loads((REPO_ROOT / "config/radle_v2_model_roster.json").read_text(encoding="utf-8"))
    roster_by_key = {model["model_key"]: model for model in roster["models"]}
    blind_entries = {entry["blind_label"]: entry for entry in roster["blind_label_map"]}

    parent_fields = KEY_FIELDS + [field for key in BASE_MODEL_KEYS for field in model_fields(key)]
    incoming_fields = KEY_FIELDS + model_fields(INCOMING_MODEL)
    parent_rows: list[dict[str, object]] = []
    incoming_rows: list[dict[str, object]] = []
    long_rows: list[dict[str, object]] = []

    for case_id in range(1, 201):
        associated, image_hashes = associated_images(case_id)
        key_values = {"Master_Case_ID": str(case_id), "Associated_Images": associated, "Image_SHA256": image_hashes}
        gt = ground_truth(case_id)
        parent_row: dict[str, object] = dict(key_values)
        for model_key in BASE_MODEL_KEYS:
            record = roster_by_key[model_key]
            raw = json.dumps({"diagnosis": gt, "likert_score": 4})
            if case_id == 1 and model_key == BASE_MODEL_KEYS[0]:
                raw = json.dumps({"diagnosis": gt, "likert_score": 4, "raw": "X" * 140_000})
            parent_row.update(model_wide_values(model_key, gt, "4.0", record["provider_value"], record["requested_model_id"], raw))
            long_rows.append({
                "run_id": "radle_v2_fixture",
                "Master_Case_ID": str(case_id),
                "Associated_Images": associated,
                "model_blinded": record["blind_label"],
                "candidate": model_key,
                "provider": record["provider_value"],
                "access": record["access"],
                "domain": record["domain"],
                "Ground_Truth_Diagnosis": gt,
                "diagnosis": gt,
                "likert": "4",
                "response_valid": "True",
                "abstained": "False",
                "technical_failure": "False",
                "score_required": "True",
                "final_score_authoritative": "1",
                "final_score_source": "fixture_parent",
                "weighted_score": "4.0",
                "rater_seniority": "",
                "rater_seniority_rank": "",
            })
        parent_rows.append(parent_row)

        diagnosis, likert = incoming_answer(case_id)
        incoming_record = roster_by_key[INCOMING_MODEL]
        incoming_row: dict[str, object] = dict(key_values)
        incoming_row.update(model_wide_values(
            INCOMING_MODEL,
            diagnosis,
            likert,
            incoming_record["provider_value"],
            incoming_record["requested_model_id"],
            json.dumps({"diagnosis": diagnosis, "likert_score": likert}),
        ))
        incoming_rows.append(incoming_row)

        for human_index, suffix in enumerate(HUMAN_LABELS, start=1):
            label = f"Candidate {suffix}"
            identity = blind_entries[label]["key"]
            correct = human_index <= 6
            candidate = "Radiologist" if human_index not in {2, 5, 7} else "Trainee"
            long_rows.append({
                "run_id": "radle_v2_fixture",
                "Master_Case_ID": str(case_id),
                "Associated_Images": associated,
                "model_blinded": label,
                "candidate": candidate,
                "provider": identity,
                "access": "human",
                "domain": "radiology",
                "Ground_Truth_Diagnosis": gt,
                "diagnosis": gt if correct else "Synthetic wrong answer",
                "likert": "4",
                "response_valid": "True",
                "abstained": "False",
                "technical_failure": "False",
                "score_required": "True",
                "final_score_authoritative": "1" if correct else "0",
                "final_score_source": "fixture_parent",
                "weighted_score": "4.0" if correct else "-4.0",
                "rater_seniority": "Senior" if candidate == "Radiologist" else "Trainee",
                "rater_seniority_rank": str(human_index),
            })

    parent_wide = out / "parent_wide.csv"
    parent_long = out / "parent_final_long_master.csv"
    blind_map = out / "blind_label_map.csv"
    incoming_root = out / "incoming_package"
    results = incoming_root / "results.csv"
    write_csv(parent_wide, parent_fields, parent_rows)
    write_csv(parent_long, FINAL_LONG_MASTER_FIELDS, long_rows, lineterminator="\r\n")
    base_blind_rows = [
        {"model_blinded": entry["blind_label"], "model_key": entry["key"], "provider": entry["provider"]}
        for entry in roster["blind_label_map"]
        if entry["blind_label"] not in {"Candidate AE", "Candidate AF", "Candidate AG"}
    ]
    write_csv(blind_map, ["model_blinded", "model_key", "provider"], base_blind_rows)
    write_csv(results, incoming_fields, incoming_rows)
    write_json(incoming_root / "source_manifest.json", {
        "schema_version": "radle_v2_fixture_source_manifest.v1",
        "model_key": INCOMING_MODEL,
        "row_count": 200,
        "test_limit": None,
        "run_label": "radle_v2_fixture_full",
        "runtime_sha": "1" * 40,
        "results_csv_sha256": sha256(results),
    })
    write_json(incoming_root / "promotion_audit.json", {
        "schema_version": "radle_v2_fixture_promotion_audit.v1",
        "case_count": 200,
        "test_limit": None,
        "unresolved_cells": 0,
    })
    write_json(incoming_root / "repair_evidence.json", {
        "schema_version": "radle_v2_fixture_repair_evidence.v1",
        "repair_complete": True,
        "unresolved_cells": 0,
    })
    inventory_paths = sorted(path for path in incoming_root.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (incoming_root / "SHA256SUMS").write_text(
        "".join(f"{sha256(path).lower()}  {path.relative_to(incoming_root).as_posix()}\n" for path in inventory_paths),
        encoding="utf-8",
    )

    roster_path = out / "roster.json"
    write_json(roster_path, roster)
    variants = out / "accepted_variants.csv"
    write_csv(variants, ["Master_Case_ID", "diagnosis", "decision"], [{"Master_Case_ID": "12", "diagnosis": "Synthetic variant", "decision": "accepted"}])
    authority = out / "parent_authority.json"
    write_json(authority, {
        "schema_version": "radle_v2_base_authority.v1",
        "base_combined_wide": {"path": "parent_wide.csv", "rows": 200, "columns": 291, "sha256": sha256(parent_wide)},
        "base_final_long_master": {"path": "parent_final_long_master.csv", "rows": 6000, "columns": 20, "sha256": sha256(parent_long)},
        "base_blinding_key": {"path": "blind_label_map.csv", "rows": 30, "columns": 3, "sha256": sha256(blind_map)},
        "requirements": {
            "requirements_radle_v2_incremental_model_admission.md": canonical_text_sha256(REPO_ROOT / "Documents/requirements_radle_v2_incremental_model_admission.md"),
            "radle_v2_incremental_model_pipeline_requirements_study.md": canonical_text_sha256(REPO_ROOT / "Documents/radle_v2_incremental_model_pipeline_requirements_study.md"),
        },
    })
    fixture_manifest = {
        "schema_version": "radle_v2_production_shape_fixture.v1",
        "parent_wide": {"rows": 200, "columns": 291, "sha256": sha256(parent_wide)},
        "parent_final_long_master": {"rows": 6000, "columns": 20, "sha256": sha256(parent_long)},
        "blind_label_map": {"rows": 30, "columns": 3, "sha256": sha256(blind_map)},
        "incoming": {"rows": 200, "columns": 19, "sha256": sha256(results)},
        "oversized_raw_response_bytes": len(str(parent_rows[0][f"Raw_Response_{BASE_MODEL_KEYS[0]}"]).encode("utf-8")),
        "image_count": 263,
    }
    write_json(out / "fixture_manifest.json", fixture_manifest)
    return fixture_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an exact production-shape RadLE incremental fixture")
    parser.add_argument("--out", required=True)
    parser.add_argument("--profile", choices=["production"], default="production")
    parser.add_argument("--model-key", default=INCOMING_MODEL)
    args = parser.parse_args()
    if args.model_key != INCOMING_MODEL:
        raise SystemExit(f"fixture currently locks model-key {INCOMING_MODEL}")
    manifest = make_fixture(Path(args.out))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print("FIXTURE_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
