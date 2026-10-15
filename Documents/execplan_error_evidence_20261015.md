# Evidence-qualified collection diagnostics

## Current State
2026-10-15 root: reviewing saved columns and adding observation-only error evidence; no paid calls, scheduling changes, promotions or Drive edits. Last supplied round4output3119saved/3200,81unresolved,67reasoningflags,backup0039. Isolated codex/radle-journal-recovery worktree.

## Locked Facts
Existing CSV has diagnosis, raw final answer (truncated2000characters), readable reasoning, prompt/completion/reasoning tokens, usage JSON, provider/model/requestextras and response timestamp. Journal has authoritative attempts, repair marker, HTTPstatus, typed provider diagnostics, response metadata and cumulative attempt history when retained. Audit legacy repair counters are from a different call log. Final CSV fields can predate latest HTTP failure.

## Do Not Revisit
No inferred clinical cause, no generic content rejection equals safety refusal, no account balance inference fromHTTP402, no invented missing tokens/finish reasons, no new repairround. Preserve files and receipts. Git-only notebook publication.

## Progress
2026-10-15 root: implemented shared evidence_record and summaries; separated image technical codes and policy codes; evidence inventory attached to completed workflow and read-only audit; storedfailure_evidence.json on future collector completion. Updated notebook defaults toauditonly, no extra calls. 53 focused tests pass; publication pending.

## Surprises & Discoveries
2026-10-15 root: raw answer is truncated2000chars; audit repair_attempts_so_far was legacylogcount. Preserve compatibility with explicit source marker. Currentmetadata must not be backfilled with olderCSVusage. Structured evidence reports missing fields as null.

## Decision Log
2026-10-15 root: preserve raw fields; observation/qualification separate from unknown rootcause. Retrospective audit can show latest retained evidence only, cannot manufacture prior provider messages. Strict replay and hashchecks remain.

## Revision Notes
2026-10-15 root: added exact typedcode distinction, journalcounter provenance, staleCSVmarker and stopped-dashboard correction.

## Outcomes & Retrospective
53 focused tests pass:6evidence,10display,10surgical,10repair-round,17recovery. Notebook four code cells compile; diffcheck clean. No manuscript causal counts claimed; no live data modified. Immutable release pending.

## Suggested Skills By Phase
Execplan and jupyter-notebook apply to existing canonical four-cell notebook and living plan. No browser execution needed to publish logging changes.
