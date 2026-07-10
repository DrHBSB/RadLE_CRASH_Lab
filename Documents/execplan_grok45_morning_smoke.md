# Add Grok 4.5 Morning Smoke Notebook

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `AGENTS.md` or `PLANS.md` was found in the current checkout during the prior IDK0/Morning audit; the user-provided instruction requires ExecPlans for complex multi-step work.

## Purpose / Big Picture

Prepare RadLE Morning to run a new OpenRouter model, Grok 4.5, without overwriting previous model outputs. The user-visible result is a new copied Colab notebook that runs only `grok_4_5` for a five-case smoke and a Python registry entry that maps that model name to OpenRouter id `x-ai/grok-4.5`.

## Current State

Current state (2026-07-09 14:30 +05:30, Codex/GPT-5): Five-case Grok 4.5 smoke passed in Colab under `RUN_LABEL = "grok45_test_5_cases"`. The canonical Morning notebook is now prepared for the real append into `RUN_LABEL = "radle_v2"` with `TEST_LIMIT = None` and `DEBUG_MODEL_NAMES = ["grok_4_5"]`. Latest pushed branch commit is `52b6a16 Prepare Morning for Grok 4.5 append` on `origin/codex/grok45-morning-smoke`. The smoke output has 5 rows / 5 unique cases / 5 accepted cells, `Provider_grok_4_5 = xAI`, `Actual_Request_Extra_grok_4_5` containing `{"provider":{"only":["xAI"],"allow_fallbacks":false}}`, and `OpenRouter_Response_Model_grok_4_5 = x-ai/grok-4.5-20260708`. Repair plan has 0 no-API cleanup rows and 0 paid repair rows.

## Locked Facts

- `src/radle_benchmark.py` is the model registry source of truth.
- `notebooks/RadLE_v1_5_Morning.ipynb` is a Colab runner over `src/radle_benchmark.py`.
- The prior three-model smoke plan used a copied notebook with surgical config changes only.
- The current working tree is already dirty with unrelated RadLE panel and notebook work; this task must preserve unrelated changes.
- The copied notebook should use `DEBUG_MODEL_NAMES = ["grok_4_5"]` so old model columns are not rerun by this smoke.
- OpenRouter model metadata checked on 2026-07-09 reports `x-ai/grok-4.5` with `text,image,file` inputs and mandatory/default-high reasoning.
- The copied smoke notebook preserves the canonical Morning promote/export guards while `TEST_LIMIT = 5`.
- Published smoke notebook commit is `9166561 Add Grok 4.5 Morning smoke notebook` on `origin/codex/grok45-morning-smoke`.
- Published provider-routing fix commit is `0f904ff Send OpenRouter provider routing via extra_body` on `origin/codex/grok45-morning-smoke`.
- Published canonical Morning append commit is `52b6a16 Prepare Morning for Grok 4.5 append` on `origin/codex/grok45-morning-smoke`.
- OpenRouter provider routing must be sent through the OpenAI SDK's `extra_body`, not as a direct `provider=` keyword argument.

## Do Not Revisit

- Do not manually edit IDK0 or final-long-master CSVs for Grok 4.5. Add the model through Morning first. See Decision Log 2026-07-09.
- Do not change prompt, payload construction, repair logic, audit logic, or existing model entries unless validation proves it is required. See Decision Log 2026-07-09.
- Do not overwrite the canonical Morning notebook or prior three-model smoke notebook. See Decision Log 2026-07-09.

## Progress

- [x] (2026-07-09 13:00 +05:30, Codex/GPT-5) Read the prior Grok 4.3/MiniMax/GLM smoke ExecPlan and current Morning/model registry context.
- [x] (2026-07-09 13:00 +05:30, Codex/GPT-5) Add the `grok_4_5` registry entry without changing previous model entries.
- [x] (2026-07-09 13:00 +05:30, Codex/GPT-5) Create `notebooks/RadLE_v1_5_Morning_Grok45_5case.ipynb` from Morning with one-model smoke config.
- [x] (2026-07-09 13:00 +05:30, Codex/GPT-5) Validate compile, notebook JSON, and OpenRouter request id mapping.
- [x] (2026-07-09 13:05 +05:30, Codex/GPT-5) Pushed only the registry edit and Grok45 smoke notebook to `origin/codex/grok45-morning-smoke`.
- [x] (2026-07-09 13:35 +05:30, Codex/GPT-5) Added xAI-only OpenRouter provider routing for `grok_4_5`.
- [x] (2026-07-09 13:55 +05:30, Codex/GPT-5) Corrected provider routing to use SDK `extra_body` after Colab reported `Completions.create() got an unexpected keyword argument 'provider'`.
- [x] (2026-07-09 14:10 +05:30, Codex/GPT-5) Reviewed user-provided Colab smoke output: 5/5 accepted, no repair targets, xAI provider proof present in output columns.
- [x] (2026-07-09 14:30 +05:30, Codex/GPT-5) Prepared canonical `notebooks/RadLE_v1_5_Morning.ipynb` to append only Grok 4.5 into the existing `radle_v2` run folder.

