# Repair RadLE v2 Before Milestone 7

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md` and the applicable repo `AGENTS.md`. It is the blocking child plan for Milestone 6.5 of `Documents/execplan_radle_v2_incremental_model_admission.md`.

## Purpose / Big Picture

The existing incremental-admission implementation proves the intended transaction on synthetic data, but it cannot safely consume the frozen production RadLE v2 files. This repair makes the transaction production-compatible and independently auditable without admitting a real model, spending on judge calls, regenerating panels, or publishing data.

Success is observable when the exact frozen 200x291 wide master, 6000x20 final master, and 30-row blind-label map pass `check-base`; a production-shaped 200-case fixture passes prepare, mocked dual judging, radiologist overlay, finalization, commit, readback, and IDK0 generation; all negative tests pass; the runtime reconciliation is reviewed; and `review/pre_m7_production_repair_review.json` records an independent `pass`. Only then may the parent plan record `PRE_M7_REPAIR_RESULT=PASS` and resume at package inventory and sealing.

## Current State

Current state (2026-07-10 15:51 +05:30, Codex/GPT-5.6 Sol): the blocking pre-M7 repair gate is passed. The rerun reproduced `check-base`, `check-config`, `git diff --check`, the full 31-test suite, production-shape no-network acceptance, committed readback, both IDK0 readbacks, and compile checks; `review/pre_m7_production_repair_review.json` now records `verdict: pass`. Next: commit and push the repair branch, then resume the parent plan at Milestone 7 package inventory and sealing.

## Locked Facts

- The repair worktree is `C:/tmp/radle_v2_pre_m7_repair`; the source incremental worktree remains `C:/tmp/radle_v2_incremental_admission` and must stay unchanged.
- Durable ref `refs/codex-preserve/incremental-admission-77dbfb0` points to `77dbfb042f9ee58717204b28803a56a8b2509b56`.
- Primary preservation uses branch `codex/radle-v2-primary-preservation` and worktree `C:/tmp/radle_v2_primary_preservation`, based on `8c9de277631813172b391e685e772feccab9de28`.
- No real model admission, paid judge call, panel regeneration, or publication is permitted in Milestone 6.5.
- Incoming packages may be downloaded and sealed in parallel, but `prepare` must not consume them until this plan passes.
- The only appendable final-master schema has exactly 20 columns in this order: `run_id`, `Master_Case_ID`, `Associated_Images`, `model_blinded`, `candidate`, `provider`, `access`, `domain`, `Ground_Truth_Diagnosis`, `diagnosis`, `likert`, `response_valid`, `abstained`, `technical_failure`, `score_required`, `final_score_authoritative`, `final_score_source`, `weighted_score`, `rater_seniority`, `rater_seniority_rank`.
- The frozen production wide master is 200x291 with SHA256 `7D9CE5C66FBECB6FF9B72EDB6676CA8CE4F9E5E3DCAF621610437A703EFDE17F`.
- The frozen production final master is 6000x20 with SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`.
- The frozen blind-label map is 30x3 with SHA256 `09EBF4562EB541B59930930C70D5D6D1E3AF76373C49EA1F4F17C1AB471AB633`.
- Re-review receipt `review/pre_m7_production_repair_review.json` records `verdict: pass` for source/test patch SHA256 `85A1E889184B0B9F0A4F76E67DB4009E412214B6BC675A31BA50D7EE00835232`.
- Production-shape rerun root `C:/tmp/radle_pre_m7_recheck_20260710_155032` passed with finalization ID `0099659ca4b3c03f0bdbf9fe65a911959363073c9bd17093932cdd1ed09c8428`, 6200 output rows, 200 appended records, exact parent byte prefix, and zero network calls.
- New score sources are limited to `auto_score_not_required`, `canonical_exact`, `ai_judges`, and `radiologist`.
- IDK, technical failure, invalid Likert, nonintegral/out-of-range Likert including `8`, and every locked invalid terminal state score zero.
- Twelve human readers remain separate backend rows. `pooled12` and `split6x6` are presentation-only projections.

