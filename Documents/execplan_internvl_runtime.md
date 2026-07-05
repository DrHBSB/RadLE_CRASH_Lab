# Run InternVL3.5 through the isolated vLLM Workbench runtime

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` or `AGENTS.md` file is present in this checkout as of 2026-06-30. The parent SSOT remains `Documents/execplan_medical_workbench_runtime.md`; this child plan owns only InternVL-specific setup, the `flash_attn.ops.triton.rotary` failure, commit `16f6628`, and next Workbench steps.


## Purpose / Big Picture

This plan isolates the resumable InternVL3.5 Workbench path from the active LLaVA work and earlier OctoMed experiment. A future agent should be able to pull the correct notebook commit on Workbench, recover from the partial FlashAttention package failure, start vLLM, and run the 200-case RadLE benchmark only after server readiness is proven.


## Current State

Current state (2026-06-30 21:40 +05:30, Codex/GPT-5): InternVL is not the active current model path; the active path in the parent SSOT is LLaVA-Med SGLang. `notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb` remains the isolated InternVL vLLM notebook. It was created, validated locally, committed, and pushed to `origin/main` as commit `16f6628`. Workbench confirmed the right config from an older local InternVL notebook: selected model `internvl3_5_8b`, run ID `internvl3_5_8b_medical_full_200_cases`, 200 cases, 263 images, vLLM endpoint, `MAX_OUTPUT_TOKENS=2048`, and `MODEL_DTYPE=bfloat16`. vLLM then failed before readiness during InternVL/Qwen3 model initialization because a partial or incompatible `flash_attn` package lacked `flash_attn.ops.triton.rotary`. Commit `16f6628` adds a dependency-cell probe for that exact path and uninstalls `flash-attn`/`flash_attn` only if the package is present but missing the rotary module. Next if InternVL resumes: on Workbench, move any untracked local InternVL notebook aside if it blocks `git pull`, pull latest `main`, reload `notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb` from disk, restart the kernel, rerun dependency/setup and server cells, confirm `/v1/models`, then run the full benchmark.


## Locked Facts

- Parent SSOT for shared dataset/run contracts is `Documents/execplan_medical_workbench_runtime.md`; keep it as the parent and use this file for InternVL-specific work.
- InternVL notebook path is `notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb`.
- InternVL run ID is `internvl3_5_8b_medical_full_200_cases`.
- Model repo is `OpenGVLab/InternVL3_5-8B`.
- InternVL is served through vLLM, not SGLang.
- InternVL uses `bfloat16`.
- `MAX_MODEL_LEN` is `model_runtime.default_max_model_len`, which resolves to 8192 for `internvl3_5_8b` in the helper config.
- InternVL max output tokens remain 2048.
- InternVL tensor parallel size is 1 in the current notebook/helper configuration.
- InternVL is not marked gated in `src/radle_medical_custom_runtime.py`; the HF token cell should only prompt when `model_runtime.requires_hf_token` is true.
- Full RadLE medical run contract remains 200 grouped cases and 263 image files.
- The current known blocker is a partial/incompatible `flash_attn` install: vLLM attempts `flash_attn.ops.triton.rotary` and crashes if that path is absent.
- Commit `16f6628` is pushed to `origin/main` and adds the FlashAttention rotary probe/cleanup.
- Do not run the benchmark until the server reaches `/v1/models`; the observed InternVL failure happened before readiness and before any trustworthy benchmark row.
- InternVL is currently a parked/resumable child path; the parent active path is LLaVA-Med SGLang.


## Do Not Revisit

- Do not treat the InternVL failure as a dataset, GCS, run-ID, or benchmark wrapper problem; config had already printed correctly and the crash was in model initialization. See Decision Log 2026-06-30.
- Do not run the full benchmark until vLLM reaches `/v1/models`. See Decision Log 2026-06-30.
- Do not broaden FlashAttention cleanup beyond the exact rotary-path failure without a new server log. See Decision Log 2026-06-30.
- Do not leave an untracked local Workbench InternVL notebook in place if it blocks `git pull`; move it aside and reload from disk. See Decision Log 2026-06-30.
- When resuming InternVL, keep edits scoped to the InternVL notebook and shared helpers only if a new InternVL log proves the need; do not change active LLaVA or parked OctoMed files unless the user asks. See Decision Log 2026-06-30.


## Progress

- [x] (2026-06-30 21:23 +05:30, user and Codex/GPT-5) Switched active request to preparing `notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb` as the custom InternVL notebook.
- [x] (2026-06-30 21:23 +05:30, Codex/GPT-5) Researched InternVL3.5 against local model config and vLLM support before editing.
- [x] (2026-06-30 21:23 +05:30, Codex/GPT-5) Updated the InternVL notebook to select `internvl3_5_8b`, use vLLM, use `bfloat16`, use helper default max model length, avoid unnecessary HF-token prompting for ungated models, and preserve the 200-case/263-image full-run contract.
- [x] (2026-06-30 21:23 +05:30, user on Workbench and Codex/GPT-5) Workbench confirmed config: `internvl3_5_8b`, run ID `internvl3_5_8b_medical_full_200_cases`, 200 cases, 263 images, vLLM endpoint, and `MODEL_DTYPE=bfloat16`.
- [x] (2026-06-30 21:24 +05:30, user on Workbench and Codex/GPT-5) Workbench attempted the InternVL vLLM server and failed before readiness with `ModuleNotFoundError: No module named 'flash_attn.ops'` while importing `flash_attn.ops.triton.rotary`.
- [x] (2026-06-30 21:24 +05:30, Codex/GPT-5) Patched the InternVL notebook dependency cell to probe `flash_attn.ops.triton.rotary` and uninstall incompatible `flash-attn`/`flash_attn` only if the partial package would make vLLM crash.
- [x] (2026-06-30 21:24 +05:30, Codex/GPT-5) Validated notebook JSON/code cells and helper module compilation, then pushed commit `16f6628` to `origin/main`.
- [ ] (future InternVL Workbench session, user/Codex) Move aside any blocking untracked local InternVL notebook, pull latest `main`, restart the kernel, reload the InternVL notebook from disk, rerun dependency and server cells, confirm `/v1/models`, and only then start the full 200-case benchmark.


## Surprises & Discoveries

- Observation: InternVL/vLLM reached model initialization but failed on a partial or incompatible FlashAttention package.
  Evidence: The server log entered `vllm/model_executor/models/internvl.py`, then Qwen3 rotary embedding construction, then failed importing `flash_attn.ops.triton.rotary` with `ModuleNotFoundError: No module named 'flash_attn.ops'`.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Observation: The InternVL config/run contract was correct before the crash.
  Evidence: Workbench printed `internvl3_5_8b`, model-scoped run ID, 200 cases, 263 images, vLLM endpoint, `MAX_OUTPUT_TOKENS=2048`, and `MODEL_DTYPE=bfloat16` before server launch failed.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Observation: A partial FlashAttention install can be worse than no FlashAttention install in this runtime.
  Evidence: vLLM attempted to import a FlashAttention rotary module that was absent. The intended fix is to remove the partial package only when that exact path is missing so vLLM can fall back.
  Date/Author: 2026-06-30, Codex/GPT-5


## Decision Log

- Decision: Keep InternVL in its own Workbench notebook.
  Rationale: InternVL has its own vLLM dtype, token-gating, max-length, and FlashAttention dependency behavior that should not affect LLaVA, OctoMed, or the normal Workbench notebook.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Decision: Use `bfloat16` for InternVL.
  Rationale: The helper/model-specific notebook marks `internvl3_5_8b` in the bfloat16 path, and Workbench config printed `MODEL_DTYPE=bfloat16`.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: Gate Hugging Face token prompting on `model_runtime.requires_hf_token`.
  Rationale: InternVL is not marked gated in the local roster, so the notebook should not prompt for a token unless metadata requires it.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: Treat missing `flash_attn.ops.triton.rotary` as an incompatible optional dependency and uninstall FlashAttention only when the exact probe fails.
  Rationale: The crash came from vLLM selecting a broken installed FlashAttention path. Removing it narrowly should let vLLM use fallback behavior without broad dependency churn.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: Keep using `main` for this notebook handoff.
  Rationale: The user is using `git pull` directly on Workbench, so a pushed commit on `main` is the simplest recovery path.
  Date/Author: 2026-06-30, Codex/GPT-5


## Revision Notes

- v1 (2026-06-30 21:26 +05:30, Codex/GPT-5): Split InternVL-specific active runtime work out of the parent Workbench ExecPlan. Recorded current commit `16f6628`, the FlashAttention rotary failure, and the next Workbench pull/reload/start steps.
- v2 (2026-06-30 21:40 +05:30, Codex/GPT-5): Reconciled the child plan with the parent LLaVA-active state. InternVL is now recorded as a parked/resumable path from commit `16f6628`, not the active current run.


## Outcomes & Retrospective

Outcome so far: InternVL has not yet produced a full RadLE run. The model-specific notebook exists and the first server blocker has a narrow pushed dependency fix in commit `16f6628`.

Remaining work: when the user returns to InternVL, execute the Workbench recovery path from the pushed notebook and verify server readiness. If a new failure appears, patch only the dependency/setup behavior that the new log proves.

Reusable lesson: for optional acceleration libraries, probe the exact module path the serving stack imports; a top-level package import is not enough. This may be reusable, but no global skill update has been made.


## Suggested Skills By Phase

| Workflow Gate | Skill To Use | Why | Activation |
| --- | --- | --- | --- |
| Maintaining this plan | `execplan` | This file is the InternVL-specific living handoff. | `auto-suggest` |
| Editing the InternVL notebook | `jupyter-notebook` | Notebook JSON and code cells must parse and compile after edits. | `auto-suggest` |
| Model/runtime research | `hugging-face:hf-cli` or primary-source web research | Use only if a future failure depends on model files, vLLM support, or revision-specific metadata. | `manual` |
| Live Workbench run guidance | `none` | Interpret pasted logs directly and keep instructions tied to current output. | `none` |
| Full-run audit after success | `data-analytics:analyze-data-quality` only if counts or repair outputs conflict | Use file/CSV audits, not notebook logs alone. | `manual` |


## Context And Orientation

The official benchmark path is `notebooks/RadLE_v1_5_Morning.ipynb` plus `src/radle_benchmark.py`. Do not change it for InternVL. The parent medical Workbench plan is `Documents/execplan_medical_workbench_runtime.md`. This child file covers only `notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb`.

Workbench run contract inherited from the parent:

- Dataset root: `/home/jupyter/radle_dataset/RadLE v2 Dataset`
- Frozen dataset GCS URI: `gs://radle-medical-data-toronto/datasets/radle-v2-frozen-2026-06-29/RadLE v2 Master Data`
- Results GCS root: `gs://radle-medical-data-toronto/runs`
- Full run: 200 grouped cases and 263 image files
- Run label base: `medical_full_200_cases`
- InternVL run ID: `internvl3_5_8b_medical_full_200_cases`


