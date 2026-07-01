# Run LLaVA-Med through vLLM with an HF-format checkpoint

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` exists. The only repo `AGENTS.md` files found are under `vllm_0_23_0/`, so they do not apply to this repo-level plan or to `Documents/`, `src/`, or `notebooks/`.


## Purpose / Big Picture

Serve `llava_med_mistral_7b` through vLLM using an HF-format LLaVA checkpoint, then run it through the same RadLE medical Workbench contract used for MedGemma. The deliverable is a new LLaVA-vLLM notebook that can produce a model-scoped full run, audit it, repair only through the established repair path, promote only under Workbench guardrails, export answer-free public tables, and sync the run bundle.

The pivot exists because the SGLang route proved image tokens were inserted but did not produce useful image-conditioned diagnoses. The new route must remove guessed SGLang shims and preserve methodological comparability with the completed MedGemma baseline.


## Current State

Current state (2026-07-01 10:48 +05:30, Codex/GPT-5): the GUI has now fast-forwarded to commit `6050807` and again verified `llava_med_mistral_7b -> chaoyinshe/llava-med-v1.5-mistral-7b-hf via vllm`. The latest pushed correction moved the vLLM optional rotary FlashAttention fallback patch into `src/radle_medical_custom_runtime.py` inside the vLLM `start_model_server()` path, so stale notebook cells that call the fresh helper should still apply the patch before launching the server subprocess. No Workbench/Jupyter runtime success has been claimed. Next required evidence is still Section 6 output showing the helper-level patch line, then `/v1/models` or the next exact traceback/log; if that passes, Section 6.5 must show raw response plus parsed `diagnosis` and valid `likert_score`. Stop before Section 7.

### Rollercoaster So Far

- SGLang looked alive but was abandoned because it inserted the expected visual-token count while generation stayed blank, echoed prompts, or emitted image-placeholder text rather than a clinical diagnosis.
- The first vLLM notebook attempt ran the wrong runtime state: the GUI imported a stale/default helper and tried `microsoft/llava-med-v1.5-mistral-7b`, which vLLM rejected before readiness.
- The branch-pinned bootstrap and mapping assertions fixed that: GUI evidence then showed `codex/llava-vllm-runtime`, the HF-format `chaoyinshe` checkpoint, and `engine=vllm`.
- The next real blocker was dependency/runtime-level: vLLM 0.23 entered Mistral rotary initialization and crashed on `ModuleNotFoundError: No module named 'flash_attn.ops'`.
- The uninstall/probe cleanup was too weak because a `flash_attn` namespace remained visible; the notebook-only optional-import patch was also too weak because the open Jupyter notebook could run stale in-memory Section 6 cell contents after a git fast-forward.
- The current pushed state (`6050807`) puts the critical vLLM optional rotary fallback patch in the imported runtime helper. This is the first version that should survive stale notebook cell text as long as Section 1 imports the fresh helper from the checked-out repo.

HANDOFF NOTE (2026-07-01, Claude/Opus 4.8 -> Codex): this plan is now the ACTIVE LLaVA-Med task and the parent SSOT (`Documents/execplan_medical_workbench_runtime.md`, HEAD `080ec65`) points here. The SGLang abandonment is backed by LIVE Workbench evidence, not a hunch — do not reopen SGLang. On Workbench HEAD `080ec65` the SGLang server came up, every shim applied (`CLIPVisionConfig/MistralConfig positional-arg shim applied`, `LlamaTokenizer.image_processor (CLIP) shim applied`, `llava_mistral config shim OK ... pad_token_id= 2 vision_feature_layer= -2`), and the custom mistral chat template loaded with NO parse error (`Loading chat template from argument: .../llava_med_mistral_chat_template.json`). The template was the canonically-correct FastChat `mistral` shape, so the failure is NOT a template-tuning gap. §6.5 confirmed the image is spliced (prompt_tokens 371->949 = exactly 576 CLIP visual tokens; a short-prompt probe went 24->600), yet a non-committed 4-way diagnostic probe against the live endpoint returned: `[A full/greedy]=''`, `[B full/temp0.7]=''`, `[C short/greedy]=''`, `[D short/temp0.7]='image> '` (4 tokens). Across TWO templates (vicuna echoed the text instructions; mistral echoes the literal `<image>` placeholder) the model NEVER engages the image — the guessed HF-projector fields + hand-attached CLIP processor produce image embeddings the LM ignores. The probe and smoke output were throwaway (NOT committed); the SGLang notebook is unchanged at `080ec65`. Calibrate the new §6.5 vLLM smoke to hard-fail on exactly this signature (empty / 1-token EOS / `<image>`-placeholder echo / prompt echo). The user (returning ~5h after this handoff) explicitly chose the vLLM + HF-checkpoint route; begin at Milestone 1 (verify `chaoyinshe/llava-med-v1.5-mistral-7b-hf`).


## Locked Facts

- SGLang LLaVA-Med is abandoned. No more SGLang shims, chat-template hacks, or `sitecustomize`.
- Candidate checkpoint: `chaoyinshe/llava-med-v1.5-mistral-7b-hf`. It must be verified live before notebook work.
- HF structural metadata for `chaoyinshe/llava-med-v1.5-mistral-7b-hf` passed on 2026-07-01 via the official Hugging Face API: resolved revision `627be53734c667cbb1669608dac747a4485a22d7`, `architectures=["LlavaForConditionalGeneration"]`, `model_type="llava"`, `image_token_index=32000`, CLIP vision config, Mistral text config, processor/preprocessor/tokenizer files, safetensor index, and four safetensor shards.
- The original `microsoft/llava-med-v1.5-mistral-7b` entry in `src/radle_medical_custom_runtime.py` is not the target for the vLLM run.
- `src/radle_medical_custom_runtime.py` maps `llava_med_mistral_7b` to `model_id="chaoyinshe/llava-med-v1.5-mistral-7b-hf"` with `preferred_engine="vllm"` as of the Antigravity static edit slice.
- The 2026-07-01 GUI run failed before `/v1/models` because the Workbench runtime imported a stale/default-branch helper and started `microsoft/llava-med-v1.5-mistral-7b`, which vLLM rejected as `LlavaMistralForCausalLM`.
- `notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb` must fetch/check out `codex/llava-vllm-runtime` by default and assert `llava_med_mistral_7b -> chaoyinshe/llava-med-v1.5-mistral-7b-hf` via `vllm` before Section 6 starts.
- The post-`0b90a60` GUI run proved the branch and mapping are correct, then failed before `/v1/models` on a partial/incompatible `flash_attn` package missing `flash_attn.ops.triton.rotary`.
- `notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb` now must probe `flash_attn.ops.triton.rotary` after vLLM install and again immediately before Section 6 server start, removing only the partial `flash-attn`/`flash_attn` package when that exact probe fails.
- vLLM 0.23.0 can still make `find_spec("flash_attn")` true through its internal virtual `flash_attn` package; Section 6 must patch only the installed vLLM optional rotary import to fall back when `flash_attn.ops.triton.rotary` is absent.
- The open Antigravity/Jupyter notebook can execute stale in-memory cell contents after Section 1 fast-forwards the repo branch; critical server preflights must live in `src/radle_medical_custom_runtime.py`, not only in notebook cell text.
- Target notebook: `notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb`.
- Run contract: `RUN_ID=llava_med_mistral_7b_medical_full_200_cases`, 200 cases, 263 images, `TEST_LIMIT=None`, `RESUME=True`, `MAX_OUTPUT_TOKENS=2048`.
- vLLM server args must include `--limit-mm-per-prompt {"image": 5}` because case 156 has 5 images.
- Use `MODEL_DTYPE="float16"` unless vLLM refuses it; if refused, stop and record evidence before changing dtype.
- Keep the RadLE prompt and OpenAI-style image payload from `src/radle_benchmark.py`: text prompt plus base64 `data:` URL `image_url` blocks.
- Do not add text-only controls, image perturbation controls, or extra experimental arms.
- The Workbench promotion guardrails are stricter than the old Morning saved-output flow; for this LLaVA run, do not promote or sync while integrity problems or repair targets remain unless the user explicitly overrides.
- Do not touch OctoMed or InternVL notebooks for this task.


## Do Not Revisit

- Do not resume SGLang without explicit new user direction. See Decision Log 2026-07-01.
- Do not use the original Microsoft checkpoint through vLLM by config relabel alone. See Decision Log 2026-07-01.
- Do not add text-only or image-perturbation controls. See Decision Log 2026-07-01.
- Do not treat server readiness or prompt-token growth as success. See Decision Log 2026-07-01.
- Do not copy the old Morning promotion behavior that promoted raw output with pending repair targets. See Decision Log 2026-07-01.


## Progress

- [x] (2026-07-01 01:17 +05:30, Codex/GPT-5) Created the vLLM child plan and removed the old SGLang child plan.
- [x] (2026-07-01 01:21 +05:30, Codex/GPT-5) Researched the preferred HF checkpoint, original Microsoft layout, vLLM multimodal usage, and fallback conversion risk.
- [x] (2026-07-01 01:57 +05:30, user and Codex/GPT-5) Locked out text-only and image-perturbation controls because they break MedGemma comparability.
- [x] (2026-07-01 02:30 +05:30, Codex/GPT-5) Reconciled this plan with the Morning notebook, Morning saved-output export, MedGemma Workbench notebook, and main runtime modules.
- [x] (2026-07-01 02:47 +05:30, Codex/GPT-5) Verified `chaoyinshe/llava-med-v1.5-mistral-7b-hf` structurally through the official Hugging Face API without downloading full weights: revision `627be53734c667cbb1669608dac747a4485a22d7`, required processor/tokenizer/index/shard files present, `LlavaForConditionalGeneration`, `model_type="llava"`, `image_token_index=32000`, vision config, and text config.
- [x] (2026-07-01 02:48 +05:30, Codex/GPT-5) Patched only the LLaVA runtime mapping so `llava_med_mistral_7b` resolves to the HF-format checkpoint under vLLM while keeping the stable model name.
- [x] (2026-07-01 02:50 +05:30, Codex/GPT-5) Created `notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb` from `notebooks/RadLE_Medical_Workbench_Runtime.ipynb`, set the required LLaVA/vLLM full-run contract, and inserted a non-writing Section 6.5 smoke gate that requires parseable clinical JSON.
- [x] (2026-07-01 02:50 +05:30, Codex/GPT-5) Completed static validation, committed, and pushed the first Antigravity edit slice as commit `7e52038` on branch `codex/llava-vllm-runtime`.
- [x] (2026-07-01 09:38 +05:30, user via Antigravity GUI) Returned the first real vLLM notebook error from Section 6: `RuntimeError: OpenAI-compatible server exited before readiness with code 1`; the last server log lines included `Value error, Model architectures ['LlavaMistralForCausalLM'] are not supported for now`, and the log showed `microsoft/llava-med-v1.5-mistral-7b`.
- [x] (2026-07-01 09:53 +05:30, Codex/GPT-5) Patched `notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb` so Section 1 fetches/checks out `codex/llava-vllm-runtime` by default and Sections 1, 3, and 4 fail early if the imported helper maps LLaVA to anything other than `chaoyinshe/llava-med-v1.5-mistral-7b-hf` through `vllm`.
- [x] (2026-07-01 10:00 +05:30, Codex/GPT-5) Static validation passed: `py -3.11 -m py_compile src/radle_medical_custom_runtime.py`; notebook JSON loaded with 19 cells and 16 compiled code cells; branch checkout/mapping assertion checks passed; forbidden stale-route string search in the vLLM notebook returned no matches; `git diff --check` passed for touched files.
- [x] (2026-07-01 10:13 +05:30, user via Antigravity GUI and Codex/GPT-5) Confirmed the post-`0b90a60` GUI run used the correct branch and mapping, then captured the new first server error before `/v1/models`: `ModuleNotFoundError: No module named 'flash_attn.ops'` from `flash_attn.ops.triton.rotary`.
- [x] (2026-07-01 10:13 +05:30, Codex/GPT-5) Patched the LLaVA-vLLM dependency cell to probe `flash_attn.ops.triton.rotary` and uninstall only partial/incompatible `flash-attn`/`flash_attn`; patched Section 6.5 to require Section 6 `endpoint_client` and `/v1/models` state before smoke.
- [x] (2026-07-01 10:24 +05:30, user via Antigravity GUI and Codex/GPT-5) Confirmed the GUI run fast-forwarded through commit `e711a5c` and branch/mapping remained correct, but Section 6 still failed on `ModuleNotFoundError: No module named 'flash_attn.ops'`; the returned output did not show a server-cell FlashAttention probe/cleanup before server start.
- [x] (2026-07-01 10:20 +05:30, Codex/GPT-5) Patched Section 6 itself to run the narrow `flash_attn.ops.triton.rotary` probe and cleanup immediately before `medical_runtime.start_model_server(...)`, making the server-start path robust to skipped/reordered dependency cells.
- [x] (2026-07-01 10:35 +05:30, user via Antigravity GUI and Codex/GPT-5) Confirmed the GUI run fast-forwarded through commit `9dfbfc6`, retained the correct branch/mapping, then Section 6 still failed before `/v1/models` on `ModuleNotFoundError: No module named 'flash_attn.ops'`.
- [x] (2026-07-01 10:35 +05:30, Codex/GPT-5) Inspected vLLM 0.23.0 local source and patched the notebook Section 6 preflight to update installed `vllm/model_executor/layers/rotary_embedding/common.py` so only the optional `flash_attn.ops.triton.rotary` import falls back cleanly when missing.
- [x] (2026-07-01 10:43 +05:30, user via Antigravity GUI and Codex/GPT-5) Confirmed the GUI run after `fa126f2` still failed on `flash_attn.ops` and did not print the notebook-only `Preflight vLLM rotary optional flash_attn fallback patch...` line, indicating stale open notebook cell contents.
- [x] (2026-07-01 10:43 +05:30, Codex/GPT-5) Moved the vLLM optional rotary FlashAttention fallback patch into `src/radle_medical_custom_runtime.py` so `start_model_server(engine="vllm")` applies it before every vLLM server subprocess launch.
- [x] (2026-07-01 10:48 +05:30, user via Antigravity GUI) Confirmed the GUI fast-forwarded from `fa126f2` to `6050807` and again verified the helper mapping `llava_med_mistral_7b -> chaoyinshe/llava-med-v1.5-mistral-7b-hf via vllm`.
- [ ] (next, Codex/GPT-5) Complete static validation, commit/push the correction slice, and return the receipt to the Codex app coordinator.
- [ ] (next, user via Antigravity GUI + Codex app coordinator) Restart/clear the vLLM notebook and run only through Section 6.5 before any full run.


## Surprises & Discoveries

- Observation: SGLang inserted the correct NUMBER of visual tokens but the features never drove generation; a green server + correct image-token count is not evidence of a working multimodal forward pass.
  Evidence: prompt_tokens expanded 371->949 (exactly 576 CLIP tokens; short prompt 24->600). 4-way live probe: `[A full/greedy]=''`, `[B full/temp0.7]=''`, `[C short/greedy]=''`, `[D short/temp0.7]='image> '`. Greedy and sampled both fail; sampling once emitted the literal placeholder. Tested at Workbench HEAD `080ec65` with all shims applied and the canonically-correct mistral chat template loaded (no parse error). Implication for this plan: the §6.5 vLLM smoke MUST assert a real clinical diagnosis, never just a prompt-token jump.
  Date/Author: 2026-07-01, user and Claude/Opus 4.8

- Observation: At the start of the first static edit slice, the runtime registry still pointed LLaVA at the abandoned path.
  Evidence: before commit `7e52038`, `src/radle_medical_custom_runtime.py` mapped `llava_med_mistral_7b` to `microsoft/llava-med-v1.5-mistral-7b` with `preferred_engine="sglang"`.
  Date/Author: 2026-07-01, Codex/GPT-5

- Observation: The old saved Morning export promoted a raw final despite pending repair targets.
  Evidence: `Documents/RadLE_v1_5_Morning_2.md` shows 1985 accepted cells, 10 paid-repair cells, 5 analysis flags, `REPAIR_CONFIRMATION="NO"`, and private final promotion from raw CSV.
  Date/Author: 2026-07-01, Codex/GPT-5

- Observation: The `hf` CLI is not installed in this Antigravity/Codex environment, so the HF gate used the official Hugging Face REST API and raw `config.json` endpoint instead.
  Evidence: `hf models info chaoyinshe/llava-med-v1.5-mistral-7b-hf --format json` failed with `hf : The term 'hf' is not recognized`; `Invoke-RestMethod https://huggingface.co/api/models/chaoyinshe/llava-med-v1.5-mistral-7b-hf` returned revision `627be53734c667cbb1669608dac747a4485a22d7` and the required file/config fields.
  Date/Author: 2026-07-01, Codex/GPT-5