## Do Not Revisit

- Do not repair production compatibility by rewriting frozen parent rows or files. See Decision Log 2026-07-10, immutable parent.
- Do not keep the synthetic `model_key`, `reader_type`, `final_score`, or `terminal_state` columns in the appendable master. See Decision Log 2026-07-10, sidecar state.
- Do not derive reader type from a final-master column. Use the committed blind-label map. See Decision Log 2026-07-10, identity authority.
- Do not merge the preservation, runtime, statistics, or final-scoring branches wholesale. See Decision Log 2026-07-10, path-scoped consolidation.
- Do not exercise real OpenRouter transport in this milestone. The real path is tested only with a mocked transport. See Decision Log 2026-07-10, no-spend gate.

## Progress

- [x] (2026-07-10 10:27 +05:30, Codex/GPT-5.6 Sol) Re-read the ExecPlan rules, confirmed no interrupted repair work existed, and verified the incremental source branch remains clean at `77dbfb0`.
- [x] (2026-07-10 10:27 +05:30, Codex/GPT-5.6 Sol) Created durable ref `refs/codex-preserve/incremental-admission-77dbfb0` and isolated repair/preservation worktrees.
- [x] (2026-07-10 10:50 +05:30, Codex/GPT-5.6 Sol) Preserved 82 dirty-primary working paths in three path-scoped commits, recorded both staged and working hashes for five `AM` files, restored the excluded Opus notebook, and recorded `0931b0c`/`071d6ec` in the ledger.
- [x] (2026-07-10 11:10 +05:30, Codex/GPT-5.6 Sol) Added platform-safe CSV field sizing and production `check-base`; the real frozen 200x291, 6000x20, and 30x3 authorities pass with the locked hashes, 263 images, and case fingerprint.
- [x] (2026-07-10 11:32 +05:30, Codex/GPT-5.6 Sol) Replaced invented master fields with the exact 20-column schema and added the exact adjudication-state sidecar.
- [x] (2026-07-10 11:55 +05:30, Codex/GPT-5.6 Sol) Hardened package validation, content-only identities, parent-chain checks, phase audits, idempotent replay checks, checksums, and exact append bytes.
- [x] (2026-07-10 11:58 +05:30, Codex/GPT-5.6 Sol with Worker/Dirac) Implemented authorization-gated real OpenRouter judging with injected mocked transport, append-only cache, zero-network default, and agreement rederivation.
- [x] (2026-07-10 11:25 +05:30, Codex/GPT-5.6 Sol with Worker/Euler) Reconciled benchmark blob `85278e2`, medical blob `5b013be`, Meta blob `511eaf`, chat template, notebooks, and 13 runtime regression tests with `review/runtime_reconciliation_review.json`.
- [x] (2026-07-10 12:08 +05:30, Codex/GPT-5.6 Sol) Passed the 200-case production-shape acceptance flow: 6200x20 child master, exact parent byte prefix, 200 appended records, 12 human backend readers, active/excluded model counts 15/4, and zero network calls.
- [x] (2026-07-10 15:51 +05:30, Codex/GPT-5.6 Sol) Re-ran independent read-only review gates, verified both prior blocking findings fail closed, recorded `review/pre_m7_production_repair_review.json` with `verdict: pass`, and set the parent gate result to `PRE_M7_REPAIR_RESULT=PASS`.

## Surprises & Discoveries

- Observation: Python's default CSV field limit prevents reading the actual wide master because raw-response cells exceed 131,072 bytes.
  Evidence: production read raised `_csv.Error: field larger than field limit (131072)` in `read_csv_table`.
  Date/Author: 2026-07-10, audit supplied by user and accepted by Codex/GPT-5.6 Sol.

- Observation: the synthetic fixture and adapter use fields that do not exist in the production master, so prior Milestones 3-6 demonstrate architecture only, not production compatibility.
  Evidence: fixture fields include `model_key`, `reader_type`, `final_score`, and `terminal_state`; the frozen production schema uses `candidate`, response flags, and `final_score_authoritative`.
  Date/Author: 2026-07-10, audit supplied by user and accepted by Codex/GPT-5.6 Sol.

