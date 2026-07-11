# Build the RadLE v2 Incremental Model Admission Pipeline

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md` and the applicable repo `AGENTS.md` instruction to keep serious plans under `Documents/`.

This draft is deliberately written for a fresh `gpt-5.4-mini` executor. The executor must complete one milestone at a time, run every stated gate, record literal evidence in this file, and stop on any failed invariant. It must not infer permission to overwrite, rescore old rows, publish private data, spend on judge calls without the explicit command token, or resolve clinical uncertainty.

Recommended execution profile: `gpt-5.4-mini` with `xhigh` reasoning, one milestone per turn. At the start of every turn, read `Current State`, the active milestone, `Locked Facts`, and `Do Not Revisit`; at the end, update this plan before yielding. Never skip forward because an external file is unavailable.

## Purpose / Big Picture

RadLE v2 needs a repeatable transaction for adding a new 200-case model arm without changing any already-finalized model or human row. After this work, an operator can take one promoted Morning or approved-runtime final-wide package, validate and seal it, create only that model's 200-row scoring delta, adjudicate only unresolved new rows, append the scored delta to a new sibling final long master, and regenerate the IDK0 Score1000/Score2000 and panel inputs from manifest-derived counts.

The first vertical slice is `grok_4_5`. The same command sequence is then replayed for `gpt_5_6_sol_pro` and `muse_spark_1_1`. Grok 4.5 and GPT-5.6 replace older active comparator arms only in roster selection; all old rows remain in the complete master with `excluded = true`. Muse Spark adds one active comparator.

Success is observable when each committed admission has a sealed input manifest, a 200-row scored delta, a new final-long-master sibling whose old bytes and old keys are unchanged, an append manifest with passing gates, and a downstream IDK0 lane whose counts follow the active roster rather than historical constants.

## Current State

Current state (2026-07-11 01:06 +05:30, Codex/GPT-5.6 Sol): Candidate AE / `grok_4_5` has been finalized, committed, and read back successfully from finalization `d5e05eb280504f189090fa9936ed2294c1e46303e81a457b7197945e1e360e53`. Candidate AF / `gpt_5_6_sol_pro` has been finalized, committed, and read back successfully from sequential finalization `658f6f2548994a62251f7e8eadcbf3e8fc51bcbbe5b37992edbde2de03626b4a`, using the committed Grok parent. Candidate AG / high-effort `muse_spark_1_1` has been finalized as a user-authorized evidence-carry-forward admission: the completed Grok-parent Muse adjudication evidence was first validated as conventional finalization `7403d14f317b2e6db8a8151afb63ad5bf1592c302e1b4bbd75d3ce6da6c477ee`, then its audited scored delta was appended to the committed GPT parent and committed/read back from finalization `18e1d292e1fe1f8d654be09aa2f65f65c6cc951be4b5d37d3c6649645e127df4`. The private final master now has 6600 rows: the frozen 6000-row parent, plus 200 Grok, 200 GPT, and 200 Muse rows. The `Repeatable Admission SOP` below is now the operating entry point for future models and versions. Next: build/audit the active IDK0 Score1000/Score2000 lane and regenerate candidate-public/panel artifacts only after the separate privacy/publication approval gate.

## Repeatable Admission SOP

This section is the short operating manual for admitting every future model version. A fresh agent should start here, then use `Locked Facts`, `Do Not Revisit`, and the active milestone for the current concrete paths. Do not use old chat memory, copied shell history, or a previous staging root as authority when this SOP and the current committed root disagree.

### Bind These Inputs First

Before any command, write the actual values into the working notes for the run:

- `ModelKey`: the roster model key to admit, for example `grok_4_5`, `gpt_5_6_sol_pro`, or `muse_spark_1_1`.
- `SourceModelKey`: only when a shared/source CSV uses a temporary family name that must project into `ModelKey`, for example `muse_spark_1_1_high` into `muse_spark_1_1`; otherwise omit it.
- `ParentCommittedRoot`: the latest committed parent root containing `COMMITTED.json`, `SHA256SUMS`, `append_manifest.json`, and `final/radle_v2_final_long_master.csv`.
- `ParentWide`: the current complete wide results CSV that matches the parent.
- `ParentAuthorityManifest`: the frozen parent authority manifest for the parent chain.
- `BlindMap`: the stable blinding map that allocates the next unused candidate label.
- `SourceWide`: the downloaded full-run source wide CSV or already projected one-model package source.
- `RuntimeSha`: the full runtime commit SHA. Use `--runtime-sha-status inferred` only when the manifest records why a direct checkout SHA is unavailable.
- `PackageRoot`, `AdmissionOutputRoot`, `RadiologistOutputRoot`, and `Idk0LaneRoot`: new dated, non-empty-safe roots for this run. Do not reuse an existing output root for a new input hash.
- `ReviewerPseudonym`, `ReviewedUtc`, and optional `RationalePrefix`: required when splitting radiologist handback rows.
- `JudgeAuthorization`: a real `paid_judge_authorization.json` path. Paid LLM judging is blocked without this explicit file.

### Normal Sequential Admission Path

Use this path for ordinary model N, including model replacements. One transaction admits exactly one model arm and appends exactly 200 rows.

1. Validate repo/config readiness.

       py -3.11 scripts/radle_v2_incremental_admission.py check-config
       py -3.11 scripts/radle_v2_incremental_admission.py check-base

   Expected: both commands print `PASS` states. Any config/hash failure blocks admission.

2. Project a shared wide source into a one-model package when needed.

       py -3.11 scripts/radle_v2_incremental_admission.py project-one-model --source-wide $SourceWide --model-key $ModelKey --output-package $PackageRoot --runtime-sha $RuntimeSha

   If the raw source family differs from the admitted identity, add:

       --source-model-key $SourceModelKey

   If runtime SHA is inferred, add:

       --runtime-sha-status inferred --runtime-sha-note "<short evidence note>"

   Expected: the package has one model family, exactly 200 rows, source-cell equality proof, `source_manifest.json`, and `SHA256SUMS`.

3. Prepare against the latest committed parent, first as dry run and then for real.

       py -3.11 scripts/radle_v2_incremental_admission.py prepare --parent-wide $ParentWide --parent-final-long-master "$ParentCommittedRoot/final/radle_v2_final_long_master.csv" --parent-authority-manifest $ParentAuthorityManifest --blind-map $BlindMap --incoming-package $PackageRoot --model-key $ModelKey --roster config/radle_v2_model_roster.json --variants config/radle_v2_base_authority.json --states config/radle_v2_terminal_states.json --output-root $AdmissionOutputRoot --dry-run
       py -3.11 scripts/radle_v2_incremental_admission.py prepare --parent-wide $ParentWide --parent-final-long-master "$ParentCommittedRoot/final/radle_v2_final_long_master.csv" --parent-authority-manifest $ParentAuthorityManifest --blind-map $BlindMap --incoming-package $PackageRoot --model-key $ModelKey --roster config/radle_v2_model_roster.json --variants config/radle_v2_base_authority.json --states config/radle_v2_terminal_states.json --output-root $AdmissionOutputRoot

   Expected: the real run emits one staging/intake root. Record the intake ID, root path, row counts, terminal-state counts, and package/source hashes in this plan.

4. Audit the prepared root.

       py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $StagingRoot --phase prepared --no-write

   Expected: `RESULT=PASS`. A prepared root is not final and is not a parent for any later model.

5. Run the dual-judge dry run, then paid judging only after explicit authorization.

       py -3.11 scripts/radle_v2_dual_judge_delta.py --staging-root $StagingRoot --config config/radle_v2_judges.json --dry-run
       py -3.11 scripts/radle_v2_dual_judge_delta.py --staging-root $StagingRoot --config config/radle_v2_judges.json --authorization $JudgeAuthorization --real
       py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $StagingRoot --phase judge --no-write

   Expected: the dry run records call ceilings; the real run records HTTP request count, cost, judge cache/result hashes, locked rows, and radiologist queue rows; the judge audit prints `RESULT=PASS`.

6. Resolve radiologist rows.

   If `radiologist_queue.csv` has rows, send only the current queue rows for review and ingest one combined handback CSV/XLSX with binary `human_score`. Convert XLSX to CSV if needed, then split:

       py -3.11 scripts/radle_v2_incremental_admission.py split-radiologist-scores --combined-scores $CombinedScoresCsv --staging-root $StagingRoot --output-root $RadiologistOutputRoot --reviewer-pseudonym $ReviewerPseudonym --reviewed-utc $ReviewedUtc

   Expected: every expected `(Master_Case_ID, model_blinded)` is present exactly once; optional `Ground_Truth_Diagnosis`, `diagnosis`, and numeric-equivalent `likert` evidence matches the queue; each per-model `radiologist_decisions.csv` has the exact overlay schema. If the queue is empty, use the header-only `NONE` overlay generated with the staging evidence.

7. Finalize and audit before commitment.

       py -3.11 scripts/radle_v2_incremental_admission.py finalize-stage --intake-root $StagingRoot --radiologist-decisions $RadiologistDecisionsCsv
       py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $FinalStagingRoot --phase precommit --no-write

   Expected: `scored_append_delta.csv` has exactly 200 rows, old parent bytes are preserved as prefix, `append_manifest.json` records every source/evidence hash, and precommit audit prints `RESULT=PASS`.

8. Commit and read back.

       py -3.11 scripts/radle_v2_incremental_admission.py commit --final-staging-root $FinalStagingRoot
       py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $CommittedRoot --phase committed-readback --no-write

   Expected: `COMMITTED.json` is written last with transaction state `FINAL_MASTER_COMMITTED`; `SHA256SUMS` verifies; committed-readback prints `RESULT=PASS`. Only after this point can this root become `ParentCommittedRoot` for the next model.

9. Build the downstream IDK0/Score1000/Score2000 lane from the committed root.

       py -3.11 scripts/radle_v2_incremental_admission.py build-idk0-lane --committed-root $CommittedRoot --output-root $Idk0LaneRoot --human-presentation pooled12 --roster config/radle_v2_model_roster.json --states config/radle_v2_terminal_states.json
       py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $Idk0LaneRoot --phase idk0-lane --no-write

   Expected: `score_rows.csv`, `source1000.csv`, `public_candidate_summary.csv`, `panel_order.csv`, `group_summary.csv`, `panel_bins.csv`, and `score_lane_manifest.json` are derived from the committed master and roster. Counts must come from the manifest, not historical constants.

10. Update this ExecPlan before yielding.

    Record the committed root, parent root, finalization ID, final master row count and SHA256, append manifest SHA256, `COMMITTED.json` state/hash, score-source counts, judge/radiologist counts, IDK0 lane root/hash, and the next action. Add or reconcile `Locked Facts`, `Do Not Revisit`, `Progress`, `Decision Log`, `Revision Notes`, and `Outcomes & Retrospective` as needed.

### Batch Radiologist Handback Path

When multiple models have open radiologist queues, it is acceptable to send a single blinded workbook/CSV and split it afterward. The split step must be exact against each current staging root, not against an obsolete queue from a different parent chain.

- Use `human_score` as the human-facing return column and normalize it to binary `score_binary` only inside the generated `radiologist_decisions.csv` overlays.
- Match on `(Master_Case_ID, model_blinded)` and, when provided, exact `Ground_Truth_Diagnosis` and `diagnosis`; allow only numeric-equivalent formatting differences for `likert`, such as `4` versus `4.0`.
- If a returned workbook includes old or obsolete rows, filter to the current queue rows and record the obsolete count as audit evidence. Do not silently lift unmatched rows.
- Previously authoritative score reuse must be produced by `prepare` as terminal state `previous_authoritative_score`. Do not simulate it by hand-filling radiologist overlays.
- The one combined handback may cover several candidates, but `finalize-stage` remains per-model and per-staging-root.

### Carry-Forward Exception Path

Carry-forward is not the normal replay path. Use it only after the user explicitly authorizes carrying a completed adjudication package from one parent chain onto the current committed parent, and only when the source finalization has already passed the conventional audit for its own parent.

For the existing Muse exception, the approved helper is:

    py -3.11 scripts/radle_v2_carry_forward_muse_admission.py --source-final-root $SourceFinalRoot --parent-committed-root $ParentCommittedRoot --output-root $CarryForwardOutputRoot --carry-forward-note $CarryForwardNote
    py -3.11 scripts/radle_v2_incremental_admission.py commit --final-staging-root $CarryForwardFinalRoot
    py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $CarryForwardCommittedRoot --phase committed-readback --no-write

Expected: the source finalization is validated before use; the output appends the audited source scored delta to the current committed parent bytes; `append_manifest.json` records `evidence_carry_forward.source_finalization_id`, `source_parent_chain_id`, and `carried_forward_to_parent_chain_id`; committed-readback prints `RESULT=PASS`. Do not generalize this helper to non-Muse models without a separate reviewed script or an explicit plan revision.

### Hard Stop Rules

Stop immediately and update `Current State` as blocked if any of these happen:

- The parent root lacks `COMMITTED.json`, has a failing readback audit, or is not the latest intended chain parent.
- The source package is a smoke/test run, not exactly 200 cases, lacks runtime provenance, or has unresolved repair targets.
- `runtime_sha` is a file hash or source CSV hash instead of a runtime commit SHA.
- A staging root belongs to a different parent chain and no user-authorized carry-forward path exists.
- Any old-row hash, old key order, or parent-prefix check fails.
- A paid judge run lacks explicit authorization or a recorded cost/request receipt.
- A radiologist queue has missing, duplicate, nonbinary, or unexpected rows after filtering.
- `finalize-stage`, precommit audit, commit, or committed-readback fails.
- `build-idk0-lane` output counts are being adjusted by hand instead of derived from the committed master and roster.
- Public/panel artifacts are about to be published before the separate privacy approval artifact exists.

### Per-Model Completion Checklist

A model admission is complete only when the plan records all of the following:

- `ModelKey`, blind label, replacement target if any, parent committed root, and final committed root.
- Source path, projected package path if any, runtime SHA/status, package SHA256 inventory, and source manifest hash.
- Prepared staging root, intake ID, prepared audit result, terminal-state counts, and judge worklist count.
- Judge dry-run ceiling; real judge receipt if used, including HTTP requests, cost, locked rows, queue rows, cache hash, result hash, and judge audit result.
- Radiologist handback path/hash, filtered current-row count, per-model decisions hash, and split result when the queue is nonempty.
- Finalization ID, `scored_append_delta.csv` row count, final master row count, final master SHA256, append manifest SHA256, checksum count, and `COMMITTED.json` state/hash.
- Score-source counts for the new 200 rows.
- IDK0 lane root, lane manifest hash, active/excluded comparator counts, and panel-order counts if the downstream lane is generated.
- An updated `Current State` naming the next exact action.

## Colab Output To SVG Command Index

This is the end-to-end script map from a Colab/Morning output CSV stored on Google Drive to regenerated SVG panel artifacts. The current production-safe route is two-stage:

1. Admission worktree: consume the Colab wide CSV, adjudicate/finalize one model, and commit a new private `radle_v2_final_long_master.csv`.
2. Panel checkout: consume the committed private final long master and regenerate Score1000/Score2000 tables, panel stats, SVGs, logo-placement variants, PNG/contact sheets, and SVG audits.

### Upstream Colab Output Producers

The local admission pipeline starts after the Colab run has produced a complete wide CSV. The relevant producers/evidence paths are:

- `notebooks/RadLE_v1_5_Morning_Grok45_GPT56_MetaMuse_Append.ipynb`: Colab/Morning runner for Grok/GPT/Muse append-style runs.
- `notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb`: Meta Muse Spark ColabPro runner.
- `src/radle_benchmark.py`: shared benchmark runtime used by Morning notebooks.
- `src/radle_meta_model_api_runtime.py`: Meta Model API runtime helper.
- Google Drive output shape: a full `RadLE_v2_results_final.csv` style wide CSV with 200 rows and model-family columns such as `Diagnosis_<model_key>`, `Likert_<model_key>`, token/provenance fields, provider fields, returned model, request extras, and raw response fields.

The Drive file must be copied or projected into a local immutable package root. Do not run admission directly against a mutable Drive path.

### Admission Worktree Python Files

Use these from `C:/tmp/radle_v2_pre_m7_repair` or the clean successor admission worktree:

- `scripts/radle_v2_incremental_admission.py`: main CLI for `check-config`, `check-base`, `project-one-model`, `prepare`, `split-radiologist-scores`, `finalize-stage`, `commit`, and `build-idk0-lane`.
- `src/radle_incremental_admission.py`: core transaction, scoring, manifest, splitter, and IDK0-lane implementation behind the CLI.
- `scripts/radle_v2_dual_judge_delta.py`: dual-judge executor for dry-run, synthetic, and real OpenRouter adjudication.
- `src/radle_openrouter_judge.py`: OpenRouter judge client/helper used by the real judge executor.
- `scripts/audit_radle_v2_incremental_admission.py`: prepared, judge, precommit, committed, committed-readback, and IDK0-lane audit entrypoint.
- `scripts/radle_v2_carry_forward_muse_admission.py`: Muse-only carry-forward helper for the already accepted historical exception; not the normal path for future models.

Canonical admission command chain:

    py -3.11 scripts/radle_v2_incremental_admission.py check-config
    py -3.11 scripts/radle_v2_incremental_admission.py check-base

    py -3.11 scripts/radle_v2_incremental_admission.py project-one-model --source-wide $SourceWide --model-key $ModelKey --output-package $PackageRoot --runtime-sha $RuntimeSha

    py -3.11 scripts/radle_v2_incremental_admission.py prepare --parent-wide $ParentWide --parent-final-long-master "$ParentCommittedRoot/final/radle_v2_final_long_master.csv" --parent-authority-manifest $ParentAuthorityManifest --blind-map $BlindMap --incoming-package $PackageRoot --model-key $ModelKey --roster config/radle_v2_model_roster.json --variants config/radle_v2_base_authority.json --states config/radle_v2_terminal_states.json --output-root $AdmissionOutputRoot --dry-run
    py -3.11 scripts/radle_v2_incremental_admission.py prepare --parent-wide $ParentWide --parent-final-long-master "$ParentCommittedRoot/final/radle_v2_final_long_master.csv" --parent-authority-manifest $ParentAuthorityManifest --blind-map $BlindMap --incoming-package $PackageRoot --model-key $ModelKey --roster config/radle_v2_model_roster.json --variants config/radle_v2_base_authority.json --states config/radle_v2_terminal_states.json --output-root $AdmissionOutputRoot

    py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $StagingRoot --phase prepared --no-write

    py -3.11 scripts/radle_v2_dual_judge_delta.py --staging-root $StagingRoot --config config/radle_v2_judges.json --dry-run
    py -3.11 scripts/radle_v2_dual_judge_delta.py --staging-root $StagingRoot --config config/radle_v2_judges.json --authorization $JudgeAuthorization --real
    py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $StagingRoot --phase judge --no-write

    py -3.11 scripts/radle_v2_incremental_admission.py split-radiologist-scores --combined-scores $CombinedScoresCsv --staging-root $StagingRoot --output-root $RadiologistOutputRoot --reviewer-pseudonym $ReviewerPseudonym --reviewed-utc $ReviewedUtc

    py -3.11 scripts/radle_v2_incremental_admission.py finalize-stage --intake-root $StagingRoot --radiologist-decisions $RadiologistDecisionsCsv
    py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $FinalStagingRoot --phase precommit --no-write
    py -3.11 scripts/radle_v2_incremental_admission.py commit --final-staging-root $FinalStagingRoot
    py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $CommittedRoot --phase committed-readback --no-write

    py -3.11 scripts/radle_v2_incremental_admission.py build-idk0-lane --committed-root $CommittedRoot --output-root $Idk0LaneRoot --human-presentation pooled12 --roster config/radle_v2_model_roster.json --states config/radle_v2_terminal_states.json
    py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $Idk0LaneRoot --phase idk0-lane --no-write

Carry-forward exception command, only with explicit user authorization:

    py -3.11 scripts/radle_v2_carry_forward_muse_admission.py --source-final-root $SourceFinalRoot --parent-committed-root $ParentCommittedRoot --output-root $CarryForwardOutputRoot --carry-forward-note $CarryForwardNote
    py -3.11 scripts/radle_v2_incremental_admission.py commit --final-staging-root $CarryForwardFinalRoot
    py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $CarryForwardCommittedRoot --phase committed-readback --no-write

### SVG / Panel Checkout Python Files

Use these from the current panel checkout `C:/Users/thehb/Documents/RadLE v2` unless they have been intentionally ported into the admission worktree:

- `scripts/build_radle_v2_score1000_idk0_pipeline.ps1`: current tested wrapper from final long master to corrected IDK0 Score1000/Score2000 CSVs, panel stats, SVG variants, 5.4 logo placement, and audit.
- `scripts/build_radle_v2_clean_adjudication_master.py`: cleans the committed final long master into `radle_v2_clean_adjudication_master.csv` and cleanup receipt.
- `scripts/make_radle_v2_likert5_score1000_csvs_IDK0.py`: builds IDK0 Score1000/Score2000 CSV outputs with `--idk-score 0`.
- `scripts/audit_radle_v2_likert5_score1000_csvs_IDK0.py`: audits clean master, Score1000/Score2000 outputs, source hash, score rules, and status counts.
- `scripts/radle_v2_score1000_panel_stats_IDK0.py`: derives panel stats and bins from the Score1000/Score2000 output root.
- `scripts/make_radle_v2_score1000_panel23_svg_IDK0.py`: generates model-group/color final SVG variants and support files.
- `scripts/make_radle_v2_score1000_panel5_logo_placement_contact_sheet_IDK0.py`: promotes/checks the Panel 5.4 logo-placement/contact-sheet variant.
- `scripts/audit_radle_v2_score1000_panel23_IDK0.py`: structural SVG/panel audit; run before visual acceptance.
- `scripts/build_radle_v2_score1000_pipeline.ps1`, `scripts/build_radle_v2_handwritten_panels.ps1`, and the non-`_IDK0` Python scripts are the older/non-IDK0 lane. Do not use them for the current IDK0 Score2000 panel path unless the user explicitly reopens the non-IDK0 figure set.

Current wrapper command from a committed private master to SVGs:

    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_radle_v2_score1000_idk0_pipeline.ps1 -InputMaster "$CommittedRoot/final/radle_v2_final_long_master.csv" -OutDir "outputs/radle_v2_stats/<dated_final_scoring_root>/likert5_score1000_IDK0"

The wrapper expands to these Python calls:

    py -3.11 scripts/build_radle_v2_clean_adjudication_master.py --input $InputMaster --out-dir $OutDir --expected-input-sha256 $InputMasterSha256

    py -3.11 scripts/make_radle_v2_likert5_score1000_csvs_IDK0.py --clean-master "$OutDir/radle_v2_clean_adjudication_master.csv" --clean-receipt "$OutDir/adjudication_master_cleanup_receipt.json" --out-dir $OutDir --idk-score 0

    py -3.11 scripts/audit_radle_v2_likert5_score1000_csvs_IDK0.py --out-dir $OutDir --idk-score 0 --expected-source-sha256 $InputMasterSha256

    py -3.11 scripts/radle_v2_score1000_panel_stats_IDK0.py --score-root $OutDir --out-dir "$OutDir/handwritten_panels_IDK0" --expected-source-sha256 $InputMasterSha256

    py -3.11 scripts/make_radle_v2_score1000_panel23_svg_IDK0.py --mode model-group-color-final --source-panel-dir "$OutDir/handwritten_panels_IDK0" --out-dir "$OutDir/handwritten_panels_model_group_color_final_IDK0" --idk-score 0 --expected-source-sha256 $InputMasterSha256

    py -3.11 scripts/make_radle_v2_score1000_panel5_logo_placement_contact_sheet_IDK0.py --source-panel-dir "$OutDir/handwritten_panels_model_group_color_final_IDK0" --out-dir "$OutDir/handwritten_panels_model_group_color_final_IDK0/p5_IDK0" --idk-score 0

    py -3.11 scripts/audit_radle_v2_score1000_panel23_IDK0.py --mode model-group-color-final --score-root $OutDir --out-dir "$OutDir/handwritten_panels_model_group_color_final_IDK0" --idk-score 0 --expected-source-sha256 $InputMasterSha256

Expected SVG outputs live under:

    $OutDir/handwritten_panels_model_group_color_final_IDK0/

Expected support/render outputs include `figure_manifest.json`, `captions.md`, `data_provenance.md`, `reviewer_checklist.md`, SVG files, PNG renders, and `contact_sheet.png`. Do not hand-edit generated SVGs; edit generator Python, regenerate all panels together, run the structural audit, then inspect PNG/contact-sheet renders.

## Locked Facts

- The current primary checkout is `C:/Users/thehb/Documents/RadLE v2`, branch `codex/radle-v2-handwritten-panels`, observed HEAD `8c9de277631813172b391e685e772feccab9de28`, with unrelated staged, unstaged, and untracked work.
- Implementation must happen in a separate clean worktree created from a refreshed `origin/main`; never consolidate in the dirty primary checkout.
- Milestone 0 created implementation worktree `C:/tmp/radle_v2_incremental_admission`, branch `codex/radle-v2-incremental-admission`, from refreshed `origin/main` SHA `3a8c38ea880c5fbdda5a418181703faadb53e3bb`.
- Runtime preservation ref `refs/codex-preserve/morning-meta-8029ad46d90b` points to `8029ad46d90b7bc8ab67af1e805ffaa2619b85a2`.
- Milestone 1 path-scoped runtime integration passed stronger review. Receipt `review/runtime_integration_review.json` has SHA256 `7E9DF6CD6E614BC46F19922DC9A7C6EC01CB0B079D8CB90F12CAFEDE2953376C` and verdict `pass`.
- Milestone 1 frozen `src/radle_benchmark.py` diff SHA256 is `dbeddb9ad3fdbc261733a313a7c9c48f8d5454270ae4bba5f46676b156d2ceec`; worktree blob is `b8e0bbea69ce8dd01696495618cf1405838f16cf`.
- Copied runtime blobs from preserved runtime SHA are `src/radle_meta_model_api_runtime.py` `511eaf27669c04db5451dca7a81c67c675585f7d`, `notebooks/RadLE_v1_5_Morning_Grok45_GPT56_MetaMuse_Append.ipynb` `d5082d1d75005cf1c688e9ae320b38500359b5a3`, and `notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb` `58a4774d9dd78cfb8a328b08e6329a5f1217dc02`.
- Runtime validation passed: Python compile for `src/radle_benchmark.py` and `src/radle_meta_model_api_runtime.py`; JSON parse for both runtime notebooks; positive search for `grok_4_5`, `gpt_5_6_sol_pro`, and `muse_spark_1_1`; negative search for `49bf0d6` and `codex/llava-vllm-runtime` in the append notebook; provider-routing/meta-client probe printed `META_CLIENT_ROUTE=PASS`.
- Notebook `REPO_REF` defaults still point at historical runtime branches. They are not stale llava refs and were accepted by review for Milestone 1, but before actual Colab execution from this integration branch they must be overridden or updated so the checkout is unambiguous.
- The study's `49bf0d65659e24cfcb1759e432017f964256f203` unified runtime SHA is historical. At plan draft time the branch head is `8029ad46d90b7bc8ab67af1e805ffaa2619b85a2`, including Meta client-factory corrections. Snapshot it again at execution time.
- The authoritative parent scored master is `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/radle_v2_final_long_master.csv`, 6000 rows, 20 columns, SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`.
- The parent master contains 18 model arms and 12 individual human readers over 200 cases. Its old row order and every old field value are immutable.
- The 18-arm complete response base is `results/radle_v2_combined/final/RadLE_v2_results_final.csv`, observed 200x291 with SHA256 `7D9CE5C66FBECB6FF9B72EDB6676CA8CE4F9E5E3DCAF621610437A703EFDE17F`. Revalidate it before implementation.
- Current active model arms are `gpt_5_5`, `claude_fable_5`, `gemini_3_1_pro`, `grok_4_3`, `qwen_3_7_plus`, `glm_5v_turbo`, `gemma_4_31b`, `llama_4_maverick`, `mistral_large_3_2512`, `minimax_m3`, `nemotron_3_omni`, `internvl3_5_8b`, `medgemma_1_5_4b`, `octomed_7b`, and `lingshu_32b`.
- Current retained-but-excluded model arms are `claude_4_8_opus`, `grok_4_20`, and `glm_4_6v`.
- The stable blind-label map `outputs/radle_v2_stats/blinding_key_blinded_combined.csv` has SHA256 `09EBF4562EB541B59930930C70D5D6D1E3AF76373C49EA1F4F17C1AB471AB633` and currently uses `Candidate A` through `Candidate AD`; model labels are A-R and human labels are S-AD. New labels are allocated from the next unused global label, provisionally AE for Grok, AF for GPT, and AG for Muse if no other admission occurs first.
- The two requirements inputs are currently untracked and must be snapshot by hash before implementation: `requirements_radle_v2_incremental_model_admission.md` SHA256 `322751F4388E305D7B2BCA056A320F643FBC5F951663C4F2DE4CB27C995F098E` and `radle_v2_incremental_model_pipeline_requirements_study.md` SHA256 `1CA43BE159B59042A01CCD6B939C4CCC8B71D03851684F621BE6E8E0599376ED`.
- Each model arm is one reader over 200 cases, effective `N = 200`. The 12 human readers stay separate in backend rows.
- IDK0 is final. Exact/approved typo IDK, invalid response, invalid Likert, provider/parse failure, and retry-exhausted failure score zero.
- A Likert outside integral 0 through 4, including `8`, is an explicit `invalid_likert` terminal state. Preserve the raw value in private provenance; do not coerce it to 0, 4, blank, or a clinical score.
- Integral decimal Likert strings such as `2.0`, `3.0`, and `4.0` are valid integral Likerts; non-integral or out-of-range values remain `invalid_likert`.
- Two different historical `8` defects exist and must not be conflated. The parent master has one model Likert `8` row, case 119 / `Candidate R`, already frozen at score zero. Separately, the external radiologist overlay had three `Radiologist_final_score = 8` cells whose parent-master scores remained zero. All four historical rows remain byte-frozen; manifests describe the distinction without rewriting old provenance.
- Roster exclusion is not stored by rewriting old final-master `access` or `domain` cells. New downstream filtering must join the versioned roster by model key; this is required when `grok_4_3` and `gpt_5_5` become excluded while their historical rows remain byte-frozen.
- Score1000 uses signed `Likert + 1`: positive when correct, negative when wrong, and zero for IDK0/invalid terminal states. Human projection weights apply only downstream.
- Score2000 is exactly `Score1000 + 1000` and must preserve rank and state.
- Only canonical normalized equality to the canonical ground truth can auto-accept in the first release. All broader semantic matching is disabled.
- Exact same-case reuse of a previously authoritative binary-scored normalized diagnosis is allowed only through terminal state `previous_authoritative_score`; conflicting prior scores for the same case and normalized diagnosis are not reusable and fall back to later routing.
- The known conflicting pair for case 164, normalized candidate `diffuse esophageal spasm`, never auto-accepts and never locks from LLM agreement; route that pair directly to radiologist review. Other case-164 responses follow the ordinary rules.
- The previous successful dual-judge model IDs are `google/gemini-3.1-pro-preview` and `z-ai/glm-5.2`, called through OpenRouter at temperature 0.
- `scripts/radle_dual_judge_review.py` is evidence, not the new executor: it has hard-coded paths and a live dependency on the excluded previous-version `RadLE Stats` folder.
- Live reads from `C:/Users/thehb/Documents/RadLE Stats` are prohibited. The hash-pinned repo-local imported scoring key may be judge context only and never final authority.
- Public candidate generation is allowed only after private final-master commitment. Actual publication requires a separate recorded privacy approval.
- Milestone 2 configs are frozen with these current hashes: roster `2D6DCC6AEF35B1EB38E80D35A0F7407363D080A26119351FEC9AA27AE2EB122C`, judges `E7EB33CE809EE30E593228B57641CF77186DB5E5EE060E08C69B85549DD6B3EC`, terminal states `129D3AB04FE4103E17460097C4116E5497D35654EF0E72ED0AE3BC24A2D37267`, base authority `4608DFAAC21EC7BC0435F15E7A8B6223B6FF250E6718CBFF6C8E718E9BB884E5`, unit fixture `C783A3EF23072FDA099C0AAE58EE14B70D9F9927EDB79CC3DBA8A8EDD96767B7`.
- Checkpoint commit `fdbe56b` contains Milestone 1 runtime integration plus Milestone 2 config/test foundation.
- The checked-in judge prompt file hash is `545989BB6BE331E469D05722F8437A2F88D6D6E381D64F345CB6C899D73458CE`; it derives from dirty-primary evidence script blob `930ae988f1e0a33c068053e75bd4abe1b644fb7a` / source SHA256 `C1017B55826D6842E22D443B14FAECD5E4978CCE612D973DBEBD628AD2FF0A60`.
- Blank Likert on exact or approved-typo IDK remains IDK0. Blank Likert on any non-IDK committed diagnosis is `invalid_likert` and scores zero; it must not enter paid judge review.
- `tests/tmp/` is ignored scratch space; static fixtures under `tests/fixtures/radle_incremental_admission/` are intentionally unignored despite the repo-wide CSV ignore rule.
- The IDK0/Score1000/Score2000/panel scripts named by the plan are absent from this worktree and `origin/main`; Milestone 6 must either import them from another trusted source after review or implement the documented dynamic contract here.
- Real Grok/GPT/Muse admission is blocked until local external result packages are downloaded, sealed, and validated as full `TEST_LIMIT=None` 200-case runs. This worktree currently has no `Runs/`, `results/`, or `outputs/radle_v2_stats/incremental_admissions` package output.
- Milestone 8 has config-only readiness today: `grok_4_5` is Candidate AE and pending admission, but there is no append manifest, old-row immutability proof, scored delta, judge/radiologist evidence, committed parent, or post-admission independent review.
- Milestone 3 prepare/projection is implemented locally: `project-one-model` produces a one-model package with `results.csv`, `source_manifest.json`, and `SHA256SUMS`; `prepare` writes a content-addressed staging tree with required prepared outputs; prepared audit validates row counts and terminal-state counts.
- Checkpoint commit `99eb087` contains Milestone 3 prepared admission staging.
- Milestone 4 synthetic judge routing is implemented locally: dry-run computes call ceilings; synthetic mode writes judge evidence sidecars and a five-column `radiologist_queue.csv`; judge audit validates counts and prompt non-leakage. Real paid judge calls are still not implemented.
- Checkpoint commit `d36938d` contains Milestone 4 synthetic dual-judge/radiologist routing.
- Milestone 5 finalization is implemented locally: `finalize-stage` validates a signed radiologist decision overlay, writes `scored_append_delta.csv`, appends to a sibling final-long-master while preserving parent bytes as prefix, and writes `append_manifest.json`; `commit` writes `SHA256SUMS` before `COMMITTED.json`; readback validates both.
- The radiologist decision overlay header is exactly `Master_Case_ID,model_blinded,score_binary,reviewer_pseudonym,reviewed_utc,rationale`; the final scored delta keeps the parent schema and writes `final_score` plus `final_score_source`.
- Checkpoint commit `ec76ec4` contains Milestone 5 finalized incremental admission append.
- Milestone 6 dynamic IDK0 lane is implemented locally: `build-idk0-lane` writes `score_rows.csv`, `source1000.csv`, `public_candidate_summary.csv`, `panel_order.csv`, `group_summary.csv`, `panel_bins.csv`, and `score_lane_manifest.json`; `--phase idk0-lane` audits hashes, Score2000 shift, public privacy shape, counts, and active-only panel order.
- `build-idk0-lane` refuses a non-empty output root. Use a new dated lane path for every real run.
- Effective active/excluded status is derived by joining final-master model keys to the roster: pending-but-present admitted models become active, and their `replaces_model_key` target becomes excluded if present.
- Checkpoint commit `7c19c8b` contains Milestone 6 dynamic IDK0 score lane builder.
- Milestones 3-6 are synthetic-only until child Milestone 6.5 passes production-schema, authority, transaction, judge, runtime, and independent-review gates.
- `PRE_M7_REPAIR_RESULT=PASS`; Milestone 7 may inventory and seal packages, but every real admission still requires the one-model package, parent-chain, runtime-provenance, and judge-authorization gates.
- `project-one-model` now requires explicit runtime provenance. Do not accept a package where `runtime_sha` equals the source wide CSV SHA256.
- The current Grok/GPT/Muse staging roots under `C:/tmp/radle_v2_scoring_m7_20260710_1640` are scoring-only prepared roots against frozen parent `BASE_V2_20260706`; do not finalize or commit GPT/Muse from these roots as a sequential final chain without rerunning prepare against the committed predecessor parent.
- `split-radiologist-scores` accepts one combined long file with `human_score`, verifies it against the per-model `radiologist_queue.csv` files, writes exact `radiologist_decisions.csv` overlays under an output root, and tolerates Excel formatting of `likert` values such as `4.0` saved as `4`.
- Old normal-effort Muse evidence under `muse_spark_1_1` / Candidate AG is abandoned before final admission; do not reuse its judge locks, radiologist queue rows, or scores.
- Final admitted Muse remains `muse_spark_1_1` / Candidate AG for downstream SVG/table cleanliness. If the source CSV uses temporary `muse_spark_1_1_high` columns, project them into the normal `muse_spark_1_1` package identity and require `Actual_Request_Extra` to contain `reasoning_effort: high`.
- Supplied workbook `C:/Users/thehb/Downloads/Radiologist Review (1).xlsx`, sheet `July10`, was exported to `C:/tmp/radle_v2_radiologist_ingest_20260710_ae_af/radiologist_review_july10_ae_af.csv` with 69 rows: 28 Candidate AE and 41 Candidate AF. Export SHA256 is `216E725B989D84FAAA3029608540C0C75E629DE0B441A06DEEC24447EE187A19`.
- Candidate AE / `grok_4_5` is committed from final root `C:/tmp/radle_v2_scoring_m7_20260710_1640/grok_4_5/finalized/d5e05eb280504f189090fa9936ed2294c1e46303e81a457b7197945e1e360e53`; committed readback audit passed with 200 scored delta rows and 6200 output rows.
- Candidate AF / `gpt_5_6_sol_pro` must use sequential staging root `C:/tmp/radle_v2_sequential_m7_20260710_ae_af/gpt_5_6_sol_pro/206dcf19823a8fd1cfa2c4dc00b8d5182d34d292b1d8e190e18e825371074fdb`, not the earlier frozen-base scoring-only GPT root. Its real judge run produced 109 worklist rows, 218 HTTP requests, 77 locked agreement rows, and 33 radiologist queue rows.
- The returned workbook's Candidate AF rows are not sufficient for the sequential GPT queue: 20 rows match the current queue, 21 supplied AF rows are obsolete for this parent chain, and 13 current AF rows are missing. The supplemental missing queue is `C:/tmp/radle_v2_radiologist_ingest_20260710_ae_af/sequential_gpt_missing_13_queue.csv`, SHA256 `2E16870FA14DD8A858FBA8E10EE3D3D092E345A9D99424A8383B7D8723F4402F`; the Excel convenience copy is `C:/tmp/radle_v2_radiologist_ingest_20260710_ae_af/sequential_gpt_missing_13_queue.xlsx`, SHA256 `3BD1E0FF11DF692C29803FD774FA4B311920B7888BD2A027AE33F8CE6FA68AD8`. `Sheet1` and `July10` had zero exact case+ground-truth+diagnosis matches for those 13 rows outside Candidate AF, so no prior workbook score was safely liftable.
- High-effort Muse source is available at `G:/.shortcut-targets-by-id/1QPf3Z_T0Y-XXw3UC7xyk8y_BE4U07q2a/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/final/RadLE_v2_results_final.csv`, SHA256 `10A454B40B7E82DC76C367C3B113D55D77CD7CBBD1C8678CADB2F5BAE746F333`, 200 rows and 275 columns. It contains 16 `muse_spark_1_1_high` columns with 200 diagnoses, 200 Likerts, 200 `Actual_Request_Extra_muse_spark_1_1_high` values equal to `{"reasoning_effort": "high"}`, 200 nonblank reasoning-token fields, provider `Meta Model API`, and returned model `muse-spark-1.1`.
- High-effort Muse projection package is `C:/tmp/radle_v2_projected_muse_high_20260710_212153/muse_spark_1_1`, projection ID `86696b0a176b82db5ecfa4453107a9c09bf9fa82b54e3e8ed93cb7d72dfe7140`, output `results.csv` SHA256 `E10FF641D86A7AFAF1A8A497FDFA80515D60E3AF50BBF11C1813204170DA31E7`. The source branch `codex/morning-meta-muse-spark-append` resolved by `git ls-remote` to runtime SHA `37a0f44211188f85fdd93d14660e019046aaecd8`.
- Provisional high-effort Muse prepare against the committed Grok parent wrote staging root `C:/tmp/radle_v2_muse_high_after_grok_provisional_20260710_212153/muse_spark_1_1/7f791d70b852a0482f83d4cd9882b3478f0940b150687fdc9a6d2b1650d4214c`. It is not a final Muse root because GPT is not committed yet. Its terminal counts were `canonical_exact=16`, `previous_authoritative_score=76`, `provider_or_parse_failure=1`, `judge_required=107`; dry-run judge SHA `0634BBEF38AF8F5A46E6AA5B8A6E618C7FEB23386DC0D77852083BE28D447F5F`, 214 logical calls, 1284 worst-case HTTP requests.
- Six provisional Muse LLM rows should become previous-score reuse after GPT commit because the same normalized diagnosis is present in pending GPT evidence for case IDs 2, 57, 58, 60, 92, and 115. Five are already GPT judge-locked; case 58 has available radiologist score `0` in `sequential_gpt_available_decisions_20.csv`. The likely post-GPT Muse LLM worklist is `C:/tmp/radle_v2_muse_high_after_grok_provisional_20260710_212153/muse_high_likely_final_llm_worklist_after_gpt_commit_101.csv`, 101 rows, SHA256 `0A057DD6BCC7477CD614D9BF06A7127E2760D5157391736F6731CA2C2E401AC5`.
- User overrode the deferred-paid-Muse recommendation with "run LLM already, dont wait for GPT." The provisional high-effort Muse real judge run passed for intake `7f791d70b852a0482f83d4cd9882b3478f0940b150687fdc9a6d2b1650d4214c`: 107 worklist rows, 214 logical judge calls, 214 HTTP requests, actual cost `$0.445817159`, 69 locked agreement rows, 38 radiologist queue rows, judge cache SHA256 `080ADB37B724305FC38A0CE60A0E6FE153EED1FD9A5FE0A1D8DD90CD4450FFC9`, judge results SHA256 `CAC7AD272EAD2FB93DE4446D194292232FF7BE748601DD581B07304332D6436B`, radiologist queue SHA256 `8979AA0F4C933C796BB5D346F738382EA8F6F28590BBBD33393B1C58A650BAC5`. `audit_judge_evidence` passed.
- Remaining radiologist handoff after the Muse paid run is `C:/tmp/radle_v2_remaining_radiologist_handoff_20260710_2130/remaining_AF_AG_radiologist_queue_51.xlsx`, SHA256 `4E531B79C16B2A7446B3843A1DEB307355F9EA4793AD93D162D6B96E271F53EF`, with 51 rows: 13 Candidate AF and 38 Candidate AG. CSV companion SHA256 is `B2B3FB2B86FD6C364276C7F4661B1B1E4DCF8DBEFF971745670707659FF5C91B`.
- Returned workbook `C:/tmp/radle_v2_radiologist_ingest_20260710_ae_af/Radiologist Review (2).xlsx`, sheet `July10`, has SHA256 `DE18C8347E1CF7666875199E0BD541182A829D497012A4AC580FCD6862B4CBBB` and 120 data rows: 28 Candidate AE, 54 Candidate AF, and 38 Candidate AG. All current 71 AF/AG queue rows were matched exactly and all `human_score` values were binary.
- Filtered current AF/AG ingestion CSV is `C:/tmp/radle_v2_radiologist_ingest_20260710_review2/radiologist_review2_current_AF_AG_71.csv`, SHA256 `5A9434337E927F041A4623AF8D23327731D04CA373C1849A633B0732DDD72538`, with 33 Candidate AF rows and 38 Candidate AG rows. Split output root `C:/tmp/radle_v2_radiologist_ingest_20260710_review2/split_decisions_71` passed `SPLIT_RESULT=PASS`; GPT decisions SHA256 is `930A1365F744FD91219AA1BE10D62A6E7BCDF8C20CA32AB388F0287E0E46889E`, Muse decisions SHA256 is `F3CFC2E794FACDC3207D060492DD2199230235C1B7B25781B2AF143C1ECD98DB`.
- Candidate AF / `gpt_5_6_sol_pro` is committed from sequential final root `C:/tmp/radle_v2_sequential_m7_20260710_ae_af/gpt_5_6_sol_pro/finalized/658f6f2548994a62251f7e8eadcbf3e8fc51bcbbe5b37992edbde2de03626b4a`; committed readback audit passed with 200 scored delta rows, 6400 output rows, 56 checksum rows, output master SHA256 `A265F363FB249289549A23E60EC3081025AD2242089F5CA1C3012F5A38118255`, and `COMMITTED.json` transaction state `FINAL_MASTER_COMMITTED`.
- User authorized finalizing Muse without re-preparing against the committed GPT parent and without returning to radiology. Conventional Muse evidence finalization `C:/tmp/radle_v2_muse_high_after_grok_provisional_20260710_212153/muse_spark_1_1/finalized/7403d14f317b2e6db8a8151afb63ad5bf1592c302e1b4bbd75d3ce6da6c477ee` passed precommit audit with 200 scored delta rows and source counts `ai_judges=69`, `auto_score_not_required=1`, `canonical_exact=16`, `previous_authoritative_score=76`, `radiologist=38`.
- Candidate AG / high-effort `muse_spark_1_1` is committed as a carry-forward final root `C:/tmp/radle_v2_muse_high_carry_forward_after_gpt_20260711/muse_spark_1_1/finalized/18e1d292e1fe1f8d654be09aa2f65f65c6cc951be4b5d37d3c6649645e127df4`; committed readback audit passed with 200 scored delta rows, 6600 output rows, 56 checksum rows, output master SHA256 `D539A42AA04AA9A9A76FF4210B0FC74DE40B27DCED54E1A3887C9C911016AB9F`, append manifest SHA256 `772B4617B3675D0126FD1A592C1DB83EDABB2650E354A48AB5A4AAF574C739DE`, and `COMMITTED.json` transaction state `FINAL_MASTER_COMMITTED`. `append_manifest.json` records `evidence_carry_forward` from source parent chain `d5e05eb280504f189090fa9936ed2294c1e46303e81a457b7197945e1e360e53` to committed GPT parent chain `658f6f2548994a62251f7e8eadcbf3e8fc51bcbbe5b37992edbde2de03626b4a`.
- Carry-forward builder script is `C:/tmp/radle_v2_pre_m7_repair/scripts/radle_v2_carry_forward_muse_admission.py`, SHA256 `E8F3E41DFA93233EA1E380403C1A30BA738B40A5C9914EE829ECEF13E8BD2F88`; it preserves the validated Muse intake snapshot and evidence hashes while appending the audited Muse scored delta to the committed GPT parent bytes.
- The `Repeatable Admission SOP` in this plan is the front-door runbook for future model/version admissions. If CLI flags or transaction rules change, update that SOP before running another real admission.
- The `Colab Output To SVG Command Index` in this plan lists the current local script chain from Google Drive Colab wide CSV through admission, committed master, IDK0/Score2000 tables, SVG generation, logo placement, and SVG audit.

