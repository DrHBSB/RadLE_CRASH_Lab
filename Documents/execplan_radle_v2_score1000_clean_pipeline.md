# RadLE v2 Score1000 Clean Pipeline

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` or `AGENTS.md` file was found during the prior intake; the active user-provided AGENTS instruction says to use an ExecPlan for complex features, multi-step analyses, or significant refactors and to prefer `Documents/` for repo-local plans.

## Purpose / Big Picture

Build a fresh RadLE v2 adjudication/scoring pipeline that separates correctness adjudication from score calculation. The current long master still contains the retired `weighted_score` column. That file remains the immutable input snapshot for this rewrite until the new lane proves itself. The new pipeline first writes a clean adjudication-master artifact under the Score1000 output root, then builds cohort, Human200 weighting, Score1000 scoring, summaries, provenance, and audit outputs from that clean artifact.

After this work, a reader can rerun the Score1000 scripts from the repo root and verify that the new CSV schemas and row-level/summary data contain only adjudication/evidence fields plus fresh `score1000_*` columns. The old `weighted_score`, `source_weighted_score`, `mean_weighted_score`, `n_weighted`, `weighted_score_rule`, and old `normalization_*` fields must not appear in generated CSV schemas or row-level/summary data. Provenance and receipts may mention `weighted_score` only as removed/source metadata.

## Current State

Current state (2026-07-07 13:33 +05:30, Codex/GPT-5): [LIKERT ACCURACY COLUMNS COMPLETE] The final scoring root contains only `radle_v2_final_long_master.csv` and the default `likert5_score1000` output lane. The generator now writes a compact `score1000_group_summary.csv` with decision-useful statistical columns, including the final weighted score as `final_score1000`, overall accuracy as `accuracy_overall_pct`, per-Likert effective denominators and accuracy percentages for Likert 0 through 4, all-IDK baseline delta, IDK rate, peak-confidence accuracy, and confident-error burden. Detailed status bookkeeping remains in `score1000_scored_rows.csv` and `score1000_status_audit.csv`. The wrapper and audit pass after regeneration, and the wrapper now fails fast on Python step errors. Next: commit only if the user asks; do not regenerate SVG panels unless asked.

## Locked Facts

- Repo root is `C:\Users\thehb\Documents\RadLE v2`.
- Current branch at plan creation is `codex/radle-v2-handwritten-panels`; the branch name is historical, but this plan is for a separate scoring/adjudication pipeline rewrite.
- The checkout is dirty with unrelated tracked modifications/deletions and untracked handwritten-panel files; preserve unrelated changes and keep any staging path-scoped.
- Do not mutate or extend `Documents/execplan_radle_v2_handwritten_panels.md` for this scoring rewrite.
- Primary input snapshot is `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/radle_v2_final_long_master.csv`.
- The input snapshot was verified on 2026-07-07 as 6000 rows, 20 columns, SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`, and `sum(final_score_authoritative)==1255`.
- The input snapshot currently contains the stale legacy score metric column `weighted_score`.
- Do not make in-place cleanup of `radle_v2_final_long_master.csv` the first implementation step. First build and validate a clean adjudication-master artifact in the new Score1000 output lane.
- Clean adjudication-master artifact target: 6000 rows, 19 columns, no `weighted_score`, no old score-metric columns, same row order and same non-score columns as the input snapshot, and `sum(final_score_authoritative)==1255`.
- Authoritative correctness truth remains `final_score_authoritative`; it is adjudication/correctness truth, not a score metric.
- New Score1000 CSV schemas and row-level/summary data use fresh `score1000_*` columns only.
- Do not preserve old `weighted_score`, rename it to `source_weighted_score`, or carry old `normalization_*` columns into Score1000 CSV schemas or row-level/summary data.
- Active Score1000 source universe is 5400 rows: 3000 non-excluded model rows plus 2400 human rows.
- Model rows for the source universe are non-human rows with `access != excluded`.
- Human rows for the source universe are rows with `domain == human`.
- Human comparator grouping: Radiology trainees are `PGY2` and `PGY3`; Board-certified radiologists are `6mo post-MD`, `2y post-MD`, `3y post-MD`, `4y post-MD`, and `7y post-MD`.
- Human comparator anchors: Board-certified radiologists have 6 readers, 1200 source rows, 466 source correct, effective `n=200`; Radiology trainees have 6 readers, 1200 source rows, 458 source correct, effective `n=200`.
- Human200 weighting preserves all human source rows. Model rows weight `1`; human rows weight `1 / n_readers_in_group`.
- Score1000 rule: valid Likert `0..4` maps to weight `1..5`; correct diagnosis scores `+weight`; wrong diagnosis scores `-weight`; true `I don't know` abstention scores `+1`; typo `Idon't know` scores `+1`; invalid Likert such as `8` scores `0` and is flagged; `PARSE_FAILED` or technical failure scores `0`.
- Effective 200-case Score1000 range is `-1000..+1000`; an all-IDK comparator baseline is `+200`.
- Verified Score1000 status counts for the 5400-row source universe: `abstention_idk_reward=688`, `abstention_idk_typo_reward=5`, `invalid_likert_zero=1`, `technical_failure_zero=10`, `valid_likert_correct=1224`, and `valid_likert_wrong=3472`.
- New default output root is `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000`.
- CSV maker and panel generator must stay separate.
- Do not regenerate SVG panels unless the user explicitly asks.
- The read-only judge approved script additions after reconciliation was recorded in this plan; no further read-only investigation is required for the first vertical slice.
- The first vertical slice is not safe to parallelize: clean master builder, Score1000 maker, and audit gate share the same output lane and depend on each other.
- New scripts must not import `radle_metrics.metrics` or `radle_llm_judge.likert_weight`, because those encode retired weighted-score semantics.
- Implemented scripts: `scripts/build_radle_v2_clean_adjudication_master.py`, `scripts/make_radle_v2_likert5_score1000_csvs.py`, `scripts/audit_radle_v2_likert5_score1000_csvs.py`, and optional wrapper `scripts/build_radle_v2_score1000_pipeline.ps1`.
- Generated Score1000 output files must exist under `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000`.
- The source master SHA256 after the wrapper run remained `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`.
- `likert5_score1000/radle_v2_clean_adjudication_master.csv` is the new default clean adjudication source for the Likert-5 Score1000 method. The older `qual_human200_likert5_score1000` lane name is superseded.
- Stale-score gate semantics: CSV schemas and row-level/summary data must not contain stale score columns; provenance and receipts may mention `weighted_score` only as removed/source metadata.
- As of 2026-07-07 12:23 +05:30, the final scoring root contains only `radle_v2_final_long_master.csv` and `likert5_score1000`; all stale root-level generated files and `_visual_qa` were removed.

