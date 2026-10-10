# Improve repair pacing and finish the collection audit

This living ExecPlan follows C:/Users/thehb/.codex/PLANS.md and the execplan skill. Implementation and one further bounded repair are now directly authorized by the human user.

## Purpose / Big Picture


Make future authorized repairs avoid repeatedly hitting a rate-limited model, explain empty responses with evidence, and produce an honest audit even when some requests remain held. Saved answers must survive unchanged, and incomplete collection must never appear to have passed the clean-data gate. A user should see which work is runnable, cooling down, exhausted, failed, or held.

## Current State


2026-10-11, root: cooldown, partial audit, failure metadata and dashboard fixes implemented.10focused tests,10display tests,17recovery tests,5lock and5round2 tests pass; queue retains same2baseline failures, collector retains same4failures/4errors reproduced on exact HEAD5060d10 in a temporary parent snapshot. Approval review rejected round3 twice, including after later user intent was documented, stating exact round3 authorization was not unambiguous. No round3 code was applied. Preparing immutable audit-only release; third repair remains BLOCKED pending explicit review approval. Do not bypass. Production data unchanged by local tests.

## Locked Facts


- Verified pasted output: release5060d10393bdfe5b7c9d7735b831e8372434ef42, run openrouter_16_32k_20261008, final backup results_BACKUP_0035.csv at2026-10-11 01:11:16 IST, active0.
- Saved3099/3200 (96.84375%);121/200 complete cases. Round1 gained22 answers and round2 gained17.
- Remaining101 comprise80failed,15exhausted pending,4content rejections,1quota hold,1unknown remote outcome. Saved/flagged is not equivalent to audit-accepted.
- Cohort200cases x16models, output cap32768, concurrency3, original2 ordinary attempts and durable repair rounds1/2 must remain unchanged.
- All implementation must reach Colab through committed, pushed immutable Git releases. Never edit browser cells or manually change Drive.
- Existing worktree C:/Users/thehb/.codex/worktrees/radle-journal-recovery/RadLE v2, branch codex/radle-journal-recovery, contains the relevant5060d10 implementation and an uncommitted status update in Documents/execplan_colab_journal_recovery_20261010.md. Preserve it and unrelated primary-checkout changes.

## Do Not Revisit


- Do not reset history, delete locks, repeat consumed lock retirement, loosen provider/privacy/reasoning gates, or buy credits. See Decision Log2026-10-11.
- Do not interpret empty raw as proof of parser failure or token truncation. Evidence is still missing. See Decision Log2026-10-11.
- Only one separately durable round3 is now authorized; never create round4 or reset prior attempts. See Decision Log2026-10-11.

## Progress


- [x] (2026-10-11, root) Inspect pasted final output and trace queue dispatch, adapter outcomes, extraction, dashboard counts, and autonomous workflow.
- [x] (2026-10-11, root) Prepare surgical implementation plan and acceptance criteria.
- [ ] (2026-10-11, root) Inventory private saved evidence read-only; classify failures without new API inference.
- [x] (2026-10-11, root) Implement shared rate-limit cooldown, replay evidence and one model slot after429 until success;10focused tests pass.
- [x] (2026-10-11, root) Implement partial audit result, read-only audit path, bounded metadata inventory and truthful dashboard states.
- [ ] (2026-10-11, root) Implement extraction changes only if captured evidence proves a specific supported response shape is mishandled.
- [ ] (2026-10-11, root) Validate, review focused diff, publish immutable release when implementation is authorized; verify offline audit before any paid pass.

## Surprises & Discoveries


- (2026-10-11, root) src/radle_concurrent_collection.py:call reads numeric Retry-After and returns an Outcome retry delay, but queue.run stores readiness on the failed job only. Other jobs for that model remain eligible. Repair conversion to Outcome('failed', value) drops retry_after, so its final rate-limit result does not pace subsequent jobs.
- (2026-10-11, root) collect raises REVIEW REQUIRED at line599 after final export when held outcomes exist. Consequently run_autonomous_openrouter_workflow never reaches its existing completed_with_failures branch and audit. Fatal identity/lock/billing errors must still fail closed.
- (2026-10-11, root) extract_result reads chat message.content as a stripped string and separately stores reasoning/details and usage. The code inspection establishes supported-shape assumptions, not the cause of these particular empty outputs.
- (2026-10-11, root) progress_summary counts all pending as queued without checking attempt eligibility. Historical quota states also produced PAUSING during verified active dispatch. Dashboard view and scheduler state have diverged.
- (2026-10-11, root) Git status in the restricted shell reported 'must be run in a work tree'; this is not evidence of a broken checkout. Verify Git with appropriate approved filesystem access before implementation.

## Decision Log


