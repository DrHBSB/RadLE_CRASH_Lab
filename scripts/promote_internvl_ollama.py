#!/usr/bin/env python3
"""Promote the clean InternVL3.5-8B Ollama run to final + public tables.

Guarded: re-audits first and REFUSES to promote unless all 200 cells are
accepted. InternVL reached a clean audit without cleanup or adjudication.

Steps:
  1. Re-audit raw CSV; assert 200/200 accepted.
  2. promote_final_results: raw -> final/RadLE_v2_results_final.csv + manifest.
  3. export_public_release_tables: final -> public_release/ (no diagnoses/raw).
  4. Print the public model summary + final sha256.

Usage:
    python scripts/promote_internvl_ollama.py
"""
import os
import pathlib
import sys

import pandas as pd

pd.set_option("display.max_colwidth", 60)
pd.set_option("display.width", 220)

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import radle_benchmark as rb  # noqa: E402
import radle_medical_custom_runtime as mrt  # noqa: E402

OLLAMA_MODEL = os.environ.get(
    "OLLAMA_INTERNVL_MODEL", "hf.co/mradermacher/InternVL3_5-8B-GGUF:Q8_0"
)
MODEL_NAME = "internvl3_5_8b"
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
    models = [{"name": MODEL_NAME, "id": OLLAMA_MODEL, "extra": None}]

    idx = rb.build_image_index(paths["master_images_folder"])
    expected = sorted(idx.keys(), key=rb.numeric_case_sort_key)

    # 1. Guard: must be 200/200 accepted.
    res = rb.audit_benchmark_output(raw_csv, models=models, expected_case_ids=expected)
    audit = res["audit"]
    n_accepted = int((audit["bucket"] == "accepted").sum())
    print(f"Pre-promote audit: {n_accepted}/{len(audit)} accepted")
    if n_accepted != len(audit):
        print(
            audit[audit["bucket"] != "accepted"][
                ["Master_Case_ID", "bucket", "status", "diagnosis", "likert"]
            ].to_string(index=False)
        )
        raise SystemExit("Refusing to promote: not all cells accepted.")

    status = res["status_summary"].set_index("status")["cells"].to_dict()
    n_diag = int(status.get("accepted_clean_diagnosis", 0))
    n_idk = int(status.get("accepted_i_dont_know", 0))

    # 2. Promote raw -> final with a rich manifest.
    metadata = {
        "model": MODEL_NAME,
        "served_via": "Ollama (OpenAI-compatible endpoint)",
        "ollama_model_tag": OLLAMA_MODEL,
        "quantization": "Q8_0 GGUF (LM) + Q8_0 mmproj (vision projector)",
        "base_model": "OpenGVLab/InternVL3_5-8B",
        "temperature": rb.UNIVERSAL_TEMPERATURE,
        "temperature_note": (
            "Ran at UNIVERSAL_TEMPERATURE (0.01) for manuscript parity. q8 quant "
            "+ 0.01 temp are serving differences vs the cloud/vLLM models; record "
            "in methods. No per-model prompt, image payload, sampling, or retry "
            "changes were used."
        ),
        "max_output_tokens": 8192,
        "image_conditioning_probe": (
            "mradermacher Q8 probe on 2026-07-02 passed: cases 1/8/78/12/45 "
            "returned distinct, image-specific outputs using the benchmark payload."
        ),
        "output_format_note": (
            "InternVL emitted RadLE JSON directly or with short prose wrappers, plus "
            "canonical I don't know abstentions. No cleanup or adjudication sidecar "
            "was needed."
        ),
        "audit_result": "200/200 accepted (no guardrail override needed)",
        "committed_diagnoses": n_diag,
        "abstentions_i_dont_know": n_idk,
        "cleanup_ref": None,
        "adjudication_ref": None,
    }
    manifest = rb.promote_final_results(
        source_csv=raw_csv,
        final_csv=paths["final_results_csv"],
        manifest_json=paths["final_manifest_json"],
        run_id=run_id,
        source_label="raw_clean",
        metadata=metadata,
    )
    print("\nPromoted -> final:")
    print("  final_csv:", paths["final_results_csv"])
    print("  manifest :", paths["final_manifest_json"])
    print("  sha256   :", manifest["sha256"])
    print(f"  split    : {n_diag} committed diagnoses / {n_idk} abstentions")

    # 3. Export public release tables from the final CSV.
    rb.export_public_release_tables(
        results_csv=paths["final_results_csv"],
        output_dir=paths["public_release_dir"],
        models=models,
        run_id=run_id,
    )
    print("\nPublic release dir:", paths["public_release_dir"])

    # 4. Show the public summary.
    summary_csv = os.path.join(paths["public_release_dir"], "RadLE_v2_public_model_summary.csv")
    summ = pd.read_csv(summary_csv)
    print("\n===== PUBLIC MODEL SUMMARY =====")
    print(summ.to_string(index=False))
    print("\nDone. Next: verify stats pipeline, then relay final + public_release off the VM via GCS.")


if __name__ == "__main__":
    main()
