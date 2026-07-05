# RadLE v2 Dynamic Stats Pipeline

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `AGENTS.md` or `PLANS.md` exists in `C:\Users\thehb\Documents\RadLE v2`; the user-provided AGENTS instruction says to place ExecPlans under `Documents/` when available.

## Purpose / Big Picture

RadLE v2 is moving from a fixed 10-model result file toward combined Workbench outputs that may contain 14-15 models or more. The stats pipeline must therefore infer model columns from the input CSV instead of relying on hardcoded model names, `Model_A..Model_J`, or fixed interpretation counts. After this work, a new contributor should be able to take a freshly combined RadLE result CSV, generate a canonical long-format table, join the confirmed case-level ground truth, produce a scoring worklist, and compute final scored metrics only after correctness scores are complete.

The current raw result source is `results/radle_v2/final/RadLE_v2_results_final.csv`. The confirmed ground-truth/scoring reference imported from the older Stats workspace is `results/reference/RadLE_RSNA_Diagnosis_Scoring_key.csv`. Both locations are ignored by git through `.gitignore`, so the plan must always give exact local paths and validation commands rather than assuming these CSVs are versioned.

## Current State

Current state (2026-06-30 21:17 IST, Codex/GPT-5): The LLM-as-judge code has been split out of `scripts/radle_v2_stats.py` into `scripts/radle_llm_judge.py`. The stats script now exposes only `long` and `scoring-worklist`; the judge script exposes `score` for live OpenRouter/GLM judging and `apply` for propagating an existing judged CSV without API calls. By default the judge script runs in safe-copy mode and writes scored copies under `outputs/`, leaving original combined/public files unchanged; in-place updates require the explicit pair `--update-in-place --overwrite`. Validation applied the 5-row smoke scores to `outputs/radle_v2_stats_safe_apply_test/` and confirmed the original public model results still have 0 populated `score_binary` values, while the safe public copy has 5 `score_binary` values, 5 signed `weighted_score` values, and 0 `score_likert` values. Next: review the five smoke adjudications, then run a controlled MedGemma-only scoring batch into safe-copy outputs before any in-place/public package update.

## Locked Facts

- The latest known full raw run is `results/radle_v2/final/RadLE_v2_results_final.csv`, SHA-256 `53543631d657349e848b38ea57632d07efbc33c22b72a24733ae107bc84d3d9c`, with 200 rows and 163 columns.
- The confirmed ground-truth reference is `results/reference/RadLE_RSNA_Diagnosis_Scoring_key.csv`, SHA-256 `5d26771da27cf8fef1a7f48204257c65b8e1f7b41423763f2e45cb384fb738d4`, with 200 rows and 25 columns.
- The ground-truth column is `Ground_Truth_Diagnosis`; it has 0 blanks, 199 unique labels, and one repeated label, `Emphysematous cholecystitis`.
- The existing imported script `scripts/radle_rsna_analysis.py` is a legacy manuscript-stage script that expects `Diagnosis_Model_A..J`, `Score_Model_A..J`, and `Likert_Model_A..J`.
- Future result files may contain 14-15 models or more; all stats scripts must infer model keys from columns such as `Diagnosis_<model_key>` and must not assume 10 models.
- Raw result CSVs must not be mutated or cleaned in place. Derived long, scorer, metrics, and QA files should be written to a separate output directory.
- `results/` and `*.csv` are ignored by git, so confidential/local result artifacts may exist without appearing in `git status`.
- The first new model result is `results/medgemma_1_5_4b_medical_full_200_cases/final/RadLE_v2_results_final.csv`, SHA-256 `05311fd71b64f0cd8f8459a6788b2653efb99d6ded9b2766d0879bbc1c3ae8be`, with 200 rows and 19 columns.
- The first combined derived result is `results/radle_v2_combined/final/RadLE_v2_results_final_plus_medgemma_1_5_4b.csv`, SHA-256 `80f6fcdc4a73be803841a55afd48651b474746d35b2bf855a4c7eff4f0e3b260`, with 200 rows and 179 columns.
- The first combined scorer view is `results/radle_v2_combined/scorer/scorer_view_plus_medgemma_1_5_4b.csv`, SHA-256 `bcbf0bff74140694291540b66603da0db0e09288251a1b2da0d99632e6f6e54b`, with 200 rows and 24 columns; columns are ordered as `Diagnosis_<model>, Likert_<model>` pairs.
- The canonical whole-package combined final is `results/radle_v2_combined/final/RadLE_v2_results_final.csv`, SHA-256 `80f6fcdc4a73be803841a55afd48651b474746d35b2bf855a4c7eff4f0e3b260`, with 200 rows and 179 columns.
- The intended canonical whole-package combined scorer view is `results/radle_v2_combined/scorer/scorer_view.csv`, but at 2026-06-30 21:08 IST that CSV was not present on disk; the paired scorer artifact currently present is `results/radle_v2_combined/scorer/scorer_view_plus_medgemma_1_5_4b.csv`, SHA-256 `bcbf0bff74140694291540b66603da0db0e09288251a1b2da0d99632e6f6e54b`, with 200 rows and 24 columns.
- The combined public case-model table is `results/radle_v2_combined/public_release/RadLE_v2_public_model_results.csv`, SHA-256 `165844afa2d412fdb907847f132627b44bf8e53b2b2624b26a25f9dce194593b`, with 2,200 rows, 14 columns, 11 models, 0 duplicate `(case_uid, model)` pairs, and run ID `radle_v2_plus_medgemma_1_5_4b`.
- The combined public model summary is `results/radle_v2_combined/public_release/RadLE_v2_public_model_summary.csv`, SHA-256 `26af3ff74f79700c5f083b0359718295db9b34ea29a4ad59bc762dee5fd1d561`, with 20 rows, 13 columns, and 11 models.
- The combined public sanitized call log is `results/radle_v2_combined/public_release/RadLE_v2_public_sanitized_call_log.csv`, SHA-256 `87820f118c56e06617a52387b4d38e8b6a836ac98ec841a1ca102f86ec149ce9`, with 16 rows, 13 columns, and only MedGemma rows because the base public package had no sanitized call log file.
- The combined public manifest is `results/radle_v2_combined/public_release/RadLE_v2_public_manifest.json`, SHA-256 `880b8e7a6cbee4224ebf1987b11bc9cb747d78dcf015bb631302d2a40b79981c`, with run ID `radle_v2_plus_medgemma_1_5_4b`.
- The combined package manifest is `results/radle_v2_combined/append_package_manifest.json`, SHA-256 `d0718472b2b23054380835dd830aca85e8775664748482ad23efb6a934c94f93`.
- `z-ai/glm-5.2` is the current default LLM judge model; OpenRouter metadata reports it as `text->text`, which fits the intended text-only diagnosis adjudication.
- Confidence-weighted scoring is deterministic and separate from the LLM judge: `score_binary=1` gives `+Likert`, `score_binary=0` gives `-Likert`, and uncertain/null judge outputs leave the weighted score blank for review.
- `scripts/radle_llm_judge.py` is the dedicated LLM judge script. It writes safe copies by default and only overwrites existing score-bearing files when invoked with `--update-in-place --overwrite`.
- The safe apply validation output `outputs/radle_v2_stats_safe_apply_test/` has 5 populated `score_binary` rows and 5 signed `weighted_score` rows in its scored worklist, long-format copy, and public model results copy; it has 0 populated `score_likert` rows because the LLM is not allowed to assign a separate Likert correctness score. The original `results/radle_v2_combined/public_release/RadLE_v2_public_model_results.csv` still has 0 populated `score_binary` rows.

