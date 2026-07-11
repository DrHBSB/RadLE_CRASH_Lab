# Consolidate RadLE v2 Branches and Worktrees

This ExecPlan is a living branch-consolidation ledger. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md` and the applicable repository instruction to keep serious plans under `Documents/`. No repo-local `PLANS.md` or checked-in `AGENTS.md` was found in the inspected worktrees on 2026-07-12.

## Purpose / Big Picture

RadLE v2 has accumulated several stacked branches and worktrees across admission, panel, Morning append, runtime, and scoring work. The goal is to reduce that state methodically without losing unique or uncommitted work. A branch is closed only after Git ancestry or patch-equivalence proves its work is preserved on a named successor, its worktree is clean, and any remaining remote action is explicitly authorized.

The admission-side factual handoff is `Documents/execplan_radle_v2_incremental_model_admission.md` from `codex/radle-v2-pre-m7-repair`. Its `Current State`, `Repeatable Admission SOP`, and `Colab Output To SVG Command Index` remain authoritative for admission behavior. This ledger owns only branch lineage, consolidation operations, closure gates, and worktree disposition.

## Current State

Current state (2026-07-12 04:05 +05:30, Codex/GPT-5): the scoped local consolidation phase is complete. `codex/radle-v2-branch-consolidation` contains current `origin/main` through merge `351b3af`, the full pre-M7 admission continuation, and the production panel integration. Eleven local branches and seven worktrees were closed after preservation gates; five local branches and four worktrees remain. The formerly untracked arXiv stats-story plan is preserved and reconciled in commits `f04fffb` and `11fd85c` on `codex/radle-v2-primary-preservation`, which is intentionally retained two commits ahead of its remote. The next action requires explicit external authority: push the consolidation and primary-preservation branches, then process the remote deletion queue. The 91-path dirty handwritten checkout and the unique Morning/Meta lanes remain separate follow-up work, not cleanup failures.

## Locked Facts

- The primary checkout `C:/Users/thehb/Documents/RadLE v2` is heavily dirty on `codex/radle-v2-handwritten-panels` and is preservation-only during consolidation.
- The consolidation worktree is `C:/tmp/radle_v2_branch_consolidation` on `codex/radle-v2-branch-consolidation`; merge `351b3af` makes current `origin/main` an exact ancestor.
- `codex/radle-v2-post-admission-panels` contains the repaired admission base through `b543827` plus panel commits `9727248` and `2f70441`.
- `codex/radle-v2-pre-m7-repair` contains two additional local commits after `b543827`: `410b447` and plan-only checkpoint `e2e0c2b`.
- Merge commit `44b6f70` preserves both `codex/radle-v2-post-admission-panels` and `codex/radle-v2-pre-m7-repair` as exact ancestors of the consolidation branch.
- `codex/radle-v2-incremental-admission` at `77dbfb0` is an ancestor of both the post-admission and pre-M7 stacks.
- Local `main` was fast-forwarded from `080ec65` and now matches the fetched `origin/main` at `f3c7d72`; `origin/main` remains the containment baseline.
- The Morning append stack is a separate consolidation lane rooted at `codex/morning-meta-muse-spark-append`; it must not be merged into the admission/panel stack merely to reduce branch count.
- Remote branch deletion and pushing require a separate explicit action; this ledger may prepare exact candidates and commands but does not infer that authority.
- Local closure set 1 removed only refs already preserved by exact ancestry; `origin/codex/radle-v2-post-admission-panels` and `origin/fix/stats-combiner-scorer-from-final` remain available remotely.
- Local closure set 2 removed only Morning smoke refs that are exact ancestors of `codex/morning-meta-muse-spark-append`; both corresponding remote refs remain available.
- Local closure set 3 removed two clean detached Claude worktrees and their local branch pointers after proving both tips are ancestors of `origin/main`.
- Local closure set 4 removed the pre-M7 worktree and local branch after its two local-only commits were merged and its ignored probe CSVs were proven semantically redundant with committed JSON receipts.
- Local closure set 5 preserved the unique arXiv stats-story plan on primary-preservation, then removed the final-scoring worktree and local branch plus redundant local llava and Meta Muse pointers.
- Final local state is five branches (`main`, consolidation, Morning append, handwritten panels, and primary preservation) across four worktrees; primary preservation is ahead of its remote by two documentation commits.

## Do Not Revisit

- Do not use the dirty primary checkout as the consolidation surface. See Decision Log 2026-07-12.
- Do not fold admission execution history into this ledger; link the existing admission ExecPlan and record only Git disposition here. See Decision Log 2026-07-12.
- Do not treat patch-equivalent branches as ancestry-contained until `git cherry` or an equivalent diff proof is recorded. See Decision Log 2026-07-12.
- Do not delete branches merely because their names look obsolete; closure requires preservation proof and clean worktree status. See Decision Log 2026-07-12.
- Do not merge the Morning append lane into the admission/panel lane without a project-level reason beyond cleanup. See Decision Log 2026-07-12.
- Do not delete `origin/codex/radle-v2-post-admission-panels` until the local consolidation branch is pushed, and do not close primary-preservation locally until `f04fffb` and `11fd85c` are pushed or integrated. See Decision Log 2026-07-12.

## Progress

- [x] (2026-07-12 03:04 +05:30, Codex/GPT-5) Fetched current `origin` refs without pruning and captured branch/worktree state.
- [x] (2026-07-12 03:04 +05:30, Codex/GPT-5) Created isolated consolidation branch/worktree from `codex/radle-v2-post-admission-panels` at `2f70441`.
- [x] (2026-07-12 03:04 +05:30, Codex/GPT-5) Created this living consolidation ledger and linked the prior admission ExecPlan as source evidence.
- [x] (2026-07-12 03:38 +05:30, Codex/GPT-5) Reconciled the completed Wave 1 containment and worktree-risk receipts; replaced the disconnected comparison agent without widening scope.
- [x] (2026-07-12 03:38 +05:30, Codex/GPT-5) Integrated the two pre-M7 continuation commits in conflict-free merge `44b6f70` after synthetic merge tree `416ab40074b20c7d931a3d1a0a7658b1a92c120c` exited 0 with no overlapping changed paths.
- [x] (2026-07-12 03:38 +05:30, Codex/GPT-5) Validated the combined admission/panel stack with compile, config, authority, unit, PowerShell, tree-preservation, diff, and token gates.
- [x] (2026-07-12 03:47 +05:30, Codex/GPT-5) Closed first local-only set after fresh gates: removed incremental-admission and post-admission worktrees, deleted their local branches, and deleted the local stats-combiner fix branch already contained by `origin/main`.
- [x] (2026-07-12 03:47 +05:30, Codex/GPT-5) Closed local Morning smoke set after exact ancestry and cleanliness gates: removed the GPT smoke worktree and deleted local GPT-5.6 and Grok 4.5 smoke branches.
- [x] (2026-07-12 03:49 +05:30, Codex/GPT-5) Closed two clean detached Claude worktrees and local branch pointers after proving their tips are in `origin/main`; fast-forwarded unused local `main` to `f3c7d72`.
- [x] (2026-07-12 03:53 +05:30, Codex/GPT-5) Closed pre-M7 local branch/worktree after independent ignored-artifact audit proved six CSV probes were non-unique projections of committed JSON evidence.
- [x] (2026-07-12 03:53 +05:30, Codex/GPT-5) Audited the separate Morning append stack and closed only the two exact-ancestor smoke branches; retained divergent Meta Muse and active Morning target.
- [x] (2026-07-12 04:05 +05:30, Codex/GPT-5) Merged fetched `origin/main` in conflict-free commit `351b3af`; validated its one 280216-byte output notebook, reran 37 tests, config gate, diff checks, ancestry checks, and 52-file panel-tree preservation.
- [x] (2026-07-12 04:05 +05:30, Codex/GPT-5) Preserved and reconciled the unique arXiv stats-story ExecPlan on primary-preservation, then closed the final-scoring worktree/local branch, redundant llava local branch, and remote-backed Meta Muse local alias.
- [x] (2026-07-12 04:05 +05:30, Codex/GPT-5) Produced the final remaining-branches register and explicit remote-action queue.

## Branch Register

Final status values distinguish active local targets, synchronized baseline, dirty/unique holds, closed local refs, and retained remote refs. No remote-retained row implies authorization to delete it.

| Branch / ref | Recorded tip | Current classification | Preservation target | Next gate |
| --- | --- | --- | --- | --- |
| `codex/radle-v2-branch-consolidation` | `351b3af` plus this ledger checkpoint | active target; current baseline integrated | itself | push after explicit authorization |
| `codex/radle-v2-post-admission-panels` | `2f70441` | local branch/worktree closed; remote retained | consolidation branch | optional remote cleanup queue |
| `codex/radle-v2-pre-m7-repair` | `e2e0c2b` | local branch/worktree closed; older remote retained | consolidation branch | optional remote cleanup queue after push decision |
| `codex/radle-v2-incremental-admission` | `77dbfb0` | local branch/worktree closed | consolidation branch | none |
| `codex/radle-v2-primary-preservation` | `11fd85c` | active archival target; ahead 2 | remote `88d66e0` plus local plan commits | push before local closure |
| `codex/radle-v2-handwritten-panels` | `8c9de27` plus 91 dirty paths | dirty hold | unresolved | separate preservation audit |
| `codex/morning-meta-muse-spark-append` | `37a0f44` | active separate lane; clean | itself | reconcile remote Meta Muse side lane separately |
| `codex/gpt56-openrouter-smoke` | `8feeb7b` | local branch/worktree closed; remote retained | Morning append stack | optional remote cleanup queue |
| `codex/grok45-morning-smoke` | `1faee5a` | local branch closed; remote retained | Morning append stack | optional remote cleanup queue |
| `codex/meta-muse-spark-colab` | `e4f2e84` | local alias closed; unique remote retained | remote side lane | separate reconciliation with Morning |
| `codex/final-scoring-csv-questions` | `071d6ec` | local branch/worktree closed | primary preservation and Morning | arXiv plan preserved at `11fd85c` |
| `fix/stats-combiner-scorer-from-final` | `2d1028c` | local branch closed; remote retained | `origin/main` | optional remote cleanup queue |
| `claude/elated-germain-35c138` | `e03b2e0` | local branch/worktree closed | `origin/main` | none |
| `claude/sad-meninsky-7102e8` | `f8a529d` | local branch/worktree closed; remote retained | `origin/main` | optional remote cleanup queue |
| `codex/llava-vllm-runtime` | `56a882b` | local branch closed | handwritten and primary-preservation lineages | optional old remote cleanup queue |
| local `main` | `f3c7d72` | synchronized baseline | `origin/main` | refresh before future closure waves |

## Remote Action Queue

No remote action was executed. Each row requires explicit authorization immediately before use and a fresh fetch/ancestry recheck.

| Remote ref | Status | Preserved by | Required predecessor |
| --- | --- | --- | --- |
| `origin/claude/sad-meninsky-7102e8` | deletion-ready | `origin/main` | authorization only |
| `origin/codex/gpt56-openrouter-smoke` | deletion-ready | `origin/codex/morning-meta-muse-spark-append` | authorization only |
| `origin/codex/grok45-morning-smoke` | deletion-ready | `origin/codex/morning-meta-muse-spark-append` | authorization only |
| `origin/codex/llava-vllm-runtime` | deletion-ready | Morning append and primary-preservation remotes | authorization only |
| `origin/codex/radle-v2-pre-m7-repair` | deletion-ready | post-admission remote and local consolidation | authorization only |
| `origin/fix/stats-combiner-scorer-from-final` | deletion-ready | `origin/main` | authorization only |
| `origin/codex/radle-v2-post-admission-panels` | wait for successor push | local consolidation branch | push `codex/radle-v2-branch-consolidation` first |
| `origin/codex/meta-muse-spark-colab` | unique remote hold | no current integrated successor | separate Meta/Morning decision |
| `origin/codex/morning-meta-muse-spark-append` | active hold | itself | complete separate lane work |
| `origin/codex/radle-v2-primary-preservation` | active archival hold | local branch is ahead 2 | push `f04fffb` and `11fd85c` first |

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

- Observation: Windows read-only attributes on `.git/worktrees/radle_v2_incremental_admission` prevented Git from deleting stale metadata after it had already removed the checkout and registration.
  Evidence: the checkout path no longer existed and `git worktree list --porcelain` omitted it; guarded PowerShell cleanup removed only the exact stale metadata directory. The same attribute was cleared before normal removal of the post-admission worktree.
  Date/Author: 2026-07-12, Codex/GPT-5

- Observation: the GPT smoke worktree path was named `RadLE v2 - grok45 push`, and Git again deregistered it before Windows refused to delete the read-only checkout shell.
  Evidence: the pre-removal status was clean except `src/__pycache__/radle_benchmark.cpython-311.pyc`; after Git removed the registration and metadata, guarded PowerShell deletion removed only the exact stale checkout directory.
  Date/Author: 2026-07-12, Codex/GPT-5

- Observation: the six ignored pre-M7 reasoning-probe CSVs were not unique evidence.
  Evidence: independent Wave 2 comparison found zero semantic mismatches against the six committed JSON receipts; CSV sizes were 336, 502, 588, 740, 905, and 1687 bytes, with hashes recorded in the agent receipt.
  Date/Author: 2026-07-12, Rawls subagent

- Observation: primary-preservation contains three unique archival commits but no production panel behavior missing from consolidation.
  Evidence: `441b25a` is stable-patch-equivalent to `9727248`; the production effect of `88d66e0` is represented by adapted integration commit `2f70441`; `a9e7115`, `ee1ea49`, and `5e6fd51` remain archival-only on the retained primary-preservation remote.
  Date/Author: 2026-07-12, Laplace subagent and Codex/GPT-5

- Observation: the final-scoring worktree's only untracked file was a unique 9524-byte arXiv statistics ExecPlan.
  Evidence: source SHA-256 `9A68A1D99A799EF0235809FF69642A8EE2AFE6169AD0D21011EB9F08999437B8` matched the path created on primary-preservation; committed blob is `486e84a0ae13bd46a3eab0a992c0f089bb72862b`.
  Date/Author: 2026-07-12, Pauli subagent and Codex/GPT-5

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

- Decision: close the first local set immediately after validation, while retaining every remote ref.
  Rationale: exact ancestry and clean tracked status made the local refs redundant; remote deletion is a separate external action and was not inferred.
  Date/Author: 2026-07-12, Codex/GPT-5

- Decision: close GPT-5.6 and Grok 4.5 smoke branches locally without closing the Morning append target.
  Rationale: both smoke tips are exact ancestors of the Morning target, but the Morning target still carries unique integration work and remains a separate active lane.
  Date/Author: 2026-07-12, Codex/GPT-5

- Decision: close the two detached Claude worktrees and fast-forward local `main` without touching the primary checkout branch.
  Rationale: both detached tips were exact ancestors of `origin/main`, their only ignored files were bytecode caches, and local `main` was an unused strict ancestor of the fetched remote baseline.
  Date/Author: 2026-07-12, Codex/GPT-5

- Decision: close the pre-M7 local branch/worktree while retaining its older remote ref.
  Rationale: merge `44b6f70` preserves both local-only commits, the worktree had no tracked or untracked changes, and the only potentially unique ignored probes were independently proven redundant with committed JSON receipts; remaining ignored content was caches and generated test output.
  Date/Author: 2026-07-12, Codex/GPT-5

- Decision: merge the single current `origin/main` commit into the consolidation target.
  Rationale: the synthetic merge was conflict-free, the unique file was a valid token-clean notebook, and making the fetched baseline an ancestor removes avoidable future integration drift.
  Date/Author: 2026-07-12, Codex/GPT-5

- Decision: preserve the unique arXiv stats-story plan on primary-preservation before closing final-scoring.
  Rationale: that lineage owns final-scoring and panel archival evidence; byte and line comparisons passed, and the source worktree had no other untracked content.
  Date/Author: 2026-07-12, Codex/GPT-5

- Decision: stop local branch deletion at the five-branch/four-worktree state.
  Rationale: every remaining local branch is active, dirty, uniquely ahead, or the canonical baseline. Further reduction requires pushing local successors, triaging the dirty primary checkout, or deciding how the unique Meta Muse remote should integrate.
  Date/Author: 2026-07-12, Codex/GPT-5

## Revision Notes

- v7 (2026-07-12, Codex/GPT-5): completed local consolidation, integrated current `origin/main`, preserved the arXiv plan, recorded closure set 5, and added the final remote-action queue.
- v6 (2026-07-12, Codex/GPT-5): recorded pre-M7 closure set 4, independent probe-equivalence evidence, and completion of the Morning smoke audit.
- v5 (2026-07-12, Codex/GPT-5): recorded local Claude closure set 3 and synchronized local `main` with fetched `origin/main`.
- v4 (2026-07-12, Codex/GPT-5): recorded local Morning smoke closure set 2 and the guarded removal of its read-only stale checkout shell.
- v3 (2026-07-12, Codex/GPT-5): recorded local closure set 1, retained remote refs, and documented guarded Windows worktree metadata cleanup.
- v2 (2026-07-12, Codex/GPT-5): recorded Wave 1 receipts, merge `44b6f70`, combined validation, and the first closure-wave boundary.
- v1 (2026-07-12, Codex/GPT-5): created the ledger from refreshed Git state, linked the admission ExecPlan, recorded the initial branch register, and established sequential closure gates.

## Outcomes & Retrospective

All five milestones are complete for the authorized local scope. The admission/panel histories and current baseline are consolidated, validation passes, eleven local branches and seven worktrees were removed, one unique untracked ExecPlan was preserved and reconciled, and every remaining local/remote ref has a named disposition. The repo is materially simpler without deleting remote refs or touching the 91-path dirty primary checkout. No new skill promotion is needed; the preservation-plus-cleanliness closure gate is already represented by the installed workflow guidance.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Ledger and planning | `workflow-router`, `execplan` | Keeps branch posture explicit and the ledger restartable | `auto-suggest` |
| Read-only wave audits | `none` | Scoped Git commands and independent agents are sufficient | `none` |
| Integration | `none` | Direct Git operation plus repository tests is sufficient | `none` |
| Pre-commit review | `Code Reviewer` if available | Useful for checking the staged consolidation boundary | `auto-suggest` |
| Final closure classification | `none` | Closure rests on explicit Git/worktree evidence | `none` |

## Context And Orientation

The repository now has four worktrees: the dirty primary handwritten checkout, the clean Morning append lane, the clean consolidation target, and the clean-but-ahead primary-preservation lane. The former post-admission and pre-M7 source histories are ancestors of consolidation; their local worktrees are closed. A Git worktree is a second checkout attached to the same repository; deleting a branch that is checked out in a worktree is blocked and removing a dirty worktree can lose uncommitted work.

Consolidation mutations occurred from `C:/tmp/radle_v2_branch_consolidation`; the one path-only archival preservation occurred in `C:/tmp/radle_v2_primary_preservation`. Read-only audits inspected other worktrees. The dirty primary checkout was never used for stage, commit, merge, branch deletion, or cleanup.

## Plan Of Work

Milestone 0 records live state and creates this ledger. Milestone 1 integrates the pre-M7 continuation into the active target. The integration method is selected from actual ancestry and conflict evidence; because the source has two coherent sequential commits, a non-fast-forward merge is preferred if the synthetic merge is conflict-free and preserves both branch histories. Cherry-pick is the fallback when merge topology would obscure an unrelated source boundary.

Milestone 2 validates both sides of the combined stack. Admission gates include Python compilation, config checks, and the focused unit suite. Panel gates include the existing base-authority check and relevant deterministic panel/audit tests available in the branch. Git gates include `git diff --check`, a secret-pattern scan, and a clean status after commit.

Milestone 3 closes only local branches and worktrees that are proven redundant and clean. Each deletion is preceded by a fresh status and ancestry check, then recorded in this register. Remote branches are queued separately and are not deleted by implication.

Milestone 4 classified the Morning append lane without merging it into the admission/panel stack, closed contained smoke branches, retained the unique Meta remote, and produced the residual/remote action register. The llava local alias was later closed after exact containment by retained branches was proven.

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

Current-baseline validation receipt:

    ORIGIN_MAIN_MERGE=351b3af
    NOTEBOOK_JSON=PASS nbformat=4 cells=10 code=10 outputs=29
    NOTEBOOK_SECRET_SCAN=PASS
    Ran 37 tests in 77.091s
    OK
    CONFIG_RESULT=PASS
    PANEL_TREE_PRESERVED_AFTER_BASELINE=PASS files=52

Local closure set 1:

    WORKTREE_CLOSED=C:/tmp/radle_v2_incremental_admission
    BRANCH_CLOSED=codex/radle-v2-incremental-admission tip=77dbfb0
    WORKTREE_CLOSED=C:/tmp/radle_v2_post_admission_panels
    BRANCH_CLOSED=codex/radle-v2-post-admission-panels tip=2f70441
    BRANCH_CLOSED=fix/stats-combiner-scorer-from-final tip=2d1028c successor=origin/main@f3c7d72

Local closure set 2:

    WORKTREE_CLOSED=C:/Users/thehb/Documents/RadLE v2 - grok45 push
    BRANCH_CLOSED=codex/gpt56-openrouter-smoke tip=8feeb7b successor=codex/morning-meta-muse-spark-append@37a0f44
    BRANCH_CLOSED=codex/grok45-morning-smoke tip=1faee5a successor=codex/morning-meta-muse-spark-append@37a0f44

Local closure set 3:

    WORKTREE_CLOSED=.../.claude/worktrees/elated-germain-35c138 detached_tip=e03b2e0 successor=origin/main@f3c7d72
    WORKTREE_CLOSED=.../.claude/worktrees/sad-meninsky-7102e8 detached_tip=f8a529d successor=origin/main@f3c7d72
    BRANCH_CLOSED=claude/elated-germain-35c138 tip=e03b2e0
    BRANCH_CLOSED=claude/sad-meninsky-7102e8 tip=f8a529d
    LOCAL_MAIN_FAST_FORWARDED=080ec65..f3c7d72

Local closure set 4:

    PROBE_CSV_EQUIVALENCE=PASS count=6 semantic_mismatches=0
    WORKTREE_CLOSED=C:/tmp/radle_v2_pre_m7_repair tip=e2e0c2b
    BRANCH_CLOSED=codex/radle-v2-pre-m7-repair tip=e2e0c2b successor=eed1dda remote_retained=b543827

Local closure set 5:

    ARXIV_PLAN_PRESERVED=f04fffb handoff=11fd85c blob=486e84a0
    WORKTREE_CLOSED=C:/Users/thehb/Documents/RadLE v2 - final scoring questions
    BRANCH_CLOSED=codex/final-scoring-csv-questions tip=071d6ec
    BRANCH_CLOSED=codex/llava-vllm-runtime tip=56a882b
    LOCAL_ALIAS_CLOSED=codex/meta-muse-spark-colab tip=e4f2e84 remote_retained=true
    FINAL_LOCAL_BRANCHES=5
    FINAL_WORKTREES=4

## Interfaces And Dependencies

This plan depends only on Git, PowerShell, and the repository's existing Python 3.11 validation commands. It introduces no runtime interface. Its durable artifact is `Documents/execplan_radle_v2_branch_consolidation_ledger.md` on `codex/radle-v2-branch-consolidation`.
