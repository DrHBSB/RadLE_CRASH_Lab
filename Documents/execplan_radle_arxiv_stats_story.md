# RadLE arXiv stats-story review

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `AGENTS.md` or `PLANS.md` exists in this worktree; the user-provided AGENTS instruction says to place ExecPlans under `Documents/` when available.

## Purpose / Big Picture

The user asked to read the RadLE arXiv paper and use it to improve the basic questions and graph/story framing for RadLE v2 stats. After this pass, a future agent should know which paper claims matter, which local v2 summary artifacts are current, and what graph improvements should be prioritized before regenerating manuscript-facing figures.

## Current State

Current state (2026-07-06 02:26 +05:30, Codex/GPT-5): Work is in the separate worktree `C:\Users\thehb\Documents\RadLE v2 - final scoring questions` on branch `codex/final-scoring-csv-questions`. The arXiv HTML for `arXiv:2509.25559` has been read for benchmark framing. The current v2 final-scoring folder now contains `radle_v2_final_long_master.csv`, audit JSON, summary CSVs, and `SUMMARY_SPEC.md`. The old RadLE Stats figure package has been inspected for its six-panel confidence-risk story, and v2 confidence-risk quantities were derived from the master. Next: deliver chat synthesis; do not generate new figures unless the user asks.

## Locked Facts

- RadLE v1 arXiv frames the benchmark as difficult expert-level spot diagnoses where radiologists and trainees are explicit comparator cohorts.
- RadLE v1 reports overall accuracy, modality/system slices, repeatability, latency/reasoning considerations, and a visual-reasoning error taxonomy.
- Current v2 final folder is `C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147`.
- Current v2 master SHA-256 is `83d469f03f78396dc0cfff03703f8d9ca22c8df82ff2e73ee0193a2832e8dac9`, with 6000 rows, 30 statistical rows in `model_summary.csv`, 200 cases, and 1255 correct.
- Manuscript-facing human comparisons must use qualification/experience categories, not individual names. The individual-reader rows are supporting data only.
- The paper-facing non-excluded AI comparison has 15 AI model arms; the 12 individual human rows should collapse to role/seniority/experience categories.
- Current v2 rollup spec defines strict accuracy, attempted accuracy, Wilson 95% CIs, signed mean weighted score, and non-excluded vs excluded universes.
- The old RadLE Stats figure family under `C:\Users\thehb\Documents\RadLE Stats\outputs\Data visualization` emphasized confidence-risk, calibration, peak-certainty PPV, safety shield, and confidence volume.

## Do Not Revisit

- Do not claim the current final folder lacks audit/summaries; files exist with 2026-07-06 02:10-02:14 timestamps.
- Do not treat `candidate` alone as a unique arm identifier; `SUMMARY_SPEC.md` locks `candidate, provider, access, domain`.
- Do not use old v1/V1.5 confidence-risk metrics as if they already exist for v2 without deriving them from the v2 master.
- Do not describe the manuscript-facing universe as "27 arms"; that incorrectly counts individual human names as arms.

## Progress

- [x] (2026-07-06 02:22 +05:30, Codex/GPT-5) Created this plan after reading the execplan skill, `~/.codex/PLANS.md`, relevant memory entries, arXiv HTML, v2 final summary artifacts, and old RadLE Stats figure metadata.
- [x] (2026-07-06 02:22 +05:30, Codex/GPT-5) Verified the v2 final folder now contains audit and rollup files: `final_scoring_audit.json`, `SUMMARY_SPEC.md`, `model_summary.csv`, `provider_summary.csv`, `access_summary.csv`, `domain_summary.csv`, `human_role_summary.csv`, `seniority_summary.csv`, and `appendix_within_provider_deltas.csv`.
- [x] (2026-07-06 02:24 +05:30, Codex/GPT-5) Read the Data Analytics `visualize-data` skill and applied it to chart-choice recommendations without rendering new visuals.
- [x] (2026-07-06 02:26 +05:30, Codex/GPT-5) Derived v2 confidence-risk quantities from the master for non-excluded access/domain/role groups and per-arm peak-confidence wrong burden.
- [x] (2026-07-06 02:31 +05:30, Codex/GPT-5) Incorporated user correction: individual human names do not matter for the stats story; humans should be grouped by experience/qualification.
- [x] (2026-07-06 02:33 +05:30, Codex/GPT-5) Computed two possible human two-bin groupings from the final master: qualification split and experience-gradient split.
- [ ] (pending) Deliver a concise recommendation set for questions to retire, questions to keep, and improved stats-story figures.

