# Add GPT 5.6 OpenRouter Smoke Notebook

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `AGENTS.md` or `PLANS.md` was found in the current checkout; user-provided AGENTS instructions require an ExecPlan for complex multi-step work.

## Purpose / Big Picture

Prepare a new GPT 5.6 model lane for RadLE without disturbing the currently running Grok 4.5 append. The user-visible result is a pushed branch with a registry entry for an OpenRouter GPT 5.6 variant and a dedicated five-case smoke notebook. The smoke notebook proves model slug, OpenRouter routing, reasoning parameters, and parser behavior before any full 200-case append.

## Current State

Current state (2026-07-10 01:31 +05:30, Codex/GPT-5): The isolated `codex/gpt56-openrouter-smoke` worktree is pushed at `8feeb7b` with canonical Morning configured for a single combined append session: `REPO_REF = "codex/gpt56-openrouter-smoke"`, `RUN_LABEL = "radle_v2"`, `TEST_LIMIT = None`, and `DEBUG_MODEL_NAMES = ["grok_4_5", "gpt_5_6_sol_pro"]`. The paid GPT56 five-case smoke and read-only audit already passed. Next: in Colab, run this pushed branch in one notebook process so any already accepted Grok 4.5 cells are skipped and remaining Grok/GPT56 cells are written by one in-memory dataframe.

## Locked Facts

- The live Grok 4.5 append is using `origin/codex/grok45-morning-smoke`; do not modify its Morning notebook while the run is in progress.
- OpenRouter model metadata checked on 2026-07-09 lists GPT 5.6 variants, not a single bare `openai/gpt-5.6` slug.
- `openai/gpt-5.6-sol-pro` supports `text,image,file->text`, `reasoning`, `reasoning_effort`, and OpenAI provider endpoints.
- OpenRouter-specific request keys must be sent through SDK `extra_body` in this repo.
- Branch `codex/gpt56-openrouter-smoke` is pushed to origin at commit `0f41f67e7694bf594ecc767cb3aefc3637fb9e39`.
- The Colab smoke used `RUN_LABEL = "gpt56_sol_pro_test_5_cases"` and `TEST_LIMIT = 5`.
- The smoke run made 5 API calls and saved raw results to `/content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/gpt56_sol_pro_test_5_cases/raw/results.csv`.
- The read-only audit subset `/tmp/gpt56_sol_pro_test_5_cases_smoke_audit_first_5_cases.csv` had 5 rows, 5 unique cases, no duplicate/missing/extra case ids, `accepted = 5`, `accepted_clean_diagnosis = 5`, and zero repair or analysis targets.
- Branch `codex/gpt56-openrouter-smoke` now has combined Morning append commit `8feeb7b Run Grok and GPT 5.6 in Morning append`.
- The safe way to run Grok 4.5 and GPT56 together into `Runs/radle_v2/raw/results.csv` is one notebook process with both model names active, not two concurrent Colab sessions.
- Existing accepted Grok 4.5 cells will be skipped by `run_benchmark()` because `classify_cell_for_audit()` returns `accepted_clean_diagnosis` when diagnosis is non-empty and Likert is valid.

## Do Not Revisit

- Do not overwrite `notebooks/RadLE_v1_5_Morning.ipynb` for this GPT 5.6 smoke while Grok 4.5 is running. See Decision Log 2026-07-09.
- Do not add a dead `openai/gpt-5.6` model id; use a verified variant. See Decision Log 2026-07-09.
- Do not promote or export public release tables from the five-case smoke output. The smoke notebook's promotion/export cells intentionally raise while `TEST_LIMIT` is not `None`. See Decision Log 2026-07-09.
- Do not run separate Grok and GPT56 Colab sessions concurrently against the same `radle_v2/raw/results.csv`; use the combined notebook or run serially. See Decision Log 2026-07-10.

## Progress

- [x] (2026-07-09 18:15 +05:30, Codex/GPT-5) Verified OpenRouter model availability and reasoning parameter support.
- [x] (2026-07-09 18:24 +05:30, Codex/GPT-5) Add model registry entry and dedicated smoke notebook.
- [x] (2026-07-09 18:25 +05:30, Codex/GPT-5) Validate compile, notebook JSON/config, request shape, and OpenRouter model metadata.
- [x] (2026-07-09 18:15 +05:30, Codex/GPT-5) Push isolated branch and provide Colab handoff.
- [x] (2026-07-10 01:26 +05:30, Codex/GPT-5) Record paid Colab smoke evidence: first 5 cases completed OK, 5 API calls, all outputs routed through OpenAI as `openai/gpt-5.6-sol-pro-20260709`.
- [x] (2026-07-10 01:26 +05:30, Codex/GPT-5) Record read-only audit evidence: dataset integrity clean, accepted bucket count 5, accepted-clean-diagnosis count 5, zero no-API cleanup targets, repair targets, analysis flags, or provider content blocks.
- [x] (2026-07-10 01:31 +05:30, Codex/GPT-5) Prepare canonical Morning on `codex/gpt56-openrouter-smoke` for one combined full append with `DEBUG_MODEL_NAMES = ["grok_4_5", "gpt_5_6_sol_pro"]`.
- [x] (2026-07-10 01:31 +05:30, Codex/GPT-5) Validate compile, notebook JSON/config, registry ids, provider routing, and diff scope; commit and push `8feeb7b`.

