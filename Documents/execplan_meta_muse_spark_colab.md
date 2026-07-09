# Build Meta Muse Spark Colab Pro Runner

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. There is no repo-local `PLANS.md` or relevant repo-local `AGENTS.md` for `Documents/`, `src/`, or `notebooks/`.

## Purpose / Big Picture

RadLE collaborators in the United States have legitimate Meta Model API access and need a Colab Pro notebook that runs Muse Spark against the RadLE v2 image benchmark without embedding secrets or changing the official benchmark roster. The deliverable is a GitHub-first Colab notebook that pulls the repo code, imports Python helpers from `src/`, reads the Meta API key from Colab Secrets, runs a small smoke first, and leaves audit/repair/final-export cells aligned with the existing RadLE notebook pattern.

## Current State

Current state (2026-07-10 02:24 +05:30, Codex/GPT-5): The client-factory state lock is resolved locally. The copied Morning notebook now invokes the helper's actual `make_openai_client()` API and has a local attribute assertion for it; the helper factory probe and all notebook-cell parse checks passed. Next: publish the two-file correction, then rerun the imports cell in Colab before any benchmark cell.

## Locked Facts

- The current checkout already has many unrelated staged and unstaged changes; this task must stay additive unless a direct dependency forces a narrower source edit.
- `src/radle_benchmark.py` is the source of truth for RadLE benchmark execution, image encoding, CSV schema, resume behavior, audit, repair, final promotion, and public export.
- Existing Colab notebooks use a GitHub-fetch-first setup cell, then import Python modules from `src/` and print the resolved commit before running.
- The Muse Spark run is collaborator-run under legitimate Meta developer access; no region bypass, proxy, VPN, or fake-location behavior belongs in this notebook.
- `audit_benchmark_output()` returns tabular `audit`, `repair_targets`, and `no_paid_cleanup` entries; its API does not include `row_count` or `no_paid_cleanup_targets`.
- The smoke run at `Runs/muse_spark_1_1_meta_muse_spark_1case/` is a valid one-case artifact only: audit reported `rows=1`, `unique_cases=1`, one `accepted` bucket cell, and zero repair or cleanup targets.
- `gpt_5_6_sol_pro` is the verified Morning model name for `openai/gpt-5.6-sol-pro`; the prepared combined Grok/GPT branch is `codex/gpt56-openrouter-smoke` at `8feeb7b`.
- Before this integration, the dispatcher routed only native Anthropic, Google, and OpenAI clients; `muse_spark_1_1` would otherwise have fallen through to Morning's OpenRouter client.
- The dispatcher now accepts optional `meta_client` in `run_benchmark`, `run_targeted_repair`, and `call_model`; only models marked `provider="meta_model_api"` use it, and their provider column is `Meta Model API`.
- The Meta helper's public factory is `make_openai_client(api_key=None, base_url=None)`, not `create_client()`.

## Do Not Revisit

- Do not add Muse Spark to the default official RadLE model registry for this first notebook. See Decision Log 2026-07-10.
- Do not paste or persist the API key in the notebook. See Decision Log 2026-07-10.
- Do not modify existing dirty notebooks for this task. See Decision Log 2026-07-10.
- Do not promote or export the one-case smoke output as a full benchmark result. See Decision Log 2026-07-10.
- Do not edit or rerun the active `codex/gpt56-openrouter-smoke` Morning process concurrently. See Decision Log 2026-07-10.

## Progress