## Do Not Revisit

- Do not hardcode model names, model letters, or a fixed model count in new stats code. See Decision Log 2026-06-30.
- Do not treat the legacy `Model_A..J` script contract as the future RadLE v2 contract. See Decision Log 2026-06-30.
- Do not use `C:\Users\thehb\Downloads\RadLE v2 Answerkey - Sheet1.csv` as the answer key for this 200-case run without a separate case-mapping audit. See Decision Log 2026-06-30.
- Do not overwrite raw Workbench or benchmark outputs while preparing stats artifacts. See Decision Log 2026-06-30.
- Do not ship scorer views with all diagnoses grouped before all Likerts; reviewer-facing scorer views must be ordered as `Diagnosis_<model>, Likert_<model>` pairs. See Decision Log 2026-06-30.
- Do not apply test or partial LLM-judge scores in place to the combined/public package. Use safe-copy outputs until the judged batch has been reviewed and approved. See Decision Log 2026-06-30.

## Progress

- [x] (2026-06-30 15:38 IST, Codex/GPT-5) Created this ExecPlan after reading the global ExecPlan standard, the `execplan` skill, current repo guidance, relevant memory entries, current audit docs, and current CSV schemas.
- [x] (2026-06-30 19:04 IST, Codex/GPT-5) Located the first new Workbench result family, `results/medgemma_1_5_4b_medical_full_200_cases/`, and confirmed its final CSV has the same 200 cases and matching image metadata as the base v2 file.
- [x] (2026-06-30 19:04 IST, Codex/GPT-5) Added `scripts/radle_append_results.py`, a roster-agnostic append tool that discovers incoming model keys from `Diagnosis_<model_key>` columns, validates case ID/image metadata alignment, refuses duplicate model keys by default, and writes a manifest.
- [x] (2026-06-30 19:04 IST, Codex/GPT-5) Created the first combined derived CSV at `results/radle_v2_combined/final/RadLE_v2_results_final_plus_medgemma_1_5_4b.csv`; validation showed 200 rows, 179 columns, 11 diagnosis model columns, metadata mismatch count 0, and exact cell-level preservation of all base and incoming source values.
- [x] (2026-06-30 20:10 IST, Codex/GPT-5) Extended `scripts/radle_append_results.py` with `--key-columns` and created `results/radle_v2_combined/scorer/scorer_view_plus_medgemma_1_5_4b.csv`; validation showed 200 rows, 24 columns, 11 diagnosis columns, 11 Likert columns, metadata mismatch count 0, and exact source-cell preservation.
- [x] (2026-06-30 20:25 IST, Codex/GPT-5) Regenerated the combined scorer views after the user caught the grouped-column layout; `results/radle_v2_combined/scorer/scorer_view.csv` and `results/radle_v2_combined/scorer/scorer_view_plus_medgemma_1_5_4b.csv` now begin `Master_Case_ID`, `Associated_Images`, `Diagnosis_gpt_5_5`, `Likert_gpt_5_5`, `Diagnosis_claude_4_8_opus`, `Likert_claude_4_8_opus`.
- [x] (2026-06-30 20:25 IST, Codex/GPT-5) Added and validated whole-package append mode for `final/`, `scorer/`, and `public_release/`; canonical outputs now live under `results/radle_v2_combined/` with combined run ID `radle_v2_plus_medgemma_1_5_4b`.
- [x] (2026-06-30 19:53 IST, Codex/GPT-5) Added `scripts/radle_v2_stats.py` with `long`, `scoring-worklist`, and the initial `judge-score` command.
- [x] (2026-06-30 19:53 IST, Codex/GPT-5) Generated `outputs/radle_v2_stats/long_format.csv` and `outputs/radle_v2_stats/raw_qa_summary.json`; validation printed `case_count=200`, `model_count=11`, `rows=2200`, `score_required_count=1830`, `abstention_count=360`, and `technical_failure_count=10`.
- [x] (2026-06-30 19:53 IST, Codex/GPT-5) Generated `outputs/radle_v2_stats/scoring_worklist.csv`; validation printed `rows=2200` and `score_required=1830`.
- [x] (2026-06-30 19:53 IST, Codex/GPT-5) Ran a 5-row MedGemma LLM-judge smoke using `TEST_OPENROUTER_API_KEY` from `radle_api_keys.env`, `z-ai/glm-5.2`, and text-only prompts; output `outputs/radle_v2_stats/scoring_judged_test_key_smoke.csv` has 5 judged rows with expected negative weighted scores.
- [x] (2026-06-30 21:13 IST, Codex/GPT-5) Split LLM judging into `scripts/radle_llm_judge.py`, leaving `scripts/radle_v2_stats.py` with only `long` and `scoring-worklist`.
- [x] (2026-06-30 21:13 IST, Codex/GPT-5) Validated safe score propagation with no API call: `scripts/radle_llm_judge.py apply --scores outputs\radle_v2_stats\scoring_judged_test_key_smoke.csv --out-dir outputs\radle_v2_stats_safe_apply_test --long outputs\radle_v2_stats\long_format.csv --overwrite` wrote safe-copy scored files and left the original public results scoreless.
- [x] (2026-06-30 21:17 IST, Codex/GPT-5) Hardened `scripts/radle_llm_judge.py` so the prompt requests only binary/equivalence fields and output propagation blanks `score_likert`; validation showed safe public/worklist/long copies have 5 `score_binary`, 5 `weighted_score`, and 0 `score_likert` values.
- [ ] (pending, next implementation agent) Receive or locate additional Workbench result CSVs with expanded model rosters.
- [ ] (pending, next implementation agent) Run a larger GLM judge batch for MedGemma or all score-required rows after user approval of scale/spend.
- [ ] (pending, next implementation agent) Implement scored metrics only after the scoring join proves complete coverage or all remaining rows are explicitly marked for human review.
- [ ] (pending, next implementation agent) Add focused tests or fixture-driven validation for dynamic model counts, missing companion columns, and unscored-vs-scored gating.