## Do Not Revisit

- Do not directly add columns to an IDK0 CSV or edit an existing final-long-master in place. See Decision Log 2026-07-10, append transaction.
- Do not rescore or rewrite old model or human rows while adding a model. See Decision Log 2026-07-10, historical immutability.
- Do not give the candidate model ground truth or accepted variants. Those are scorer/judge-only inputs. See Decision Log 2026-07-10, blinding.
- Do not inject accepted-variant context into release-1 judge prompts. Store variants as sidecar evidence only unless the user explicitly reopens this. See Decision Log 2026-07-10, minimal judge payload.
- Do not collapse 12 human backend readers into one or two stored rows. Pooling/splitting is presentation configuration. See Decision Log 2026-07-10, human projection.
- Do not use `weighted_score` as Score1000. It remains blank for new final-master rows and is removed in the downstream clean-master derivation. See Decision Log 2026-07-10, scoring.
- Do not use broad fuzzy, embedding, edit-distance, or LLM-generated aliases for deterministic acceptance in release 1. See Decision Log 2026-07-10, false-accept policy.
- Do not use smoke folders as full-run inputs and do not admit an unprojected shared Grok/GPT wide file containing historical families. See Decision Log 2026-07-10, package projection.
- Do not merge stale branches wholesale or accept the `8c9de27` GoalBuddy deletions incidentally. Runtime integration is path-scoped and SHA-reviewed. See Decision Log 2026-07-10, branch posture.
- Do not publish or upload generated candidate-public artifacts without a separate privacy approval artifact. See Decision Log 2026-07-10, privacy.
- Do not admit, score, or regenerate radiologist handoff from the old normal-effort Muse judge root. See Decision Log 2026-07-10 20:06, high-effort Muse identity.
- Do not repeat the provisional-root Muse paid-judge/carry-forward path as the default. The only accepted historical exception is the user-authorized high-effort Muse carry-forward committed on 2026-07-11; future carry-forward needs explicit user authorization and a reviewed manifest path. See Decision Log 2026-07-11 01:06, carry-forward exception.

