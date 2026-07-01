# Run LLaVA-Med through vLLM with an HF-format checkpoint

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` exists. The only repo `AGENTS.md` files found are under `vllm_0_23_0/`, so they do not apply to this repo-level plan or to `Documents/`, `src/`, or `notebooks/`.


## Purpose / Big Picture

Serve `llava_med_mistral_7b` through vLLM using an HF-format LLaVA checkpoint, then run it through the same RadLE medical Workbench contract used for MedGemma. The deliverable is a new LLaVA-vLLM notebook that can produce a model-scoped full run, audit it, repair only through the established repair path, promote only under Workbench guardrails, export answer-free public tables, and sync the run bundle.

The pivot exists because the SGLang route proved image tokens were inserted but did not produce useful image-conditioned diagnoses. The new route must remove guessed SGLang shims and preserve methodological comparability with the completed MedGemma baseline.


## Current State

Current state (2026-07-01, Claude/Opus 4.8): Root cause confirmed and fix pushed. The 6.4 diagnostic probes proved: (a) LM and text JSON format work fine without extra_body; (b) image pathway works — model generated real clinical diagnoses (Pulmonary tuberculosis, Von Hippel-Lindau syndrome); (c) `bad_words=['</s>', '<pad>']` was blocking the EOS token causing a "1." repetition loop after the model finished its answer. Fix: removed `bad_words`, added VQA-format numbered-list fallback parser to `extract_json_safely`. The model outputs `1. Diagnosis: score (confidence)` format (LLaVA-Med training style) which the parser now handles. Next: user pulls, restarts kernel, runs 6 → 6.4 → 6.5 to confirm smoke passes. The whitespace loop has survived every token-level band-aid (min_tokens, skip_special_tokens, bad_words, control-whitespace logit_bias). Image tokens ARE spliced (`prompt_tokens=3256`) but the model emits only whitespace to the cap — the SAME "model ignores the image" signature SGLang showed across two templates. Rather than block more token IDs, this change adds a non-writing text-only diagnostic (new Section 6.4) that runs BEFORE the image smoke and prints raw output for three text-only requests (clean params, the real RadLE JSON task, and the smoke's own extra_body). This finally splits the two fused failure modes: (a) if plain text ALSO whitespaces, the fault is the LM decode path / chat template / `--generation-config vllm` and is fixable here; (b) if plain text answers coherently but images still whitespace, the fault is the image pathway of the `chaoyinshe` HF conversion (projector weights) and is a checkpoint decision for the user, not a token trick. No server args changed in this push so the single GUI run gives a clean signal. Next: pull, restart/clear if needed, run Section 6 to readiness, then Section 6.4 (read the three probes), then Section 6.5. Stop before Section 7 and report the 6.4 output.

### Rollercoaster So Far

- SGLang looked alive but was abandoned because it inserted the expected visual-token count while generation stayed blank, echoed prompts, or emitted image-placeholder text rather than a clinical diagnosis.
- The first vLLM notebook attempt ran the wrong runtime state: the GUI imported a stale/default helper and tried `microsoft/llava-med-v1.5-mistral-7b`, which vLLM rejected before readiness.
- The branch-pinned bootstrap and mapping assertions fixed that: GUI evidence then showed `codex/llava-vllm-runtime`, the HF-format `chaoyinshe` checkpoint, and `engine=vllm`.
- The next real blocker was dependency/runtime-level: vLLM 0.23 entered Mistral rotary initialization and crashed on `ModuleNotFoundError: No module named 'flash_attn.ops'`.
- The uninstall/probe cleanup was too weak because a `flash_attn` namespace remained visible; the notebook-only optional-import patch was also too weak because the open Jupyter notebook could run stale in-memory Section 6 cell contents after a git fast-forward.
- The pushed state at `6050807` put the critical vLLM optional rotary fallback patch in the imported runtime helper. That was the first version that survived stale notebook cell text as long as Section 1 imported the fresh helper from the checked-out repo.
- The latest GUI evidence proved the rotary fallback/server-readiness slice worked: `/v1/models` returned `chaoyinshe/llava-med-v1.5-mistral-7b-hf`, but Section 6.5 still failed because generation returned `Smoke raw response:` blank with `Smoke completion tokens: 1`.
- Forcing OpenAI structured content, vLLM generation defaults, a repo-owned BOS-prefixed Mistral template, and `min_tokens=16` did not produce acceptable smoke output. The latest GUI run proved `min_tokens` changes the signature from one-token EOS to a full-length blank/stripped generation, so the current correction exposes special-token output and prints raw-response diagnostics while preserving the strict JSON smoke gate.
- The smoke gate must continue to reject full-length hidden/blank output. A valid pass still requires visible strict JSON with a non-placeholder diagnosis and valid `likert_score`.
- The post-`38134f8` diagnostic showed the hidden payload is ordinary control whitespace, so the current correction blocks only tab/newline/carriage-return token IDs through vLLM `logit_bias`; normal spaces remain allowed so diagnosis text can still contain words.

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
- The post-helper-patch GUI run reached `/v1/models` successfully with `chaoyinshe/llava-med-v1.5-mistral-7b-hf`; startup is no longer the current blocker unless later GUI evidence regresses.
- The latest Section 6.5 GUI failure is an empty smoke response for case `156` with 5 images, `finish_reason=stop`, `prompt_tokens=3255`, and `completion_tokens=1`; this is still a hard failure, not runtime success.
- Target notebook: `notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb`.
- Run contract: `RUN_ID=llava_med_mistral_7b_medical_full_200_cases`, 200 cases, 263 images, `TEST_LIMIT=None`, `RESUME=True`, `MAX_OUTPUT_TOKENS=2048`.
- vLLM server args must include `--limit-mm-per-prompt {"image": 5}` because case 156 has 5 images.
- LLaVA-vLLM server args must include `--chat-template src/templates/llava_med_mistral_vllm_chat_template.jinja`, `--chat-template-content-format openai`, and `--generation-config vllm` so vLLM renders a Mistral-shaped multimodal prompt with `bos_token` and uses vLLM generation defaults.
- LLaVA-vLLM request extra body must include `{"min_tokens": 16}` until a GUI smoke proves the model can produce strict JSON without immediate EOS; this does not relax the smoke acceptance checks.
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
- [x] (2026-07-01 10:56 +05:30, user via Antigravity GUI) Confirmed Section 6 reached readiness: the vLLM rotary fallback patch applied, `/v1/models` returned `chaoyinshe/llava-med-v1.5-mistral-7b-hf`, then Section 6.5 failed on smoke case `156` with blank raw output and `completion_tokens=1`.
- [x] (2026-07-01 10:56 +05:30, Codex/GPT-5) Patched the LLaVA-vLLM server defaults to force `--chat-template-content-format openai` and `--generation-config vllm`, and added Section 6.5 smoke diagnostics for finish reason and prompt tokens.
- [x] (2026-07-01 11:26 +05:30, user via Antigravity GUI) Confirmed the post-`717a0ed`/coordinator-head GUI run still fails in Section 6.5: case `156`, 5 images, blank raw response, `finish_reason=stop`, `prompt_tokens=3255`, and `completion_tokens=1`.
- [x] (2026-07-01 11:26 +05:30, Codex/GPT-5) Added a repo-controlled LLaVA-Mistral vLLM chat template with `bos_token`, wired it into notebook-visible `EXTRA_SERVER_ARGS`, and added the same `--chat-template` default in the runtime helper for stale-cell resilience.
- [x] (2026-07-01 11:37 +05:30, user via Antigravity GUI) Confirmed the post-`254631b` GUI run still fails in Section 6.5 with the same immediate EOS signature: blank raw response, `finish_reason=stop`, `prompt_tokens=3255`, and `completion_tokens=1`.
- [x] (2026-07-01 11:37 +05:30, Codex/GPT-5) Added LLaVA-only `request_extra_body={"min_tokens": 16}` through the runtime model config, and made Section 4 plus Section 6.5 print/use that same request extra body.
- [x] (2026-07-01 11:40 +05:30, Codex/GPT-5) Static validation passed for the `min_tokens` correction, and commit `9f4422f` was pushed to `origin/codex/llava-vllm-runtime`.
- [x] (2026-07-01 12:10 +05:30, user via Antigravity GUI) Confirmed a new kernel/session pulled to coordinator head `409ce2b`, Section 4 printed `Request extra body: {'min_tokens': 16}`, Section 6 reached `/v1/models` for `chaoyinshe/llava-med-v1.5-mistral-7b-hf`, and Section 6.5 failed with blank visible output, `finish_reason=length`, `prompt_tokens=3256`, and `completion_tokens=2048`.
- [x] (2026-07-01 12:18 +05:30, Codex/GPT-5) Updated the LLaVA-only request extra body to `min_tokens=16`, `skip_special_tokens=False`, `spaces_between_special_tokens=False`, and `bad_words=['</s>', '<pad>']`; Section 6.5 now prints the unstripped raw response, a `repr(...)` preview, and raw character length.
- [x] (2026-07-01 12:34 +05:30, user via Antigravity GUI) Confirmed the post-`38134f8` Section 6.5 diagnostics ran: request extra body included `skip_special_tokens=False`, `spaces_between_special_tokens=False`, and `bad_words=['</s>', '<pad>']`; raw response was one leading space plus newline tokens, `repr(...)` showed only whitespace, raw char length was `2048`, `finish_reason=length`, `prompt_tokens=3256`, and `completion_tokens=2048`.
- [x] (2026-07-01 12:37 +05:30, Codex/GPT-5) Added vLLM `logit_bias` for this tokenizer's control-whitespace token IDs `12`, `13`, and `16`, and added Section 6.5 whitespace-count diagnostics.
- [x] (2026-07-01, Claude/Opus 4.8) Pivoted from token-hacking to diagnosis: added non-writing Section 6.4 text-only probe (clean params, RadLE JSON task, smoke extra_body) before the 6.5 image smoke to split LM/template fault from image-pathway/checkpoint fault. No server args changed. Set aside the unrelated §7 promote scorer-rebuild edit (stashed) so this push stays diagnostic-only.
- [x] (2026-07-01, user via Workbench Jupyter) Returned 6.4 probe results: A/B (no extra_body) answered cleanly and stopped — LM is fine. C (with extra_body) hit the "1. 1." loop. Image smoke produced REAL diagnoses (Pulmonary tuberculosis, Von Hippel-Lindau syndrome) then hit the same "1. 1." loop. Root cause confirmed: `bad_words=['</s>', '<pad>']` blocks EOS; after finishing its VQA-format numbered-list answer the model cannot stop, and since logit_bias also blocks newlines it repeats "1. ". Image pathway is working. Output format is VQA numbered-list, not JSON.
- [x] (2026-07-01, Claude/Opus 4.8) Removed `bad_words` from LLaVA extra_body (stops blocking EOS). Added VQA-format numbered-list fallback parser to `extract_json_safely` (picks first real diagnosis and score from "1. Diagnosis: N" pattern). Updated EXPECTED_REQUEST_EXTRA_BODY assertion in notebook Section 4.
- [ ] (next, user via Workbench Jupyter) Pull, restart/clear kernel, run Section 6 → 6.4 → 6.5. Expected: probes A/B/C all stop cleanly; image smoke produces numbered-list answer then stops (not loops); 6.5 parses first diagnosis via VQA fallback and passes. Stop before Section 7 and report 6.5 outcome.


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

- Observation: Once the helper-level rotary fallback patch executed, vLLM reached `/v1/models` for the correct HF-format checkpoint, but the smoke generation still terminated immediately.
  Evidence: Section 6 printed `Endpoint ready: http://127.0.0.1:8000/v1/models` and returned `id: chaoyinshe/llava-med-v1.5-mistral-7b-hf`; Section 6.5 then printed `Smoke case: 156 (5 images)`, `Smoke raw response:` blank, `Smoke completion tokens: 1`, and raised `RuntimeError: LLaVA-vLLM smoke failed: empty response.`
  Date/Author: 2026-07-01, user and Codex/GPT-5

