# Add Medical Custom Runtime Colab Path

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` exists. The prompt-provided AGENTS.md instruction requires an ExecPlan for complex features, multi-step analyses, or significant refactors and prefers `Documents/`.

## Purpose / Big Picture

This work adds a separate experimental Colab path for medical/open vision-language models: `medgemma_1_5_4b`, `llava_med_mistral_7b`, and `internvl3_5_8b`. It must not alter the official RadLE benchmark roster or official notebook. The new path should let the user attach a GCP-backed custom Colab runtime, serve one model at a time through a local OpenAI-compatible vLLM/SGLang endpoint, and write RadLE-shaped outputs to Google Drive.

## Current State

Current state (2026-06-18 23:59 +05:30, Codex/GPT-5): Initial implementation was pushed to `origin/main` as commit `7769c86`. The user then tested in Colab Enterprise and hit `NotImplementedError: google.colab.drive.mount is not supported in Colab Enterprise`, which prevented the import cell from running and caused a later `NameError: name 'medical_runtime' is not defined`. The notebook now keeps the first code cell as GitHub clone/pull/path setup only, moves storage resolution to cell 4, and supports Colab Enterprise via `DATASET_ROOT_OVERRIDE` or `RADLE_DATASET_ROOT`. Local validation passed; next action is commit and push this follow-up.

Current state (2026-06-27 09:10 +05:30, Codex/GPT-5): The user ran the Colab dependency cell and saw pip dependency-conflict warnings after forced upgrades replaced Colab-pinned packages such as `pandas`, `google-auth`, and `google-genai`. Cell 2 now installs required packages without `--upgrade`, preserving Colab's pinned stack unless a package is missing. Local validation passed with notebook JSON parse and `git diff --check`.

Current state (2026-06-27 09:28 +05:30, Codex/GPT-5): The user then hit `ImportError: libcudart.so.13` when starting vLLM on free Colab T4, meaning the plain vLLM package resolved to a CUDA-13 wheel while the runtime has CUDA 12. Cell 2 now installs the explicit vLLM `0.23.0+cu129` wheel from the upstream release, and cell 4 defaults the first T4 smoke to `MAX_MODEL_LEN = 4096` with `--dtype float16`.

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
- Initial medical custom runtime implementation was pushed to `origin/main` as `7769c86 Add medical custom runtime Colab`.
- Colab Enterprise cannot use `google.colab.drive.mount()`; Enterprise runs need a Cloud Storage/local dataset path set in cell 4 or `RADLE_DATASET_ROOT`.
- The first code cell is now intentionally GitHub clone/pull/path setup only, so the user can rerun it first after each pushed change.
- Notebook dependency setup must not force-upgrade Colab's preinstalled stack; install missing packages without `--upgrade` unless a specific compatibility issue proves a pin is needed.
- Free Colab T4 should use CUDA-12-compatible vLLM packages and conservative first-smoke settings; the first MedGemma T4 run uses `MAX_MODEL_LEN = 4096` and `--dtype float16`.

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
- [x] (2026-06-18 23:55 +05:30, Codex/GPT-5) Pushed initial medical custom runtime implementation to `origin/main` as `7769c86`.
- [x] (2026-06-18 23:59 +05:30, Codex/GPT-5) Reproduced the user-facing failure chain from the shared traceback: `drive.mount()` fails first in Colab Enterprise, then `medical_runtime` is undefined because the import cell was not successfully run.
- [x] (2026-06-18 23:59 +05:30, Codex/GPT-5) Patched the notebook so cell 1 only clones/pulls the repo and adds `src/` to `sys.path`; dataset storage selection and optional standard-Colab Drive mounting happen in cell 4.
- [x] (2026-06-18 23:59 +05:30, Codex/GPT-5) Validated the Enterprise notebook patch locally with compile checks, notebook JSON parse, clear-output check, a cell-1 no-`drive.mount()` assertion, `git diff --check`, no official-file diff, and a dry-run one-case medical smoke.
- [ ] (2026-06-18 23:59 +05:30, Codex/GPT-5) Commit and push the Enterprise notebook patch to `origin/main`.
- [x] (2026-06-27 09:10 +05:30, Codex/GPT-5) Diagnosed Colab pip dependency-conflict warnings as caused by forced `--upgrade` in notebook cell 2 and patched the cell to preserve already-installed Colab packages.
- [x] (2026-06-27 09:10 +05:30, Codex/GPT-5) Validated the dependency-cell patch with notebook JSON parse and `git diff --check`.
- [x] (2026-06-27 09:28 +05:30, Codex/GPT-5) Diagnosed vLLM startup failure `ImportError: libcudart.so.13` as a CUDA wheel mismatch and patched cell 2 to install the explicit `vllm-0.23.0+cu129` wheel.
- [x] (2026-06-27 09:28 +05:30, Codex/GPT-5) Adjusted cell 4 first-smoke defaults for free Colab T4: `MAX_MODEL_LEN = 4096` and `EXTRA_SERVER_ARGS = ["--dtype", "float16"]`.

## Surprises & Discoveries

- Observation: In Colab Enterprise, `google.colab.drive.mount("/content/drive")` raises `NotImplementedError`, so any later cell that depends on imports from this setup sequence can fail with misleading `NameError`s.
  Evidence: User traceback showed `NotImplementedError: google.colab.drive.mount is not supported in Colab Enterprise`, then `NameError: name 'medical_runtime' is not defined`.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Observation: Google's current docs describe Colab Enterprise storage as different from regular Colab's Google Drive storage, and Cloud Storage mounting is the supported GCP-side data access path.
  Evidence: Official Colab Enterprise docs list Enterprise storage separately from Colab Google Drive storage; Workbench docs describe mounting Cloud Storage buckets in JupyterLab.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Observation: `pip install --upgrade` in Colab can replace preinstalled packages that other Colab/GCP packages require, producing warnings such as `google-colab` requiring `pandas==2.2.2` while the runtime has `pandas 3.0.3`.
  Evidence: User-shared Colab output showed conflicts for `google-colab`, `cudf-cu12`, `dask-cudf-cu12`, `gradio`, and `google-adk` after the dependency cell ran.
  Date/Author: 2026-06-27, Codex/GPT-5.
- Observation: The plain vLLM install path can pick a CUDA-13 wheel in Colab, failing before model load with `ImportError: libcudart.so.13`.
  Evidence: User-shared vLLM traceback failed during `import vllm._C`; vLLM release metadata confirms a separate `vllm-0.23.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl` asset is available.
  Date/Author: 2026-06-27, Codex/GPT-5.

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
- Decision: Keep notebook cell 1 as GitHub clone/pull/path setup only.
  Rationale: The user needs a top cell that can be rerun immediately after a pushed fix without triggering storage mounts or model setup.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Decision: Move dataset root resolution into cell 4 and use `DATASET_ROOT_OVERRIDE`/`RADLE_DATASET_ROOT` for Colab Enterprise.
  Rationale: Standard Colab can still mount Drive when the default Drive path is used, but Enterprise cannot; the model run should fail with a clear dataset-path instruction instead of blocking the GitHub update/import path.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Decision: Remove forced `--upgrade` from the medical notebook dependency cell.
  Rationale: The experimental runner only needs required packages present; upgrading Colab's pinned packages creates avoidable conflicts before the local model server starts.
  Date/Author: 2026-06-27, Codex/GPT-5.
- Decision: Pin the vLLM notebook install to the explicit CUDA 12.9 wheel URL instead of the plain `vllm` package.
  Rationale: The observed Colab runtime is CUDA 12/T4; a CUDA-13 vLLM wheel cannot import there.
  Date/Author: 2026-06-27, Codex/GPT-5.
- Decision: Lower initial T4 smoke settings to `MAX_MODEL_LEN = 4096` and `--dtype float16`.
  Rationale: Free Colab T4 has limited VRAM and lacks BF16 support; the first objective is a one-case smoke, not a maximum-context benchmark.
  Date/Author: 2026-06-27, Codex/GPT-5.

## Revision Notes

- v1 (2026-06-18, Codex/GPT-5): Initial plan for the medical custom runtime notebook and module.
- v2 (2026-06-18, Codex/GPT-5): Recorded cache-routing and server-log diagnostic patch after seeing the user's custom runtime disk layout.
- v3 (2026-06-18, Codex/GPT-5): Recorded Colab Enterprise storage incompatibility, changed the first notebook cell to GitHub setup only, and documented dataset path overrides.
- v4 (2026-06-27, Codex/GPT-5): Recorded Colab pip dependency conflicts and removed forced package upgrades from the dependency cell.
- v5 (2026-06-27, Codex/GPT-5): Recorded vLLM CUDA wheel mismatch and pinned the notebook to explicit CUDA-12.9 vLLM plus T4-safe smoke settings.

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

Post-Enterprise validation:

    python -m py_compile src\radle_benchmark.py src\radle_medical_custom_runtime.py
    # exited 0

    python -c "import json, pathlib; json.loads(pathlib.Path('notebooks/RadLE_Medical_Custom_Runtime.ipynb').read_text(encoding='utf-8')); print('medical notebook JSON parse OK')"
    medical notebook JSON parse OK

    python -c "<notebook output/execution count and cell-1 drive.mount assertion>"
    cells 10
    outputs 0
    executed 0
    cell1_drive_mount False

    git diff --check
    # exited 0; line-ending warnings only for README.md and this plan

    git diff -- src\radle_benchmark.py notebooks\RadLE_v1_5_Morning.ipynb
    # no output

    C:\Users\thehb\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "<dry-run one-case medgemma smoke>"
    MEDICAL_CUSTOM_RUNTIME_DRY_RUN_OK rows=1

## Idempotence And Recovery

The notebook defaults to `TEST_LIMIT=1` and separate run labels, so reruns are safe. If a model server fails to start, stop the server process, restart the Colab runtime, and rerun setup with a single selected model. If MedGemma access fails, accept the Hugging Face terms and set a Colab secret named `HF_TOKEN`.