## Progress

- [x] (2026-07-10 03:19 +05:30, Codex/GPT-5) Consolidated the requirements and study into an implementation-oriented draft.
- [x] (2026-07-10 03:19 +05:30, Codex/GPT-5) Verified the parent master shape/hash, current blind-label range, old score-source counts, exact dual-judge IDs, dirty primary state, and live unified runtime head.
- [x] (2026-07-10 03:19 +05:30, Codex/GPT-5) Reconciled parallel critiques covering requirements contradictions, exact code interfaces, small-executor failure modes, PowerShell commands, transaction identity, and commit sequencing.
- [x] (2026-07-10 04:16 +05:30, Codex/GPT-5) User approved execution with "GPT 5.5 please proceed"; no plan content changes were requested before Milestone 0.
- [x] (2026-07-10 04:16 +05:30, Codex/GPT-5) Created clean integration worktree `C:/tmp/radle_v2_incremental_admission`, preserved the runtime ref, and copied the three planning documents with matching hashes.
- [x] (2026-07-10 04:40 +05:30, Codex/GPT-5) Snapshot and path-review branch/runtime inputs; preserved only required current blobs, ran validations, and stored independent stronger review receipt.
- [x] (2026-07-10 04:54 +05:30, Codex/GPT-5) Add roster, judge, terminal-state, and base-authority configs; extract/freeze judge prompt evidence; add config validator, CLI `check-config`, static terminal-state fixture, and synthetic fixture generator. Local validation passes with 11 terminal fixture rows.
- [x] (2026-07-10 05:02 +05:30, Codex/GPT-5) Committed the Milestone 1-2 foundation checkpoint as `fdbe56b` (`Add RadLE v2 incremental admission foundation`).
- [x] (2026-07-10 05:11 +05:30, Codex/GPT-5) Implement package projection, prepared-stage validation, ground-truth snapshot, parent wide/long reconciliation, long-delta creation, terminal-state routing, judge worklist, and read-only prepared audit.
- [x] (2026-07-10 05:13 +05:30, Codex/GPT-5) Committed Milestone 3 as `99eb087` (`Implement prepared incremental admission staging`).
- [x] (2026-07-10 05:19 +05:30, Codex/GPT-5) Implement local/synthetic judge evidence generation, dry-run call math, agreement locks, radiologist queue routing, and read-only judge evidence audit.
- [x] (2026-07-10 05:20 +05:30, Codex/GPT-5) Committed Milestone 4 as `d36938d` (`Add synthetic dual judge routing`).
- [x] (2026-07-10 05:28 +05:30, Codex/GPT-5) Implement radiologist overlay validation, scored-delta finalization, immutable append, and independent precommit/committed-readback audit.
- [x] (2026-07-10 05:28 +05:30, Codex/GPT-5) Make IDK0 Score1000/Score2000 and panel-source contracts roster/manifest-derived and prove them on synthetic admissions.
- [x] (2026-07-10 15:51 +05:30, Codex/GPT-5.6 Sol) Completed blocking child Milestone 6.5 and recorded `PRE_M7_REPAIR_RESULT=PASS` from bounded read-only re-review receipt `review/pre_m7_production_repair_review.json`.
- [x] (2026-07-10 16:28 +05:30, Codex/GPT-5.6 Sol) Project and prepare Grok/GPT/Muse from sealed source with explicit inferred runtime SHA provenance, then run deterministic scoring and judge dry-run gates. Prepared audits passed for intake IDs `c1a2584464d6ee5a1dcee9368126b021daed3f729c56677ac766f0325847f797`, `be8f1a6ca7ca7672b9cf7ec3270f1d7de13553b40d3e539df35276483eda3a15`, and `2b42fe43bbac054d73c085037e187957ba479c05ef15a486269968962d8a8e80`.
- [x] (2026-07-10 16:28 +05:30, Codex/GPT-5.6 Sol) After `OPENROUTER_API_KEY` is exposed to the Codex process, run real dual-judge adjudication for the three scoring-only staging roots, audit evidence, and hand over the remaining radiologist queues.
- [x] (2026-07-10 18:39 +05:30, Codex/GPT-5.6 Sol) Ran real dual-judge adjudication for Grok scoring root `c1a2584464d6ee5a1dcee9368126b021daed3f729c56677ac766f0325847f797`; `--phase judge --no-write` printed `RESULT=PASS`, `judge_result_rows=196`, `locked_agreement_rows=71`, and `radiologist_queue_rows=28`.
- [x] (2026-07-10 18:52 +05:30, Codex/GPT-5.6 Sol) Ran and audited real dual-judge adjudication for GPT and Muse. GPT root `be8f1a6ca7ca7672b9cf7ec3270f1d7de13553b40d3e539df35276483eda3a15` used 224 HTTP requests, actual cost `$0.4667126392`, locked 72 rows, and left 41 radiologist rows. Muse root `2b42fe43bbac054d73c085037e187957ba479c05ef15a486269968962d8a8e80` used 232 HTTP requests, actual cost `$0.4877105322`, locked 89 rows, and left 28 radiologist rows.
- [x] (2026-07-10 18:52 +05:30, Codex/GPT-5.6 Sol) Created radiologist handoff `C:/tmp/radle_v2_radiologist_handoff_20260710_1845` with combined blinded queue `radiologist_queue_all_models_blinded.csv` (97 rows, SHA256 `5CC6D47615855F02F4B9EDE58B883B053883A5917351D85923CB3ED3F0441F53`) and combined decisions template `radiologist_decisions_all_models_template.csv` (97 rows, SHA256 `DAF6106FF6A48BBDA446D6E8E806E54D74DCBFDD5B3CF64FA274290065C139F7`).
- [x] (2026-07-10 19:24 +05:30, Codex/GPT-5.6 Sol) Added combined radiologist-score ingestion: one long file keyed by `(Master_Case_ID, model_blinded)` with `human_score` now splits into per-model exact `radiologist_decisions.csv` overlays and rejects missing, duplicate, unexpected, nonbinary, or misaligned rows.
- [x] (2026-07-10 20:06 +05:30, Codex/GPT-5.6 Sol) Reconciled the Muse rerun policy: abandoned old normal-effort Muse evidence, kept final admitted Muse as `muse_spark_1_1` / Candidate AG, added high-effort request-shape validation, and added projection support for temporary high-effort source columns via `--source-model-key`.
- [x] (2026-07-10 20:53 +05:30, Codex/GPT-5.6 Sol) Imported `Radiologist Review (1).xlsx`, split the July10 sheet into exact AE/AF score overlays, and finalized/committed Candidate AE / `grok_4_5`; committed readback passed.
- [x] (2026-07-10 20:53 +05:30, Codex/GPT-5.6 Sol) Re-prepared Candidate AF / `gpt_5_6_sol_pro` sequentially against the committed Grok parent and reran real dual judges; the run used 218 HTTP requests, cost `$0.4354546672`, locked 77 rows, and left 33 radiologist rows.
- [x] (2026-07-10 21:27 +05:30, Codex/GPT-5.6 Sol) Located and validated the completed high-effort Muse source in the Drive final CSV, projected `muse_spark_1_1_high` into normal `muse_spark_1_1` identity, and ran a provisional no-paid prepare/dry-run against the Grok-only parent.
- [x] (2026-07-10 21:27 +05:30, Codex/GPT-5.6 Sol) Estimated final Muse judge workload: provisional Grok-only parent gives 107 LLM rows, but after GPT commit six rows should become previous-score reuse, leaving likely 101 final Muse LLM rows.
- [x] (2026-07-10 21:30 +05:30, Codex/GPT-5.6 Sol) After the user explicitly overrode the wait-for-GPT recommendation, ran real paid dual judges for the provisional high-effort Muse Grok-parent root; result PASS, 214 HTTP requests, cost `$0.445817159`, 69 locks, 38 Candidate AG radiologist rows.
- [x] (2026-07-10 21:30 +05:30, Codex/GPT-5.6 Sol) Created remaining combined radiologist handoff with 51 rows: 13 Candidate AF plus 38 Candidate AG.
- [x] (2026-07-10 23:53 +05:30, Codex/GPT-5.6 Sol) Imported `Radiologist Review (2).xlsx`, extracted the current 71-row AF/AG queue, split exact decision overlays for GPT and provisional Muse, and finalized/committed Candidate AF / `gpt_5_6_sol_pro`; committed readback passed.
- [x] (2026-07-11 00:54 +05:30, Codex/GPT-5.6 Sol) Finalized Candidate AG / high-effort `muse_spark_1_1` as a user-authorized evidence-carry-forward admission onto the committed GPT parent; committed readback passed with 6600 final-master rows.
- [x] (2026-07-11 01:06 +05:30, Codex/GPT-5.6 Sol) Promoted a concise `Repeatable Admission SOP` near the top of this plan so future model/version admissions can follow a deterministic end-to-end runbook instead of reading the historical diary first.
- [x] (2026-07-11 01:13 +05:30, Codex/GPT-5.6 Sol) Added the `Colab Output To SVG Command Index` that enumerates the admission Python files, SVG/panel Python files, wrapper command, and wrapper-expanded commands from GDrive output to SVG audit.
- [ ] (YYYY-MM-DD HH:MM TZ, Agent/Model) Generate sanitized public candidates, regenerate active-only panels, perform structural/visual QA, and obtain publication approval separately.
- [ ] (YYYY-MM-DD HH:MM TZ, Agent/Model) Complete branch consolidation, evidence retention, final audit, and retrospective.

## Surprises & Discoveries

- Observation: the unified runtime branch advanced from study SHA `49bf0d6` to `8029ad4` with `b12cc58` and `8029ad4`, which correct the Meta client factory.
  Evidence: `git -C C:/tmp/radle_morning_meta_append log --oneline -3` on 2026-07-10.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: Production result packages store committed Likerts as integral decimal strings such as `2.0`, `3.0`, and `4.0`; the previous `int(raw_likert)` classifier would have misrouted those rows as `invalid_likert`.
  Evidence: first scoring dry-run incorrectly returned GPT terminal counts `{"invalid_likert": 200}`; after switching to `Fraction(raw_likert)` with denominator-one validation, config validation and the full 33-test suite passed, and GPT dry-run counts became canonical 17 / prior-score reuse 70 / mandatory-radiologist 1 / judge-required 112.
  Date/Author: 2026-07-10, Codex/GPT-5.6 Sol

- Observation: The user authorized using the environment key for real LLM judging, but this Codex process currently has no `OPENROUTER_API_KEY` or OpenRouter-named environment variable.
  Evidence: `if ($env:OPENROUTER_API_KEY) ...` printed `OPENROUTER_API_KEY_PRESENT=0`; `Get-ChildItem Env:` filtered for OpenRouter/router names returned no entries; all three `--real` judge invocations failed closed with `OPENROUTER_API_KEY is required for --real`.
  Date/Author: 2026-07-10, Codex/GPT-5.6 Sol

