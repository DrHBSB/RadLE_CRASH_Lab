# Admit Argon as the seventeenth model through Morning

This living ExecPlan follows ~/.codex/PLANS.md and the collection worktree AGENTS.md.

## Purpose / Big Picture

Expand the current October16-model collection to17 through the existing four-cell Morning notebook. Preserve all prior answers, failures, flags and attempt evidence; collect only the200Argon responses, automatically audit, run bounded eligible repairs and audit the combined3400cells. The user starts Colab. Older historical-study consolidation happens after this cohort is audited/promoted, not during this task. No private data or paid clinical requests are sent locally.

## Current State

SUPERSEDED 2026-10-16 root: the user requires reusable roster-driven admissions, not a model-specific module. Active implementation and handoff are now Documents/execplan_collection_admission_20261016.md. Existing experimental data, runlabel and retryauthority stay preserved; only code/config organization changes. This document records the prior correction, not current execution instructions.

## Locked Facts

- Canonical notebook: notebooks/RadLE_v1_5_Morning.ipynb, exactly four cells, autonomous workflow calls in Cell4. No separate Argon notebook.
- Existing source: Runs/openrouter_16_32k_20261008/raw/results.csv; user output reports3186saved,14unresolved,200rows269columns and finalbackup0045. This is user-provided runtime evidence, not a fresh agent download.
- Expanded cohort version: Runs/openrouter_17_32k_20261016. Its initial wide CSV is a byte-for-byte copy of the16-model source, not an Argon-only dataset. Source16-model run remains immutable.
- ACTIVE_MODELS contains source16models plusArgon; COLLECTION_MODELS contains Argon only. The new collection journal grants authority only forArgon, while cohort_admission.json pins the original journals/checkpoint and retains all inherited unresolved states/attempt counts.
- Argon google/gemini-4-argon, canonicalgoogle/gemini-4-argon-20261013; pinned Google google-vertex/global, ZDR, data_collection deny, no provider fallbacks. High initial reasoning, medium/low supported fallbacks;32768cap,concurrency1,sameprompt/images.
- At most2ordinary plus2durable spaced repairs perArgon pair; fixed policyIDradle-argon4-two-repairs-20261016,minimum60secondspacing. Stop on success; uncertainty/refusal/quota/local blocks stayheld. SDK transport retries disabled. Known empty-at-cap can end ordinary phase early;4is an upper bound, not required spending.
- Automatic order: collect -> pre-repair audit -> eligible bounded repairs -> final full17-model audit. No automatic private promotion, public export, judging or old-model requests. User separately requested later audit/promotion and subsequent historical consolidation.

## Do Not Revisit

- User approved narrowed17-model phase after identifying the missing historical scope; do not block this launch on consolidating the29historical arms (Decision2026-10-16).
- Do not create another notebook, change paid IDs, reset counts, overwrite old source columns, resend old failures or replace immutable historical releases. Do not edit Colab cells or Drive manually.
- Do not call anArgon-only gate a clean17-model gate; inherited14unresolved outcomes remain explicit in combined status.

## Progress

- [x] (2026-10-16 root) Read Octoberreadiness/Morning handoff, collection recovery/retry, and incremental-admission ExecPlans. Trace Mistral315be12cohort extension and historicalwide source headers.
- [x] (2026-10-16 root) Correct notebook targeting and preserve16-modelwide source by validated admission; remove standalone notebook.
- [x] (2026-10-16 root) Seven correction tests prove metadata drift holds,4-attempt replay bound, reasoning ladder, oldfield/evidence preservation, new-arm-onlydispatch, canonicalworkflowcombinedstatus and4-cellcompilation.
- [x] (2026-10-16 root) Rerun focused tests after explicit pre-repair audit labels; stage scoped changes, commit/push and immutable tag; verify remoteSHA and hand off canonicalColabURL.

## Surprises & Discoveries

2026-10-16 root: generic retry mode selects only its granted jobs and replaces ordinary pending authority, so ordinary collection runs first, then one durable repair phase. Old unresolved responses must not be given this grant. Collection lane remains Argon-only even though the CSV and final audit include17models.

## Decision Log

2026-10-16 user/root: narrowed scope approved after correction: finish17-modelOctobercohort now; historical29-arm consolidation later through the established admission process. Prior separate notebook is removed, its Git history remains recoverable.

2026-10-16 root: follow priorMistral pattern with canonicalMorning plus expanded cohort version carrying oldwidecolumns. Keep old journal/artifacts at pinned immutable paths rather than injecting fabricated old requests into the newArgonjournal. SourceCSV/contract/checkpoint copied privately; sourcejournal digest and paths plus original unresolved evidence retained. Source locks/hash mismatches fail closed.

## Revision Notes

2026-10-16 root: reconcile previous wrong separate-notebook design in place. Contradicting artifact: October5readinessplan says no parallel notebook; user expected oneexperiment. Missed verification: source/admissionplans before initialimplementation. Userview: isolatedArgonlink, then17-onlyproposal before explaining29historicalarms. User now explicitly approves17now/historicalmerge later, resolving scope block. No historical consolidation claimed.

## Outcomes & Retrospective

Corrected offline implementation ready for finaltests/publication. Prior40retry/reasoning/recoveryregressions passed on unchanged sharedcollector modules;7Argoncorrectiontests passed. Latest route receipt Documents/argon4_route_receipt_20261016.json confirms metadata/authenticatedZDR only, not clinical response success. Live acceptance remains user-started. No reusable skill mutation needed.

## Suggested Skills By Phase

Execplan/manual for planning and corrections; jupyter-notebook/manual for aligned four-cellNotebook. StandardPython/unittest for validation. No delegation. Browser limited to opening/running/monitoring committed release if later requested.

## Concrete Steps and Acceptance

From existing collection worktree run python -X utf8 -m unittest discover -s tests -p test_argon4_colab.py; expect7passingtests. Compilefourcells and git diff --check. Commit only Documents/execplan_argon4_colab_20261016.md, src/radle_argon4.py, tests/test_argon4_colab.py, notebooks/RadLE_v1_5_Morning.ipynb and deletionnotebooks/RadLE_Gemini_4_Argon.ipynb. Pushbranch andtagcodex/radle-17-argon4-20261016, verifyremoteSHA. User opens fullSHAcanonicalMorningURL andRunall. ExpectREADY17modelscope/Argononly, billingpassed, actualArgonrequest, durablebackup,pre-repairaudit, boundedrepairs and combined3400cellaudit. No repeated grant onresume.

## Idempotence and Recovery

ParentCSV/journal/checkpoint/contract are hash-pinned and must stay unchanged onresume. Freshadmission fails if locks, incompatible sourcecontract, non200casecohort, incompleteinitialization or already-started supersededArgon-onlyoutput exists. Never silently discard suchdata. NewCSVbaseline preserves all oldcolumns; finalcombinedaudit compares every inheritedfield to frozenparent. SameRunlabel/policyID resumes onlyunusedArgonauthority. No lockreclamation or journalreset.

Publication receipt2026-10-16root: canonicalColab https://colab.research.google.com/github/DrHBSB/RadLE_CRASH_Lab/blob/89d175fe58354b3dd5c2d4dfdbbe5af63d57133a/notebooks/RadLE_v1_5_Morning.ipynb . Status-only localplanupdate follows the immutablecode release.
