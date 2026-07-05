# Import RadLE Stats Results Script

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` or `AGENTS.md` was found in `C:\Users\thehb\Documents\RadLE v2`; the user-provided AGENTS instruction says to place ExecPlans under `Documents/` when available.

## Purpose / Big Picture

The user wants the RadLE Stats results-analysis script pulled into this RadLE v2 repo, then audited against the latest full `radle_v2` run. After this pass, a future implementation agent should know exactly where the imported script lives and what must change before it can produce valid statistics from `results/radle_v2/final/RadLE_v2_results_final.csv`.

## Current State

Current state (2026-06-30 11:05 IST, Codex/GPT-5): `scripts/radle_rsna_analysis.py` has been imported byte-identically from RadLE Stats, compiles, and the compatibility audit is documented in `Documents/radle_stats_script_new_results_audit.md`. Next: wait for user direction before implementing a raw-results adapter or scored-analysis refactor.

## Locked Facts

- The latest pulled full run is `results/radle_v2/final/RadLE_v2_results_final.csv`, with 200 rows, 163 columns, and manifest SHA-256 `53543631d657349e848b38ea57632d07efbc33c22b72a24733ae107bc84d3d9c`.
- The latest run model suffixes are `gpt_5_5`, `claude_4_8_opus`, `gemini_3_1_pro`, `grok_4_20`, `qwen_3_7_plus`, `gemma_4_31b`, `llama_4_maverick`, `mistral_large_3_2512`, `glm_4_6v`, and `nemotron_3_omni`.
- The source Stats script is `C:\Users\thehb\Documents\RadLE Stats\radle_rsna_analysis.py`.
- The imported script must not mutate or clean the raw result CSV; any future scoring/analysis should use derived files or adapters.
- The imported script expects scored Model A-J CSVs, while the latest `radle_v2` files use raw model-suffix columns and currently contain no populated correctness-score fields.

## Do Not Revisit

- Do not overwrite the latest full raw result CSV while adapting the stats script. See Decision Log 2026-06-30.
- Do not treat the imported script as runnable on the new full-result CSV until the audit blockers are resolved. See Decision Log 2026-06-30.

## Progress

- [x] (2026-06-30 10:55 IST, Codex/GPT-5) Read ExecPlan instructions, memory context, current repo file layout, and current git state.
- [x] (2026-06-30 11:00 IST, Codex/GPT-5) Copied `radle_rsna_analysis.py` into `scripts/radle_rsna_analysis.py`; SHA-256 matches the source and `py -3.11 -m py_compile scripts\radle_rsna_analysis.py` passes.
- [x] (2026-06-30 11:04 IST, Codex/GPT-5) Audited imported script assumptions against the latest full `radle_v2` CSV schema and existing public/scorer artifacts.
- [x] (2026-06-30 11:05 IST, Codex/GPT-5) Saved the audit to `Documents/radle_stats_script_new_results_audit.md`; playback to user remains in the final response.

## Surprises & Discoveries

- Observation: The latest full/scorer files have diagnosis and Likert columns but no ground-truth or correctness-score columns; the public case-model file has `score_binary` and `score_likert`, but both are blank across all 2,000 rows.
  Evidence: Python schema probe over `results/radle_v2/final/RadLE_v2_results_final.csv`, `results/radle_v2/scorer/scorer_view.csv`, and `results/radle_v2/public_release/RadLE_v2_public_model_results.csv`.
  Date/Author: 2026-06-30, Codex/GPT-5

- Observation: The import target can compile with `py -3.11`, and runtime dependencies are available: numpy 1.26.4, pandas 3.0.3, scipy 1.17.1.
  Evidence: `py -3.11 -m py_compile scripts\radle_rsna_analysis.py` and direct dependency import probe.
  Date/Author: 2026-06-30, Codex/GPT-5

## Decision Log

- Decision: Stay on the current `main` checkout and do not create a branch for this small import/audit pass.
  Rationale: The worktree already has unrelated user changes; creating or switching branches could confuse ownership of those changes.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: Copy the Stats script exactly before auditing modifications.
  Rationale: The user asked to pull the script first, and preserving the imported baseline makes the adaptation delta auditable.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: Stop at import plus audit, not implementation.
  Rationale: The audit found that a real adaptation needs a scoring-source decision; implementing around absent correctness scores would produce misleading manuscript metrics.
  Date/Author: 2026-06-30, Codex/GPT-5

## Revision Notes

- v2 (2026-06-30, Codex/GPT-5): Updated after exact script import, compile verification, schema probes, and audit-note creation.

## Outcomes & Retrospective

The imported script now exists in RadLE v2 as `scripts/radle_rsna_analysis.py`. The main outcome is negative but useful: the script is not a one-line tweak away from running on the latest full raw results. It needs a raw-to-canonical adapter and a scored-analysis layer, because the current result files do not contain populated correctness scores. No reusable skill should be created from this project-specific adapter audit without explicit user permission.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | The task combines a repo mutation with schema/statistical compatibility analysis. | `manual` |
| Script import | `none` | A direct file copy is sufficient. | `none` |
| Compatibility audit | `none` | Direct Python/schema inspection is sufficient. | `none` |
| Future implementation | `none` | The likely change is a focused adapter/refactor inside the imported script. | `none` |

## Context And Orientation

The RadLE v2 repo contains the current benchmark runner under `src/radle_benchmark.py`, notebooks under `notebooks/`, and local full-run results under `results/radle_v2/`. The results folder is ignored by git. The separate older `RadLE Stats` workspace contains an older results-analysis script that consumes two human-reviewed wide CSVs, not the raw benchmark result CSV used by the current RadLE v2 run.

## Plan Of Work

First, copy `C:\Users\thehb\Documents\RadLE Stats\radle_rsna_analysis.py` to `scripts/radle_rsna_analysis.py` without editing its contents. Then compare its expected input contract with `results/radle_v2/final/RadLE_v2_results_final.csv` and the derived public/scorer files under `results/radle_v2/`. Finally, report the exact blockers and likely code changes needed before adaptation.

## Milestones

Milestone 1, script import. Skill: `none`. The imported file exists at `scripts/radle_rsna_analysis.py`, compiles, and has the same SHA-256 as the source file.

Milestone 2, compatibility audit. Skill: `none`. The audit identifies all hard schema mismatches, semantic/statistical blockers, and low-risk mechanical updates needed for the new `radle_v2` results.

## Concrete Steps (Commands)

From `C:\Users\thehb\Documents\RadLE v2`:

    Copy-Item -LiteralPath "C:\Users\thehb\Documents\RadLE Stats\radle_rsna_analysis.py" -Destination "scripts\radle_rsna_analysis.py"
    Get-FileHash "scripts\radle_rsna_analysis.py" -Algorithm SHA256
    py -3.11 -m py_compile scripts\radle_rsna_analysis.py

Expected: the copied file hash matches the source hash, and `py_compile` exits with status 0.

## Validation And Acceptance

The import is valid when the copied file is byte-identical to the source and compiles. The audit is valid when it explicitly distinguishes input-shape blockers from statistical-method blockers and does not claim the imported script can run on the latest full raw CSV as-is.

## Idempotence And Recovery

Copying the script is safe to rerun if the destination is meant to remain an exact import. If future edits begin, compare against the source file before overwriting. Do not delete or modify `results/radle_v2/final/RadLE_v2_results_final.csv`.

## Artifacts And Notes

The latest run manifest says `run_id=radle_v2`, `test_limit=full`, `rows=200`, `columns=163`, `case_count=200`, and SHA-256 `53543631d657349e848b38ea57632d07efbc33c22b72a24733ae107bc84d3d9c`.

## Interfaces And Dependencies

The imported script currently depends on `numpy`, `pandas`, and `scipy`. Future adaptation should either preserve those dependencies or add a documented installation path in this repo.