- Observation: After Candidate AE / Grok was committed, the Candidate AF / GPT queue changed relative to the earlier all-three frozen-base handoff: the true sequential AF queue has 33 rows, only 20 of the workbook's 41 AF rows match it, 21 supplied AF rows no longer belong to the current parent chain, and 13 current AF rows still need human scoring.
  Evidence: `C:/tmp/radle_v2_radiologist_ingest_20260710_ae_af/sequential_gpt_radiologist_reconciliation_summary.json` records `available_decisions_from_workbook=20`, `missing_decisions_requiring_radiologist=13`, and `obsolete_supplied_af_rows_not_in_current_queue=21`.
  Date/Author: 2026-07-10, Codex/GPT-5.6 Sol

- Observation: High-effort Muse can be projected now, but its final paid judge root is blocked on GPT commitment. The provisional Grok-only Muse root has 107 judge-required rows, while pending GPT evidence should make six of those rows previous-score reusable after GPT commit, leaving likely 101 final Muse LLM rows.
  Evidence: `C:/tmp/radle_v2_muse_high_after_grok_provisional_20260710_212153/muse_gpt_overlap_reuse_estimate.json` records six overlap case IDs and `likely_final_muse_judge_rows_after_gpt_if_locked_gpt_reuse_applies=102`; after confirming case 58 already has available radiologist score `0`, `C:/tmp/radle_v2_muse_high_after_grok_provisional_20260710_212153/muse_high_llm_workload_summary.json` records `likely_final_llm_rows_after_gpt_commit=101`.
  Date/Author: 2026-07-10 21:27 +05:30, Codex/GPT-5.6 Sol

- Observation: The user explicitly accepted running paid Muse LLM judging before GPT commit despite the stale-root warning. The run completed successfully and produced a Candidate AG radiologist queue rather than a final post-GPT Muse admission root.
  Evidence: user instruction "run LLM already, dont wait for GPT"; `judge_evidence/judge_summary.json` under provisional Muse intake `7f791d70b852a0482f83d4cd9882b3478f0940b150687fdc9a6d2b1650d4214c` records `result=PASS`, `actual_cost_usd=0.445817159`, `locked_agreement_rows=69`, and `radiologist_queue_rows=38`; `audit_judge_evidence` returned `result=PASS`.
  Date/Author: 2026-07-10 21:30 +05:30, Codex/GPT-5.6 Sol

- Observation: The old judge scripts were useful but should not replace the audited executor. `radle_dual_judge_review.py` and `radle_llm_judge.py` load `radle_api_keys.env`, request JSON mode, and do not require returned OpenRouter model aliases to equal the requested alias exactly. OpenRouter currently returns concrete version IDs such as `google/gemini-3.1-pro-preview-20260219` and `z-ai/glm-5.2-20260616`.
  Evidence: one-off probes using the same staged case succeeded for both judges in about 3-4 seconds; a six-call threaded probe completed in 7.01 seconds; focused and full judge tests passed after patching alias/version matching and concurrency.
  Date/Author: 2026-07-10, Codex/GPT-5.6 Sol

- Observation: A combined radiologist CSV may round-trip through Excel with `likert` values rendered as `4` instead of the source queue's `4.0`. The combined-score splitter must still catch row drift without falsely rejecting numeric-equivalent Likert cells.
  Evidence: the actual handoff queue begins with `4.0` values, while the user's screenshot displayed those cells as `4`; `test_split_combined_radiologist_scores_for_multi_model_sheet` rewrites `.0` Likerts to integral strings and still validates.
  Date/Author: 2026-07-10, Codex/GPT-5.6 Sol

- Observation: the pre-existing `project-one-model` implementation used `sha256_file(source_wide)` as `runtime_sha`, which would satisfy shape validation while misrepresenting runtime provenance.
  Evidence: `src/radle_incremental_admission.py` set projection manifest `runtime_sha` to the source wide SHA before the 2026-07-10 16:08 repair. The CLI now requires `--runtime-sha`, rejects equality with the source wide SHA, and records `runtime_sha_status`.
  Date/Author: 2026-07-10 16:08 +05:30, Codex/GPT-5.6 Sol

- Observation: the existing dual-judge script names the locked judge models but also hard-codes `C:/Users/thehb/Documents/RadLE Stats/RadLE_RSNA_Diagnosis_Scoring_key.csv` and cannot be the production adapter.
  Evidence: `scripts/radle_dual_judge_review.py` lines 35-53.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: current IDK0 generators/audits contain fixed historical counts, comparator totals, source hashes, labels, and panel prose. Passing the wrapper is not enough to make it append-safe.
  Evidence: `scripts/make_radle_v2_likert5_score1000_csvs_IDK0.py` and `scripts/audit_radle_v2_score1000_panel23_IDK0.py` contain expected counts for 15 active models and 16 displayed comparators.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: the five-field radiologist queue has no place to store a verdict. Keep the queue exact and issue a separate signed decision overlay keyed to it.
  Evidence: requirements lock the queue fields while finalization requires a binary reviewer decision and sign-off provenance.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: `git restore --source=<runtime>` from the clean worktree failed because Git metadata for the worktree lives under the primary checkout `.git/worktrees` path and the sandbox could not create `index.lock` there. Mechanical file copy from the preserved runtime worktree followed by `git hash-object` blob verification succeeded for the three added runtime files.
  Evidence: failed `git restore` reported permission denied on `C:/Users/thehb/Documents/RadLE v2/.git/worktrees/radle_v2_incremental_admission/index.lock`; copied blobs matched the runtime ref IDs.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: `origin/main` is behind the desired cloud roster and contains only 10 default `MODELS`; the runtime branch contains the required Grok 4.5 and GPT-5.6 entries, while Muse Spark is supplied by `src/radle_meta_model_api_runtime.py` rather than by a default `MODELS` row.
  Evidence: AST model-list comparison printed `MODEL_COUNT=10` for `origin/main`, `MODEL_COUNT=14` for the runtime branch, and the Milestone 1 route probe printed worktree `MODEL_COUNT=12` after adding only the two OpenRouter entries.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: Milestone 3 has no implemented transaction adapter yet. `scripts/radle_append_results.py` has useful CSV helpers and scorer rebuilding, but its replacement/mismatch/overwrite switches are too permissive for admission.
  Evidence: Scout Mill reported `scripts/radle_v2_incremental_admission.py` exposes only `check-config`; `scripts/radle_append_results.py` validates wide case metadata and can rebuild scorer view, but is not a final-long-master adapter.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: blank Likert was initially able to fall toward `judge_required` for a non-IDK committed diagnosis. This contradicted `src/radle_benchmark.py` validity semantics and the locked invalid-Likert policy.
  Evidence: Scout Meitner flagged the contradiction; fixture row `10,Pulmonary edema,,Pneumonia,false,invalid_likert,zero` and `invalid_likert_rules` now lock the zero path.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: the old handwritten panel script and panel CSV shapes are not present in this worktree or `origin/main`.
  Evidence: Scout Locke found no matching panel/figure/export filenames; only existing public export shapes in `src/radle_benchmark.py` are sanitized case-model/model-summary/call-log tables and a basic manifest.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: Milestone 6 named legacy IDK0/Score1000/panel scripts, but they are absent from this worktree and `origin/main`.
  Evidence: Scout Fermat found only `scripts/radle_append_results.py` for score/public terms on `origin/main`; visible worktree scripts are `internvl_experimental_probe.py`, `radle_append_results.py`, and `radle_v2_incremental_admission.py`.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: the existing public append path concatenates old public sidecars, while the required public candidate path must regenerate from the committed master with roster-derived excluded flags.
  Evidence: Scout Fermat reported `scripts/radle_append_results.py` public-table concatenation and `src/radle_benchmark.py` sanitized case-model/model-summary functions lack Score1000/Score2000, excluded flags, score-state metadata, and human projection fields.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: no real external Grok/GPT/Muse result package is present in this worktree, and the package gate is intentionally pre-admission.
  Evidence: Scout James found no `Runs`, `results`, or `outputs/radle_v2_stats/incremental_admissions` outputs; package admission requires full-run `TEST_LIMIT=None`, non-smoke run IDs, sealed manifests, and SHA256 inventories.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: Milestone 8 cannot be treated as ready because the existing review receipt is runtime-only and the admission transaction commands do not exist yet.
  Evidence: Scout Chandrasekhar found `scripts/radle_v2_incremental_admission.py` only exposes `check-config`; `review/runtime_integration_review.json` scopes its pass to Milestone 1; required `append_manifest.json`, scored delta, old-row proof, judge/radiologist evidence, and post-admission review are missing.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: Milestone 3 now covers prepared-stage transaction mechanics but intentionally does not finalize scores or append the final long master.
  Evidence: `prepare` writes `new_model_long_delta.csv` with terminal states and blank final scores, plus `judge_worklist.csv`; `audit_radle_v2_incremental_admission.py --phase prepared --no-write` reports `RESULT=PASS`. Scored delta, radiologist overlay, and immutable final-master append remain Milestones 4-5.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: Milestone 4 now covers local/synthetic judge routing only. It exercises agreement, disagreement, review flag, and mandatory-radiologist routing without network access.
  Evidence: `scripts/radle_v2_dual_judge_delta.py --dry-run` prints `JUDGE_RESULT=DRY_RUN_VALIDATED`; `--synthetic` writes 388 judge rows, 192 agreement locks, and 3 radiologist queue rows; `audit_radle_v2_incremental_admission.py --phase judge --no-write` prints `RESULT=PASS`.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: Milestone 5 needs two score field names by design. The human decision overlay uses `score_binary` to avoid pretending it is already a parent-master row, while the emitted scored long delta uses the parent schema's `final_score`.
  Evidence: `RADIOLOGIST_DECISION_FIELDS` in `src/radle_incremental_admission.py`; tests write `score_binary` decisions and assert binary `final_score` in `scored_append_delta.csv`.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: committed-readback must validate the checksum inventory, not merely the marker file. `SHA256SUMS` is written before `COMMITTED.json`, excludes both mutable files, and `COMMITTED.json` records the hash of the completed checksum file.
  Evidence: `commit_finalized_admission`, `audit_sha256sums`, and `audit_finalized_admission(..., require_committed=True)` in `src/radle_incremental_admission.py`; `test_finalize_commit_and_readback_preserve_parent_bytes` asserts `SHA256SUMS`, `COMMITTED.json`, and positive checksum row count.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: the first Milestone 6 scout confirmed that finalized append support exists and that the remaining gap was a dynamic score/panel-source lane. Additional branch and handoff scouts could not be launched because the thread's subagent limit was reached.
  Evidence: subagent `019f4951-2789-7b42-8b6c-5305a4418ae5` receipt; subsequent `spawn_agent` attempts returned `agent thread limit reached`.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: the implemented judge CLI takes `--staging-root`, not the older worklist/variant arguments that still appeared in the plan text.
  Evidence: a CLI receipt attempt with `--worklist` failed with "the following arguments are required: --staging-root"; rerun with `--staging-root ... --synthetic` printed `JUDGE_RESULT=PASS`.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: PowerShell direct writes into the generated `tests/tmp/.../m6_cli_output/<intake_id>` staging directory failed with access denied, while Python-created generated artifacts succeeded.
  Evidence: `Set-Content` and `New-Item` failed on the generated path; `py -3.11 -c ... Path.write_text(...)` wrote the scratch radiologist overlay used for the CLI receipt.
  Date/Author: 2026-07-10, Codex/GPT-5

- Observation: adjacent branch consolidation must be file-level, not branch-level. `codex/radle-v2-handwritten-panels` has a potentially useful `0931b0c` stats commit adding `scripts/radle_metrics.py`, `scripts/radle_v2_finalize_summaries.py`, and `scripts/summary_*.py`, but the branch diff would also delete this plan, configs, incremental scripts, and runtime notebooks. Runtime smoke branches contain useful Grok/GPT/Meta runtime commits but also long LLaVA/Ollama history.
  Evidence: `git show --name-status 0931b0c`, `git show --name-status 8c9de27`, and `git diff --name-status codex/radle-v2-incremental-admission..codex/radle-v2-handwritten-panels -- scripts src config Documents notebooks`.
  Date/Author: 2026-07-10, Codex/GPT-5

## Decision Log

- Decision: use transaction states distinct from roster status: `intake_prepared`, `adjudication_pending`, `radiologist_pending`, `precommit_validated`, and `final_master_committed`.
  Rationale: package validation is not the same event as scoring completion or active-roster replacement. A model becomes active only after `final_master_committed`.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: preserve old parent rows as exact bytes and append new rows; record historical invalid-Likert caveats without rewriting old provenance.
  Rationale: the user locked old rows and scores. Fixing old source labels would be a separate migration, not a model admission.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: release 1 auto-accepts canonical normalized equality only, and release 1 judge prompts show only canonical ground truth plus candidate diagnosis. Accepted variants may be snapshotted as sidecar evidence, but are not injected into judge prompts unless the user explicitly reopens that scope.
  Rationale: false accepts are more harmful than false rejects, current variant evidence is not calibrated to the required bound, and the latest locked prompt payload is intentionally minimal.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: dual-judge lock requires two parsed equal binary verdicts and neither judge flagging review. Disagreement, parse/API failure, either review flag, the known case-164 conflict pair, or another mandatory-review rule goes to radiology.
  Rationale: this is the conservative interpretation of the approved three-tier policy and preserves a low false-accept posture.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: `radiologist_queue.csv` has exactly five columns: `Master_Case_ID`, `model_blinded`, `Ground_Truth_Diagnosis`, `diagnosis`, and `likert`. `radiologist_decisions.csv` is a separate signed overlay containing the key, binary verdict, reviewer pseudonym, review time, and optional short rationale.
  Rationale: the queue remains minimal and blind while finalization still receives auditable decisions.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: generated private admissions live under a content-addressed ignored output root and are never overwritten. Code/config/tests live in Git.
  Rationale: private diagnosis and provider evidence must remain auditable without entering public source history.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: use two content identities. `intake_id` covers the parent authorities, incoming package, ground truth, roster baseline, requirements, normalizer, and terminal policy. `finalization_id` covers `intake_id` plus all judge/radiologist evidence and finalizer code; the committed admission ID is the finalization ID.
  Rationale: score-determining evidence arrives after package preparation, so one early ID could otherwise point to two different finalized outcomes.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: port runtime work by reviewed paths from a freshly resolved full SHA; never merge the long runtime ancestry wholesale.
  Rationale: the runtime branch diverges far before `origin/main` and contains unrelated historical runtime material.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: execute admissions in order Grok 4.5, GPT-5.6 Sol Pro, then Muse Spark, each using the prior committed master as its parent.
  Rationale: this matches current result availability and gives one reusable transaction rather than a three-model special case.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: public-candidate generation and publication are separate states. Sanitized candidate files may be generated after private commitment; publishing remains blocked until `privacy_approval.json` passes.
  Rationale: generation can be audited before release without treating local files as approved for distribution.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: blank Likert on non-IDK committed diagnoses is `invalid_likert`, scores zero, and bypasses judges. Exact/approved typo IDK may have blank Likert and remains IDK0.
  Rationale: missing Likert is malformed scoring evidence, not a clinical disagreement requiring paid adjudication; preserving IDK blank behavior keeps the locked IDK0 rule intact.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: Milestone 3 may reuse helper logic from `scripts/radle_append_results.py`, but must implement a stricter admission adapter with one-model projection, frozen parent proof, final-long delta creation, and no replacement/mismatch/overwrite escape hatches.
  Rationale: the existing appender solves useful CSV mechanics but not the append-only scored-master transaction.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: do not let Milestone 6 depend on absent legacy scripts without an explicit import/review step. The default path is to implement the dynamic IDK0/Score1000/Score2000 and public-candidate contracts from the committed master, roster, and manifests.
  Rationale: the visible branch and `origin/main` do not contain the named legacy scripts, and regenerating from source-of-truth manifests is safer than concatenating stale public sidecars.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: treat the external package gate as a hard stop for real admissions. Smoke folders, shared unprojected Grok/GPT outputs, missing checksum inventories, stale final hashes, missing repair evidence, or `TEST_LIMIT` not `None` block admission.
  Rationale: real package defects would contaminate the append-only master; package sealing must happen before scoring or promotion.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: prepared-stage reruns with the same `intake_id` must audit the existing staging tree before returning `already_prepared`.
  Rationale: idempotence should not bless a partially written or manually corrupted staging directory.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: Milestone 4 implements only no-network dry-run and synthetic evidence. Any real OpenRouter execution remains a later authorization-gated implementation and must not be inferred from the local synthetic path.
  Rationale: the user explicitly wants reliability before real package/panel work, and paid clinical adjudication needs a separate call ceiling and authorization artifact.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: Milestone 5 commit keeps the finalized admission in its content-addressed `intake_root/finalized/<finalization_id>` root and makes it authoritative by writing `SHA256SUMS` followed by `COMMITTED.json` as the last marker.
  Rationale: the synthetic and future private package roots can remain append-only without a second filesystem move; authority comes from manifest hashes plus committed readback, not from directory name alone.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: `score_binary` is the radiologist overlay verdict field; `final_score` is only written into the scored parent-schema delta.
  Rationale: keeping the overlay separate makes it clear which file is human adjudication input and which file is admitted scoring output.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: implement Milestone 6 directly in `src/radle_incremental_admission.py` and `scripts/radle_v2_incremental_admission.py` rather than importing absent legacy IDK0/panel scripts.
  Rationale: the visible worktree and `origin/main` do not contain the named legacy scripts; direct implementation from committed master, roster, and manifest is auditable and avoids stale hard-coded counts.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: `build-idk0-lane` emits row-level `score_rows.csv`, comparator-level `source1000.csv`, sanitized `public_candidate_summary.csv`, active-only `panel_order.csv`, `group_summary.csv`, `panel_bins.csv`, and `score_lane_manifest.json`.
  Rationale: this preserves the requested panel-data shape while keeping diagnosis/ground-truth/reasoning/image/private-path fields out of public/panel candidate outputs.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: human pooled/split presentation is computed only in summaries. Backend `score_rows.csv` retains the 12 individual human readers.
  Rationale: this matches the locked requirement that human storage remains individual while pooled12 or split6x6 is a downstream presentation decision.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: do not merge `codex/radle-v2-handwritten-panels`, Grok/GPT smoke branches, Meta Muse branches, or LLaVA runtime branches wholesale into incremental admission.
  Rationale: needed runtime blobs have already been copied and reviewed; future stats/panel imports should be selected by exact file path/commit after review because adjacent branches contain unrelated histories and, in the handwritten branch, deletions of current incremental-admission files.
  Date/Author: 2026-07-10, Codex/GPT-5

- Decision: deterministic reuse of previous scored answers is same-case and exact-normalized only, represented by terminal state `previous_authoritative_score`, and never overrides canonical exact, IDK/invalid/failure, or mandatory-radiologist rules.
  Rationale: this satisfies the user's request to reuse previously validated/scored answers without opening broad semantic matching or hiding the scoring source.
  Date/Author: 2026-07-10, Codex/GPT-5.6 Sol

- Decision: while waiting for radiologist decisions, it is acceptable to build all-three scoring-only staging roots against the frozen base to produce judge worklists and eventual radiologist queues. These roots are not final-chain commit roots for GPT/Muse; final admission must still rerun prepare sequentially after each predecessor is committed, or explicitly prove evidence reuse.
  Rationale: this gives the radiologist all needed rows in one batch while preserving the append-only parent-chain invariant for the final master.
  Date/Author: 2026-07-10, Codex/GPT-5.6 Sol

- Decision: support the radiologist return path as one combined long CSV with `human_score`, then split it into per-model `radiologist_decisions.csv` overlays. Require all expected queue keys by default, reject extra keys unless explicitly allowed, compare diagnosis/ground-truth evidence exactly when present, and compare `likert` numerically to survive spreadsheet formatting.
  Rationale: the user expects one all-models file, but the finalizer's per-model signed overlay contract remains the safer admission boundary.
  Date/Author: 2026-07-10 19:24 +05:30, Codex/GPT-5.6 Sol