- Observation: The Workbench runtime can import stale repo code even when this local branch is correct, because the notebook bootstrap previously cloned/pulled without forcing `codex/llava-vllm-runtime`.
  Evidence: the GUI run selected `SELECTED_MODEL_NAME="llava_med_mistral_7b"` and `SERVER_ENGINE="vllm"`, but the Section 6 server log showed vLLM starting `microsoft/llava-med-v1.5-mistral-7b` and rejecting `LlavaMistralForCausalLM` before `/v1/models`.
  Date/Author: 2026-07-01, user and Codex/GPT-5

- Observation: A partial or incompatible `flash_attn` package can crash vLLM 0.23.0 during LLaVA-Med Mistral startup before `/v1/models`.
  Evidence: the post-`0b90a60` GUI server log entered Mistral rotary embedding initialization, then failed importing `flash_attn.ops.triton.rotary` with `ModuleNotFoundError: No module named 'flash_attn.ops'`; Section 6.5 then produced `NameError: endpoint_client is not defined` only because Section 6 had not completed.
  Date/Author: 2026-07-01, user and Codex/GPT-5

- Observation: In vLLM 0.23.0, uninstalling `flash-attn` is not enough if vLLM has registered its own virtual `flash_attn` package.
  Evidence: local source `vllm/vllm_flash_attn/__init__.py` can register `sys.modules["flash_attn"]`; `vllm/model_executor/layers/rotary_embedding/common.py` checks only `find_spec("flash_attn")` before directly importing `flash_attn.ops.triton.rotary`, causing the same missing-ops crash even without a usable upstream FlashAttention package.
  Date/Author: 2026-07-01, Codex/GPT-5