## Surprises & Discoveries

- Observation: The request-assertion command timed out with the default timeout during module import, then passed with a longer timeout.
  Evidence: Rerun printed `model_assertions_ok x-ai/grok-4.5 True False`.
  Date/Author: 2026-07-09, Codex/GPT-5
- Observation: Passing `provider` as a direct OpenAI SDK keyword fails before the request reaches OpenRouter.
  Evidence: Colab printed `Completions.create() got an unexpected keyword argument 'provider'`.
  Date/Author: 2026-07-09, Codex/GPT-5
- Observation: Sending OpenRouter provider routing via `extra_body` succeeds and is captured in the smoke output.
  Evidence: Smoke preview shows `Provider_grok_4_5 = xAI`, `Actual_Request_Extra_grok_4_5` with `only: ["xAI"]` and `allow_fallbacks: false`, and `OpenRouter_Response_Model_grok_4_5 = x-ai/grok-4.5-20260708`.
  Date/Author: 2026-07-09, Codex/GPT-5

## Decision Log

- Decision: Add Grok 4.5 through the Morning benchmark path, not by CSV surgery in the IDK0/final-long-master lane.
  Rationale: Morning owns raw model response columns; downstream scoring/IDK0 expects finalized long masters and has hard row-count/SHA gates.
  Date/Author: 2026-07-09, Codex/GPT-5
- Decision: Use a copied smoke notebook with `RUN_LABEL = "grok45_test_5_cases"` and `DEBUG_MODEL_NAMES = ["grok_4_5"]`.
  Rationale: This keeps the smoke output separate from the canonical `radle_v2` run and prevents old models from being rerun.
  Date/Author: 2026-07-09, Codex/GPT-5
- Decision: Leave `REPO_REF` matching the source Morning notebook for now and call out the branch/push requirement before Colab execution.
  Rationale: The current checkout is dirty on a different branch, and the user asked to prepare files, not switch or publish branches yet.
  Date/Author: 2026-07-09, Codex/GPT-5
- Decision: Use `model["provider_routing"]` for registry-level OpenRouter provider constraints and merge it into `api_params["extra_body"]["provider"]`.
  Rationale: OpenRouter documents provider routing as part of the request body, while the OpenAI Python SDK only accepts unknown OpenRouter-specific body keys through `extra_body`.
  Date/Author: 2026-07-09, Codex/GPT-5
- Decision: Prepare canonical Morning for `RUN_LABEL = "radle_v2"` instead of a separate `grok45_full` label.
  Rationale: The user's goal is to append a Grok 4.5 column into the existing Morning run outputs, not create a disconnected full-run folder.
  Date/Author: 2026-07-09, Codex/GPT-5

## Revision Notes

- v1 (2026-07-09, Codex/GPT-5): Created plan before source edits.
- v2 (2026-07-09, Codex/GPT-5): Marked file prep complete and recorded validation evidence.
- v3 (2026-07-09, Codex/GPT-5): Recorded clean-branch push and smoke readiness.
- v4 (2026-07-09, Codex/GPT-5): Recorded provider-routing fix, successful five-case smoke, and zero-repair audit.
- v5 (2026-07-09, Codex/GPT-5): Recorded canonical Morning append preparation.

## Outcomes & Retrospective

- Completed file prep, provider routing, push, and five-case smoke. `py -3.11 -m py_compile src\radle_benchmark.py` passed; notebook JSON parse passed for canonical Morning and the Grok 4.5 copy; config assertions passed for `RUN_LABEL = "grok45_test_5_cases"` and `DEBUG_MODEL_NAMES = ["grok_4_5"]`; request assertion passed with `extra_body.provider.only = ["xAI"]` and `allow_fallbacks = False`. Latest branch commit `0f904ff` is pushed to `origin/codex/grok45-morning-smoke`. User-provided Colab output shows 5 accepted cells and 0 repair targets. No reusable skill lesson needs promotion.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | User instructions require an ExecPlan for multi-step repo work | `manual` |
| Implementation | `none` | Direct Python and notebook JSON edits are sufficient | `none` |
| Validation | `none` | Local compile/JSON/request assertions are sufficient | `none` |

