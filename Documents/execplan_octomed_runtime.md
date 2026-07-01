# Run OctoMed through the isolated vLLM Workbench runtime

> **SUPERSEDED (2026-07-02): OctoMed is pivoting to Ollama, not vLLM.** After the
> LLaVA-Med vLLM/HF route died and the Ollama GGUF path worked end-to-end, OctoMed
> follows the same Ollama recipe. Use `Documents/handoff_octomed_ollama_next_session.md`
> and the recipe in `Documents/execplan_medical_vlm_ollama_runtime.md`. Keep this
> file only for OctoMed model facts (Qwen2.5-VL, 200 cases / 263 images, case 156 =
> only 5-image case) and the history of the vLLM `llguidance` dead end. Do NOT
> reopen the vLLM route unless the user explicitly asks.

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` or `AGENTS.md` file is present in this checkout as of 2026-06-30. The parent SSOT remains `Documents/execplan_medical_workbench_runtime.md`; this child plan owns only OctoMed/vLLM-specific setup, failures, and recovery steps.


## Purpose / Big Picture

This plan isolates OctoMed work from the broader Workbench model sequence. A future agent should be able to return to `OctoMed/OctoMed-7B`, understand why `--limit-mm-per-prompt image=5` was wrong, why the later `llguidance` failure was a dependency-cleanup regression rather than model download trouble, and patch the OctoMed notebook without re-opening LLaVA or InternVL decisions.


## Current State

Current state (2026-06-30 21:40 +05:30, Codex/GPT-5): OctoMed is not the active current run; the active path in the parent SSOT is LLaVA-Med SGLang. OctoMed remains isolated in `notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb`. Commit `65a774bd6c4be214cbcc70318ba2cbfbe7efc73e` (`65a774b`) was pushed and Workbench pulled it. That fixed the first vLLM CLI failure by changing `--limit-mm-per-prompt image=5` to JSON `--limit-mm-per-prompt '{"image": 5}'` and added a non-writing case-156 smoke for the only 5-image RadLE case. The next Workbench attempt got past CLI parsing but failed before model download/load because the dependency cleanup removed `llguidance`, which vLLM 0.23.0 imports during OpenAI server startup. The local worktree currently has an uncommitted OctoMed notebook candidate that removes `llguidance`, `tilelang`, `tokenspeed-mla`, and `outlines` from the uninstall list, but that candidate is not validated, committed, or pushed, and it still needs a post-cleanup `vllm`/`llguidance` import probe or reinstall guard before another Workbench retry. Next if OctoMed resumes: inspect the local candidate diff, complete the dependency/setup guard, validate locally, commit, push, then rerun on Workbench from a restarted kernel.


## Locked Facts

- Parent SSOT for shared dataset/run contracts is `Documents/execplan_medical_workbench_runtime.md`; do not edit it for this child split unless the user explicitly asks.
- OctoMed notebook path is `notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb`.
- OctoMed run ID is `octomed_7b_medical_full_200_cases`.
- Model repo is `OctoMed/OctoMed-7B`.
- OctoMed is served through vLLM, not SGLang.
- OctoMed uses `bfloat16`, tensor parallel size 2, GPU memory utilization 0.8, max model length 8192, and max output tokens 2048.
- OctoMed sampling settings are temperature 0.6 and top-p 0.95.
- The full RadLE medical run has 200 grouped cases and 263 image files.
- RadLE case `156` is the only 5-image grouped case: `156.1.png`, `156.2.png`, `156.3.png`, `156.4.png`, and `156.5.png`.
- The vLLM image-limit argument must be JSON: `--limit-mm-per-prompt '{"image": 5}'`.
- The rejected `image=5` form was a vLLM CLI syntax error, not an OctoMed capacity or model-download failure.
- vLLM 0.23.0 imports `llguidance` during OpenAI server startup.
- vLLM 0.23.0 depends on shared packages including `llguidance >=1.7.0,<1.8.0`, `outlines_core==0.2.14`, `tilelang==0.1.9`, and `tokenspeed-mla==0.1.2`.
- Do not remove those vLLM shared dependencies just to silence stale SGLang resolver warnings.
- The current local worktree may contain an uncommitted OctoMed notebook candidate edit; inspect it before deciding whether it is usable.
- As of 2026-06-30 21:40 +05:30, the observed local candidate only changes the uninstall list; it is not a complete accepted fix until notebook compile checks and a post-cleanup vLLM import probe pass.


## Do Not Revisit

- Do not diagnose `--limit-mm-per-prompt image=5` as an image-count cap issue; it was invalid CLI syntax. See Decision Log 2026-06-30.
- Do not diagnose missing `llguidance` as a model download failure; vLLM exited before download/load while importing server modules. See Decision Log 2026-06-30.
- Do not use the LLaVA/SGLang dependency cleanup list for OctoMed/vLLM. See Decision Log 2026-06-30.
- Do not delete `llguidance`, `outlines_core`, `tilelang`, or `tokenspeed-mla` from the OctoMed vLLM environment unless new evidence proves a different vLLM version no longer needs them. See Decision Log 2026-06-30.
- Do not start the full benchmark until `/v1/models` is ready and the case-156 smoke has passed. See Decision Log 2026-06-30.


## Progress

- [x] (2026-06-30 21:16 +05:30, Codex/GPT-5) Researched OctoMed against official Hugging Face/arXiv/vLLM/Qwen sources and prepared `notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb` as an isolated vLLM/Qwen2.5-VL notebook.
- [x] (2026-06-30 21:16 +05:30, user and Codex/GPT-5) Workbench printed the expected OctoMed config: 200 cases, 263 images, max 5 images per case, `bfloat16`, tensor parallel size 2, GPU utilization 0.8, max model length 8192, temperature 0.6, top-p 0.95, and endpoint `http://127.0.0.1:8000/v1`.
- [x] (2026-06-30 21:16 +05:30, user and Codex/GPT-5) Captured the first OctoMed server failure: vLLM rejected `--limit-mm-per-prompt image=5` because that argument is parsed with JSON loading.
- [x] (2026-06-30 21:16 +05:30, Codex/GPT-5) Patched the OctoMed notebook to use JSON `{"image": 5}`, added a non-writing case-156 smoke, validated locally, and pushed commit `65a774bd6c4be214cbcc70318ba2cbfbe7efc73e`.
- [x] (2026-06-30 21:16 +05:30, user and Codex/GPT-5) Workbench pulled commit `65a774b`; the server got past CLI parsing but exited before readiness with `ModuleNotFoundError: No module named 'llguidance'`.
- [x] (2026-06-30 21:16 +05:30, Codex/GPT-5) Researched vLLM 0.23.0 requirements and concluded the cleanup must preserve vLLM shared dependencies and reinstall/probe pinned vLLM if imports fail.
- [x] (2026-06-30 21:40 +05:30, Codex/GPT-5) Inspected the current local OctoMed candidate diff: it preserves the vLLM shared packages by removing `llguidance`, `tilelang`, `tokenspeed-mla`, and `outlines` from the cleanup uninstall list, but it has not yet added/proved a post-cleanup import guard.
- [ ] (future OctoMed session, Codex/GPT-5) Complete the candidate by preserving vLLM shared dependencies, verifying `vllm` and `llguidance` imports after cleanup, adding a pinned-vLLM reinstall fallback if that probe fails, validating locally, committing, and pushing.
- [ ] (future OctoMed Workbench session, user/Codex) Pull the fix, restart/reload the OctoMed notebook, rerun dependency/setup cells, confirm `/v1/models`, run the case-156 smoke, and only then start the full 200-case benchmark.