## Surprises & Discoveries

- Observation: OpenRouter exposes GPT 5.6 as variant names rather than a bare GPT 5.6 slug.
  Evidence: Models API returned `openai/gpt-5.6-sol`, `openai/gpt-5.6-sol-pro`, `openai/gpt-5.6-terra`, `openai/gpt-5.6-terra-pro`, `openai/gpt-5.6-luna`, and `openai/gpt-5.6-luna-pro`.
  Date/Author: 2026-07-09, Codex/GPT-5

## Decision Log

- Decision: Use `openai/gpt-5.6-sol-pro` and registry name `gpt_5_6_sol_pro` for the first smoke.
  Rationale: Sol is described as flagship; the Pro slug is served with pro reasoning mode for complex tasks, matching a medical-image benchmark better than the cheaper Luna or balanced Terra variants.
  Date/Author: 2026-07-09, Codex/GPT-5
- Decision: Use unified OpenRouter reasoning `{"reasoning": {"effort": "high"}}` rather than native OpenAI-only `reasoning_effort` in the model entry.
  Rationale: The request travels through OpenRouter via the OpenAI SDK, and OpenRouter docs recommend the unified `reasoning` parameter for future compatibility.
  Date/Author: 2026-07-09, Codex/GPT-5
- Decision: Create a separate copied smoke notebook instead of editing canonical Morning.
  Rationale: The Grok 4.5 full append is currently running, and a unique notebook filename avoids stale-Colab-cell confusion.
  Date/Author: 2026-07-09, Codex/GPT-5
- Decision: For the full `radle_v2` append, run Grok 4.5 and GPT56 together in one canonical Morning notebook process rather than separate concurrent Colab sessions.
  Rationale: `run_benchmark()` loads the output CSV once and writes the whole dataframe at checkpoints/final save; one combined process can skip already accepted Grok cells and write both models without a last-writer-wins race.
  Date/Author: 2026-07-10, Codex/GPT-5

## Revision Notes

- v1 (2026-07-09, Codex/GPT-5): Created plan after model availability and routing checks.
- v2 (2026-07-09, Codex/GPT-5): Recorded implementation and validation receipt before branch push.
- v3 (2026-07-10, Codex/GPT-5): Reconciled the plan with the pushed branch and user-provided paid smoke/audit outputs.
- v4 (2026-07-10, Codex/GPT-5): Recorded the combined Grok 4.5 + GPT56 Morning append decision and pushed notebook commit.

## Outcomes & Retrospective

Implementation, local validation, branch push, paid five-case smoke, read-only smoke audit, and combined full-append notebook prep are complete. `py -3.11 -m py_compile src\radle_benchmark.py` passed; notebook config assertions passed; request-shape assertion printed model `openai/gpt-5.6-sol-pro`, SDK keys `extra_body,max_tokens,messages,model,temperature`, and `extra_body` containing high reasoning plus OpenAI-only provider routing. The paid smoke then ran 5/5 cases successfully in Colab, made 5 API calls, returned clean JSON diagnoses and Likert values for all five rows, and the audit accepted all 5 case-model cells with no cleanup or repair targets. Commit `8feeb7b` prepares canonical Morning for one combined `radle_v2` append that runs Grok 4.5 first and GPT56 second while preserving skip semantics for already accepted cells. No reusable cross-project skill lesson needs promotion from this milestone; the useful lesson is project-specific: avoid concurrent writers to the same Morning raw CSV.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | User instructions require a durable plan for multi-step benchmark prep | `manual` |
| Implementation | `none` | Direct Python/notebook edits are sufficient | `none` |
| Validation | `none` | Local compile, JSON, and request-shape checks are sufficient before paid smoke | `none` |

## Context And Orientation

`src/radle_benchmark.py` owns the model registry and request builder. OpenRouter calls go through `build_api_params`; unknown OpenRouter-specific request fields are merged into `extra_body`. Notebook files under `notebooks/` are Colab runners that set `RUN_LABEL`, `TEST_LIMIT`, and `DEBUG_MODEL_NAMES`.

## Plan Of Work

Add a model dictionary near existing OpenAI/GPT entries in `src/radle_benchmark.py`:

    name: gpt_5_6_sol_pro
    id: openai/gpt-5.6-sol-pro
    extra: {"reasoning": {"effort": "high"}}
    provider_routing: {"only": ["OpenAI"], "allow_fallbacks": False}

Copy the prepared Morning notebook to `notebooks/RadLE_v1_5_Morning_GPT56SolPro_5case.ipynb`, then configure it as a five-case smoke with a unique `RUN_LABEL` and model-set guard for exactly `gpt_5_6_sol_pro`.

For the full append, use canonical `notebooks/RadLE_v1_5_Morning.ipynb` on branch `codex/gpt56-openrouter-smoke`. It is configured for `RUN_LABEL = "radle_v2"`, `TEST_LIMIT = None`, and `DEBUG_MODEL_NAMES = ["grok_4_5", "gpt_5_6_sol_pro"]`, with active models selected in that same order.