- Decision: keep the final Muse identity as `muse_spark_1_1` / Candidate AG even though the successful Colab rerun may appear in the raw CSV as a temporary high-effort source family such as `muse_spark_1_1_high`. The old normal-effort Muse attempt is abandoned before final admission and its scoring/judge/radiologist evidence is not reusable.
  Rationale: downstream CSVs, summaries, SVGs, and labels should show one Muse Spark 1.1 arm, while private package provenance still proves high reasoning effort.
  Date/Author: 2026-07-10 20:06 +05:30, Codex/GPT-5.6 Sol

- Decision: do not force the earlier 41 Candidate AF workbook rows into the sequential GPT admission after Grok is committed. Reuse only exact matching AF decisions from the workbook, collect a supplemental 13-row AF radiologist queue, and keep the 21 obsolete supplied AF rows as audit evidence only.
  Rationale: final admission is parent-chain sensitive; committing GPT from stale AF rows would mix evidence generated for the frozen-base queue with the post-Grok sequential queue.
  Date/Author: 2026-07-10 20:53 +05:30, Codex/GPT-5.6 Sol

- Decision: defer paid high-effort Muse LLM judging until after GPT is finalized and committed, unless the user explicitly chooses to spend on provisional/stale-root evidence.
  Rationale: the OpenRouter judge cache key includes `judge_worklist_sha256` and manifest input hashes, so the final post-GPT Muse root will not safely reuse paid calls made against the Grok-only provisional root. Deferring also avoids likely duplicate calls for the six rows expected to become GPT-derived previous-score reuse.
  Date/Author: 2026-07-10 21:27 +05:30, Codex/GPT-5.6 Sol

- Decision: honor the user's explicit instruction to run paid Muse LLM judging before GPT commit, while preserving the warning that this evidence is bound to the provisional Grok-parent Muse root.
  Rationale: the user prioritized immediate LLM scoring over waiting for GPT. The resulting Candidate AG queue is useful for radiologist scoring now, but final Muse admission still needs a deliberate parent-chain decision after GPT is resolved.
  Date/Author: 2026-07-10 21:30 +05:30, Codex/GPT-5.6 Sol

- Decision: accept the user-authorized high-effort Muse evidence-carry-forward admission as the committed third admission and do not require re-preparing Muse or returning to radiology solely to satisfy the normal sequential path.
  Rationale: the completed Muse evidence was validated conventionally, all current AG radiologist rows were answered, and the carry-forward manifest records both the original Grok-parent evidence chain and the committed GPT parent chain. Repeating the normal path would add engineering churn and possible duplicate clinical review without a concrete scoring contradiction.
  Date/Author: 2026-07-11 01:06 +05:30, Codex/GPT-5.6 Sol

- Decision: promote the `Repeatable Admission SOP` near the top of this plan as the operational entry point for future model/version admissions.
  Rationale: the plan now needs to support continual model additions. A concise front-door runbook reduces the chance that a future session follows stale milestone history, skips parent-chain gates, or misses radiologist/judge/privacy stop rules.
  Date/Author: 2026-07-11 01:06 +05:30, Codex/GPT-5.6 Sol

- Decision: document the Colab-output-to-SVG path as a two-stage command chain: admission worktree first, then panel checkout wrapper.
  Rationale: future models will arrive as Colab/Morning wide CSVs, but current SVG generation is a tested panel-checkout wrapper that starts from the committed private final long master. Keeping both stages explicit prevents a future session from feeding raw Drive CSVs directly into SVG scripts or treating dynamic IDK0 lane outputs as already audited SVG figures.
  Date/Author: 2026-07-11 01:13 +05:30, Codex/GPT-5.6 Sol

## Revision Notes

- v1 (2026-07-10 03:19 +05:30, Codex/GPT-5): drafted the first implementation-ready plan from the requirements and research ledger; added transaction-state separation, exact judge configuration, old-byte immutability, dynamic expected counts, and small-agent stop gates.
- v2 (2026-07-10 03:19 +05:30, Codex/GPT-5): reconciled adversarial reviews; split intake and finalization identities, corrected the distinct model-Likert/radiologist-verdict `8` defects, pinned ground truth to the parent, specified normalizer/cache/repair contracts, added paid-run authorization, made commit/readback sequencing executable, pinned Python 3.11, and added worktree/public/privacy containment gates.
- v3 (2026-07-10 04:16 +05:30, Codex/GPT-5): recorded user approval and Milestone 0 execution evidence; updated current state, locked facts, progress, and artifact notes for the clean worktree.
- v4 (2026-07-10 04:40 +05:30, Codex/GPT-5): recorded Milestone 1 runtime integration, validations, independent review receipt, copied runtime blob IDs, and the notebook `REPO_REF` caveat before Milestone 2.
- v5 (2026-07-10 04:54 +05:30, Codex/GPT-5): recorded Milestone 2 implementation and validation; integrated scout findings for Milestones 3-6; locked blank-Likert behavior; added config/fixture hashes and next staging gate.
- v6 (2026-07-10 04:54 +05:30, Codex/GPT-5): integrated second-wave scout findings for dynamic IDK0/public candidates, external package gating, and Grok vertical-slice readiness; clarified that Milestone 8 is config-ready only until Milestones 3-5 exist.
- v7 (2026-07-10 05:02 +05:30, Codex/GPT-5): recorded checkpoint commit `fdbe56b` and advanced Current State to Milestone 3 implementation.
- v8 (2026-07-10 05:11 +05:30, Codex/GPT-5): recorded Milestone 3 prepare/projection implementation, validation receipts, and the remaining boundary between prepared staging and scored/finalized admission.
- v9 (2026-07-10 05:13 +05:30, Codex/GPT-5): recorded Milestone 3 commit `99eb087` and advanced Current State to Milestone 4.
- v10 (2026-07-10 05:19 +05:30, Codex/GPT-5): recorded Milestone 4 local/synthetic judge routing, evidence sidecars, judge audit, and paid-call boundary.
- v11 (2026-07-10 05:20 +05:30, Codex/GPT-5): recorded Milestone 4 commit `d36938d` and advanced Current State to Milestone 5.
- v12 (2026-07-10 05:28 +05:30, Codex/GPT-5): recorded Milestone 5 finalization, checksum/commit semantics, validation receipts, and commit `ec76ec4`; advanced Current State to Milestone 6.
- v13 (2026-07-10 05:28 +05:30, Codex/GPT-5): recorded Milestone 6 dynamic IDK0 score lane, implemented output schemas, scout receipt, local branch-consolidation scout, CLI receipts, validation evidence, and commit `7c19c8b`; advanced Current State to the external-results gate.
- v14 (2026-07-10 15:51 +05:30, Codex/GPT-5.6 Sol): recorded child Milestone 6.5 PASS, the repair review receipt, 31-test rerun, production-shape acceptance rerun, and the transition to Milestone 7 package inventory/sealing.
- v15 (2026-07-10 16:08 +05:30, Codex/GPT-5.6 Sol): recorded the projection provenance repair after discovering the CSV-hash-as-runtime-SHA defect; continued Milestone 7 with explicit inferred runtime SHA handling.
- v16 (2026-07-10 16:28 +05:30, Codex/GPT-5.6 Sol): recorded prior-score reuse, decimal-integral Likert validation, projected/prepared/audited all-three scoring roots, exact judge dry-run ceilings, paid authorization files, and the `OPENROUTER_API_KEY` environment blocker.
- v17 (2026-07-10 18:39 +05:30, Codex/GPT-5.6 Sol): recorded old-script-inspired OpenRouter executor repairs, bounded concurrency, successful Grok real judge run, actual cost, and Grok radiologist queue count.
- v18 (2026-07-10 18:52 +05:30, Codex/GPT-5.6 Sol): recorded GPT/Muse real judge PASS receipts, all-three radiologist queue handoff artifacts and hashes, and the next gate requiring filled radiologist decision overlays before sequential final admission and IDK0/SVG work.
- v19 (2026-07-10 19:24 +05:30, Codex/GPT-5.6 Sol): recorded combined radiologist-score splitter support, the Excel `likert` formatting edge case, CLI contract, focused splitter tests, full 36-test suite pass, and the updated next gate for one long returned file.
- v20 (2026-07-10 20:06 +05:30, Codex/GPT-5.6 Sol): recorded the high-effort Muse correction: final identity stays `muse_spark_1_1` / Candidate AG, old normal-effort Muse evidence is abandoned, and `project-one-model` can rename a temporary high-effort source family into the normal downstream Muse package.
- v21 (2026-07-10 20:53 +05:30, Codex/GPT-5.6 Sol): recorded the AE/AF workbook intake, committed Candidate AE / Grok, reran Candidate AF / GPT sequential judges against the Grok parent, and stopped GPT before finalization pending 13 supplemental AF radiologist decisions.
- v22 (2026-07-10 21:09 +05:30, Codex/GPT-5.6 Sol): recorded post-interruption readiness validation after the high-effort Muse identity correction and subsequent Grok/GPT plan progress; full discovery test suite passed with 37 tests.
- v23 (2026-07-10 21:27 +05:30, Codex/GPT-5.6 Sol): recorded Drive final CSV high-effort Muse validation, `_high` to normal Muse projection, provisional Grok-parent dry-run, expected post-GPT Muse LLM workload, and the decision to defer paid Muse judging until GPT commit.
- v24 (2026-07-10 21:30 +05:30, Codex/GPT-5.6 Sol): recorded the user override to run paid Muse LLM before GPT commit, the real judge PASS receipt, the Candidate AG radiologist queue, and the combined 51-row AF/AG remaining radiologist handoff.
- v25 (2026-07-11 00:54 +05:30, Codex/GPT-5.6 Sol): recorded `Radiologist Review (2).xlsx` ingestion, GPT commit, the user-authorized Muse evidence-carry-forward decision, the carry-forward builder script, Muse committed root `18e1d292e1fe1f8d654be09aa2f65f65c6cc951be4b5d37d3c6649645e127df4`, and the 6600-row committed-readback PASS.
- v26 (2026-07-11 01:06 +05:30, Codex/GPT-5.6 Sol): added a front-loaded `Repeatable Admission SOP`, including normal sequential admission, batch radiologist handback, carry-forward exception, hard stop rules, and per-model completion checklist; reconciled the stale Muse provisional-root prohibition into the accepted carry-forward exception rule.
- v27 (2026-07-11 01:13 +05:30, Codex/GPT-5.6 Sol): added a `Colab Output To SVG Command Index` that names the upstream Colab producers, admission worktree scripts, panel checkout scripts, canonical admission command chain, current Score1000/IDK0 wrapper command, and the wrapper-expanded Python calls through SVG audit.

## Outcomes & Retrospective

Milestone 0 outcome (2026-07-10 04:16 +05:30, Codex/GPT-5): implementation state is protected. The dirty primary checkout remains untouched for code work, and the clean implementation branch/worktree now holds only the three copied planning documents plus this Milestone 0 plan update. No implementation code exists yet.

Milestone 1 outcome (2026-07-10 04:40 +05:30, Codex/GPT-5): runtime integration is path-scoped and review-gated. Grok 4.5 and GPT-5.6 OpenRouter/provider routing, Meta Model API helper/client routing, and the two runtime notebooks are present with validation evidence and a passing stronger-model review receipt. No reusable lesson has been promoted to a skill; ask the user before creating or editing any skill.

Milestone 2 outcome (2026-07-10 04:54 +05:30, Codex/GPT-5): configuration contracts are executable. `check-config` validates roster counts, judge IDs and prompt hash, terminal-state order, invalid-Likert rules, source evidence, static fixtures, and prohibited-path absence. The remaining reusable lesson is project-specific enough to keep here for now; do not promote to a global skill without explicit user approval.

Milestone 3 outcome (2026-07-10 05:11 +05:30, Codex/GPT-5): prepared-stage admission is executable on synthetic 200-case data. `project-one-model` handles shared wide projection into a one-model package; `prepare` validates parent/incoming cases, metadata, parent wide/long reconciliation, ground-truth uniqueness, one model family, terminal-state routing, and writes the prepared staging tree; `audit_radle_v2_incremental_admission.py --phase prepared --no-write` validates the prepared outputs. No reusable lesson has been promoted to a skill; ask the user before creating or editing any skill.

Child Milestone 6.5 outcome (2026-07-10 15:51 +05:30, Codex/GPT-5.6 Sol): production-readiness repair is no longer blocked by the prior P0/P1 findings. The rerun passed `check-base`, `check-config`, `git diff --check`, `py_compile` for five modules, full discovery `Ran 31 tests`, production-shape acceptance, committed readback, and both IDK0 readbacks. Receipt `review/pre_m7_production_repair_review.json` records `verdict: pass`; no reusable lesson has been promoted to a skill.

Milestone 4 outcome (2026-07-10 05:19 +05:30, Codex/GPT-5): local judge/radiologist routing is executable on synthetic prepared staging. Dry-run call math reports 194 worklist rows, 2 judges, 388 base calls, and 2328 retry-inclusive worst-case HTTP requests. Synthetic evidence writes `request_payloads.jsonl`, `judge_cache.jsonl`, `judge_results.jsonl`, `agreement_locks.csv`, `radiologist_queue_routing_audit.json`, `judge_evidence_index.json`, and `radiologist_queue.csv`; judge audit passes. No reusable lesson has been promoted to a skill; ask the user before creating or editing any skill.

Milestone 5 outcome (2026-07-10 05:28 +05:30, Codex/GPT-5): finalized append is executable on synthetic prepared staging. `finalize-stage` creates a 200-row `scored_append_delta.csv`, copies/records the signed `radiologist_decisions.csv`, appends those rows to `final/radle_v2_final_long_master.csv` with the parent bytes as exact prefix, and writes `append_manifest.json`; `commit` writes `SHA256SUMS` then `COMMITTED.json`; committed readback validates the manifest hashes and checksum inventory. Validation receipts: `py -3.11 -m py_compile ...` passed, `py -3.11 -m unittest tests.test_radle_incremental_admission -v` ran 13 tests OK, `check-config` printed `CONFIG_RESULT=PASS`, the old RadLE Stats path scan had no matches, and `git diff --check` was clean. No reusable lesson has been promoted to a skill; ask the user before creating or editing any skill.

Milestone 6 outcome (2026-07-10 05:28 +05:30, Codex/GPT-5): dynamic IDK0 Score1000/Score2000 and panel-source output generation is executable on synthetic committed admissions. `build-idk0-lane` derives `score_rows.csv`, `source1000.csv`, `public_candidate_summary.csv`, `panel_order.csv`, `group_summary.csv`, `panel_bins.csv`, and `score_lane_manifest.json` from the committed final master plus roster/terminal policy; `audit --phase idk0-lane` validates hashes, counts, public-summary privacy shape, active-only panel order, and `Score2000 = Score1000 + 1000`. CLI receipt on synthetic data printed `IDK0_RESULT=PASS` with 2800 score rows, 2 complete models, 1 active model, 1 excluded model, 12 human backend readers, 3 presentation comparators, and 2 panel comparators. Validation receipts: `py -3.11 -m py_compile ...` passed, `py -3.11 -m unittest tests.test_radle_incremental_admission -v` ran 15 tests OK, `check-config` printed `CONFIG_RESULT=PASS`, the old RadLE Stats path scan had no matches, and `git diff --check` was clean. No reusable lesson has been promoted to a skill; ask the user before creating or editing any skill.

Combined radiologist-score adapter outcome (2026-07-10 19:24 +05:30, Codex/GPT-5.6 Sol): the pipeline is prepared for the user's single long all-models return file. `src/radle_incremental_admission.py` exposes `split_combined_radiologist_scores`; `scripts/radle_v2_incremental_admission.py` exposes `split-radiologist-scores`; focused tests prove successful multi-model splitting plus rejection of missing, duplicate, nonbinary, and mismatched rows. Validation receipts: `py -3.11 -B -m py_compile src\radle_incremental_admission.py scripts\radle_v2_incremental_admission.py tests\test_radle_incremental_admission.py` passed; focused splitter tests passed; `py -3.11 -B -m unittest discover -s tests -p test_*.py -v` ran 36 tests OK; `git diff --check -- src\radle_incremental_admission.py scripts\radle_v2_incremental_admission.py tests\test_radle_incremental_admission.py` was clean apart from line-ending warnings. No reusable lesson has been promoted to a skill; ask the user before creating or editing any skill.

High-effort Muse correction outcome (2026-07-10 21:09 +05:30, Codex/GPT-5.6 Sol): the convenient downstream path is ready. The roster keeps Candidate AG as `muse_spark_1_1`, requires private high-effort request evidence, and does not create a visible `muse_spark_1_1_high` comparator. `project-one-model` now accepts `--source-model-key` so a temporary source family can be projected into the normal admitted model identity. Validation receipts: `check-config` printed `CONFIG_RESULT=PASS` with roster hash `E2A04EC58B14638AB647CE75FAAADB31403AFA3BD436630D2914E89E6085AB63`; `test_muse_projection_can_rename_high_effort_source_family` passed; `test_projection_requires_real_runtime_sha_provenance` passed; `project-one-model --help` shows `--source-model-key`; `py -3.11 -B -m unittest discover -s tests -p test_*.py -v` ran 37 tests OK.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Plan maintenance | `execplan` | Keeps this living plan self-contained and reconciled | `manual` |
| Branch/runtime inspection | `none` | Focused Git and file inspection is sufficient | `none` |
| CSV/manifest implementation and tests | `none` | Direct Python engineering is sufficient | `none` |
| Radiologist workbook import/export, if XLSX is used | `spreadsheets` | Preserves formulas/types and supports workbook verification | `manual` |
| Data contract and final count validation | `data-analytics:validate-data` | Independent reconciliation of row counts, joins, and metrics | `manual` |
| SVG panel regeneration | `svg-panel-qa` | Structural SVG checks catch count/layout regressions | `manual` |
| Figure package readiness | `output-artifact-verifier` | Render-and-inspect verification for final visual artifacts | `manual` |
| Multi-agent coordination | `none` by default | A single transaction is intentionally serial; use orchestration only if several independent admissions run later | `none` |

## Context And Orientation

The repo root is `C:/Users/thehb/Documents/RadLE v2`.

Terms used here:

- A **final-wide package** is a 200-row Morning/runtime CSV with the three case keys and 16 columns for exactly one model family.
- A **long delta** is the same one model expressed as 200 rows, one row per case, before correctness is finalized.
- A **scored append delta** is exactly 200 finalized rows in the 20-column final-long-master schema.
- A **complete master** retains every admitted model arm, including excluded/replaced arms, plus 12 human readers.
- An **active roster** controls Score1000/panels only. Excluding an arm does not delete its rows.
- A **terminal state** is the single classified response state that determines whether a row auto-scores zero, auto-accepts exact match, needs judges, or needs radiology.
- An **admission** is committed only when the new final master and `COMMITTED.json` exist and all audit gates pass.
- A **candidate-public artifact** is locally sanitized output. It is not published until privacy approval is recorded.

Important existing files:

- `src/radle_benchmark.py`: Morning model registry, execution, audit, repair, promotion, and output conventions.
- `src/radle_meta_model_api_runtime.py`: Meta Muse Spark client path on the unified runtime branch.
- `scripts/radle_append_results.py`: existing wide appender; reuse helpers where correct, but normal admission must never pass `--replace-existing-model` or `--allow-metadata-mismatch`.
- `scripts/radle_v2_stats.py`: current roster-agnostic wide-to-long converter. Its abstention/failure classification and exact-match behavior are incomplete for this contract.
- `scripts/radle_llm_judge.py`: safe-copy single-judge implementation evidence.
- `scripts/radle_dual_judge_review.py`: historical dual-judge policy evidence; do not retain its hard-coded live prior path.
- Legacy IDK0/panel scripts named in earlier study notes are absent from this worktree and `origin/main`. Do not depend on them unless a later reviewed import explicitly adds them.
- `scripts/radle_v2_incremental_admission.py build-idk0-lane`: current dynamic Score1000/Score2000 and panel-source lane builder.
- `scripts/audit_radle_v2_incremental_admission.py --phase idk0-lane`: current read-only audit for generated IDK0 lane outputs.
- `Documents/requirements_radle_v2_incremental_model_admission.md`: distilled user requirements.
- `Documents/radle_v2_incremental_model_pipeline_requirements_study.md`: evidence and branch/artifact ledger.

## Target Files And Interfaces

Create or modify only these implementation families unless a milestone documents a justified expansion:

1. `config/radle_v2_model_roster.json`

   Store a schema version, stable candidate-label map, model metadata, and status. Keep transaction state separate from roster status. Required model fields are:

       model_key
       display_name
       requested_model_id
       returned_model_pattern
       runtime_path
       provider_route
       provider_value
       access
       domain
       blind_label
       roster_status

   Allowed `roster_status` values are `complete_master_active`, `complete_master_excluded`, `pending_admission`, and `rejected_or_incomplete`.

   Also create `config/radle_v2_base_authority.json` for the first transaction. It pins the base combined-wide, final-long-master, blinding-key, requirements, case-fingerprint, and ordered model-roster hashes. Later transactions use the previous committed admission's `COMMITTED.json` and `append_manifest.json` as parent authority instead of editing this base file.

2. `config/radle_v2_judges.json`

   Version and hash all judge behavior. Release 1 contains:

       google/gemini-3.1-pro-preview
       z-ai/glm-5.2
       base_url = https://openrouter.ai/api/v1
       temperature = 0
       timeout_seconds = 90
       max_retries = 6
       concurrency = 6
       review_on_any_flag = true

   Store the exact prompt text in checked-in UTF-8 `config/radle_v2_dual_judge_prompt_v1.txt`. Release 1 starts from the exact `SYSTEM_PROMPT` constant in `scripts/radle_dual_judge_review.py`, serialized with LF endings and no rubric changes. Approved variant context is added as structured request data, not by rewriting the system rubric. The manifest records source-script blob ID, extracted prompt hash, and final prompt hash.

3. `config/radle_v2_terminal_states.json`

   Define one precedence-ordered classifier. Required states and actions:

   | State | Trigger | Correctness action |
   | --- | --- | --- |
   | `invalid_likert` | nonblank Likert not integral 0..4 | zero, no judge |
   | `provider_or_parse_failure` | recognized provider/parse/failure marker or blank failed response | zero, no judge |
   | `idk_exact` | canonical exact IDK | zero, no judge |
   | `idk_approved_typo` | approved typo IDK only | zero, no judge |
   | `canonical_exact` | normalized candidate equals normalized canonical ground truth | one, no judge |
   | `mandatory_radiologist` | known conflict/rule match | radiologist |
   | `judge_required` | other valid committed diagnosis | dual judge |

   The classifier must assign exactly one state per new row. Preserve raw diagnosis and raw Likert in private files.

   Lock diagnosis normalizer version `radle_exact_v1` in this config. Its only operations are: convert the input to text; apply Unicode NFKC normalization; case-fold; replace Unicode punctuation characters, including apostrophes and hyphens, with one space; collapse whitespace; and trim. It must not stem, reorder or delete alphanumeric tokens, remove stop words, expand acronyms, apply synonyms, use edit distance, or call an LLM. Terminal IDK detection runs before canonical equality and accepts only `i don t know` from exact `I don't know` and `idon t know` from the observed typo `Idon't know`. Fixtures lock these outputs plus punctuation/case/whitespace boundaries and reject broader uncertainty phrases unless the user later approves them. A blank diagnosis is a terminal failure only when package audit/repair provenance identifies the failed attempt; a blank value by itself is not enough to fabricate failure provenance.

4. `src/radle_incremental_admission.py`

   Implement pure/testable helpers. The minimum public interfaces are:

       sha256_file(path: Path) -> str
       compute_case_triplet_sha256(rows: list[dict[str, str]]) -> str
       discover_one_model_family(fieldnames: list[str]) -> str
       project_one_model_bytes(source_csv: Path, model_key: str) -> tuple[bytes, dict]
       validate_one_model_package(package_root: Path, model_key: str, roster: dict) -> dict
       normalize_diagnosis(value: object) -> str
       classify_terminal_state(row: dict[str, str], ground_truth: str, policy: dict) -> str
       build_new_model_long_delta(...) -> dict
       allocate_next_candidate_label(existing_labels: list[str]) -> str
       build_adjudication_inputs(...) -> dict
       validate_radiologist_decisions(...) -> dict
       finalize_scored_delta(...) -> dict
       append_parent_bytes(parent_master: Path, scored_delta: Path, output_master: Path) -> dict
       build_idk0_score_lane(...) -> dict
       audit_idk0_score_lane(lane_root: Path) -> dict
       compute_intake_id(...) -> str
       compute_finalization_id(...) -> str
       audit_committed_admission(admission_root: Path) -> dict

   Functions return structured receipts and raise typed validation errors. They do not call network APIs and do not overwrite existing files.

5. `scripts/radle_v2_incremental_admission.py`

   Provide these subcommands:

       project-one-model
       prepare
       split-radiologist-scores
       finalize-stage
       commit
       build-idk0-lane

   `project-one-model --dry-run` computes deterministic projection bytes/hash without writing. Its optional `--source-model-key` reads a temporary source family, such as `muse_spark_1_1_high`, while writing the projected package under the normal `--model-key`, such as `muse_spark_1_1`. `prepare` writes only under a content-addressed output root; `split-radiologist-scores` writes copy-out per-model decision overlays and a receipt under its `--output-root`; `finalize-stage` writes only under `intake_root/finalized/<finalization_id>/`; `commit` marks a passing precommit tree by writing `SHA256SUMS` and then `COMMITTED.json`; `build-idk0-lane` refuses a non-empty output root. No command writes beside the downloaded/shared source. No command accepts an overwrite, replace-existing-model, or allow-metadata-mismatch escape hatch.

6. `scripts/radle_v2_dual_judge_delta.py`

   Read only the prepared `--staging-root`, judge config, and generated staging sidecars. Current implementation supports no-network `--dry-run` and deterministic local `--synthetic`. Real paid calls are not implemented yet; a future extension must require a separately created `paid_judge_authorization.json` whose admission/intake ID, judge IDs, prompt/config hashes, maximum HTTP requests, optional cost ceiling, approver, approval time, and expiry all validate.

7. `scripts/audit_radle_v2_incremental_admission.py`

   Independently recompute every count/hash from files. Do not import the write-path finalizer. Print one final line, `RESULT=PASS` or `RESULT=FAIL`, and exit nonzero on failure.

8. `tests/test_radle_incremental_admission.py` and `tests/fixtures/radle_incremental_admission/`

   Use synthetic, non-clinical rows. Include a small 5-case unit fixture for pure helpers and a generated 200-case end-to-end fixture for CLI gates. Add `tests/make_radle_incremental_fixture.py` to create the 200-case fixture under `tests/tmp/`; do not check generated fixture outputs into Git. Cover one valid new family, wrong case metadata, duplicate case, missing family column, same-key collision, IDK, typo-IDK, blank failure, Likert 8, exact match, non-exact judge row, judge disagreement, review flag, radiologist decision, and interrupted staging directory.

   The repo ignores `*.csv`. Add narrow `.gitignore` exceptions for `tests/fixtures/radle_incremental_admission/**/*.csv` and required JSON/TXT fixtures, then prove each static fixture is tracked with `git ls-files --error-unmatch`. Keep `tests/tmp/` ignored.

9. Existing IDK0/panel scripts

   Refactor inputs to accept a roster manifest and current source-master manifest. Remove historical row/count/source-hash assumptions from data logic. Keep display text, logos, colors, and selected variants explicit. Missing display registry or logo coverage for an active model is a hard error.

## Closed Data Contracts

### One-model final-wide input

The projected input has exactly 200 rows and exactly 19 columns in this order:

    Master_Case_ID
    Associated_Images
    Image_SHA256
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

Projection from a shared wide source must record source SHA256, selected columns, output SHA256, and cell-for-cell equality. Unknown extra columns are forbidden in the projected file.

Validation rules:

- `Master_Case_ID` is integral, unique, and exactly 1 through 200.
- Case metadata exactly matches the frozen triplet fingerprint `d65221a441c5687cd44d11df689072969d6bbe69089ab0eacaf84cb69ab28dd7` and its 263-image manifest.
- A committed diagnosis has integral Likert 0..4. IDK may have blank Likert. Any other Likert is retained but classified terminal invalid-zero.
- Token fields are blank only when unavailable by route/failure; otherwise nonnegative integers.
- Latency is blank only for a terminal failure; otherwise finite and nonnegative.
- Timestamp is a parseable UTC timestamp for every attempted row.
- Provider, returned-model, fallback, and request-extra fields satisfy the model-specific roster rules.
- Every row reaches one terminal state; no repair target remains unresolved.

The sealed incoming package must also contain or locally generate these private contracts:

- `requirements_snapshot.json`: hashes of the two requirements documents, the user-approved ExecPlan draft hash at implementation start, schema/policy versions, and approval timestamp. Later living-status edits to this plan do not mutate the frozen snapshot.
- `provenance/source_manifest.json`: schema version, original download/source path, runtime branch and full SHA, notebook/run label, requested model/config, prompt/config hashes, source file paths/hashes, and the deterministic one-model projection hash.
- `audit/promotion_audit.json`: one entry per case with terminal response state, repair target/attempt count, final promoted cell hash, and aggregate counts. Exactly 200 case entries and zero unresolved targets are required.
- `repair/repair_plan.csv` and `repair/repair_call_log.csv` when any repair occurred. Every changed cell must be an incoming-family cell named in the plan; before/after hashes and bounded attempt counts must reconcile. A missing conditional artifact is allowed only when the source manifest explicitly records `repair_required=false`.
- `SHA256SUMS`: every sealed package file except itself and the post-seal receipt, sorted by POSIX-relative path.

Package validation fails on an unlisted changed cell, an unresolved repair target, missing repair evidence, unbounded/missing attempt count, stale final manifest hash, or a source path that crosses into the previous-version RadLE Stats tree.

Model-specific expected routing:

| Model key | Required evidence |
| --- | --- |
| `grok_4_5` | requested `x-ai/grok-4.5`; xAI-only routing; provider `xAI`; returned model starts `x-ai/grok-4.5`; fallback false |
| `gpt_5_6_sol_pro` | requested `openai/gpt-5.6-sol-pro`; OpenAI-only routing; provider `OpenAI`; returned model starts `openai/gpt-5.6-sol-pro`; reasoning effort high |
| `muse_spark_1_1` | Meta OpenAI-compatible route; model `muse-spark-1.1`; provider `Meta Model API`; max output 2048; temperature omitted/suppressed; final admitted package must prove `reasoning_effort: high` in request-extra evidence |

### Final-long-master output

The output schema remains exactly the parent's 20 columns and order:

    run_id, Master_Case_ID, Associated_Images, model_blinded, candidate,
    provider, access, domain, Ground_Truth_Diagnosis, diagnosis, likert,
    response_valid, abstained, technical_failure, score_required,
    final_score_authoritative, final_score_source, weighted_score,
    rater_seniority, rater_seniority_rank

New model rows use these score-source values:

- `auto_score_not_required` for IDK, invalid Likert, provider/parse failure, or retry-exhausted terminal zero.
- `canonical_exact` for normalized equality to canonical ground truth.
- `previous_authoritative_score` for same-case exact-normalized reuse of a prior non-conflicting authoritative score.
- `ai_judges` when both judges agree without a review flag.
- `radiologist` only when a valid signed radiologist overlay supplies the binary verdict.

Historical source values, including `human_prior`, remain untouched. `weighted_score`, `rater_seniority`, and `rater_seniority_rank` are blank on new model rows.

The final master keeps the parent's single combined `run_id` value, currently `radle_v2_blinded_combined`, on new appended rows. The incoming runtime run ID remains in `append_input_manifest.json`, `source_manifest.json`, and `new_model_long_delta.csv`; it is not used to create a mixed-run final master. Finalized identity is `(Master_Case_ID, model_blinded)` plus the retained `candidate` model key.

Derive every new final-master field by this table; do not improvise per row:

| Field | New-row rule |
| --- | --- |
| `run_id` | parent's one combined run ID |
| `Master_Case_ID`, `Associated_Images` | exact incoming/frozen case values |
| `model_blinded` | committed next global blind label |
| `candidate` | roster `model_key` |
| `provider`, `access`, `domain` | roster values for the new model |
| `Ground_Truth_Diagnosis` | pinned canonical snapshot derived from parent master |
| `diagnosis`, `likert` | raw promoted incoming values |
| `response_valid` | false for invalid Likert or provider/parse failure; true otherwise |
| `abstained` | true only for exact/approved typo IDK; false otherwise |
| `technical_failure` | true only for provider/parse/retry-exhausted failure; false for invalid Likert |
| `score_required` | true only for `canonical_exact`, `mandatory_radiologist`, or `judge_required` |
| `final_score_authoritative` | binary result from terminal precedence |
| `final_score_source` | allowed source listed above |
| `weighted_score`, `rater_seniority`, `rater_seniority_rank` | blank |

For invalid Likert, retain the raw invalid Likert string, set `response_valid=false`, `abstained=false`, `technical_failure=false`, `score_required=false`, `final_score_authoritative=0`, and preserve `terminal_state=invalid_likert` in the scored-delta sidecar/manifest. This distinguishes response-schema invalidity from a provider/transport failure.

### Radiologist artifacts

`radiologist_queue.csv` columns, exact order:

    Master_Case_ID,model_blinded,Ground_Truth_Diagnosis,diagnosis,likert

`radiologist_decisions.csv` columns, exact order:

    Master_Case_ID,model_blinded,score_binary,reviewer_pseudonym,reviewed_utc,rationale

Finalization requires exactly one decision for every queued key, no extra key, score in `{0,1}`, nonblank reviewer pseudonym, parseable UTC time, and a recorded file SHA256. The rationale may be blank. If an XLSX is used for human convenience, it is a transport artifact; the sealed CSV overlay is authoritative.

The preferred all-models handback can be one combined long CSV with required columns:

    Master_Case_ID,model_blinded,human_score

If present, these queue evidence columns are checked before splitting:

    Ground_Truth_Diagnosis,diagnosis,likert

`split-radiologist-scores` validates that every expected `(Master_Case_ID, model_blinded)` from the supplied staging roots is present exactly once, rejects unexpected rows by default, normalizes `human_score` to binary `score_binary`, and writes one exact-schema `radiologist_decisions.csv` under each model output folder. `Ground_Truth_Diagnosis` and `diagnosis` are exact string checks. `likert` accepts numeric-equivalent formatting such as `4` versus `4.0` because spreadsheet tools may strip decimal zeros.

Always create a header-only decisions template beside the queue. If the queue has zero data rows, that header-only file is the valid `NONE` overlay and hashes as such. If the queue is nonempty, finalization blocks until every required decision row is present and valid.

### Generated transaction tree

Use:

    outputs/radle_v2_stats/incremental_admissions/
      .staging/intake/<intake_id>/
      .staging/final/<finalization_id>/
      admissions/<finalization_id>/
        requirements_snapshot.json
        append_input_manifest.json
        canonical_ground_truth_snapshot.csv
        provenance/source_manifest.json
        audit/promotion_audit.json
        one_model_final_wide.csv
        combined_wide/RadLE_v2_results_final.csv
        combined_wide/scorer_view.csv
        new_model_long_delta.csv
        audit/terminal_state_audit.json
        accepted_variants_snapshot.csv
        judge_worklist.csv
        judge_evidence/
        judge_evidence/judge_evidence_index.json
        radiologist_queue.csv
        radiologist_decisions.csv
        scored_append_delta.csv
        roster/model_roster.json
        roster/blind_label_map.csv
        final/radle_v2_final_long_master.csv
        append_manifest.json
        audit/admission_audit.json
        SHA256SUMS
        COMMITTED.json

Define an immutable preparation identity before any judge call:

    intake_id = SHA256(
      "radle-intake-v1\n" +
      parent_combined_wide_sha256 + "\n" +
      parent_final_long_master_sha256 + "\n" +
      incoming_one_model_final_wide_sha256 + "\n" +
      roster_manifest_sha256 + "\n" +
      package_manifest_sha256 + "\n" +
      requirements_snapshot_sha256 + "\n" +
      canonical_ground_truth_snapshot_sha256 + "\n" +
      terminal_policy_sha256 + "\n" +
      normalizer_code_sha256 + "\n"
    )

After all judge/radiologist evidence exists, define the finalized admission identity:

    finalization_id = SHA256(
      "radle-finalization-v1\n" +
      intake_id + "\n" +
      accepted_variants_snapshot_sha256 + "\n" +
      terminal_state_audit_sha256 + "\n" +
      judge_worklist_sha256 + "\n" +
      judge_config_sha256 + "\n" +
      judge_prompt_sha256 + "\n" +
      judge_evidence_index_sha256 + "\n" +
      paid_judge_authorization_sha256_or_NONE + "\n" +
      radiologist_queue_sha256_or_NONE + "\n" +
      radiologist_decisions_sha256_or_NONE + "\n" +
      scored_append_delta_sha256 + "\n" +
      finalized_roster_sha256 + "\n" +
      finalized_blind_label_map_sha256 + "\n" +
      finalizer_code_sha256 + "\n"
    )

`finalization_id` is the committed admission ID. `finalize-stage` writes the complete candidate tree under `intake_root/finalized/<finalization_id>/`. Run independent `audit --phase precommit` there. Only on `RESULT=PASS` may `commit` write `SHA256SUMS` and then write `COMMITTED.json` in that finalized root as the last operation. Then run read-only `audit --phase committed-readback --no-write`; it may print a receipt or write outside the committed tree, never mutate it. The visible final directory remains non-authoritative until the marker exists.

An identical committed finalization returns `ALREADY_ADMITTED` only after all hashes revalidate. The same `intake_id` may have several abandoned/rejected finalization attempts, but only an explicitly selected committed finalization may become the next parent. An uncommitted staging/final directory is non-authoritative and may resume only after all recorded hashes revalidate. Same model key with differing incoming content is a hard collision.

`SHA256SUMS` contains lowercase SHA256 values for every regular transaction file using sorted POSIX-relative paths, except `SHA256SUMS` itself and `COMMITTED.json`. Those two exclusions prevent a circular checksum and are declared in `append_manifest.json`. `COMMITTED.json` records the SHA256 of the completed `SHA256SUMS` file and the parent committed finalization ID, or `BASE_V2_20260706` for the first admission.

## Dynamic Count Table

Use formulas, not historical constants:

    C = 200 cases
    H = 12 backend human readers
    M = complete-master model arms
    A = active model arms
    complete_long_rows = C * (M + H)
    active_score1000_rows = C * (A + H)
    combined_wide_columns = 3 + (16 * M)
    scorer_columns = 2 + (2 * M)
    public_model_result_rows = C * M
    displayed_comparators = configured_human_projection_rows + A

Expected chain if no other model is admitted first:

| State | Complete M | Active A | Complete long rows | Active Score1000 rows | Wide columns | Scorer columns | Public model rows | Displayed with pooled human |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Parent | 18 | 15 | 6000 | 5400 | 291 | 38 | 3600 | 16 |
| After Grok 4.5 | 19 | 15 | 6200 | 5400 | 307 | 40 | 3800 | 16 |
| After GPT-5.6 | 20 | 15 | 6400 | 5400 | 323 | 42 | 4000 | 16 |
| After Muse Spark | 21 | 16 | 6600 | 5600 | 339 | 44 | 4200 | 17 |

Grok commitment changes `grok_4_3` to excluded and `grok_4_5` to active in the new roster version. GPT commitment changes `gpt_5_5` to excluded and `gpt_5_6_sol_pro` to active. Muse commitment adds `muse_spark_1_1` as active without excluding another arm.

## Execution Posture

Branch strategy: create `codex/radle-v2-incremental-admission` from refreshed `origin/main` in `C:/tmp/radle_v2_incremental_admission`. If that branch or path already exists, stop and inspect it; do not delete or reuse blindly.

Environment: use the clean worktree for code, config, tests, and living-plan updates. Read ignored authoritative artifacts from the primary checkout by absolute path until they are deliberately mirrored into a private test/input root with matching hashes.

Before every mutating command, assert the worktree and branch. Use resolved paths for every output and reject any output that is not a descendant of the expected worktree or approved private output root:

    $ExpectedRoot = (Resolve-Path -LiteralPath 'C:/tmp/radle_v2_incremental_admission').Path
    $ActualRoot = (git rev-parse --show-toplevel).Trim() -replace '\\','/'
    if (($ExpectedRoot -replace '\\','/') -ne $ActualRoot) { throw "Wrong worktree: $ActualRoot" }
    if ((git branch --show-current).Trim() -ne 'codex/radle-v2-incremental-admission') { throw 'Wrong branch' }

