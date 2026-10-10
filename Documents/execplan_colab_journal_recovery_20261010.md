# Restore collection through a Git release

## Purpose / Big Picture

Resume the existing RadLE collection without losing paid answers or granting additional attempts. All edits happen in this isolated Git checkout; publish an immutable release and open/run its four-cell notebook. Never edit Colab code or Drive files directly.

## Current State

2026-10-10: ca50404 bounded repair release stopped at an existing PID-only writer lock before dispatch. User explicitly approved terminating old runtimes and recovering leftover locks through Git. Manage sessions initially showed current ca50404 and old f1d3bdb (dd465e7 already gone); after Terminate other sessions, it reported No active sessions. New immutable release adds one-time retirement in configuration after contract/metadata checks. It archives both outer and queue legacy PID locks, consumes a durable receipt before unlinking, and refuses any later lock. Runtime acceptance pending; last verified saved answers3060/3200.

## Locked Facts

2026-10-10 user explicitly authorized one additional eligible repair attempt. New bounded repair release sets AUTO_REPAIR_UNRESOLVED_ONCE=True. Collector selects terminal failures only, plus jobs with an existing durable repair authorization (to resume/finalize without duplication). Unknown remote outcomes, rejected content, quota and exhausted pending evidence remain held. Original max_attempts remains2 and completed answers are excluded. Prior V3 release published f1d3bdb; live verification blocked by Colab Run anyway security prompt requiring user handoff. Never bypass that rejection.

- Run openrouter_16_32k_20261008: 200 cases, 16 models, concurrency3, cap32768, two attempts including inherited history.
- Original journal: 186277552 bytes, SHA256 7587e7bf0b33f9fa6bf19224f837b1a206fe1bfa6c446629697191ffd607d49c; 13 invalid fragments and out-of-order/missing events. Filtering invalid lines cannot replay.
- Downloaded checkpoint has1839 jobs. Its CSV hash matched the original CSV in the idle runtime. All valid event attempts are at or below checkpoint counts; latest results at equal attempts agree with checkpoint statuses.
- Original workspace has unrelated dirty changes; implementation branch codex/radle-journal-recovery is based on b9a2b9b in the managed worktree radle-journal-recovery.
- No scoring, promotion, export, purchases, or bypass of identity/billing. One bounded terminal repair attempt and one legacy lock retirement after verified runtime shutdown are explicitly authorized.

## Do Not Revisit

Do not skip invalid records or reset jobs. Do not use main's legacy notebook. Do not modify browser code or Drive directly (user steering and AGENTS.md).

## Progress

- [x] User approved old runtime termination; Colab reports No active sessions.
- [ ] Test and publish one-time lock retirement release.
- [ ] Run committed release and verify archive receipt plus repair dispatch.

- [x] 2026-10-10 root: inspect copied journal/checkpoint and identify corruption; preserve originals.
- [x] 2026-10-10 root: implement CSV-bound snapshot recovery and original archive verification.
- [x] 2026-10-10 root: eleven focused tests plus collector integration pass, including no request for recovered completed jobs.
- [x] 2026-10-10 root: eleven recovery tests and collector recovery integration pass; branch/tag published and remote SHA verified.
- [x] 2026-10-10 root: open/run published notebook; recovery succeeds, muse_spark_1_3 case180 saved at00:25:27 IST, backup0023 saved and three slots active.

## Surprises & Discoveries

- 2026-10-10 root: damaged journal contains fragments, missing records and result-before-start ordering; a checkpoint snapshot is safer than inventing individual events.
- 2026-10-10 root: two pre-existing queue tests fail identically on b9a2b9b; this patch does not alter dispatch/rejection policy.

## Decision Log

- 2026-10-10 root: recover only on explicit resume and failed strict replay, under both writer locks. Require exact manifest identity, cohort, attempt bounds, matching CSV hash, and agreement with valid events. Archive every original byte before replacing the replay log with manifest plus checkpoint snapshot. Saved fields come from exact CSV strings; uncertain requests remain held.
- 2026-10-10 root: new tag codex/radle-checkpoint-recovery-v2-20261010 points to notebook and modules together; preserve old tag and collection contract release field.

## Plan Of Work / Milestones

Implement src/radle_journal_recovery.py and strict snapshot replay in src/radle_job_queue.py. Wire recovery through the existing resume path in src/radle_concurrent_collection.py after billing. Update only REPO_REF in notebooks/RadLE_v1_5_Morning.ipynb. Add tests/test_journal_recovery.py. Publish the tested commit and tag; browser actions only open/run/monitor committed cells.

## Validation And Acceptance

Run python -m unittest discover -s tests -p test_journal_recovery.py: expect eleven passing tests. Run existing queue and collector tests; record any baseline failures explicitly. Check notebook JSON, four-cell count, unchanged contract/settings. Runtime acceptance requires RECOVERED with attempts unchanged, three active slots, then a new saved answer in the same run. A push alone is not runtime success.

## Idempotence And Recovery

Healthy journals take ordinary replay. Recovery is bounded by checkpoint attempts; archive filename includes original hash. Verify archive and candidate replay, then recheck journal/checkpoint/CSV immediately before replacement. On mismatch abort without replacing original. On interruption original archive remains. Subsequent snapshot replay verifies the archive and continues ordinary events. No raw data enters Git.

## Suggested Skills By Phase

Planning: global ExecPlan instructions. Notebook: jupyter-notebook skill for targeted release ref change. Runtime handoff: computer-use skill for open/run/monitor only. Tests: none.

## Revision Notes

- 2026-10-10 root: replace stale download-blocked plan with current Git-only implementation and evidence.

## Outcomes & Retrospective

Current lock recovery is not yet live-verified. Earlier journal recovery success does not prove this repair has started.

Git and live runtime acceptance complete. Original journal archived by SHA256, checkpoint counts preserved, new answer and backup observed. Existing exhausted/rate-limited pairs remain held under the two-attempt budget. Root cause of Drive journal corruption is not proven; recovery does not claim to eliminate recurrence.

2026-10-10 root: initial release a6da9de published; opened notebook and renewed existing Drive access. Stopped setup before collector to add CSV large-field compatibility; revised v2 immutable tag pending.

2026-10-10 revision: lock retirement is an explicit one-time externally verified shutdown recovery, not PID/age-based automatic reclamation. A failure after receipt creation requires review; never repeat authorization. Focused tests cover both locks, archives, data preservation, rerun idempotence, unknown locks and new locks after consumption.