- Observation: OpenAI structured content format and vLLM generation defaults did not resolve the immediate EOS.
  Evidence: after the pushed default-args fix, Section 6.5 printed `Smoke case: 156 (5 images)`, `Smoke raw response:` blank, `Smoke finish reason: stop`, `Smoke prompt tokens: 3255`, `Smoke completion tokens: 1`, then raised `RuntimeError: LLaVA-vLLM smoke failed: empty response.`
  Date/Author: 2026-07-01, user and Codex/GPT-5

- Observation: The repo-controlled BOS-prefixed chat template also did not resolve the immediate EOS.
  Evidence: after commit `254631b`, Section 1 pulled the template override, Section 6 reached `/v1/models`, and Section 6.5 still printed `Smoke raw response:` blank, `Smoke finish reason: stop`, `Smoke prompt tokens: 3255`, `Smoke completion tokens: 1`.
  Date/Author: 2026-07-01, user and Codex/GPT-5

- Observation: `min_tokens=16` changed the failure from immediate EOS to a full-length blank/stripped generation, which means token count alone is still not runtime proof.
  Evidence: after a fresh kernel/session at coordinator head `409ce2b`, Section 6.5 printed `Smoke request extra_body: {'min_tokens': 16}`, `Smoke raw response:` blank, `Smoke finish reason: length`, `Smoke prompt tokens: 3256`, `Smoke completion tokens: 2048`, then raised `RuntimeError: LLaVA-vLLM smoke failed: empty response.`
  Date/Author: 2026-07-01, user and Codex/GPT-5