- Observation: Git fast-forward evidence in Section 1 does not guarantee the already-open notebook UI is executing the new notebook cell contents.
  Evidence: after `fa126f2`, Section 1 printed `Using repo commit: fa126f2`, but Section 6 output contained only the older `Preflight flash_attn rotary probe before server start...` cleanup and never printed `Preflight vLLM rotary optional flash_attn fallback patch...`.
  Date/Author: 2026-07-01, user and Codex/GPT-5


## Decision Log

- Decision: Abandon LLaVA-Med SGLang and pivot to vLLM with an HF-format checkpoint.
  Rationale: SGLang required guessed projector config and hand-attached image processing; image-token count was correct but the model did not diagnose.
  Date/Author: 2026-07-01, user and Claude/Opus 4.8

- Decision: Correct the LLaVA model mapping for this route instead of relying on notebook prose.
  Rationale: `start_model_server()` and `run_medical_model_benchmark()` both resolve the model through `src/radle_medical_custom_runtime.py`; leaving that registry on Microsoft/SGLang would make the new notebook fragile.
  Date/Author: 2026-07-01, Codex/GPT-5

- Decision: Keep this pivot isolated from OctoMed and InternVL.
  Rationale: Those are separate model tracks and must not inherit LLaVA-specific serving changes.
  Date/Author: 2026-07-01, user and Codex/GPT-5