## Plan Of Work

First, only resume this plan when the user explicitly returns to InternVL. Then recover Workbench to the pushed notebook. If `git pull` refuses because a local untracked `notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb` exists, move that local file aside outside the repo or to a clearly named backup, pull latest `main`, reload the notebook from disk, and restart the kernel.

Second, rerun dependency/setup cells from the pulled notebook. The FlashAttention probe must check `flash_attn.ops.triton.rotary`. If `flash_attn` exists but that path is absent, the cell should uninstall `flash-attn`/`flash_attn` and print the post-cleanup spec.

Third, start vLLM and wait for `/v1/models`. Do not run the benchmark cell until readiness succeeds.

Fourth, if readiness succeeds, run the full benchmark with `RESUME=True`, then audit actual output files before any repair, promotion, export, or sync.

Fifth, if a new server failure appears, capture the last server log lines, update this plan, and patch only the narrow cause shown by that log.


## Milestones

Milestone 1, Workbench synchronization, uses `none`: Workbench is on commit `16f6628` or newer, local untracked notebook conflicts are moved aside, and the open notebook is reloaded from disk.

Milestone 2, dependency recovery, uses `none`: the dependency cell proves either FlashAttention rotary exists or partial FlashAttention has been removed before server launch.

Milestone 3, live vLLM readiness, uses `none`: vLLM reaches `/v1/models` for `internvl3_5_8b`.

