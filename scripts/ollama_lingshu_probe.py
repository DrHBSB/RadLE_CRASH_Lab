#!/usr/bin/env python3
"""Image-conditioning probe for Lingshu-32B served via Ollama.

Lingshu-32B is built on Qwen2.5-VL-32B-Instruct -- the same base architecture
as OctoMed-7B (Qwen2.5-VL-7B), which already proved the Ollama GGUF+mmproj
path works cleanly for this vision tower. That lowers image-conditioning risk
relative to InternVL (a genuinely new architecture), but this probe still has
to pass before any full run -- never trust a green server.

CURRENT BOX = single A100-SXM4-40GB (radle-pro-a100-*). Lingshu Q8 (~34 GB LM
+ mmproj + KV cache at num_ctx=8192) fits on the ONE GPU with a few GB to
spare. Pass criterion here: watch `nvidia-smi` while this probe's first request
loads the model and confirm ~37 GB on the single A100 with NO OOM -- there is NO
multi-GPU split to look for on this box (that was the retired 2x L4). If it OOMs
near 40 GB, lower num_ctx slightly (rebuild the Modelfile) rather than dropping
quant. HISTORICAL: on the retired 2x L4 (23 GB each) Q8 fit only by splitting
across both cards over PCIe (~6 tok/s); the A100's single-GPU placement is why
we migrated.

Setup on the VM (once):
    cd ~/RadLE_CRASH_Lab && git pull
    ollama pull hf.co/mradermacher/Lingshu-32B-GGUF:Q8_0
    # Bake the context cap into a derived model -- the OpenAI endpoint ignores
    # extra_body num_ctx, so this Modelfile is the ONLY thing that caps context:
    printf 'FROM hf.co/mradermacher/Lingshu-32B-GGUF:Q8_0\nPARAMETER num_ctx 8192\n' > /tmp/Lingshu8k.Modelfile
    ollama create lingshu-32b-8k -f /tmp/Lingshu8k.Modelfile
    # ollama serves an OpenAI-compatible endpoint at http://localhost:11434/v1

The context cap is mandatory regardless of box: with the raw tag's default 32768
context the vision (CLIP) compute buffer OOMs. The Modelfile-derived
`lingshu-32b-8k` (num_ctx=8192, matching vLLM's MAX_MODEL_LEN=8192 proven for
OctoMed/InternVL) is what loads cleanly. (First proven on the 2x L4 box
2026-07-02; the single A100 has more headroom.)

Run (default cases mirror the InternVL/OctoMed probe set):
    python scripts/ollama_lingshu_probe.py
    python scripts/ollama_lingshu_probe.py <model_tag> 1 8 78 12 45

If Lingshu turns out to reason before answering (like OctoMed's <think>
trace), raise the token budget so the trace doesn't eat the whole probe:
    PROBE_MAX_TOKENS=1024 python scripts/ollama_lingshu_probe.py

Interpretation:
  * Real, DIFFERENT diagnoses per image -> vision path works; confirm the
    single-A100 fit (~37 GB, no OOM) and proceed to the shakedown run.
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
# Default to the Modelfile-derived model with num_ctx=8192 baked in. The raw
# GGUF tag loads at 32768 context and OOMs on the first image (the OpenAI
# endpoint ignores extra_body num_ctx). Create it once (see module docstring).
DEFAULT_MODEL = os.environ.get("OLLAMA_LINGSHU_MODEL", "lingshu-32b-8k")
# Reasoning models (e.g. OctoMed emits <think>...</think>) can spend the whole
# budget on the trace before the final answer -- raise PROBE_MAX_TOKENS for those.
PROBE_MAX_TOKENS = int(os.environ.get("PROBE_MAX_TOKENS", "256"))
# Caps Ollama's context window (same role as vLLM's MAX_MODEL_LEN=8192) so KV
# cache doesn't eat the VRAM headroom needed for a 200-case run.
PROBE_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "8192"))


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
    print("num_ctx cap:", PROBE_NUM_CTX)
    print("Watch nvidia-smi in another terminal NOW -- the first request below")
    print("triggers the model load; on the A100 expect ~37 GB on the one GPU, no OOM.")
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
                extra_body={"options": {"num_ctx": PROBE_NUM_CTX}},
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
