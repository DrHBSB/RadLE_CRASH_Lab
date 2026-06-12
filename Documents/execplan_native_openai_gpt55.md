# Native OpenAI GPT-5.5 migration

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. The repo has no repo-local `PLANS.md`; the user-provided `AGENTS.md` instruction requires repo-local ExecPlans for complex or multi-step work and prefers `Documents/`.

## Purpose / Big Picture

The benchmark currently sends GPT-5.5 through OpenRouter. After this change, only the `gpt_5_5` benchmark model will use the native OpenAI API with Colab/local `OPENAI_API_KEY`; all other benchmark models will remain on the existing OpenRouter client and configs. The visible proof of success is a local one-case GPT-5.5 benchmark run that writes a reloadable CSV and scorer-view CSV, followed by a commit pushed to `origin/main` for Colab testing.

## Current State

Current state (2026-06-12 17:29 +05:30, Codex/GPT-5): User's Colab runtime pulled `1529abd` but hit `TypeError: run_benchmark() got an unexpected keyword argument 'openai_client'` because the old `radle_benchmark` module was still cached in memory. The notebook import cell now explicitly reloads `radle_benchmark` after git pull and asserts the loaded `run_benchmark` supports `openai_client`. Next: user should pull latest in Colab, rerun cells 1 and 2, then run `TEST_LIMIT = 1`.

## Locked Facts

- `src/radle_benchmark.py` owns benchmark logic; `notebooks/RadLE_v1_5_Morning.ipynb` owns Colab client setup and Drive paths.
- The user explicitly chose native model alias `gpt-5.5`, `reasoning_effort="high"`, and GPT-5.5-only migration.
- `radle_api_keys.env` is ignored and may be read locally only to load `OPENAI_API_KEY`; secret values must not be printed or committed.
- Local smoke image exists at `local_smoke/images/55.2.jpg`.
- Live local GPT-5.5 smoke output validated at `local_smoke/radle_native_openai_live.csv`; scorer view validated at `local_smoke/radle_native_openai_live_SCORER_VIEW.csv`. These CSVs are ignored by `.gitignore`.
- Colab can keep an old imported Python module in memory after `git pull`; the notebook import cell must explicitly reload `radle_benchmark`.

## Do Not Revisit

- Do not migrate non-GPT-5.5 models off OpenRouter in this pass. See Decision Log 2026-06-12 17:11 +05:30.
- Do not change the benchmark prompt, Drive paths, `TEST_LIMIT`, or add/remove CSV columns unless validation proves a compatibility fix is required. See Decision Log 2026-06-12 17:11 +05:30.

## Progress

- [x] (2026-06-12 17:11 +05:30, Codex/GPT-5) Read `~/.codex/PLANS.md`, confirmed no repo-local `PLANS.md`, inspected module/notebook/git status.
- [x] (2026-06-12 17:24 +05:30, Codex/GPT-5) Implemented native OpenAI routing for GPT-5.5 only in module and notebook.
- [x] (2026-06-12 17:24 +05:30, Codex/GPT-5) Ran syntax, notebook, no-network routing, live GPT-5.5, raw CSV, and scorer-view validations.
- [x] (2026-06-12 17:34 +05:30, Codex/GPT-5) Committed implementation as `97326ea` and pushed it to `origin/main`.
- [x] (2026-06-12 17:34 +05:30, Codex/GPT-5) Prepared handback Colab test instructions: run with `TEST_LIMIT = 1`, then optionally `TEST_LIMIT = 5`.
- [x] (2026-06-12 17:29 +05:30, Codex/GPT-5) Patched notebook import cell to reload `radle_benchmark` and assert `openai_client` support before running.

## Surprises & Discoveries

- (2026-06-12 17:24 +05:30, Codex/GPT-5) Writing a temporary helper under `C:\tmp` was denied by local permissions, so validation wrote ignored CSV outputs under `local_smoke/` instead.
- (2026-06-12 17:29 +05:30, Codex/GPT-5) Colab traceback after fast-forward to `1529abd`: `TypeError: run_benchmark() got an unexpected keyword argument 'openai_client'`. Root cause is stale module cache in the running Colab kernel, not a missing source update.

## Decision Log

- (2026-06-12 17:11 +05:30, Codex/GPT-5) Stay on local `main` and push directly to `origin/main`, matching the user's plan and current repo workflow.
- (2026-06-12 17:11 +05:30, Codex/GPT-5) Keep `client=` as the existing OpenRouter client and add optional `openai_client=` so current call sites remain understandable and only GPT-5.5 needs new routing.
- (2026-06-12 17:24 +05:30, Codex/GPT-5) Use `local_smoke/` for local validation outputs because `C:\tmp` rejected helper-file writes; outputs remain uncommitted due existing ignore rules.
- (2026-06-12 17:29 +05:30, Codex/GPT-5) Make the notebook reload `radle_benchmark` with `importlib.reload()` and assert `openai_client` is present in the loaded `run_benchmark` signature to prevent stale-runtime failures after `git pull`.

## Revision Notes

- (2026-06-12 17:11 +05:30, Codex/GPT-5) Initial plan created from the user-approved implementation plan.
- (2026-06-12 17:24 +05:30, Codex/GPT-5) Validation milestone completed. Temporary validation script was deleted after successful run.

## Outcomes & Retrospective

- Local validation passed:
  - `py -3.11 -m py_compile src\radle_benchmark.py local_smoke\radle_native_openai_validation.py`
  - notebook JSON parsed with 5 cells and expected `OPENAI_API_KEY`, `TEST_OPENROUTER_API_KEY`, and `openai_client=openai_client` wiring
  - prompt comparison against `HEAD:src/radle_benchmark.py` returned `prompt_unchanged True`
  - no-network fake routing confirmed GPT-5.5 used native OpenAI params and llama kept OpenRouter-style params
  - live GPT-5.5 run returned `OK (21.5s | 539 out / 1592 in | 25.1 tok/sec)` and CSV validation printed `live_csv_ok local_smoke/radle_native_openai_live.csv local_smoke/radle_native_openai_live_SCORER_VIEW.csv`
- Code commit `97326ea` was pushed to `origin/main`; a follow-up plan-only commit records this final state.

## Suggested Skills By Phase

- Planning and handoff: `execplan`, activation `manual`, used because repo instructions require durable planning for multi-step work.
- Module/notebook edits: `none`, activation `none`; this is direct Python and notebook JSON editing.
- CSV/output validation: `none`, activation `none`; pandas reload and column checks are sufficient.
