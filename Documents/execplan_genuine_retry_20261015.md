# Evidence-led retry plan for remaining RadLE case-model pairs

## Purpose

Give each eligible unsuccessful pair a technically valid, auditable retry, without changing the clinical target, erasing failures, repeatedly spending on the same unresolved cause, or selecting responses by clinical correctness. Passing means response-validation success, never a guarantee of a correct diagnosis.

## Current State

2026-10-15 root: implementing the approved response-durability and evidence work package in codex/radle-journal-recovery. User explicitly requires unchanged reasoning levels. Model roster, reasoning effort/visibility, outputcap32768, prompts/images/provider/privacy settings and attempt authority are unchanged. No new paid round is enabled; notebook remains audit-only/concurrency1. Added immutable locally staged/hash-verified private response and result artifacts; compact journal references with backward-compatible replay/recovery; original Responses identity/status preserved before local enrichment; local preparation/processing failures isolated; read-only archive lineage and per-pair retry-review table. Existing historical logs remain untouched. Current production ledger still requires the user to run the published audit release; no provider calls made locally.

## Locked Facts

- The displayed dataframe is truncated; it is not the full evidence ledger.
- Journal attempts, authorized repair limits, response-attempt metadata and CSV timestamps can differ. Counts alone do not prove a request was dispatched or returned.
- An existing partial metadata dictionary prevents the evidence helper from using CSV fields. This explains some missing displayed evidence but does not establish a provider cause.
- Some empty-answer records report completion tokens at32768; others are below that limit. No common cause has been established.
- Round4 only adds authority to selected consumed failed repair states. Ordinary exhausted pending, rejected and uncertain states were excluded. Another numbered round alone will not address all81 pairs.
- Collection configuration is200cases,16models,32768output cap and fixed provider/privacy/reasoning settings. User now prefers concurrency1. Saved successful answers and original attempt history are protected.

## Do Not Revisit

No wiping journals or repair markers, silently reclaiming locks, resending saved/flagged responses, interpreting missing metadata as zero, calling all image errors moderation, or claiming every pair had six requests. No prompt/image/provider/reasoning/output-cap changes hidden inside an ordinary retry. No promotion, public export or judging in this work package. Do not retry until success or condition retries on diagnostic correctness.

## Phase 1: Build the full attempt ledger (execplan; no inference)

Read the CSV, checkpoint, migration/replacement receipts, current journal and every hash-linked original archive. Preserve the original bytes. Reconstruct starts, results, grants, interrupted grants and unknown outcomes per pair. Deduplicate archived prefixes using lineage/event position and identity, not matching timestamps alone. Validate cohort, image/prompt/request hashes, grant authority and checkpoint agreement. Refuse contradictory or unverifiable chains. Record issued grant, dispatched start and returned result separately.

Produce one full CSV/JSON per-attempt ledger plus one81-row eligibility table, a separate67-row reasoning-flag table, source hashes and explicit missingness. All references to earlier attempts must carry attempt IDs and evidence source. Do not treat a recovered snapshot as original response evidence.

## Root-cause priorities from request to durable result

### A. Request sent, model answered and answer saved are separate facts

The scheduler appends start before pool.submit. It then calls the adapter, which may raise during response extraction or route assertions after paid inference. A counted attempt without a durable response can therefore reflect pre-dispatch interruption, transport uncertainty, received-but-unarchived output, or local processing failure. Replacing this with an unlimited free retry would also be wrong: unknown delivery can still incur cost.

Mitigation: retain distinct reserved, dispatch-entered, response-received, response-archived and validated events. Persist the exact request fingerprint and complete private returned envelope before extraction and route assertions. Record deterministic pre-request failure separately from ambiguous remote failure; neither process-local dispatch entry nor a client-generated ID proves exactly-once execution. Use supported provider receipts for reconciliation, not invented idempotency guarantees.

### B. Empty final answer can be a genuine completed inference without usable output

Some supplied rows report32768completiontokens,32768reasoningtokens and empty finalcontent. OpenRouter official reasoning documentation describes a shared reasoning/visible-output budget and this exact length-stop pattern. Confirm finishreason against the original envelope or generation metadata. Repeating the same maximal reasoning configuration under the same total cap can consume another full budget without producing an answer. Other rows belowcap require a different explanation.

