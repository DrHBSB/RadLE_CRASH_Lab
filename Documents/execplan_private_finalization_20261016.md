# Private finalization with explicit dispositions

## Current State
2026-10-16 root: User explicitly authorized private finalization of the 17-model dataset. Implement a no-inference snapshot path, preserving raw bytes and recording unresolved pairs as failed with original evidence and analysis flags retained. Publish aligned canonical notebook; live Drive finalization must be verified separately.

## Locked Facts
User output:200cases,17models,287columns,3318accepted,68reasoningflags,14inherited unresolved. Source run openrouter_17_32k_20261016. No OpenRouter spending, no Gemini inference, no retries, no scoring or public export. Existing clean-publication gates unchanged. Raw diagnoses, provider fields, request history, images and source files remain untouched.

## Do Not Revisit
Do not attempt to make the audit clean by removing failures or reasoning flags. Do not invent causes or treat unknown outcomes as proven provider errors. Failed final dispositions retain original journal status and classifications. No repeated repair grants.

## Progress
2026-10-16 root: Existing promotion requires clean audit; create an explicitly non-clean private snapshot instead. Standard final CSV is byte-identical to raw. Sidecar outcomes identify every pair, with failures and flags. Manifest records source/evidence hashes, counts, false clean gate and private-only status.

## Surprises & Discoveries
2026-10-16 root: Finalization must bypass all API client/metadata setup, not merely prevent inference in the collector. Audit-only workflow and source existence guard are required.

## Decision Log
2026-10-16 root: New finalizer never imports a client, revalidates CSV-bound evidence and inherited values, refuses mismatched failure inventories, existing conflicting snapshots and active locks. Exclusive file creation with manifest written last; matching reruns verify artifacts and reuse the snapshot. Interrupted partial snapshots are preserved and rejected, never overwritten.

## Revision Notes
2026-10-16 root: Initial plan. Existing feature worktree retained; unrelated dirty plans/logs excluded from commits.

## Outcomes & Retrospective
Six private-finalization tests, eight admission tests and seven Gemini-only regression tests pass (21 total). Four notebook cells compile. Exact byte preservation, source changes, active lock refusal, disposition/evidence agreement, snapshot tamper and idempotence verified. Release codex/radle-private-final-20261016 prepared; live receipt pending.

## Suggested Skills By Phase
Execplan and existing jupyter-notebook workflow applied; standard unittest fixtures for no-network finalization and idempotency.
