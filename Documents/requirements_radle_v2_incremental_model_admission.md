# RadLE v2 Incremental Model Admission Requirements

This document distills `Documents/radle_v2_incremental_model_pipeline_requirements_study.md` into implementation requirements for the next ExecPlan. It is requirements-only: do not treat it as the implementation plan and do not edit source or generated pipeline outputs merely because this file exists.

## Objective

RadLE v2 needs a repeatable path for adding new model arms, beginning with Grok 4.5 and GPT-5.6 Sol Pro, without changing already-finalized model or human rows. A new model should enter through Morning or another approved runtime, be promoted into a sealed one-model package, be scored through the same deterministic/judge/radiologist policy, then produce a new complete final-long-master sibling and refreshed IDK0 Score1000/Score2000 panel inputs.

The adapter from "new model columns" to "scored long master" must be boring, auditable, and append-only.

## Locked Decisions

- Storage is append-only within RadLE v2. Existing finalized model and human rows, columns, values, and scores do not change.
- Grok 4.5 replaces the previous/current active Grok arm for active comparison after admission. The older Grok rows remain retained-but-excluded.
- GPT-5.6 Sol Pro replaces the previous/current active GPT arm for active comparison after admission. The older GPT rows remain retained-but-excluded.
- Muse Spark is intended to be added as an active contender after full 200-case admission.
- The complete master can grow while the active comparator roster stays the same size when a new model replaces an older active arm. The active roster increases by one after Muse Spark is admitted as an additional contender.
- New models enter through Morning or another approved runtime, not by direct IDK0 or long-master CSV surgery.
- Each model arm is one reader over 200 cases, effective `N = 200`.
- Human rows stay individual in the backend. Pooled 12-reader or split 6+6 presentation is a downstream configuration.
- IDK0 is final: exact IDK, approved typo-IDK, invalid response, invalid Likert, technical failure, and retry-exhausted failure score zero.
- Likert values outside 0 through 4, including observed value `8`, are invalid-zero terminal states. They require explicit provenance and must not be silently coerced.
- Score1000 is the signed sum of `Likert + 1`, positive when correct and negative when wrong, with human projection weights applied only in presentation/summary lanes.
- Score2000 is `Score1000 + 1000` for 200-case RadLE v2. It is display math and must not change rank or state.
- Humans remain visually first/left in panels. Models are ordered by Score2000 within the active model set.
- Axis kink/compression is display-only.
- Use three adjudication tiers: deterministic accepted match, blinded dual LLM judging, and radiologist review.
- Judge models should match the previous successful dual-judge workflow unless the user explicitly changes them.
- Full dual judging is approved for rows that need judging.
- Radiologist review receives only unresolved rows.
- Radiologist queue fields are intentionally minimal: case number, blind candidate code, ground truth, candidate diagnosis, and Likert.
- Canonical normalized exact diagnosis matches auto-score correct without LLM judging.
- Judges may see ground truth and approved variants/context for non-exact rows, but never model identity.
- Public-release candidate generation may happen after private admission, but publication requires separate recorded privacy approval.

## Roster Requirements

The implementation must create a roster manifest that separates these statuses:

- `complete_master_active`: model is in the complete master and active comparator set.
- `complete_master_excluded`: model is retained in files but excluded from active comparison.
- `pending_admission`: model has runtime work or Drive files pending validation.
- `rejected_or_incomplete`: model exists as an experiment but is not roster-ready.

Current active pre-append comparator arms are the 15-model set from the study ledger. Current retained-but-excluded arms are `claude_4_8_opus`, `grok_4_20`, and `glm_4_6v`. After Grok 4.5 admission, the old active Grok arm moves to `complete_master_excluded`. After GPT-5.6 admission, the old active GPT arm moves to `complete_master_excluded`.

Keep exclusion simple: old active Grok/GPT arms become `complete_master_excluded` without replacement-reason machinery unless the user asks for it later.

Meta Muse Spark is pending and should become `complete_master_active` after it passes admission. It does not replace an existing arm.

## Incoming Package Requirements

Each incoming private package must represent exactly one model family and exactly 200 RadLE v2 cases.

Required case keys:

    Master_Case_ID
    Associated_Images
    Image_SHA256

Required per-model columns for model key `{k}`:

    Diagnosis_{k}
    Likert_{k}
    Prompt_Tokens_{k}
    Total_Tokens_Out_{k}
    Reasoning_Tokens_{k}
    Latency_{k}
    Provider_{k}
    Timestamp_UTC_{k}
    Reasoning_{k}
    Reasoning_Raw_{k}
    Reasoning_Details_{k}
    Actual_Request_Extra_{k}
    Grok_Fallback_Used_{k}
    OpenRouter_Response_Model_{k}
    Usage_JSON_{k}
    Raw_Response_{k}

A one-model final-wide CSV has 19 columns. It must contain no historical model families. If Grok/GPT were run into a shared `Runs/radle_v2` wide file, project that file into independent one-model packages before admission.

## Admission Gates

Private admission must fail unless all gates pass:

- Branch and full commit SHA are recorded.
- Run is full 200-case, not smoke, and `TEST_LIMIT = None`.
- Final manifest hash matches the promoted final-wide CSV.
- Case IDs are exactly 1 through 200, unique and nonblank.
- `Associated_Images` and `Image_SHA256` match the frozen RadLE v2 case fingerprint.
- Exactly one complete model family is present.
- Every row has an accepted terminal state: valid committed diagnosis, canonical IDK, or explicit invalid-zero/failure state with provenance.
- Invalid-zero/failure states do not block admission if every such row has explicit terminal provenance.
- Provider routing and returned model IDs match model-specific rules.
- Scorer output is regenerated from promoted final, not trusted from a stale incoming scorer.
- Existing base columns and values remain identical and ordered.
- Same model key with different content is a hard collision; replacement requires a separate approved supersession transaction, not overwrite.