Milestone 4, completed-run audit, uses `data-analytics:analyze-data-quality` optionally: only after 200 output rows exist, audit actual files, row counts, repair targets, and manifests.


## Concrete Steps (Commands)

Local validation from repo root:

    git status --short --branch
    git rev-parse --short HEAD
    rg -n "internvl3_5_8b|SELECTED_MODEL_NAME|SERVER_ENGINE|BF16_MODELS|MODEL_DTYPE|MAX_MODEL_LEN|requires_hf_token|flash_attn.ops.triton.rotary|flash-attn|uninstall" notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb src/radle_medical_custom_runtime.py

Expected key facts:

    selected_model: internvl3_5_8b
    server_engine: vllm
    model_dtype: bfloat16
    max_model_len: model_runtime.default_max_model_len
    flash_attn.ops.triton.rotary

Validate helper modules:

    py -3.11 -m py_compile src/radle_medical_custom_runtime.py src/radle_benchmark.py

Expected: no output and exit code 0.

Validate notebook code cells:

    py -3.11 -c "import json,pathlib; p=pathlib.Path('notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb'); nb=json.loads(p.read_text(encoding='utf-8-sig')); cells=[c for c in nb['cells'] if c.get('cell_type')=='code']; [compile(''.join(c.get('source',[])), f'internvl_cell_{i}', 'exec') for i,c in enumerate(cells,1)]; print('compiled InternVL code cells', len(cells))"

Expected: prints `compiled InternVL code cells` followed by a positive count.

Workbench pull recovery if an untracked local notebook blocks pull:

    cd /home/jupyter/RadLE_CRASH_Lab
    mv notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb /home/jupyter/RadLE_Medical_Workbench_Internvl_Runtime.local_before_16f6628.ipynb
    git pull
    git rev-parse --short HEAD