## Surprises & Discoveries

- Observation: A first narrow listing saw only the master CSV, but a later direct listing showed the companion files exist.
  Evidence: `Get-ChildItem` on the final folder lists summary/audit files with 2026-07-06 02:10-02:14 timestamps.
  Date/Author: 2026-07-06, Codex/GPT-5

- Observation: The v2 human aggregate differs from the simple RadLE v1 hierarchy because trainees slightly exceed radiologists in strict aggregate accuracy while abstention behavior differs by reader.
  Evidence: `human_role_summary.csv` shows Trainee accuracy 0.4040 and Radiologist accuracy 0.3714; attempted accuracy is 0.4709 vs 0.4392.
  Date/Author: 2026-07-06, Codex/GPT-5

- Observation: The earlier "27 arms" phrasing was wrong for manuscript purposes because it counted individual human names.
  Evidence: User correction on 2026-07-06; `model_summary.csv` has 15 non-excluded AI rows, 3 excluded AI rows, and 12 individual human rows, while `human_role_summary.csv` and `seniority_summary.csv` provide category-level human comparisons.
  Date/Author: 2026-07-06, Codex/GPT-5

- Observation: In the recommended qualification split, trainees outperform post-MD radiologists in this aggregate.
  Evidence: From `radle_v2_final_long_master.csv`, Radiology Trainees have n=1000, correct=404, strict accuracy=0.4040, attempted accuracy=0.4709; Post-MD Radiologists have n=1400, correct=520, strict accuracy=0.3714, attempted accuracy=0.4392.
  Date/Author: 2026-07-06, Codex/GPT-5

## Decision Log

- Decision: Treat the arXiv paper as narrative/methodological context, not as an instruction to copy v1 metrics exactly.
  Rationale: v2 has 200 cases, 30 arms, human seniority, excluded twins, open/closed/medical domains, and authoritative binary scoring; the graph set must reflect these additional axes.
  Date/Author: 2026-07-06, Codex/GPT-5

- Decision: Keep graph recommendations data-first and defer implementation.
  Rationale: The user asked for reading and suggestions, not figure regeneration.
  Date/Author: 2026-07-06, Codex/GPT-5

- Decision: Collapse humans into qualification/experience categories for all main stats-story figures.
  Rationale: Individual names are not meaningful manuscript entities; the scientific question is where AI sits relative to trainees, radiologists, and seniority/experience tiers.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

## Revision Notes

- v1 (2026-07-06, Codex/GPT-5): Initial plan for arXiv-grounded stats-story review.

## Outcomes & Retrospective

Pending final synthesis. No reusable skill should be created from this pass without explicit user permission.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | The task spans web literature, local data artifacts, old figure packages, and future graph recommendations. | `manual` |
| Data quality check | `none` | Direct CSV inspection is sufficient for this lightweight pass. | `none` |
| Chart recommendation | `data-analytics:visualize-data` | Used for chart-family choice, denominator discipline, and graph QA framing. | `manual` |
| Future figure generation | `svg-panel-qa`, `skill-paperbanana`, or `data-analytics:visualize-data` | Use only if the user asks to regenerate or package figures. | `manual` |

## Context And Orientation

The v2 final scoring artifacts are local generated files outside this worktree at `C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147`. The old RadLE Stats figure package is in a separate non-git workspace at `C:\Users\thehb\Documents\RadLE Stats\outputs\Data visualization`. This plan is saved in the worktree only, so it does not mutate the main checkout's generated outputs.

## Plan Of Work

1. Read the RadLE arXiv paper for the core benchmark story: comparator hierarchy, dataset bias, evaluation limits, reproducibility, and failure taxonomy.
2. Inspect v2 summary artifacts to identify which questions are already answered by evidence.
3. Compare the old six-panel confidence-risk figure family with v2's richer cohort and source-mix fields.
4. Provide graph recommendations grouped by main figure, supplementary figure, and caution/denominator rules.

## Validation And Acceptance

Success for this analysis pass is a final chat response that cites the arXiv source, names the local evidence paths, corrects stale earlier questions, and gives concrete graph/story changes that can be implemented later.

## Idempotence And Recovery

This plan is additive and safe to reread. If future figure generation starts, create or update a separate figure-specific ExecPlan and verify generated SVG/PDF/HTML artifacts visually before delivery.