## Scoring And Adjudication Requirements

Only new model rows are scored. Existing finalized rows are carried forward byte-for-byte except for materialized-file placement in the new sibling master.

The scoring path must produce:

- a 200-row new-model long delta before adjudication;
- deterministic accepted exact/canonical matches;
- judge worklist for rows needing LLM equivalence judging;
- full dual-judge evidence sidecars;
- radiologist queue for unresolved, discordant, conflict, or mandatory-review rows, with only case number, blind code, ground truth, candidate diagnosis, and Likert;
- a 200-row scored append delta;
- a new complete final-long-master sibling with old rows unchanged plus the scored delta;
- a manifest proving old-row immutability, delta hashes, score-source counts, terminal-state counts, and roster status.

Ground-truth variants may be supplied to the scorer/judge. They must never be supplied to the candidate model. Imported prior evidence from the previous RadLE version is judge context only unless a later calibrated policy promotes it.

Case 164 remains quarantined for deterministic variant reuse because current v2-reviewed evidence has a conflict. It can still be judged or radiologist-reviewed normally for new rows.

Blind labels use a stable global map. New models receive the next unused `Candidate <letter>` label rather than a fresh per-batch label map.

## False-Accept Policy

"False accept" means the automation marks a model answer correct when it should be wrong. The project should treat false accepts as worse than false rejects because they can inflate model performance.

Current requirement: broad semantic auto-acceptance is disabled. Canonical exact matches may auto-accept after normalizer validation. Non-exact semantic matches go through dual judging and radiologist review as needed. A future deterministic variant tier needs a calibration release with zero observed false accepts and a predefined upper confidence bound before activation.

## Score1000, IDK0, And Panel Requirements

Downstream counts must be derived from manifests, not hard-coded historical counts.

For RadLE v2:

- Complete master rows are `200 * (model_arms_in_complete_master + 12 human_readers)`.
- Active Score1000 rows are `200 * (active_model_arms + 12 human_readers)`.
- If Grok 4.5 replaces an older Grok arm, active model count may stay unchanged even though complete-master rows grow.
- Same for GPT-5.6 replacing the older GPT arm.
- After Grok/GPT replacement plus Muse Spark admission, active model count increases by one because Muse is an additional contender.
- Correctness totals are `parent_total + appended_delta_total`, not fixed historical constants.
- Human pooled and split views are projections from the same individual human rows.
- Score2000 is display-only and must be generated from Score1000.
- The active handwritten path is the IDK0 Score1000 Panel 2/3 wrapper lane, not the older confidence-summary generator.
- Public candidate CSV/table ordering is humans first, active models by Score2000, then excluded models with `excluded = true`.
- Panels include active contenders only.

Panel registries for display name, category, logo, color, selected membership, and label wrapping remain explicit configuration. Missing required logo assets should fail loudly.

## Required Artifacts

Each admitted model should leave these artifacts or their explicit equivalent:

- `append_input_manifest.json`
- `new_model_long_delta.csv`
- `accepted_variants_snapshot.csv`
- `judge_worklist.csv`
- judge evidence sidecars
- `radiologist_queue.csv`
- `scored_append_delta.csv`
- new `radle_v2_final_long_master.csv`
- `append_manifest.json`
- new dated IDK0 Score1000/Score2000 lane
- panel-ready summaries and figure QA outputs when panels are generated

Private artifacts must retain enough information to audit diagnosis text, raw responses, request extras, repairs, and score sources. Public artifacts must exclude diagnosis text, reasoning, raw responses, image names/hashes, private paths, and raw provider errors.

Public candidate files should include all complete-master models, including excluded old arms, with a simple `excluded` flag.

## Implementation ExecPlan Requirements

The implementation ExecPlan should be created from this requirements file plus the full study ledger. It should include milestones for:

1. Protecting the dirty primary checkout and creating a clean integration base.
2. Preserving or integrating the unified Morning runtime head for Grok/GPT/Meta.
3. Building the roster manifest and one-model private package contract.
4. Implementing final-wide-to-new-model-long-delta conversion.
5. Implementing terminal-state classification, including invalid-zero Likert handling.
6. Implementing isolated dual-judge/radiologist scoring for new rows only.
7. Materializing the new complete final-long-master sibling with old-row immutability proof.
8. Making Score1000/IDK0/panel counts manifest-derived.
9. Running Grok 4.5 as the first vertical slice.
10. Replaying the same transaction for GPT-5.6, then Meta Muse Spark after full package validation.

## Open Items Before Code Execution

- Download and hash the new Drive packages when available.
- Snapshot current branch SHAs again before integrating runtime work.
- Identify the exact previous judge model IDs/config from the existing successful dual-judge workflow.
- Clinically resolve case 164 before using it for deterministic variant automation.

## Safe Work Before Results Arrive

These tasks can proceed before Grok/GPT/Muse result packages are downloaded:

- draft the implementation ExecPlan from this requirements file and the study ledger;
- implement schema and manifest validators against synthetic one-model fixtures;
- prepare roster configuration with simple active/excluded flags;
- identify the exact previous dual-judge model settings;
- implement dry-run/idempotence checks for one-model admission;
- add tests proving old rows remain unchanged and active panels exclude excluded models.

Actual admission, scoring, public candidate generation, and panel regeneration must wait for downloaded package paths and hashes.
