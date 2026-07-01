# Serve open medical VLMs for RadLE via Ollama (LLaVA-Med first)

This ExecPlan is a living document. Keep `Current State`, `Locked Facts`, `Do Not
Revisit`, `Progress`, `Surprises & Discoveries`, and `Decision Log` up to date as
work proceeds. It follows `~/.codex/PLANS.md`. The only repo `AGENTS.md` files are
under `vllm_0_23_0/`, so they do not apply here.

This plan supersedes the serving approach in `Documents/execplan_llava_vllm_runtime.md`
(the full vLLM/HF-checkpoint rollercoaster). Read that only for the historical
evidence that the HF checkpoint is dead; do not reopen the vLLM route.


## Purpose / Big Picture

Run open/self-hosted medical vision-language models through the same RadLE medical
Workbench benchmark used for the cloud models, producing a model-scoped full run
that can be audited, repaired, promoted, and released under the established
guardrails — WITHOUT changing the shared RadLE prompt or image payload (manuscript
parity is absolute).

The first such model is **LLaVA-Med v1.5 Mistral 7B**. Its HF-format checkpoint does
not work (see Locked Facts); it is now served via **Ollama** (a local
OpenAI-compatible GGUF endpoint). The same pattern generalizes to future open models.


## Workflow (how Claude and the user collaborate)

- **Claude** edits `src/*.py` and `scripts/*.py` in this local repo on branch
  `codex/llava-vllm-runtime`, commits, and pushes to `origin`.
- **User** runs commands on the Workbench VM (GCP Jupyter notebook, terminal) and
  pastes outputs back. The CLI here cannot run the VM.
