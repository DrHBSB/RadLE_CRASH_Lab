# Compare Pristine And Morning Notebooks

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` or root `AGENTS.md` file was found; this plan also follows the prompt-provided instruction to place ExecPlans under `Documents/` when present.

## Purpose / Big Picture

The user wants a focused comparison between `C:/Users/thehb/Downloads/RadLE_v1_5_PRISTINE.ipynb` and `notebooks/RadLE_v1_5_Morning.ipynb`. The outcome is not a merge. The outcome is a shortlist of distinct behaviors, helpers, parameters, analyses, or notebook sections that the old pristine notebook performs and that could be selectively copied into the Morning notebook later.

## Current State

Current state (2026-06-17 23:54 +05:30, Codex/GPT-5): The comparison is complete. The final response should present a surgical menu of pristine-only future-run behavior, explicitly excluding the first-50 preservation / 51-200 historical resume workflow.

## Locked Facts

- `C:/Users/thehb/Downloads/RadLE_v1_5_PRISTINE.ipynb` is the old pristine source notebook for comparison.
- `notebooks/RadLE_v1_5_Morning.ipynb` is the current target notebook for potential surgical additions.
- This task is comparison only; no notebook code should be imported or edited during this pass.
- The Morning notebook is already modified in the worktree before this comparison.
- The first-50 preservation / 51-200 rerun overlap logic in the pristine notebook is historical one-time resume scaffolding and should not be recommended for the new fresh script.

## Do Not Revisit

- Do not perform a broad import from the pristine notebook. See Decision Log 2026-06-17 23:44 +05:30.
- Do not revert the existing Morning notebook changes. See Decision Log 2026-06-17 23:44 +05:30.
- Do not recommend the first-50 preservation workflow for the fresh new run. See Decision Log 2026-06-17 23:49 +05:30.

## Progress

- [x] (2026-06-17 23:44 +05:30, Codex/GPT-5) Read global ExecPlan instructions and confirmed `Documents/` exists.
- [x] (2026-06-17 23:44 +05:30, Codex/GPT-5) Checked git status; Morning notebook is already modified.
- [x] (2026-06-17 23:49 +05:30, Codex/GPT-5) Extract structured summaries from both notebooks and `src/radle_benchmark.py`.
- [x] (2026-06-17 23:54 +05:30, Codex/GPT-5) Compare imports, setup/config, functions, analysis stages, outputs, and notebook narrative, excluding the historical first-50 overlap workflow.
- [x] (2026-06-17 23:54 +05:30, Codex/GPT-5) Produce a surgical candidate list for the user to choose from.

## Surprises & Discoveries

- (2026-06-17 23:44 +05:30, Codex/GPT-5) `git status --short` shows `M notebooks/RadLE_v1_5_Morning.ipynb` before any notebook edits by this agent.
- (2026-06-17 23:49 +05:30, Codex/GPT-5) The pristine notebook is a large self-contained script with historical overlap, audit, repair, and scoring-packet cells; Morning is a thin Colab launcher that delegates benchmark behavior to `src/radle_benchmark.py`.
- (2026-06-17 23:54 +05:30, Codex/GPT-5) The prompt text in pristine and `src/radle_benchmark.py` is identical; apparent mojibake in PowerShell output was a console display artifact.

## Decision Log

- (2026-06-17 23:44 +05:30, Codex/GPT-5) Treat this as a structured notebook behavior comparison, not a raw text diff, because `.ipynb` JSON ordering and output noise can obscure the meaningful differences.
- (2026-06-17 23:44 +05:30, Codex/GPT-5) Stay in the local worktree and do not create a branch for this analysis-only pass.
- (2026-06-17 23:49 +05:30, Codex/GPT-5) Exclude pristine's first-50 preservation / 51-200 resume logic from recommendations because the user clarified it was a one-time safe-resume mechanism, not desired behavior for the fresh script.

## Revision Notes

- (2026-06-17 23:49 +05:30, Codex/GPT-5) Updated plan with the user's clarification to ignore first-50 overlap/resume logic.

## Outcomes & Retrospective

Comparison complete. Reusable future-run candidates from pristine are: robust JSON extraction, dry-run/spend gates, per-case-model call logging, atomic progress/backups, read-only audit/triage, schema-stable targeted repair, and the RSNA scoring packet builder. Historical first-50 overlap reconstruction, old OpenRouter-only setup, and old hard-coded model names should not be imported as-is.

## Suggested Skills By Phase

- Planning phase: `execplan`, activation mode `manual`, used because the repo instructions call for an ExecPlan on multi-step analyses.
- Notebook extraction phase: `none`, activation mode `none`, because structured JSON parsing is enough and no notebook creation or editing is planned.
- Final comparison phase: `none`, activation mode `none`, because the deliverable is a concise behavioral shortlist rather than a generated artifact.
