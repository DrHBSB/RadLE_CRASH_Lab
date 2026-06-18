# Implement Parsing, Backups, Audit, And Repair

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` or root `AGENTS.md` file was found. It implements `Documents/requirements_json_audit_repair.md`.

## Purpose / Big Picture

The user selected features 1, 4, 5, and 6 from the pristine notebook comparison: robust JSON parsing, atomic progress saves with backups every 10 completed cases, read-only audit, and targeted repair. After implementation, a fresh RadLE benchmark run can recover malformed model JSON more reliably, save progress safely, audit output without writes or API calls, and rerun only failed or invalid case-model cells under explicit confirmation.

## Current State

Current state (2026-06-18 10:11 +05:30, Codex/GPT-5): Implementation, no-API validation, and paid OpenRouter-only validation are complete. `run_benchmark` now resumes an existing output CSV, skips accepted case-model cells, retries failed or malformed cells, and fills missing later cases. Paid testing used `TEST_OPENROUTER_API_KEY`, one local smoke image, and OpenRouter-routed models only. Next: hand results to the user.

## Locked Facts

- Requirements live at `Documents/requirements_json_audit_repair.md`.
- Historical first-50 preservation and 51-200 overlap rerun logic are out of scope.
- The notebook should remain a thin Colab runner; reusable logic belongs in `src/radle_benchmark.py`.
- The normal benchmark checkpoint cadence must be 10 completed cases, not 5.
- Phase 1 local smoke passed using the bundled Python runtime and SDK stubs: parser samples and `save_benchmark_progress` output/latest/numbered backup creation worked.
- Phase 2 local smoke passed using synthetic benchmark and repair-log CSVs: audit returned dataset integrity, cell audit rows, repair targets, no-paid cleanup, and provider block tables.
- Phase 3 local smoke passed in `NO` mode with no writes, and in a fake-client repair call with output CSV, repair plan, repair log, latest backup, numbered backup, schema-stable columns, and zero remaining repair targets.
- Notebook JSON and all code cells parse after adding audit and repair cells.
- Combined synthetic validation passed: parser recovery, audit repair target detection, repair `NO` dry-run, fake-client confirmed repair, schema-stable repaired output, and zero remaining repair targets.
- Repair attempt tracking must live in a separate repair log, not new benchmark CSV columns.
- Repair attempt counting only counts `REPAIR_STARTED` events, so ordinary benchmark call logs with `STARTED` events do not consume repair-attempt budget.
- Stronger no-API smoke passed on 2026-06-18 09:37 +05:30: 10 fake image cases through `run_benchmark`, checkpoint at case 10, final numbered backup, audit accepted all cells, and repair `NO` mode wrote nothing.
- Resume/gap no-API tests passed on 2026-06-18 09:46 +05:30: if cases 1-3 are complete, rerun skips them and calls only case 4; if case 2 has two failed model cells, rerun fixes those cells before filling case 4.
- Live local OpenRouter smoke did not complete. In sandbox it produced `API_ERROR` from `WinError 10013`; the escalated network rerun was rejected by policy because it would transfer a local image and prompt to OpenRouter using the user's API key.
- After explicit user approval for paid testing, paid OpenRouter tests ran on 2026-06-18 10:11 +05:30. `qwen/qwen-vl-max` returned `OpenRouter HTTP 404: No endpoints found`, revealing a stale model ID and over-retry issue. The code now treats `http 404` and `http 400` as fatal.
- Paid OpenRouter baseline/resume smoke passed with OpenRouter-routed `openai/gpt-4o-mini`: baseline made 2 successful calls for two model slots; after corrupting one model slot, resume skipped the accepted slot and made exactly 1 paid retry. Final audit had 2 accepted cells and 0 repair targets.
- Paid smoke output was written under `local_smoke/openrouter_paid_resume_smoke_20260618_100947.csv` with latest and numbered backups.
- The worktree already had a modified Morning notebook before this implementation began.

## Do Not Revisit

- Do not import the pristine notebook wholesale. See Decision Log 2026-06-18 01:17 +05:30.
- Do not restore old OpenRouter-only provider routing. See Decision Log 2026-06-18 01:17 +05:30.
- Do not implement the first-50/51-200 historical resume workflow. See Decision Log 2026-06-18 01:17 +05:30.

## Progress

- [x] (2026-06-18 01:17 +05:30, Codex/GPT-5) Read requirements, current module, README, and relevant skills.
- [x] (2026-06-18 01:23 +05:30, Codex/GPT-5) Phase 1: robust JSON parser plus atomic 10-case checkpoint saves.
- [x] (2026-06-18 01:29 +05:30, Codex/GPT-5) Phase 2: read-only audit helpers and classification outputs.
- [x] (2026-06-18 01:36 +05:30, Codex/GPT-5) Phase 3: targeted schema-stable repair workflow.
- [x] (2026-06-18 01:43 +05:30, Codex/GPT-5) Phase 4: update Morning notebook orchestration cells to expose audit and repair calls.
- [x] (2026-06-18 01:43 +05:30, Codex/GPT-5) Phase 5: validation with compile checks and local synthetic smoke tests.

## Surprises & Discoveries

- (2026-06-18 01:17 +05:30, Codex/GPT-5) `src/radle_benchmark.py` is a single compact module; audit and repair can be added without creating a new package.
- (2026-06-18 01:17 +05:30, Codex/GPT-5) `run_benchmark` currently writes `output_csv.replace(".csv", "_BACKUP.csv")` every 5 cases and writes the final CSV directly.
- (2026-06-18 01:23 +05:30, Codex/GPT-5) The default Python lacks `anthropic` and `pandas`; validation uses `C:/Users/thehb/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe` plus lightweight SDK stubs.
- (2026-06-18 01:29 +05:30, Codex/GPT-5) Audit uses the same classification logic that repair will use; `repair_targets` is derived from `needs_api_repair == True`.
- (2026-06-18 01:36 +05:30, Codex/GPT-5) Repair `confirmation="NO"` returns the plan and writes nothing; confirmed repair writes a separate repair plan/log and preserves the input CSV schema in the repaired output.
- (2026-06-18 01:43 +05:30, Codex/GPT-5) Notebook edit added two new cells instead of embedding large implementation logic: read-only audit and targeted repair plan/run. The default repair confirmation is `NO`.
- (2026-06-18 01:46 +05:30, Codex/GPT-5) Repair attempts count only `REPAIR_STARTED`; ordinary benchmark `STARTED` and `FINISHED` events remain available for call-log sanity tables without affecting repair budgets.
- (2026-06-18 09:37 +05:30, Codex/GPT-5) Local live API testing is blocked in this environment unless the user explicitly approves external image/prompt transfer after being informed of the risk, or runs the notebook in Colab where the API calls are expected to happen.
- (2026-06-18 09:46 +05:30, Codex/GPT-5) The original `run_benchmark` resume smoke made 8 fake API calls and overwrote clean cases 1-3. This exposed a real gap: benchmark resume/fill behavior was not implemented yet.
- (2026-06-18 09:46 +05:30, Codex/GPT-5) After patching `run_benchmark`, the clean-resume smoke made exactly 2 fake calls for case 4, and the failed-cell smoke made exactly 4 fake calls for case 2's two failed model cells plus case 4's two missing model cells.
- (2026-06-18 10:11 +05:30, Codex/GPT-5) OpenRouter currently reports no endpoints for `qwen/qwen-vl-max`. The paid validation used OpenRouter-routed `openai/gpt-4o-mini` instead.

## Decision Log

- (2026-06-18 01:17 +05:30, Codex/GPT-5) Keep implementation local without creating a branch because the user did not request git operations and the target notebook is already dirty.
- (2026-06-18 01:17 +05:30, Codex/GPT-5) Put reusable functions in `src/radle_benchmark.py`; notebook edits should only wire up imports and calls.
- (2026-06-18 01:17 +05:30, Codex/GPT-5) Implement first in phases inside the module before editing the notebook, so notebook changes remain small and verifiable.
- (2026-06-18 01:23 +05:30, Codex/GPT-5) Keep the existing rolling latest backup name `*_BACKUP.csv` for compatibility; add numbered backups as `*_BACKUP_0001.csv`, `*_BACKUP_0002.csv`, etc.
- (2026-06-18 09:46 +05:30, Codex/GPT-5) Normal benchmark execution now resumes by default (`resume=True`) and uses the same audit classifier to decide whether each case-model cell needs an API call. Accepted cells are not overwritten.
- (2026-06-18 10:11 +05:30, Codex/GPT-5) Treat `http 404` and `http 400` as fatal model/request errors in transport retry logic so stale OpenRouter model IDs do not retry three times.

## Revision Notes

- (2026-06-18 10:11 +05:30, Codex/GPT-5) Added paid OpenRouter test results and fatal HTTP status retry fix.

## Outcomes & Retrospective

Implemented selected requirements. The module now includes robust response parsing, atomic benchmark progress saving with latest and numbered backups, benchmark checkpoints every 10 completed cases, resume/fill behavior for partial output CSVs, read-only audit outputs, and schema-stable targeted repair. The notebook now exposes audit and repair cells while keeping `REPAIR_CONFIRMATION = "NO"` by default. No-API validation and paid OpenRouter-only validation are complete.

## Suggested Skills By Phase

- Planning: `execplan`, activation mode `manual`, used because this is multi-phase implementation.
- Notebook orchestration: `jupyter-notebook`, activation mode `manual`, use only when editing `notebooks/RadLE_v1_5_Morning.ipynb`.
- Module implementation and validation: `none`, activation mode `none`, because ordinary Python editing and local smoke tests are sufficient.