Mitigation: original-contract trials remain recorded as failures when no valid final answer exists. A separately versioned recovery trial can reserve visible-output headroom by a supported reasoning-token budget or a larger total output allowance, after checking exact model/provider semantics. Do not invent one universal numeric budget, disable reasoning blindly, mine the reasoning trace for an answer, or merge altered-policy results into the primary benchmark without explicit methodology. Source: https://github.com/OpenRouterTeam/docs/blob/main/guides/best-practices/reasoning-tokens.mdx .

### C. Evidence is lost or conflated locally

extract_result parses the full chat content before saving Raw_Response truncated to2000characters. This truncation is not the cause of the immediate empty parse, but it limits later reprocessing. The Responses normalizer drops ID/finish/status fields. Partial metadata suppresses CSV fallback; safe reconstruction requires matching response identity rather than borrowing fields from another attempt. A provider-model provenance assertion occurs before durable returned content is available in the ordinary result row.

Mitigation: archive first, normalize second, validate third. Preserve original envelope alongside normalized fields; adapter failure must retain response and error stage. Test native and normalized response shapes, contentnull versus emptystring, reasoning-details and structured refusal fields. Reprocess archived responses at zero inference cost where justified.

### D. Credit positive is not a request-availability guarantee

The current billing gate tests account_remaining>0 and key_remaining>0 only. A subsequent402 can reflect a different limit, including in-flight reservation limits, while429 can be provider/model-specific. Concurrency1 reduces simultaneous reservation but does not guarantee token-rate compliance for large generations.

Mitigation: retain exact typed limit_source and Retry-After when supplied, distinguish key/account/in-flight/upstream constraints, estimate worst-case request affordability from verified prices and request bounds, and enforce model/provider pacing. Use a small canary within the authorized allowance and stop on repeated identical structural errors. Source: https://github.com/OpenRouterTeam/docs/blob/main/api_reference/errors-and-debugging.mdx .

### E. Repeated journal corruption is a primary engineering issue

The code appends a shared events.jsonl under the Drive-mounted output tree and uses process-localfsync. Multiple corruptions are observed; the exact mechanism (interruption, filesystem semantics, overlapping sessions or another cause) is not proven. Reconstructing a checkpoint makes data usable but does not remove this reliability hazard.

Mitigation: investigate writer/session ownership and corrupted byte boundaries before another broad run. Prefer small immutable per-attempt result files written/closed/hashed locally and then copied to the existing private Drive location with verified hashes and an explicit commit manifest. Keep metadata-only journal records referencing response artifacts rather than repeatedly embedding long reasoning. Preserve missing/uncommitted transfers as detectable states; local storage alone is not durable across runtime death. Do not assume rename/fsync behavior on a remote mount provides database transactions or cross-VM locking.

### F. Sequential numbering is not a repair strategy

Four repair rounds selected different state subsets. Some81pairs were excluded, some failed deterministically and some lack conclusive outcomes. More round numbers cannot establish a genuine chance or fix malformed metadata. Eligibility should be a reviewable request-specific manifest grounded in the corrected execution path and evidence, not the desire to reduce the failure count.

## Phase 2: Correct evidence capture and extraction (jupyter-notebook; local tests first)

Record response API surface, HTTP status, typed error code, response ID, finish/status/incomplete reason, content type/length, prompt/completion/reasoning tokens, requested limits, timing, resolved provider/model and rate-limit/retry headers where actually supplied. Keep non-sensitive metadata separately from private raw provider envelopes; never log keys or clinical payloads in console/public artifacts. Preserve a complete private response before parsing, subject to the existing privacy policy.

Fix field-level provenance: a missing metadata field may use CSV/usage JSON only if it is proven to describe the same returned response/attempt, with explicit source and consistency checks. Otherwise retain separate earlier/current observations. Distinguish reasoning-only content, missing answer, technical image error, refusal, nonempty unparsed answer and transport uncertainty. A parser correction may recover an existing valid answer without any API call; preserve original text and record recovery method/version. Do not fabricate an answer from reasoning.

## Phase 3: Route each pair to a defensible action