- Observation: The post-`38134f8` raw-response diagnostics proved the blank output is an ordinary whitespace loop.
  Evidence: Section 6.5 printed `Smoke request extra_body: {'min_tokens': 16, 'skip_special_tokens': False, 'spaces_between_special_tokens': False, 'bad_words': ['</s>', '<pad>']}`, `Smoke raw response repr: ' \n\n...`, `Smoke raw response char length: 2048`, `Smoke finish reason: length`, `Smoke prompt tokens: 3256`, and `Smoke completion tokens: 2048`.
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

- Decision: Force LLaVA-vLLM to use OpenAI structured chat-template content and vLLM generation defaults.
  Rationale: The HF checkpoint's chat template expects image blocks rendered before text from structured content, while the latest real failure is no longer server startup but immediate empty generation; making `--chat-template-content-format openai` and `--generation-config vllm` explicit removes two server-side ambiguities without changing the benchmark prompt or image payload.
  Date/Author: 2026-07-01, Codex/GPT-5

- Decision: Override the LLaVA-Med Mistral chat template with a repo-controlled vLLM template that prepends `bos_token`.
  Rationale: The latest request reaches the model with thousands of prompt tokens but stops immediately; the bundled HF template uses Mistral `[INST] ... [/INST]` framing but does not visibly include the Mistral beginning-of-sequence token. A repo-owned template preserves image-first/text-next ordering and adds the BOS token without changing the RadLE prompt or image payload.
  Date/Author: 2026-07-01, Codex/GPT-5

