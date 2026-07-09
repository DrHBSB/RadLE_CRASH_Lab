# Build Meta Muse Spark Colab Pro Runner

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. There is no repo-local `PLANS.md` or relevant repo-local `AGENTS.md` for `Documents/`, `src/`, or `notebooks/`.

## Purpose / Big Picture

RadLE collaborators in the United States have legitimate Meta Model API access and need a Colab Pro notebook that runs Muse Spark against the RadLE v2 image benchmark without embedding secrets or changing the official benchmark roster. The deliverable is a GitHub-first Colab notebook that pulls the repo code, imports Python helpers from `src/`, reads the Meta API key from Colab Secrets, runs a small smoke first, and leaves audit/repair/final-export cells aligned with the existing RadLE notebook pattern.

## Current State

Current state (2026-07-10 01:05 +05:30, Codex/GPT-5): The additive helper module and Colab Pro notebook exist, local validation passed, and branch `codex/meta-muse-spark-colab` has been pushed to GitHub. A collaborator text probe succeeded with `muse-spark-1.1` and showed the first built-in probe budget was too small because the response used 380 hidden reasoning tokens before emitting JSON. Next: collaborator should rerun setup/import after pulling the branch and proceed to the 1-case smoke.

## Locked Facts

- The current checkout already has many unrelated staged and unstaged changes; this task must stay additive unless a direct dependency forces a narrower source edit.
- `src/radle_benchmark.py` is the source of truth for RadLE benchmark execution, image encoding, CSV schema, resume behavior, audit, repair, final promotion, and public export.
- Existing Colab notebooks use a GitHub-fetch-first setup cell, then import Python modules from `src/` and print the resolved commit before running.
- The Muse Spark run is collaborator-run under legitimate Meta developer access; no region bypass, proxy, VPN, or fake-location behavior belongs in this notebook.

## Do Not Revisit

- Do not add Muse Spark to the default official RadLE model registry for this first notebook. See Decision Log 2026-07-10.
- Do not paste or persist the API key in the notebook. See Decision Log 2026-07-10.
- Do not modify existing dirty notebooks for this task. See Decision Log 2026-07-10.

## Progress

- [x] (2026-07-10 00:43 +05:30, Codex/GPT-5) Read `~/.codex/PLANS.md`, the Jupyter notebook skill, and the relevant notebook quality references.
- [x] (2026-07-10 00:43 +05:30, Codex/GPT-5) Inspected existing Morning and medical Colab notebooks plus `src/radle_benchmark.py` and `src/radle_medical_custom_runtime.py` for the GitHub-first runner pattern.
- [x] (2026-07-10 00:46 +05:30, Codex/GPT-5) Added `src/radle_meta_model_api_runtime.py`.
- [x] (2026-07-10 00:46 +05:30, Codex/GPT-5) Added `notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb`.
- [x] (2026-07-10 00:49 +05:30, Codex/GPT-5) Validated Python syntax, notebook JSON/code-cell parsing, output cleanliness, fixed-string secret-prefix scan, and helper import/config without a Meta API key.
- [x] (2026-07-10 00:56 +05:30, Codex/GPT-5) Published `codex/meta-muse-spark-colab` to GitHub without absorbing unrelated dirty files.
- [x] (2026-07-10 01:05 +05:30, Codex/GPT-5) Raised the helper text-probe token budget to 512 after collaborator evidence showed 128 could return empty content.

## Surprises & Discoveries

- Observation: The working tree is already heavily dirty on `codex/radle-v2-handwritten-panels`, including existing notebook and `src/radle_benchmark.py` modifications.
  Evidence: `git status --short --branch` printed numerous `M`, `A`, `AM`, and `??` entries before this task's edits.
  Date/Author: 2026-07-10, Codex/GPT-5