## Do Not Revisit

- Do not patch the handwritten-panel ExecPlan or treat this as a continuation of the handwritten-panel workflow. See Decision Log 2026-07-07.
- Do not make the existing `radle_v2_final_long_master.csv` adjudication-only in place as the first implementation step. See Decision Log 2026-07-07.
- Do not use, preserve, rename, or compare against old `weighted_score` for Score1000 scoring. See Decision Log 2026-07-07.
- Do not carry `source_weighted_score`, `mean_weighted_score`, `n_weighted`, `weighted_score_rule`, or old `normalization_*` columns into new Score1000 CSV schemas or row-level/summary data. See Decision Log 2026-07-07.
- Do not regenerate SVG panels or modify panel scripts as part of this Score1000 CSV pass. See Decision Log 2026-07-07.
- Do not add scripts until the read-only subagent waves complete and the judge reconciliation is recorded in this plan. See Decision Log 2026-07-07.
- Do not parallelize the initial script work. Implement the clean master builder, Score1000 maker, and audit gate sequentially until the first passing vertical slice exists. See Decision Log 2026-07-07.

## Progress

- [x] (2026-07-07 11:30 +05:30, Codex/GPT-5) Re-read `~/.codex/PLANS.md`, ran `git status --short --branch`, verified this new ExecPlan file did not already exist, and created `Documents/execplan_radle_v2_score1000_clean_pipeline.md` as the first mutation for this rewrite.
- [x] (2026-07-07 11:38 +05:30, Codex/GPT-5 plus Origin Scout Ampere) Ran read-only origin/dependency scout. It found old weighted-score semantics in `scripts/radle_v2_stats.py`, `scripts/radle_llm_judge.py`, `scripts/radle_metrics.py`, summary scripts, `scripts/write_audit.py`, and historical output CSV/JSON/MD files; it recommended clean replacement scripts for the Score1000 lane rather than patching old summary scripts.
- [x] (2026-07-07 11:40 +05:30, Codex/GPT-5 plus Cohort Scout Aristotle) Ran read-only cohort/Human200 scout. It independently confirmed the 5400-row active universe, 15 non-excluded model arms, 12 human readers, 6+6 human split, and Human200 effective denominators of 200 for both comparator groups.
- [x] (2026-07-07 11:36 +05:30, Codex/GPT-5 plus Edge Scout Harvey) Ran read-only Score1000 edge-case scout. It independently matched all status counts: exact IDK 688, typo IDK 5, invalid Likert 1, technical failure 10, valid-correct 1224, valid-wrong 3472.
- [x] (2026-07-07 11:44 +05:30, Codex/GPT-5 plus Judge Architect) Ran judge reconciliation. The judge approved script additions after this plan update, required explicit row-order/non-score-value gates, forbade imports from old weighted-score helpers, and directed sequential implementation.
- [x] (2026-07-07 11:45 +05:30, Codex/GPT-5) Added and ran `scripts/build_radle_v2_clean_adjudication_master.py`; it wrote `radle_v2_clean_adjudication_master.csv` and `adjudication_master_cleanup_receipt.json` under the Score1000 output root, with source hash matched, 6000x19 clean shape, 1255 correct, row order preserved, and only `weighted_score` removed.
- [x] (2026-07-07 11:45 +05:30, Codex/GPT-5) Added and ran `scripts/make_radle_v2_likert5_score1000_csvs.py`; it wrote row-level source/scored CSVs, model/human/group summaries, status audit, provenance, audit notes, and manifest with 5400 source rows and locked status counts.
- [x] (2026-07-07 11:45 +05:30, Codex/GPT-5) Added and ran `scripts/audit_radle_v2_likert5_score1000_csvs.py`; it passed source snapshot, stale-score schema, cohort/Human200, row-score, summary reconciliation, provenance, and manifest gates.
- [x] (2026-07-07 11:46 +05:30, Codex/GPT-5) Added optional `scripts/build_radle_v2_score1000_pipeline.ps1` wrapper and ran it end to end successfully.
- [x] (2026-07-07 11:46 +05:30, Codex/GPT-5) Ran `py -3.11 -m py_compile` for the three new Python scripts, direct trailing-whitespace scan for this plan and new scripts, output inventory, source-master SHA confirmation, and `git status --short --branch`.
- [x] (2026-07-07 12:15 +05:30, Codex/GPT-5) Renamed the default output lane from `qual_human200_likert5_score1000` to `likert5_score1000`, added generated method `README.md`, regenerated the lane, removed the superseded old generated lane after path verification, and reran wrapper/compile/whitespace/import/output/provenance checks.
- [x] (2026-07-07 12:05 +05:30, Codex/GPT-5) Patched audit findings: audit no longer rewrites `manifest.json` or `audit_notes.md`, generator summary aggregation no longer sums rounded per-row effective scores, summary audit now checks mean/min/max/all-IDK baseline fields, and stale-score gate wording is scoped to CSV schemas/data.
- [x] (2026-07-07 12:10 +05:30, Codex/GPT-5) Reran the wrapper and requested verification commands after the audit-finding fixes. Wrapper passed, compile passed, whitespace scan produced no matches, strict import scan produced no matches, human totals are Board-certified radiologists `19.5` and Radiology trainees `17.5`, and the source master SHA remained `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`.
- [x] (2026-07-07 12:23 +05:30, Codex/GPT-5) Cleaned stale files from `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147`, keeping only `radle_v2_final_long_master.csv` and `likert5_score1000`; reran the Score1000 audit gate successfully.
- [x] (2026-07-07 12:37 +05:30, Codex/GPT-5) Reconciled the handwritten-panel plan to the completed `likert5_score1000` lane, then staged only the agreed Score1000 scripts, ExecPlans/repo-structure docs, and reference-only old-panel files. Generated outputs stayed ignored/unstaged except the forced reference `font_sizes.csv` source copy.
- [x] (2026-07-07 12:48 +05:30, Codex/GPT-5) Added generated Score1000 documentation: expanded `README.md`, new required `score1000_group_summary_manual.md`, manifest coverage, and audit coverage for the manual; reran the wrapper successfully.
- [x] (2026-07-07 13:25 +05:30, Codex/GPT-5) Reworked `score1000_group_summary.csv` from a wide audit dump into a compact stats summary. The summary now exposes `final_score1000` directly and keeps only ranking, identity, denominator, accuracy, score, abstention, and peak-confidence error metrics. The generator, manual, and audit were patched together, then the wrapper passed end to end.
- [x] (2026-07-07 13:33 +05:30, Codex/GPT-5) Added explicit `accuracy_overall_pct` and paired per-Likert columns `likert_0_effective_cases`/`likert_0_accuracy_pct` through `likert_4_effective_cases`/`likert_4_accuracy_pct`. The audit independently recalculates these fields from row-level scored data. Also hardened the PowerShell wrapper to stop on Python step failures after an Excel file lock exposed the previous fall-through behavior.