At each milestone boundary, save `git status --short`, compare it with that milestone's path allowlist, and stop on any unexpected path. Because `outputs/` is ignored, also resolve and print every intended output root before writing; Git status alone is not a containment check.

Every external command must exit 0 before its output is parsed or the next command runs. In PowerShell, check `$LASTEXITCODE` immediately after captured native commands and throw on nonzero. Never treat missing parseable status lines as success.

Handoff: remain in the worktree through implementation and synthetic validation. Hand back to Local only after a reviewed commit/branch exists and the user wants normal IDE inspection. Do not remove any worktree or branch during this plan.

## Milestones

### Milestone 0: Protect state and establish the clean execution base

Skill: `execplan` for updating this plan; otherwise `none`.

At the end, a clean worktree exists, the current source SHAs are recorded, the three planning documents are present with matching hashes, and no primary-checkout file except this plan has changed.

From the dirty primary checkout:

    git status --short
    git branch --show-current
    git rev-parse HEAD
    git fetch origin
    git rev-parse origin/main
    git rev-parse codex/morning-meta-muse-spark-append
    git worktree list --porcelain

Stop if fetch fails, a required ref is absent, or `C:/tmp/radle_v2_incremental_admission` already contains unknown work.

Before creating the worktree, preserve the resolved runtime object under a durable local ref:

    $RUNTIME_SHA = (git rev-parse codex/morning-meta-muse-spark-append).Trim()
    if ($LASTEXITCODE -ne 0 -or $RUNTIME_SHA -notmatch '^[0-9a-f]{40}$') { throw 'Invalid runtime SHA' }
    git update-ref "refs/codex-preserve/morning-meta-$($RUNTIME_SHA.Substring(0,12))" $RUNTIME_SHA

Create the worktree only after the checks:

    git worktree add -b codex/radle-v2-incremental-admission C:/tmp/radle_v2_incremental_admission origin/main

Copy only these planning documents from the primary checkout into the clean worktree, then compare SHA256:

    Documents/requirements_radle_v2_incremental_model_admission.md
    Documents/radle_v2_incremental_model_pipeline_requirements_study.md
    Documents/execplan_radle_v2_incremental_model_admission.md

Use literal paths in PowerShell:

    $SourceRoot = 'C:/Users/thehb/Documents/RadLE v2'
    $TargetRoot = 'C:/tmp/radle_v2_incremental_admission'
    $Docs = @(
      'Documents/requirements_radle_v2_incremental_model_admission.md',
      'Documents/radle_v2_incremental_model_pipeline_requirements_study.md',
      'Documents/execplan_radle_v2_incremental_model_admission.md'
    )
    foreach ($Relative in $Docs) {
      $Source = Join-Path $SourceRoot $Relative
      $Target = Join-Path $TargetRoot $Relative
      Copy-Item -LiteralPath $Source -Destination $Target
      if ((Get-FileHash -Algorithm SHA256 -LiteralPath $Source).Hash -ne
          (Get-FileHash -Algorithm SHA256 -LiteralPath $Target).Hash) {
        throw "Planning document hash mismatch: $Relative"
      }
    }

Acceptance:

- Worktree `git status --short` lists only the copied planning documents.
- Source and destination SHA256 match for each copied file.
- Record refreshed `origin/main` and unified runtime full SHAs in `Current State` and `Locked Facts`.

Recovery: if worktree creation partially fails, inspect `git worktree list` and the target directory. Do not run `git worktree remove --force`; ask the user if unknown files exist.

### Milestone 1: Review and preserve the runtime integration paths

Skill: `none`.

At the end, the clean branch contains only the required current Morning/Grok/GPT/Meta runtime paths and no unrelated runtime history.

Resolve `RUNTIME_SHA` from the preserved ref at execution time and record the source blob IDs before touching the worktree:

    $RUNTIME_SHA = (git rev-parse codex/morning-meta-muse-spark-append).Trim()
    git diff --name-status origin/main...$RUNTIME_SHA
    git log --reverse --oneline origin/main..$RUNTIME_SHA
    git diff origin/main $RUNTIME_SHA -- src/radle_benchmark.py
    git show "${RUNTIME_SHA}:src/radle_meta_model_api_runtime.py"
    $RuntimePaths = @(
      'src/radle_benchmark.py',
      'src/radle_meta_model_api_runtime.py',
      'notebooks/RadLE_v1_5_Morning_Grok45_GPT56_MetaMuse_Append.ipynb',
      'notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb'
    )
    foreach ($Path in $RuntimePaths) { git rev-parse "${RUNTIME_SHA}:$Path" }

Required path candidates are:

    src/radle_benchmark.py
    src/radle_meta_model_api_runtime.py
    notebooks/RadLE_v1_5_Morning_Grok45_GPT56_MetaMuse_Append.ipynb
    notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb

For paths that do not exist on `origin/main`, restore only the named blob from the pinned runtime SHA:

    git restore --source=$RUNTIME_SHA -- src/radle_meta_model_api_runtime.py
    git restore --source=$RUNTIME_SHA -- notebooks/RadLE_v1_5_Morning_Grok45_GPT56_MetaMuse_Append.ipynb
    git restore --source=$RUNTIME_SHA -- notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb

Do not wholesale-restore `src/radle_benchmark.py`. It exists on both lines and must be reconciled hunk by hunk: the Grok/GPT model entries, provider locks, Meta dispatch/client import, and append guards are in scope; unrelated historical runtime changes are not. Save and review the focused diff before applying it. If those hunks depend on an unlisted helper, add the helper deliberately and record it under `Surprises & Discoveries` rather than copying the whole branch.

The current dirty primary Morning notebook contains a scorer-view rebuild that is not guaranteed to exist on the runtime branch. A mini executor may produce a focused diff and record the primary notebook SHA, but must not copy the whole dirty notebook. Port this behavior only after the stronger-model review names the exact notebook cells/hunks and expected target blob hash.

Do not copy all files from the runtime branch. After path-level integration:

    py -3.11 -m py_compile src/radle_benchmark.py src/radle_meta_model_api_runtime.py
    py -3.11 -m json.tool notebooks/RadLE_v1_5_Morning_Grok45_GPT56_MetaMuse_Append.ipynb > $null
    py -3.11 -m json.tool notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb > $null
    rg -n "grok_4_5|gpt_5_6_sol_pro|muse_spark_1_1" src notebooks
    rg -n "49bf0d6|codex/llava-vllm-runtime" notebooks/RadLE_v1_5_Morning_Grok45_GPT56_MetaMuse_Append.ipynb

Acceptance:

- Both Python files compile and both notebooks parse.
- The unified notebook prints branch/full commit evidence and does not pin a stale superseded branch.
- Grok/GPT routing remains OpenRouter/provider-locked; Muse uses the Meta client path.
- No unrelated GoalBuddy deletion or broad runtime file import appears in `git diff --stat origin/main`.
- `git status --short` contains only the four runtime allowlist paths plus the three planning documents at this milestone.

Stop gate: this semantic path review should receive a stronger-model review before staging. A mini executor may prepare the diff but must not declare the runtime consolidation complete without that review receipt.

The receipt is `review/runtime_integration_review.json` with reviewer model/identity, UTC time, runtime SHA, reviewed diff SHA, exact path allowlist, validation outputs, verdict `pass|fail`, and rationale. The mini executor cannot author its own passing receipt.

### Milestone 2: Freeze schemas, roster, policies, and synthetic fixtures

Skill: `none`.

At the end, configuration and synthetic fixtures express every contract above without reading private production data during tests.

Create the three config files, prompt file, JSON schemas where useful, and fixture set. Add a `--check-config` command that validates:

- unique model keys and blind labels;
- no active/excluded overlap;
- exactly 12 frozen human blind labels in the existing map;
- candidate label ordering supports A..Z, AA..AZ, BA..;
- all required active display fields exist;
- judge IDs and prompt hash are fixed;
- terminal-state precedence is total and non-overlapping for fixtures;
- no config or code string contains the live previous-version path.

Commands:

    py -3.11 scripts/radle_v2_incremental_admission.py check-config --roster config/radle_v2_model_roster.json --judges config/radle_v2_judges.json --states config/radle_v2_terminal_states.json
    rg -n -F "C:/Users/thehb/Documents/RadLE Stats" src scripts config tests
    if ($LASTEXITCODE -eq 0) { throw 'Prohibited live path found in new code' }
    if ($LASTEXITCODE -gt 1) { throw 'rg search failed' }
    py -3.11 -m unittest tests.test_radle_incremental_admission -v
    $TrackedFixtures = @(git ls-files 'tests/fixtures/radle_incremental_admission/**')
    if ($TrackedFixtures.Count -eq 0) { throw 'Static fixtures are not tracked' }

Expected final lines:

    CONFIG_RESULT=PASS
    Ran <N> tests
    OK

The `rg` command must return exit 1 (no matches) in new production paths; exit 2 or higher is an error. Existing historical scripts are evidence only and are excluded from this gate. `git ls-files` must list every static fixture, including required CSV files despite the repo-wide CSV ignore rule.

### Milestone 3: Implement projection, package validation, and prepare transaction

Skill: `none`.

At the end, a synthetic wide package can be projected to one family, sealed, validated, converted to a 200-row-equivalent fixture delta, and partitioned into exact/zero/judge/radiologist states without network calls.

The `prepare` command accepts:

    --parent-wide <path>
    --parent-final-long-master <path>
    --parent-authority-manifest <path>
    --incoming-package <dir>
    --model-key <key>
    --roster <path>
    --variants <path>
    --output-root <path>
    --dry-run

The canonical ground-truth snapshot is derived only from `Ground_Truth_Diagnosis` in the pinned parent final-long master. Require exactly one nonblank identical ground-truth value for each case 1..200 and include its hash in `intake_id`; there is no arbitrary ground-truth CLI path. Before preparation, prove the parent wide's ordered model families and every diagnosis/Likert cell agree with the model rows in the parent final-long master. For later admissions, require a valid parent `COMMITTED.json`, append-manifest chain, and roster/blind-map hashes.

`--dry-run` validates and prints the derived `intake_id`, counts, routing proof, next blind label, and intended paths without writing. Without `--dry-run`, it writes only to a new intake staging directory.

Both modes end with parseable status lines:

    INTAKE_ID=<64 lowercase hex characters>
    TRANSACTION_STATE=DRY_RUN_VALIDATED

or:

    INTAKE_ID=<64 lowercase hex characters>
    STAGING_ROOT=<absolute path>
    TRANSACTION_STATE=ADJUDICATION_PENDING

Required prepare outputs are `requirements_snapshot.json`, `append_input_manifest.json`, `canonical_ground_truth_snapshot.csv`, `provenance/source_manifest.json`, `audit/promotion_audit.json`, `one_model_final_wide.csv`, versioned `combined_wide`, rebuilt `scorer_view.csv`, `new_model_long_delta.csv`, `audit/terminal_state_audit.json`, `accepted_variants_snapshot.csv`, `judge_worklist.csv`, and versioned roster/blind-label staging files. Conditional repair artifacts are copied and hashed when repair occurred.

The accepted-variants snapshot is sidecar evidence only in release 1. It never auto-scores a non-canonical match and is not injected into judge prompts unless the user explicitly reopens that scope. Exclude conflicting entries and record case 164 conflict status explicitly.

Build the release-1 snapshot prospectively from parent-master rows with `final_score_source=radiologist`, grouped by `(Master_Case_ID, normalized diagnosis)`. Record accepted and rejected consistent evidence, but do not show variants to release-1 judges. Imported v1 evidence remains in the evidence ledger only and is not injected into release-1 prompts. Quarantine every conflicting group, especially case 164 / `diffuse esophageal spasm`. Minimum snapshot fields are policy version, case ID, image hash, canonical reference raw/normalized, variant raw/normalized, evidence tier, decision, conflict flag, automation action, source row keys, and source artifact hash.

Generate the 200-case synthetic CLI fixture, then use explicit arguments:

    py -3.11 tests/make_radle_incremental_fixture.py --out tests/tmp/synthetic_admission
    $PrepareArgs = @(
      '--parent-wide', 'tests/tmp/synthetic_admission/parent_wide.csv',
      '--parent-final-long-master', 'tests/tmp/synthetic_admission/parent_final_long_master.csv',
      '--parent-authority-manifest', 'tests/tmp/synthetic_admission/parent_authority.json',
      '--incoming-package', 'tests/tmp/synthetic_admission/incoming_package',
      '--model-key', 'synthetic_model_v1',
      '--roster', 'tests/tmp/synthetic_admission/model_roster.json',
      '--variants', 'tests/tmp/synthetic_admission/accepted_variants.csv',
      '--output-root', 'tests/tmp/synthetic_admission/output'
    )
    py -3.11 scripts/radle_v2_incremental_admission.py prepare @PrepareArgs --dry-run
    $PrepareOutput = @(py -3.11 scripts/radle_v2_incremental_admission.py prepare @PrepareArgs)
    $PrepareOutput | ForEach-Object { Write-Host $_ }
    $StagingLine = $PrepareOutput | Where-Object { $_ -like 'STAGING_ROOT=*' }
    if (@($StagingLine).Count -ne 1) { throw 'prepare did not emit one STAGING_ROOT' }
    $StagingRoot = ($StagingLine -split '=', 2)[1]
    py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $StagingRoot --phase prepared --no-write
    py -3.11 -m unittest tests.test_radle_incremental_admission -v

Acceptance:

- One and only one model family is discovered.
- Synthetic case/family/collision failures exit nonzero and write no committed output.
- Every delta row has exactly one terminal state.
- Likert 8 remains raw `8`, is invalid-zero, and never enters the judge worklist.
- Blank Likert on exact/approved typo IDK remains IDK0; blank Likert on any other committed diagnosis is invalid-zero and never enters the judge worklist.
- Canonical exact enters `canonical_exact`; no non-exact row auto-accepts.
- Dry run is byte-idempotent and creates no files.
- Repeating prepare with identical input reports the same intake ID; differing same-key input is a hard collision.
- Parent wide/long model diagnoses and Likerts reconcile exactly, canonical ground truth is unique for all 200 cases, and source artifact hashes are unchanged before/after prepare.

### Milestone 4: Implement dual-judge evidence and radiologist routing

Skill: `none` for CSV/JSONL code. Use `spreadsheets` only if an XLSX transport is added.

At the end, synthetic judge results produce deterministic agreement locks and a minimal radiologist queue, with an append-only/resumable cache.

The release-1 judge prompt contains canonical ground truth and candidate diagnosis only. It excludes model key, blind label, provider, Likert, variants, reasoning, image names, and raw response. Case ID and blind label may exist in sidecar/cache/radiologist metadata, but are not visible to the judge prompt. Serialize the complete request payload deterministically. The judge runner hashes its worklist, sidecar variant snapshot, normalizer/terminal policies, config, and prompt. Cache key:

    (requested_judge_model_id, returned_judge_model_id, exact_request_payload_sha256,
     judge_config_sha256, prompt_sha256, normalizer_code_sha256,
     terminal_policy_sha256, case_triplet_sha256, variants_snapshot_sha256)

Dry-run command:

    $JudgeOut = Join-Path $StagingRoot 'judge_evidence'
    py -3.11 scripts/radle_v2_dual_judge_delta.py --staging-root $StagingRoot --config config/radle_v2_judges.json --out-dir $JudgeOut --dry-run
    py -3.11 scripts/radle_v2_dual_judge_delta.py --staging-root $StagingRoot --config config/radle_v2_judges.json --out-dir $JudgeOut --synthetic

Dry run prints cache misses and a worst-case request ceiling that includes retries:

    base_calls = cache_miss_pairs * 2 judges
    worst_case_http_requests = base_calls * max_retries

Before real calls, ask the user to approve the displayed intake ID, judge IDs, cache misses, `worst_case_http_requests`, and estimated/maximum cost if OpenRouter exposes one. Store that separate response in `paid_judge_authorization.json`; the mini executor cannot self-authorize from this plan. Then run:

    if (-not $env:RADLE_PAID_JUDGE_AUTHORIZATION) { throw 'Set RADLE_PAID_JUDGE_AUTHORIZATION only after user approval' }
    $Authorization = (Resolve-Path -LiteralPath $env:RADLE_PAID_JUDGE_AUTHORIZATION).Path
    $AuthorizationPayload = Get-Content -LiteralPath $Authorization -Raw | ConvertFrom-Json
    $ApprovedMaxRequests = [int]$AuthorizationPayload.max_http_requests
    # Real paid calls are not implemented in the current CLI; this remains a future authorization-gated extension.

Acceptance:

- Dry run prints unique pair count, cache hit/miss count, two logical judge calls per miss, retry-inclusive worst-case HTTP requests, and refuses a real run whose authorization/request cap is absent, expired, mismatched, or smaller than the computed ceiling.
- Each judge result records requested/returned model, prompt/config hashes, timestamps, raw response hash, parsed verdict, confidence, flag, retries, and terminal API status.
- Agreement locks only equal binary verdicts from the two distinct configured requested/returned judge identities with no review flag.
- Disagreement, missing/parse/API error, any review flag, and mandatory-review rows enter the queue.
- Model identity is absent from the judge prompt and radiologist queue; blind label is absent from the judge prompt.
- Queue has exactly the five locked columns.
- No API key value appears in logs or artifacts.

Recovery: rerun with the same cache. Never truncate JSONL. A malformed final line is quarantined and recorded; earlier valid entries remain usable.

### Milestone 5: Finalize the delta and append an immutable sibling master

Skill: `data-analytics:validate-data` for an independent final reconciliation; otherwise `none`.

At the end, synthetic adjudication produces a sealed 200-row-equivalent scored delta and a committed sibling master while preserving all parent bytes.

Finalization refuses to run when a radiologist queue is nonempty and its decision overlay is missing/incomplete. It applies precedence only to new rows:

1. terminal invalid/IDK/failure -> zero;
2. canonical exact -> one;
3. valid radiologist decision for queued row;
4. unflagged dual-judge agreement;
5. otherwise block.

Commands, using paths emitted by the preceding phases:

    $RadiologistDecisions = Join-Path $StagingRoot 'radiologist_decisions.csv'
    $FinalizeOutput = @(py -3.11 scripts/radle_v2_incremental_admission.py finalize-stage --intake-root $StagingRoot --radiologist-decisions $RadiologistDecisions)
    $FinalizeOutput | ForEach-Object { Write-Host $_ }
    $FinalStagingLine = $FinalizeOutput | Where-Object { $_ -like 'FINAL_STAGING_ROOT=*' }
    if (@($FinalStagingLine).Count -ne 1) { throw 'finalize-stage did not emit one FINAL_STAGING_ROOT' }
    $FinalStagingRoot = ($FinalStagingLine -split '=', 2)[1]
    py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $FinalStagingRoot --phase precommit
    $CommitOutput = @(py -3.11 scripts/radle_v2_incremental_admission.py commit --final-staging-root $FinalStagingRoot)
    $CommitOutput | ForEach-Object { Write-Host $_ }
    $CommittedLine = $CommitOutput | Where-Object { $_ -like 'COMMITTED_ROOT=*' }
    if (@($CommittedLine).Count -ne 1) { throw 'commit did not emit one COMMITTED_ROOT' }
    $CommittedRoot = ($CommittedLine -split '=', 2)[1]
    py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $CommittedRoot --phase committed-readback --no-write

Acceptance:

- Scored delta has exactly one row per case, sorted numeric 1..C, unique `(Master_Case_ID, model_blinded)` keys, binary final score, and allowed source.
- The new master begins with the exact parent bytes and preserves every parsed parent row/key in the same order. Parse the scored delta with a real CSV parser and require exactly 200 records; do not count physical lines because quoted fields may contain embedded newlines.
- The append implementation copies the parent file bytes unchanged, detects/reuses the parent's line terminator for appended serialization, validates the scored-delta header against the parent header, and appends only the 200 parsed delta records. It must not round-trip parent rows through pandas or `csv.DictWriter`.
- Parent-row semantic hash, parent-byte SHA, delta SHA, output SHA, roster SHA, judge evidence hashes, and radiologist overlay hash are in `append_manifest.json`.
- `finalize-stage` emits `FINALIZATION_ID` and `FINAL_STAGING_ROOT`; precommit audit prints `RESULT=PASS`; `commit` performs promotion and writes `COMMITTED.json` last; committed-readback is read-only and prints `RESULT=PASS` again.
- Rerunning committed input reports `ALREADY_ADMITTED`; it does not rewrite timestamps or files.
- A same-key/different-content replay fails.

