from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


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
LONG_MASTER_FIELDS = [
    "Master_Case_ID",
    "model_blinded",
    "model_key",
    "model_name",
    "reader_type",
    "access",
    "domain",
    "Ground_Truth_Diagnosis",
    "diagnosis",
    "likert",
    "final_score",
    "final_score_source",
    "terminal_state",
    "score1000_raw",
    "weighted_score",
    "effective_n",
    "source_file",
    "source_row_sha256",
    "notes",
    "admission_id",
]


def model_fields(model_key: str) -> list[str]:
    return [f"{suffix}_{model_key}" for suffix in MODEL_SUFFIXES]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def ground_truth_for(case_id: int) -> str:
    if case_id == 164:
        return "Achalasia"
    return "synthetic condition"


def incoming_diagnosis_for(case_id: int) -> tuple[str, str]:
    if case_id == 1:
        return "synthetic condition", "4"
    if case_id == 2:
        return "I don't know", ""
    if case_id == 3:
        return "synthetic condition", "8"
    if case_id == 4:
        return "API_ERROR", ""
    if case_id == 10:
        return "candidate alternate", ""
    if case_id == 164:
        return "Diffuse esophageal spasm", "3"
    return "candidate alternate", "3"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create synthetic 200-case RadLE incremental-admission fixtures")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    incoming = out / "incoming_package"
    incoming.mkdir(parents=True, exist_ok=True)

    parent_model_key = "existing_model_v1"
    incoming_model_key = "synthetic_model_v1"
    parent_fields = KEY_FIELDS + model_fields(parent_model_key)
    incoming_fields = KEY_FIELDS + model_fields(incoming_model_key)

    parent_rows = []
    incoming_rows = []
    long_rows = []
    for case_id in range(1, 201):
        key_values = {
            "Master_Case_ID": str(case_id),
            "Associated_Images": f"synthetic_{case_id}.png",
            "Image_SHA256": f"{case_id:064x}",
        }
        gt = ground_truth_for(case_id)
        parent_row = dict(key_values)
        parent_row.update({
            f"Diagnosis_{parent_model_key}": gt,
            f"Likert_{parent_model_key}": "4",
            f"Prompt_Tokens_{parent_model_key}": "10",
            f"Total_Tokens_Out_{parent_model_key}": "20",
            f"Reasoning_Tokens_{parent_model_key}": "0",
            f"Latency_{parent_model_key}": "1.0",
            f"Provider_{parent_model_key}": "Synthetic",
            f"Timestamp_UTC_{parent_model_key}": "2026-01-01T00:00:00+00:00",
            f"Reasoning_{parent_model_key}": "",
            f"Reasoning_Raw_{parent_model_key}": "",
            f"Reasoning_Details_{parent_model_key}": "",
            f"Actual_Request_Extra_{parent_model_key}": "{}",
            f"Grok_Fallback_Used_{parent_model_key}": "False",
            f"OpenRouter_Response_Model_{parent_model_key}": "existing-model",
            f"Usage_JSON_{parent_model_key}": "{}",
            f"Raw_Response_{parent_model_key}": json.dumps({"diagnosis": gt, "likert_score": 4}),
        })
        parent_rows.append(parent_row)

        diagnosis, likert = incoming_diagnosis_for(case_id)
        incoming_row = dict(key_values)
        incoming_row.update({
            f"Diagnosis_{incoming_model_key}": diagnosis,
            f"Likert_{incoming_model_key}": likert,
            f"Prompt_Tokens_{incoming_model_key}": "11",
            f"Total_Tokens_Out_{incoming_model_key}": "21",
            f"Reasoning_Tokens_{incoming_model_key}": "0",
            f"Latency_{incoming_model_key}": "1.1",
            f"Provider_{incoming_model_key}": "Synthetic",
            f"Timestamp_UTC_{incoming_model_key}": "2026-01-02T00:00:00+00:00",
            f"Reasoning_{incoming_model_key}": "",
            f"Reasoning_Raw_{incoming_model_key}": "",
            f"Reasoning_Details_{incoming_model_key}": "",
            f"Actual_Request_Extra_{incoming_model_key}": "{}",
            f"Grok_Fallback_Used_{incoming_model_key}": "False",
            f"OpenRouter_Response_Model_{incoming_model_key}": "synthetic-model",
            f"Usage_JSON_{incoming_model_key}": "{}",
            f"Raw_Response_{incoming_model_key}": json.dumps({"diagnosis": diagnosis, "likert_score": likert}),
        })
        incoming_rows.append(incoming_row)

        long_rows.append({
            "Master_Case_ID": str(case_id),
            "model_blinded": "Candidate A",
            "model_key": parent_model_key,
            "model_name": "Existing Synthetic Model",
            "reader_type": "model",
            "access": "synthetic",
            "domain": "synthetic",
            "Ground_Truth_Diagnosis": gt,
            "diagnosis": gt,
            "likert": "4",
            "final_score": "1",
            "final_score_source": "fixture",
            "terminal_state": "canonical_exact",
            "score1000_raw": "5",
            "weighted_score": "",
            "effective_n": "200",
            "source_file": "parent_wide.csv",
            "source_row_sha256": "",
            "notes": "",
            "admission_id": "synthetic_parent",
        })

    write_csv(out / "parent_wide.csv", parent_fields, parent_rows)
    write_csv(out / "parent_final_long_master.csv", LONG_MASTER_FIELDS, long_rows)
    write_csv(incoming / "results.csv", incoming_fields, incoming_rows)

    synthetic_roster = {
        "schema_version": "synthetic_roster.v1",
        "models": [
            {
                "model_key": parent_model_key,
                "display_name": "Existing Synthetic Model",
                "requested_model_id": "synthetic/existing-model",
                "returned_model_pattern": "existing-model",
                "runtime_path": "synthetic",
                "provider_route": "synthetic",
                "provider_value": "Synthetic",
                "access": "synthetic",
                "domain": "synthetic",
                "blind_label": "Candidate A",
                "roster_status": "complete_master_active",
            },
            {
                "model_key": incoming_model_key,
                "display_name": "Synthetic Admission Model",
                "requested_model_id": "synthetic/admission-model",
                "returned_model_pattern": "synthetic-model",
                "runtime_path": "synthetic incoming package",
                "provider_route": "synthetic",
                "provider_value": "Synthetic",
                "access": "synthetic",
                "domain": "synthetic",
                "blind_label": "Candidate AE",
                "roster_status": "pending_admission",
                "replaces_model_key": parent_model_key,
            },
        ],
        "blind_label_map": [
            {"blind_label": "Candidate A", "entry_type": "model", "key": parent_model_key, "provider": "Synthetic"},
            {"blind_label": "Candidate AE", "entry_type": "model", "key": incoming_model_key, "provider": "Synthetic"},
        ],
    }
    (out / "model_roster.json").write_text(json.dumps(synthetic_roster, indent=2) + "\n", encoding="utf-8")
    (out / "parent_authority.json").write_text(
        json.dumps({"schema_version": "synthetic", "case_count": 200, "parent_model_key": parent_model_key}) + "\n",
        encoding="utf-8",
    )
    (out / "accepted_variants.csv").write_text(
        "Master_Case_ID,diagnosis,decision\n1,synthetic condition,accepted\n",
        encoding="utf-8",
    )
    print(f"SYNTHETIC_FIXTURE_ROOT={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