## Surprises & Discoveries

- Observation: The active correction changes the plan boundary: this is a new adjudication/scoring pipeline and not a handwritten-panel continuation.
  Evidence: User explicitly directed not to mutate or extend `Documents\execplan_radle_v2_handwritten_panels.md`, and named this plan file as the first mutation.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Observation: The existing master remains an input snapshot until the output-lane clean adjudication artifact is proven.
  Evidence: User explicitly directed not to make in-place cleanup of `radle_v2_final_long_master.csv` the first implementation step.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Observation: Legacy weighted-score semantics are spread across the old scoring and summary stack and existing final outputs, so patching old scripts first would risk corrupting historical proof artifacts.
  Evidence: Origin Scout Ampere found `weighted_score`/`weighted_score_rule` in `scripts/radle_v2_stats.py` and `scripts/radle_llm_judge.py`, `mean_weighted_score`/`n_weighted` emitted by `scripts/radle_metrics.py` and summary scripts, `weighted_score_blanks` in `scripts/write_audit.py`, and stale weighted fields in top-level output CSVs and `SUMMARY_SPEC.md`.
  Date/Author: 2026-07-07, Origin Scout Ampere and Codex/GPT-5

- Observation: `score_required` is not equivalent to active cohort membership.
  Evidence: Cohort Scout Aristotle found active rows include 698 rows with `score_required=False`, while excluded rows include 352 rows with `score_required=True`.
  Date/Author: 2026-07-07, Cohort Scout Aristotle and Codex/GPT-5

- Observation: Blank Likert rows in the 5400-row Score1000 universe are only IDK/typo-IDK abstention rows.
  Evidence: Edge Scout Harvey found 688 exact `I don't know` rows and 5 typo `Idon't know` rows; all blank Likert rows were in those two categories.
  Date/Author: 2026-07-07, Edge Scout Harvey and Codex/GPT-5

## Decision Log

- Decision: Create a separate ExecPlan at `Documents/execplan_radle_v2_score1000_clean_pipeline.md` and leave `Documents/execplan_radle_v2_handwritten_panels.md` untouched.
  Rationale: The scoring/adjudication rewrite has a separate purpose, output lane, validation surface, and mutation order from handwritten SVG panels.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Decision: Treat `radle_v2_final_long_master.csv` as a fixed input snapshot for the first proven pass and write a new clean adjudication master into the Score1000 output lane.
  Rationale: This preserves the current final master while de-risking the new cleanup/scoring pipeline. In-place master cleanup can be considered later only after the new lane is validated.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Decision: Run read-only subagent waves before adding pipeline scripts.
  Rationale: The rewrite is data-sensitive and methodology-sensitive. Independent origin, cohort, human weighting, edge-case, and judge reconciliation passes reduce the risk of carrying legacy score semantics forward.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Decision: Keep SVG and panel generation out of scope for this pass.
  Rationale: The requested architecture separates CSV/scoring generation from panel generation, and the user explicitly said not to regenerate SVG panels unless asked.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Decision: Implement the Score1000 lane with clean replacement scripts and leave old summary/panel scripts as historical unless a later request targets them.
  Rationale: The old script stack is internally consistent around retired weighted-score semantics. New replacement scripts can enforce stale-score gates without disturbing prior July 6 proof artifacts.
  Date/Author: 2026-07-07, Origin Scout Ampere, Judge Architect, and Codex/GPT-5

