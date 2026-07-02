#!/usr/bin/env python3
"""Run the RadLE medical benchmark for Lingshu-32B served via Ollama.

Lingshu-32B is a Qwen2.5-VL-32B-Instruct medical fine-tune, from the same base
architecture family as OctoMed-7B, which already proved the Ollama GGUF+mmproj
path for this vision tower. GGUF builds: `mradermacher/Lingshu-32B-GGUF`
(standard quants incl. Q8_0) and `mradermacher/Lingshu-32B-i1-GGUF` (imatrix
quants, e.g. Q6_K/Q5_K_M) as a fallback ONLY if Q8 does not fit.

IMPORTANT model-specific facts (prove/watch before trusting a full run):
  * The image-conditioning probe (scripts/ollama_lingshu_probe.py) MUST pass
    before this script is used.
  * CURRENT BOX = single A100-SXM4-40GB. Q8 (~34 GB LM + mmproj + KV cache at
    num_ctx=8192, ~37 GB total) fits on the ONE GPU with a few GB to spare --
    confirm ~37 GB, no OOM, no split on `nvidia-smi`. If it OOMs near 40 GB,
    lower num_ctx slightly (rebuild the Modelfile) rather than dropping quant;
    if a quant step-down were ever needed, record it explicitly in the run's
    manifest metadata (all prior models were q8). HISTORICAL: on the retired
    2x L4 (23 GB each) Q8 fit only by splitting across both cards over PCIe
    (~6 tok/s) -- the A100's single-GPU placement is why we migrated.
  * The shared extract_json_safely <think>-strip is guarded and stays inert
    if Lingshu does not emit a reasoning trace (it emits its JSON directly).
  * Temperature stays at UNIVERSAL_TEMPERATURE (0.01) for manuscript parity,
    NOT any model-card-recommended sampling. Record the q8 (or fallback)
    quant as a serving difference in the methods section.
  * CONTEXT CAP IS MANDATORY and MUST be baked in via a Modelfile -- Ollama's
    OpenAI-compatible endpoint (/v1/chat/completions) IGNORES options.num_ctx
    passed in extra_body (proven on this VM 2026-07-02: an extra_body num_ctx
    request still loaded the default 32768 context and OOM'd on the first image;
    a Modelfile-derived model with the cap baked in loaded cleanly and ran all
    5 probe cases). With no cap, Ollama loads the GGUF's default 32768-token
    context, reserving an 8192 MiB combined KV cache and leaving GPU0 with only
    ~504 MiB free (22530/23034 MiB) -- then the image's CLIP compute buffer
    (pinned to GPU0) OOMs. Create the capped model ONCE on the VM:
        printf 'FROM hf.co/mradermacher/Lingshu-32B-GGUF:Q8_0\nPARAMETER num_ctx 8192\n' > /tmp/Lingshu8k.Modelfile
        ollama create lingshu-32b-8k -f /tmp/Lingshu8k.Modelfile
    then run this script against the derived tag (the default below). 8192 is
    RadLE's actual need (same image payload + prompt that already fit OctoMed/
    InternVL at MAX_MODEL_LEN=8192). This is a serving-parameter cap, not a
    prompt/quant/temperature change -- it does not affect parity.
  * OUTPUT FORMAT NOTE (2026-07-02 probe): Lingshu tends to emit MULTIPLE JSON
    objects per response -- it commits a diagnosis, adds a "Note", then emits a
    SECOND JSON that often abstains ("I don't know"). extract_json_safely takes
    the LAST valid JSON (radle_benchmark.py:285), so a commit-then-abstain
    response is recorded as an abstention. Per user (radiologist) ruling
    2026-07-02, this is CORRECT and intended: the model's FINAL word counts, so
    if it walks itself back to "I don't know" that is a genuine abstention. Do
    NOT change the extractor to take-first, and do NOT build an adjudication
    sidecar to "recover" these -- the take-last behavior is the chosen scoring
    semantics. Lingshu therefore runs the standard raw -> audit -> promote path
    with no special handling (same as InternVL).

Usage:
    python scripts/run_lingshu_32b_ollama.py            # full 200-case run
    python scripts/run_lingshu_32b_ollama.py --limit=8  # shakedown
"""
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import radle_benchmark as rb  # noqa: E402
import radle_medical_custom_runtime as mrt  # noqa: E402

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
# Default to the Modelfile-derived model with num_ctx=8192 baked in. The raw
# GGUF tag (hf.co/mradermacher/Lingshu-32B-GGUF:Q8_0) loads at 32768 context and
# OOMs on the first image -- do NOT point this at the raw tag. Create the derived
# model first (see docstring), then optionally override OLLAMA_LINGSHU_MODEL.
OLLAMA_MODEL = os.environ.get("OLLAMA_LINGSHU_MODEL", "lingshu-32b-8k")
MODEL_NAME = "lingshu_32b"
RUN_LABEL = "medical_full_200_cases_ollama"
# Generation budget (resource cap, NOT a parity param). OctoMed used 8192 to fit
# a legitimate <think> reasoning trace; Lingshu emits its answer JSON FIRST and
# short (largest genuine answer observed on the shakedown was 172 output tokens),
# with NO <think> trace to protect. Its known repetition tendency (see OUTPUT
# FORMAT NOTE) makes a looping case grind at ~6 tok/s toward whatever the cap is,
# burning tokens the take-last extractor discards anyway (~20 min at 8192, ~5 min
# at 2048). 1024 keeps ~5x headroom over the largest genuine answer while capping
# a loop to ~3 min, roughly halving the 200-case wall-clock vs 2048. Scored
# answers are unchanged (take-last is stable; genuine answers fit with margin).
# Env-overridable. Document this per-model budget in the methods section
# alongside the q8 quant and num_ctx cap.
MAX_OUTPUT_TOKENS = int(os.environ.get("LINGSHU_MAX_OUTPUT_TOKENS", "1024"))
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "8192"))
EXPECTED_CASES = 200
EXPECTED_IMAGES = 263


