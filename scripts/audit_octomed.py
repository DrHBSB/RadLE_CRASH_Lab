#!/usr/bin/env python3
"""Read-only audit of the OctoMed-7B Ollama run.

Prints the standard audit tables (bucket/status/abstention summaries, dataset
integrity) and then fully surfaces every non-accepted cell -- repair targets,
no-paid cleanups, and analysis flags -- with the FULL raw response so we can
adjudicate. No writes, no API calls.

Usage:
    python scripts/audit_octomed.py
"""
import os
import pathlib
import sys

import pandas as pd

pd.set_option("display.max_rows", 300)
pd.set_option("display.max_colwidth", 200)
pd.set_option("display.width", 200)

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import radle_benchmark as rb  # noqa: E402
import radle_medical_custom_runtime as mrt  # noqa: E402

OLLAMA_MODEL = os.environ.get("OLLAMA_OCTOMED_MODEL", "hf.co/mradermacher/OctoMed-7B-GGUF:Q8_0")
MODEL_NAME = "octomed_7b"
RUN_LABEL = "medical_full_200_cases_ollama"


def dataset_root():
    root = os.environ.get("RADLE_LOCAL_DATASET_ROOT") or str(
        pathlib.Path.home() / "radle_dataset" / "RadLE v2 Dataset"
    )
    return pathlib.Path(root)


def main():
    ds = dataset_root()
    run_id = f"{MODEL_NAME}_{RUN_LABEL}"
    paths = mrt.build_medical_run_paths(ds, model_name=MODEL_NAME, run_label=RUN_LABEL, run_id=run_id)
    raw_csv = paths["raw_results_csv"]
    print("Raw CSV:", raw_csv)

    idx = rb.build_image_index(paths["master_images_folder"])
    expected = sorted(idx.keys(), key=rb.numeric_case_sort_key)
    models = [{"name": MODEL_NAME, "id": OLLAMA_MODEL, "extra": None}]

    res = rb.audit_benchmark_output(raw_csv, models=models, expected_case_ids=expected)

    print("\n===== DATASET INTEGRITY =====")
    print(res["dataset_integrity"].to_string(index=False))
    print("\n===== BUCKET SUMMARY =====")
    print(res["bucket_summary"].to_string(index=False))
    print("\n===== STATUS SUMMARY =====")
    print(res["status_summary"].to_string(index=False))
    print("\n===== ABSTENTION SUMMARY =====")
    print(res["abstention_summary"].to_string(index=False))

    audit = res["audit"]
    accepted = audit[audit["bucket"] == "accepted"]
    print(f"\nAccepted cells: {len(accepted)} / {len(audit)}")

    # Any committed diagnosis flagged for bad/missing Likert?
    bad_likert = audit[audit["status"].astype(str).str.contains("invalid_or_missing_likert", na=False)]
    print(f"Committed-diagnosis cells with invalid/missing Likert: {len(bad_likert)}")
    if len(bad_likert):
        print(bad_likert[["Master_Case_ID", "diagnosis", "likert", "status"]].to_string(index=False))

    # Everything not accepted, with FULL raw for adjudication.
    non_accepted = audit[audit["bucket"] != "accepted"].copy()
    print(f"\n===== NON-ACCEPTED CELLS ({len(non_accepted)}) =====")
    print(non_accepted[["Master_Case_ID", "bucket", "status", "reason", "diagnosis", "likert"]].to_string(index=False))

    # Full raw for the true repair targets (e.g. PARSE_FAILED) -- read from the CSV.
    df = pd.read_csv(raw_csv, dtype={"Master_Case_ID": str})
    df["Master_Case_ID"] = df["Master_Case_ID"].apply(rb.normalize_case_id)
    targets = audit[audit["bucket"].isin(["paid_repair", "terminal"])]
    raw_col = f"Raw_Response_{MODEL_NAME}"
    for cid in targets["Master_Case_ID"].tolist():
        rows = df[df["Master_Case_ID"] == cid]
        raw = rb.safe_str(rows.iloc[0].get(raw_col, "")) if len(rows) else "<row not found>"
        print("\n" + "=" * 70)
        print(f"REPAIR-TARGET CASE {cid} -- FULL RAW ({len(raw)} chars):")
        print(raw)


if __name__ == "__main__":
    main()