- (2026-10-11, root) Keep this as a successor plan to the completed journal-recovery plan; avoid rewriting its historical recovery scope.
- (2026-10-11, root) Separate pacing from attempt authorization. Cooldown delays dispatch; it never refunds an attempt or grants another call.
- (2026-10-11, root) Start with a per-model cooldown because that grouping exists in every queued job. Broader provider/account cooldown requires evidence that the scope is shared; do not stall all models speculatively.
- (2026-10-11, root) Audit incomplete output through an explicit opt-in partial-result workflow path, leaving direct collector behavior fail-closed by default. Partial audit cannot promote, export, score, or claim clean gates.
- (2026-10-11, root) SUPERSEDING HUMAN AUTHORIZATION: after this plan the user said 'sure, go ahead', then explicitly 'please take care of it and ensure you refresh adn start the repair ...i want it doen by the time i wake up'. Following the usage-limit blocker, the user annotated that response 'please proceed' and reiterated 'do not stop midway due to auth ... good night'. This is a new request to implement fixes and start the discussed third repair, superseding the old no-round3 limit only for one bounded round. Grant only failed round2 terminal/retry outcomes, excluding remote-unknown/rejected/quota/exhausted pending and saved answers; retain durable per-pair authorization and never repeat round3.

## Context And Orientation


src/radle_job_queue.py coordinates jobs and is the only journal writer. A job is a case/model pair. Outcome.status describes a response; ready_at is the next eligible time. Repair markers authorize specific additional attempts durably. src/radle_concurrent_collection.py adapts API responses, saves CSV/checkpoints, and renders LiveProgress. src/radle_benchmark.py extracts responses and performs audit/workflow gates. notebooks/RadLE_v1_5_Morning.ipynb is the canonical four-cell entry point. Tests live under tests/.

The supplied source evidence is C:/Users/thehb/.codex/attachments/51ca4004-e847-4e9a-af93-b55103d4d152/Pasted text.txt. It includes empty-raw failures for Opus cases60,75,86 and a successful case77. Prior live monitoring observed Qwen rate-limit failures. Exact totals by failure cause require private journal inspection; do not infer them from the five recent dashboard events.

## Plan Of Work And Milestones


### 1. Establish failure evidence (skill: none)


Read existing journal/checkpoint/CSV and available saved response artifacts through authorized read-only access. Do not remount or run collection merely to inspect data. Build a local private inventory with case, model, attempt/repair round, HTTP status, failure category, response id, finish reason, native finish reason, prompt/completion/reasoning tokens, answer/reasoning lengths, and evidence path. Mark absent fields unknown. Avoid copying clinical images or raw answers into Git. Record source hashes and reconcile exactly101 unresolved pairs and3099 saved answers against backup0035; stop on disagreement.

For representative empty responses distinguish: no content with nonzero reasoning, length termination, content refusal, supported text omitted by extraction, genuinely empty response, and unknown. Inspect existing artifacts first. If full response evidence was never retained, document that limit and add minimal bounded diagnostics for future authorized calls; do not reconstruct an answer from reasoning.

### 2. Pace model dispatch (skill: none)


In src/radle_concurrent_collection.py:call retain explicit rate-limit category and sanitized delay, including parsing numeric or HTTP-date Retry-After. In src/radle_job_queue.py:run keep model cooldown separately from individual-job readiness and from repair terminalization. When a429 completes, update model readiness before considering new starts. Persist the absolute cooldown in result evidence so replay can restore the remaining wait without adding paid attempts. Reuse existing result schema/value fields where possible; validate finite, nonnegative delays and handle clock boundaries defensively. Already active requests drain normally.

During a cooldown other eligible models continue. After429 use one in-flight slot for the affected model until a successful response restores normal scheduling; repeated429 extends the cooldown rather than immediately cycling through new cases. Keep global concurrency3. Use an injectable clock or narrow scheduler helper for deterministic tests, avoiding real sleeps. Record the chosen default cooldown/backoff explicitly in code/config and do not tune it to force successful benchmark outcomes.

### 3. Audit saved partial output and fix display (skill: none)


In collect add an explicit allow_partial_result=False parameter. After durable final export, when enabled return a DataFrame carrying failed_pairs, held_pairs, exhausted_pairs, collection_status and receipt paths; otherwise preserve existing exception behavior. Identity mismatch, unknown lock, damaged/unproven journal and failed billing still raise and are never caught generically.

The autonomous workflow passes the opt-in, detects any unresolved category, runs audit_benchmark_output read-only, returns completed_with_unresolved with an empty gate receipt and no promotion/export/scoring, and prints category counts and paths. Existing completed_with_failures behavior remains supported. Notebook Cell4 prints the unresolved summary alongside the audit. Provide a separately explicit audit-only committed entry path so auditing backup0035 does not rerun collector/config recovery or issue inference calls.