### Milestone 6: Make IDK0, Score1000/2000, public candidates, and panels dynamic

Skills: `svg-panel-qa` for generated SVG structure and `output-artifact-verifier` for final visual files.

At the end, downstream data logic derives counts/ordering from the committed roster and master manifests. Synthetic Grok/GPT replacement and Muse-addition fixtures prove the four rows of the Dynamic Count Table.

The legacy IDK0/Score1000/panel scripts named in earlier notes are not present in this worktree or `origin/main`. Before this milestone, either import those scripts from a reviewed trusted source and immediately remove hard-coded counts, or implement the dynamic contract directly in this branch. The default is direct implementation from committed master, roster, and manifests. Do not concatenate old public sidecars as the public candidate source.

Required behavior:

- Backend clean/source/scored rows keep individual human rows.
- Active/excluded filtering joins the committed admission's `roster/model_roster.json` by model key. Checked-in `config/radle_v2_model_roster.json` is the validated baseline/schema input, not the authority after commitment. It must not infer current roster status from frozen final-master `access` or `domain` values.
- Human presentation mode is a required CLI/config choice: `pooled12` or `split6x6`; no backend rebuild.
- Public candidate ordering is human presentation rows first, active models descending Score2000, then excluded models descending Score2000 with `excluded=true`.
- Active panels include no excluded model.
- Score2000 equals Score1000+1000 for every comparator and sorting by either score is identical.
- Axis kink/compression is a rendering transform only. Exported Score1000/Score2000 values and rank are identical with the kink enabled or disabled.
- Status/count audits are recomputed from rows and terminal states, not constants.
- Panel display registries explicitly cover every active model. Missing label/category/logo/color/wrap rule fails before render.
- Candidate-public files omit diagnosis, ground truth, reasoning, raw response, image names/hashes, private paths, and raw provider errors.

Synthetic validation:

    $CommittedRoot = 'tests/tmp/m6_cli_output/<intake_id>/finalized/<finalization_id>'
    $SyntheticOut = 'tests/tmp/m6_cli_idk0_pooled12'
    py -3.11 scripts/radle_v2_incremental_admission.py build-idk0-lane --committed-root $CommittedRoot --output-root $SyntheticOut --human-presentation pooled12 --states config/radle_v2_terminal_states.json
    py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root $SyntheticOut --phase idk0-lane --no-write
    py -3.11 -m unittest tests.test_radle_incremental_admission -v

Expected counts are derived from the lane manifest. For the current synthetic replacement fixture, the committed final master has 2800 row-level score rows, 2 complete models, 1 active model, 1 excluded model, 12 human backend readers, 3 pooled12 presentation comparators, and 2 active panel comparators. Do not update expected values by eyeballing output.

Tests must also prove all signed scores for Likert 0..4, IDK0/invalid-zero, pooled human weight `1/12`, split human weight `1/6`, pooled/split derivation from the same 2400 human rows, and identical model rankings under Score1000 and Score2000.

For real panels, use SVG structural QA before screenshots. Then render desktop/contact-sheet outputs and verify no missing logos, overlap, clipping, stale model names, wrong comparator counts, or excluded arms.

### Milestone 7: External-results gate

This milestone is blocked while `PRE_M7_REPAIR_RESULT` is not `PASS`. The blocking repair contract and evidence live in `Documents/execplan_radle_v2_pre_m7_production_repair.md`. Downloading, inventorying, and sealing packages may happen in parallel, but `prepare` must not consume a real package before the repair gate passes.

Skill: `execplan` to update state; otherwise `none`.

Do not proceed to a real admission until each available package has:

- local immutable path;
- package tree inventory;
- SHA256 for every file and a package-level `SHA256SUMS`;
- final-wide manifest and matching final-wide hash;
- exact runtime branch/full SHA and notebook/run label;
- proof that it is 200 cases with `TEST_LIMIT=None`, not a smoke folder;
- recorded source shared-wide hash if projection is needed.

This is a hard stop, not a best-effort checklist. Smoke/test folders such as 5-case Grok/GPT or 1-case Muse runs are evidence only and cannot be admitted. A shared Grok/GPT wide result must first be projected into a one-model package with source-cell equality proof and its own checksum inventory. The worktree currently has no real package outputs, so no real admission can be validated until the operator downloads and seals them.

For incoming packages, `SHA256SUMS` excludes itself and any post-seal receipt, uses sorted POSIX-relative paths, and must explicitly list those exclusions in the package manifest.

If a downloaded Drive package has no `SHA256SUMS`, do not edit it in place. Copy it into a new immutable local intake directory, inventory every file, generate the sorted checksum file and `source_manifest.json` there, record the original download path and file hashes, and admit only the sealed local copy.

Record paths/hashes in this plan. If only Grok is available, proceed with Grok; do not wait for GPT/Muse. If a package is incomplete, classify it `pending_admission` and stop that transaction without changing the parent.

### Milestone 8: Grok 4.5 first real vertical slice

Skill: `data-analytics:validate-data` for independent count/hash reconciliation.

Run `project-one-model`, `prepare --dry-run`, `prepare`, judge dry run, paid judges only with confirmation token, radiologist queue/overlay, `finalize`, and independent `audit` in that order.

As of Milestone 2, this milestone has only config-level readiness. `grok_4_5` is Candidate AE and pending admission, but the commands and artifacts needed to make Grok the GPT parent do not exist yet: one-model package validation, scored long delta, judge/radiologist evidence, old-row immutability proof, `append_manifest.json`, final `COMMITTED.json`/`SHA256SUMS`, and post-admission independent review. Do not use the Milestone 1 runtime review receipt as this gate.

Expected after commitment, if no intervening admission:

    complete models = 19
    active models = 15
    complete long rows = 6200
    active Score1000 rows = 5400
    grok_4_5 = complete_master_active
    grok_4_3 = complete_master_excluded
    Candidate AE = grok_4_5

Generate a new dated IDK0 lane from this committed master. Do not overwrite the July 8 IDK0 lane.

Stop gate: a stronger-model/data review must sign off the append manifest, old-row immutability proof, score-source counts, and active/excluded roster before this becomes the parent for GPT.

The receipt is `review/first_admission_review.json` with reviewer model/identity, UTC time, committed finalization ID, append-manifest SHA, audit SHA, roster SHA, verdict `pass|fail`, and rationale. The mini executor cannot author its own passing receipt.

### Milestone 9: Replay for GPT-5.6 Sol Pro

Skill: `data-analytics:validate-data` for independent reconciliation.

Use the committed Grok master as parent and replay the same commands; do not add GPT-specific branches to generic admission logic beyond declarative roster routing rules.

Expected after commitment:

    complete models = 20
    active models = 15
    complete long rows = 6400
    active Score1000 rows = 5400
    gpt_5_6_sol_pro = complete_master_active
    gpt_5_5 = complete_master_excluded
    next available label, provisionally Candidate AF = gpt_5_6_sol_pro

### Milestone 10: Replay for Meta Muse Spark

Skill: `data-analytics:validate-data` for independent reconciliation.

Use the committed GPT master as parent and replay the same commands. Meta-specific client/provenance rules remain config, not scoring forks.

Expected after commitment:

    complete models = 21
    active models = 16
    complete long rows = 6600
    active Score1000 rows = 5600
    muse_spark_1_1 = complete_master_active
    next available label, provisionally Candidate AG = muse_spark_1_1

### Milestone 11: Candidate-public artifacts, panels, and final consolidation

Skills: `svg-panel-qa`, then `output-artifact-verifier`; `spreadsheets` only for any final XLSX review transport.

Generate sanitized candidate-public files from the latest committed master, not by concatenating old public sidecars. Include all complete-master model arms and a simple `excluded` flag. Keep panels active-only. Write a public manifest with source master hash, roster hash, sanitizer code hash, shapes/hashes, and `publication_approved=false` until a separate `privacy_approval.json` exists.

Public staging is a separate transaction under `outputs/radle_v2_stats/public_candidates/<source_master_sha256>/<public_candidate_id>/`. A failed privacy scan can quarantine only that public staging tree; it must not modify or invalidate the committed private admission.

The current local candidate/panel-source command is:

    $PublicOutput = @(py -3.11 scripts/radle_v2_incremental_admission.py build-idk0-lane --committed-root $CommittedRoot --human-presentation pooled12 --output-root outputs/radle_v2_stats/public_candidates/<dated_lane>)
    $PublicOutput | ForEach-Object { Write-Host $_ }
    $PublicLine = $PublicOutput | Where-Object { $_ -like 'IDK0_LANE_ROOT=*' }
    if (@($PublicLine).Count -ne 1) { throw 'IDK0 lane command did not emit one IDK0_LANE_ROOT' }
    $PublicCandidateRoot = ($PublicLine -split '=', 2)[1]

It emits `IDK0_LANE_ROOT=<absolute path>`. The row-level `score_rows.csv` contains backend model and human rows without diagnosis or ground truth. The comparator summary/table includes projected human rows and orders them humans first, active models by Score2000, then excluded models by Score2000. Summary outputs expose `excluded`; no excluded arm enters `panel_order.csv`.

Use explicit allowlists for public columns. Add a separate command:

    py -3.11 scripts/audit_radle_v2_incremental_admission.py --public-candidate-root $PublicCandidateRoot --phase privacy-scan

`privacy_scan.json` records source-master hash, roster hash, sanitizer code hash, file hashes/shapes, allowed columns, prohibited-column/text/path scans, and `RESULT=PASS`. Publication later requires `privacy_approval.json` with reviewer, UTC time, policy version, exact public manifest/hash, exact privacy-scan hash, and `approved=true`. Changing any source/public file invalidates approval.

Run structural and visual figure QA. Record generated paths and audit results. Do not upload or publish.

Finally review the clean branch diff, ensure all required evidence is durable, and make path-scoped commits. Do not delete old branches/worktrees merely because their pointers appear superseded. Retire them only in a separate cleanup decision after every needed blob and artifact is reachable from a durable ref.

## Validation And Acceptance

The complete project is accepted only when all of the following are true:

- A fresh machine/contributor can run synthetic tests without private data or API keys.
- Every real incoming package passes one-model schema, frozen case fingerprint, provider routing, manifest hash, and terminal-state gates.
- No new production code reads the previous-version `RadLE Stats` folder.
- Exactly one model's 200 rows are scored per transaction.
- Old rows remain byte-identical and key-order-identical through every committed master.
- Judge prompts and radiologist queues reveal no model identity.
- Every new row has one terminal state, a binary final score, and an auditable score source.
- No incomplete radiologist queue can be committed.
- Grok/GPT replacements change active roster only after final commitment; old arms remain retained and excluded.
- Muse adds one active arm.
- IDK0, Score1000, Score2000, public tables, and panel counts follow manifests and roster config.
- Score2000 shift and ranking invariants pass.
- Public candidate sanitization scans pass; publication remains separately approval-gated.
- All generated SVG/panel artifacts pass structural and visual QA.
- This ExecPlan's living sections accurately state the final branch, worktree, artifact paths, hashes, tests, known caveats, and next action.

## Idempotence And Recovery

- Read-only inspection and dry-run commands are safe to repeat.
- Generated transaction paths are content-addressed. Never reuse a path for different input hashes.
- All CSV/JSON writes use temporary files in the transaction staging directory followed by atomic rename.
- `COMMITTED.json` is the only commitment marker and is written last.
- A staging tree without `COMMITTED.json` is not a parent. Revalidate all hashes before resuming; otherwise rename it under `quarantine/` and start the same content-addressed transaction again.
- Judge JSONL is append-only and cache-keyed by model/prompt/input/context hashes.
- Radiologist overlays are immutable inputs once hashed. A correction creates a new overlay and therefore a new finalization attempt/manifest; it never edits a committed master.
- If any old-row hash fails, stop. Do not repair the generated output in place; identify the write-path bug, add a regression test, and rebuild from the unchanged parent.
- If a roster or blind-label collision appears, stop and allocate from the latest committed global map. Never relabel old rows.
- If a downstream audit fails, do not adjust expected counts to match output. Recompute the formulas from the committed roster and find the discrepancy.

## Artifacts And Notes

Record short literal proof here as execution proceeds:

    origin/main SHA: 3a8c38ea880c5fbdda5a418181703faadb53e3bb
    unified runtime SHA: 8029ad46d90b7bc8ab67af1e805ffaa2619b85a2
    implementation branch/worktree: codex/radle-v2-incremental-admission at C:/tmp/radle_v2_incremental_admission
    runtime preserve ref: refs/codex-preserve/morning-meta-8029ad46d90b
    planning document hashes: requirements=322751F4388E305D7B2BCA056A320F643FBC5F951663C4F2DE4CB27C995F098E; study=1CA43BE159B59042A01CCD6B939C4CCC8B71D03851684F621BE6E8E0599376ED; copied plan source hash before Milestone 0 update=268E391899DCFE3EECCDDC44CCF4D10E5C1B1B7F37FB20A9E1B80E815C6D604A
    runtime integration review: review/runtime_integration_review.json, SHA256 7E9DF6CD6E614BC46F19922DC9A7C6EC01CB0B079D8CB90F12CAFEDE2953376C, verdict pass
    runtime benchmark diff SHA256: dbeddb9ad3fdbc261733a313a7c9c48f8d5454270ae4bba5f46676b156d2ceec
    runtime worktree blobs: radle_benchmark=b8e0bbea69ce8dd01696495618cf1405838f16cf; meta_helper=511eaf27669c04db5451dca7a81c67c675585f7d; append_notebook=d5082d1d75005cf1c688e9ae320b38500359b5a3; meta_notebook=58a4774d9dd78cfb8a328b08e6329a5f1217dc02
    runtime validation: py_compile PASS; both notebooks json.tool PASS; model-name rg PASS; stale-ref rg PASS; provider/meta route probe PASS
    Milestone 2 config hashes: roster=2D6DCC6AEF35B1EB38E80D35A0F7407363D080A26119351FEC9AA27AE2EB122C; judges=E7EB33CE809EE30E593228B57641CF77186DB5E5EE060E08C69B85549DD6B3EC; terminal_states=129D3AB04FE4103E17460097C4116E5497D35654EF0E72ED0AE3BC24A2D37267; base_authority=4608DFAAC21EC7BC0435F15E7A8B6223B6FF250E6718CBFF6C8E718E9BB884E5; unit_fixture=C783A3EF23072FDA099C0AAE58EE14B70D9F9927EDB79CC3DBA8A8EDD96767B7
    Milestone 2 judge prompt/source: prompt_file_sha256=545989BB6BE331E469D05722F8437A2F88D6D6E381D64F345CB6C899D73458CE; source_script_git_blob=930ae988f1e0a33c068053e75bd4abe1b644fb7a; source_script_sha256=C1017B55826D6842E22D443B14FAECD5E4978CCE612D973DBEBD628AD2FF0A60
    Milestone 2 validation: py_compile PASS for src/radle_incremental_admission.py and scripts/radle_v2_incremental_admission.py; unittest PASS `Ran 4 tests`; check-config PASS with fixture_rows=11 and active/excluded/pending counts 15/3/3; prohibited live-path rg returned exit 1; JSON_PARSE=PASS; synthetic fixture generator emitted SYNTHETIC_FIXTURE_ROOT=tests\tmp\synthetic_admission; git add --dry-run showed static unit fixture addable and tests/tmp ignored; git ls-files --error-unmatch tests/fixtures/radle_incremental_admission/unit_cases.csv PASS; git diff --cached --check PASS
    checkpoint commit: fdbe56b Add RadLE v2 incremental admission foundation
    checkpoint commit: 18afdc5 Record incremental admission checkpoint state
    checkpoint commit: 99eb087 Implement prepared incremental admission staging
    checkpoint commit: d36938d Add synthetic dual judge routing
    Milestone 3 CLI dry-run: project-one-model printed PROJECTION_STATE=DRY_RUN_VALIDATED with row_count=200 and selected_field_count=19; prepare printed INTAKE_ID=5bce784a17cd85b17863c2578cfd5c571a5f297b00ce6200f5af7e8698351190 and TRANSACTION_STATE=DRY_RUN_VALIDATED
    Milestone 3 prepared audit: py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root tests/tmp/synthetic_admission/output_cli/5bce784a17cd85b17863c2578cfd5c571a5f297b00ce6200f5af7e8698351190 --phase prepared --no-write printed RESULT=PASS with row_counts new_model_long_delta=200, judge_worklist=194
    Milestone 3 validation: py_compile PASS for core/CLI/audit/fixture/tests; unittest PASS `Ran 10 tests`; check-config PASS; prohibited live-path rg returned exit 1
    Milestone 4 dry-run: py -3.11 scripts/radle_v2_dual_judge_delta.py --staging-root tests/tmp/synthetic_m4b/output/5bce784a17cd85b17863c2578cfd5c571a5f297b00ce6200f5af7e8698351190 --config config/radle_v2_judges.json --dry-run printed JUDGE_RESULT=DRY_RUN_VALIDATED, worklist_rows=194, base_calls=388, worst_case_http_requests=2328
    Milestone 4 synthetic run: same staging root with --synthetic printed JUDGE_RESULT=PASS, judge_result_rows=388, locked_agreement_rows=192, radiologist_queue_rows=3
    Milestone 4 judge audit: py -3.11 scripts/audit_radle_v2_incremental_admission.py --admission-root tests/tmp/synthetic_m4b/output/5bce784a17cd85b17863c2578cfd5c571a5f297b00ce6200f5af7e8698351190 --phase judge --no-write printed RESULT=PASS
    PRE_M7_REPAIR_RESULT=PASS: review/pre_m7_production_repair_review.json verdict pass; source/test patch SHA256 85A1E889184B0B9F0A4F76E67DB4009E412214B6BC675A31BA50D7EE00835232
    Pre-M7 repair validation rerun: check-base PASS before/after; check-config PASS; git diff --check PASS; full unittest discovery PASS `Ran 31 tests in 69.865s`; py_compile PASS for five modules
    Pre-M7 production-shape acceptance: root C:/tmp/radle_pre_m7_recheck_20260710_155032; acceptance receipt SHA256 8CDD1A5187952F13853327ED0EE3CF46B44FBF0C992A94EE325013372FB92047; finalization_id 0099659ca4b3c03f0bdbf9fe65a911959363073c9bd17093932cdd1ed09c8428; 6200 rows; 200 appended records; parent byte prefix true; network_calls=0; committed/idk0 pooled12/idk0 split6x6 readbacks PASS
    parent wide path/SHA/shape:
    parent final-long path/SHA/shape:
    roster manifest SHA:
    judge config/prompt SHA:
    synthetic test command/result:
    Grok package path/SHA:
    Grok admission ID/output SHA/audit result:
    GPT package path/SHA:
    GPT admission ID/output SHA/audit result:
    Muse package path/SHA:
    Muse admission ID/output SHA/audit result:
    latest IDK0 lane path/SHA/audit result:
    candidate-public path/privacy state:
    panel path/structural QA/visual QA:

## Interfaces And Dependencies

- Python version: use `py -3.11` consistently for implementation, tests, and wrappers. Record `py -3.11 --version` and the resolved interpreter path before implementation; do not mix the machine's default Python 3.14 with the existing 3.11 wrapper environment.
- Required Python libraries already used in this repo include standard library CSV/JSON/hash/path modules and `pandas`; tests should prefer the standard library where practical.
- OpenRouter is required only for real dual-judge calls. Credentials come from environment variables and are never printed or written.
- Morning/Meta runtime dependencies are separate from the local admission adapter. The adapter consumes sealed CSV/manifest packages and must not require Colab to run.
- Ground truth and variants are private scorer inputs. Candidate-model runtime code must have no path or argument for them.
- Ignored `outputs/`, `results/`, and `deliverables/` may contain authoritative private evidence. Git ignore status is not evidence of disposability.
- The new public-candidate sanitizer must use explicit allowlists, not a denylist.
