# Audit IDK0 Pipeline Integration With Morning Outputs

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `AGENTS.md` or `PLANS.md` was found by `rg --files -g 'AGENTS.md' -g 'PLANS.md'` on 2026-07-09.

## Purpose / Big Picture

The user asked how well the `idk0` pipeline is integrated with the kinds of files produced by the Morning benchmark path. This audit should answer from current repo evidence, not memory alone: identify the Morning output contract, identify the IDK0 pipeline inputs and outputs, then compare where the contracts align, where adapters exist, and where manual or sidecar assumptions remain.

## Current State

Current state (2026-07-09 12:20 +05:30, Codex/GPT-5): Audit complete. Morning produces wide per-case result files under `Runs/<run_id>/...` or local `results/radle_v2/...`; IDK0 is strongly integrated from the already-scored long master onward, but only indirectly integrated with Morning outputs through separate long/scoring/finalization adapters.

## Locked Facts

- The current branch is `codex/radle-v2-handwritten-panels` and the worktree is dirty before this audit.
- This audit is read-only for source/data outputs except for this ExecPlan document.
- Prior memory is only a starting point; final claims must be grounded in current repo files.
- Morning paths come from `src/radle_benchmark.py::build_run_paths`: raw `results.csv`, repair `repaired_results.csv`, final `RadLE_v2_results_final.csv`, scorer `scorer_view.csv`, and public release tables.
- IDK0 wrapper starts from `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/radle_v2_final_long_master.csv`, not directly from Morning raw/final/scorer/public files.
- Current IDK0 Score1000 audit report says `result: pass` for `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0`.
- Current IDK0 panel package audit report says `result: pass`, `rows: 16`, and includes variants/panels 2.1 through 6.4 plus promoted 5.4.

## Do Not Revisit

- Do not stage, commit, or clean unrelated dirty work during this audit. See Decision Log 2026-07-09.
- Do not treat ignored generated `outputs/` artifacts as absent merely because Git ignores them. See Decision Log 2026-07-09.

## Progress

- [x] (2026-07-09 12:16 +05:30, Codex/GPT-5) Read global ExecPlan instructions and confirmed no repo-local `AGENTS.md` or `PLANS.md` was found.
- [x] (2026-07-09 12:20 +05:30, Codex/GPT-5) Mapped the Morning benchmark output contract from current files.
- [x] (2026-07-09 12:20 +05:30, Codex/GPT-5) Mapped the IDK0 wrapper and generated file contract from current files.
- [x] (2026-07-09 12:20 +05:30, Codex/GPT-5) Compared integration quality and prepared evidence-backed gaps.

## Surprises & Discoveries

- Observation: IDK0 is wrapper-safe but script-default risky: several IDK0 scripts still default `IDK_SCORE = 1` / `--idk-score 1`; the wrapper passes `--idk-score 0` consistently.
  Evidence: `scripts/build_radle_v2_score1000_idk0_pipeline.ps1` passes `--idk-score 0`; `scripts/make_radle_v2_likert5_score1000_csvs_IDK0.py` and related visual/audit scripts default to `1`.
  Date/Author: 2026-07-09, Codex/GPT-5
- Observation: The generated IDK0 artifacts have strong downstream provenance but no one-command bridge from Morning wide files.
  Evidence: `scripts/radle_v2_stats.py` can convert wide `Diagnosis_<model>` files to long rows, while the IDK0 wrapper accepts only a finalized long master.
  Date/Author: 2026-07-09, Codex/GPT-5

## Decision Log

- Decision: Keep this audit in the current Local checkout and avoid branch/worktree changes.
  Rationale: The user asked for a repo study, not code changes or parallel implementation.
  Date/Author: 2026-07-09, Codex/GPT-5
- Decision: Include ignored generated outputs in the audit if present on disk.
  Rationale: The user asked about file integration, and generated artifacts are part of that contract even when not committed.
  Date/Author: 2026-07-09, Codex/GPT-5
- Decision: Classify integration as strong downstream of final-long-master, partial between Morning outputs and IDK0.
  Rationale: There are robust gates/provenance after the long master exists, but no direct wrapper from Morning `raw/final/scorer/public_release` outputs into IDK0.
  Date/Author: 2026-07-09, Codex/GPT-5

## Revision Notes

- v1 (2026-07-09, Codex/GPT-5): Created the audit plan before reading pipeline files.
- v2 (2026-07-09, Codex/GPT-5): Recorded final audit findings after reading Morning, stats adapter, IDK0 wrapper, receipts, provenance, and generated audit reports.

## Outcomes & Retrospective

- Completed: IDK0 is production-like from `radle_v2_final_long_master.csv` through Score1000 CSVs and panels, with manifests, SHA gates, row-count checks, and audit reports. The weak point is earlier: Morning produces wide run artifacts and IDK0 expects a finalized scored long master, so the integration depends on separate conversion, judging, and finalization work rather than a single Morning-to-IDK0 pipeline.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | Required by user instruction for multi-step analysis | `manual` |
| Repo inspection | `none` | Direct file and command inspection is sufficient | `none` |
| Final integration report | `none` | A concise evidence-backed answer is the deliverable | `none` |

## Context And Orientation

The likely source of truth for the Morning benchmark is `src/radle_benchmark.py`, with `notebooks/RadLE_v1_5_Morning.ipynb` acting as a runner. The likely IDK0 lane includes `scripts/build_radle_v2_score1000_idk0_pipeline.ps1`, `scripts/make_radle_v2_likert5_score1000_csvs_IDK0.py`, `scripts/audit_radle_v2_likert5_score1000_csvs_IDK0.py`, `scripts/radle_v2_score1000_panel_stats_IDK0.py`, `scripts/make_radle_v2_score1000_panel23_svg_IDK0.py`, and `scripts/audit_radle_v2_score1000_panel23_IDK0.py`.

## Plan Of Work

First, inspect Morning notebook/module output naming and saved fields. Second, inspect IDK0 scripts for their expected input file paths, required columns, and output file names. Third, inspect generated output directories under `outputs/` and any documentation under `Documents/`. Finally, summarize integration level as strong, partial, or weak for each link in the pipeline.

Branch strategy: stay on current branch and do not stage. Environment: Local. Worktree: not needed. Handoff: final answer will point to the ExecPlan and exact evidence paths.

## Milestones

Milestone 1, repo contract map, skill `none`: Morning output shapes and locations are known from code/docs.

Milestone 2, IDK0 contract map, skill `none`: IDK0 script inputs/outputs and wrapper order are known from code/docs.

Milestone 3, final report, skill `none`: user receives a concise integration assessment with file-backed gaps.

## Concrete Steps (Commands)

Run focused searches and file reads from repo root:

    rg -n "idk0|IDK0|Morning|RUN_NAME|output|csv|final_scoring" src scripts notebooks Documents
    rg --files outputs | rg -i "IDK0|final_scoring|likert5|score1000"

## Validation And Acceptance

The audit is complete when the final answer names the exact Morning output contract, the exact IDK0 expected input/output contract, and the concrete integration gaps or strengths with file references.

## Idempotence And Recovery

All inspection commands are read-only. If output scans are too large, narrow to known roots under `outputs/radle_v2_stats/`.

## Artifacts And Notes

No source artifacts generated beyond this plan.

## Interfaces And Dependencies

No code interfaces are changed. The audit depends on readable repo files and locally present generated outputs.
