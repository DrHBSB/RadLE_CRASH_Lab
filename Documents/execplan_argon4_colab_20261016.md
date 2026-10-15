# Prepare the separate Gemini 4 Argon Colab run

## Purpose / Big Picture

Provide a Git-backed four-cell notebook the user can start before sleeping. Collect Argon on the same 200 images and prompt, without modifying the completed 16-model run. Publish aligned Python/notebook under an immutable tag. No paid requests are issued locally.

## Current State

2026-10-16 root: implementation and45focusedtests verified on existing codex/radle-journal-recovery worktree, parent f7f3d33. Live authenticated metadata verifies pinned Google route and ZDR; receipt Documents/argon4_route_receipt_20261016.json contains no credentials. Next commit only new Argon files, push branch/tag and provide full-SHA Colab URL. Existing dirty plans/logs are excluded.

## Locked Facts

- User approved maximum four paid attempts per case-model pair: two ordinary plus two repair attempts; stop on success and hold unknown/refusal/billing/local failures.
- Output cap32768, concurrency1, same200cases/prompt/images. High initial effort, medium/low enabled fallbacks after confirmed ceilings. No promotion/export/judging.
- Source16-model contract is read only; source results and backup0045 remain untouched. New run gemini_argon4_32k_20261016 has no answer/attempt migration.
- Metadata verified2026-10-16: canonicalgoogle/gemini-4-argon-20261013, Google google-vertex/global status0 cap65536, effortshigh/medium/low. Authenticated ZDR listing and billing are checked in Colab before inference.

## Do Not Revisit

- No extra synthetic paid smoke: first actual dataset request is saved under ordinary journal authority. No new retry IDs on rerun (Decision2026-10-16).
- No browser code edits or manual Drive modifications. Existing canonical16-arm notebook remains unchanged.

## Progress

- [x] (2026-10-16 root) Read applicable AGENTS, globalPLANS, existing workflow, retry queue and reasoning helper; verify public endpoint metadata.
- [x] (2026-10-16 root) Prepare isolated module and four-cell notebook with contract/image guard and ordinary-then-repair workflow.
- [x] (2026-10-16 root) Verify mocked route drift/privacy checks, prompt/image isolation, four-attempt/restart bounds and notebook compilation.
- [ ] (2026-10-16 root) Commit/push new Argon files and immutable tag; provide runnable URL. Live inference is user-started and unverified here.

## Surprises & Discoveries

2026-10-16 root: explicit generic retry mode replaces ordinary pending authority, so fresh run must execute ordinary phase first, followed by one durable repair phase. A confirmed empty-at-cap outcome can terminate ordinary phase early; four is a maximum, not a requirement to spend all four. Existing recovery/stepdown capture is reused without modification.

## Decision Log

2026-10-16 root: fixed new Argon run and retry ID; exclude uncertain/quota/refusal/local-block outcomes from repair. Pin canonical version in metadata preflight, official Google route, ZDR and data_collection deny. Highest/fallback ladder is checked live; future metadata drift stops before spending.

## Revision Notes

2026-10-16 root: initial authorized implementation. Existing plans/logs preserved and excluded from commit.

## Outcomes & Retrospective

Offline verification complete:5Argon tests,12retry tests,9reasoning tests and19journal recovery tests pass (45total); four notebook cells compile. Live metadata authentication and ZDR verification pass; no paid smoke performed. Publication next. No local paid calls, live Drive mount, or collection completion claim. No new reusable skill needed for this scoped admission.

## Suggested Skills By Phase

Planning: execplan/manual. Notebook creation: jupyter-notebook/manual, clone existing tested four-cell workflow. Testing/publication: none. No delegation.

## Concrete Steps and Acceptance

From existing feature worktree run python -m unittest discover -s tests -p test_argon4_colab.py, then relevant retry/reasoning regressions. Tests must prove unchanged original artifacts, same four-attempt upper bound after repeated execution, protected held states, route/cap/privacy drift failure and compiled four-cell notebook. Publish tag codex/radle-argon4-colab-20261016 and verify remote SHA. User opens immutable Colab URL and Run all; normal Drive/Secrets approval may appear. Live acceptance requires READY exactrelease, billingpassed, actual dispatch and durable result backup.

## Idempotence and Recovery

Resume with same run label and authorization ID. Contract mismatch, unknown lock or journal evidence failure stops; never delete/reset history. Collector uses existing protected recovery and private response artifacts. Existing16-model paths are read only. If publication fails, preserve commit and report exact limitation.
