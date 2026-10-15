# Reusable roster-driven Morning model additions

This living ExecPlan follows ~/.codex/PLANS.md and the collection worktree AGENTS.md.

## Purpose / Big Picture

Keep one Morning notebook and one general Python admission workflow. Add future models by extending the roster configuration, preserve existing results and request history, and automatically collect, audit, perform bounded eligible retries and audit the whole expanded experiment. No model-specific notebook, Python module, headings or conditional branches. The current configuration adds one model to the October16-model cohort; older-study consolidation remains deferred by explicit user instruction.

## Current State

2026-10-16 root: generic implementation prepared in existing codex/radle-journal-recovery worktree, parent89d175fe58354b3dd5c2d4dfdbbe5af63d57133a. New src/radle_collection_admission.py and configs/radle_collection.json replace src/radle_argon4.py. Canonical four-cell notebooks/RadLE_v1_5_Morning.ipynb is model-neutral. Seven tests pass, including successive arbitrary roster additions and inherited failure lineage. Live metadata-only check passed for configured17entries/oneaddition, high->medium->low reasoning and ZDR. Twelve existing retry regressions also pass (19targetedtests total). Next commit/push only scoped files and tagcodex/radle-roster-admission-20261016. No paid inference or browser launch.

## Locked Facts

- configs/radle_collection.json contains the complete model roster, parent/output run labels, capability/version pins and existing paid retry authority. It preserves current runopenrouter_17_32k_20261016, parentopenrouter_16_32k_20261008 and policyradle-argon4-two-repairs-20261016. IDs stay unchanged to preserve any already-created durable authority.
- New work is the roster-name difference against the parent's frozen contract. No named-model switch; arbitrary roster sizes and multiple additions work. Removing/changing old model settings fails closed.
- Existing results are copied byte-for-byte into the expanded cohort baseline; existing requests remain in hash-pinned parent journals/checkpoints. No old-model dispatch, grant, reset or fabricated exhaustion. Inherited failures/refusals/unknowns and attempts remain explicit, including through successive expansions.
- Same images/prompt/cap required; ordinary2 plus up to2durable spaced repairs, no automatic repeat grants, stop on success, new unknown/refusal/credit/localblock held. Concurrency1/currentcap32768. Highest verified enabled reasoning and conditional one-level ceiling reductions reuse existing general policy.
- One Runall: collect -> audit -> eligible repairs -> full-roster audit. No promotion/publicexport/judging or old-study consolidation in this release. Source data/keys never enter Git.

## Do Not Revisit

- No separate Colab, model-specific Python workflow or hard-coded model counts (usercorrection2026-10-16).
- No retry ID/run-label changes simply to obtain more calls. Do not delete journals, manually modify Drive or edit browser cells.
- Historical29-arm consolidation remains after this cohort's later audit/promotion; not a launch blocker under the user's approved narrowedscope.

## Progress

- [x] (2026-10-16 root) Reconcile user correction: earlier Argon-specific admission was wrong abstraction despite preserving data. Remove special workflow/module; retain only declarative model settings.
- [x] (2026-10-16 root) Implement generic roster diff, capability checks, source/attempt lineage and combined audit. Configure same17-model cohort and unchangedbudget.
- [x] (2026-10-16 root) Seven tests pass: arbitrary model names/counts, successive additions, parent field/attempt/failure preservation, metadata drift holds,4-attempt cap/replay and neutral canonical notebook.
- [x] (2026-10-16 root) Complete retry regressions, scoped commit/push/tag and remote verification; give canonicalMorninglink.

## Surprises & Discoveries

2026-10-16 root: a later admission's current journal covers only its own additions. Preserving older failure history therefore requires retaining inherited outcomes from its admission receipt in addition to current journal outcomes. The new engine hashes that parent receipt and carries the full non-overlapping lineage forward. A two-successive-addition test proves old failures/attemptcounts survive.

## Decision Log

2026-10-16 user/root: let additions run naturally from roster/history. Derive new work from the configured roster rather than hard-code Argon. Preserve exhausted or held old states exactly; do not artificially mark all old attempts exhausted. User approval covers publication of this correction, not more paid attempts.

2026-10-16 root: configuration stores immutable version pins, supported reasoning ladders and exact routes. Generic preflight checks only roster additions, since finished arms are retained without dispatch. Reruns use the same contract and retryID. Currentcontract_release stays unchanged for compatibility; runtime Git release is separately pinned in Cell1.

## Revision Notes

2026-10-16 root: supersedes Documents/execplan_argon4_colab_20261016.md. Contradictingartifact: user identified Argon-labelledmodule/cells instead of a reusable workflow. Missedverification: test arbitrary nextmodel and successive additions before initialrelease. Correction now includes those tests and neutral notebook assertions; no model-specific code path remains. Earlier separate notebook was already deleted at89d175f.

## Outcomes & Retrospective

Offline generic path,19targetedtests and authenticated metadata verified; publication pending. Live Colab Drive/Secrets flow and paid collection not executed here. No claim that the whole historicalstudy is consolidated or the combineddataset is promoted. No global skill/memory changes required.

## Suggested Skills By Phase

Execplan/manual for durable scope and handoff; jupyter-notebook/manual for canonical four-cell alignment. Standardunittest/metadata tools for evidence. No delegation or newworktree needed; existing unrelated dirty files preserved.

## Concrete Steps and Acceptance

Run python -X utf8 -m unittest discover -s tests -p test_collection_admission.py and test_retry_policy.py. Compile allfourcells and git diff --check. Assert no Argon/16/17/3400 special cases in src/radle_collection_admission.py or notebook. Commit configs/radle_collection.json, genericmodule/tests, canonicalnotebook and plan; delete src/radle_argon4.py and tests/test_argon4_colab.py. Publish tagcodex/radle-roster-admission-20261016 and verify remoteSHA. User opens immutable canonicalMorningURL andRunall. Expected READY counts derive fromconfig, existinganswers/history retained, only rosteraddition requests, then audit/boundedrepair/finalaudit.

## Adding the Next Model

Extend models in configs/radle_collection.json without altering old entries. Record its exact canonicalID and verified enabled reasoning levels in capabilities; preserve privacy/pin settings. Set parent_run to the completed current cohort and run_label/contract_release to the next explicitly approved cohort version. Scope retry_authorization to newly admitted pairs and approved attempts; never change identity to repeat an existing pair. Publish an aligned immutable release; no Python branch or second notebook is needed.

## Idempotence and Recovery

ParentCSV/journal/checkpoint/contract/admissionreceipt are hash-pinned; refuse changed parents, active locks, duplicate name/settings, unexpectedimages or partialinitialization. Superseded incompatible outputs are a config-level guard and require evidence reconciliation. Same contract/policyID resumes only unused authority. Each finalaudit compares every inheritedfield against the frozenparent. Errors stop instead of resetting history or silently repeating calls.
