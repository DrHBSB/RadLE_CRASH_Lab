# OctoMed via Ollama — next-session handoff (lean)

Read the actual files fresh; this is a pointer, not a summary to trust blindly.

## Goal
Serve **OctoMed-7B** through the RadLE medical Workbench benchmark via **Ollama**
(same pattern that worked for LLaVA-Med), producing an auditable, promotable
model-scoped full run — WITHOUT changing the shared RadLE prompt or image payload
(manuscript parity is absolute).

## Primary plan + reusable recipe (READ FIRST)
`Documents/execplan_medical_vlm_ollama_runtime.md` — the working approach and the
reusable **"Recipe: add a NEW open medical VLM"** section. OctoMed follows that
recipe step by step. The LLaVA-Med run under that plan is DONE (16/200 committed,
184 genuine abstentions) and is the reference implementation.

`Documents/execplan_octomed_runtime.md` is the RETIRED OctoMed **vLLM** rollercoaster
(stuck on the `llguidance` dependency). Read only for OctoMed's model facts
(Qwen2.5-VL, 200 cases / 263 images, case 156 = only 5-image case). Do NOT reopen
the vLLM route.

## Workflow (unchanged from LLaVA-Med)
- Claude edits `scripts/*.py` + `src/*.py` on branch `codex/llava-vllm-runtime`,
  commits, pushes. User runs on the Workbench VM (Ollama at :11434/v1) and pastes
  outputs. CLI here can't run the VM.

## First actions (the recipe, applied to OctoMed)
1. **Find/pull an OctoMed GGUF for Ollama — UNKNOWN IF ONE EXISTS.** This is the
   first real risk. Search Ollama/HF for an OctoMed-7B GGUF; if none exists, that's
   a blocker to raise with the user (converting to GGUF yourself is out of scope
   unless the user asks). Do not assume it exists.
2. **Prove image conditioning BEFORE integration.** Adapt
   `scripts/ollama_llava_med_probe.py` — two visually different real cases through
   the exact `build_content_array` payload; outputs must differ per image. A green
   endpoint is not proof.
3. **Characterize output** on ~6–8 cases: JSON? commits vs describes? boilerplate?
4. **Run via a copy of `scripts/run_llava_med_ollama.py`** → `run_octomed_ollama.py`:
   change `MODEL_NAME="octomed_7b"`, `RUN_LABEL`, `run_id`, and the Ollama model
   tag. Keep the RadLE prompt/payload identical.
5. **Audit → adjudicate → promote → export** under the guardrails below.

## Reusable assets proven on LLaVA-Med (apply directly to OctoMed)
- **Prose failsafe + abstention guard** already live in
  `radle_benchmark.extract_json_safely` (commit 5b7422f): JSON → numbered-VQA →
  conservative committed-prose, with a negation/abstention guard so
  "diagnosis is not provided" is NOT returned as a diagnosis. Shared across models.
- **Adjudication sidecar** pattern: `scripts/radle_llava_med_adjudication.json` +
  the apply snippet (backup → verify `from` → set `to`) recovers mis-extractions
  from the model's OWN text. Do NOT tune extractor triggers against the eval set.
- **Promote-with-override**: `rb.promote_final_results(..., metadata={...override
  rationale...})`. If the model emits no Likert / genuine no-answers, the audit
  buckets everything as `paid_repair`/`needs_api_repair`; promotion is an explicit,
  documented override because those "repair targets" are not repairable under parity.
- **Get outputs off the VM**: OS Login SSH/SCP is BLOCKED for the Gmail account on
  this external org. Use the GCS relay: on VM `gsutil cp <tar> gs://
  radle-medical-data-toronto/transfers/`, then locally `gcloud storage cp` it down.
  VM = `medical-master-radfm`, zone `northamerica-northeast2-b`, project
  `crashlab-synthetic`. Buckets visible locally: `radle-medical-data-toronto`,
  `radle-benchmark-images`.

## OPEN ISSUE that will bite OctoMed too (fix before trusting stats)
The public export summary mis-buckets a prose-only, no-Likert model: LLaVA-Med
came out `valid_response_rate=0.0` AND `abstention_rate=0.0` (should be ~0.08 valid,
~0.92 abstention) because the classifier keys "valid" off a non-null Likert 0–4,
which these models never emit. Real scoring happens in `scripts/radle_v2_stats.py`
+ `scripts/radle_llm_judge.py` against ground truth. Before reporting OctoMed (or
LLaVA-Med) numbers, verify that pipeline counts a committed prose diagnosis as an
attempt and a no-answer as an abstention, independent of Likert. Not yet fixed.

## Do not
Reopen vLLM for OctoMed; change the RadLE prompt or add per-model prompt/token
hacks; make the prose failsafe aggressive; best-of-N / retry to inflate the answer
rate (proven a dead end for LLaVA-Med — deterministic empties, parity-locked
levers); promote with unresolved integrity problems (repair-target override is OK
and expected for these no-Likert models, but must be documented in the manifest).