- Decision: Add an explicit clean-master preservation gate that compares the full ordered key sequence and all non-score column values against the source snapshot.
  Rationale: The clean master is allowed to remove stale score columns only. Any row reorder or non-score value change would compromise provenance.
  Date/Author: 2026-07-07, Judge Architect and Codex/GPT-5

- Decision: Forbid new Score1000 scripts from importing `radle_metrics.metrics` or `radle_llm_judge.likert_weight`.
  Rationale: Those helpers encode the retired weighted-score method and could silently leak old semantics into new outputs.
  Date/Author: 2026-07-07, Judge Architect and Codex/GPT-5

- Decision: Implement the initial scripts sequentially, not in parallel.
  Rationale: The clean master builder, Score1000 maker, and audit gate share one output lane and depend on each other; a sequential first vertical slice is easier to verify and less likely to conflict.
  Date/Author: 2026-07-07, Judge Architect and Codex/GPT-5

- Decision: Keep the audit gate read-only with respect to generator-produced artifacts.
  Rationale: The audit should validate `manifest.json` and `audit_notes.md` as produced by the generator, not overwrite them before validating. Audit receipts are separate files named `score1000_audit_report.json` and `score1000_audit_report.md`.
  Date/Author: 2026-07-07, Codex/GPT-5 after user audit finding

- Decision: Aggregate Score1000 summaries from exact rational row weights and raw scores, then round only final exported summary fields.
  Rationale: Per-row rounded effective scores caused Human200 drift such as `19.50003` and `17.500044`. Exact aggregation gives Board-certified radiologists `19.5` and Radiology trainees `17.5`.
  Date/Author: 2026-07-07, Codex/GPT-5 after user audit finding

- Decision: Rename the default output lane from `qual_human200_likert5_score1000` to `likert5_score1000`.
  Rationale: The clean adjudication artifact and Score1000 method are now the default for this slice; the longer folder name over-specified implementation details already documented inside the lane.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Clean stale root-level generated files from the final scoring folder while preserving the immutable source master and the current Score1000 lane.
  Rationale: The root-level summaries, old weighted-score spec/audit files, seniority plots, handwritten-panel audit files, and `_visual_qa` no longer represent the active clean Score1000 method and could mislead future work.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Make `score1000_group_summary.csv` a compact statistical comparison table, not a status-audit table.
  Rationale: The reader-facing summary should answer ranking, final score, denominator, accuracy, abstention, and confidence-calibration questions without forcing readers through implementation bookkeeping. Row-level status details remain auditable in `score1000_scored_rows.csv`; global status totals remain in `score1000_status_audit.csv`.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Include per-Likert accuracy with each Likert stratum denominator.
  Rationale: Accuracy by confidence level is not interpretable without knowing how often that confidence level was used. The summary therefore pairs each `likert_N_accuracy_pct` with `likert_N_effective_cases` for N=0..4.
  Date/Author: 2026-07-07, user and Codex/GPT-5

## Revision Notes

- v1 (2026-07-07, Codex/GPT-5): Created the standalone Score1000 clean-pipeline ExecPlan after user correction. It supersedes any handwritten-panel plan for this task without modifying that file.
- v2 (2026-07-07, Codex/GPT-5): Recorded read-only scout and judge reconciliation. The plan is now ready for sequential script additions with extra gates for row-order preservation, stale-score absence, and banned imports from old weighted-score helpers.
- v3 (2026-07-07, Codex/GPT-5): Completed the first Score1000 vertical slice. Added clean-master builder, Score1000 maker, audit gate, optional wrapper, and recorded passing verification evidence.
- v4 (2026-07-07, Codex/GPT-5): Addressed audit findings. Clarified stale-score gate scope, made the audit validate generator artifacts read-only, moved audit receipts to separate files, switched summary aggregation to exact fractions, and expanded summary field audit coverage.
- v5 (2026-07-07, Codex/GPT-5): Recorded successful rerun after audit-finding fixes, including exact human comparator totals and source-master hash confirmation.
- v6 (2026-07-07, Codex/GPT-5): Renamed the active output lane to `likert5_score1000`, added a generated method `README.md`, updated script defaults and acceptance text, removed the superseded verbose lane after path verification, and recorded passing validation evidence.
- v7 (2026-07-07, Codex/GPT-5): Recorded stale-root cleanup. The final scoring root now retains only the immutable source master and `likert5_score1000`; the Score1000 audit passed after cleanup.
- v8 (2026-07-07, Codex/GPT-5): Recorded path-scoped staging after handwritten-plan reconciliation and reference-copy restoration.
- v9 (2026-07-07, Codex/GPT-5): Added first-principles Score1000 README expansion and a generated `score1000_group_summary.csv` manual with column definitions.
- v10 (2026-07-07, Codex/GPT-5): Replaced the wide group-summary status-count schema with a compact expert-facing stats schema centered on `final_score1000`, accuracy, all-IDK baseline delta, IDK rate, peak-confidence accuracy, and confident-error rate.
- v11 (2026-07-07, Codex/GPT-5): Added overall and per-Likert accuracy fields to the compact summary, paired per-Likert accuracy with effective denominators, and made the wrapper fail fast on Python subprocess errors.

## Outcomes & Retrospective

The first Score1000 vertical slice is complete. The pipeline now creates an output-lane clean adjudication master without mutating the source master, creates fresh `score1000_*` row-level and summary outputs, and passes the audit gate. No SVG panels were regenerated. No reusable skill should be promoted without explicit user approval.

