from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create synthetic 200-case RadLE incremental-admission fixtures")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    incoming = out / "incoming_package"
    incoming.mkdir(parents=True, exist_ok=True)

    key_fields = ["Master_Case_ID", "Associated_Images", "Image_SHA256"]
    model_key = "synthetic_model_v1"
    model_fields = [
        f"Diagnosis_{model_key}",
        f"Likert_{model_key}",
        f"Prompt_Tokens_{model_key}",
        f"Total_Tokens_Out_{model_key}",
        f"Reasoning_Tokens_{model_key}",
        f"Latency_{model_key}",
        f"Provider_{model_key}",
        f"Timestamp_UTC_{model_key}",
        f"Reasoning_{model_key}",
        f"Reasoning_Raw_{model_key}",
        f"Reasoning_Details_{model_key}",
        f"Actual_Request_Extra_{model_key}",
        f"Grok_Fallback_Used_{model_key}",
        f"OpenRouter_Response_Model_{model_key}",
        f"Usage_JSON_{model_key}",
        f"Raw_Response_{model_key}",
    ]
    fields = key_fields + model_fields

    rows = []
    for case_id in range(1, 201):
        rows.append({
            "Master_Case_ID": str(case_id),
            "Associated_Images": f"synthetic_{case_id}.png",
            "Image_SHA256": f"{case_id:064x}",
            f"Diagnosis_{model_key}": "synthetic condition",
            f"Likert_{model_key}": "3",
            f"Prompt_Tokens_{model_key}": "10",
            f"Total_Tokens_Out_{model_key}": "20",
            f"Reasoning_Tokens_{model_key}": "0",
            f"Latency_{model_key}": "1.0",
            f"Provider_{model_key}": "Synthetic",
            f"Timestamp_UTC_{model_key}": "2026-01-01T00:00:00+00:00",
            f"Reasoning_{model_key}": "",
            f"Reasoning_Raw_{model_key}": "",
            f"Reasoning_Details_{model_key}": "",
            f"Actual_Request_Extra_{model_key}": "{}",
            f"Grok_Fallback_Used_{model_key}": "False",
            f"OpenRouter_Response_Model_{model_key}": "synthetic-model",
            f"Usage_JSON_{model_key}": "{}",
            f"Raw_Response_{model_key}": "{\"diagnosis\":\"synthetic condition\",\"likert_score\":3}",
        })

    for path in [out / "parent_wide.csv", incoming / "results.csv"]:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    (out / "parent_authority.json").write_text('{"schema_version":"synthetic"}\n', encoding="utf-8")
    (out / "accepted_variants.csv").write_text(
        "Master_Case_ID,diagnosis,decision\n1,synthetic condition,accepted\n",
        encoding="utf-8",
    )
    print(f"SYNTHETIC_FIXTURE_ROOT={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
