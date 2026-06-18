# Requirements Note: Robust Parsing, Progress Saves, Read-Only Audit, and Targeted Repair

Status: Draft for user review  
Date: 2026-06-18  
Target repository: `C:/Users/thehb/Documents/RadLE v2`  
Primary target files: `src/radle_benchmark.py` and `notebooks/RadLE_v1_5_Morning.ipynb`

## Objective

Add four specific capabilities from the old pristine workflow into the current fresh RadLE benchmark workflow:

1. A robust JSON response extractor that can recover valid diagnosis and Likert fields from imperfect model responses.
2. Atomic progress saves with latest and numbered backups, using a 10-case checkpoint cadence.
3. A read-only audit workflow that classifies benchmark output quality without API calls or file writes.
4. A schema-stable targeted repair workflow that reruns only invalid or failed case-model cells under explicit user confirmation.

The goal is to improve reliability and recoverability for new benchmark runs without importing historical migration logic or turning the Morning notebook back into a large monolithic script.

## Background

The current Morning notebook delegates benchmark execution to `src/radle_benchmark.py`. That modular design should be preserved. The old pristine notebook contains useful safety and post-processing behavior, but also includes historical first-50-case preservation and overlap-resume logic that was used once to safely continue an older run. That historical logic is not relevant to the new fresh version.

## Scope

This requirement covers only these four selected features.

### Feature 1: Robust JSON Extraction

Replace or upgrade the current response parser so it can:

- Accept `None`, empty strings, Markdown fenced JSON, raw JSON, and text containing JSON.
- Try direct JSON parsing first.
- Scan for non-greedy JSON-like objects and prefer the last valid object containing a `diagnosis` key.
- Accept either `likert_score` or `likert` as the confidence field.
- Fall back to conservative regex extraction for quoted `diagnosis` and `likert_score` fields.
- Return the existing tuple contract: `(diagnosis, likert)`.
- Preserve current sentinel values where extraction fails: `PARSE_FAILED`, `JSON_MISSING_KEY`, and `NULL` where applicable.

### Feature 4: Atomic Progress Saves And 10-Case Backups

Add safer progress persistence to the benchmark run loop. It must:

- Resume from an existing benchmark output CSV by default.
- Skip already-accepted case-model cells when resuming.
- Fill missing case rows and missing model outputs when new images or models are present.
- Retry case-model cells classified as failed, malformed, or otherwise needing API repair before moving on to later missing cases.
- Write benchmark CSV progress atomically by writing to a temporary file first and then replacing the target file.
- Maintain a latest backup CSV alongside the main output CSV.
- Maintain numbered backup CSVs at a fixed interval.
- Use a 10-case checkpoint cadence for routine benchmark backups, replacing the current 5-case backup cadence.
- Save final output and a final numbered backup at the end of a run.
- Preserve all existing benchmark columns and row values when saving.
- Avoid partial/corrupt CSVs if the runtime is interrupted during a write.
- Keep backup naming predictable and tied to the configured output CSV path.

### Feature 5: Read-Only Audit

Add a reusable audit function or notebook cell that evaluates a benchmark CSV without mutation. It must:

- Perform no API calls.
- Perform no file writes.
- Load the selected raw or repaired benchmark CSV.
- Normalize `Master_Case_ID` for stable sorting and comparison.
- Check dataset integrity: row count, unique cases, duplicate case IDs, missing expected case IDs, extra case IDs, and column count.
- Classify every case-model cell into explicit audit buckets, such as accepted, no-paid cleanup, paid repair, limited provider retry, and terminal/exhausted if implemented.
- Detect missing diagnosis columns, empty diagnoses, `PARSE_FAILED`, `JSON_MISSING_KEY`, `API_ERROR`, `ERROR`, `NULL_ERROR`, invalid or missing Likert values, exact valid `I don't know`, and abstention variants.
- Detect provider/content/safety blocks using diagnosis, raw response, reasoning fields, and usage/error text.
- Detect max-token and empty-raw-response problem patterns.
- Summarize problem cells by reason and by model.
- Summarize abstentions by model.
- If a call log exists, audit started/finished imbalance, repeated calls, failed events, and failures that are now resolved in the CSV.
- Return dataframes suitable for display in Colab, rather than only printing text.

### Feature 6: Targeted Repair Workflow

Add a repair workflow that reruns only cells that the audit classifies as repair targets. It must:

- Use the current model registry and provider routing from `src/radle_benchmark.py`.
- Require explicit confirmation before any API call.
- Support a small test mode, for example a capped `YES_REPAIR_10` style run.
- Support a full repair mode for all currently eligible repair targets.
- Build and display a repair plan before spending.
- Track attempts in a separate repair call log, not by adding repair tracking columns to the main benchmark CSV.
- Preserve the benchmark CSV schema.
- Apply per-reason attempt limits, including:
  - malformed or parse-related output: up to 2 attempts;
  - non-content API errors: up to 2 attempts;
  - provider content block: up to 1 attempt;
  - clean diagnosis: 0 attempts;
  - exact valid `I don't know`: 0 attempts.
- Re-check a cell immediately before spending, so a cell already repaired or exhausted is skipped.
- Save progress after each attempt.
- Log `REPAIR_STARTED`, `REPAIR_FINISHED`, and `REPAIR_INTERRUPTED` events.
- Mark interrupted calls as `UNKNOWN_IF_CHARGED`.
- Reclassify each cell after a repair attempt and stop retrying when the output becomes acceptable or the attempt cap is reached.
- Perform a final schema check after repair.

## Out Of Scope

The following must not be included in this work:

- First-50-case preservation.
- 51-200 overlap rerun logic.
- Reconstruction from older trusted CSVs for historical resume.
- Broad import of the pristine notebook.
- Reverting the current modular `src/radle_benchmark.py` structure back into notebook-only code.
- Replacing the current native OpenAI, Anthropic, Gemini, and OpenRouter provider routing with the old OpenRouter-only design.
- Changing the diagnostic prompt unless separately requested.
- Changing model selection defaults unless needed to make repair use the same active model registry.
- Human scoring packet generation; that was candidate 8, not part of this requirement.
- Statistical analysis of model accuracy after human scoring.

## Functional Requirements

### Parser Requirements

- The parser must be deterministic and side-effect free.
- The parser must not throw on malformed model output.
- The parser must preserve compatibility with existing benchmark row fields.
- The parser must handle model outputs where final JSON appears after reasoning text.
- The parser must not over-correct clinical diagnosis text.

### Progress Save Requirements

- Progress saving must be reusable by both normal benchmark execution and targeted repair where practical.
- The normal benchmark execution path must checkpoint after every 10 completed cases.
- The implementation should not checkpoint every 5 cases anymore unless separately configured.
- Atomic writes must be used for main output, latest backup, and numbered backups.
- Backup creation must not change dataframe schema or column order.
- A failed backup write must surface clearly rather than silently pretending progress was saved.
- If the run stops cleanly after case 3 with all selected models complete, rerunning against the same output CSV must skip cases 1-3 and start paid calls at case 4.
- If case 2 has failed selected model cells while cases 1-3 otherwise exist, rerunning against the same output CSV must retry those failed case-model cells before filling later missing cases.

### Audit Requirements

- The audit must be callable from the Morning notebook with a small amount of configuration: source CSV path, model list, optional expected case range, and optional call log path.
- The audit must produce at least:
  - an overall bucket summary;
  - a status/reason summary;
  - a repair target dataframe;
  - a no-paid cleanup candidate dataframe;
  - a provider content block dataframe;
  - a max-token/empty-raw summary;
  - an abstention summary;
  - call-log sanity outputs when a log is provided.
- The audit must make it clear which cells require paid repair and why.

### Repair Requirements

- Repair must be driven by the same classification logic used by audit, so audit and repair do not disagree.
- Repair must not spend unless the user explicitly confirms.
- Repair must write a repair plan CSV only after confirmation.
- Repair must keep the main benchmark CSV schema stable.
- Repair must use atomic writes for the repaired output and latest backup.
- Repair must support numbered backups at a fixed interval.
- Repair must update only model-specific fields for the target model and existing image metadata fields.
- Repair must preserve unrelated case-model outputs.

## Nonfunctional Requirements

- Safety: dry-run audit and repair planning must be available before any paid call.
- Recoverability: interruption must leave the output CSV and repair log in a resumable state.
- Traceability: each repair attempt must be traceable by case ID, model, reason, attempt number, timestamp, status, token counts, latency, and error text if applicable.
- Maintainability: reusable logic should live in `src/radle_benchmark.py`; the notebook should remain a thin orchestration layer.
- Compatibility: functions should work in Colab with Drive paths and local repository import flow.
- Performance: audit should operate with vectorized or straightforward dataframe operations and avoid unnecessary image reads.