## Context And Orientation

The source Morning notebook currently sets `TEST_LIMIT = 5`, `RUN_LABEL = "radle_v2"`, and `DEBUG_MODEL_NAMES = ["grok_4_3", "minimax_m3", "glm_5v_turbo"]`. For a Grok 4.5 smoke, the copied notebook should set a smoke-specific run label and only one debug model. The canonical Morning notebook keeps guards that block promotion/export when `TEST_LIMIT` is not `None`; preserving those guards prevents accidental five-case final package publication.

## Plan Of Work

Edit `src/radle_benchmark.py` by inserting one dictionary entry near `grok_4_3`:

    {"name": "grok_4_5", "id": "x-ai/grok-4.5", "extra": None, "provider_routing": {"only": ["xAI"], "allow_fallbacks": False}}

Create `notebooks/RadLE_v1_5_Morning_Grok45_5case.ipynb` from `notebooks/RadLE_v1_5_Morning.ipynb`, then modify only the config cell: smoke comment, `RUN_LABEL = "grok45_test_5_cases"`, and `DEBUG_MODEL_NAMES = ["grok_4_5"]`.

Branch strategy: stay in Local for file prep. Before running in Colab, ensure the branch referenced by `REPO_REF` contains the registry edit.

## Concrete Steps (Commands)

From repo root:

    py -3.11 -m py_compile src/radle_benchmark.py
    py -3.11 -c "<parse notebook and assert grok_4_5 request id>"

Expected success: no compile error, notebook has 9 cells, and request assertion returns `x-ai/grok-4.5`.

## Validation And Acceptance

The change is ready when `src/radle_benchmark.py` compiles, the copied notebook parses as valid JSON, the notebook config has only `DEBUG_MODEL_NAMES = ["grok_4_5"]`, and `radle_benchmark.build_api_params` maps `grok_4_5` to OpenRouter model id `x-ai/grok-4.5` with `extra_body.provider.only = ["xAI"]` and `extra_body.provider.allow_fallbacks = False`.

## Idempotence And Recovery

The notebook copy can be regenerated from canonical Morning if needed. If validation fails, inspect only `src/radle_benchmark.py` and the copied notebook; do not touch unrelated dirty files.

## Artifacts And Notes

- `py -3.11 -m py_compile src\radle_benchmark.py` completed with exit code 0.
- Notebook parse printed `notebook_json_ok notebooks\RadLE_v1_5_Morning.ipynb cells=9`, `notebook_json_ok notebooks\RadLE_v1_5_Morning_Grok45_5case.ipynb cells=9`, and `grok45_config_ok`.
- Request assertion printed `model_assertions_ok x-ai/grok-4.5 True False`.
- Provider-routing assertion printed `{"extra_body": {"provider": {"allow_fallbacks": false, "only": ["xAI"]}}, "keys": ["extra_body", "max_tokens", "messages", "model", "temperature"], "logged": {"provider": {"allow_fallbacks": false, "only": ["xAI"]}}}`.
- User-provided smoke output printed 5 `SKIP (accepted_clean_diagnosis)` rows after resuming existing successful cells, `API calls made this run: 0`, and previewed five prior successful Grok 4.5 calls from 2026-07-09T08:25:19Z through 2026-07-09T08:27:22Z.
- Smoke audit printed `rows = 5`, `unique_cases = 5`, `models_audited = 1`, `expected_case_model_cells = 5`, no duplicate/missing/extra case IDs, bucket summary `accepted = 5`, and status summary `accepted_clean_diagnosis = 5`.
- Targeted repair preview printed `No-API cleanup rows / affected cells: 0` and `Repair plan rows / affected cells: 0`; confirmation was `NO`, so no repair files were written.
- OpenRouter metadata check printed `{"id":"x-ai/grok-4.5","modality":"text+image+file->text","inputs":"text,image,file","reasoning_mandatory":true,"reasoning_default_effort":"high"}`.

## Interfaces And Dependencies

The only code interface changed is the `MODELS` list in `src/radle_benchmark.py`. The notebook depends on `radle_benchmark.build_run_paths`, `run_benchmark`, `audit_benchmark_output`, `run_targeted_repair`, `promote_final_results`, and `export_public_release_tables`.
