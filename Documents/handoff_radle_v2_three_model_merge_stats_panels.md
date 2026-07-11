# RadLE v2 Three-Model Merge, Scoring, and Panels Handoff

Status note, 2026-07-12: this is a historical pre-M7 handoff artifact retained for evidence. For future execution, start with `Documents/execplan_radle_v2_incremental_model_admission.md`, especially the `Repeatable Admission SOP` and `Colab Output To SVG Command Index` sections.

## Mission

Admit the completed Grok 4.5, GPT-5.6 Sol Pro, and Meta Muse Spark 1.1 results into the frozen RadLE v2 comparator universe, score only their 600 new case-model rows, then regenerate the IDK0 Score1000/Score2000 statistics and panels.

Do not restart repository archaeology. Do not rerun models. Do not rescore or rewrite any existing model or human row.

## Start Here

Work from:

`C:\tmp\radle_v2_pre_m7_repair`

Branch:

`codex/radle-v2-pre-m7-repair`

Current implementation HEAD is `70700d1`. Two reviewer findings were fixed locally but are not committed yet:

- `src/radle_incremental_admission.py` now requires the exact radiologist-overlay schema and a valid timezone-aware UTC timestamp.
- `audit_idk0_score_lane()` now independently rebuilds the lane from committed inputs and compares every output byte.
- `tests/test_radle_incremental_admission.py` contains regressions for both findings.

Targeted tests for these fixes passed. The full 31-test rerun was interrupted by the user and must be rerun once, followed by one independent read-only re-review. Keep this bounded; do not open another research cycle.

## Ready Source

Mounted Drive source:

`G:\.shortcut-targets-by-id\1QPf3Z_T0Y-XXw3UC7xyk8y_BE4U07q2a\RaDLE\CONFIDENTIAL\RadLE v2 Dataset\Runs\radle_v2`

Immutable local seal:

`C:\tmp\radle_v2_incoming_sealed\20260710_095126_radle_v2`

Promoted wide master:

`C:\tmp\radle_v2_incoming_sealed\20260710_095126_radle_v2\final\RadLE_v2_results_final.csv`

Verified facts:

- Shape: 200 rows x 259 columns.
- SHA256: `91B641C0953B6A81FF25B2BD962AEA6FF8ACB22E9D605976D4F2509CEC276311`.
- Case/image fingerprint: `d65221a441c5687cd44d11df689072969d6bbe69089ab0eacaf84cb69ab28dd7`, exactly matching the frozen base.
- Grok 4.5: 200 accepted cells; 175 clean diagnoses and 25 valid exact-IDK responses.
- GPT-5.6 Sol Pro: 200/200 accepted clean diagnoses.
- Muse Spark 1.1: 200/200 accepted clean diagnoses.
- Zero paid-repair, cleanup, or unresolved cells.
- Returned routes: `x-ai/grok-4.5-20260708`, `openai/gpt-5.6-sol-pro-20260709`, and `muse-spark-1.1`.

The source is one combined wide CSV containing all three new column families. Project one sealed package per model; never replace the official base with this 259-column source.

## Provenance Reconciliation

The producer manifest records a full 200-case run as `"test_limit": "full"` instead of JSON `null`, and it omits `runtime_sha`. Preserve that original manifest unchanged.

The notebook fetched branch `codex/morning-meta-muse-spark-append`. The likely runtime commit is `8029ad46d90b7bc8ab67af1e805ffaa2619b85a2`, which predates the run and is the current remote branch tip. Record this as inferred until confirmed from Colab setup output or another immutable receipt. Do not fabricate evidence and do not rerun the models for this metadata-only gap.

## Locked Admission Semantics