def dataset_root():
    root = os.environ.get("RADLE_LOCAL_DATASET_ROOT") or str(
        pathlib.Path.home() / "radle_dataset" / "RadLE v2 Dataset"
    )
    return pathlib.Path(root)


def main():
    # Accept BOTH --limit=N and --limit N, and REJECT anything unrecognized.
    # (The old startswith("--limit=") silently dropped "--limit 8" -> a full
    #  200-case run instead of a shakedown. Fail loud instead of surprising.)
    test_limit = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--limit="):
            test_limit = int(arg.split("=", 1)[1])
        elif arg == "--limit":
            if i + 1 >= len(args):
                raise SystemExit("--limit requires a value, e.g. --limit 8 or --limit=8")
            test_limit = int(args[i + 1])
            i += 1
        else:
            raise SystemExit(f"Unrecognized argument: {arg!r}. Use --limit=N (or --limit N).")
        i += 1

    ds = dataset_root()
    run_id = f"{MODEL_NAME}_{RUN_LABEL}"
    paths = mrt.build_medical_run_paths(ds, model_name=MODEL_NAME, run_label=RUN_LABEL, run_id=run_id)
    print("Run id:", paths["run_id"])
    print("Master images:", paths["master_images_folder"])
    print("Raw CSV:", paths["raw_results_csv"])
    print("Ollama endpoint:", OLLAMA_BASE_URL, "| model:", OLLAMA_MODEL)
    print("Ollama num_ctx cap:", OLLAMA_NUM_CTX)

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
    model_config = {
        "name": MODEL_NAME,
        "id": OLLAMA_MODEL,
        "extra": {"options": {"num_ctx": OLLAMA_NUM_CTX}},
    }

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