## Surprises & Discoveries

- Observation: vLLM 0.23.0 rejects the `image=5` form before model startup.
  Evidence: Workbench server log ended with `api_server.py: error: argument --limit-mm-per-prompt: Value image=5 cannot be converted to <function loads ...>` and exit code 2.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Observation: The `5` image limit is relevant because RadLE groups multiple images into a single case prompt.
  Evidence: Workbench config showed 50 multi-image grouped cases, max 5 images per grouped case, and case 156 as the only 5-image example.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Observation: The later `llguidance` failure is local dependency damage, not OctoMed download/load failure.
  Evidence: The server failed while importing `vllm/v1/structured_output/backend_guidance.py`, before any Hugging Face download or safetensors loading, with `ModuleNotFoundError: No module named 'llguidance'`.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Observation: SGLang conflict cleanup and vLLM cleanup cannot share a delete list.
  Evidence: vLLM 0.23.0 requirements include `llguidance`, `outlines_core`, `tilelang`, and `tokenspeed-mla`, while the attempted cleanup removed some of those packages after SGLang resolver warnings.
  Date/Author: 2026-06-30, Codex/GPT-5


## Decision Log

- Decision: Keep OctoMed in its own notebook, not in the normal Workbench notebook.
  Rationale: OctoMed has Qwen2.5-VL/vLLM-specific arguments, sampling settings, pixel processor kwargs, and a case-156 smoke that should not affect other model paths.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Decision: Use JSON for `--limit-mm-per-prompt`.
  Rationale: vLLM 0.23.0 parses the argument with JSON loading; `image=5` fails before model startup.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: Keep `{"image": 5}` for the RadLE full run and smoke-test case 156.
  Rationale: The dataset includes one grouped case with five images, so the server must accept up to five image items in one prompt.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: Preserve vLLM shared dependencies in OctoMed setup.
  Rationale: Removing `llguidance` breaks vLLM OpenAI server imports before model download/load.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: If vLLM imports fail after cleanup, reinstall the pinned vLLM wheel and repeat the import probe before server launch.
  Rationale: Continuing to launch the server with a broken vLLM import wastes Workbench time and produces a misleading "server did not become ready" failure.
  Date/Author: 2026-06-30, Codex/GPT-5