## Surprises & Discoveries

- Observation: The current latest raw result has model-suffix columns such as `Diagnosis_gpt_5_5`, `Likert_gpt_5_5`, `Provider_gpt_5_5`, and `Raw_Response_gpt_5_5`, not old `Model_A` columns.
  Evidence: `py -3.11` schema probe on `results/radle_v2/final/RadLE_v2_results_final.csv` showed first columns beginning with `Master_Case_ID`, `Associated_Images`, `Image_SHA256`, `Diagnosis_gpt_5_5`, and `Likert_gpt_5_5`.
  Date/Author: 2026-06-30, Codex/GPT-5

- Observation: The ground-truth reference imported into `results/reference/` is locally correct but ignored by git.
  Evidence: SHA-256 matches the source from `C:\Users\thehb\Documents\RadLE Stats\RadLE_RSNA_Diagnosis_Scoring_key.csv`; `git check-ignore -v` reports `.gitignore:16:results/`.
  Date/Author: 2026-06-30, Codex/GPT-5

- Observation: The first new Workbench result is a one-model wide CSV with the same three metadata columns as the v2 baseline plus 16 columns suffixed `_medgemma_1_5_4b`.
  Evidence: Schema probe showed 19 columns: `Master_Case_ID`, `Associated_Images`, `Image_SHA256`, then `Diagnosis_medgemma_1_5_4b` through `Raw_Response_medgemma_1_5_4b`; case IDs, image hashes, and associated-images values match the current v2 baseline exactly.
  Date/Author: 2026-06-30, Codex/GPT-5

- Observation: The GLM judge smoke returned coherent text-only adjudications and deterministic negative marking.
  Evidence: First five MedGemma score-required rows all returned `score_binary=0`; Likert 3 rows produced `weighted_score=-3`, and a Likert 2 row produced `weighted_score=-2`.
  Date/Author: 2026-06-30, Codex/GPT-5

- Observation: The first scorer append passed row-count and cell-preservation checks but failed the user-facing column-order check.
  Evidence: Contradicting Artifact: the user pasted a scorer header where all `Diagnosis_*` columns appeared before all `Likert_*` columns, with the MedGemma diagnosis/Likert pair at the end. Missed Verification: the validation checked shape and source-cell preservation but did not assert reviewer-facing pair order. User View: the pasted header showed the grouped diagnosis block followed by the grouped Likert block.
  Date/Author: 2026-06-30, Codex/GPT-5