- Observation: Local import of `radle_meta_model_api_runtime` takes noticeable time because it imports `radle_benchmark` and provider SDKs, but it completed and returned the expected config.
  Evidence: `py -3.11 -c "import sys; sys.path.insert(0, 'src'); import radle_meta_model_api_runtime as m; cfg=m.get_model_config(); print(cfg); print('no_temp', m.MODEL_ID in m.radle_benchmark.NO_TEMPERATURE_MODELS)"` printed `{'name': 'muse_spark_1_1', 'id': 'muse-spark-1.1', 'provider': 'meta_model_api', 'extra': None}` and `no_temp True`.
  Date/Author: 2026-07-10, Codex/GPT-5
- Observation: A normal `git commit` would have risked capturing unrelated staged work, so the publish used a temporary Git index and `git commit-tree`.
  Evidence: The isolated commit stat was exactly `Documents/execplan_meta_muse_spark_colab.md`, `notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb`, and `src/radle_meta_model_api_runtime.py`; `git push -u origin codex/meta-muse-spark-colab` created the remote branch.
  Date/Author: 2026-07-10, Codex/GPT-5
- Observation: The collaborator's full probe response had `finish_reason: stop`, `message.content: {"diagnosis":"probe_ok","likert_score":0}`, model `muse-spark-1.1`, and `completion_tokens_details.reasoning_tokens: 380`.
  Evidence: User-pasted Colab response JSON from `chat.completions.create(... max_tokens=512 ...)`.
  Date/Author: 2026-07-10, Codex/GPT-5

## Decision Log

- Decision: Keep Muse Spark in a separate helper module and notebook instead of adding it to `radle_benchmark.MODELS`.
  Rationale: This preserves the official/default benchmark roster and avoids mutating an already dirty shared source file for an access-limited collaborator experiment.
  Date/Author: 2026-07-10, Codex/GPT-5
- Decision: Read `MODEL_API_KEY` or `META_MODEL_API_KEY` from Colab Secrets/environment only.
  Rationale: Collaborator API access must remain non-secret in Git; notebooks should be shareable without credential cleanup.
  Date/Author: 2026-07-10, Codex/GPT-5
- Decision: Use an OpenAI-compatible hosted client with a configurable base URL defaulting to `https://api.meta.ai/v1`.
  Rationale: Current Meta Model API public material describes OpenAI SDK compatibility; making the base URL configurable lets collaborators update it if their dashboard shows a different endpoint.
  Date/Author: 2026-07-10, Codex/GPT-5

## Revision Notes

- v1 (2026-07-10, Codex/GPT-5): Initial plan created for the Meta Muse Spark Colab Pro runner.

## Outcomes & Retrospective

Completed additive local validation. Full top-to-bottom notebook execution remains pending because it requires the collaborator's Colab Pro runtime, private RadLE dataset, GitHub token if needed, and Meta Model API key.

The task branch was published as `codex/meta-muse-spark-colab`. The implementation commit was `3f17f03 Add Meta Muse Spark Colab runner`, followed by plan-only publication updates.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | Required for a multi-step collaborator-facing notebook with secrets and runtime validation. | `auto-suggest` |
| Notebook construction | `jupyter-notebook` | Provides notebook structure and validation guidance. | `auto-suggest` |
| Implementation | `none` | Direct additive source and notebook edits are sufficient. | `none` |
| Validation | `jupyter-notebook` | Use notebook JSON and code-cell validation; full execution needs collaborator API and RadLE data. | `auto-suggest` |

## Context And Orientation

RadLE v2 is a radiology benchmark repository. The main hosted/cloud benchmark path lives in `src/radle_benchmark.py`; existing notebooks under `notebooks/` are thin orchestration layers. The user asked for the "usual py github way", which in this repo means the notebook's first cell clones or pulls `https://github.com/DrHBSB/RadLE_CRASH_Lab.git`, adds `src/` to `sys.path`, prints the resolved commit, and then imports repo Python modules rather than carrying benchmark logic inline.