- Decision: Do not add creative smoke controls.
  Rationale: Controls not used in the MedGemma path are methodology drift for the final comparison.
  Date/Author: 2026-07-01, user and Codex/GPT-5

- Decision: Use Workbench promotion guardrails, not the older Morning raw-promotion behavior.
  Rationale: A full medical run must not be promoted or synced while repairs or integrity warnings remain unless the user explicitly accepts that state.
  Date/Author: 2026-07-01, Codex/GPT-5

- Decision: Keep the Antigravity static edit slice on branch `codex/llava-vllm-runtime`.
  Rationale: The coordinator packet requested that branch when repo state permits, and the checkout had unrelated dirty work that must not be folded into this slice.
  Date/Author: 2026-07-01, Codex/GPT-5

- Decision: Force the notebook bootstrap to fetch/check out `codex/llava-vllm-runtime` and assert the LLaVA-vLLM mapping before starting the server.
  Rationale: The first GUI vLLM error proved the runtime could otherwise start the stale Microsoft checkpoint and fail before readiness; the correction must make the imported helper observable and fail early if it is wrong.
  Date/Author: 2026-07-01, user and Codex/GPT-5

- Decision: Reuse the narrow FlashAttention cleanup pattern from the InternVL Workbench route for LLaVA-vLLM.
  Rationale: vLLM only crashes because `flash_attn` is discoverable but lacks `flash_attn.ops.triton.rotary`; if that exact probe fails, uninstalling the partial package lets vLLM use its rotary fallback without adding a new experimental dependency or changing model semantics.
  Date/Author: 2026-07-01, Codex/GPT-5