## Revision Notes

- v1 (2026-06-30 21:26 +05:30, Codex/GPT-5): Split OctoMed-specific vLLM JSON image-limit and `llguidance` cleanup work out of the parent Workbench ExecPlan. Parent remains the SSOT for shared dataset and run-contract facts.
- v2 (2026-06-30 21:40 +05:30, Codex/GPT-5): Reconciled the child plan with the parent LLaVA-active state and recorded the uncommitted OctoMed cleanup candidate as incomplete pending import probes, validation, commit, and push.


## Outcomes & Retrospective

Outcome so far: OctoMed has not produced a full RadLE run. The server syntax issue is solved in commit `65a774b`; the current known blocker is dependency cleanup that removed `llguidance`.

Remaining work: complete and validate the existing local OctoMed dependency-cleanup candidate before another Workbench retry. Do not resume OctoMed by rerunning the existing pushed notebook or the unvalidated local candidate without the import probe/reinstall guard.

Reusable lesson: warnings from one serving engine should not drive package removal for another serving engine unless that other engine's import probe still passes afterward. This may be reusable, but no global skill update has been made.


## Suggested Skills By Phase

| Workflow Gate | Skill To Use | Why | Activation |
| --- | --- | --- | --- |
| Maintaining this plan | `execplan` | This file is the OctoMed-specific living handoff. | `auto-suggest` |
| Editing the OctoMed notebook | `jupyter-notebook` | Notebook JSON and code cells must parse and compile after edits. | `auto-suggest` |
| vLLM dependency research | `hugging-face:hf-cli` or primary-source web research | Use only if a future vLLM version changes requirements. | `manual` |
| Live Workbench run guidance | `none` | Interpret pasted logs directly and keep instructions tied to current output. | `none` |
| Full-run audit after success | `data-analytics:analyze-data-quality` only if counts or repair outputs conflict | Use file/CSV audits, not notebook logs alone. | `manual` |