- [x] (2026-07-10 00:43 +05:30, Codex/GPT-5) Read `~/.codex/PLANS.md`, the Jupyter notebook skill, and the relevant notebook quality references.
- [x] (2026-07-10 00:43 +05:30, Codex/GPT-5) Inspected existing Morning and medical Colab notebooks plus `src/radle_benchmark.py` and `src/radle_medical_custom_runtime.py` for the GitHub-first runner pattern.
- [x] (2026-07-10 00:46 +05:30, Codex/GPT-5) Added `src/radle_meta_model_api_runtime.py`.
- [x] (2026-07-10 00:46 +05:30, Codex/GPT-5) Added `notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb`.
- [x] (2026-07-10 00:49 +05:30, Codex/GPT-5) Validated Python syntax, notebook JSON/code-cell parsing, output cleanliness, fixed-string secret-prefix scan, and helper import/config without a Meta API key.
- [x] (2026-07-10 00:56 +05:30, Codex/GPT-5) Published `codex/meta-muse-spark-colab` to GitHub without absorbing unrelated dirty files.
- [x] (2026-07-10 01:05 +05:30, Codex/GPT-5) Raised the helper text-probe token budget to 512 after collaborator evidence showed 128 could return empty content.
- [x] (2026-07-10 01:44 +05:30, Codex/GPT-5) Resolved the audit-schema state lock by changing the audit display cell to count the `audit`, `repair_targets`, and `no_paid_cleanup` DataFrames and show dataset/bucket summaries.
- [x] (2026-07-10 01:44 +05:30, Codex/GPT-5) Validated all 10 notebook code cells with `ast.parse` and called `audit_benchmark_output()` against a one-row local fixture; observed audit display counts `1 0 0`.
- [x] (2026-07-10 01:44 +05:30, Codex/GPT-5) Published the narrow notebook and plan correction as `6460d22 Fix Meta Muse Spark audit display schema` using an isolated Git index; no unrelated worktree files were staged.
- [x] (2026-07-10 01:55 +05:30, Codex/GPT-5) Received collaborator Colab audit evidence: resumed one-case run made `0` API calls; `rows=1`, `unique_cases=1`, no duplicate/missing/extra IDs, `accepted=1`, `repair_targets=0`, and `no_paid_cleanup_targets=0`.
- [x] (2026-07-10 01:55 +05:30, Codex/GPT-5) Created clean worktree `C:\\tmp\\radle_morning_meta_append` and branch `codex/morning-meta-muse-spark-append` from `8feeb7b`; cherry-picked the validated Meta runner commits through `e4f2e84` without touching the active GPT/Grok branch.
- [x] (2026-07-10 01:55 +05:30, Codex/GPT-5) Added Meta client dispatch to `src/radle_benchmark.py` and updated `src/radle_meta_model_api_runtime.py` to pass its direct client through that path.
- [x] (2026-07-10 01:55 +05:30, Codex/GPT-5) Copied the active-branch Morning notebook into `notebooks/RadLE_v1_5_Morning_Grok45_GPT56_MetaMuse_Append.ipynb`, pinned it to the follow-on branch, and configured a three-model serial resume run plus matching audit, repair, and export lists.
- [x] (2026-07-10 01:55 +05:30, Codex/GPT-5) Passed `py -3.11 -m py_compile` for both Python modules, parsed all nine notebook code cells, passed `git diff --check`, and passed a no-network fake-client Meta dispatch probe through `call_model`.
- [x] (2026-07-10 01:55 +05:30, Codex/GPT-5) Committed the prepared integration branch as `b0a1ba5 Integrate Meta Muse Spark into Morning append`; Colab execution remains deferred until the active Grok/GPT process is no longer writing the shared CSV.
- [x] (2026-07-10 01:55 +05:30, Codex/GPT-5) Pushed `codex/morning-meta-muse-spark-append` to origin. Use the branch-pinned integration notebook only after the active writer stops.
- [x] (2026-07-10 02:24 +05:30, Codex/GPT-5) Resolved the client-factory state lock by replacing the invalid `create_client()` call with `make_openai_client()` and adding an explicit helper-attribute guard in the imports cell.
- [x] (2026-07-10 02:24 +05:30, Codex/GPT-5) Passed `py_compile`, a fake-key helper factory probe, notebook JSON/AST parsing, obsolete-call absence check, and `git diff --check`.
- [ ] (2026-07-10 02:24 +05:30, Codex/GPT-5) Publish the two-file factory correction to `codex/morning-meta-muse-spark-append` before rerunning Colab imports.

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
- Observation: The copied Morning imports cell called `create_client()`, but the helper defines `make_openai_client()`.
  Contradicting artifact: `notebooks/RadLE_v1_5_Morning_Grok45_GPT56_MetaMuse_Append.ipynb` line in Colab invoked `radle_meta_model_api_runtime.create_client()`.
  Missed verification: the no-network dispatch probe exercised `call_model()` but did not assert that every notebook helper attribute exists.
  User view: after confirmed checkout `49bf0d6`, Colab raised `AttributeError: module 'radle_meta_model_api_runtime' has no attribute 'create_client'` at the imports cell.
  Evidence: User-pasted Colab traceback and local helper definition at `src/radle_meta_model_api_runtime.py:65`.
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
- Decision: Treat the existing `audit_benchmark_output()` dictionary as the contract and fix only the consumer notebook.
  Rationale: The one-row audit helper validation proves the source function's present keys; changing its broadly used return shape would be disproportionate to a stale display-only consumer.
  Date/Author: 2026-07-10, Codex/GPT-5