## Plan Of Work

Add `src/radle_meta_model_api_runtime.py` with a narrow hosted-provider wrapper for `muse_spark_1_1`. The helper will read secrets, build an OpenAI-compatible client, return a RadLE-compatible one-model config, build model-scoped run paths, run the existing benchmark, and stamp provider metadata without changing diagnoses or raw responses.

Add `notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb` with cells for:

1. GitHub repo setup only.
2. Dependency install and imports.
3. Meta API secret/client plus optional text-only probe.
4. Dataset root and run configuration.
5. One-model smoke/full run.
6. Scorer view and read-only audit.
7. Targeted repair preview/run.
8. Private final promotion guard.
9. Public release export guard.

## Concrete Steps (Commands)

From repo root:

    py -3.11 -m py_compile src\radle_meta_model_api_runtime.py

Expected: no output and exit code 0.

From repo root:

    py -3.11 -c "import json, ast, pathlib; nb=json.loads(pathlib.Path('notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb').read_text(encoding='utf-8')); print(nb['nbformat'], len(nb['cells'])); [ast.parse(''.join(c.get('source', []))) for c in nb['cells'] if c.get('cell_type')=='code']; print('notebook code cells parse')"

Expected: prints notebook format/count and `notebook code cells parse`.

Actual local validation run on 2026-07-10:

    py -3.11 -m py_compile src\radle_meta_model_api_runtime.py

    # exit code 0

    py -3.11 -c "import json, ast, pathlib; p=pathlib.Path('notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb'); nb=json.loads(p.read_text(encoding='utf-8')); print('nbformat', nb['nbformat'], 'cells', len(nb['cells'])); [ast.parse(''.join(c.get('source', []))) for c in nb['cells'] if c.get('cell_type')=='code']; print('notebook code cells parse')"

    nbformat 4 cells 10
    notebook code cells parse

    py -3.11 -c "import json, pathlib; nb=json.loads(pathlib.Path('notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb').read_text(encoding='utf-8')); print([c['cell_type'] for c in nb['cells']]); print('has_outputs', any(c.get('outputs') for c in nb['cells'] if c.get('cell_type')=='code'))"

    ['markdown', 'code', 'code', 'code', 'code', 'code', 'code', 'code', 'code', 'code']
    has_outputs False

## Validation And Acceptance

Local validation can confirm syntax and notebook structure. Full top-to-bottom execution requires the collaborator's Colab Pro runtime, private RadLE dataset, GitHub token if the repo is private, and Meta Model API key.

Acceptance:

- The new notebook is valid `.ipynb` JSON.
- Every code cell parses as Python.
- The helper module compiles under `py -3.11`.
- The notebook does not contain an API key.
- The notebook setup cell fetches GitHub code and prints the resolved commit before imports.
- The benchmark cell runs only `muse_spark_1_1` by default with `TEST_LIMIT = 1`.

## Idempotence And Recovery

The notebook setup cell is rerunnable: it updates an existing checkout with `git pull --ff-only` or clones if absent. If the checkout becomes stale or locally modified in Colab, restart the runtime or remove `/content/RadLE_CRASH_Lab`, then rerun cell 1. Benchmark runs are resumable via `RESUME = True`; change `RUN_LABEL` before switching from smoke to a full run if outputs should stay separated.

## Artifacts And Notes

New files:

- `src/radle_meta_model_api_runtime.py`
- `notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb`
- `Documents/execplan_meta_muse_spark_colab.md`

## Interfaces And Dependencies

The notebook requires:

- Colab Secret or environment variable `MODEL_API_KEY` or `META_MODEL_API_KEY`.
- Optional `META_MODEL_API_BASE_URL` override; default is `https://api.meta.ai/v1`.
- Optional `GITHUB_TOKEN` Colab Secret for private repo clone.
- Python packages: `openai`, `pandas`, `anthropic`, `google-genai`.