Audit-finding fixes are complete. The audit no longer overwrites generator-produced `manifest.json` or `audit_notes.md`; it writes separate `score1000_audit_report.json` and `score1000_audit_report.md` files after validation. Human comparator totals now export exactly as Board-certified radiologists `19.5` and Radiology trainees `17.5`.

Lane renaming is complete. The default output folder is `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000`; the generated `README.md`, `manifest.json`, and provenance all point to that lane and the original source-master SHA remains unchanged.

Stale-root cleanup is complete. The final scoring root now contains only `radle_v2_final_long_master.csv` and `likert5_score1000`; the Score1000 audit passed after cleanup.

Path-scoped staging is complete. The staged set contains the Score1000 pipeline scripts, the relevant ExecPlans/repo-structure docs, and the reference-only RadLE Stats handwritten generator copy. Ignored generated outputs remain unstaged.

Group-summary documentation is complete. `scripts/make_radle_v2_likert5_score1000_csvs.py` now generates `score1000_group_summary_manual.md`; `scripts/audit_radle_v2_likert5_score1000_csvs.py` requires it and validates manifest coverage.

Group-summary schema cleanup is complete. `score1000_group_summary.csv` is now a compact comparison table instead of a wide audit dump. The final weighted score is explicitly named `final_score1000`; detailed status counts are intentionally excluded from this summary and preserved in the row-level/status-audit files.

Per-Likert accuracy expansion is complete. `score1000_group_summary.csv` now includes `accuracy_overall_pct` plus paired `likert_0_effective_cases`/`likert_0_accuracy_pct` through `likert_4_effective_cases`/`likert_4_accuracy_pct`; the generated manual defines these fields and the audit recalculates them from `score1000_scored_rows.csv`.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning and living plan maintenance | `execplan` | Required by user and global plan standard for this multi-step rewrite | `auto-suggest` |
| Origin/dependency scouts | `none` | Direct read-only repo analysis plus subagents is sufficient | `none` |
| Cohort/Human200 scouts | `none` | Direct pandas probes and subagent receipts are sufficient | `none` |
| Score1000 edge-case scouts | `none` | Direct pandas probes and subagent receipts are sufficient | `none` |
| Judge reconciliation | `none` | Read-only skeptical reconciliation before code | `none` |
| Clean adjudication artifact builder | `none` | Narrow CSV transformation with explicit row/hash gates | `none` |
| Score1000 CSV generation | `none` | Direct repo-local Python is sufficient once the contract is locked | `none` |
| Data quality escalation | `data-analytics:analyze-data-quality` | Use only if counts or denominator reconciliation becomes ambiguous or contradictory | `manual` |
| Visual artifacts | `svg-panel-qa`, `output-artifact-verifier` | Later only if the user explicitly asks to regenerate figures from Score1000 summaries | `manual` |

## Context And Orientation

RadLE v2 has an existing final scoring folder at `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147`. The current final long master in that folder is authoritative for adjudicated correctness, but it still contains a retired signed confidence score called `weighted_score`. The new method must not use that score. Instead, it uses `final_score_authoritative` as correctness truth and applies a new deterministic Score1000 rule from diagnosis, Likert confidence, abstention, and technical-failure fields.

The current final master columns are expected to be:

    run_id, Master_Case_ID, Associated_Images, model_blinded, candidate, provider, access, domain, Ground_Truth_Diagnosis, diagnosis, likert, response_valid, abstained, technical_failure, score_required, final_score_authoritative, final_score_source, weighted_score, rater_seniority, rater_seniority_rank

The clean adjudication artifact in the new lane should remove only `weighted_score` at first, leaving all adjudication/evidence fields intact. That artifact then becomes the source for cohort building, Human200 weighting, Score1000 scoring, and summaries.

## Plan Of Work

First, run the read-only subagent waves required by the user. These agents should not edit files. They should return compact evidence receipts with exact files inspected, commands run if any, counts found, and a recommendation. The main thread records the reconciled result in this plan before code starts. This is complete as of 2026-07-07 11:44 +05:30.

Second, add a clean adjudication-master builder script, tentatively `scripts/build_radle_v2_clean_adjudication_master.py`. It reads the input snapshot, validates row count, column count, correctness total, pre-cleanup SHA256, and presence of `weighted_score`; writes a clean CSV under the new Score1000 output root; and writes a cleanup/provenance receipt. It must not mutate the source master. It must compare the full ordered key sequence and every non-score column value in the clean artifact to the source snapshot.

Third, add a Score1000 CSV-maker script, tentatively `scripts/make_radle_v2_likert5_score1000_csvs.py`. It reads the clean adjudication-master artifact, builds the active 5400-row cohort, applies Human200 row weights, classifies every row into a `score1000_status`, applies the Score1000 row score, and writes row-level and summary outputs. It must not import `radle_metrics.metrics` or `radle_llm_judge.likert_weight`.

Fourth, add an audit gate script, tentatively `scripts/audit_radle_v2_likert5_score1000_csvs.py`. It validates every artifact from the output lane, including stale-score absence, status counts, group membership, row-weight sums, score range, file manifest, and summary reconciliation.

Fifth, optionally add `scripts/build_radle_v2_score1000_pipeline.ps1` only after the Python scripts are stable. This wrapper should call clean-master builder, CSV maker, and audit gate in sequence. It should not call panel builders.

## Subagent Wave Contract

Wave 1: Origin/dependency scouts.

Scout A traces where `weighted_score`, `weighted_score_rule`, `mean_weighted_score`, and `n_weighted` enter scripts and outputs. Scout B inspects final master schema, root summaries, historical `qual_human200` outputs, and dependent scripts that assume weighted metrics. Judge reconciles whether the rewrite should patch old scripts or create clean replacement scripts. Completed result: use clean replacement scripts for Score1000 and avoid patching old weighted-summary scripts unless the user later requests historical package regeneration.