- Observation: The base `radle_v2` public package did not contribute a sanitized call-log file to the combined package.
  Evidence: `results/radle_v2_combined/public_release/RadLE_v2_public_sanitized_call_log.csv` has 16 rows from MedGemma only; this is expected for call logs and does not imply case-model duplicate failure.
  Date/Author: 2026-06-30, Codex/GPT-5

- Observation: The canonical scorer path named in the package plan was not present during the 21:08 validation pass.
  Evidence: `Get-ChildItem results\radle_v2_combined\scorer` showed `scorer_view_plus_medgemma_1_5_4b.csv` and scorer manifests, but no `scorer_view.csv`. The paired plus file remains present and valid. Do not depend on `scorer/scorer_view.csv` until it is regenerated intentionally.
  Date/Author: 2026-06-30, Codex/GPT-5

- Observation: The old 5-row smoke CSV included LLM-populated `score_likert` values, including a contradictory row with `score_binary=0` and `score_likert=3`.
  Evidence: Safe-copy inspection of `outputs/radle_v2_stats_safe_apply_test/scoring_judged.csv` before hardening showed the mismatch. The judge prompt and propagation now treat the LLM as binary-only and blank `score_likert`, while deterministic `weighted_score` carries signed Likert weighting.
  Date/Author: 2026-06-30, Codex/GPT-5

## Decision Log

- Decision: Build the RadLE v2 stats path around dynamic model discovery from result-file headers.
  Rationale: The user is actively producing more Workbench results and expects tomorrow's combined files to include 14-15 models instead of the current 9-10. Header-driven discovery avoids repeated code edits when the roster changes.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Decision: Keep the imported `scripts/radle_rsna_analysis.py` as a legacy reference unless a later implementation explicitly refactors it behind a dynamic adapter.
  Rationale: The script is useful for metric formulas and old outputs, but its fixed `MODEL_LETTERS = A..J` contract is the wrong boundary for the new raw result format.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: Use `results/reference/RadLE_RSNA_Diagnosis_Scoring_key.csv` as the confirmed source for case-level `Ground_Truth_Diagnosis`.
  Rationale: The user confirmed this is the correct file after inspecting its head, and the imported copy hash matches the older Stats source.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Decision: Split the pipeline into unscored raw-QA outputs and scored manuscript-metric outputs.
  Rationale: Raw result files can support validity, latency, provider, Likert, and parse-failure summaries without correctness scores. Accuracy, high-confidence error, ECE, and Spearman confidence-correctness metrics must wait for a complete scoring join.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: Stay in the Local checkout for planning. Create a `codex/radle-v2-stats-pipeline` branch before the first substantial implementation edit if the user wants this tracked cleanly.
  Rationale: The working tree already contains unrelated user changes and generated/imported files. Planning can happen locally; implementation should have a clearer branch boundary if it grows beyond a small script.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: Implement the new-model append step as a separate wide-CSV merger script before the long-format stats adapter.
  Rationale: The user is receiving new model results one by one, so the immediate operational need is to safely append one model-family at a time while preserving the original v2 and incoming files.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Decision: Use an LLM as a text-only correctness judge, not as an image reviewer.
  Rationale: The judge should compare `Ground_Truth_Diagnosis` and final model `diagnosis` text for synonym/equivalence. It must not infer from images or model reasoning, because the benchmark output already contains the final answer to be scored.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Decision: Keep confidence weighting outside the LLM judge.
  Rationale: The LLM's job is binary/equivalence adjudication. The negative marking rule should be deterministic and auditable on the native Likert scale: correct answers receive `+Likert`; wrong answers receive `-Likert`; uncertain judge outputs remain blank for human review.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Decision: Scorer views must use model-wise diagnosis/Likert pairs.
  Rationale: A grouped diagnosis block followed by a grouped Likert block is technically mergeable but poor for review. The user caught this directly, so `scripts/radle_append_results.py` now supports `--column-order diagnosis-likert-pairs`, and package mode uses it for `scorer/scorer_view.csv`.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Decision: Whole-package append mode is the operational default for adding new Workbench runs to the public package.
  Rationale: The user asked to append the whole package, including the public release. Package mode keeps `final/`, `scorer/`, and `public_release/` synchronized, rewrites public `run_id` values to the combined run ID, and writes a package manifest.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Decision: Split LLM judging from stats preparation.
  Rationale: `radle_v2_stats.py` should only shape wide results into long/worklist outputs. `scripts/radle_llm_judge.py` should own OpenRouter calls, score normalization, negative marking, audit logs, and score propagation to companion files.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Decision: Default LLM-judge propagation must be safe-copy mode.
  Rationale: The user explicitly does not want main/original files polluted by bad or partial test results. The judge script writes scored copies under `outputs/` by default; in-place updates require `--update-in-place --overwrite`.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Decision: The LLM judge must not populate `score_likert`.
  Rationale: The user-approved scoring rule is binary text equivalence plus deterministic signed Likert weighting from the model's own confidence. A separate LLM-generated Likert correctness score can contradict `score_binary`, so `score_likert` is left blank and `weighted_score` carries the negative-marking result.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