- Decision: Accept the smoke gate and keep the next execution as a separate full-run milestone.
  Rationale: The user-provided audit proves a complete and accepted one-case model result, but `TEST_LIMIT = 1` is intentionally non-promotable. A new full-run label prevents any partial artifact from being mistaken for the complete dataset.
  Date/Author: 2026-07-10, Codex/GPT-5
- Decision: Promote Meta to a native client path in `radle_benchmark.py` and use one serial Morning process for all three models.
  Rationale: This makes the benchmark and targeted repair paths select the right client for every model while retaining one shared, resumable CSV. A new branch prevents concurrent writers from changing the active Grok/GPT append.
  Date/Author: 2026-07-10, Codex/GPT-5
- Decision: Use the helper's existing `make_openai_client()` API rather than introducing a second alias.
  Rationale: The standalone runner already exposes and uses that factory. Correcting the notebook consumer is narrower and makes the visible integration call match the helper's documented implementation.
  Date/Author: 2026-07-10, Codex/GPT-5

## Revision Notes

- v1 (2026-07-10, Codex/GPT-5): Initial plan created for the Meta Muse Spark Colab Pro runner.
- v2 (2026-07-10, Codex/GPT-5): Recorded the Colab-discovered audit display schema mismatch, state-lock resolution, local reproduction, and the narrow consumer-only correction.
- v3 (2026-07-10, Codex/GPT-5): Compacted the resolved audit mismatch into Locked Facts and recorded publication commit `6460d22`.
- v4 (2026-07-10, Codex/GPT-5): Recorded the clean collaborator smoke audit and advanced the next action to a separate full-run milestone.
- v5 (2026-07-10, Codex/GPT-5): Extended the existing plan, rather than creating a child plan, for post-resume Morning integration with Grok 4.5 and GPT 5.6 Sol Pro.
- v6 (2026-07-10, Codex/GPT-5): Recorded the implemented native Meta dispatch, copied three-model Morning notebook, static validation, and no-network dispatcher proof.
- v7 (2026-07-10, Codex/GPT-5): Recorded the local integration commit and retained the active-writer wait condition for Colab execution.
- v8 (2026-07-10, Codex/GPT-5): Reconciled the amended commit hash and recorded publication of the follow-on Morning integration branch.
- v9 (2026-07-10, Codex/GPT-5): Recorded the user-observed client-factory mismatch, its local validation, and the branch publication pending state.

## Outcomes & Retrospective

Completed additive local validation, collaborator text probe, collaborator one-case benchmark execution, and a prepared three-model Morning integration. The one-case result showed native Meta provider routing, diagnosis `Left carotid cavernous fistula`, Likert `4`, `1361` prompt tokens, `950` output tokens, `919` reasoning tokens, and `8.3` seconds latency. The resumed audit verified one expected row, no ID integrity defects, one `accepted` cell, and zero repair/cleanup targets. The integration adds no paid calls locally; it is safe to execute only after the live Grok/GPT writer has stopped because all models then share one serial resumable CSV.

The task branch was published as `codex/meta-muse-spark-colab`. The implementation commit was `3f17f03 Add Meta Muse Spark Colab runner`, followed by plan-only publication updates. The follow-on Morning integration branch `codex/morning-meta-muse-spark-append` is published at `b0a1ba5` and has not made any paid calls.

No reusable skill change is proposed: this was a repository-specific stale consumer key rather than a cross-project workflow gap.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | Required for a multi-step collaborator-facing notebook with secrets and runtime validation. | `auto-suggest` |
| Notebook construction | `jupyter-notebook` | Provides notebook structure and validation guidance. | `auto-suggest` |
| Morning integration | `workflow-router`, `execplan`, `jupyter-notebook` | Keeps the active writer isolated, preserves the living handoff, and validates the copied runnable notebook. | `auto-suggest` |
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

For the Morning integration, edit `src/radle_benchmark.py` so Meta has the same explicit client-selection behavior as the existing native providers, including benchmark and targeted-repair callers. Copy `notebooks/RadLE_v1_5_Morning.ipynb` into a new integration notebook rather than mutating the notebook used by the active resume. The new notebook must create a Meta client from `MODEL_API_KEY` or `META_MODEL_API_KEY`, select the existing `grok_4_5` and `gpt_5_6_sol_pro` registry entries plus the Meta model config, and run them serially into `Runs/radle_v2/raw/results.csv` with `RESUME=True`.

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