Wave 2: Cohort/Human200 scouts.

Scout A derives the active cohort counts from the input snapshot: non-excluded model rows, human rows, excluded rows, model arms, and human readers. Scout B derives Human200 group membership and row-weight denominators independently. Judge reconciles the 5400-row source universe and 6+6 human split.
Completed result: 5400 source rows, 3000 non-excluded model rows, 2400 human rows, 15 non-excluded model arms, 12 human readers, 6 trainee readers, 6 board-certified radiologist readers, and effective denominator 200 for each human comparator.

Wave 3: Score1000 edge-case scouts.

Scout A inventories exact and typo IDK rows. Scout B inventories invalid Likert, Likert 0 with diagnosis, blank Likert, and `PARSE_FAILED` rows. Scout C independently computes Score1000 status counts and expected score range. Judge reconciles all edge-case counts against locked anchors.
Completed result: status counts match locked anchors exactly. Blank Likert rows are only exact IDK plus typo IDK rows.

Only after these read-only waves finish and this plan is updated should scripts be added. This gate is complete as of 2026-07-07 11:44 +05:30.

## Milestones

Milestone 1 uses `execplan`. Outcome: this standalone plan exists, records the dirty working tree, names the new output-lane-first mutation order, and forbids handwritten-panel plan edits.

Milestone 2 uses `none` plus read-only subagents. Outcome: origin, dependency, cohort, Human200, edge-case, and judge receipts are reconciled into this plan. Completed on 2026-07-07.

Milestone 3 uses `none`. Outcome: `scripts/build_radle_v2_clean_adjudication_master.py` writes a clean adjudication artifact under `likert5_score1000` without mutating the input master.

Milestone 4 uses `none`. Outcome: `scripts/make_radle_v2_likert5_score1000_csvs.py` writes row-level Score1000 source/scored files and summaries with fresh `score1000_*` columns only.

Milestone 5 uses `none`. Outcome: `scripts/audit_radle_v2_likert5_score1000_csvs.py` validates all gates, including stale-score absence and final reconciliation.

Milestone 6 uses `none`. Outcome: optional PowerShell wrapper exists only if useful after Python scripts pass.

Milestones 3 through 6 completed on 2026-07-07.

## Concrete Steps (Commands)

From repo root, preflight the input snapshot without writing:

    py -3.11 -c "import hashlib, pathlib, pandas as pd; p=pathlib.Path(r'outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/radle_v2_final_long_master.csv'); h=hashlib.sha256(p.read_bytes()).hexdigest().upper(); df=pd.read_csv(p); print('sha256', h); print('rows', len(df)); print('cols', len(df.columns)); print('has_weighted_score', 'weighted_score' in df.columns); print('correct', int((df.final_score_authoritative == 1).sum()))"

Expected excerpt:

    sha256 7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED
    rows 6000
    cols 20
    has_weighted_score True
    correct 1255

After the scout/judge wave, add and run the clean adjudication builder:

    py -3.11 scripts/build_radle_v2_clean_adjudication_master.py --input outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/radle_v2_final_long_master.csv --out-dir outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000

Expected excerpt:

    [PASS] input snapshot rows=6000 cols=20 sha256=7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED
    [PASS] clean adjudication master rows=6000 cols=19 correct=1255
    [PASS] removed stale score columns: weighted_score

Run the Score1000 CSV maker:

    py -3.11 scripts/make_radle_v2_likert5_score1000_csvs.py --clean-master outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/radle_v2_clean_adjudication_master.csv --out-dir outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000

Expected excerpt:

    [PASS] score1000 source universe rows=5400
    [PASS] non-excluded model rows=3000 human rows=2400
    [PASS] human effective denominators Board-certified radiologists=200 Radiology trainees=200
    [PASS] score1000 status counts match locked anchors

Run the audit gate:

    py -3.11 scripts/audit_radle_v2_likert5_score1000_csvs.py --out-dir outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000

Expected excerpt:

    [PASS] stale-score gate
    [PASS] clean adjudication provenance
    [PASS] cohort and human200 gates
    [PASS] score1000 gates
    [PASS] final summary reconciliation

## Validation And Acceptance

Acceptance requires all of the following:

- `Documents/execplan_radle_v2_handwritten_panels.md` remains unmodified by this work.
- Existing `radle_v2_final_long_master.csv` remains unchanged until the user explicitly approves any later promotion or in-place cleanup.
- The new output root exists at `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000`.
- The output-lane clean adjudication master has 6000 rows, 19 columns, no `weighted_score`, no old score-metric columns, preserved row order, preserved non-score fields, and `sum(final_score_authoritative)==1255`.
- The clean adjudication builder compares the full ordered key sequence and all non-score column values against the source snapshot.
- The clean adjudication receipt records input SHA256, clean SHA256, removed column list, row counts, column counts, correctness total, and generated timestamp.
- The row-level Score1000 source/scored CSV contains 5400 rows: 3000 non-excluded model rows and 2400 human rows.
- Human rows are preserved, not sampled; human comparator row weights sum to 200 for Board-certified radiologists and 200 for Radiology trainees.
- Model rows have `score1000_row_weight=1`.
- Human rows have `score1000_row_weight=1 / n_readers_in_group`.
- Score1000 status counts match the locked anchors exactly.
- Score1000 summaries reconcile exactly to row-level scored CSVs.
- New output files do not contain `weighted_score`, `source_weighted_score`, `mean_weighted_score`, `n_weighted`, `weighted_score_rule`, or old `normalization_*` columns.
- No SVG panels are regenerated.
- New scripts do not import `radle_metrics.metrics` or `radle_llm_judge.likert_weight`.
- `py -3.11 -m py_compile` passes for new Python scripts.
- A direct trailing-whitespace scan passes for this plan and new scripts.