- Claude can ALSO drive the VM's JupyterLab directly via the Claude-in-Chrome
  extension (Browser 1, local): the user logs into the GCP notebook in that tab,
  Claude opens a NEW terminal (do not touch the user's existing terminals). Typing
  into the xterm can inject stray escape sequences — prefer having the user run
  long/critical commands, and use the browser mainly to read outputs.
- The Codex-app + Antigravity GUI coordination play is DROPPED; ignore the
  GoalBuddy paired-goal docs under `docs/goals/llava-vllm-*`.


## Current State

Current state (2026-07-01, Claude/Opus 4.8): LLaVA-Med is served through Ollama and
proven to read images. The HF checkpoint route is dead. Two artifacts are pushed and
ready to run on the VM:
- `scripts/run_llava_med_ollama.py` — runs the standard RadLE benchmark through
  Ollama's OpenAI endpoint with the SAME prompt/payload, writes the normal run CSV
  (run label `medical_full_200_cases_ollama`), and prints a diagnosis-recovery
  summary. Registry and the dead vLLM notebook are untouched (inline model config).
- Conservative prose-diagnosis failsafe in `radle_benchmark.extract_json_safely`
  (JSON -> numbered-VQA -> committed-prose), unit-tested so it recovers real
  diagnoses (e.g. "presence of pulmonary embolism") but never fabricates from a
  modality description or a possibility list.

Known behavior from an 8-case probe: LLaVA-Med reads images but usually DESCRIBES
the modality/anatomy rather than giving a diagnosis; only ~1/8 commit to one, and it
never returns JSON. So expect many `PARSE_FAILED` (no-diagnosis) rows in the full
run — that is the model's genuine behavior, routed to the audit/repair path, not a
bug and not to be forced with prompt changes.

Next: user runs `--limit=5` shakedown then the full run, pastes the diagnosis-rate
summary, then audit -> repair -> promote. Open methodology question deferred to the
user after the numbers are in: how to score no-diagnosis cases (abstention vs repair).


## Locked Facts

- The RadLE prompt (`radle_benchmark.PROMPT`) and the OpenAI-style base64 image
  payload (`build_content_array`) are IDENTICAL for every model. Parity is absolute
  for the manuscript. Do not special-case prompts per model.
- The HF checkpoint `chaoyinshe/llava-med-v1.5-mistral-7b-hf` does NOT do
  image-conditioned generation. Proven by `scripts/llava_med_hf_probe.py`: native
  transformers with the checkpoint's own chat template emits immediate `</s>` on
  image input, and when forced past EOS it emits 256 pure newlines, byte-identical
  across two different images. Not a vLLM/template/token problem — the weights.
- The Ollama GGUF `z-uo/llava-med-v1.5-mistral-7b_q8_0` DOES read images. Proven by
  `scripts/ollama_llava_med_probe.py`: cases 1 vs 8 vs 78 give different,
  image-specific outputs; case 78 committed "presence of a pulmonary embolism".
- Ollama serves an OpenAI-compatible endpoint at `http://localhost:11434/v1`; it
  runs as a systemd service after install (no manual `ollama serve` needed) and
  auto-places the model on a GPU. It is 8-bit (q8) quantized — record this serving
  difference vs the vLLM-served models in the methods section.
- The benchmark request is built in `radle_benchmark.build_api_params` (default
  branch): `model=model["id"]`, base64 image content, `max_tokens`, `temperature`
  (UNIVERSAL_TEMPERATURE=0.01), and `extra_body=model["extra"]` if present. Passing
  an OpenAI client pointed at Ollama plus an inline model config
  `{"name": "llava_med_mistral_7b", "id": "z-uo/...q8_0", "extra": None}` runs the
  full pipeline unchanged (`get_api_client` returns the passed client for non-native
  models).
- Extraction lives in `radle_benchmark.extract_json_safely`: JSON, then a
  numbered-VQA fallback, then the conservative committed-prose fallback. The prose
  fallback only fires on explicit commitment and rejects modality/anatomy and
  possibility lists, so it never invents a diagnosis.
- Run outputs use `build_medical_run_paths(dataset_root, model_name, run_label,
  run_id)`; the run CSV schema is model-scoped (`Diagnosis_llava_med_mistral_7b`,
  etc.), so the existing audit/repair/promote/export code applies to the Ollama run.
- Two L4 GPUs on the VM (23 GB each). The retired vLLM server used GPU0 (~20 GB);
  Ollama and the native HF probe fit alongside on the idle GPU.


## Do Not Revisit

- Do not reopen the vLLM + HF-checkpoint route for LLaVA-Med. The checkpoint is
  broken; native transformers proved it. See Decision Log.
- Do not add per-model prompt variants, min_tokens/logit_bias/bad_words token
  hacks, or chat-template surgery to "fix" output. Those were band-aids on a broken
  checkpoint and/or would break manuscript parity.
- Do not make the prose failsafe aggressive. It must never extract a diagnosis from
  a modality description or a "can be used to diagnose ..." possibility list.
- Do not promote or sync a run while integrity problems or repair targets remain,
  unless the user explicitly overrides (Workbench guardrails).
- Do not add retries/best-of-N to raise LLaVA-Med's answer rate. Proven dead end:
  empty generations are deterministic and the fix-levers break parity (see Decision
  Log 2026-07-02). Retries recover transport failures (Morning), not this.


## Progress

- [x] (2026-07-01) Proved the HF checkpoint does not read images (native transformers
  probe); abandoned the vLLM route.
- [x] (2026-07-01) Pivoted to Ollama; proved `z-uo/llava-med-v1.5-mistral-7b_q8_0`
  reads images (two-image conditioning probe).
- [x] (2026-07-01) Characterized behavior (8 cases): describes > diagnoses, ~1/8
  commits, never JSON.
- [x] (2026-07-01) Built the conservative prose failsafe in `extract_json_safely`
  (unit-tested) and `scripts/run_llava_med_ollama.py` (standard benchmark via Ollama).
- [x] (2026-07-02) Ran the full 200-case run. Result: 18 raw commits / 182 no-answer.
  Re-extraction after the abstention fix -> **16 commits / 184 no-answer** (~8%).
- [x] (2026-07-02) Fixed an abstention leak in the prose failsafe (commit 5b7422f):
  cases 42, 53 had "diagnosis is not provided in this case" returned as a diagnosis.
  Negation/abstention guard added; re-extracted in place (no re-inference), 18->16.
- [x] (2026-07-02) Investigated retries (Morning-style) to recover no-answers.
  DEAD END: the 52 empty-generation cases are DETERMINISTICALLY empty (3x re-hits
  with the exact locked payload -> [0,0,0] chars every time), and parity forbids
  the only levers that would change them (temperature/prompt/image). Retries help
  transport failures (Morning), not this model's deterministic non-answers.
- [ ] (next) Adjudicate the 16 commits: recover 3 mis-extractions (43 bilateral
  optic nerve gliomas, 183 ovarian tumor, 196 pulmonary TB) from the model's own
  text; decide the 4 finding-only cases (65/97/108/151 "large mass in <location>").
- [x] (2026-07-02) Adjudicated the 16 commits: recovered 3 mis-extractions via the
  sidecar `scripts/radle_llava_med_adjudication.json` (43 bilateral optic nerve
  gliomas, 183 ovarian tumor, 196 pulmonary TB); user (radiologist) ruled the 4
  finding-only cases (65/97/108/151) COUNT as attempts. Final: 16/200 committed.
- [x] (2026-07-02) User decided the 184 no-answers = genuine abstentions; promoted
  with an explicit guardrail override (all 200 audit as `paid_repair` because
  LLaVA-Med emits no Likert self-confidence -- also unrepairable under parity).
  raw -> final (sha256 b6ebbba9...), public_release tables exported. Override
  rationale + 16/184 split + adjudication ref baked into the final manifest.
- [x] RUN COMPLETE. LLaVA-Med v1.5 Mistral 7B (Ollama q8): 16/200 committed
  diagnoses, 184 genuine abstentions (52 deterministic-empty + 132 descriptions),
  0 self-confidence scores. Reportable capability result; do not "improve" via
  retries/prompt changes (parity). Remaining: transfer outputs off the VM.


## Surprises & Discoveries

- The HF conversion's image pathway is silently broken: image tokens splice
  (prompt_tokens grows) and the server looks healthy, but the LM gets zero signal.
  A green server + spliced image tokens is NOT evidence of a working multimodal pass.
  Only a native forward pass on two different images (does output vary?) is decisive.
- Every earlier vLLM "diagnosis" (e.g. constant "Pulmonary tuberculosis") was the
  text prior surfaced by token-suppression, not image reading. Token hacks can
  manufacture plausible-but-fake output from a blind model.
- The Ollama GGUF of the same model works, so "LLaVA-Med" viability depends on the
  conversion/serving path, not the weights in the abstract.
- LLaVA-Med (VQA-tuned) tends to describe modality/anatomy rather than commit to a
  diagnosis under a long instruction prompt; sometimes returns byte-identical
  boilerplate for different images. This is a model-capability finding, reportable.
- The full-run no-answer set is bimodal: 52/184 are EMPTY generations (model emits
  EOS-first, `raw=nan`) and 132/184 are full descriptions with no committed
  diagnosis. The empties are deterministic (retries return [0,0,0] chars) even
  though non-empty cases vary run-to-run (case 5: 67->95 tokens across runs) -- so
  the empties are a hard EOS decision on those images, not sampling noise. Both
  classes are genuine model behavior; neither is a transport failure a retry fixes.
- The prose failsafe's first-trigger-wins can UNDERSELL the model: on 3 cases it
  grabbed a finding phrase over a diagnosis the model actually named earlier in the
  same response (43, 183, 196). Fixed by human adjudication of the ~16 commits, NOT
  by tuning trigger priority against the 200-case eval set (that would fit the
  extractor to the test data -- a manuscript-integrity hazard).


## Decision Log

- Decision: Abandon vLLM+HF for LLaVA-Med; serve via Ollama GGUF.
  Rationale: native transformers proved the HF checkpoint does not read images;
  the Ollama GGUF does. Date/Author: 2026-07-01, user + Claude/Opus 4.8.
- Decision: Keep the RadLE prompt identical; add a last-resort prose extractor
  instead of prompting the model differently.
  Rationale: manuscript parity is absolute; the failsafe recovers committed
  diagnoses without changing inputs. Date/Author: 2026-07-01, user + Claude/Opus 4.8.
- Decision: Make the prose extractor conservative (commitment-only, reject
  modality/possibility text).
  Rationale: a lenient extractor would fabricate diagnoses from descriptions and
  corrupt the results. Date/Author: 2026-07-01, Claude/Opus 4.8.
- Decision: Run through a standalone script, not the vLLM notebook.
  Rationale: the notebook is vLLM-specific and retired; a script reuses the proven
  benchmark/audit code with an inline Ollama config and no registry churn.
  Date/Author: 2026-07-01, Claude/Opus 4.8.
- Decision: Do NOT add retries/best-of-N to recover no-answers for LLaVA-Med.
  Rationale: proven empirically -- the 52 empty-generation cases are deterministic
  ([0,0,0] chars over 3 re-hits with the exact locked payload), so a retry recovers
  nothing; and resampling the 132 considered descriptions until they commit would
  be best-of-N cherry-picking, not the transport-failure recovery Morning did. The
  only levers that could change the empties (temperature/prompt/image) break
  manuscript parity. Date/Author: 2026-07-02, user + Claude/Opus 4.8.


## Recipe: add a NEW open medical VLM (reference for future models / Codex)

1. **Prove image conditioning BEFORE any integration.** Never trust a green server.
   - If an HF checkpoint: adapt `scripts/llava_med_hf_probe.py` — load via native
     transformers with the model's own processor/chat template, greedy, no
     constraints, run two visually DIFFERENT real cases, and confirm the outputs
     differ per image. Add a forced `min_new_tokens` pass to distinguish
     immediate-EOS from true blindness.
   - If served via an OpenAI-compatible endpoint (Ollama/vLLM/etc.): adapt
     `scripts/ollama_llava_med_probe.py` — same two-image conditioning gate using
     the real `build_content_array` payload. Different outputs per image = go;
     identical/empty/degenerate = the conversion/serving is broken, do not proceed.
2. **Characterize output format** on ~6-8 varied cases: does it return JSON? Does it
   commit to a diagnosis or just describe? Identical boilerplate across images?
3. **Keep the RadLE prompt identical.** If the model does not emit JSON, rely on
   `extract_json_safely` (JSON -> VQA -> conservative prose). Extend the prose
   triggers/stoplist ONLY if needed and keep it commitment-only.
4. **Run via a small script** modeled on `scripts/run_llava_med_ollama.py`: build
   run paths, build an OpenAI client for the endpoint, pass an inline model config
   `{"name": <stable_model_name>, "id": <endpoint_model_tag>, "extra": <or None>}`,
   call `radle_benchmark.run_benchmark`, print a diagnosis-rate summary.
5. **Audit -> repair -> promote -> export** under the standard Workbench guardrails.
   Do not promote with pending repair targets/integrity warnings unless the user
   overrides. Record any serving/quantization difference in the methods section.


## Concrete Steps And Commands

On the Workbench VM terminal:

    # One-time (already done for LLaVA-Med):
    curl -fsSL https://ollama.com/install.sh | sh
    ollama pull z-uo/llava-med-v1.5-mistral-7b_q8_0

    # Prove image conditioning:
    cd ~/RadLE_CRASH_Lab && git pull
    python scripts/ollama_llava_med_probe.py 1 8 78 12 45 120 180

    # Run the benchmark (shakedown then full):
    python scripts/run_llava_med_ollama.py --limit=5
    python scripts/run_llava_med_ollama.py

Local static checks (repo root, this machine):

    py -3.11 -m py_compile src/radle_benchmark.py scripts/run_llava_med_ollama.py
    py -3.11 -c "import sys; sys.path.insert(0,'src'); import radle_benchmark as rb; print(rb.extract_json_safely('shows the presence of a pulmonary embolism.'))"


## Interfaces And Dependencies

- Ollama OpenAI endpoint: `http://localhost:11434/v1`, model tag
  `z-uo/llava-med-v1.5-mistral-7b_q8_0` (`OLLAMA_BASE_URL` / `OLLAMA_LLAVA_MODEL`
  env overrides).
- Benchmark API: `radle_benchmark.run_benchmark(client, image_folder, output_csv,
  models=[{name,id,extra}], resume, max_output_tokens, ...)`.
- Extraction: `radle_benchmark.extract_json_safely(raw_text)` (+ `_extract_prose_diagnosis`).
- Paths: `radle_medical_custom_runtime.build_medical_run_paths(...)`.
- Audit/repair/promote/export: `radle_benchmark.audit_benchmark_output`,
  repair plan/run helpers, `promote_final_results`, `export_public_release_tables`.
- Probes: `scripts/llava_med_hf_probe.py` (native HF), `scripts/ollama_llava_med_probe.py`
  (endpoint conditioning gate).
- Dataset root on VM: `/home/jupyter/radle_dataset/RadLE v2 Dataset`
  (`RADLE_LOCAL_DATASET_ROOT`); master images under `.../RadLE v2 Master Data`.


## Related Documents

- `Documents/execplan_llava_vllm_runtime.md` — the retired vLLM/HF rollercoaster and
  the evidence the HF checkpoint is dead. Read for history; do not reopen the route.
- `Documents/execplan_medical_workbench_runtime.md` — parent SSOT for the medical
  Workbench (SGLang abandonment, guardrails).
- `Documents/handoff_llava_vllm_next_session.md` — lean session pointer.
