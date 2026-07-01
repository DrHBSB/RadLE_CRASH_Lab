#!/usr/bin/env python3
"""Native-transformers probe for chaoyinshe/llava-med-v1.5-mistral-7b-hf.

Purpose: answer ONE question with zero vLLM / custom-template / logit_bias
variables -- does this HF checkpoint do real image-conditioned generation?

It loads the checkpoint through plain `LlavaForConditionalGeneration` +
`AutoProcessor` (the checkpoint's OWN processor and chat template), runs GREEDY
decode with NO constraints on two visually different real RadLE cases, and
prints the raw output for each.

Interpretation:
  * Real, DIFFERENT diagnoses per image -> the checkpoint works; our vLLM
    serving/template is the bug.
  * Empty / newline flood / identical-constant output -> the HF conversion's
    image pathway is broken; switch model or serving source.

Runs on GPU1 by default (idle per nvidia-smi) so it does not disturb the vLLM
server on GPU0. Override with CUDA_VISIBLE_DEVICES.

Usage:
    python scripts/llava_med_hf_probe.py            # cases 1 and 8
    python scripts/llava_med_hf_probe.py 1 8 23     # explicit case IDs
"""
import os
import pathlib
import sys

# Pin to the idle GPU BEFORE importing torch so the running vLLM server (GPU0)
# is untouched. Override by exporting CUDA_VISIBLE_DEVICES yourself.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "1")

import torch  # noqa: E402
from PIL import Image  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import radle_benchmark  # noqa: E402

MODEL_ID = "chaoyinshe/llava-med-v1.5-mistral-7b-hf"


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
    folder = find_master_images()
    print("Master images folder:", folder)
    idx = radle_benchmark.build_image_index(str(folder))
    case_ids = sys.argv[1:] or ["1", "8"]

    from transformers import AutoProcessor, LlavaForConditionalGeneration
    import transformers

    print("transformers version:", transformers.__version__)
    print("torch cuda available:", torch.cuda.is_available(),
          "| visible devices:", os.environ.get("CUDA_VISIBLE_DEVICES"))
    print("Loading processor + model from cache (no download if already present)...")
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    # No device_map (that path needs `accelerate`); load then move to CUDA.
    # CUDA_VISIBLE_DEVICES pins us to the idle GPU, so cuda:0 == physical GPU1.
    model = LlavaForConditionalGeneration.from_pretrained(
        MODEL_ID, torch_dtype=torch.float16
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    model.eval()
    has_ct = getattr(processor, "chat_template", None) is not None
    print("processor chat_template present:", has_ct)
    print("image_token_index:", getattr(model.config, "image_token_index", "?"))

    outputs = {}
    for cid in case_ids:
        paths = idx.get(str(cid), [])
        if not paths:
            print(f"case {cid}: NO IMAGES FOUND")
            continue
        img = Image.open(paths[0]).convert("RGB")

        template_mode = "chat_template"
        try:
            conv = [{
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": radle_benchmark.PROMPT},
                ],
            }]
            text = processor.apply_chat_template(conv, add_generation_prompt=True)
        except Exception as exc:  # noqa: BLE001
            template_mode = f"manual (apply_chat_template failed: {type(exc).__name__})"
            text = "[INST] <image>\n" + radle_benchmark.PROMPT + " [/INST]"

        inputs = processor(images=img, text=text, return_tensors="pt").to(model.device)
        if "pixel_values" in inputs:
            inputs["pixel_values"] = inputs["pixel_values"].to(torch.float16)
        n_in = inputs["input_ids"].shape[1]

        print("=" * 70)
        print(f"CASE {cid} | image={pathlib.Path(paths[0]).name} | template={template_mode}")
        print(f"  input_tokens={n_in}")

        # Pass 1: natural greedy (the model's own choice -> we already saw immediate EOS).
        with torch.no_grad():
            out_nat = model.generate(**inputs, max_new_tokens=256, do_sample=False)
        gen_nat = out_nat[0][n_in:]
        dec_nat = processor.decode(gen_nat, skip_special_tokens=True)
        print(f"  [natural]     gen_tokens={gen_nat.shape[0]} repr={dec_nat[:400]!r}")

        # Pass 2: FORCED past the first-token EOS. This is the real image-conditioning
        # test: if forced content differs between case 1 and case 8 it reads images.
        with torch.no_grad():
            out_forced = model.generate(
                **inputs, max_new_tokens=256, min_new_tokens=64, do_sample=False
            )
        gen_forced = out_forced[0][n_in:]
        dec_forced = processor.decode(gen_forced, skip_special_tokens=True)
        ws = sum(dec_forced.count(c) for c in [" ", "\n", "\r", "\t"])
        print(f"  [forced m64]  gen_tokens={gen_forced.shape[0]} "
              f"char_len={len(dec_forced)} whitespace={ws} non_ws={len(dec_forced) - ws}")
        print(f"                repr={dec_forced[:800]!r}")
        outputs[cid] = dec_forced.strip()

    print("=" * 70)
    distinct = set(v.strip() for v in outputs.values() if v.strip())
    print("VERDICT INPUTS:")
    print("  cases probed:", list(outputs.keys()))
    print("  distinct non-empty outputs:", len(distinct))
    if len(outputs) >= 2 and len(distinct) <= 1:
        print("  -> outputs are empty or IDENTICAL across different images:"
              " image conditioning looks BROKEN.")
    elif distinct:
        print("  -> outputs differ per image: image conditioning WORKS natively;"
              " the vLLM serving/template is the problem.")
    print("done")


if __name__ == "__main__":
    main()