## Revision Notes

- v1 (2026-06-30, Codex/GPT-5): Started the RadLE v2 stats ExecPlan with the dynamic-roster constraint, confirmed ground-truth source, raw/scored output split, and implementation milestones.
- v2 (2026-06-30, Codex/GPT-5): Added the append-one-new-model workflow, first MedGemma result facts, combined output path, and `scripts/radle_append_results.py` validation results.
- v3 (2026-06-30, Codex/GPT-5): Added the dynamic long/worklist/judge script, GLM text-only judge decision, deterministic Likert-weighted negative marking, and 5-row test-key smoke evidence.
- v4 (2026-06-30, Codex/GPT-5): Added scorer-view append support through configurable key columns and recorded the combined MedGemma scorer artifact.
- v5 (2026-06-30, Codex/GPT-5): Recorded the user-caught scorer column-order correction, whole-package append mode, canonical combined output paths, public release hashes, and package validation state.
- v6 (2026-06-30, Codex/GPT-5): Split LLM-as-judge into `scripts/radle_llm_judge.py`, recorded safe-copy score propagation as the default, and reconciled the observed missing canonical scorer CSV.
- v7 (2026-06-30, Codex/GPT-5): Hardened the judge contract so the LLM only returns binary/equivalence fields, `score_likert` stays blank, and deterministic signed `weighted_score` is propagated to safe copies.

## Outcomes & Retrospective

The append-one-new-model workflow, whole-package append workflow, dynamic long-format export, scoring worklist generation, split LLM-judge script, safe score propagation, and small LLM-judge smoke are implemented and validated. Future stats work must remain roster-agnostic and must distinguish raw unscored QA, LLM-judged correctness scores, human-review flags, final scored metrics, and approved-vs-test score artifacts. At milestone completion, ask whether the dynamic-result-adapter checklist should be promoted into a reusable skill; do not create or update a skill without explicit user permission.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning and plan revision | `execplan` | This is a multi-step data/statistics pipeline with state that must survive tomorrow's combined results handoff. | `manual` |
| Data quality and scoring join audit | `data-analytics:analyze-data-quality` | Useful when checking one-to-one case coverage, missing scores, duplicate model-case pairs, and whether evidence is safe for metrics. | `auto-suggest` |
| Metric/report validation | `data-analytics:validate-data` | Useful before accepting accuracy, confidence-error, ECE, or manuscript-facing claims. | `auto-suggest` |
| Figure or dashboard work | `svg-panel-qa` or `data-analytics:visualize-data` | Only needed if this pipeline regenerates charts, SVGs, dashboards, or figure panels. | `manual` |
| Routine coding | `none` | The core adapter can be implemented directly in Python with focused tests. | `none` |

## Context And Orientation

This repo is the active RadLE v2 workspace at `C:\Users\thehb\Documents\RadLE v2`. Current benchmark outputs live locally under `results/`, but `.gitignore` excludes `results/`, `*.csv`, `*.xlsx`, and generated result artifacts. The older separate stats workspace is `C:\Users\thehb\Documents\RadLE Stats`; it contains old 10-model RSNA scripts and outputs, including `radle_rsna_analysis.py` and `outputs\Raw Outputs\long_format.csv`.

The current raw result CSV is wide: each case is one row, and each model contributes a family of columns named with a suffix. For example, `Diagnosis_gpt_5_5` and `Likert_gpt_5_5` belong to model key `gpt_5_5`. A canonical long table means one row per `(Master_Case_ID, model_key)`, with common columns such as diagnosis, Likert score, provider, latency, token counts, response validity, and eventually correctness score.

The confirmed ground-truth reference has `Master_Case_ID` and `Ground_Truth_Diagnosis`, plus old `Diagnosis_Model_A..J` and `Score_Model_A..J` columns. The old scores may be useful as provenance for exact-output reuse in some cases, but they must not be treated as complete scores for new or changed Workbench model outputs.

## Plan Of Work

Milestone 0 is incoming result-package accumulation. As each new one-model or multi-model Workbench result package arrives, run `scripts/radle_append_results.py --package` with the latest combined run directory as `--base-run-dir` and the new run directory as `--incoming-run-dir`. This produces synchronized combined `final/`, `scorer/`, and `public_release/` files plus a package manifest, while leaving both source run directories unchanged. The script must keep rejecting duplicate model keys unless `--replace-existing-model` is deliberately supplied.

Milestone 1 is input discovery and schema locking. When a combined Workbench result is ready, inspect the header and derive `model_key` values from every `Diagnosis_<model_key>` column. Validate that each discovered model has at least `Diagnosis_<model_key>` and `Likert_<model_key>`. Companion columns such as `Provider_<model_key>`, `Latency_<model_key>`, `Prompt_Tokens_<model_key>`, `Total_Tokens_Out_<model_key>`, `Reasoning_Tokens_<model_key>`, `Raw_Response_<model_key>`, and structured validity/error columns should be optional but captured when present.

Milestone 2 is the raw-to-long adapter. Add a new dynamic script, preferably `scripts/radle_v2_stats.py`, rather than making the legacy imported script more complex immediately. The script should expose a command such as:

    py -3.11 scripts\radle_v2_stats.py long --input <combined_results.csv> --ground-truth results\reference\RadLE_RSNA_Diagnosis_Scoring_key.csv --out outputs\radle_v2_stats

