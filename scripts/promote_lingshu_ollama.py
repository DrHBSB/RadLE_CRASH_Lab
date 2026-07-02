#!/usr/bin/env python3
"""Promote the Lingshu-32B Ollama run to final + public tables.

Structurally a parametrized copy of promote_internvl_ollama.py. Guarded:
re-audits first and REFUSES to promote unless all 200 cells are accepted. If
Lingshu leaves repair targets (e.g. a truncated case with no complete JSON ->
PARSE_FAILED), handle them via the standard audit/repair or an adjudication
sidecar BEFORE promoting -- do not override blindly.

KEY DIFFERENCE vs the InternVL/OctoMed promote scripts: this passes
max_output_tokens=MAX_OUTPUT_TOKENS (1024) to audit_benchmark_output. The other
promote scripts omit it and the audit silently uses the module default (16384)
for its truncation check (execplan latent-bug note). Lingshu is the first model
that routinely hits finish_reason=length (its repetition tendency + the 1024
cap), so the audit must be told the real cap to label truncation honestly.

WHY THIS DOES NOT CHANGE ANY SCORE (verified against classify_cell_for_audit):
`hit_max_tokens` is consulted in exactly ONE place -- inside the PARSE_FAILED
branch (radle_benchmark.py:979) -- and only to pick a diagnostic DETAIL label
(`parse_failed_hit_max_tokens` vs `parse_failed_raw_not_recoverable`). It never
moves a cell into the repair bucket and is NEVER consulted for a cell that
extracted a valid diagnosis. A truncated Lingshu loop-case still has a complete
JSON early in the response, so extract_json_safely (take-last) yields a valid
diagnosis/abstention and the cell is `accepted` regardless of truncation. So
passing 1024 only makes the audit's truncation LABEL/column honest; it cannot
turn a clean run into a needs-override run. Take-last genuinely makes truncation
a non-issue for scoring; a truncated case with NO complete JSON correctly falls
through to PARSE_FAILED -> repair target (not a silent accept).

Steps:
  1. Re-audit raw CSV (with the real 1024 cap); assert 200/200 accepted.
  2. promote_final_results: raw -> final + manifest.
  3. export_public_release_tables: final -> public_release/ (no diagnoses/raw).
  4. Print the public model summary + final sha256.

Usage:
    python scripts/promote_lingshu_ollama.py
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

# The served model is the Modelfile-derived, context-capped tag (num_ctx=8192),
# built over hf.co/mradermacher/Lingshu-32B-GGUF:Q8_0.
OLLAMA_MODEL = os.environ.get("OLLAMA_LINGSHU_MODEL", "lingshu-32b-8k")
OLLAMA_BASE_TAG = os.environ.get("OLLAMA_LINGSHU_BASE_TAG", "hf.co/mradermacher/Lingshu-32B-GGUF:Q8_0")
MODEL_NAME = "lingshu_32b"
RUN_LABEL = "medical_full_200_cases_ollama"
# Must match the generation budget the run used (run_lingshu_32b_ollama.py) so the
# audit's truncation check reflects the actual cap, not the module default.
MAX_OUTPUT_TOKENS = int(os.environ.get("LINGSHU_MAX_OUTPUT_TOKENS", "1024"))


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

    # 1. Guard: must be 200/200 accepted. Pass the REAL cap so truncation is
    #    labeled honestly (see module docstring -- does not change any bucket).
    res = rb.audit_benchmark_output(
        raw_csv,
        models=models,
        expected_case_ids=expected,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    audit = res["audit"]
    n_accepted = int((audit["bucket"] == "accepted").sum())
    print(f"Pre-promote audit: {n_accepted}/{len(audit)} accepted (cap={MAX_OUTPUT_TOKENS})")
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
        "ollama_base_tag": OLLAMA_BASE_TAG,
        "quantization": "Q8_0 GGUF (LM) + mmproj (vision projector)",
        "base_model": "Lingshu-32B (Qwen2.5-VL-32B-Instruct medical fine-tune)",
        "temperature": rb.UNIVERSAL_TEMPERATURE,
        "temperature_note": (
            "Ran at UNIVERSAL_TEMPERATURE (0.01) for manuscript parity. q8 quant "
            "+ 0.01 temp are serving differences vs the cloud/vLLM models; record "
            "in methods. No per-model prompt, image payload, sampling, or retry "
            "changes were used."
        ),
        "context_window_note": (
            "num_ctx capped to 8192 via a Modelfile-derived model (lingshu-32b-8k) "
            "-- Ollama's OpenAI endpoint ignores extra_body num_ctx, and the raw "
            "tag's default 32768 context OOMs the vision compute buffer on a 40GB "
            "GPU. Mirrors the vLLM MAX_MODEL_LEN=8192 used for OctoMed/InternVL."
        ),
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "max_output_tokens_note": (
            "Generation budget capped at 1024 (resource cap, not a parity change): "
            "Lingshu emits its answer JSON first and short (largest genuine answer "
            "~172 tokens) but has a repetition tendency that would otherwise burn "
            "the budget. Take-last scoring is unchanged by the cap."
        ),
        "output_format_note": (
            "Lingshu often emits MULTIPLE JSON objects per response (commits a "
            "diagnosis, then a second JSON abstaining). extract_json_safely takes "
            "the LAST valid JSON; per radiologist ruling 2026-07-02 the model's "
            "FINAL JSON counts, so a commit-then-abstain response is a genuine "
            "abstention. No adjudication sidecar or take-first exception was used."
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