- Decision: Run the FlashAttention probe in Section 6 as well as the dependency cell.
  Rationale: The GUI can reach the server cell without evidence that the dependency-cell cleanup ran in the current kernel; the invariant that matters is immediately before starting the vLLM subprocess.
  Date/Author: 2026-07-01, Codex/GPT-5

- Decision: Patch vLLM's installed optional rotary FlashAttention import in the notebook preflight rather than adding a sitecustomize hook or changing model settings.
  Rationale: The crash is in an optional acceleration path; catching only missing `flash_attn*` rotary modules preserves all other import failures while enabling vLLM's existing native rotary fallback.
  Date/Author: 2026-07-01, Codex/GPT-5

- Decision: Put critical vLLM server preflights in the runtime helper as well as the notebook.
  Rationale: The helper is imported from the checked-out repo during the run, while open notebook cell contents can stay stale after a branch fast-forward.
  Date/Author: 2026-07-01, Codex/GPT-5


## Revision Notes

- v1-v5 (2026-07-01, Codex/GPT-5): Created the vLLM child plan, added research, then compacted after speculative controls were rejected.
- v6 (2026-07-01 02:30 +05:30, Codex/GPT-5): Removed remaining fluff, added concrete repo orientation, exact implementation target files, validation commands, and guardrails from the Morning and Workbench evidence.
- v7 (2026-07-01 02:34 +05:30, Codex/GPT-5): Tightened Section 6.5 smoke acceptance to require an actual clinical diagnosis; `"I don't know"` remains valid only for the full benchmark path.
- v8 (2026-07-01 02:50 +05:30, Codex/GPT-5): Recorded the Antigravity coordinator packet execution: HF structural metadata passed, the LLaVA runtime mapping was patched to the HF-format checkpoint, the new vLLM notebook was created from the Workbench pattern, and GUI runtime proof remains pending.
- v9 (2026-07-01 09:53 +05:30, Codex/GPT-5): Recorded the GUI Section 6 runtime defect and the correction: branch-pinned notebook bootstrap plus pre-server mapping assertions. Runtime proof remains pending and must come from a fresh GUI run through Section 6.5.
- v10 (2026-07-01 10:13 +05:30, Codex/GPT-5): Recorded the post-branch-fix `flash_attn.ops.triton.rotary` startup failure and the notebook dependency-cell cleanup plus Section 6.5 prerequisite guard. Runtime proof remains pending.
- v11 (2026-07-01 10:24 +05:30, Codex/GPT-5): Strengthened the FlashAttention cleanup by adding the same exact probe to Section 6 immediately before server startup, after GUI evidence through `e711a5c` still failed on the partial `flash_attn` package. Runtime proof remains pending.
- v12 (2026-07-01 10:35 +05:30, Codex/GPT-5): Recorded the post-`9dfbfc6` repeated `flash_attn.ops` failure and added a notebook-time vLLM optional-import patch for the rotary fallback path. Runtime proof remains pending.
- v13 (2026-07-01 10:43 +05:30, Codex/GPT-5): Recorded the post-`fa126f2` stale-cell evidence and moved the vLLM optional-import fallback patch into the runtime helper server-start path. Runtime proof remains pending.
- v14 (2026-07-01 10:48 +05:30, Codex/GPT-5): Added the rollercoaster timeline and recorded that GUI setup pulled `6050807` with the correct LLaVA-vLLM helper mapping. Runtime proof remains pending.