## Context And Orientation

The official benchmark path is `notebooks/RadLE_v1_5_Morning.ipynb` plus `src/radle_benchmark.py`. Do not change it for OctoMed. The parent medical Workbench plan is `Documents/execplan_medical_workbench_runtime.md`. This child file covers only `notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb`.

Workbench run contract inherited from the parent:

- Dataset root: `/home/jupyter/radle_dataset/RadLE v2 Dataset`
- Frozen dataset GCS URI: `gs://radle-medical-data-toronto/datasets/radle-v2-frozen-2026-06-29/RadLE v2 Master Data`
- Results GCS root: `gs://radle-medical-data-toronto/runs`
- Full run: 200 grouped cases and 263 image files
- Run label base: `medical_full_200_cases`
- OctoMed run ID: `octomed_7b_medical_full_200_cases`


## Plan Of Work

First, inspect the current local OctoMed notebook diff before editing. There is already an uncommitted candidate cleanup change in the worktree; treat it as a starting point, not as a validated fix.

Second, patch only the dependency/setup cell. The cleanup list may remove stale `sglang`, `pandas-profiling`, or `moviepy` if needed, but must not remove `llguidance`, `outlines_core`, `tilelang`, or `tokenspeed-mla`.

Third, add or preserve a post-cleanup import probe:

    import vllm
    import llguidance

If that probe fails, reinstall the pinned vLLM wheel and repeat the probe before server launch. The current local candidate is incomplete until this guard exists and notebook code cells compile.

Fourth, keep the JSON image limit and case-156 smoke unchanged.

Fifth, validate locally, commit, push, and only then ask Workbench to pull/restart/reload.


## Milestones

Milestone 1, OctoMed dependency repair, uses `jupyter-notebook`: the notebook preserves vLLM shared dependencies and proves `vllm`/`llguidance` imports after cleanup.

Milestone 2, live OctoMed server readiness, uses `none`: Workbench dependency/setup cells pass, the server reaches `/v1/models`, and case-156 smoke completes without writing to the full raw CSV.

Milestone 3, completed-run audit, uses `data-analytics:analyze-data-quality` optionally: only after 200 output rows exist, audit actual files, row counts, repair targets, and manifests.


## Concrete Steps (Commands)

Inspect the OctoMed notebook and local diff:

    git status --short -- notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb
    git diff -- notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb
    rg -n "octomed_7b|OCTOMED_|limit-mm-per-prompt|llguidance|outlines_core|tilelang|tokenspeed-mla|vllm_conflict_cleanup_packages|OCTOMED_SMOKE_CASE_ID" notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb

Expected key facts after the fix:

    SELECTED_MODEL_NAME = "octomed_7b"
    --limit-mm-per-prompt
    {"image": 5}
    OCTOMED_SMOKE_CASE_ID = "156"
    llguidance is not in the uninstall list

Validate helper modules:

    py -3.11 -m py_compile src/radle_medical_custom_runtime.py src/radle_benchmark.py

Expected: no output and exit code 0.

Validate notebook code cells:

    py -3.11 -c "import json,pathlib; p=pathlib.Path('notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb'); nb=json.loads(p.read_text(encoding='utf-8-sig')); cells=[c for c in nb['cells'] if c.get('cell_type')=='code']; [compile(''.join(c.get('source',[])), f'octomed_cell_{i}', 'exec') for i,c in enumerate(cells,1)]; print('compiled OctoMed code cells', len(cells))"

Expected: prints `compiled OctoMed code cells` followed by a positive count.

