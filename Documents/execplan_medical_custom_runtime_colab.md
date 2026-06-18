# Add Medical Custom Runtime Colab Path

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` exists. The prompt-provided AGENTS.md instruction requires an ExecPlan for complex features, multi-step analyses, or significant refactors and prefers `Documents/`.

## Purpose / Big Picture

This work adds a separate experimental Colab path for medical/open vision-language models: `medgemma_1_5_4b`, `llava_med_mistral_7b`, and `internvl3_5_8b`. It must not alter the official RadLE benchmark roster or official notebook. The new path should let the user attach a GCP-backed custom Colab runtime, serve one model at a time through a local OpenAI-compatible vLLM/SGLang endpoint, and write RadLE-shaped outputs to Google Drive.

## Current State

Current state (2026-06-18 23:55 +05:30, Codex/GPT-5): Implementation and local validation are complete, and a local commit exists but has not been pushed because sandbox policy blocked GitHub egress. After the user showed a `g2-standard-8` L4 custom runtime with root disk already 65/94 GB used and empty `/content` disk, the notebook/module were patched to route Hugging Face, Transformers, vLLM, and pip caches under `/content/radle_runtime_cache` and to print server log tails if startup fails. Next: rerun validation, amend the local commit, and ask the user to push or explicitly approve push.

## Locked Facts

- Official benchmark logic stays in `src/radle_benchmark.py`.
- Official default `MODELS` in `src/radle_benchmark.py` must not be changed.
- The official full-run notebook stays `notebooks/RadLE_v1_5_Morning.ipynb`.
- Experimental medical model outputs and downloaded weights must stay out of git.
- The medical custom runtime path should write outputs under the existing Drive dataset root, using a separate run label.
- A single L4 custom runtime should run one served model at a time, not all three simultaneously.
- MedGemma requires accepting Google Health AI terms on Hugging Face and usually needs `HF_TOKEN`.
- The new medical custom runtime notebook has 10 cells, 0 outputs, and 0 executed cells.
- Local dry-run smoke passed for `medgemma_1_5_4b` using the bundled Codex Python runtime and wrote ignored files under `local_smoke/`.
- The custom Colab runtime screenshot showed `g2-standard-8`, NVIDIA L4 x1, Python 3.12, about 22.5 GB GPU RAM, and a tight root disk; model/package caches should stay under `/content/radle_runtime_cache`.

## Do Not Revisit

- Do not merge these medical models into the official ten-model roster during this task. See Decision Log 2026-06-18.
- Do not rewrite `src/radle_benchmark.py` for this side path. See Decision Log 2026-06-18.
- Do not commit generated benchmark outputs, model weights, or confidential images. See README and `.gitignore`.

## Progress

- [x] (2026-06-18 21:45 +05:30, Codex/GPT-5) Read README, official notebook, official benchmark module, jupyter-notebook skill, and current git status.
- [x] (2026-06-18 22:05 +05:30, Codex/GPT-5) Added `src/radle_medical_custom_runtime.py` with model roster, vLLM/SGLang launch helpers, endpoint wait helpers, dry-run fake client, output validation, and a one-model benchmark wrapper.
- [x] (2026-06-18 22:05 +05:30, Codex/GPT-5) Added `notebooks/RadLE_Medical_Custom_Runtime.ipynb` as a thin Colab runner for one selected medical model at a time.
- [x] (2026-06-18 22:05 +05:30, Codex/GPT-5) Updated README with the experimental notebook link and run sequence.
- [x] (2026-06-18 22:05 +05:30, Codex/GPT-5) Validated compile, notebook JSON, output clearing, local dry-run smoke, `git diff --check`, and no official source/notebook diff.
- [x] (2026-06-18 22:05 +05:30, Codex/GPT-5) Created local commit `5bb7b4a Add medical custom runtime Colab`.
- [x] (2026-06-18 23:55 +05:30, Codex/GPT-5) Revalidated cache-routing and log-diagnostic fixes with compile, notebook JSON parse, clear-output check, `git diff --check`, no official-file diff, and a local dry-run smoke.
- [ ] (2026-06-18 23:55 +05:30, Codex/GPT-5) Amend the local commit with cache-routing and log-diagnostic fixes.
- [ ] (2026-06-18 21:45 +05:30, Codex/GPT-5) Push intended source/docs to `origin/main`.

## Surprises & Discoveries

- None yet.

## Decision Log

- Decision: Create a separate module, `src/radle_medical_custom_runtime.py`, rather than changing `src/radle_benchmark.py`.
  Rationale: The official benchmark roster must remain stable, while the medical model path needs endpoint-serving helpers that are experimental.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Decision: The notebook will serve or connect to one model at a time.
  Rationale: G2/L4 custom runtimes are suitable for 4B/7B/8B single-model tests, but simultaneous serving would waste VRAM and increase failure risk.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Decision: Use OpenAI-compatible local endpoints as the integration boundary.
  Rationale: The existing `radle_benchmark.run_benchmark` already speaks OpenAI-style chat completions with image URLs, and vLLM/SGLang can expose that interface.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Decision: Route caches to `/content/radle_runtime_cache` in the notebook and helper module.
  Rationale: The user's GCP-backed Colab runtime has a constrained root disk but a separate empty `/content` volume; model downloads and pip caches should not compete with the root filesystem.
  Date/Author: 2026-06-18, Codex/GPT-5.

## Revision Notes

- v1 (2026-06-18, Codex/GPT-5): Initial plan for the medical custom runtime notebook and module.
- v2 (2026-06-18, Codex/GPT-5): Recorded cache-routing and server-log diagnostic patch after seeing the user's custom runtime disk layout.

## Outcomes & Retrospective

Implementation complete locally. No reusable skill should be created; this is a project-specific Colab/benchmark path.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | Repo instructions require durable planning for multi-step work. | `manual` |
| Notebook creation | `jupyter-notebook` | The user requested a new `.ipynb`; this skill gives notebook structure/validation guidance. | `manual` |
| Module implementation | `none` | Ordinary Python module work around existing helpers. | `none` |
| Validation | `none` | Use compile, JSON parse, focused dry-run smoke, and git checks. | `none` |

## Context And Orientation

The official notebook clones/pulls this private GitHub repo in Colab, mounts Google Drive, imports `src/radle_benchmark.py`, and runs the official model roster. The new notebook should follow the same repo/Drive setup pattern but import a separate module defining a medical experimental roster and local endpoint helpers.

The three first medical/open candidates are:

- `medgemma_1_5_4b` -> `google/medgemma-1.5-4b-it`
- `llava_med_mistral_7b` -> `microsoft/llava-med-v1.5-mistral-7b`
- `internvl3_5_8b` -> `OpenGVLab/InternVL3_5-8B`

## Plan Of Work

Add `src/radle_medical_custom_runtime.py` with the model roster, endpoint wait helpers, vLLM/SGLang launch helpers, a dry-run OpenAI-compatible fake client for local validation, and a `run_medical_model_benchmark` wrapper that calls `radle_benchmark.run_benchmark` with a single explicit model config.

Add `notebooks/RadLE_Medical_Custom_Runtime.ipynb` as a thin Colab runner. It should mount Drive, pull the repo, install endpoint/runtime dependencies only when requested, load `HF_TOKEN` from Colab secrets without printing it, select one model, optionally start a local vLLM/SGLang server, run `TEST_LIMIT=1`, create scorer/audit views, and show paths.

Update README with the experimental notebook link and the one-model-at-a-time workflow.

## Validation And Acceptance

Validation must include:

- `python -m py_compile src\radle_benchmark.py src\radle_medical_custom_runtime.py`
- notebook JSON parse for `notebooks/RadLE_Medical_Custom_Runtime.ipynb`
- focused local dry-run smoke under ignored `local_smoke/`
- `git diff --check`
- `git diff -- src/radle_benchmark.py notebooks/RadLE_v1_5_Morning.ipynb` has no output

Acceptance is a pushed GitHub commit containing the new `.py`, new `.ipynb`, README link, and this plan, with no generated outputs staged.

Actual validation transcript:

    python -m py_compile src\radle_benchmark.py src\radle_medical_custom_runtime.py
    # exited 0

    python -c "import json, pathlib; json.loads(pathlib.Path('notebooks/RadLE_Medical_Custom_Runtime.ipynb').read_text(encoding='utf-8')); print('medical notebook JSON parse OK')"
    medical notebook JSON parse OK

    python -c "import json, pathlib; nb=json.loads(pathlib.Path('notebooks/RadLE_Medical_Custom_Runtime.ipynb').read_text(encoding='utf-8')); print('cells', len(nb['cells'])); print('outputs', sum(len(c.get('outputs', [])) for c in nb['cells'] if c.get('cell_type') == 'code')); print('executed', sum(1 for c in nb['cells'] if c.get('cell_type') == 'code' and c.get('execution_count') is not None))"
    cells 10
    outputs 0
    executed 0

    git diff --check
    # exited 0; warning only that README line endings may be normalized by git

    git diff -- src\radle_benchmark.py notebooks\RadLE_v1_5_Morning.ipynb
    # no output

    C:\Users\thehb\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "<dry-run one-case medgemma smoke>"
    MEDICAL_CUSTOM_RUNTIME_DRY_RUN_OK rows=1

Post-cache-routing validation:

    python -m py_compile src\radle_benchmark.py src\radle_medical_custom_runtime.py
    # exited 0

    python -c "import json, pathlib; json.loads(pathlib.Path('notebooks/RadLE_Medical_Custom_Runtime.ipynb').read_text(encoding='utf-8')); print('medical notebook JSON parse OK')"
    medical notebook JSON parse OK

    python -c "import json, pathlib; nb=json.loads(pathlib.Path('notebooks/RadLE_Medical_Custom_Runtime.ipynb').read_text(encoding='utf-8')); print('cells', len(nb['cells'])); print('outputs', sum(len(c.get('outputs', [])) for c in nb['cells'] if c.get('cell_type') == 'code')); print('executed', sum(1 for c in nb['cells'] if c.get('cell_type') == 'code' and c.get('execution_count') is not None))"
    cells 10
    outputs 0
    executed 0

    git diff --check
    # exited 0; line-ending warnings only

    git diff -- src\radle_benchmark.py notebooks\RadLE_v1_5_Morning.ipynb
    # no output

    C:\Users\thehb\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "<cache-routed dry-run one-case medgemma smoke>"
    MEDICAL_CUSTOM_RUNTIME_DRY_RUN_OK rows=1

## Idempotence And Recovery

The notebook defaults to `TEST_LIMIT=1` and separate run labels, so reruns are safe. If a model server fails to start, stop the server process, restart the Colab runtime, and rerun setup with a single selected model. If MedGemma access fails, accept the Hugging Face terms and set a Colab secret named `HF_TOKEN`.