## Outcomes & Retrospective

The first static vLLM implementation slice was pushed, and the branch/mapping correction was proven in the GUI at commit `0b90a60`. The current pushed state at `6050807` has the correct HF-format checkpoint mapping and a helper-level vLLM optional rotary FlashAttention fallback patch. The next unproven gate is still runtime: Section 6 must show the helper-level patch line and `/v1/models`, then Section 6.5 must prove a real benchmark-style JSON diagnosis with valid `likert_score`. No Workbench/Jupyter smoke or full run has been proven yet. The main reusable lesson is project-specific here: a smoke gate must prove a real benchmark-style JSON diagnosis, not just server readiness or image-token insertion, and remote notebook bootstraps must make both the imported repo revision and stale-cell risk visible.


## Suggested Skills By Phase

| Phase | Skill | Why | Activation |
| --- | --- | --- | --- |
| Plan maintenance | `execplan` | Keep this handoff current and compact. | `auto-suggest` |
| HF checkpoint verification | `hugging-face:hf-cli` | Verify Hub files and resolved revision before edits. | `manual` |
| Notebook creation | `jupyter-notebook` | Create/edit notebook JSON programmatically and validate cell structure. | `auto-suggest` |
| Code edits | `none` | The source change is a small registry update. | `none` |


## Context And Orientation

`src/radle_benchmark.py` is the benchmark source of truth. It defines the diagnostic radiologist prompt, builds the OpenAI-style multimodal content array, runs models with resume support, audits outputs, builds repair plans, promotes private finals, and exports answer-free public release tables.

`src/radle_medical_custom_runtime.py` is the medical Workbench runtime helper. It defines `MedicalRuntimeModel`, the medical model registry, vLLM/SGLang server command builders, server start/wait helpers, and `run_medical_model_benchmark()`.

`notebooks/RadLE_Medical_Workbench_Runtime.ipynb` is the successful Workbench pattern. It stages the frozen GCS dataset to local disk, installs vLLM, starts a local OpenAI-compatible server, runs one selected model, audits, optionally repairs, promotes under guardrails, exports public tables, and syncs results.

`Documents/RadLE_v1_5_Morning_2.md` is a saved-output export of the older official run. It is useful for the original experiment shape and audit output, but its raw-promotion behavior is not the guardrail to copy for this medical Workbench run.


## Plan Of Work