| Evidence | Planned action before any additional paid call |
|---|---|
| Valid answer present but extraction failed | Fix/test extraction; reprocess locally, zero inference. |
| HTTP429 | Concurrency1; honor recorded Retry-After and per-model/provider cooldown; inspect actual key/endpoint limits. No immediate retry loop. |
| Known quota/billing failure | Confirm current same-key credit and endpoint availability; log the check time/result. One scoped retry only after a valid budget gate. |
| Empty final answer at token cap | Confirm same-attempt finish/status and usage. If the original contract cannot yield an answer within its cap, record that outcome; investigate a separate recovery configuration rather than silently altering the benchmark. |
| Empty answer below cap | Inspect original envelope, API surface and refusal/incomplete indicators; validate extraction and endpoint behavior before retry. |
| Technical image-input error | Check local format/dimensions, exact original image hash and request encoding. Fix transport/encoding only if clinical pixels and frozen input identity are preserved. Otherwise require a separately documented input change. |
| Typed content-policy rejection | Retain as a refusal; no moderation evasion or automatic repeated request. |
| Unknown remote outcome | Look up retained response/generation ID through an authorized read-only provider mechanism if available. If still unknown, keep held; a deliberately authorized reissue must acknowledge possible prior completion/cost. |
| Exhausted pending or grant not dispatched | Reconcile the ledger. Do not infer either a missing call or a free attempt from the label. |

Before changing provider-specific request parameters, verify the current official endpoint documentation and its supported parameter combinations. The user explicitly forbids reasoning-level changes. Keep effort/visibility unchanged. Output cap also remains32768 in this release. Any later input/provider/output-cap change requires a separately documented configuration and user approval; reasoning-level reductions are excluded.

## Phase 4: Request-scoped bounded retry manifest

Prepare a reviewable manifest listing exact case/model pairs, last verified outcome, why a fresh request is appropriate, request hash, configuration identity, source evidence and one additional attempt bound. Include estimated upper spending bound and a hard cap; explicitly account for the observed variable token usage. Record unknown costs as unknown rather than assuming prior balance differences belong only to these requests.

After user approval of the concrete scope, implement a distinct durable authorization ID, independent of arbitrary historical round numbers. Atomically consume once at dispatch; interrupted dispatched requests become unknown/held, not automatically eligible again. Existing unused grants must be reconciled, not duplicated. Protect successful and flagged responses. Use concurrency1 and circuit-break repeated identical structural failures for review; stopping early must preserve unused authority without granting extras.

Begin with a small representative canary within the same per-pair allowance, not an additional hidden attempt. Verify transport and response-validation behavior, then continue only the eligible manifest entries. No global output/reasoning changes unless separately approved as a recovery configuration.

## Phase 5: Validate and publish

Tests must cover old and partial metadata, null versus zero, old CSV versus latest HTTP error, response API variants, reasoning-only and token-cap responses, typed image versus policy codes, archive replay, conflicting evidence, unused grants, interrupted starts, all eligibility buckets, saved-answer exclusion, spending/cooldown stops and zero calls on rerun. Verify that protected CSV fields and source hashes stay unchanged except explicitly accepted replacements.

Publish aligned Python and the canonical four-cell notebook through an immutable GitHub release. Browser actions only open/run/monitor committed code; no pasted code or manual Drive edits. Inspect runtime and active requests before changing releases. Verify actual dispatch and durable saves, then final backup and audit. Deliver before/after pair dispositions and response-validation counts with the evidence ledger. Do not claim that all81 succeeded, or that saved/accepted means clinically correct.

## Progress

2026-10-15 root: reviewed queue eligibility, evidence provenance and user audit. Wrote this plan only. Full current production ledger has not yet been acquired.

## Surprises & Discoveries

2026-10-15 root: some displayed failed states have journal attempts below an authorized limit, while their retained response metadata belongs to an earlier attempt. This needs sequence-level reconstruction, not an automatic repeat or a blanket exhausted label.

## Decision Log

2026-10-15 root: prioritize ledger and parser fixes before paid retries. Address safe transport/rate issues under original settings; isolate experimental changes to token/reasoning/input policy. Reasoning flags remain separate from unsuccessful answer pairs.

## Revision Notes

2026-10-15 root: initial plan, based on code and truncated user audit; classifications remain provisional pending complete private evidence.

## Outcomes & Retrospective

Implementation in progress; private capture, compact replay/recovery and audit review tested locally. 78 focused tests passed (12artifact,19recovery,10repairround,6evidence,10display,11surgical,10Responses). Broad collector23tests retain same4failures/4errors reproduced on exact parentd63fcab in a temporary snapshot. Notebook four cells compile. Publication and live audit acceptance pending. No paid requests or additional repair authorization created.

## Suggested Skills By Phase

Execplan: active for all phases. Jupyter-notebook: manual for canonical notebook changes in phase5. Computer-use: manual for committed notebook execution only. No subagents needed. Provider documentation lookup is required before proposing endpoint parameter changes.
