# Final Binary Scoring For Blinded RadLE Combined Diagnosis CSV

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` exists. The root checkout has no applicable `AGENTS.md`; only `vllm_0_23_0/AGENTS.md` files were found and they do not apply to `outputs/radle_v2_stats/` or `Documents/`. The user-provided AGENTS instruction says to place ExecPlans under `Documents/` when available.

## Purpose / Big Picture

The user needs a complete binary correctness scoring of `outputs/radle_v2_stats/long_format_diag_likert_blinded_combined.csv` with no human-review leftovers. The scoring must preserve blinding: each row is judged only from `Ground_Truth_Diagnosis` and `diagnosis`; image paths and true model identity are not scoring evidence. The deliverable is a timestamped output folder containing scored blinded and unblinded long-format CSVs, a model summary, an audit JSON, and a README with exact commands.

## Current State

Current state (2026-07-05 01:21 IST, Codex/GPT-5): Final scoring is complete. The output folder `outputs/radle_v2_stats/final_binary_scoring_20260705_010315/` contains the required scored blinded CSV, scored unblinded CSV, model summary, audit JSON, and README. Read-back validation confirmed 6,000 scored blinded rows, 6,000 scored unblinded rows, score values only `0/1`, zero duplicate `(Master_Case_ID, model_blinded)` rows, all 30 blinded candidates represented, and zero missing unblinded `model_key`/`provider` rows. Next: report the output folder, final CSV paths, and validation summary.

## Locked Facts

- Input long CSV: `outputs/radle_v2_stats/long_format_diag_likert_blinded_combined.csv`.
- Input blinding key: `outputs/radle_v2_stats/blinding_key_blinded_combined.csv`.
- Output root: `outputs/radle_v2_stats/final_binary_scoring_20260705_010315/`.
- Final scored blinded output has 6,000 rows and score counts `0=4665`, `1=1335`.
- Final scored unblinded output has 6,000 rows and zero missing `model_key`/`provider` joins.
- Final model summary has 30 rows, one per blinded candidate/model key.
- `score_required == false` always receives `score_binary=0`.
- `weighted_score` is deterministic: `+likert` if `score_binary=1`, `-likert` if `score_binary=0`, blank only when `likert` is nonnumeric.
- True model identity is used only after scoring to create the unblinded output and summaries.
- Existing RadLE stats plan `Documents/execplan_radle_v2_stats_pipeline.md` established the text-only judge boundary, safe-copy outputs, and signed Likert weighting.

## Do Not Revisit

- Do not inspect images or infer image content. See Decision Log 2026-07-05.
- Do not use `model_key`, `provider`, or true model identity to decide correctness. See Decision Log 2026-07-05.
- Do not leave rows unresolved or flagged for human review. See Decision Log 2026-07-05.
- Do not overwrite either input CSV. See Decision Log 2026-07-05.

## Progress

- [x] (2026-07-05 01:03 IST, Codex/GPT-5) Read the global ExecPlan standard, the `execplan` skill, relevant RadLE memory, the existing RadLE stats pipeline ExecPlan, and the `data-analytics:analyze-data-quality` skill.
- [x] (2026-07-05 01:03 IST, Codex/GPT-5) Validated the input row count, columns, score-required counts, model count, case count, key rows, duplicate count, and numeric-likert count.
- [x] (2026-07-05 01:03 IST, Codex/GPT-5) Created six deterministic row-range shard input CSVs plus `shards/shard_manifest.csv`.
- [x] (2026-07-05 01:14 IST, Codex/GPT-5) Spawned six subagents for the six disjoint shard files; each wrote and validated one scored shard CSV.
- [x] (2026-07-05 01:20 IST, Codex/GPT-5) Merged shard outputs, reviewed worker/evidence conflicts plus duplicate text-pair inconsistencies, and applied 32 main adjudication overrides.
- [x] (2026-07-05 01:21 IST, Codex/GPT-5) Wrote final required files and read them back to validate row counts, score values, duplicates, candidate coverage, unblinded join coverage, blank checks, and weighted-score blank semantics.

## Surprises & Discoveries

- Observation: Deterministic row ranges preserve original CSV order, but later ranges are not contiguous by `Master_Case_ID`.
  Evidence: `shard_manifest.csv` shows shard 4 covers case IDs 1 through 200 while still holding row IDs 3061-4080.
  Date/Author: 2026-07-05, Codex/GPT-5

- Observation: Prior dual-judge evidence was useful but not authoritative for final scoring.
  Evidence: `worker_evidence_disagreements.csv` had 103 worker/evidence disagreements, including obvious overly strict or erroneous evidence-side rows; duplicate text-pair inconsistencies were narrowed to eight rows in `worker_duplicate_pair_inconsistencies.csv`.
  Date/Author: 2026-07-05, Codex/GPT-5

## Decision Log

- Decision: Use row IDs 1 through 6000 as the merge and coverage key.
  Rationale: The user allowed deterministic row ID/range sharding, and row ID validation is independent of case ordering.
  Date/Author: 2026-07-05, Codex/GPT-5

- Decision: Keep all generated scoring artifacts under the timestamped output folder and make no source/input edits.
  Rationale: The working tree is dirty with unrelated user changes, and the user explicitly required outputs under `outputs/radle_v2_stats/final_binary_scoring_<timestamp>/`.
  Date/Author: 2026-07-05, Codex/GPT-5

- Decision: Treat subagent shard outputs as independent scoring decisions, with the main chat responsible for final merge, validation, and any unresolved adjudication.
  Rationale: The user requested multiple chats/subagents for reliability but also required the main chat to decide every row with no human-review leftovers.
  Date/Author: 2026-07-05, Codex/GPT-5

- Decision: Use subagent shard scores as the base and apply explicit main-chat overrides only for reviewed conflicts and inconsistent duplicate text pairs.
  Rationale: The workers scored every row directly under the supplied rubric, while older evidence artifacts were incomplete and sometimes too strict or clinically wrong for the final requested rubric.
  Date/Author: 2026-07-05, Codex/GPT-5

## Revision Notes

- v1 (2026-07-05, Codex/GPT-5): Created a task-specific plan after validating input shape and writing deterministic shard inputs.
- v2 (2026-07-05, Codex/GPT-5): Recorded final shard merge, main adjudication overrides, required output files, and read-back validation.

## Outcomes & Retrospective

Completed. Required final artifacts were written under `outputs/radle_v2_stats/final_binary_scoring_20260705_010315/`. No lesson needs promotion into a reusable skill without explicit user request.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | Required by repo instruction for complex multi-step data work. | `manual` |
| Input and final validation | `data-analytics:analyze-data-quality` | The deliverable depends on row coverage, uniqueness, join coverage, and blank checks. | `manual` |
| Shard scoring | `none` | The scoring rubric is provided in the task and will be applied directly. | `none` |
| Final reporting | `none` | Required output files are CSV, JSON, and README only. | `none` |

## Context And Orientation

This checkout is `C:\Users\thehb\Documents\RadLE v2`. The scoring input is already long-form: one row per `(Master_Case_ID, model_blinded)` candidate answer. The blinding key maps each `model_blinded` label to `model_key` and `provider`, but that key must not be used while deciding correctness. `score_required` marks nonanswers and failures; rows with `score_required=False` receive `score_binary=0` without semantic adjudication.

## Plan Of Work

First, subagents score disjoint shard input files and write shard-scored CSVs under `outputs/radle_v2_stats/final_binary_scoring_20260705_010315/shards/`. Each shard output must include `row_id`, `score_binary`, `score_confidence`, and `score_reason`. Second, the main chat merges shard outputs back to the original long CSV by `row_id`, computes deterministic `weighted_score`, joins the blinding key for the unblinded copy, computes model summaries, and writes the audit JSON and README. Third, the main chat validates row counts, allowed score values, duplicate keys, candidate coverage, unblinded join coverage, blanks, and score-required counts.

Execution posture: stay in Local. Do not create a branch for generated ignored outputs. Do not modify existing source scripts unless a validation blocker requires it.

## Concrete Steps (Commands)

From repo root, already run:

    Get-Date -Format "yyyyMMdd_HHmmss"
    py -3.11 -c "<input shape probe>"
    New-Item -ItemType Directory -Force -Path "outputs/radle_v2_stats/final_binary_scoring_20260705_010315/shards"
    py -3.11 -c "<add row_id and write six deterministic shard inputs>"

Next commands will be recorded in `README.md` after execution.

## Validation And Acceptance

Success requires:

- final scored blinded row count equals 6,000 input rows.
- every row has `score_binary` exactly `0` or `1`.
- there are zero duplicate `(Master_Case_ID, model_blinded)` rows.
- all 30 blinded candidates are represented.
- the unblinded join matches all 6,000 rows and has no missing `model_key` or `provider`.
- no row has blank `score_confidence` or `score_reason`.
- `weighted_score` is blank only when `likert` is nonnumeric.
- the two input CSVs remain untouched.

## Idempotence And Recovery

The output folder is timestamped, so reruns should use a new timestamp rather than overwriting final artifacts. Shard inputs and outputs can be regenerated from the long input because `row_id` is deterministic. If a shard output is missing or malformed, rerun only that shard and then rerun the merge/validation step.

## Artifacts And Notes

Initial validation excerpt:

    rows 6000
    score_required: True 5054, False 946
    model_blinded nunique 30
    Master cases 200
    duplicates 0
    key rows 30
