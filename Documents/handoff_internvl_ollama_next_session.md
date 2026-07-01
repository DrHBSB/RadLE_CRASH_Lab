# InternVL3.5-8B via Ollama — next-session handoff (lean)

Read the actual files fresh; this is a pointer, not a summary to trust blindly.
Written 2026-07-02 by Claude/Opus 4.8 right after OctoMed-7B went through the same
recipe cleanly. InternVL is the third open medical VLM through the Ollama path
(LLaVA-Med done, OctoMed done/underway, InternVL next).

## Goal
Serve **InternVL3.5-8B** through the RadLE medical Workbench benchmark via **Ollama**
(same pattern proven on LLaVA-Med and OctoMed), producing an auditable, promotable
model-scoped full run — WITHOUT changing the shared RadLE prompt or image payload
(manuscript parity is absolute).

## Primary plan + reusable recipe (READ FIRST)
`Documents/execplan_medical_vlm_ollama_runtime.md` — the working approach and the
reusable **"Recipe: add a NEW open medical VLM"** section (now includes the
reasoning-model `<think>`-strip step, added for OctoMed). InternVL follows that
recipe step by step. LLaVA-Med and OctoMed are the reference implementations.

`Documents/execplan_internvl_runtime.md` is the RETIRED InternVL **vLLM** attempt
(stuck on a partial `flash_attn.ops.triton.rotary` install, commit `16f6628`). Read
only for InternVL model facts. Do NOT reopen the vLLM route — the Ollama GGUF path
is the decided route for all open VLMs now.

## Workflow (unchanged)
Claude edits `scripts/*.py` + `src/*.py` on branch `codex/llava-vllm-runtime`,
commits, pushes. User runs on the Workbench VM (Ollama at :11434/v1, VM
`medical-master-radfm`, project `crashlab-synthetic`) and pastes outputs. CLI here
can't run the VM.

## First risk ALREADY RESOLVED: GGUF + mmproj exist
Both `mradermacher/InternVL3_5-8B-GGUF` and
`bartowski/OpenGVLab_InternVL3_5-8B-GGUF` ship the vision projector. Use the
mradermacher q8 build for parity with OctoMed/LLaVA (q8):
- LM: `InternVL3_5-8B` Q8_0 (8.71 GB) + `InternVL3_5-8B.mmproj-Q8_0.gguf` (365 MB).
- **Ollama tag: `hf.co/mradermacher/InternVL3_5-8B-GGUF:Q8_0`** (pull auto-detects mmproj).
- Fits with room on an L4 (23 GB); OctoMed/LLaVA both ran on the idle GPU.

**But mmproj-present is NOT proof it works.** InternVL's vision projector arch
differs from Qwen2.5-VL (OctoMed). Ollama's bundled llama.cpp must actually support
the InternVL3.5 vision tower. This is THE risk to clear first — prove image
conditioning on the VM before touching integration. If the probe returns
empty/identical/degenerate outputs across different images, Ollama's build doesn't
support this vision arch yet → raise it with the user (do not force it).

## First actions (the recipe, applied to InternVL)
1. **Prove image conditioning.** The probe is already generic — no new script:
   ```
   ollama pull hf.co/mradermacher/InternVL3_5-8B-GGUF:Q8_0
   PROBE_MAX_TOKENS=1024 python scripts/ollama_llava_med_probe.py \
       hf.co/mradermacher/InternVL3_5-8B-GGUF:Q8_0 1 8 78 12 45
   ```
   GO = different, image-specific outputs across cases 1/8/78. Degenerate = stop.
2. **Characterize format** on the shakedown: does it emit RadLE JSON
   `{diagnosis, likert_score}` like OctoMed, or prose like LLaVA-Med?
   **InternVL3.5 has a "thinking" mode and may emit `<think>...</think>`.** The
   trace-strip is ALREADY LIVE in `extract_json_safely` (commit 5ae5e51) and is
   inert if it doesn't. If it emits clean JSON after the trace like OctoMed, you're
   in the easy path; if prose-only, lean on the conservative prose failsafe.
3. **Run via a copy of `scripts/run_octomed_ollama.py`** → `run_internvl_ollama.py`.
   4-line diff:
   ```
   OLLAMA_MODEL = os.environ.get("OLLAMA_INTERNVL_MODEL",
       "hf.co/mradermacher/InternVL3_5-8B-GGUF:Q8_0")
   MODEL_NAME = "internvl3_5_8b"
   RUN_LABEL  = "medical_full_200_cases_ollama"
   # run_id auto-derives -> internvl3_5_8b_medical_full_200_cases_ollama
   ```
   Keep `MAX_OUTPUT_TOKENS=8192` (safe if it reasons), temp at
   `UNIVERSAL_TEMPERATURE=0.01` (parity, NOT any card-recommended sampling), and the
   RadLE prompt/payload identical. Shakedown `--limit=8` first, then the full 200.
4. **Audit → adjudicate → promote → export** under the standard guardrails.

## InternVL model facts (from the retired vLLM plan)
- Model repo `OpenGVLab/InternVL3_5-8B`; ungated (no HF token needed).
- Stable model name `internvl3_5_8b`; run id (Ollama) `internvl3_5_8b_medical_full_200_cases_ollama`.
- Same dataset contract: 200 grouped cases / 263 image files; case `156` is the only
  5-image case. The run script's EXPECTED_CASES/EXPECTED_IMAGES guard enforces this.
- The vLLM route died on FlashAttention, not on the model — irrelevant to Ollama,
  which uses its own llama.cpp runtime (no torch/vLLM/flash-attn dependency).

## Reusable assets proven on LLaVA-Med + OctoMed (apply directly)
- **`extract_json_safely`** (commit 5ae5e51): `<think>`-strip → JSON → numbered-VQA →
  conservative committed-prose, with an abstention/negation guard. Shared across
  models; guarded so non-reasoning outputs are byte-identical.
- **Adjudication sidecar** pattern (`scripts/radle_*_adjudication.json` + backup →
  verify `from` → set `to`) recovers mis-extractions from the model's OWN text. Do
  NOT tune extractor triggers against the eval set.
- **Promote-with-override** only if needed: if a model emits no Likert / only
  genuine no-answers, the audit buckets everything as repair targets and promotion
  is an explicit documented override. OctoMed emits Likert, so it likely won't need
  this; check InternVL's output first.
- **Get outputs off the VM via the GCS relay** (OS Login SSH/SCP is BLOCKED for the
  Gmail account): on VM `gsutil cp <tar> gs://radle-medical-data-toronto/transfers/`,
  then locally `gcloud storage cp` it down. Zone `northamerica-northeast2-b`.

## OPEN ISSUE (verify before trusting stats)
The public export summary mis-buckets a prose-only, no-Likert model (LLaVA-Med came
out valid_rate=0.0 AND abstention_rate=0.0). Real scoring is in
`scripts/radle_v2_stats.py` + `scripts/radle_llm_judge.py` against ground truth.
Before reporting InternVL numbers, verify that pipeline counts a committed diagnosis
as an attempt and a no-answer as an abstention independent of Likert. If InternVL
emits Likert like OctoMed, it likely dodges this bug — but confirm, don't assume.

## Do not
Reopen vLLM for InternVL; change the RadLE prompt or add per-model prompt/token/
sampling hacks (parity is absolute); make the prose failsafe aggressive; use
best-of-N / retries to inflate the answer rate; promote with unresolved integrity
problems unless the user explicitly overrides (and then document it in the manifest).