- Decision: Add a LLaVA-only vLLM `min_tokens` request guard and keep the strict smoke gate.
  Rationale: The model is accepting the multimodal request but immediately emits EOS. Setting `min_tokens=16` prevents an EOS-only completion from hiding the model's next-token behavior; it does not make blank output, prompt echo, image-placeholder echo, non-JSON, missing diagnosis, `I don't know`, or invalid Likert acceptable.
  Date/Author: 2026-07-01, Codex/GPT-5

- Decision: Expose stripped/special-token output in the LLaVA-vLLM smoke request before changing the benchmark gate.
  Rationale: The latest GUI run generated 2048 completion tokens but no visible `smoke_text`, so the next evidence must distinguish whitespace-only output from special-token-only output. `skip_special_tokens=False` and `spaces_between_special_tokens=False` make hidden token loops visible, while `bad_words=['</s>', '<pad>']` blocks the most likely EOS/PAD string candidates without weakening the strict JSON diagnosis checks.
  Date/Author: 2026-07-01, Codex/GPT-5

- Decision: Block only control-whitespace token IDs after the post-`38134f8` whitespace-loop proof.
  Rationale: Hugging Face tokenizer metadata for `chaoyinshe/llava-med-v1.5-mistral-7b-hf` identifies the base tokenizer as `LlamaTokenizer`; raw tokenizer JSON maps tab `<0x09>` to `12`, newline `<0x0A>` to `13`, and carriage return `<0x0D>` to `16`. vLLM accepts OpenAI `logit_bias` as string token IDs and clamps values to `[-100, 100]`. Blocking these control-whitespace tokens targets the observed newline loop without blocking normal spaces needed inside diagnosis text.
  Date/Author: 2026-07-01, Codex/GPT-5

- Decision: Stop escalating token-level suppression; add a text-only diagnostic to root-cause the whitespace loop before any further change.
  Rationale: min_tokens, skip_special_tokens/spaces_between_special_tokens, bad_words, and control-whitespace logit_bias have all failed to produce a real diagnosis, and blocking newlines only risks shifting the loop onto spaces. The loop is the same "image not driving generation" signature seen under SGLang, so it may be a broken image pathway in the `chaoyinshe` HF conversion rather than anything a token trick can fix. A non-writing text-only probe (Section 6.4) is the cheapest experiment that separates an LM/template/generation-config fault (plain text also degenerates -> fixable here) from an image-pathway/checkpoint fault (plain text is coherent but images break -> user decision on the checkpoint). Keeping server args unchanged in this push ensures the single GUI run yields an uncontaminated signal.
  Date/Author: 2026-07-01, Claude/Opus 4.8


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
- v15 (2026-07-01 10:56 +05:30, Codex/GPT-5): Recorded that Section 6 now reaches `/v1/models` with the correct model, while Section 6.5 fails on an empty one-token smoke response; added the OpenAI chat-template content-format and vLLM generation-default correction plus extra smoke diagnostics. Runtime proof remains pending.
- v16 (2026-07-01 11:26 +05:30, Codex/GPT-5): Recorded the post-default-args empty response with `finish_reason=stop` and `prompt_tokens=3255`; added the repo-controlled LLaVA-Mistral chat template override with `bos_token`. Runtime proof remains pending.
- v17 (2026-07-01 11:37 +05:30, Codex/GPT-5): Recorded that the template override still produced the same immediate EOS signature; added LLaVA-only `min_tokens=16` request extra body shared by smoke and full benchmark paths. Runtime proof remains pending.
- v18 (2026-07-01 11:40 +05:30, Codex/GPT-5): Reconciled the handoff state after commit `9f4422f` was pushed. The plan now says the min-tokens correction is remote evidence, not local work, and the next action is GUI-only smoke evidence through Section 6.5. Runtime proof remains pending.
- v19 (2026-07-01 12:18 +05:30, Codex/GPT-5): Recorded the post-min-tokens GUI failure at `409ce2b`: full-length blank/stripped output with `finish_reason=length` and 2048 completion tokens. Added the special-token exposure and EOS/PAD bad-word diagnostic correction. Runtime proof remains pending.
- v20 (2026-07-01 12:37 +05:30, Codex/GPT-5): Recorded the post-`38134f8` whitespace-only payload proof and added tokenizer-ID-based `logit_bias` for tab/newline/carriage return plus Section 6.5 whitespace-count diagnostics. Runtime proof remains pending.


## Outcomes & Retrospective

The first static vLLM implementation slice was pushed, and the branch/mapping correction was proven in the GUI at commit `0b90a60`. The helper-level vLLM optional rotary FlashAttention fallback patch moved the run past server startup: GUI evidence now repeatedly shows `/v1/models` returning `chaoyinshe/llava-med-v1.5-mistral-7b-hf`. The next unproven gate is still Section 6.5 runtime generation: immediate-EOS fixes moved the failure from `finish_reason=stop` with one token to `finish_reason=length` with 2048 completion tokens, and the post-`38134f8` diagnostics proved those tokens decode to ordinary whitespace. This commit blocks the observed control-whitespace token loop and adds explicit whitespace counts for the next GUI run. No Workbench/Jupyter smoke or full run has been proven yet. The main reusable lesson is project-specific here: a smoke gate must prove a real benchmark-style JSON diagnosis, not just server readiness, image-token insertion, completion-token growth, or non-special decoded payload length.


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
