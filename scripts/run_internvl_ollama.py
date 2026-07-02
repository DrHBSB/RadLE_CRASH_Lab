#!/usr/bin/env python3
"""Run the RadLE medical benchmark for InternVL3.5-8B served via Ollama.

InternVL3.5-8B is served through the Q8_0 GGUF build
`mradermacher/InternVL3_5-8B-GGUF`, which ships the LM quant and vision projector.
The image-conditioning probe must pass before this script is used. This runs the
SAME RadLE prompt and base64 image payload through Ollama's OpenAI-compatible
endpoint and writes the standard model-scoped run CSV, so the existing
audit/repair/promote path applies unchanged.

IMPORTANT model-specific facts (prove/watch before trusting a full run):
  * The mradermacher Q8 probe passed on cases 1/8/78/12/45 on 2026-07-02: outputs
    were distinct and image-specific, so Ollama's current llama.cpp build is reading
    images for this GGUF.
  * InternVL may emit clean JSON, prose around JSON, or abstentions. Do not change
    the prompt, image payload, temperature, or use best-of-N/retries to raise the
    answer rate; characterize the shakedown and treat the output as the model's
    capability result.
  * MAX_OUTPUT_TOKENS stays at 8192, matching the OctoMed path. The shared
    extract_json_safely trace-strip is guarded and inert if InternVL does not emit
    <think>...</think>.

Usage:
    python scripts/run_internvl_ollama.py            # full 200-case run
    python scripts/run_internvl_ollama.py --limit=8  # shakedown
"""
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import radle_benchmark as rb  # noqa: E402
import radle_medical_custom_runtime as mrt  # noqa: E402

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.environ.get(
    "OLLAMA_INTERNVL_MODEL", "hf.co/mradermacher/InternVL3_5-8B-GGUF:Q8_0"
)
MODEL_NAME = "internvl3_5_8b"
RUN_LABEL = "medical_full_200_cases_ollama"
MAX_OUTPUT_TOKENS = 8192
EXPECTED_CASES = 200
EXPECTED_IMAGES = 263


def dataset_root():
    root = os.environ.get("RADLE_LOCAL_DATASET_ROOT") or str(
        pathlib.Path.home() / "radle_dataset" / "RadLE v2 Dataset"
    )
    return pathlib.Path(root)


def main():
    test_limit = None
    for arg in sys.argv[1:]:
        if arg.startswith("--limit="):
            test_limit = int(arg.split("=", 1)[1])

    ds = dataset_root()
    run_id = f"{MODEL_NAME}_{RUN_LABEL}"
    paths = mrt.build_medical_run_paths(ds, model_name=MODEL_NAME, run_label=RUN_LABEL, run_id=run_id)
    print("Run id:", paths["run_id"])
    print("Master images:", paths["master_images_folder"])
    print("Raw CSV:", paths["raw_results_csv"])
    print("Ollama endpoint:", OLLAMA_BASE_URL, "| model:", OLLAMA_MODEL)

    idx = rb.build_image_index(paths["master_images_folder"])
    all_cases = sorted(idx.keys(), key=rb.numeric_case_sort_key)
    n_cases = len(all_cases) if test_limit is None else min(test_limit, len(all_cases))
    n_images = sum(len(idx[c]) for c in all_cases[:n_cases])
    print(f"Cases this run: {n_cases} | image files: {n_images}")
    if test_limit is None:
        if n_cases != EXPECTED_CASES:
            raise SystemExit(f"Expected {EXPECTED_CASES} cases, found {n_cases}. Check staging.")
        if n_images != EXPECTED_IMAGES:
            raise SystemExit(f"Expected {EXPECTED_IMAGES} images, found {n_images}. Check staging.")

    from openai import OpenAI

    client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    model_config = {"name": MODEL_NAME, "id": OLLAMA_MODEL, "extra": None}

    df = rb.run_benchmark(
        client=client,
        image_folder=paths["master_images_folder"],
        output_csv=paths["raw_results_csv"],
        test_limit=test_limit,
        models=[model_config],
        backup_dir=paths["raw_backup_dir"],
        resume=True,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    print("\nRows written:", len(df))

    # Quick diagnosis-rate summary so we can approve or stop after shakedown.
    diag_col = f"Diagnosis_{MODEL_NAME}"
    likert_col = f"Likert_{MODEL_NAME}"
    fail_tokens = {"PARSE_FAILED", "JSON_MISSING_KEY", "", "nan", "None"}
    parsed_ok = df[diag_col].apply(lambda d: str(d) not in fail_tokens)
    idk = df[diag_col].astype(str).str.lower().eq("i don't know").sum()
    real_diag = df[parsed_ok & ~df[diag_col].astype(str).str.lower().eq("i don't know")]

    print("=" * 60)
    print(f"Parsed SOME value (not PARSE_FAILED): {parsed_ok.sum()}/{len(df)}")
    print(f"  of which 'I don't know': {idk}")
    print(f"  of which a real diagnosis: {len(real_diag)}")
    print(f"No diagnosis (PARSE_FAILED, -> repair targets): {(~parsed_ok).sum()}")
    print("\nSample recovered diagnoses:")
    for _, r in real_diag.head(20).iterrows():
        print(f"  case {r['Master_Case_ID']}: {r[diag_col]!r} (likert {r.get(likert_col)!r})")
    print("\nDone. Next: audit this raw CSV, then repair/promote under the usual guardrails.")


if __name__ == "__main__":
    main()