## Idempotence And Recovery

The clean adjudication builder is output-lane-only and safe to rerun. It may overwrite its own generated clean master and receipts under `likert5_score1000`, but it must not mutate the input master or historical `qual_human200` panel artifacts.

The Score1000 CSV maker and audit gate are safe to rerun. The maker owns generated CSVs, `audit_notes.md`, `data_provenance.*`, and `manifest.json`. The audit gate validates those generator-produced artifacts read-only and may overwrite only its separate `score1000_audit_report.json` and `score1000_audit_report.md` receipts. If an audit fails, stop, record the failure in this plan, patch the relevant script, delete or overwrite only files under the Score1000 output root, and rerun the pipeline from the clean adjudication builder. Do not fix failures by copying old weighted-score data forward.

If staging is needed later, run `git status --short --branch` first and stage only files that belong to this task.

## Artifacts And Notes

Plan-creation posture command:

    git status --short --branch

Observed on 2026-07-07 11:30 +05:30:

    ## codex/radle-v2-handwritten-panels
     M Documents/execplan_medical_custom_runtime_colab.md
     M Documents/execplan_medical_workbench_runtime.md
     M README.md
     D docs/goals/llava-vllm-antigravity-extension/.goalbuddy-board/app.js
     D docs/goals/llava-vllm-antigravity-extension/.goalbuddy-board/index.html
     D docs/goals/llava-vllm-antigravity-extension/.goalbuddy-board/server.err.log
     D docs/goals/llava-vllm-antigravity-extension/.goalbuddy-board/server.out.log
     D docs/goals/llava-vllm-antigravity-extension/.goalbuddy-board/styles.css
     D docs/goals/llava-vllm-antigravity-extension/goal.md
     D docs/goals/llava-vllm-antigravity-extension/state.yaml
     D docs/goals/llava-vllm-runtime/.goalbuddy-board/app.js
     D docs/goals/llava-vllm-runtime/.goalbuddy-board/index.html
     D docs/goals/llava-vllm-runtime/.goalbuddy-board/server.err.log
     D docs/goals/llava-vllm-runtime/.goalbuddy-board/server.out.log
     D docs/goals/llava-vllm-runtime/.goalbuddy-board/styles.css
     D docs/goals/llava-vllm-runtime/goal.md
     D docs/goals/llava-vllm-runtime/notes/T001-first-antigravity-packet.md
     D docs/goals/llava-vllm-runtime/notes/T002-antigravity-receipt-review.md
     D docs/goals/llava-vllm-runtime/notes/T003-antigravity-gui-smoke-instructions.md
     D docs/goals/llava-vllm-runtime/notes/T004-gui-evidence-review.md
     D docs/goals/llava-vllm-runtime/notes/T005-corrective-gui-smoke-instruction.md
     D docs/goals/llava-vllm-runtime/notes/T006-current-gui-review.md
     D docs/goals/llava-vllm-runtime/notes/T007-vllm-gui-smoke-instruction.md
     D docs/goals/llava-vllm-runtime/notes/T008-gui-evidence-review.md
     D docs/goals/llava-vllm-runtime/notes/T009-antigravity-correction-response.md
     D docs/goals/llava-vllm-runtime/notes/T010-vllm-open-no-output-review.md
     D docs/goals/llava-vllm-runtime/notes/T011-vllm-gui-run-instruction.md
     D docs/goals/llava-vllm-runtime/notes/T012-vllm-still-not-run-review.md
     D docs/goals/llava-vllm-runtime/state.yaml
     M notebooks/RadLE_Medical_Custom_Runtime.ipynb
     M notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb
     M notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb
     M notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb
     M notebooks/RadLE_Medical_Workbench_Runtime.ipynb
     M notebooks/RadLE_v1_5_Morning.ipynb
     M scripts/radle_v2_finalize_summaries.py
     M scripts/summary_human.py
     M scripts/write_audit.py
    ?? Documents/execplan_radle_v2_handwritten_panels.md
    ?? Documents/execplan_repo_structure_audit.md
    ?? Documents/repo_structure_audit_pass_two_ledger.md
    ?? scripts/audit_radle_v2_handwritten_panels.py
    ?? scripts/build_radle_v2_handwritten_panels.ps1
    ?? scripts/make_radle_v2_handwritten_svg_panels.py
    ?? scripts/radle_v2_handwritten_stats.py

Prior read-only intake verified the following input snapshot facts:

    sha256 7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED
    rows 6000
    cols 20
    score_cols_present ['weighted_score']
    correct_total 1255
    source_universe_rows 5400
    non_excluded_model_rows 3000
    human_rows 2400
    score1000_status_counts {'abstention_idk_reward': 688, 'abstention_idk_typo_reward': 5, 'invalid_likert_zero': 1, 'technical_failure_zero': 10, 'valid_likert_correct': 1224, 'valid_likert_wrong': 3472}

Wrapper verification evidence from 2026-07-07 11:45 +05:30:

    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_radle_v2_score1000_pipeline.ps1

    [PASS] input snapshot rows=6000 cols=20 sha256=7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED
    [PASS] clean adjudication master rows=6000 cols=19 correct=1255
    [PASS] removed stale score columns: weighted_score
    [PASS] score1000 source universe rows=5400
    [PASS] non-excluded model rows=3000 human rows=2400
    [PASS] human effective denominators Board-certified radiologists=200 Radiology trainees=200
    [PASS] score1000 status counts {'abstention_idk_reward': 688, 'abstention_idk_typo_reward': 5, 'invalid_likert_zero': 1, 'technical_failure_zero': 10, 'valid_likert_correct': 1224, 'valid_likert_wrong': 3472}
    [PASS] preflight clean adjudication master and source snapshot
    [PASS] stale-score schema gate
    [PASS] cohort and human200 gates
    [PASS] score1000 status and row-score gates
    [PASS] final summary reconciliation
    [PASS] provenance and manifest gates
    [PASS] RadLE v2 Score1000 pipeline complete