## Proposed Public Interfaces

The exact names can change during implementation, but the following shape is expected:

- `extract_json_safely(raw_text) -> tuple[str, object]`
- `atomic_to_csv(df, path) -> None`
- `save_benchmark_progress(df, output_csv, latest_backup_csv=None, numbered=False) -> str | None`
- `run_benchmark(..., resume=True) -> pandas.DataFrame`
- `audit_benchmark_output(raw_csv, models=None, call_log_csv=None, expected_case_ids=None) -> dict[str, pandas.DataFrame]`
- `build_repair_plan(df, models=None, repair_log_df=None, image_index=None) -> pandas.DataFrame`
- `run_targeted_repair(...) -> pandas.DataFrame`

The Morning notebook should call these module functions instead of embedding hundreds of lines of duplicated notebook code.

## Data And Logging Requirements

The benchmark CSV must continue to use the existing per-model column pattern:

- `Diagnosis_<model>`
- `Likert_<model>`
- `Prompt_Tokens_<model>`
- `Total_Tokens_Out_<model>`
- `Reasoning_Tokens_<model>`
- `Latency_<model>`
- `Provider_<model>`
- `Timestamp_UTC_<model>`
- `Reasoning_<model>`
- `Reasoning_Raw_<model>`
- `Reasoning_Details_<model>`
- `Actual_Request_Extra_<model>`
- `Grok_Fallback_Used_<model>`
- `OpenRouter_Response_Model_<model>`
- `Usage_JSON_<model>`
- `Raw_Response_<model>`

The normal benchmark run should write:

- main configured output CSV;
- latest backup CSV;
- numbered backup CSV every 10 completed cases and at final save.

The repair call log should be separate from the benchmark CSV and include at least:

- `timestamp_utc`
- `Master_Case_ID`
- `model`
- `event`
- `reason`
- `repair_attempt_number`
- `status`
- `post_repair_status`
- `latency`
- `completion_tokens`
- `prompt_tokens`
- `error`

## Acceptance Criteria

The work is acceptable when:

- The parser handles clean JSON, fenced JSON, reasoning-plus-final-JSON, malformed JSON with recoverable quoted fields, and unrecoverable text.
- Normal benchmark execution checkpoints with atomic writes every 10 completed cases, not every 5 cases.
- A latest backup and numbered backups are produced without changing schema or column order.
- Rerunning a partially complete output CSV skips clean cells, fills missing case/model gaps, and retries failed cells without overwriting accepted cells.
- The audit can be run on a completed or partial benchmark CSV without writing files.
- The audit outputs clearly separate accepted cells, no-paid cleanup candidates, and paid repair targets.
- The repair workflow shows a plan and exits without file writes or API calls when confirmation is `NO`.
- A capped repair run only attempts the configured number of repair API calls.
- Repair attempts are logged in a separate repair log.
- The repaired benchmark CSV keeps the same columns as the input benchmark CSV.
- Interrupted repair attempts produce a resumable state and an `UNKNOWN_IF_CHARGED` log entry.
- Existing benchmark execution still works after these additions.

## Validation Plan

Minimum validation should include:

- Unit-style parser checks using hard-coded sample model outputs.
- A save/checkpoint test confirming backup cadence is 10 cases and atomic temporary files do not remain after successful writes.
- A small synthetic dataframe audit test covering missing diagnosis, parse failure, invalid Likert, API error, provider content block, valid diagnosis, and valid `I don't know`.
- A dry-run repair plan test that confirms no writes occur in `NO` mode.
- A schema-stability check comparing columns before and after a simulated repair update.
- A Colab smoke run on `TEST_LIMIT=1` after module changes.

## Risks

- Parser changes may alter historical classification of borderline malformed outputs.
- Repair classification can create unnecessary paid calls if the audit logic is too aggressive.
- Provider-specific response formats may drift, especially for native Anthropic and Gemini reasoning fields.
- Long raw responses may exceed Google Sheets limits if later reused for scoring packet work.

## Open Decisions

- Whether no-paid cleanup should actually rewrite harmless abstention variants, or only report them.
- Whether repair should write to a new `_REPAIRED.csv` file by default or update a configured repair output path.
- Whether expected case IDs should default to `1..200` or be inferred from the image folder for fresh runs.
- Whether repair confirmation strings should be interactive `input()` values or explicit function parameters in the notebook.