- Observation: useful primary-only panel work has newer unstaged content over staged versions in five `AM` files.
  Evidence: the preservation audit reported 1,294 insertions and 201 deletions beyond the staged copies.
  Date/Author: 2026-07-10, audit supplied by user and accepted by Codex/GPT-5.6 Sol.

- Observation: Windows checkout line endings changed the raw judge-prompt and JSON hashes even though their effective content was unchanged.
  Evidence: raw prompt SHA was `BE04121A...A3033`; canonical LF SHA is the locked `545989BB...458CE`. Canonical text hashing and `.gitattributes` now make the effective request identity stable.
  Date/Author: 2026-07-10, Codex/GPT-5.6 Sol.

- Observation: nesting both the intake ID and finalization ID exceeded legacy Windows path limits while copying evidence.
  Evidence: `shutil.copytree` failed under `<intake_id>/finalized/<finalization_id>/intake_snapshot`; finalizations now use the sibling path `admissions/finalized/<finalization_id>` and the same flow passes.
  Date/Author: 2026-07-10, Codex/GPT-5.6 Sol.

## Decision Log

- Decision: immutable parent. Validate frozen authorities, append exactly 200 records in the parent's header order, and require the child master to begin with the exact parent bytes.
  Rationale: unchanged hashes and byte-prefix identity are stronger and easier to audit than row-level assurances alone.
  Date/Author: 2026-07-10, user-approved plan; recorded by Codex/GPT-5.6 Sol.

- Decision: sidecar state. Keep `new_model_long_delta.csv` and `scored_append_delta.csv` in the exact 20-column master schema; store terminal and routing state in `adjudication_state.csv` keyed by `(Master_Case_ID, model_blinded)`.
  Rationale: scoring workflow metadata must not contaminate the appendable production contract.
  Date/Author: 2026-07-10, user-approved plan; recorded by Codex/GPT-5.6 Sol.

- Decision: identity authority. `candidate` identifies model rows; the roster supplies provider/access/domain; the blind-label map distinguishes model and human readers and supplies human identity.
  Rationale: the production master has no `reader_type` field and historical rows remain immutable.
  Date/Author: 2026-07-10, user-approved plan; recorded by Codex/GPT-5.6 Sol.

- Decision: content-only transaction IDs. Paths are provenance only. Intake and finalization identities must include every content artifact that can determine routing or scores.
  Rationale: moving an identical package must not change identity, while changing any score-determining evidence must.
  Date/Author: 2026-07-10, user-approved plan; recorded by Codex/GPT-5.6 Sol.

- Decision: path-scoped consolidation. Preserve primary work in separate commits, restore the historical Opus notebook as excluded evidence, record commits `0931b0c` and `071d6ec`, and selectively import only reviewed files.
  Rationale: adjacent branches contain useful files mixed with stale or regressive whole-file versions.
  Date/Author: 2026-07-10, user-approved plan; recorded by Codex/GPT-5.6 Sol.

- Decision: no-spend gate. Default judge mode is dry-run. Real mode requires exact unexpired authorization and `OPENROUTER_API_KEY`; pre-M7 tests inject a mock transport and make no network request.
  Rationale: the implementation must be testable without interpreting test success as spend approval.
  Date/Author: 2026-07-10, user-approved plan; recorded by Codex/GPT-5.6 Sol.

## Revision Notes

- v2 (2026-07-10 12:11 +05:30, Codex/GPT-5.6 Sol): recorded completed implementation and local acceptance; left the production gate pending independent review.
- v3 (2026-07-10 15:51 +05:30, Codex/GPT-5.6 Sol): recorded the bounded re-review pass, the 31-test rerun, the production-shape acceptance rerun, and the `PRE_M7_REPAIR_RESULT=PASS` gate transition.

## Outcomes & Retrospective