## Concrete Steps (Commands)

From repo root:

    py -3.11 -m py_compile src/radle_benchmark.py
    py -3.11 -c "<parse notebook and assert config/request shape>"

Expected success: compile exits 0, notebook has 9 cells, and request shape includes `extra_body.reasoning.effort = high` plus `extra_body.provider.only = [OpenAI]`.

## Validation And Acceptance

The branch is ready when the Python module compiles, the smoke notebook parses as valid JSON, the active model guard is exactly `gpt_5_6_sol_pro`, `build_api_params` maps the model to `openai/gpt-5.6-sol-pro` with OpenAI-only provider routing, and the five-case Colab smoke plus audit complete without repair targets. Current evidence satisfies those criteria.

The combined full-append notebook is ready when canonical Morning parses as valid JSON, `REPO_REF` points to `codex/gpt56-openrouter-smoke`, `TEST_LIMIT = None`, `RUN_LABEL = "radle_v2"`, `DEBUG_MODEL_NAMES = ["grok_4_5", "gpt_5_6_sol_pro"]`, and registry assertions confirm `x-ai/grok-4.5` with xAI-only routing plus `openai/gpt-5.6-sol-pro` with high reasoning and OpenAI-only routing. Current evidence satisfies those criteria.

## Idempotence And Recovery

The smoke notebook is a copied runner and can be regenerated from Morning. If OpenRouter returns 404/400 during smoke, stop and re-check the models API before changing the benchmark path.

## Artifacts And Notes

- OpenRouter models API showed `openai/gpt-5.6-sol-pro`, modality `text+image+file->text`, inputs `file,image,text`, supported parameters including `reasoning` and `reasoning_effort`.
- Request assertion printed `{"extra_body": {"provider": {"allow_fallbacks": false, "only": ["OpenAI"]}, "reasoning": {"effort": "high"}}, "keys": ["extra_body", "max_tokens", "messages", "model", "temperature"], "logged": {"provider": {"allow_fallbacks": false, "only": ["OpenAI"]}, "reasoning": {"effort": "high"}}, "model": "openai/gpt-5.6-sol-pro"}`.
- Model metadata assertion printed prompt price `$5/M`, completion price `$30/M`, modality `text+image+file->text`, and supported parameters `include_reasoning,max_tokens,reasoning,reasoning_effort,response_format,seed,structured_outputs,tool_choice,tools`.
- Git worktree verification on 2026-07-10: `C:/Users/thehb/Documents/RadLE v2 - grok45 push` is on `codex/gpt56-openrouter-smoke...origin/codex/gpt56-openrouter-smoke`; `git rev-parse HEAD` and `git rev-parse '@{u}'` both returned `0f41f67e7694bf594ecc767cb3aefc3637fb9e39`.
- Paid smoke transcript excerpt: cases 1 through 5 all returned `OK`; latencies were 19.4s, 4.8s, 7.6s, 36.7s, and 16.6s; output tokens were 1384, 406, 538, 4071, and 1378; prompt tokens were 6760, 5151, 5936, 9189, and 6924; final raw CSV path was `/content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/gpt56_sol_pro_test_5_cases/raw/results.csv`; final numbered backup was `/content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/gpt56_sol_pro_test_5_cases/raw/backups/results_BACKUP_0001.csv`; API calls made this run: 5.
- Smoke output rows showed `Provider_gpt_5_6_sol_pro = OpenAI`, `OpenRouter_Response_Model_gpt_5_6_sol_pro = openai/gpt-5.6-sol-pro-20260709`, and `Actual_Request_Extra_gpt_5_6_sol_pro` containing high reasoning plus OpenAI-only provider routing.
- Read-only audit transcript excerpt: `rows = 5`, `unique_cases = 5`, `models_audited = 1`, `expected_case_model_cells = 5`, duplicate/missing/extra case ids all `none`, bucket summary `accepted = 5`, status summary `accepted_clean_diagnosis = 5`, and 0 rows for no-API cleanup targets, repair targets, analysis flags, and provider content blocks.
- Combined Morning commit: `8feeb7b Run Grok and GPT 5.6 in Morning append`, pushed to `origin/codex/gpt56-openrouter-smoke`.
- Combined Morning validation: `py -3.11 -m py_compile src\radle_benchmark.py` passed; registry assertion printed `combined_registry_ok`; PowerShell JSON parse/config assertion printed `combined_notebook_config_ok cells=9`; `git diff --check` passed.
- Skip-semantics evidence: in `src/radle_benchmark.py`, `run_benchmark()` calls `classify_cell_for_audit()` before each case-model API call and prints `SKIP` when `needs_api_repair` is false; `classify_cell_for_audit()` returns `accepted_clean_diagnosis` with `needs_api_repair=False` when diagnosis is present and Likert is valid.

## Interfaces And Dependencies

No new dependency is required. The only code interface changed is `MODELS` in `src/radle_benchmark.py`; existing `build_api_params` already merges `extra` and `provider_routing` into OpenRouter `extra_body`.
