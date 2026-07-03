#!/usr/bin/env python3
"""Targeted repair for the Lingshu-32B Ollama run's remaining bad cells.

Standard schema-stable repair path (same mechanism used for OctoMed/InternVL),
NOT a new decision: `run_targeted_repair` re-queries ONLY the flagged
case-model cells, using the exact same payload/prompt/temperature as the
original run (manuscript parity preserved -- this is a retry of a malformed
response, not a prompt/sampling change). Distinct from the LLaVA-Med
no-retry ruling, which was specifically about deterministic EMPTY
generations (a capability finding); a single out-of-range `likert_score`
(e.g. 10, outside the 0-4 spec) is a malformed-output repair target, exactly
what this mechanism exists for.

Writes the repaired rows back onto the SAME raw_results_csv (in place, with
numbered backups via backup_dir) so promote_lingshu_ollama.py's raw CSV
pointer picks up the fix with no path changes needed.

Usage:
    python scripts/repair_lingshu_ollama.py               # dry run (plan only)
    python scripts/repair_lingshu_ollama.py --confirm      # repair up to 10 cells
"""
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import radle_benchmark as rb  # noqa: E402
import radle_medical_custom_runtime as mrt  # noqa: E402

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_LINGSHU_MODEL", "lingshu-32b-8k")
MODEL_NAME = "lingshu_32b"
RUN_LABEL = "medical_full_200_cases_ollama"
MAX_OUTPUT_TOKENS = int(os.environ.get("LINGSHU_MAX_OUTPUT_TOKENS", "1024"))
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "8192"))


def dataset_root():
    root = os.environ.get("RADLE_LOCAL_DATASET_ROOT") or str(
        pathlib.Path.home() / "radle_dataset" / "RadLE v2 Dataset"
    )
    return pathlib.Path(root)


def main():
    confirm = "YES_REPAIR_10" if "--confirm" in sys.argv[1:] else "NO"

    ds = dataset_root()
    run_id = f"{MODEL_NAME}_{RUN_LABEL}"
    paths = mrt.build_medical_run_paths(ds, model_name=MODEL_NAME, run_label=RUN_LABEL, run_id=run_id)
    raw_csv = paths["raw_results_csv"]
    print("Raw CSV (repair in place):", raw_csv)
    print("Confirmation mode:", confirm)

    from openai import OpenAI

    client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    model_config = {
        "name": MODEL_NAME,
        "id": OLLAMA_MODEL,
        "extra": {"options": {"num_ctx": OLLAMA_NUM_CTX}},
    }

    result = rb.run_targeted_repair(
        client=client,
        image_folder=paths["master_images_folder"],
        input_csv=raw_csv,
        output_csv=raw_csv,
        confirmation=confirm,
        models=[model_config],
        max_output_tokens=MAX_OUTPUT_TOKENS,
        backup_dir=paths["raw_backup_dir"],
    )
    print("\nAPI calls this run:", result["api_calls_this_run"])
    print("No-paid cleanups applied:", result["no_paid_cleanups_applied"])
    remaining = result["remaining_repair_plan"]
    print(f"Remaining repair-plan rows: {len(remaining)}")
    if len(remaining):
        print(remaining.to_string(index=False))
    print("\nDone. Re-run scripts/promote_lingshu_ollama.py to re-audit.")


if __name__ == "__main__":
    main()
