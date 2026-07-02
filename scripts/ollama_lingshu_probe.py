#!/usr/bin/env python3
"""Image-conditioning probe for Lingshu-32B served via Ollama.

Lingshu-32B is built on Qwen2.5-VL-32B-Instruct -- the same base architecture
as OctoMed-7B (Qwen2.5-VL-7B), which already proved the Ollama GGUF+mmproj
path works cleanly for this vision tower. That lowers image-conditioning risk
relative to InternVL (a genuinely new architecture), but this probe still has
to pass before any full run -- never trust a green server.

THE REAL RISK for this model is VRAM/placement, not vision conditioning: a 32B
model at Q8 is roughly 32 GB for the LM alone plus a (32B-scale) mmproj file
plus KV cache, call it 35-40 GB. The VM has 2x NVIDIA L4 (23 GB each, 46 GB
combined). Do NOT drop to a lower quant just because it doesn't fit on ONE
GPU -- Ollama/llama.cpp can split layers across both L4s automatically. Watch
`nvidia-smi` (a second terminal, `watch -n 2 nvidia-smi`) while this probe's
first request loads the model, and confirm memory is actually used on BOTH
GPU0 and GPU1 before concluding anything about fit.

Setup on the VM (once):
    cd ~/RadLE_CRASH_Lab && git pull
    ollama pull hf.co/mradermacher/Lingshu-32B-GGUF:Q8_0
    # ollama serves an OpenAI-compatible endpoint at http://localhost:11434/v1

Run (default cases mirror the InternVL/OctoMed probe set):
    python scripts/ollama_lingshu_probe.py
    python scripts/ollama_lingshu_probe.py <model_tag> 1 8 78 12 45

If Lingshu turns out to reason before answering (like OctoMed's <think>
trace), raise the token budget so the trace doesn't eat the whole probe:
    PROBE_MAX_TOKENS=1024 python scripts/ollama_lingshu_probe.py

Interpretation:
  * Real, DIFFERENT diagnoses per image -> vision path works; proceed to the
    VRAM/split check (if not already confirmed) and then the shakedown run.
  * Empty / identical / degenerate -> do not proceed; treat like the LLaVA-Med
    HF-checkpoint failure and investigate before any full run.
"""
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import radle_benchmark  # noqa: E402

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
DEFAULT_MODEL = os.environ.get(
    "OLLAMA_LINGSHU_MODEL", "hf.co/mradermacher/Lingshu-32B-GGUF:Q8_0"
)
# Reasoning models (e.g. OctoMed emits <think>...</think>) can spend the whole
# budget on the trace before the final answer -- raise PROBE_MAX_TOKENS for those.
PROBE_MAX_TOKENS = int(os.environ.get("PROBE_MAX_TOKENS", "256"))


def find_master_images():
    root = os.environ.get("RADLE_LOCAL_DATASET_ROOT") or str(
        pathlib.Path.home() / "radle_dataset" / "RadLE v2 Dataset"
    )
    folder = pathlib.Path(root) / "RadLE v2 Master Data"
    if folder.exists():
        return folder
    for cand in pathlib.Path.home().rglob("RadLE v2 Master Data"):
        return cand
    raise SystemExit("Could not locate 'RadLE v2 Master Data'. Set RADLE_LOCAL_DATASET_ROOT.")


def main():
    args = sys.argv[1:]
    model = DEFAULT_MODEL
    if args and not args[0].isdigit():
        model = args.pop(0)
    case_ids = args or ["1", "8", "78", "12", "45"]

    folder = find_master_images()
    print("Master images folder:", folder)
    print("Ollama endpoint:", OLLAMA_BASE_URL)
    print("Model:", model)
    print("Watch nvidia-smi in another terminal NOW -- the first request below")
    print("triggers the model load and is the real VRAM/multi-GPU-split test.")
    idx = radle_benchmark.build_image_index(str(folder))

    from openai import OpenAI

    client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

    outputs = {}
    for cid in case_ids:
        paths = idx.get(str(cid), [])
        if not paths:
            print(f"case {cid}: NO IMAGES FOUND")
            continue
        # Same payload shape the benchmark uses: text prompt + base64 image_url blocks.
        content = radle_benchmark.build_content_array(str(cid), idx, prompt=radle_benchmark.PROMPT)
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                temperature=radle_benchmark.UNIVERSAL_TEMPERATURE,
                max_tokens=PROBE_MAX_TOKENS,
            )
        except Exception as exc:  # noqa: BLE001
            print("=" * 70)
            print(f"CASE {cid}: request RAISED {type(exc).__name__}: {exc}")
            continue
        raw = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        outputs[cid] = raw.strip()
        ws = sum(raw.count(c) for c in [" ", "\n", "\r", "\t"])
        print("=" * 70)
        print(f"CASE {cid} | images={[pathlib.Path(p).name for p in paths]}")
        print("  finish_reason:", getattr(resp.choices[0], "finish_reason", None))
        print("  prompt_tokens:", getattr(usage, "prompt_tokens", None),
              "completion_tokens:", getattr(usage, "completion_tokens", None))
        print(f"  char_len={len(raw)} whitespace={ws} non_ws={len(raw) - ws}")
        print("  OUTPUT repr:", repr(raw[:800]))
        diag, likert = radle_benchmark.extract_json_safely(raw)
        print("  parsed diagnosis:", repr(diag), "| likert:", repr(likert))

    print("=" * 70)
    distinct = set(v for v in outputs.values() if v)
    print("VERDICT INPUTS:")
    print("  cases probed:", list(outputs.keys()))
    print("  distinct non-empty outputs:", len(distinct))
    if len(outputs) >= 2 and len(distinct) <= 1:
        print("  -> empty or IDENTICAL across different images: vision path is BROKEN.")
    elif distinct:
        print("  -> outputs DIFFER per image: vision path works -> proceed to shakedown.")
    print("done")


if __name__ == "__main__":
    main()
