# LLaVA-Med — next-session handoff (lean)

Read the actual files fresh; this is a pointer, not a summary to trust blindly.

## Primary plan (READ FIRST)
`Documents/execplan_medical_vlm_ollama_runtime.md` — the current, working approach:
serve open medical VLMs for RadLE via Ollama; LLaVA-Med first. It has Current State,
Locked Facts, Do Not Revisit, and a reusable "add a new model" recipe.

`Documents/execplan_llava_vllm_runtime.md` is the RETIRED vLLM/HF rollercoaster.
Read it only for the evidence that the HF checkpoint is dead — do NOT reopen that route.

## Workflow (2026-07-01)
- Claude edits `src/*.py` + `scripts/*.py` on branch `codex/llava-vllm-runtime`, commits, pushes.
- User runs on the Workbench VM (GCP Jupyter) and pastes outputs. CLI here can't run the VM.
- Claude can also drive the VM's JupyterLab via the Claude-in-Chrome extension (Browser 1);
  user logs in, Claude opens a NEW terminal (don't touch the user's terminals). Prefer having
  the user run long/critical commands (xterm typing can inject stray escape sequences).

## Where things stand
- HF checkpoint `chaoyinshe/llava-med-v1.5-mistral-7b-hf` is DEAD (does not read images; proven
  by native transformers in `scripts/llava_med_hf_probe.py`). vLLM route abandoned.
- Ollama GGUF `z-uo/llava-med-v1.5-mistral-7b_q8_0` READS images (proven by
  `scripts/ollama_llava_med_probe.py`). Installed + pulled on the VM; serves at :11434/v1.
- Behavior: reads images but usually DESCRIBES rather than diagnoses (~1/8 commit), never JSON.
  Prompt is LOCKED (manuscript parity). A conservative committed-prose failsafe was added to
  `radle_benchmark.extract_json_safely` (never fabricates from descriptions; unit-tested).
- `scripts/run_llava_med_ollama.py` runs the standard benchmark through Ollama and writes the
  normal run CSV (run label `medical_full_200_cases_ollama`); prints a diagnosis-rate summary.

## First action
On the VM: `cd ~/RadLE_CRASH_Lab && git pull`, then
`python scripts/run_llava_med_ollama.py --limit=5` (shakedown), then the full
`python scripts/run_llava_med_ollama.py`. Paste the diagnosis-rate summary. Then audit ->
decide no-diagnosis scoring (abstention vs repair) WITH the user -> repair/promote/export
under Workbench guardrails. Expect many PARSE_FAILED (no-diagnosis) rows — genuine behavior.

## Do not
Reopen vLLM/HF for LLaVA-Med; add per-model prompt variants or token hacks; make the prose
failsafe aggressive; promote with pending repairs unless the user overrides.
