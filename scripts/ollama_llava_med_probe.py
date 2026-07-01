#!/usr/bin/env python3
"""Image-conditioning probe for LLaVA-Med served via Ollama.

The HF checkpoint chaoyinshe/llava-med-v1.5-mistral-7b-hf was proven broken:
native transformers emits pure newlines regardless of the image. This probe
tests whether the Ollama GGUF build (default z-uo/llava-med-v1.5-mistral-7b_q8_0)
actually reads images, using the SAME OpenAI-style base64 payload the benchmark
sends, on two visually different real cases.

Setup on the VM (once):
    curl -fsSL https://ollama.com/install.sh | sh
    ollama pull z-uo/llava-med-v1.5-mistral-7b_q8_0
    # ollama serves an OpenAI-compatible endpoint at http://localhost:11434/v1

Run:
    python scripts/ollama_llava_med_probe.py
    python scripts/ollama_llava_med_probe.py <model_tag> 1 8 23

Interpretation:
  * Real, DIFFERENT diagnoses per image -> GGUF reads images; wire Ollama into
    the benchmark (point BASE_URL at http://localhost:11434/v1).
  * Empty / identical / degenerate -> this GGUF is broken too; the LLaVA-Med
    weights do not survive conversion in this environment.
"""
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import radle_benchmark  # noqa: E402

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
DEFAULT_MODEL = "z-uo/llava-med-v1.5-mistral-7b_q8_0"
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
    case_ids = args or ["1", "8"]

    folder = find_master_images()
    print("Master images folder:", folder)
    print("Ollama endpoint:", OLLAMA_BASE_URL)
    print("Model:", model)
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
        print("  -> empty or IDENTICAL across different images: this GGUF is also BROKEN.")
    elif distinct:
        print("  -> outputs DIFFER per image: GGUF reads images -> wire Ollama into the benchmark.")
    print("done")


if __name__ == "__main__":
    main()