Final verification evidence:

    py -3.11 -m py_compile scripts/build_radle_v2_clean_adjudication_master.py scripts/make_radle_v2_likert5_score1000_csvs.py scripts/audit_radle_v2_likert5_score1000_csvs.py

This exited 0. Direct trailing-whitespace scan over this plan and the four new scripts produced no matches. The source master hash after the wrapper remained `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`.

Audit-finding fix rerun evidence from 2026-07-07 12:10 +05:30:

    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_radle_v2_score1000_pipeline.ps1

    [PASS] input snapshot rows=6000 cols=20 sha256=7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED
    [PASS] clean adjudication master rows=6000 cols=19 correct=1255
    [PASS] removed stale score columns: weighted_score
    [PASS] score1000 source universe rows=5400
    [PASS] non-excluded model rows=3000 human rows=2400
    [PASS] human effective denominators Board-certified radiologists=200 Radiology trainees=200
    [PASS] score1000 status counts {'abstention_idk_reward': 688, 'abstention_idk_typo_reward': 5, 'invalid_likert_zero': 1, 'technical_failure_zero': 10, 'valid_likert_correct': 1224, 'valid_likert_wrong': 3472}
    [PASS] preflight clean adjudication master and source snapshot
    [PASS] stale-score schema gate
    [PASS] cohort and human200 gates
    [PASS] score1000 status and row-score gates
    [PASS] final summary reconciliation
    [PASS] provenance and manifest gates
    [PASS] wrote outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\likert5_score1000\score1000_audit_report.json
    [PASS] wrote outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\likert5_score1000\score1000_audit_report.md
    [PASS] audited outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\likert5_score1000
    [PASS] RadLE v2 Score1000 pipeline complete

Final human comparator summary:

    Board-certified radiologists score1000_total=19.5 mean_per_effective_case=0.0975 min=-1000.0 max=1000.0 all_idk_baseline=200.0
    Radiology trainees score1000_total=17.5 mean_per_effective_case=0.0875 min=-1000.0 max=1000.0 all_idk_baseline=200.0

Lane rename verification evidence from 2026-07-07 12:15 +05:30:

    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_radle_v2_score1000_pipeline.ps1

    [PASS] audited outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\likert5_score1000
    [PASS] RadLE v2 Score1000 pipeline complete

    old_exists False
    new_exists True
    source_sha256 7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED
    readme_title # RadLE v2 Likert-5 Score1000
    manifest_output_root outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\likert5_score1000
    manifest_has_readme True
    provenance_method RadLE v2 Likert-5 Score1000
    provenance_source_sha256 7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED
    trailing_whitespace=0
    banned_imports []

Current generated file inventory under `likert5_score1000`:

    adjudication_master_cleanup_receipt.json
    audit_notes.md
    data_provenance.json
    data_provenance.md
    manifest.json
    radle_v2_clean_adjudication_master.csv
    README.md
    score1000_audit_report.json
    score1000_audit_report.md
    score1000_group_summary.csv
    score1000_human_comparator_summary.csv
    score1000_model_summary.csv
    score1000_scored_rows.csv
    score1000_source_rows.csv
    score1000_status_audit.csv

Stale-root cleanup evidence from 2026-07-07 12:23 +05:30:

    REMOVE C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\_visual_qa
    REMOVE C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\access_summary.csv
    REMOVE C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\appendix_within_provider_deltas.csv
    REMOVE C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\domain_summary.csv
    REMOVE C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\final_scoring_audit.json
    REMOVE C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\handwritten_panels_audit_*.txt
    REMOVE C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\human_role_summary.csv
    REMOVE C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\model_summary.csv
    REMOVE C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\provider_summary.csv
    REMOVE C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\seniority_monotonicity_*
    REMOVE C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\seniority_summary.csv
    REMOVE C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\SUMMARY_SPEC.md
    removed_count=21

    remaining root entries:
    radle_v2_final_long_master.csv
    likert5_score1000

    py -3.11 scripts/audit_radle_v2_likert5_score1000_csvs.py --out-dir outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000

    [PASS] preflight clean adjudication master and source snapshot
    [PASS] stale-score schema gate
    [PASS] cohort and human200 gates
    [PASS] score1000 status and row-score gates
    [PASS] final summary reconciliation
    [PASS] provenance and manifest gates

## Interfaces And Dependencies

New scripts should use Python 3.11 via `py -3.11` and may use pandas, matching existing repo scripts. The scripts should expose command-line arguments rather than hardcoding only one path, but defaults may point to the current final scoring folder.

Required generated files under `likert5_score1000`:

- `radle_v2_clean_adjudication_master.csv`
- `adjudication_master_cleanup_receipt.json`
- `score1000_source_rows.csv`
- `score1000_scored_rows.csv`
- `score1000_group_summary.csv`
- `score1000_group_summary_manual.md`
- `score1000_model_summary.csv`
- `score1000_human_comparator_summary.csv`
- `score1000_status_audit.csv`
- `data_provenance.json`
- `data_provenance.md`
- `README.md`
- `audit_notes.md`
- `manifest.json`
- `score1000_audit_report.json`
- `score1000_audit_report.md`
