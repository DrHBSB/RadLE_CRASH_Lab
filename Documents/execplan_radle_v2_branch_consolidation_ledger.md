# Consolidate RadLE v2 Branches and Worktrees

This ExecPlan is a living branch-consolidation ledger. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md` and the applicable repository instruction to keep serious plans under `Documents/`. No repo-local `PLANS.md` or checked-in `AGENTS.md` was found in the inspected worktrees on 2026-07-12.

## Purpose / Big Picture

RadLE v2 has accumulated several stacked branches and worktrees across admission, panel, Morning append, runtime, and scoring work. The goal is to reduce that state methodically without losing unique or uncommitted work. A branch is closed only after Git ancestry or patch-equivalence proves its work is preserved on a named successor, its worktree is clean, and any remaining remote action is explicitly authorized.

The admission-side factual handoff is `Documents/execplan_radle_v2_incremental_model_admission.md` from `codex/radle-v2-pre-m7-repair`. Its `Current State`, `Repeatable Admission SOP`, and `Colab Output To SVG Command Index` remain authoritative for admission behavior. This ledger owns only branch lineage, consolidation operations, closure gates, and worktree disposition.

## Current State

Current state (2026-07-12 03:38 +05:30, Codex/GPT-5): `codex/radle-v2-branch-consolidation` now contains both source tips through conflict-free merge commit `44b6f70`. The ledger checkpoint is `733fee8`; pre-M7 continuation commits `410b447` and `e2e0c2b` are preserved with panel commits `9727248` and `2f70441`. Combined validation passed: 37 unit tests, config and frozen-base gates, admission and panel Python compilation, PowerShell parsing, panel-tree preservation across 52 files, diff checks, and token-pattern scan. The next bounded action is Wave 2: recheck exact containment and worktree cleanliness, then close only the first local ancestry-contained set. No push, remote deletion, dirty-worktree removal, or primary-checkout edit is authorized by this ledger.

## Locked Facts

- The primary checkout `C:/Users/thehb/Documents/RadLE v2` is heavily dirty on `codex/radle-v2-handwritten-panels` and is preservation-only during consolidation.
- The consolidation worktree is `C:/tmp/radle_v2_branch_consolidation` on `codex/radle-v2-branch-consolidation`, based at `2f70441`.
- `codex/radle-v2-post-admission-panels` contains the repaired admission base through `b543827` plus panel commits `9727248` and `2f70441`.
- `codex/radle-v2-pre-m7-repair` contains two additional local commits after `b543827`: `410b447` and plan-only checkpoint `e2e0c2b`.
- Merge commit `44b6f70` preserves both `codex/radle-v2-post-admission-panels` and `codex/radle-v2-pre-m7-repair` as exact ancestors of the consolidation branch.
- `codex/radle-v2-incremental-admission` at `77dbfb0` is an ancestor of both the post-admission and pre-M7 stacks.
- Local `main` at `080ec65` is stale relative to the currently fetched `origin/main` at `f3c7d72`; `origin/main` is the baseline for containment decisions.
- The Morning append stack is a separate consolidation lane rooted at `codex/morning-meta-muse-spark-append`; it must not be merged into the admission/panel stack merely to reduce branch count.
- Remote branch deletion and pushing require a separate explicit action; this ledger may prepare exact candidates and commands but does not infer that authority.

## Do Not Revisit

- Do not use the dirty primary checkout as the consolidation surface. See Decision Log 2026-07-12.
- Do not fold admission execution history into this ledger; link the existing admission ExecPlan and record only Git disposition here. See Decision Log 2026-07-12.
- Do not treat patch-equivalent branches as ancestry-contained until `git cherry` or an equivalent diff proof is recorded. See Decision Log 2026-07-12.
- Do not delete branches merely because their names look obsolete; closure requires preservation proof and clean worktree status. See Decision Log 2026-07-12.
- Do not merge the Morning append lane into the admission/panel lane without a project-level reason beyond cleanup. See Decision Log 2026-07-12.

## Progress

- [x] (2026-07-12 03:04 +05:30, Codex/GPT-5) Fetched current `origin` refs without pruning and captured branch/worktree state.
- [x] (2026-07-12 03:04 +05:30, Codex/GPT-5) Created isolated consolidation branch/worktree from `codex/radle-v2-post-admission-panels` at `2f70441`.
- [x] (2026-07-12 03:04 +05:30, Codex/GPT-5) Created this living consolidation ledger and linked the prior admission ExecPlan as source evidence.
- [x] (2026-07-12 03:38 +05:30, Codex/GPT-5) Reconciled the completed Wave 1 containment and worktree-risk receipts; replaced the disconnected comparison agent without widening scope.
- [x] (2026-07-12 03:38 +05:30, Codex/GPT-5) Integrated the two pre-M7 continuation commits in conflict-free merge `44b6f70` after synthetic merge tree `416ab40074b20c7d931a3d1a0a7658b1a92c120c` exited 0 with no overlapping changed paths.
- [x] (2026-07-12 03:38 +05:30, Codex/GPT-5) Validated the combined admission/panel stack with compile, config, authority, unit, PowerShell, tree-preservation, diff, and token gates.
- [ ] (2026-07-12 03:04 +05:30, Codex/GPT-5) Close the first local-only set of ancestry-contained branches/worktrees after rechecking cleanliness.
- [ ] (2026-07-12 03:04 +05:30, Codex/GPT-5) Audit the separate Morning append stack and classify its contained smoke branches.
- [ ] (2026-07-12 03:04 +05:30, Codex/GPT-5) Produce the final remaining-branches register and explicit remote-action queue.

## Branch Register

Status values are `active target`, `integrate next`, `closure candidate`, `patch-equivalence review`, `preserve`, and `separate lane`. A closure candidate is not deleted until its worktree gate is also green.

| Branch / ref | Tip at inventory | Current classification | Preservation target | Next gate |
| --- | --- | --- | --- | --- |
| `codex/radle-v2-branch-consolidation` | `44b6f70` | active target | itself | first local closure wave |
| `codex/radle-v2-post-admission-panels` | `2f70441` | closure candidate | consolidation branch | clean worktree recheck |
| `codex/radle-v2-pre-m7-repair` | `e2e0c2b` | preserve until ignored probes are classified | consolidation branch | ignored-artifact decision plus clean recheck |
| `codex/radle-v2-incremental-admission` | `77dbfb0` | closure candidate | post-admission and pre-M7 stacks | clean worktree and successor proof |
| `codex/radle-v2-primary-preservation` | `88d66e0` | patch-equivalence review | post-admission panel commits | `git cherry` and tree-diff proof |
| `codex/radle-v2-handwritten-panels` | `8c9de27` plus dirty files | preserve | unresolved | inventory only; no mutation |
| `codex/morning-meta-muse-spark-append` | `37a0f44` | separate lane | itself | Wave 2 containment audit |
| `codex/gpt56-openrouter-smoke` | `8feeb7b` | closure candidate | Morning append stack | clean worktree; exact ancestry already passes |
| `codex/grok45-morning-smoke` | `1faee5a` | closure candidate | Morning append stack | exact ancestry passes; confirm no attached worktree |
| `codex/meta-muse-spark-colab` | `e4f2e84` | preserve / divergent | Morning append stack unresolved | patch-distinct and file-diff review |
| `codex/final-scoring-csv-questions` | `071d6ec` | preserve until dirty file is captured | Morning append stack | untracked plan plus ancestry proof |
| `fix/stats-combiner-scorer-from-final` | `2d1028c` | closure candidate | `origin/main` | remote/local containment proof |
| `claude/elated-germain-35c138` | `e03b2e0` | closure candidate | `origin/main` | detached-worktree cleanliness |
| `claude/sad-meninsky-7102e8` | `f8a529d` | closure candidate | `origin/main` | detached-worktree cleanliness |
| `codex/llava-vllm-runtime` | `56a882b` | preserve | unresolved | inspect unique local commits and remote mismatch |
| local `main` | `080ec65` | stale baseline | `origin/main` | do not use for containment |

## Surprises & Discoveries

- Observation: the two major RadLE stacks diverge by two commits on each side from `b543827`, rather than one being a direct ancestor of the other.
  Evidence: `git rev-list --left-right --count codex/radle-v2-post-admission-panels...codex/radle-v2-pre-m7-repair` returned `2 2`.
  Date/Author: 2026-07-12, Codex/GPT-5

- Observation: local `main` fell one additional commit behind the fetched remote baseline compared with the prior session's snapshot.
  Evidence: local `main` is `080ec65`; fetched `origin/main` advanced first to `3a8c38e` and then to `f3c7d72` while Wave 1 was running.
  Date/Author: 2026-07-12, Codex/GPT-5

- Observation: committed cleanliness is insufficient for two worktrees because untracked or ignored artifacts remain outside branch history.
  Evidence: `C:/Users/thehb/Documents/RadLE v2 - final scoring questions` has untracked `Documents/execplan_radle_arxiv_stats_story.md`; `C:/tmp/radle_v2_pre_m7_repair` has two local-only commits and six ignored reasoning-probe CSVs reported by the worktree-risk audit.
  Date/Author: 2026-07-12, Hilbert subagent and Codex/GPT-5

- Observation: the primary checkout has 91 unique dirty paths, including staged files with further unstaged edits and staged additions deleted from disk.
  Evidence: Wave 1 worktree audit counted 56 staged entries, 21 unstaged entries, and 22 untracked entries; overlapping status categories reduce this to 91 unique paths.
  Date/Author: 2026-07-12, Hilbert subagent

- Observation: the isolated consolidation worktree does not contain the ignored private authority CSVs needed by `check-base`.
  Evidence: `check-base --authority-root C:/tmp/radle_v2_branch_consolidation` failed only because `results/radle_v2_combined/final/RadLE_v2_results_final.csv` was absent; rerunning read-only against the recorded authority root `C:/Users/thehb/Documents/RadLE v2` returned `BASE_RESULT=PASS` with the expected 200-case and 6000-row frozen base hashes.
  Date/Author: 2026-07-12, Codex/GPT-5

## Decision Log

- Decision: use a dedicated worktree and branch based on `codex/radle-v2-post-admission-panels`.
  Rationale: it is clean, already carries the passed repair base and production panel integration, and isolates consolidation from the dirty primary checkout.
  Date/Author: 2026-07-12, Codex/GPT-5

- Decision: retain the prior admission ExecPlan and create this separate ledger.
  Rationale: the admission plan is operational product evidence; branch closure needs a compact Git-centric record that can evolve without obscuring the admission SOP.
  Date/Author: 2026-07-12, Codex/GPT-5

- Decision: use sequential consolidation waves with independent read-only audits before each mutation.
  Rationale: small reversible steps prevent a broad cleanup from absorbing dirty or unique work.
  Date/Author: 2026-07-12, Codex/GPT-5

- Decision: require both preservation proof and a clean worktree before local branch closure.
  Rationale: ancestry alone does not preserve uncommitted files, and patch-equivalence is not identical to ancestry.
  Date/Author: 2026-07-12, Codex/GPT-5

- Decision: preserve the pre-M7 continuation with a non-fast-forward merge rather than cherry-picking.
  Rationale: the source has two coherent sequential commits, both source tips remain auditable as ancestors, the synthetic merge exited 0, and the two sides changed no overlapping paths after common base `b543827`.
  Date/Author: 2026-07-12, Codex/GPT-5

## Revision Notes

- v2 (2026-07-12, Codex/GPT-5): recorded Wave 1 receipts, merge `44b6f70`, combined validation, and the first closure-wave boundary.
- v1 (2026-07-12, Codex/GPT-5): created the ledger from refreshed Git state, linked the admission ExecPlan, recorded the initial branch register, and established sequential closure gates.

## Outcomes & Retrospective

Milestones 0 through 2 are complete. The isolated ledger exists, both admission/panel histories are consolidated at `44b6f70`, and combined validation passes. No existing source branch or worktree has yet been removed. The preservation-plus-cleanliness closure gate is useful but already captured by the installed workflow guidance; no new skill promotion is needed.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Ledger and planning | `workflow-router`, `execplan` | Keeps branch posture explicit and the ledger restartable | `auto-suggest` |
| Read-only wave audits | `none` | Scoped Git commands and independent agents are sufficient | `none` |
| Integration | `none` | Direct Git operation plus repository tests is sufficient | `none` |
| Pre-commit review | `Code Reviewer` if available | Useful for checking the staged consolidation boundary | `auto-suggest` |
| Final closure classification | `none` | Closure rests on explicit Git/worktree evidence | `none` |

## Context And Orientation

The repository contains several concurrent bodies of work. The admission/panel stack is the first consolidation lane. `codex/radle-v2-post-admission-panels` carries panel assets and scripts, while `codex/radle-v2-pre-m7-repair` carries the latest admission continuation. The Morning stack is operationally separate. A Git worktree is a second checkout attached to the same repository; deleting a branch that is checked out in a worktree is blocked and removing a dirty worktree can lose uncommitted work.

All mutation in this plan occurs from `C:/tmp/radle_v2_branch_consolidation`. Read-only audits may inspect other worktrees. The primary checkout is never used for stage, commit, merge, branch deletion, or worktree removal during this plan.

## Plan Of Work

Milestone 0 records live state and creates this ledger. Milestone 1 integrates the pre-M7 continuation into the active target. The integration method is selected from actual ancestry and conflict evidence; because the source has two coherent sequential commits, a non-fast-forward merge is preferred if the synthetic merge is conflict-free and preserves both branch histories. Cherry-pick is the fallback when merge topology would obscure an unrelated source boundary.

Milestone 2 validates both sides of the combined stack. Admission gates include Python compilation, config checks, and the focused unit suite. Panel gates include the existing base-authority check and relevant deterministic panel/audit tests available in the branch. Git gates include `git diff --check`, a secret-pattern scan, and a clean status after commit.

Milestone 3 closes only local branches and worktrees that are proven redundant and clean. Each deletion is preceded by a fresh status and ancestry check, then recorded in this register. Remote branches are queued separately and are not deleted by implication.

Milestone 4 repeats the method for the Morning append lane, without merging it into the admission/panel stack. Remaining unique branches such as the dirty handwritten checkout and the llava runtime lane remain open with an explicit reason.

## Milestones

### Milestone 0: Ledger and live inventory

Skill: `workflow-router` plus `execplan`. Completion means this file reflects fetched refs, worktrees, exact tips, and the next operation.

### Milestone 1: Admission/panel integration

Skill: `none`. Completion means `410b447` and `e2e0c2b` are preserved on the consolidation branch, merge conflicts are absent or explicitly resolved, and the prior admission plan remains intact.

### Milestone 2: Combined validation

Skill: `none`. Completion means focused admission and panel gates pass from the consolidation worktree and their literal summaries are recorded here.

### Milestone 3: First local closure wave

Skill: `none`. Completion means only clean, proven-contained local branches/worktrees are removed and every action is recorded with the preservation target.

### Milestone 4: Morning lane and residual register

Skill: `none`. Completion means smoke branches are classified against the Morning stack and every remaining branch has one named next action or preservation reason.

## Concrete Steps (Commands)

Run from `C:/tmp/radle_v2_branch_consolidation` unless noted.

    git status --short --branch
    git rev-list --left-right --count codex/radle-v2-post-admission-panels...codex/radle-v2-pre-m7-repair
    git merge-tree --write-tree codex/radle-v2-post-admission-panels codex/radle-v2-pre-m7-repair

Expected before integration: clean status, `2 2`, and a synthetic merge tree without unmerged entries.

    git merge --no-ff codex/radle-v2-pre-m7-repair

Expected: one merge commit preserving both two-commit branches. If Git reports conflicts, stop before manual resolution and record the files here.

    py -3.11 -B -m py_compile src\radle_incremental_admission.py src\radle_openrouter_judge.py scripts\radle_v2_incremental_admission.py scripts\radle_v2_carry_forward_muse_admission.py
    py -3.11 -B scripts\radle_v2_incremental_admission.py check-config --roster config\radle_v2_model_roster.json --judges config\radle_v2_judges.json --states config\radle_v2_terminal_states.json --fixture tests\fixtures\radle_incremental_admission\unit_cases.csv
    py -3.11 -B -m unittest discover -s tests -p test_*.py -v
    git diff --check

Expected: compile succeeds, config prints `CONFIG_RESULT=PASS`, tests pass, and the diff check is silent except possible line-ending warnings.

## Validation And Acceptance

The consolidated branch is accepted when Git proves both source tips are ancestors of `HEAD`, all required files from both sides exist, the admission suite passes, the panel integration assets remain present, and no unrelated primary-checkout changes appear in the consolidation commit.

A branch is accepted for local closure only when:

- its committed work is an ancestor of a named successor, or patch-equivalence is explicitly proven;
- its attached worktree reports clean;
- it is not the only pointer to unique commits;
- the ledger records the successor and evidence immediately before deletion.

## Idempotence And Recovery

Read-only inventory commands are safe to rerun. Before the integration commit, a failed merge may be aborted with `git merge --abort` only from the consolidation worktree. Existing worktrees are never reset or cleaned. If validation fails after a successful merge, keep the merge commit local, mark the milestone blocked, and diagnose on the consolidation branch rather than rewriting source branches.

Local branch deletion is not idempotent, so it is always preceded by `git show-ref`, `git merge-base --is-ancestor`, and worktree status checks. Remote deletion is outside the current authority.

## Artifacts And Notes

Initial divergence proof:

    2  2
    > e2e0c2b Record pre-M7 consolidation checkpoint
    > 410b447 Checkpoint three-model admission continuation
    < 2f70441 Integrate frontier models into IDK0 panels
    < 9727248 Preserve IDK0 panel core and assets

Combined validation receipt:

    PY_COMPILE=PASS
    PANEL_PY_COMPILE=PASS
    CONFIG_RESULT=PASS
    BASE_RESULT=PASS
    Ran 37 tests in 88.097s
    OK
    PANEL_TREE_PRESERVED=PASS files=52
    MERGE_DIFF_CHECK=PASS
    MERGE_SECRET_SCAN=PASS

## Interfaces And Dependencies

This plan depends only on Git, PowerShell, and the repository's existing Python 3.11 validation commands. It introduces no runtime interface. Its durable artifact is `Documents/execplan_radle_v2_branch_consolidation_ledger.md` on `codex/radle-v2-branch-consolidation`.