The long output should include `run_id`, `Master_Case_ID`, `model_key`, `Ground_Truth_Diagnosis`, `diagnosis`, `likert`, `provider`, `latency`, token columns when present, `abstained`, `technical_failure`, and `response_valid` where derivable. It should also write a machine-readable QA summary with `case_count`, `model_count`, `model_keys`, `expected_rows`, `actual_rows`, missing companion columns, duplicate keys, and ground-truth join coverage.

Milestone 3 is the scoring worklist. Generate a CSV that contains one row per `(Master_Case_ID, model_key)` requiring correctness review. It should include ground truth, model diagnosis, Likert, raw validity fields, and blank scoring fields such as `score_binary`, `score_likert`, `scorer_notes`, and `score_source`. If an exact prior output match is ever reused from the old scoring key, mark it explicitly as `score_source=reused_prior_exact_diagnosis_match`; do not silently blend reused and newly reviewed scores.

Milestone 4 is the scored metrics layer, which is not implemented yet. When score coverage is complete, add a command such as:

    py -3.11 scripts\radle_v2_stats.py metrics --long outputs\radle_v2_stats\long_format.csv --scores outputs\radle_v2_stats\scoring_completed.csv --out outputs\radle_v2_stats

This future command must refuse final metric output if any answered, scoreable model-case pair lacks a correctness score. It may write partial QA output only if invoked with an explicit `--allow-partial` flag that marks every result as partial and not for submission.

Milestone 5 is validation and optional downstream integration. Update or add tests and fixtures so the adapter works with 10, 14, 15, and missing-companion-column model counts. Only after the long and scored metrics outputs are validated should figure scripts or manuscript table scripts consume the new outputs.

Execution posture: stay in `Local` unless the user asks for parallel work. If implementation begins before the combined file arrives, create small fixture CSVs only and keep generated outputs under ignored output paths. If implementation touches more than one script or test file, create branch `codex/radle-v2-stats-pipeline` first unless the user directs otherwise.

## Milestones

Milestone 0, append incoming result packages. Skill: `none`. The result is a combined package containing `final/RadLE_v2_results_final.csv`, `scorer/scorer_view.csv`, public release files, and a package manifest after each incoming model run, preserving all source files unchanged.

Milestone 1, combined input orientation. Skill: `data-analytics:analyze-data-quality` auto-suggest. The result is a short schema report that lists discovered model keys and proves the file can be interpreted without a hardcoded roster.

Milestone 2, dynamic long-format adapter. Skill: `none`. The result is a script command that turns any compatible wide RadLE result CSV into a long table with one row per case-model pair.

Milestone 3, scoring worklist and ground-truth join. Skill: `data-analytics:analyze-data-quality` auto-suggest. The result is a review-ready scoring CSV with complete case-level ground truth and no duplicate `(Master_Case_ID, model_key)` rows.

Milestone 4, scored metrics. Skill: `data-analytics:validate-data` auto-suggest. The result is a metrics table that computes accuracy/confidence metrics only when correctness scores are complete.

Milestone 5, downstream outputs. Skill: `svg-panel-qa` or `data-analytics:visualize-data` manual. The result is updated chart/table generation only after the numeric outputs are validated.

## Concrete Steps (Commands)

From `C:\Users\thehb\Documents\RadLE v2`, inspect the current known raw input:

    py -3.11 -c "import pandas as pd; p=r'results\radle_v2\final\RadLE_v2_results_final.csv'; df=pd.read_csv(p,nrows=0,encoding='utf-8-sig'); print(len(df.columns)); print([c for c in df.columns if c.startswith('Diagnosis_')])"

Expected for the current known file: 163 columns and 10 `Diagnosis_...` model columns. For tomorrow's combined file, the same command should print the larger model roster without code changes.

Append the first incoming model result:

    py -3.11 scripts\radle_append_results.py --base results\radle_v2\final\RadLE_v2_results_final.csv --incoming results\medgemma_1_5_4b_medical_full_200_cases\final\RadLE_v2_results_final.csv --output results\radle_v2_combined\final\RadLE_v2_results_final_plus_medgemma_1_5_4b.csv

Expected: 200 rows, 163 base columns, 16 incoming append columns, 179 output columns, appended model key `medgemma_1_5_4b`, and a manifest at `results\radle_v2_combined\final\RadLE_v2_results_final_plus_medgemma_1_5_4b.csv.manifest.json`.

Append the whole first incoming package, including public release files:

    py -3.11 scripts\radle_append_results.py --package --base-run-dir results\radle_v2 --incoming-run-dir results\medgemma_1_5_4b_medical_full_200_cases --output-run-dir results\radle_v2_combined --combined-run-id radle_v2_plus_medgemma_1_5_4b --overwrite