Final repair outcome (2026-07-10 15:51 +05:30, Codex/GPT-5.6 Sol): real `check-base` passes all three frozen hashes before and after the rerun; 31 unit/integration/runtime/judge tests pass, including committed-parent chain replay and the two prior blocker regressions; the production-shape acceptance receipt reports zero network calls, exact parent byte prefix, 200 appended records, 6200 output rows, score-source counts `191/5/1/3` for AI/automatic-zero/canonical/radiologist, and IDK0 counts of 19 complete models, 15 active, 4 excluded, and 12 human backend readers. The child gate is PASS and no reusable lesson has been promoted to a skill.

## Suggested Skills By Phase

- Planning and living-plan maintenance: `execplan`, manual. Keep this child and the parent synchronized at every gate transition.
- Preservation and production-schema implementation: none. Use repository-native Git, Python, and test tooling.
- Independent data and transaction validation: `data-analytics:validate-data`, auto-suggest if available; the repository's read-only audit remains authoritative.
- Runtime reconciliation: none. Use AST, compile, JSON, route, parser, and blob-diff receipts.
- Panel regeneration: intentionally out of scope; `svg-panel-qa` is deferred until a later milestone.

## Execution Posture

All repair changes are made in `C:/tmp/radle_v2_pre_m7_repair` on `codex/radle-v2-pre-m7-repair`. Dirty-primary preservation is made in `C:/tmp/radle_v2_primary_preservation` on `codex/radle-v2-primary-preservation`. The primary checkout is a read-only copy source. The source incremental and unified runtime worktrees remain unchanged.

No branch is pushed until its path-scoped diff and generated review receipt pass. No whole-branch merge is allowed. Git commits are checkpoints after preservation, core compatibility, transaction/judge integrity, runtime reconciliation, and final gate review.

## Milestones

### Milestone 6.5A: Preserve useful work before repair

Create a preservation manifest for each copied primary path with working SHA256, staged Git blob when present, source branch, and classification. For every `AM` file, record both staged and working identities. Copy final working versions, not index versions. Exclude `.claude/settings.local.json` and stale primary copies of the incremental plan, benchmark runtime, and Meta helper.

Commit panel core/assets, panel experiments/docs, and runtime/document changes separately. Restore blob `4295ae9dc8f97595b791f2063e6da89b17405bb6` under `notebooks/archive/replaced_models/` with an excluded historical README. Record selective-source commits `0931b0c` and `071d6ec` in the ledger. Verify every manifest hash against the preservation worktree.

### Milestone 6.5B: Make production authorities readable and enforceable

Add a reusable CSV field-size helper that attempts `csv.field_size_limit(2147483647)` and backs off safely on smaller platforms. Invoke it before every `csv` read.

Add CLI command `check-base`. It must validate configured paths, SHA256 values, exact row and column counts, exact 20-column final schema, case fingerprint, wide/final/blind case and label reconciliation, and the first-admission requirement. For chained admissions, validate parent `COMMITTED.json`, `append_manifest.json`, `SHA256SUMS`, roster/blind-map hashes, and parent-chain identity.

### Milestone 6.5C: Repair schema and scoring state

Replace the fixture and adapter's invented fields with the exact 20-column production schema. The prepared delta has all non-score fields populated; `final_score_authoritative` and `final_score_source` are blank before adjudication. Add `adjudication_state.csv` with key fields followed by `candidate`, `terminal_state`, `normalized_ground_truth`, `normalized_diagnosis`, `package_failure`, `source_row_sha256`, `automatic_score`, `requires_judge`, and `requires_radiologist`.

Finalization joins this state sidecar with automatic, judge, and radiologist evidence and emits the exact 20-column scored delta. The emitted master has the exact parent bytes as its prefix and exactly 200 appended parsed records in parent header order.

### Milestone 6.5D: Harden transaction and judge integrity

Verify incoming `SHA256SUMS`, source manifest, final-wide hash, runtime SHA/run label, `TEST_LIMIT=None`, routing/provider/returned-model fields, promotion audit, repair evidence, and zero unresolved cells before computing `intake_id`.

