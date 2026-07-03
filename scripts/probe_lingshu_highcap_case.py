#!/usr/bin/env python3
"""Diagnostic: re-query ONE Lingshu case at a raised max_output_tokens.

Purpose: case 119 spiraled at the 1024 cap -- it emits JSON after JSON with a
likert counter that ratchets upward, and 1024 truncated it on an out-of-range
value (10, then 8 on repair). This probe asks the ONLY parity-safe question:
given a much larger generation budget, does the model self-TERMINATE
(finish_reason=stop) with a genuine final JSON whose likert is in-range 0-4 --
or does it just keep spiraling until it hits the bigger cap too?

EVERYTHING except max_output_tokens is byte-identical to the run: same
build_content_array payload, same PROMPT, same UNIVERSAL_TEMPERATURE (0.01),
same num_ctx=8192. max_output_tokens is the already-declared per-model RESOURCE
cap (not a parity param), so raising it for this diagnostic changes nothing that
affects manuscript parity.

Read the verdict:
  * finish_reason=stop AND parsed likert in 0-4  -> the model DOES converge to a
    valid final answer when not truncated; a uniform rerun of all 200 at this
    budget is justified (consistent budget, no per-cell special-casing).
  * finish_reason=length (hit the cap) OR parsed likert still out-of-range
    -> the spiral does not self-terminate; a bigger budget does not recover a
    valid likert. Do NOT rerun; case 119's likert is genuinely absent.

Usage:
    python scripts/probe_lingshu_highcap_case.py                 # case 119 @ 8192
    python scripts/probe_lingshu_highcap_case.py 119 8192
    python scripts/probe_lingshu_highcap_case.py 119 16384
"""
import os
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import radle_benchmark as rb  # noqa: E402

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_LINGSHU_MODEL", "lingshu-32b-8k")
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "8192"))


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


def show_long(raw):
    """Print head + tail so the FINAL JSON (the take-last target) is visible."""
    if len(raw) <= 4000:
        print(repr(raw))
        return
    print("HEAD 1200:", repr(raw[:1200]))
    print(f"...[{len(raw) - 3200} chars omitted]...")
    print("TAIL 2000:", repr(raw[-2000:]))


def main():
    args = sys.argv[1:]
    case_id = args[0] if len(args) >= 1 else "119"
    max_tokens = int(args[1]) if len(args) >= 2 else 8192

    folder = find_master_images()
    idx = rb.build_image_index(str(folder))
    paths = idx.get(str(case_id), [])
    if not paths:
        raise SystemExit(f"case {case_id}: NO IMAGES FOUND")

    print("Master images folder:", folder)
    print("Model:", OLLAMA_MODEL, "| num_ctx:", OLLAMA_NUM_CTX)
    print(f"Case {case_id} | images={[pathlib.Path(p).name for p in paths]}")
    print(f"max_output_tokens (raised diagnostic budget): {max_tokens}")

    from openai import OpenAI

    client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    content = rb.build_content_array(str(case_id), idx, prompt=rb.PROMPT)
    resp = client.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": content}],
        temperature=rb.UNIVERSAL_TEMPERATURE,
        max_tokens=max_tokens,
        extra_body={"options": {"num_ctx": OLLAMA_NUM_CTX}},
    )
    raw = resp.choices[0].message.content or ""
    usage = getattr(resp, "usage", None)
    finish = getattr(resp.choices[0], "finish_reason", None)

    # Characterize the spiral: how many JSON objects, and the likert in each.
    json_objs = re.findall(r"\{[^{}]*\}", raw, flags=re.DOTALL)
    likerts = re.findall(r'"likert_score"\s*:\s*(null|None|-?\d+)', raw, flags=re.IGNORECASE)

    print("=" * 70)
    print("finish_reason:", finish)
    print("prompt_tokens:", getattr(usage, "prompt_tokens", None),
          "completion_tokens:", getattr(usage, "completion_tokens", None))
    print("char_len:", len(raw))
    print("JSON objects in response:", len(json_objs))
    print("likert values in order:", likerts)
    print("-" * 70)
    show_long(raw)
    print("-" * 70)

    diag, likert = rb.extract_json_safely(raw)
    print("take-last extraction -> diagnosis:", repr(diag), "| likert:", repr(likert))
    valid_likert = rb.is_valid_likert_value(likert)

    print("=" * 70)
    print("VERDICT:")
    if finish == "stop" and valid_likert:
        print("  SELF-TERMINATED with a valid in-range likert -> a uniform rerun of")
        print("  all 200 at this budget is justified (no per-cell special-casing).")
    elif finish == "stop" and not valid_likert:
        print("  Terminated on its own but the final likert is STILL out of range")
        print("  -> a bigger budget does not recover a valid likert. Do NOT rerun.")
    else:
        print(f"  Hit the cap (finish_reason={finish!r}) -> the spiral does NOT")
        print("  self-terminate; a bigger budget just truncates higher. Do NOT rerun.")


if __name__ == "__main__":
    main()