Expected: canonical combined outputs at `results\radle_v2_combined\final\RadLE_v2_results_final.csv`, `results\radle_v2_combined\scorer\scorer_view.csv`, and `results\radle_v2_combined\public_release\`. The scorer header must begin with diagnosis/Likert pairs, not grouped diagnosis and Likert blocks:

    Master_Case_ID, Associated_Images, Diagnosis_gpt_5_5, Likert_gpt_5_5, Diagnosis_claude_4_8_opus, Likert_claude_4_8_opus, ...

Validation from the first whole-package append:

    final: shape (200, 179), sha256 80f6fcdc4a73be803841a55afd48651b474746d35b2bf855a4c7eff4f0e3b260
    scorer: shape (200, 24), sha256 bcbf0bff74140694291540b66603da0db0e09288251a1b2da0d99632e6f6e54b
    public model results: shape (2200, 14), 11 models, duplicate_case_model 0
    public model summary: shape (20, 13), 11 models
    public sanitized call log: shape (16, 13), MedGemma-only because the base package had no sanitized call log
    public run_id values: ['radle_v2_plus_medgemma_1_5_4b']

Validation from the first append run:

    rows=200
    base_columns=163 incoming_append_columns=16 output_columns=179
    appended_model_keys=medgemma_1_5_4b
    output_sha256=80f6fcdc4a73be803841a55afd48651b474746d35b2bf855a4c7eff4f0e3b260
    base_cells_equal True
    incoming_cells_equal True
    out_shape (200, 179)

Inspect the confirmed ground-truth file:

    py -3.11 -c "import pandas as pd; p=r'results\reference\RadLE_RSNA_Diagnosis_Scoring_key.csv'; df=pd.read_csv(p,encoding='utf-8-sig'); print(df.shape); print(df[['Master_Case_ID','Ground_Truth_Diagnosis']].head().to_string(index=False))"

Expected: shape `(200, 25)` and first ground-truth rows beginning with case 1 `CCF`, case 2 `OSMOTIC DEMYELINATION`, and case 3 `LHERMITE - DUCLOS DISEASE`.

After package append, run the dynamic adapter on the canonical combined final:

    py -3.11 scripts\radle_v2_stats.py long --input results\radle_v2_combined\final\RadLE_v2_results_final.csv --ground-truth results\reference\RadLE_RSNA_Diagnosis_Scoring_key.csv --out outputs\radle_v2_stats

Expected for the current combined file: `case_count=200`, `model_count=11`, `expected_rows=2200`, `actual_rows=2200`, and no duplicate `(Master_Case_ID, model_key)` pairs. For a 15-model combined file, expected rows should be `200 * 15 = 3000`.

Preview judge prompts without making API calls or writing files:

    py -3.11 scripts\radle_llm_judge.py score --worklist outputs\radle_v2_stats\scoring_worklist.csv --out-dir outputs\radle_v2_stats_dry_run --models medgemma_1_5_4b --limit 2 --dry-run

Expected: the command prints two text-only prompts and ends with `dry_run=true; no API calls or files written`.

Apply an existing judged smoke CSV to safe-copy score outputs without API calls:

    py -3.11 scripts\radle_llm_judge.py apply --scores outputs\radle_v2_stats\scoring_judged_test_key_smoke.csv --out-dir outputs\radle_v2_stats_safe_apply_test --long outputs\radle_v2_stats\long_format.csv --overwrite

Expected: the command prints `safe_copy_mode=true; original combined/public files will not be overwritten`, then writes `outputs\radle_v2_stats_safe_apply_test\scoring_judged.csv`, `outputs\radle_v2_stats_safe_apply_test\long_format_scored.csv`, and scored public-release copies under `outputs\radle_v2_stats_safe_apply_test\public_release\`.

When scored metrics are later implemented and score coverage is complete, run the future metrics command:

    py -3.11 scripts\radle_v2_stats.py metrics --long outputs\radle_v2_stats\long_format_scored.csv --scores outputs\radle_v2_stats\scoring_completed.csv --out outputs\radle_v2_stats

Expected after implementation: the command writes scored metrics only if every scoreable answered row has a correctness score. Missing scores should cause a clear nonzero exit before manuscript-facing outputs are written.

## Validation And Acceptance

The dynamic adapter is accepted when it passes all of these checks:

- It discovers model keys from the input header and does not contain constants listing the expected 10, 14, or 15 model names as the control path.
- It writes exactly `case_count * model_count` long rows.
- Every `(Master_Case_ID, model_key)` pair is unique.
- Every raw case joins to one `Ground_Truth_Diagnosis`.
- It handles missing optional companion columns by recording QA warnings, not by crashing unnecessarily.
- It refuses to compute accuracy, high-confidence error, very-high-confidence error, ECE, or Spearman confidence-correctness metrics without correctness scores.
- It derives all denominator text from observed data, not hardcoded "2,000 interpretations" prose.

The whole-package append layer is accepted when it passes all of these checks:

- It produces synchronized combined `final/`, `scorer/`, and `public_release/` outputs from a base run directory and an incoming run directory.
- The scorer view orders each model as `Diagnosis_<model>, Likert_<model>` pairs.
- The public case-model table has no duplicate `(case_uid, model)` pairs for the combined run ID.
- Public model results, model summary, and sanitized call log rows use the combined run ID.
- Raw source run directories are preserved byte-for-byte.

The split LLM-judge layer is accepted when it passes all of these checks:

- `scripts/radle_v2_stats.py --help` lists only `long` and `scoring-worklist`.
- `scripts/radle_llm_judge.py --help` lists `score` and `apply`.
- `score --dry-run` prints prompts and makes no API calls or file writes.
- `apply` can propagate an existing judged CSV to safe-copy scored worklist, long-format, public model results, public model summary, and a summary JSON.
- By default, the original combined/public files keep 0 populated test score rows; in-place mutation requires `--update-in-place --overwrite`.
- Public model summary mean scores stay blank for partial score coverage unless `--allow-partial-summary` is explicitly used.

The scored metrics layer is accepted when it passes all of these checks:

- It refuses final output if any answered, scoreable pair lacks a correctness score.
- It reports `model_count`, `case_count`, score coverage, abstention counts, technical-failure counts, and provider distribution from data.
- It can process fixture files with 10, 14, and 15 discovered models without code changes.
- It preserves raw input files byte-for-byte.

If this work generates visual artifacts such as SVGs, PDFs, dashboards, or figure panels, read the relevant visual-verification skill before adding the visualization milestone's validation steps. No visual artifact is in scope for the initial dynamic adapter.

## Idempotence And Recovery

All adapter and metrics commands must be safe to rerun. They should create or overwrite only files under a caller-provided output directory such as `outputs/radle_v2_stats/`. They must never edit `results/radle_v2/final/RadLE_v2_results_final.csv`, tomorrow's combined input file, or `results/reference/RadLE_RSNA_Diagnosis_Scoring_key.csv`. LLM-judge commands must write safe copies by default and must require `--update-in-place --overwrite` before mutating an existing score-bearing combined/public file.

If a run fails halfway, delete or move only the generated output directory and rerun the command. If the ground-truth join fails, stop and inspect case IDs before producing downstream outputs. If model discovery produces an unexpected roster, stop and print the discovered model keys rather than falling back to a hardcoded list.

## Artifacts And Notes

Current schema probe for the known raw file:

    FILE C:\Users\thehb\Documents\RadLE v2\results\radle_v2\final\RadLE_v2_results_final.csv
    exists True
    sha256 53543631d657349e848b38ea57632d07efbc33c22b72a24733ae107bc84d3d9c
    columns 163
    first_columns ['Master_Case_ID', 'Associated_Images', 'Image_SHA256', 'Diagnosis_gpt_5_5', 'Likert_gpt_5_5', ...]

Current schema probe for the confirmed ground-truth reference:

    FILE C:\Users\thehb\Documents\RadLE v2\results\reference\RadLE_RSNA_Diagnosis_Scoring_key.csv
    exists True
    sha256 5d26771da27cf8fef1a7f48204257c65b8e1f7b41423763f2e45cb384fb738d4
    columns 25
    first_columns ['Master_Case_ID', 'Associated_Images', 'Image_SHA256', 'Ground_Truth_Diagnosis', ...]

Ground-truth head:

    Master_Case_ID      Ground_Truth_Diagnosis
                 1                         CCF
                 2       OSMOTIC DEMYELINATION
                 3   LHERMITE - DUCLOS DISEASE
                 4 ANTERIOR SACRAL MENINGOCELE
                 5            BAASTRUP DISEASE

## Interfaces And Dependencies

Target append script interface:

- `scripts/radle_append_results.py --package --base-run-dir <base_run_dir> --incoming-run-dir <incoming_run_dir> --output-run-dir <combined_run_dir> --combined-run-id <combined_run_id> [--overwrite]`
- `scripts/radle_append_results.py --base <base_csv> --incoming <incoming_csv> --output <combined_csv> [--key-columns <columns>] [--column-order preserve|diagnosis-likert-pairs] [--overwrite]`

Target stats script interface:

- `scripts/radle_v2_stats.py long --input <wide_results.csv> --ground-truth <ground_truth.csv> --out <output_dir>`
- `scripts/radle_v2_stats.py scoring-worklist --long <long_format.csv> --out <output_dir>`

Target judge script interface:

- `scripts/radle_llm_judge.py score --worklist <scoring_worklist.csv> --out-dir <output_dir> [--models <model_key>] [--limit <n>] [--audit-log <jsonl>]`
- `scripts/radle_llm_judge.py apply --scores <judged_scoring.csv> --out-dir <output_dir> [--long <long_format.csv>]`
- Add `--update-in-place --overwrite` only after judged outputs are approved and the target files should intentionally be overwritten.

Future scored metrics interface:

- `scripts/radle_v2_stats.py metrics --long <scored_long_format.csv> --scores <scored_pairs.csv> --out <output_dir> [--allow-partial]`

Target output files:

- `outputs/radle_v2_stats/long_format.csv`
- `outputs/radle_v2_stats/raw_qa_summary.json`
- `outputs/radle_v2_stats/scoring_worklist.csv`
- `outputs/radle_v2_stats/scoring_judged.csv`
- `outputs/radle_v2_stats/long_format_scored.csv`
- `outputs/radle_v2_stats/public_release/RadLE_v2_public_model_results.csv`
- `outputs/radle_v2_stats/public_release/RadLE_v2_public_model_summary.csv`
- `outputs/radle_v2_stats/score_update_summary.json`
- `outputs/radle_v2_stats/results_table.csv`
- `outputs/radle_v2_stats/analysis_log.txt`

Use `py -3.11` for local execution. Current local dependencies are adequate for the legacy script path: `pandas`, `numpy`, and `scipy` are available. Prefer the Python standard library plus `pandas` for the adapter. Do not add heavy dependencies for simple CSV reshaping.