Make `intake_id` content-only over parent authorities, projected input, package manifest, requirements, ground truth, roster, terminal policy, and normalizer code. Make `finalization_id` cover every score-determining artifact including judge config/prompt/results/index, authorization, queue, radiologist overlay, scored delta, roster/blind map, and finalizer code.

Each audit phase independently recomputes hashes, classifications, counts, queue routing, judge locks, parent prefix/key order, append bytes, and checksum inventory. Existing roots may return `already_prepared`, `already_finalized`, or `ALREADY_ADMITTED` only after the full phase audit passes.

Implement real OpenRouter judging behind `paid_judge_authorization.json`. Validate exact intake, judge IDs, prompt/config/worklist hashes, HTTP ceiling, optional cost ceiling, approver, approval time, and expiry. Cache append-only entries keyed by requested and returned model, exact payload, policy/config, case fingerprint, and input hashes. Require two distinct configured judges, parsed equal binary verdicts, no review flag, and matching evidence hashes for agreement.

### Milestone 6.5E: Reconcile runtime generations

Three-way reconcile `src/radle_benchmark.py` from base blob `6b6cc03`, unified runtime blob `85278e2`, and incremental blob `b8e0bbe`. Preserve the unified roster and `<think>`, VQA, abstention, and conservative prose parsing while retaining GPT-5.6/Grok-4.5 routing and Meta plumbing.

Import medical-runtime blob `5b013be` and its chat template. Retain Meta helper blob `511eaf` and the matching append/Meta notebooks. Run compile, AST, notebook JSON, registry, provider-route, and parser regressions. Store a reviewed diff receipt. Never overwrite the whole file from a branch without the hunk review.

### Milestone 6.5F: Prove the gate

Generate an exact 200-case production-shape fixture including a raw-response field larger than 131,072 bytes. Exercise prepare, mocked judging, radiologist overlay, finalization, commit, readback, and IDK0 generation. Test authority mismatch, package tamper, routing mismatch, unresolved repair, path-independent identity, prepared-artifact tamper, forged agreement, incomplete radiologist decisions, roster/blind-map changes, and same-key/different-content replay.

Run `check-base` against the real frozen files and re-hash them after all tests. Require `git diff --check`, compile/config/unit/integration tests, a clean repair worktree after commit, preservation-manifest verification, and remote refs. An independent read-only reviewer writes `review/pre_m7_production_repair_review.json` with `verdict: pass` only if every gate is reproduced.

## Validation And Acceptance

The final command set must include these observable gates:

    py -3.11 scripts/radle_v2_incremental_admission.py check-base --base-authority config/radle_v2_base_authority.json
    py -3.11 -m unittest discover -s tests -p "test_radle_incremental*.py" -v
    py -3.11 -m py_compile src/radle_incremental_admission.py src/radle_benchmark.py src/radle_medical_custom_runtime.py src/radle_meta_model_api_runtime.py
    py -3.11 scripts/audit_radle_v2_incremental_admission.py --phase committed --root <fixture-committed-root> --no-write
    py -3.11 scripts/audit_radle_v2_incremental_admission.py --phase idk0-lane --root <fixture-lane-root> --no-write
    git diff --check

Passing means: real frozen authorities retain their exact hashes; all tests pass without a network call; the fixture child master starts with exact parent bytes and adds 200 records; every generated inventory and evidence identity is independently recomputed; runtime receipts pass; preservation manifest verification passes; and the independent review JSON says `pass`.

## Idempotence And Recovery

Generated roots are content-addressed and non-overwriting. A repeat with identical content returns the existing identity only after a full audit. A repeated logical key with different content fails. If an audit fails, leave the root untouched as evidence and use a new root after fixing the cause.

The source incremental ref and preservation branch make recovery non-destructive. Never reset the dirty primary checkout. Restore an individual preserved file by its manifest hash and commit, not by merging the preservation branch wholesale.

## Gate Result

`PRE_M7_REPAIR_RESULT=PASS`

Milestone 7 may proceed to inventory and seal the already downloaded package source. Real `prepare` must still wait for one-model package projection, source seal validation, parent-chain validation, and the no-paid-judge authorization rule.