Dependency-guard extraction:

    py -3.11 -c "import json,pathlib,re; p=pathlib.Path('notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb'); src='\n'.join(''.join(c.get('source',[])) for c in json.loads(p.read_text(encoding='utf-8-sig'))['cells'] if c.get('cell_type')=='code'); block=re.search(r'vllm_conflict_cleanup_packages\\s*=\\s*\\[(.*?)\\]', src, re.S); print(block.group(0) if block else 'NO CLEANUP BLOCK FOUND'); [print('forbidden cleanup term present:', term) for term in ['llguidance','outlines_core','tilelang','tokenspeed-mla'] if block and term in block.group(1)]"

Expected: cleanup block, if present, does not report forbidden vLLM dependency terms.

Workbench import probe before server launch:

    /opt/micromamba/bin/python3 -c "import vllm, llguidance; print('vllm import OK')"

Expected: prints `vllm import OK`.


## Validation And Acceptance

Local acceptance:

- The OctoMed notebook parses and compiles.
- Helper modules compile.
- Grep confirms `octomed_7b`, JSON `{"image": 5}`, and case-156 smoke remain.
- The cleanup list does not remove `llguidance`, `outlines_core`, `tilelang`, or `tokenspeed-mla`.
- Dependency setup verifies `vllm` and `llguidance` imports before server launch.

Live acceptance:

- Workbench pulls the intended commit and reloads the OctoMed notebook from disk.
- Config printout shows `octomed_7b`, 200 cases, 263 images, `bfloat16`, tensor parallel size 2, max model length 8192, temperature 0.6, top-p 0.95, and JSON `--limit-mm-per-prompt`.
- Dependency/setup cells prove `vllm` and `llguidance` import.
- Server reaches `/v1/models`.
- Case-156 smoke completes before the full benchmark.
- A completed run is not claimed until actual CSV/manifests show 200 rows and 200 unique cases.


## Idempotence And Recovery

If the old dependency cell already removed `llguidance`, restart the kernel after pulling the fixed notebook, rerun dependency/setup, and wait for the import probe to pass.

If `llguidance` remains missing, reinstall the pinned vLLM wheel from the notebook dependency path and repeat the probe before starting the server.

If Workbench asks whether to reload from disk after `git pull`, reload from disk and restart the kernel.

If the server reaches readiness but the benchmark is interrupted, keep the same `RUN_ID`, `RUN_LABEL_BASE`, and `RESUME=True`.


## Artifacts And Notes

OctoMed config transcript from Workbench:

    Selected model: octomed_7b
    Model ID: OctoMed/OctoMed-7B
    Model-scoped run ID: octomed_7b_medical_full_200_cases
    Expected cases this run: 200
    Expected image files this run: 263
    Multi-image grouped cases: 50
    Max images per grouped case: 5
    Max output tokens: 2048
    OctoMed sampling temperature: 0.6
    OctoMed top_p: 0.95
    Tensor parallel size: 2
    GPU memory utilization: 0.8
    Max model len: 8192
    Model dtype: bfloat16

First OctoMed failure:

    api_server.py: error: argument --limit-mm-per-prompt: Value image=5 cannot be converted to <function loads ...>

Fixed argument form:

    --limit-mm-per-prompt '{"image": 5}'

Second OctoMed failure after commit `65a774b`:

    ModuleNotFoundError: No module named 'llguidance'

Dependency research note:

    vLLM 0.23.0 requirements include llguidance >=1.7.0,<1.8.0 and outlines_core==0.2.14.
    vLLM 0.23.0 CUDA requirements include tilelang==0.1.9 and tokenspeed-mla==0.1.2.


## Interfaces And Dependencies

- `notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb` owns OctoMed setup, JSON multimodal limit, case-156 smoke, and server launch.
- `src/radle_medical_custom_runtime.py` provides model metadata and shared server helpers.
- `src/radle_benchmark.py` provides audit, repair, promotion, and export helpers.
- vLLM OpenAI server must be importable before launch: `import vllm, llguidance`.
- The server must receive `--trust-remote-code` through the helper when required by model metadata.