In progress_summary and LiveProgress derive displayed runnable, cooldown, exhausted and held counts from the same eligibility helper used by scheduling. Actual scheduler pause/drain state determines PAUSING; historical holds appear as held. No display callback may mutate scheduling state. Show flagged counts distinctly from accepted audit results.

### 4. Conditional extraction correction (skill: jupyter-notebook only if notebook changes)


Only after milestone1 identifies a concrete mishandled response shape, add a narrow text-normalization helper in src/radle_benchmark.py:extract_result, with captured sanitized fixtures. Preserve route assertions and reasoning gates. Do not raise output caps, switch providers/models, rewrite prompts, use reasoning as final answers, or accept missing usage/reasoning. If evidence proves no extraction bug, skip this code change and record the diagnosis.

### 5. Release and handoff (skill: jupyter-notebook for canonical notebook validation)


Reuse the existing isolated worktree after verifying HEAD/status with appropriate filesystem access; do not reset or clean either checkout. Keep changes limited to the named source modules, relevant tests, canonical notebook when needed and this plan copied into that worktree. Commit focused verified changes, push an immutable tag, and verify the remote SHA. Browser execution only opens/runs committed releases after confirming active0 and backup. A new security warning previously rejected by automatic review remains a user handoff; never bypass indirectly. Validate audit-only behavior first. No automatic collection restart or third repair follows publication.

## Concrete Steps And Validation


From the isolated worktree, inspect existing tests before choosing fixtures:

    python -X utf8 -m unittest discover -s tests -p test_job_queue.py
    python -X utf8 -m unittest discover -s tests -p test_concurrent_collection.py
    python -X utf8 -m unittest discover -s tests -p test_journal_recovery.py
    python -X utf8 -m unittest discover -s tests -p test_repair_round2.py
    python -X utf8 -m unittest discover -s tests -p test_lock_recovery.py
    git diff --check

Use approved filesystem access for Windows temporary-directory tests if the sandbox prevents writes; do not change production logic to fix sandbox failures. Prior receipts:17recovery,5round2,5lock tests passed; queue34/36 with2known baseline failures, collector previously had4failures/3errors. Reproduce baseline on the exact parent before attributing failures; require no additional regressions and all new focused tests passing. Find actual workflow/extraction tests via rg --files tests before broadening validation.

Required behavioral tests: a429 for modelA prevents anotherA dispatch before its cooldown while modelB proceeds; repair finalization still preserves cooldown; replay preserves cooldown and durable repair markers; long and malformed Retry-After handling is deterministic; active calls drain; no attempt increase or saved-pair call occurs. Partial audit performs zero inference calls, returns101 categorized unresolved in a fixture matching the final state, never invokes promotion/scoring/export, and still refuses identity/lock/billing errors. Dashboard reports15 exhausted rather than15 runnable and does not say PAUSING merely because a historical quota hold exists. Extraction fixtures must preserve final-answer/reasoning separation and reject unsupported shapes safely.

If notebook changes, parse its JSON, compile each code cell, verify exactly four canonical cells and no stored outputs or secrets. A live acceptance receipt must identify immutable SHA, source hash, zero audit-only inference calls, category totals and unchanged source CSV hash. Do not claim live acceptance from offline tests.

## Idempotence And Recovery


Read-only inventory/audit is repeatable and must not change Drive journals/CSVs. New diagnostics are additive; old journals remain readable. Cooldown replay changes scheduling time only. Preserve every authorization and original attempt counter. On missing/corrupt authority or uncertain remote outcome remain held. On live failure drain/save, retain evidence and diagnose; never rerun blindly, delete a lock or restore an older scheduler over a newer journal. No rollback may erase repair history.

## Interfaces And Dependencies


Retain queue.Job, queue.Outcome and existing status semantics. Add only narrowly scoped eligibility/cooldown helpers and optional partial-result/audit-only parameters with safe defaults. Existing pandas audit output remains authoritative for acceptance; scheduler statuses alone do not establish data validity. No new external dependency is required. Audit-only must not initialize a paid collection request.

## Suggested Skills By Phase


Planning: execplan (activated and read), for durable scope/evidence/validation. Diagnosis, scheduler and audit implementation: none; focused Python inspection and tests suffice. Notebook edits: jupyter-notebook, auto-suggest when implementation reaches that phase, preserving four-cell structure. No subagents or new cloud services needed.

## Revision Notes


- (2026-10-11, root) v1: inspected actual5060d10 source and pasted final output; separated confirmed pacing/audit/display defects from unproven extraction hypotheses. Planning artifact only.

## Outcomes & Retrospective


Implementation tested locally; audit-only release pending publication/live acceptance. No third pass started; production data unchanged. Approval review blocks paid-attempt expansion. Expected outcome is fewer wasted rate-limit attempts and a usable partial audit, not guaranteed recovery of all101 answers. Judge preparation remains downstream of explicit audit disposition of missing/flagged cells. No global skill or memory updates are requested.