1. Verify the HF-format checkpoint before edits.
   Use `hugging-face:hf-cli` or `huggingface_hub` to confirm `config.json`, `preprocessor_config.json`, `processor_config.json`, tokenizer files, `model.safetensors.index.json`, safetensor shards, `architectures=["LlavaForConditionalGeneration"]`, `model_type="llava"`, `image_token_index`, CLIP vision config, and a resolved commit SHA.

2. Correct only the LLaVA runtime mapping.
   In `src/radle_medical_custom_runtime.py`, change the `llava_med_mistral_7b` entry to `model_id="chaoyinshe/llava-med-v1.5-mistral-7b-hf"` and `preferred_engine="vllm"`. Keep `name="llava_med_mistral_7b"` so the run ID and output schema stay stable. Do not modify OctoMed, InternVL, or MedGemma entries.

3. Create the new notebook from the proven Workbench pattern.
   Create `notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb` programmatically from `notebooks/RadLE_Medical_Workbench_Runtime.ipynb`, not from the SGLang notebook. Use:
   - `SELECTED_MODEL_NAME = "llava_med_mistral_7b"`
   - `SERVER_ENGINE = "vllm"`
   - `RUN_LABEL_BASE = "medical_full_200_cases"`
   - `TEST_LIMIT = None`
   - `RESUME = True`
   - `MAX_OUTPUT_TOKENS = 2048`
   - `EXPECTED_FULL_CASES = 200`
   - `EXPECTED_FULL_IMAGES = 263`
   - `MODEL_DTYPE = "float16"`
   - `MAX_MODEL_LEN = 8192`
   - `EXTRA_SERVER_ARGS = ["--dtype", MODEL_DTYPE, "--limit-mm-per-prompt", "{\"image\": 5}"]`

4. Add a non-writing Section 6.5 smoke gate.
   After server readiness and before `run_medical_model_benchmark()`, send the normal RadLE prompt and images through the local endpoint without writing to the run CSV. Use case 156 or another verified 5-image case. Hard-fail if the response is empty, repeats the prompt, emits `<image>`, is not parseable JSON, lacks `diagnosis`, returns `"I don't know"`, or returns any other placeholder instead of a clinical diagnosis. This is not a new control arm; it is a run-safety gate using the same benchmark payload style.

5. Preserve the established audit/repair/promote/export/sync sequence.
   Keep the Workbench audit cell, targeted repair dry-run default, promotion guardrails, public answer-free export, runtime provenance, run-context JSON, and GCS sync. Do not promote or sync if final output is absent, void, unaudited, has integrity problems, or has repair targets unless the user explicitly overrides.

6. Validate notebook structure before committing or handing off.
   Count cells, list section headers, ensure no duplicate/missing major sections, and ensure no SGLang/sitecustomize/chat-template shim cells are present.


## Milestones

### Milestone 1: Checkpoint Gate

Skill: `hugging-face:hf-cli` manually if available.

End state: the preferred checkpoint is proven structurally compatible enough to try vLLM, or the plan stops before code/notebook edits.

Acceptance:
- HF files and config fields are present.
- Resolved revision SHA is recorded.
- No fallback conversion is started unless the HF checkpoint fails structurally.

### Milestone 2: Runtime Mapping And Notebook Build

Skill: `jupyter-notebook` auto-suggest for notebook editing.

End state: one new LLaVA-vLLM notebook exists and the shared runtime resolves LLaVA to the HF-format checkpoint.

Acceptance:
- `src/radle_medical_custom_runtime.py` changes only the LLaVA entry.
- New notebook uses vLLM and contains no SGLang machinery.
- Notebook structure validation passes.

### Milestone 3: Non-Writing Smoke

Skill: `none`.

End state: the live server produces one parseable benchmark-style clinical JSON response before the full run.

Acceptance:
- `/v1/models` responds.
- Section 6.5 returns non-empty JSON with an actual clinical `diagnosis` and `likert_score`.
- The smoke diagnosis is not `"I don't know"`.
- The response is not prompt echo and not `<image>` echo.
- No result CSV row is written by the smoke gate.

### Milestone 4: Full Run And Release Guardrails

Skill: `none`.

End state: the 200-case run is complete, audited, repaired if needed through the established path, promoted only if allowed by guardrails, exported, and synced.

Acceptance:
- Audit shows 200 rows and 200 unique cases for this one-model run.
- Missing, duplicate, and extra case IDs are `none`.
- Repair targets are resolved or explicitly accepted by the user before promotion.
- Final manifest, public release manifest, and runtime provenance exist.


## Concrete Steps And Commands

Run local checks from repo root on Windows PowerShell unless noted.