- Append only.
- Existing 6,000 long-master rows and their scores remain frozen and byte-identical.
- Models are one reader x 200 cases.
- Candidate labels: Grok 4.5 `AE`, GPT-5.6 `AF`, Muse Spark `AG`.
- Grok 4.5 replaces Grok 4.3; GPT-5.6 replaces GPT-5.5.
- Replaced models remain in committed data with an excluded flag; they disappear only from active panel order.
- Muse Spark is a new active contender.
- IDK0 is locked. Exact/approved IDK scores zero.
- Technical failures and invalid Likert values score zero. Likert `8` is invalid and scores zero.
- Only new rows may enter automatic matching, AI judging, or radiologist adjudication.
- Radiologist review receives case number, blinded candidate label, ground truth, and candidate diagnosis only.
- Twelve human backend readers remain frozen. `pooled12` and `split6x6` are presentation projections only.
- Produce both Score1000 and Score2000. Score2000 equals Score1000 + 1000 and changes no rank or state.
- Active models sort descending by Score2000. Human baseline comparator(s) remain leftmost.

## Execution Order

1. Review the two local repair hunks, run the 31 tests and production-shape acceptance once, obtain a fresh independent PASS receipt, commit/push the repair branch, and record `PRE_M7_REPAIR_RESULT=PASS` in both plans.
2. Inventory and project the sealed 259-column source into three one-model packages. Preserve the source seal and original manifests. Resolve the runtime-SHA metadata by confirmation or an explicit provenance exception receipt.
3. Admit sequentially in roster order: Grok 4.5, then GPT-5.6, then Muse Spark. Every later admission must validate the preceding `COMMITTED.json` parent chain.
4. Confirm each admission appends exactly 200 parsed rows in the existing 20-column header order and leaves the parent bytes as an exact prefix.
5. Score only the 600 appended rows using terminal rules, current validated diagnosis variants, and dual judges only where still required. Send only unresolved judge disagreements/review flags to the radiologist queue.
6. Build the committed IDK0 lane and verify `score_rows.csv`, `source1000.csv`, `group_summary.csv`, `panel_bins.csv`, public summary, and active-only panel order.
7. Selectively bring panel scripts/assets from `codex/radle-v2-primary-preservation`; do not merge that branch wholesale.
8. Regenerate statistics and panels, confirm old comparator values are unchanged, confirm replacements/exclusions, and produce a compact before/after audit.

No paid judge call without a matching unexpired `paid_judge_authorization.json`. Default judge mode remains dry-run.

## Reading Order

Repair worktree:

1. `Documents/requirements_radle_v2_incremental_model_admission.md`
2. `Documents/radle_v2_incremental_model_pipeline_requirements_study.md`
3. `Documents/execplan_radle_v2_incremental_model_admission.md`
4. `Documents/execplan_radle_v2_pre_m7_production_repair.md`
5. `review/pre_m7_production_repair_review.json` (FAIL against `70700d1`; its two findings are locally fixed and require re-review)
6. `review/runtime_reconciliation_review.json`
7. `src/radle_incremental_admission.py`
8. `tests/test_radle_incremental_admission.py`

Preservation worktree `C:\tmp\radle_v2_primary_preservation`, reviewed/pushed at `5e6fd51`:

1. `review/primary_preservation_review.json`
2. `preservation/primary_worktree_manifest.json`
3. `Documents/execplan_radle_v2_idk0_score2000_svg_lane.md`
4. `scripts/audit_radle_v2_score1000_panel23_IDK0.py`
5. `scripts/make_radle_v2_score1000_panel23_svg_IDK0.py`

## Paste-Ready Prompt

You are continuing RadLE v2 incremental admission. Read `C:\tmp\radle_v2_pre_m7_repair\Documents\handoff_radle_v2_three_model_merge_stats_panels.md` first and follow its reading order. Work from `C:\tmp\radle_v2_pre_m7_repair` on `codex/radle-v2-pre-m7-repair`.

The three completed model outputs are already sealed at `C:\tmp\radle_v2_incoming_sealed\20260710_095126_radle_v2`; do not rerun models. Keep the next work strictly on the critical path: close the two already-fixed pre-M7 reviewer findings with one bounded test/re-review cycle, then project and sequentially append Grok 4.5, GPT-5.6 Sol Pro, and Muse Spark 1.1, score only their 600 new rows, and regenerate the IDK0 Score1000/Score2000 stats and panels. Existing 6,000 long-master rows and scores are immutable.

Do not do more branch archaeology. Do not merge the preservation branch wholesale. Do not make paid judge calls without authorization. Report exact hashes, row counts, terminal-state counts, judge/radiologist queue counts, old-score immutability proof, and final panel artifacts.