Expected:

    16f6628

Workbench FlashAttention probe before server launch:

    /opt/micromamba/bin/python3 -c "import importlib.util; print(importlib.util.find_spec('flash_attn')); print(importlib.util.find_spec('flash_attn.ops.triton.rotary'))"

Expected after the dependency cell: either `flash_attn` is absent, or `flash_attn.ops.triton.rotary` is present. If `flash_attn` exists and the rotary path is absent, the patched notebook should uninstall it before server startup.


## Validation And Acceptance

Local acceptance:

- The InternVL notebook parses and compiles.
- Helper modules compile.
- Grep confirms `internvl3_5_8b`, vLLM, `bfloat16`, helper default max model length, gated-token prompt logic, and FlashAttention rotary probe/cleanup.
- Parent ExecPlan, LLaVA notebook, OctoMed notebook, and official benchmark notebook are not edited as part of InternVL recovery unless the user explicitly asks.

Live acceptance:

- Workbench is on commit `16f6628` or newer.
- Notebook is reloaded from disk and kernel restarted.
- Config printout shows `internvl3_5_8b`, `medical_full_200_cases`, model-scoped run ID, expected 200 cases, expected 263 image files, `MAX_OUTPUT_TOKENS=2048`, and `bfloat16`.
- Dependency/setup cells run the FlashAttention rotary probe before server startup.
- Server reaches `/v1/models`.
- Benchmark cell validates exactly 200 output rows.
- Audit reports 200 rows, 200 unique cases, no missing/extra case IDs, and zero repair targets before promotion. If repair targets exist, inspect them before repair.
- Completed-run claims are verified by actual files: final manifest, final CSV row count, public summary, GCS object listing, and local mirror when requested.


## Idempotence And Recovery

If Workbench has a local untracked `notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb` and `git pull` refuses, move it aside before pulling. Do not overwrite it blindly.

If the old dependency cell already failed on `flash_attn.ops.triton.rotary`, restart the kernel after pulling `16f6628` or newer and rerun dependency/setup cells from the top.

If `flash_attn` remains installed and the rotary module remains missing after the dependency cell, do not start vLLM. Patch the cleanup cell or manually uninstall the partial package in the same environment, then repeat the probe.

If `nvidia-smi` shows no `VLLM::EngineCore`, the server is dead; rerun the server cell before rerunning the benchmark.

If a full run is interrupted after readiness, keep the same `RUN_ID`, `RUN_LABEL_BASE`, and `RESUME=True`.


## Artifacts And Notes

InternVL config transcript before the FlashAttention fix:

    Selected model: internvl3_5_8b
    Run label base: medical_full_200_cases
    Model-scoped run ID: internvl3_5_8b_medical_full_200_cases
    Test limit: full
    Expected cases this run: 200
    Expected image files this run: 263
    Multi-image grouped cases: 50
    Dataset GCS URI: gs://radle-medical-data-toronto/datasets/radle-v2-frozen-2026-06-29/RadLE v2 Master Data
    Run folder: /home/jupyter/radle_dataset/RadLE v2 Dataset/Runs/internvl3_5_8b_medical_full_200_cases
    Raw results CSV: /home/jupyter/radle_dataset/RadLE v2 Dataset/Runs/internvl3_5_8b_medical_full_200_cases/raw/results.csv
    Max output tokens: 2048
    Model dtype: bfloat16
    Endpoint: http://127.0.0.1:8000/v1

InternVL server failure transcript before commit `16f6628`:

    Starting vllm server for internvl3_5_8b...
    Server process started. Log path: /home/jupyter/internvl3_5_8b_vllm_server.log
    ModuleNotFoundError: No module named 'flash_attn.ops'

InternVL dependency fix note:

    Commit 16f6628 probes importlib.util.find_spec('flash_attn.ops.triton.rotary') after vLLM install/import.
    If flash_attn exists but that rotary path is missing, the notebook uninstalls flash-attn and flash_attn, then prints the post-cleanup flash_attn spec.
    The intent is to let vLLM use its fallback path instead of crashing on a partial FlashAttention package.


## Interfaces And Dependencies

- `notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb` owns InternVL setup, FlashAttention rotary probe/cleanup, and server launch.
- `src/radle_medical_custom_runtime.py` provides model metadata and shared server helpers.
- `src/radle_benchmark.py` provides audit, repair, promotion, and export helpers.
- vLLM must be launched with trust-remote-code when `model_runtime.needs_trust_remote_code` is true.
- The FlashAttention cleanup is intentionally narrow: remove `flash-attn` only when `flash_attn` exists and `flash_attn.ops.triton.rotary` is absent.