Check files that define the current contract:

    rg -n "llava_med_mistral_7b|medgemma_1_5_4b|def build_vllm_command|def run_medical_model_benchmark" src/radle_medical_custom_runtime.py
    rg -n "PROMPT|build_content_array|image_url|run_benchmark|audit_benchmark_output|promote_final_results|export_public_release_tables" src/radle_benchmark.py

Expected: LLaVA currently appears once in the model registry and currently points to Microsoft/SGLang before the planned patch.

Validate notebook structure after creating the new notebook:

    py -3.11 -c "import json,pathlib; p=pathlib.Path('notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb'); nb=json.loads(p.read_text(encoding='utf-8')); print('cells', len(nb['cells'])); headers=[]; [headers.append(''.join(c.get('source',[])).splitlines()[0]) for c in nb['cells'] if ''.join(c.get('source',[])).lstrip().startswith('#')]; print('\n'.join(headers))"

Expected: section headers follow the Workbench flow, include a Section 6.5 smoke gate, and contain no SGLang/sitecustomize/chat-template shim sections.

Search the new notebook for forbidden carryover:

    rg -n "sglang|sitecustomize|chat_template|llava_mistral|CLIPVisionConfig|MistralConfig positional|image_processor shim" notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb

Expected: no matches in the new notebook.

Confirm the runtime registry points LLaVA at the HF-format checkpoint after the patch:

    rg -n "llava_med_mistral_7b|chaoyinshe/llava-med-v1.5-mistral-7b-hf|preferred_engine=\"vllm\"" src/radle_medical_custom_runtime.py

Expected: the LLaVA registry entry keeps `name="llava_med_mistral_7b"`, uses `model_id="chaoyinshe/llava-med-v1.5-mistral-7b-hf"`, and uses `preferred_engine="vllm"`.

Check worktree scope before commit:

    git status --short

Expected: only `Documents/execplan_llava_vllm_runtime.md`, `src/radle_medical_custom_runtime.py`, and `notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb` should be part of this task unless the user explicitly expands scope.


## Validation And Acceptance

Checkpoint acceptance:
- HF checkpoint metadata and processor files are present.
- vLLM imports in the runtime.
- Server starts and `/v1/models` lists the served checkpoint.

Smoke acceptance:
- Section 6.5 uses the standard RadLE prompt and image payload.
- Output parses to JSON.
- `diagnosis` is a non-empty clinical diagnosis, not `"I don't know"`.
- `likert_score` is `0` through `4`.
- Output is not prompt echo, not `<image>` echo, and not blank.

Full-run acceptance:
- Raw CSV has 200 rows for the one selected model.
- Audit integrity has no missing, duplicate, or extra case IDs.
- No promotion occurs while pending repairs or integrity warnings remain unless explicitly overridden by the user.
- Final CSV, final manifest, public release outputs, runtime provenance, and GCS sync log exist after a promoted run.


## Idempotence And Recovery

HF verification is read-only and safe to rerun. Notebook creation should be programmatic; rerun it from a clean source notebook if cell structure validation fails. Server startup is safe to rerun after stopping the previous process. The full benchmark uses `RESUME=True`, so reruns should skip accepted existing cells. If Section 6.5 fails with blank output or echo behavior, stop before the full run and inspect server logs and checkpoint compatibility. If vLLM cannot load the preferred HF checkpoint structurally, use the local conversion fallback only after recording the exact error.


## Artifacts And Notes

Morning saved-output evidence:
- `Documents/RadLE_v1_5_Morning_2.md` shows 200 rows, 200 unique cases, 2000 case-model cells, 1985 accepted, 10 paid repair, 5 analysis flags.
- It also shows `REPAIR_CONFIRMATION="NO"` and raw final promotion. That is historical evidence, not the guardrail for this Workbench run.

Workbench evidence:
- `notebooks/RadLE_Medical_Workbench_Runtime.ipynb` already has the safer promotion guardrail: halt promotion on integrity problems or pending repairs unless explicit override flags are set.

Runtime evidence:
- `src/radle_medical_custom_runtime.py` currently routes LLaVA to Microsoft/SGLang. This must be corrected for the vLLM path.


## Interfaces And Dependencies

- vLLM OpenAI-compatible endpoint: `http://127.0.0.1:8000/v1`.
- Main benchmark API: `radle_benchmark.run_benchmark(...)`.
- Medical wrapper: `medical_runtime.run_medical_model_benchmark(...)`.
- Server helper: `medical_runtime.start_model_server(...)`.
- Audit helper: `radle_benchmark.audit_benchmark_output(...)`.
- Promotion helper: `radle_benchmark.promote_final_results(...)`.
- Public export helper: `radle_benchmark.export_public_release_tables(...)`.
