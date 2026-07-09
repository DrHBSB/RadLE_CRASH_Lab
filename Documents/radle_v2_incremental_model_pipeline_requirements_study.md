# RadLE v2 Incremental Model Pipeline Requirements Study

This is a living research ledger, not the implementation ExecPlan. It preserves the evidence, contradictions, decisions, and open questions needed to write a self-contained ExecPlan for repeatedly adding new model arms to the existing RadLE v2 comparator universe.

## Objective

Design an auditable, append-only path with this target shape:

    Morning or other approved runtime
      -> promoted final-wide model package
      -> isolated new-model long delta
      -> deterministic match / LLM judge / radiologist queue
      -> immutable scored append delta
      -> new materialized final-long-master sibling
      -> IDK0 Score1000 and Score2000 summaries
      -> panel-ready comparator data and figures

The immediate examples are Grok 4.5, GPT-5.6, and Meta Muse Spark. The contract must also support later API and local/open-weight models without re-scoring or mutating already-finalized rows.

## Current State

Current state (2026-07-10 03:19 +05:30, Codex): two read-only research waves are complete and consolidated below. The user has approved the active/excluded roster policy, append-only storage, independent one-model admission transactions, frozen historical scores, same-as-before judge models, full dual judging, private admission first, optional public generation after privacy approval, and conversion of the study into a requirements document. Grok 4.5 and GPT-5.6 should become active replacements for the previous/current Grok and GPT arms after admission; the replaced arms are simply excluded without special replacement-status complexity. Muse Spark should be admitted as an active contender after validation. Likert value `8` is resolved as invalid and scores zero.

Next action: document the pre-results implementation work that can proceed safely, draft the implementation ExecPlan from the requirements document, then revise the plan after new Drive packages are downloaded and hashed.

## Locked User Decisions

- New model additions are append-only within RadLE v2 unless the project explicitly moves to a future RadLE v3.
- A new API model enters through Morning or another approved runtime and becomes a new model arm; it is not inserted by manually editing the IDK0 or final-long-master CSV.
- Existing finalized model and human rows must remain immutable when a new model is appended.
- New Grok and GPT arms append to the complete master but replace the previous/current Grok and GPT arms in the active comparator roster after admission. The old Grok/GPT rows remain retained-but-excluded, like Opus and Grok 4.20.
- Muse Spark is intended to be added as an active contender after it passes the same full 200-case admission gates.
- Each model arm is one reader over the same 200 cases and has effective `N = 200`.
- Human readers remain separate in the backend. Presentation may use one pooled 12-reader human baseline or two human groups, chosen later without rebuilding adjudication data.
- The current IDK rule is IDK0: exact IDK, accepted typo-IDK, invalid response, and technical failure score zero.
- Invalid Likert values, including the observed `8`, are terminal invalid responses and score zero. They must be carried with explicit provenance rather than silently coerced.
- Score1000 uses Likert 0 through 4 mapped to magnitudes 1 through 5, positive when correct and negative when wrong.
- Score2000 is `Score1000 + 1000`; it changes display scale but not ordering or state.
- Model order is descending by Score2000, while selected human baseline rows remain visually first/left.
- The axis kink is display-only. It must not alter underlying Score1000 or Score2000 values.
- Adjudication has three tiers: deterministic accepted match, blinded LLM judging, and radiologist review for unresolved rows.
- The LLM judge models should be the same as the previous successful dual-judge workflow unless a later explicit decision changes them.
- Use full dual judging for new model rows that require judging; unresolved or discordant rows go to the radiologist queue.
- Radiologist queues include only unresolved rows and show only case number, blind candidate code, ground truth, candidate diagnosis, and Likert.
- Canonical normalized exact diagnosis matches auto-score correct without LLM judging.
- Judges may see ground truth and approved variants/context for non-exact rows, but never model identity.
- Approved ground-truth variants may be supplied to the scoring judge. They must not be supplied to the candidate model.
- Provenance, hashes, model routing, score sources, and reviewer decisions must remain auditable.

## Do Not Revisit Without New Evidence

- Do not propose direct column surgery into an IDK0 CSV or the authoritative final-long-master.
- Do not make the candidate model aware of canonical ground truth or accepted variants.
- Do not collapse human reader rows in the backend merely because a panel shows one pooled human comparator.
- Do not use the retired `weighted_score` calculation as Score1000.
- Do not treat ignored `outputs/` or `results/` folders as absent; they contain required provenance and lineage evidence.
- Do not merge stale branches wholesale into the current dirty branch.
- Do not use `C:/Users/thehb/Documents/RadLE Stats` as requirements evidence. The user confirmed it is the previous RadLE version, despite using the same images.
- Hash-pinned historical evidence already imported inside the current RadLE v2 repo remains admissible as a lower-priority evidence tier; live cross-repo paths remain prohibited.
- Final-binary scoring is third-opinion evidence only; its verified override count is 30.
- Temp/IDK0 sibling copies are not new finalized masters.
- Do not alter old finalized row order or values. Identity checks are key-based, but deterministic order is also part of the immutable materialized-master contract.
- `scripts/radle_v2_finalize_summaries.py` is not the radiologist-overlay finalizer.
- Never run concurrent Morning writers against the same `raw/results.csv`.

## Evidence Rules

- Prefer current files, manifests, hashes, schemas, and Git objects over chat recollection.
- Record exact paths, commit IDs, row counts, model rosters, and key uniqueness checks.
- Distinguish authoritative input, derived output, evidence sidecar, stale copy, and unknown-status artifact.
- Treat a manifest as evidence only for the artifact it actually hashes; do not infer package completeness from one file receipt.
- Any future new-model package must be validated before it is admitted to scoring.
- Contradictory evidence remains explicitly listed until reconciled; later evidence does not silently erase earlier facts.

Evidence precedence:

1. Current hash-pinned RadLE v2 authority, including promoted wide masters and finalized long masters.
2. Hash-pinned historical evidence imported inside this repo, with origin and unknown metadata recorded.
3. Judge-context-only or challenge-selected evidence that may inform review but cannot finalize automatically.
4. Prohibited live external dependencies and unverified transcript claims.

## Known Pipeline Topology

### Morning and runtime outputs

- `src/radle_benchmark.py` is the Morning model registry and benchmark source of truth.
- `notebooks/RadLE_v1_5_Morning.ipynb` is a runner over that module.
- Morning run roots contain `raw/results.csv`, `repair/repaired_results.csv`, `final/RadLE_v2_results_final.csv`, `scorer/scorer_view.csv`, and optionally `public_release/` artifacts.
- `scripts/radle_append_results.py` can combine promoted model packages and derive scorer data from the combined final-wide file.
- A promoted final-wide file, not a raw or stale scorer view, is the intended scoring input.

### Scoring and adjudication

- `scripts/radle_v2_stats.py` converts wide `Diagnosis_<model>` and companion columns into long case-model rows and scoring worklists.
- `scripts/radle_llm_judge.py` supports model-filtered judging but does not by itself implement immutable carry-forward into a new authoritative master.
- Historical dual-judge and radiologist-finalization paths exist and are under renewed study.
- The missing central adapter is: isolate only new model rows, carry old finalized rows unchanged, adjudicate only score-required new rows, and materialize a new complete sibling master.

### Verified RadLE v2 scoring lineage

- `scripts/radle_v2_stats.py` discovers wide `Diagnosis_<model_key>` families and produces a 26-column long table. Current `score_required` means valid, non-abstained response; normalized exact ground-truth matches are not currently removed from the worklist.
- Its scoring worklist has 25 columns and blank score/judge/review fields. `--only-score-required` excludes abstentions and failures, not exact matches.
- `scripts/radle_llm_judge.py` passes only ground truth, candidate diagnosis, and Likert to the judge and applies results by `(run_id, Master_Case_ID, model_key)`. Safe-copy is its default posture.
- `scripts/radle_dual_judge_review.py` implements auto-zero, deterministic prior lookup, dual-judge agreement, and `NEEDS_REVIEW`, but its deterministic-prior source is the now-excluded previous-version repository and is therefore not portable RadLE v2 evidence.
- `outputs/radle_v2_stats/radle_v2_dual_judge_scored_combined_with_codex_v2.xlsx` contains a 6000-row scored sheet, 101 unresolved rows, and 102 suggested-review rows. Codex/Claude columns in that workbook are recommendations, not final human scores.
- The radiologist finalization precedence was radiologist verdict, then existing locked score, otherwise block. The resulting 6000-row final master has no duplicate `(Master_Case_ID, model_blinded)` keys.
- Final authoritative scores are `0 = 4745` and `1 = 1255`.
- Final score sources are `ai_judges = 3788`, `human_prior = 1063`, `auto_score_not_required = 946`, and `radiologist = 203`.
- The 203 radiologist rows exactly cover the 101 unresolved plus 102 suggested-review keys. Radiologist review filled all unresolved rows and changed 53 suggested rows: 48 from zero to one and five from one to zero.
- The archived Codex-only scoring lane is evidence, not final authority. Its audit and shard comparison support 30 overrides; the old final-binary ExecPlan statement of 32 overrides is stale.
- `scripts/build_radle_v2_temp_final_scoring_version.py` already demonstrates source-SHA, schema, row-count, key-uniqueness, and binary-score gates for an unchanged sibling copy.
- `scripts/build_radle_v2_clean_adjudication_master.py` demonstrates preservation of row order and non-derived values while removing only retired `weighted_score`.

### Score1000, IDK0, and panels

- The current source final-long-master has 6000 rows representing 30 candidate/reader arms across 200 cases.
- The current active Score1000/IDK0 cohort has 5400 rows: 3000 non-excluded model rows plus 2400 human-reader rows.
- Current IDK0 outputs are production-like after the finalized long master exists, but scripts still contain fixed row, model, comparator, roster, and display assumptions.
- Adding one included 200-case model should produce a 6200-row complete master and a 5600-row active Score1000 cohort, subject to roster approval and exact exclusion rules.

## Current Branch and Checkout Map

Preliminary observations to be independently verified:

| Ref or checkout | Observed purpose | Preliminary status |
| --- | --- | --- |
| `origin/main` at `3a8c38e` | Includes roster-agnostic final-wide combiner | Candidate clean consolidation base |
| `codex/radle-v2-handwritten-panels` at `8c9de27` | Current heavily dirty Score1000/IDK0/panel checkout | Preserve; do not branch-switch casually |
| `codex/grok45-morning-smoke` at `1faee5a` | Grok 4.5 registry, routing, smoke, Morning append guard | Port surgically after lineage review |
| `codex/gpt56-openrouter-smoke` at `8feeb7b` | Newer Grok/GPT Morning append work | Active adjacent evidence |
| `codex/meta-muse-spark-colab` at `e4f2e84` | Meta Muse Spark smoke/runtime work | Active adjacent evidence; branch advanced during this study |
| `codex/morning-meta-muse-spark-append` at `49bf0d6` | Unified serial Morning append for Grok, GPT-5.6, and Meta Muse Spark | Current clean pushed integration head in `C:/tmp/radle_morning_meta_append` |
| `codex/llava-vllm-runtime` / `codex/final-scoring-csv-questions` | Older runtime and scoring lineage | Historical; do not merge wholesale |
| `C:/Users/thehb/Documents/RadLE v2 - final scoring questions` | Git-linked sibling checkout | Historical scoring evidence under study |
| `C:/Users/thehb/Documents/RadLE v2 - grok45 push` | Git-linked sibling checkout | New-model branch evidence under study |

## Branch Consolidation Findings

First-wave branch audit, verified read-only on 2026-07-10:

    080ec65  local main
    |-- 2d1028c stats-combiner fix
    |   `-- 3a8c38e origin/main merge
    `-- shared runtime history through 071d6ec
        |-- 0931b0c -> 56a882b -> 8c9de27 handwritten
        |   `-- Meta Muse Spark development -> e4f2e84
        `-- Grok commits -> 1faee5a
            `-- GPT-5.6 commits -> 8feeb7b
                `-- unified Meta Morning port -> 49bf0d6

The current relevant committed heads are `origin/main@3a8c38e`, the unified runtime head `codex/morning-meta-muse-spark-append@49bf0d6`, and the separate Meta development head `codex/meta-muse-spark-colab@e4f2e84`.

### Retain before consolidation

- `origin/main@3a8c38e`, including the already-merged roster-agnostic append combiner from `2d1028c`.
- The shared runtime line through `071d6ec`, subject to path-level review rather than blind branch merge.
- `0931b0c`, which adds the seven-file final-scoring stats pipeline.
- `codex/morning-meta-muse-spark-append@49bf0d6`, which descends from `8feeb7b` and therefore contains all Grok and GPT-5.6 commits, then adds nine commits for Meta runner evidence and unified Morning dispatch.
- The five net paths added after the GPT head: Meta ExecPlan, Meta Colab notebook, unified three-model Morning notebook, `src/radle_meta_model_api_runtime.py`, and the Meta dispatch change in `src/radle_benchmark.py`.
- The separate Meta sequence `3f17f03..e4f2e84` as development history until its final blobs are proven equivalent to the unified port.
- The primary checkout's uncommitted Score1000, IDK0, handwritten-panel, asset, and document payload. Most of that implementation is not represented by the current branch tip.
- The untracked `Documents/execplan_radle_arxiv_stats_story.md` in the final-scoring worktree, if it remains useful; it is not reachable from any branch.
- The working Morning notebook's scorer-view rebuild from repaired final, which is not present on the GPT branch.

### Superseded branch pointers after safe retention

- `fix/stats-combiner-scorer-from-final` is already merged into `origin/main`.
- `codex/grok45-morning-smoke` is contained by `codex/gpt56-openrouter-smoke`.
- `codex/gpt56-openrouter-smoke` is contained by `codex/morning-meta-muse-spark-append`.
- `codex/final-scoring-csv-questions` aliases the older remote runtime tip.
- Local `codex/llava-vllm-runtime` and `codex/radle-v2-handwritten-panels` become removable pointers only after their unique commits and uncommitted paths are reachable from durable refs.

### Semantic merge hazards

- `56a882b` is a mixed 34-file bulk commit. Its combiner blob is already identical to the one on `origin/main`, while its other notebooks, docs, hunt scripts, and board artifacts require individual decisions.
- `8c9de27` deletes 26 GoalBuddy files. Accepting Meta's ancestry wholesale also accepts those deletions.
- The primary worktree had 54 staged, 18 unstaged, and 19 untracked paths at audit time. It is not a safe place to perform consolidation.
- The untracked Grok smoke notebook in the primary checkout is stale because it still pins `codex/llava-vllm-runtime`; the committed branch copy has the correct Grok branch pin.
- The working `src/radle_benchmark.py` matched the Grok tip but lacked GPT-5.6, while the working Morning notebook was Grok-only plus the scorer rebuild.
- Merge-tree probes found no textual conflicts among the major heads. That does not make whole-branch merges semantically safe.

### Future consolidation posture

1. Preserve the primary and final-scoring worktree payloads with reviewed path-scoped commits or durable backup refs.
2. Create a separate clean integration worktree from `origin/main@3a8c38e`; do not consolidate inside the dirty primary checkout.
3. Bring forward the required runtime foundation and `0931b0c` deliberately.
4. Review `56a882b` path by path and adjudicate the `8c9de27` deletions explicitly.
5. Integrate `codex/morning-meta-muse-spark-append@49bf0d6` as the current Grok-plus-GPT-plus-Meta runtime head, then reapply only the working scorer-view rebuild.
6. Compare its five Meta-related path blobs against `e4f2e84`; retain the separate Meta history only where it contains non-equivalent evidence.
7. Validate notebook JSON, branch pins, Python compilation, model registries, and the complete integration diff.
8. Retire aliases and remove worktrees only after every retained artifact is reachable from a durable ref.

The Meta branch moved from `e782649` to `e4f2e84`, and the unified Morning branch appeared at `49bf0d6`, while this study was running. Requirements and the eventual ExecPlan must snapshot full branch SHAs at execution time rather than relying on branch names alone.

## Current Artifact Contradictions

These are requirements-driving facts, not yet reconciled:

- Local `results/radle_v2/raw/results.csv` and `scorer/scorer_view.csv` previously exposed 13 model families, while `repair/repaired_results.csv` and `final/RadLE_v2_results_final.csv` exposed 10.
- `results/radle_v2_combined/final/RadLE_v2_results_final.csv` previously exposed a larger 18-model roster, but its manifest and package completeness did not yet prove it was the authoritative scoring base.
- The current finalized long master contains a scored candidate universe that is not automatically synchronized with every model family found in wide result folders.
- Current Score1000/IDK0 scripts validate fixed historical counts. Those checks are useful integrity gates but are not append-safe requirements.
- The IDK0 wrapper passes `--idk-score 0`, while direct script defaults may still be `1`; invocation safety depends on the wrapper.
- Existing final/public/scorer package completeness guarantees differ between promotion and append paths.
- `scripts/radle_dual_judge_review.py` currently points its human-prior lookup at the previous-version `RadLE Stats` folder. The future adapter must eliminate that live path. The repo-local hash-pinned reference may be retained only under the approved imported-evidence tier; otherwise prior reuse is disabled.
- The source radiologist workbook, the actual merge implementation, reviewer rationales, and the expected `final_scoring_audit.json` are not preserved in the current v2 roots. `scripts/write_audit.py` still refers to a file under `C:/Users/thehb/Downloads/`.
- The current final master contains one contradictory radiologist-reviewed normalized pair: case 164, diagnosis `diffuse esophageal spasm`, is labeled both zero and one for identical normalized text.

## Model Package Universe

The active `results/` tree contains 426 files: 358 checkpoint backups and 68 active package files. Nineteen model families have some result rows; Grok 4.5 and GPT-5.6 Sol Pro are configured in an adjacent worktree but have no downloaded local results yet.

### Package-level assessment

| Package root | Layer/roster state | Assessment |
| --- | --- | --- |
| `results/radle_v2` | raw 13; repair/final 10; scorer 13; no public | Internally inconsistent; not the complete response base |
| `results/drive_sources/radle_v2` | raw/final 13; repair 10; scorer 13; public only three models | Drive final equals raw rather than repaired output |
| `results/radle_v2_combined` | final-wide 18 only | Complete response roster, incomplete package/provenance |
| `results/claude_fable_5_full_200_cases` | raw/final/scorer/public | Complete standalone package |
| `results/medgemma_1_5_4b_medical_full_200_cases` | raw/repair/final/scorer/public plus runtime provenance | Strongest standalone package |
| InternVL and OctoMed packages | raw/final/public; no scorer | Response-complete but package-incomplete |
| Lingshu package | raw/final/public plus repair logs; no scorer | Response-complete; one documented invalid Likert path |
| LLaVA-Med package | final/public only | Not roster-ready: 184 malformed plus 16 invalid-Likert public rows |

### Response and scored authorities

- Use `results/radle_v2_combined/final/RadLE_v2_results_final.csv` as the private authoritative 18-model response base, while explicitly labeling it package-incomplete.
- All 13 base model families in that combined file exactly match `results/radle_v2/raw/results.csv`.
- The five appended families exactly match the standalone Fable, MedGemma, OctoMed, InternVL, and Lingshu promoted finals.
- The combined manifest verifies the final output hash but records only the final Lingshu append and an ephemeral temporary base path. It does not prove the full merge chain.
- The combined package has no raw, scorer, or public companions. Scorer coverage exists for 12 of the 15 active models and public coverage for only eight.
- Public manifests list files and privacy notes but do not hash the exports.
- Use the 6000-row July 6 final long master as the authoritative scored base. It contains the same 18 model families, and every diagnosis and numerically normalized Likert matches the combined response base.

### Proposed pre-append roster

Active official comparator candidates, 15 arms:

    gpt_5_5
    claude_fable_5
    gemini_3_1_pro
    grok_4_3
    qwen_3_7_plus
    glm_5v_turbo
    gemma_4_31b
    llama_4_maverick
    mistral_large_3_2512
    minimax_m3
    nemotron_3_omni
    internvl3_5_8b
    medgemma_1_5_4b
    octomed_7b
    lingshu_32b

Present in the complete master but explicitly excluded from active Score1000 comparison:

    claude_4_8_opus
    grok_4_20
    glm_4_6v

LLaVA-Med is not roster-ready. Grok 4.5, GPT-5.6 Sol Pro, and Meta Muse Spark remain pending model arms until their downloaded packages pass the same 200-case admission gates. Per the user's append-only decision, admission adds a new complete-master arm rather than overwriting an existing row family.

Roster replacement rule approved by the user on 2026-07-10:

- When `grok_4_5` is admitted, it becomes the active Grok comparator and the previous/current Grok active arm becomes retained-but-excluded.
- When `gpt_5_6_sol_pro` is admitted, it becomes the active GPT comparator and the previous/current GPT active arm becomes retained-but-excluded.
- This replacement changes active roster membership, not historical data. Existing rows, scores, columns, and files remain frozen.
- Use simple exclusion flags for older arms; do not create unnecessary replacement/deprecation status layers or exclusion-reason machinery.
- `muse_spark_1_1` is intended as an additional active contender after full 200-case admission, so the active model count increases by one after Grok/GPT replacement plus Muse admission.

### Package requirements exposed by this inventory

- A roster manifest must explicitly distinguish complete-master arms, active comparator arms, excluded arms, pending arms, and rejected/incomplete experiments. Do not add replacement/deprecation status unless the user asks for it later.
- A model cannot be admitted merely because a final manifest hash matches; semantic validity and companion-package completeness are separate gates.
- Every append must record the full ordered merge chain, not only the most recent incoming package.
- Final-wide, scorer, and public artifacts must all be regenerated from the same promoted final SHA and checked for exact model-roster agreement.
- Public exports and manifests must include content hashes and expected `200 * model_count` unique case-model rows.
- Public candidate exports include all complete-master models, including excluded old arms, with a simple `excluded` flag. Panels show active contenders only.
- Checkpoint backups remain recovery evidence but must not be counted as active package members.

## Normalized Incoming Model Contract

Grok 4.5, GPT-5.6 Sol Pro, and Meta Muse Spark can share one normalized append-input schema because all ultimately use `radle_benchmark.run_benchmark()` and its common result columns.

Required case keys:

    Master_Case_ID
    Associated_Images
    Image_SHA256

Required 16-column family for each model key `{k}`:

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

A one-model incoming CSV therefore has exactly 19 columns. A combined Grok-plus-GPT incoming CSV has 35. Although the current appender can work from fewer columns, model admission should require the complete family. The normalized incoming file must contain no historical model families or unrelated non-key columns.

### Model-specific provenance rules

| Model key | Required evidence |
| --- | --- |
| `grok_4_5` | Requested `x-ai/grok-4.5`; `Actual_Request_Extra.provider.only = ["xAI"]`; fallbacks false; provider `xAI`; returned model matches `x-ai/grok-4.5*`; fallback-used false |
| `gpt_5_6_sol_pro` | Requested `openai/gpt-5.6-sol-pro`; reasoning effort high; OpenAI-only routing; provider `OpenAI`; returned model matches `openai/gpt-5.6-sol-pro*`; fallback column blank |
| `muse_spark_1_1` | Separate Meta OpenAI-compatible client; model `muse-spark-1.1`; max output 2048; temperature suppressed; provider `Meta Model API`; request-extra normally null; fallback column blank |

`OpenRouter_Response_Model_*` remains the common historical returned-model column name even for the Meta route.

### Expected Drive artifacts

Smoke folders are evidence only and cannot be admitted as full runs:

    Runs/grok45_test_5_cases/
    Runs/gpt56_sol_pro_test_5_cases/
    Runs/muse_spark_1_1_meta_muse_spark_1case/

Expected full package:

    raw/results.csv
    raw/backups/results_BACKUP.csv
    repair/repaired_results.csv
    repair/repair_plan.csv
    repair/repair_call_log.csv
    final/RadLE_v2_results_final.csv
    final/RadLE_v2_results_final_manifest.json
    scorer/scorer_view.csv
    public_release/RadLE_v2_public_model_results.csv
    public_release/RadLE_v2_public_model_summary.csv
    public_release/RadLE_v2_public_sanitized_call_log.csv
    public_release/RadLE_v2_public_manifest.json

Repair files and sanitized call log are conditional when no repair occurred, but the manifest must state their absence explicitly.
Public-release files may be absent from a private-only Drive intake; their absence does not block private scoring admission.

Grok/GPT full output is currently designed to append into `Runs/radle_v2/`. Before package admission, project that wide file to the three keys plus only the new model families. Never use `--replace-existing-model` to force an unprojected historical-wide file through the adapter. Meta should use a new full-run label; changing `TEST_LIMIT` to none while retaining the one-case smoke label is not acceptable.

### Incoming admission gates

1. Record exact branch and full commit SHA; require `TEST_LIMIT = None` and a non-smoke run ID.
2. Verify the final manifest hash against the promoted final-wide CSV.
3. Require the exact base case-ID set: 200 unique, nonblank cases with no duplicates.
4. Require exact `Associated_Images` and `Image_SHA256` agreement with the base; do not waive metadata mismatch.
5. Discover exactly the intended model keys and complete column families; reject unprojected historical columns.
6. Require every case-model cell to be in an accepted terminal state, with zero unresolved repair targets. Invalid Likert values, provider blocks, parse failures, and retry exhaustion may be terminal invalid-zero states only when explicitly classified and provenance-recorded.
7. Validate provider, returned-model, and request-extra evidence against the model-specific rules.
8. Rebuild scorer output from the promoted final rather than trusting an incoming stale scorer after repair.
9. Run the appender dry-run. Public tables are a separate optional publication gate, not a prerequisite for private scoring admission.

At current branch tips, no branch contains saved run CSVs or manifests and all three notebooks have zero stored outputs. Smoke claims in ExecPlans remain transcript evidence until the Drive artifacts are downloaded and hashed locally.

## Private Admission Transaction

Admit one future model as an immutable private delta package, then derive a new versioned combined wide master. Never append directly into the existing unversioned file.

### Required private package

| File | Contract |
| --- | --- |
| `final/RadLE_v2_results_final.csv` | Exactly 200 rows, 19 columns, one model family |
| `final/RadLE_v2_results_final_manifest.json` | Final/source hashes, model identity, frozen-dataset identity, promotion state |
| `audit/promotion_audit.json` | One terminal-state record per case plus aggregate counts and approved exceptions |
| `provenance/source_manifest.json` | Raw source, runtime, prompt/config, repair and adjudication lineage |
| `SHA256SUMS` | Lowercase SHA256 for every packaged file using sorted POSIX-relative paths |
| `repair/*` or `adjudication/*` | Conditional but mandatory when promotion was not clean |

A submitted scorer is never authoritative; admission generates it from the promoted final. Backups and runtime logs are optional, but the raw source must be packaged or available at an immutable private URI with a verified hash.

The package manifest needs at least:

- `schema_version`, immutable `run_id`, model key/id/revision/provider/runtime/quantization;
- prompt and generation-config hashes;
- dataset snapshot ID, transfer/file manifest hashes, case count, image count, and case-triplet hash;
- promotion state `clean|repaired|normalized|exception_approved`, source label/hash, initial/final audit hashes, conditional repair/adjudication hashes, and exception references;
- final path/hash/shape and a model-family hash.

Frozen dataset anchors currently verified:

    snapshot_id = radle-v2-frozen-2026-06-29
    transfer_manifest_sha256 = 1654067c323bf664967b73c14938d094b066d278d976b7dde05e2bd489225884
    file_manifest_sha256 = cca42f1699d9661e72cbef34656dbddb1b59db48d9673f61b29aad60a78fc135
    case_count = 200
    image_count = 263
    case_triplet_sha256 = d65221a441c5687cd44d11df689072969d6bbe69089ab0eacaf84cb69ab28dd7

The case-triplet fingerprint is SHA256 over numeric-case-sorted compact JSON arrays `[Master_Case_ID, Associated_Images, Image_SHA256]`, encoded UTF-8 with one LF-terminated array per case.

### Admission behavior

1. Integrity: every listed artifact exists and matches `SHA256SUMS`; manifests use package-relative paths or immutable URIs, never temporary absolute paths.
2. Case set: IDs are exactly 1 through 200, unique and nonblank; all case metadata matches the frozen fingerprint and 263-image manifest. Metadata overrides are forbidden.
3. Schema: exactly one diagnosis family and all 16 companion columns share one model key.
4. Roster: derive the base roster from the 18 ordered `Diagnosis_*` columns in the current 200x291 combined wide master. Live code registries are supporting identity evidence, not roster authority.
5. Promotion: each incoming cell is either a committed diagnosis with integral Likert 0 through 4, canonical `I don't know` with blank Likert, or an explicit invalid-zero terminal state. Blank diagnosis, parse marker, provider failure, or invalid Likert must not be silently coerced; if accepted after repair exhaustion, it is classified as invalid and scores zero.
6. Repair: require immutable initial audit, exact target list, bounded attempt log, source/repaired hashes, and a diff proving only planned incoming cells changed. Normalization/adjudication requires per-cell before/after value, source-cell hash, rationale, approver, and script hash.
7. Merge: all existing 291 columns and values remain identical and ordered; append the 16 incoming columns. The result is 200x307 with 19 model keys.
8. Scorer: derive a 200x40 projection with the two scorer keys followed by ordered diagnosis/Likert pairs. Exact strings must equal the promoted master.
9. Legacy state: freeze historical exceptions already present in the base. Admission may not alter or increase them; strict new gates apply to the incoming family.

The repo-local historical scoring key has the same 200 IDs but 75 metadata-cell differences from the frozen/current case set. It may supply scored evidence under its own hash but must not be used as metadata authority.

Existing scorer drift confirms why this gate matters: `results/radle_v2/scorer` differs from its repaired final in 20 diagnosis/Likert cells. MedGemma demonstrates correct repaired promotion; the Drive-source base demonstrates stale promotion where final still equals raw; Lingshu and OctoMed demonstrate why exceptions and deterministic cleanup need machine-readable lineage.

### Idempotence and recovery

Define:

    admission_id = SHA256(
      "radle-admission-v1\n" +
      base_master_sha256 + "\n" +
      incoming_final_sha256 + "\n" +
      package_manifest_sha256 + "\n"
    )

Write the delta under `admissions/<admission_id>/` and the resulting master under `masters/<output_final_sha256>/`. Generate inside `.staging/<admission_id>/` and write `COMMITTED.json` last. The existing master is never overwritten.

- Identical committed admission: `ALREADY_ADMITTED`.
- Existing identical model family and manifest: `ALREADY_PRESENT`.
- Same model key with any differing family or manifest hash: hard collision.
- Replacement requires a separate approved supersession transaction; normal admission forbids replace, metadata-mismatch, and overwrite flags.
- A staging directory without `COMMITTED.json` is non-authoritative. Resume only after revalidating every hash; otherwise quarantine it.

### Optional public package

Generate publication artifacts from the admitted combined master, never by concatenating standalone public sidecars. Require a public manifest containing source-master hash, ordered model keys, file hashes/shapes, score state, sanitization-tool hash, and explicit privacy approval with reviewer/time/policy/scan hash.

A full 19-model public release has 3800 unique `(run_id, case_uid, model)` rows. Public candidate files should include all complete-master models and a simple `excluded` flag so excluded arms are preserved in tables without entering active panels. Diagnosis text, reasoning, raw responses, image names/hashes, private paths, and raw provider errors remain prohibited. A sanitized call log is required when repairs occurred.

## RadLE v2 Variant Evidence

No governed accepted-variants or alias table currently exists. The defensible RadLE v2 seed is the 203 rows with `final_score_source = radiologist` in the current final master:

- 155 unique `(Master_Case_ID, normalized diagnosis)` pairs across 67 cases.
- 154 pairs have one consistent radiologist outcome: 70 accepted and 84 rejected.
- All are non-exact under the current dual-judge normalizer.
- Case 164 is contradictory and must not seed automation until re-adjudicated.
- Pair-level review would have reduced 203 row packets to 155, saving 48 packets or 23.6%, without any semantic alias expansion.

This is a challenge-selected subset, not a representative sample of all 200 cases. It can seed equivalence and boundary rules but cannot estimate overall automatic-scoring accuracy by itself. Both accepted and rejected near-match evidence should be retained.

Case 164 has reference `corkscrew esophagus with diverticulum` and six reviewed occurrences of normalized response `diffuse esophageal spasm`. Candidates A/C/E received zero and F/T/U received one despite identical case, images, reference, and normalized diagnosis. This is a scoring contradiction, not a variant distinction. Quarantine the pair and resolve it once, preferably with two independent radiologists and a tie adjudicator.

The current-repo imported reference at `results/reference/RadLE_RSNA_Diagnosis_Scoring_key.csv` is in scope as hash-pinned historical evidence even though the live `RadLE Stats` sibling is excluded. It has 2000 scored cells, 1546 normalized pairs, one conflict, and SHA256 `5D26771DA27CF8FEF1A7F48204257C65B8E1F7B41423763F2E45CB384FB738D4`.

Only 20 of the 155 v2-reviewed pairs overlap that imported prior. Two are conflicts; among the other 18, only seven agree and 11 disagree. This challenge-selected overlap is not an error-rate estimate, but it rules out treating imported V1 decisions as unconditional authority. They may be a versioned `imported_v1_prior` evidence tier only with explicit user approval, unknown reviewer/rubric metadata recorded as unknown, and precedence below v2 evidence.

### Conservative match classes

| Class | Meaning | Current action |
| --- | --- | --- |
| `canonical_exact` | Candidate safely normalizes exactly to the canonical reference | Auto-accept after normalizer validation |
| `v2_reviewed_exact` | Exact case-specific pair with one consistent v2 verdict | Prospective reuse; initially shadow-review accepted entries |
| `imported_v1_prior_exact` | Exact pair supported only by hash-pinned imported V1 evidence | Judge context only |
| `surface_equivalent` | Case, whitespace, punctuation, or hyphen change with unchanged tokens | Calibrate on held-out cases before automation |
| `curated_clinical_alias` | Synonym, acronym, or eponym explicitly approved by radiologist | Judge context only until prospective validation passes |
| `mandatory_review` | Conflict, broadening/narrowing, subtype, anatomy, laterality, negation, or compound-diagnosis issue | Radiologist only |

No fuzzy matching, edit-distance threshold, embedding similarity, or LLM-generated alias may directly auto-accept.

### Calibration requirements

- Freeze 47 of the 67 reviewed cases for development and 20 as untouched holdout, stratified by outcome, multiplicity, and source.
- Never split duplicate rows from one case across development and holdout.
- Freeze the matching policy before receiving the next model's outputs and keep model identity out of matching.
- Initially send every proposed auto-accept to blinded radiologist shadow review.
- Require zero false accepts and a one-sided 95% upper confidence bound no greater than 1% before enabling a broader class. Seventy accepted pairs with zero observed errors still imply an upper bound around 4.2%, so present evidence is insufficient.
- Any false accept quarantines the entry and related rule and triggers replay of affected rows.
- Do not rescore the frozen existing master from a variants table derived from that same master. Reuse is prospective only.

A governed release should use three append-only artifacts:

    policy_release:
      policy_version, status, normalizer_version, normalizer_code_sha256,
      source_artifact_hashes, split_manifest_sha256, approval identity/time

    variant_entry:
      entry_id, policy_version, case_id, image_sha256,
      raw/normalized reference and response, evidence_tier, match_class,
      scope, decision, automation_action, conflict/approval states,
      effective dates, supersedes_entry_id

    variant_evidence:
      entry_id, blinded source-row key, review sheet, source score,
      artifact hash, reviewer pseudonym, review time, rationale

Unique constraint: `(policy_version, case_id, image_sha256, normalizer_version, response_norm)`. Case 164 remains a conflict entry with six evidence rows and no automated action.

## Authoritative Artifact Ancestry

Verified first-wave ancestry:

| Stage | Classification | Exact anchor | Meaning |
| --- | --- | --- | --- |
| Combined blinded input | Authoritative pre-scoring input | `outputs/radle_v2_stats/long_format_diag_likert_blinded_combined.csv`, 6000x11, SHA256 `607FAE4D339054EF6F2587895292239C2A7675FB85633B4E32566BC272EF272B` | Fed both scoring branches; unique case/blind-label keys |
| Blinding key | Authoritative identity map | `outputs/radle_v2_stats/blinding_key_blinded_combined.csv`, 30x3, SHA256 `09EBF4562EB541B59930930C70D5D6D1E3AF76373C49EA1F4F17C1AB471AB633` | Maps the 30 model/human arms |
| Final-binary archive | Historical third-opinion evidence | `_stale_archive/final_binary_scoring_20260705_010315/`; blinded output SHA256 `7707FC441B5E819AAB29AFCF021E79AB6BB88EF6064F0B5C21E3D25D89C7DB70` | Not a direct ancestor of final correctness; used for Codex third-opinion/review routing |
| Dual-judge workbook | Historical finalization base | `radle_v2_dual_judge_scored_combined_with_codex_v2.xlsx`, SHA256 `0932375709B6222609D5FAD25CEA9250E96460DAE59E4748B8337E7280CCFDBA` | Contains the 6000 scored rows plus 101 unresolved and 102 suggested-review rows |
| Radiologist overlay | Authoritative finalization input with unresolved caveat | `C:/Users/thehb/Downloads/Radiologist Review.xlsx`, 203x12, SHA256 `8AF96E1E349DCD6A562F86289A6F6A09434DE609E999C116D4A9059CE2E1D90D` | Covers the 203 review keys after normalizing 17 `Model_X` labels to `Candidate X`; currently outside the repo/package |
| Final long master | Global authoritative correctness table | `final_scoring_radiologist_20260706_001147/radle_v2_final_long_master.csv`, 6000x20, SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED` | Authority for `final_score_authoritative` and `final_score_source` |
| Clean adjudication master | Canonical Score1000 input | 6000x19, SHA256 `F49AE40BFC99F77DA5C966F33C16D57778331DAC28F4C318B4158116B0859D87` | Removes only retired `weighted_score` |
| Original Score1000 lane | Valid historical derivation | July 6 `likert5_score1000/` | IDK earns +1; humans presented as two six-reader groups |
| Current IDK0 lane | Current production downstream derivation | July 8 `likert5_score1000_IDK0/` | IDK earns zero; humans pooled as 12-reader baseline; Score2000 is display-only |

The final-binary scores disagree with the final master on 86 rows and must never be promoted as authoritative correctness. They are third-opinion evidence only.

The July 8 IDK0 top-level master and clean master are byte-identical to the July 6 authoritative files. The IDK0 folder is therefore a new downstream scoring/presentation lane, not a new final-scoring version. A new model requires a genuinely new complete final master before an IDK0 lane is created.

### Finalization gaps to repair

- The checked-in finalization generator is absent. `scripts/radle_v2_finalize_summaries.py` adds seniority fields and changes 600 human-role rows; it did not perform the original radiologist merge.
- The radiologist workbook contains three `Radiologist_final_score = 8` values. The final master stores zero for all three, retains their prior locked zero, and labels the source `radiologist`. No surviving merge code or audit proves whether this was intended fallback or accidental coercion.
- No `final_scoring_audit.json` survives in the checked v2 roots.
- Future finalization must normalize `Model_X` to `Candidate X` explicitly, reject every score outside `{0,1}`, preserve the overlay workbook inside a sealed package, and write a manifest covering every input/transformation/output hash.
- Obsolete workbooks include the 3600-row dual-judge predecessor and the first `with_codex` workbook whose suggested-review sheet has only 17 columns. The `with_codex_v2` workbook is the complete historical review base.
- The `before_state_score1000_net_score_IDK0_20260708_183000` snapshot is stale and cites a scored-row hash that is no longer active.

The three invalid overlay values are precisely:

| Workbook cell | Normalized key | Diagnosis | Prior/final behavior |
| --- | --- | --- | --- |
| `L149` | `32, Candidate T` | `anterior medistinal hydatid cyst` | prior zero retained; master zero; source marked radiologist |
| `L163` | `96, Candidate C` | `Buried bumper syndrome` | prior human-lock zero retained; master zero; source marked radiologist |
| `L171` | `134, Candidate I` | `Ankle fracture` | prior zero retained; master zero; source marked radiologist |

They are ordinary numeric cells without formula, comment, or data validation. Whether `8` meant zero, missing/fallback, or transcription error is unprovable. A strict reconstruction must fail until they are re-adjudicated or explicitly grandfathered as prior-score fallbacks with truthful non-radiologist sources.

If independently re-adjudicated, the bounded correct-total range is 1255 through 1258. If treated as missing overlays, the scores stay zero but the truthful source counts become `ai_judges = 3790`, `human_prior = 1064`, `auto = 946`, and `radiologist = 200`.

The overlay changes 17 labels using `Model_<letters>` to `Candidate <letters>`. It also carries obsolete run IDs and four whitespace-only diagnosis differences. It is authoritative only for normalized key plus validated score, never for replacement row payload.

The reconstructed 53-row flip ledger has SHA256 `348FD2CC1F60B11A4F71D493B85A6ACEE0C5D0D59B9988905F2122B3BC5EA69B` when serialized as sorted `MCID|normalized_label|prior|final` lines. A future finalizer should emit an equivalent row-level ledger with original label, normalized label, review class, prior score, overlay score, final score, source, flip direction, rationale, reviewer, and approval metadata.

The old handoff also claimed 951 blank `weighted_score` cells, while the current master has 952. This is another reason to exclude `weighted_score` from adjudication authority and recompute only current Score1000 derivatives.

## Dynamic Downstream Contract

Let:

    C = case count, locked at 200 for RadLE v2
    M = all model arms in the complete master
    A = active non-excluded model arms
    H = backend human readers, locked at 12
    P = configured human presentation rows, 1 pooled or 2 split
    D = panel percentage display units per comparator, currently 100

| Contract | Required formula | Current | After one included model |
| --- | --- | ---: | ---: |
| Complete master rows | `C * (M + H)` | `200 * (18 + 12) = 6000` | `200 * (19 + 12) = 6200` |
| Active Score1000 rows | `C * (A + H)` | `200 * (15 + 12) = 5400` | `200 * (16 + 12) = 5600` |
| Active model rows | `C * A` | 3000 | 3200 |
| Model summaries | `A` | 15 | 16 |
| Comparator/panel rows | `A + P` | pooled 16; split 17 | pooled 17; split 18 |
| Panel percentage units | `(A + P) * D` | pooled 1600; split 1700 | pooled 1700; split 1800 |

Additional formulas:

- Correctness total is `parent_correct_total + appended_delta_correct`, not fixed `1255`.
- Every status total is `parent_status_counts + appended_delta_counts`; their sum must equal the active row count.
- IDK0 raw score is zero for exact IDK, approved typo-IDK, invalid response, and technical failure. Otherwise magnitude is `Likert + 1`, positive when correct and negative when wrong.
- Model projection weight is one. Human projection weight is `1 / readers_in_projection`: `1/12` pooled or `1/6` in each split group.
- Score1000 is the sum of row raw scores times projection weight.
- Score2000 is `Score1000 + C * 5`; with `C = 200`, the shift is `+1000`.
- All-IDK baseline is `C * IDK_SCORE`, not a row-count shortcut whose denominator changes when models are appended.
- Presentation pins the configured human row or rows first, then orders models by Score2000.

### Current hard-coded surfaces

- Clean/temp master builders lock the source SHA, 6000 rows, 20/19 columns, and 1255 correct rows.
- Score1000/IDK0 generators and audits lock 5400 active rows, 3000 model rows, 2400 human rows, six status counts, and 15 models.
- Split and pooled lanes separately lock human summary counts, comparator counts, panel rows, clip paths, tracks, outlines, metadata rows, and barcode units.
- Direct `_IDK0.py` script defaults still use IDK `+1`; only the wrapper reliably passes zero.
- Generated READMEs, captions, manifests, checklists, and provenance contain literal roster/cardinality prose.
- Panel categories and selected-reader lists are fixed in `scripts/make_radle_v2_score1000_panel23_svg_IDK0.py` and mirrored by audits.
- Adding a selected model currently requires coordinated category, display-name, wrapped-label, reader-key, color, logo, and audit entries. The fallback-badge registry is empty, so a missing logo is fatal.
- Display-label drift already exists, including `InternVL3.5 8B` versus `InternVL 3.5 8B` and `Mistral Large 3` versus `Mistral Large 3 2512`.

Canonical row data must retain all 12 individual human readers and a projection-neutral raw score. Pooled and split human outputs must be downstream projections over the same backend rows, not separately scored sources.

## Research Waves

### Wave 1: topology and lineage

Status: complete and consolidated.

Independent scopes:

1. Git branch and sibling-checkout lineage.
2. Final-binary, radiologist-final, clean-master, Score1000, and IDK0 output ancestry.
3. Complete model-result package and roster inventory.
4. Historical exact-match, judge, discrepancy, and radiologist-review evidence inside RadLE v2.
5. Score1000/Score2000/IDK0/panel hard-coded contract inventory.
6. Grok 4.5, GPT-5.6, and Meta Muse Spark runtime/package comparison.
7. Existing requirements and ExecPlan decision reconciliation.

### Wave 2: challenge and reconciliation

Status: complete and consolidated.

Resolved or bounded questions:

- Which exact promoted final-wide package and model roster should be the pre-append V2 base?
- Can old finalized scores be carried by stable keys without semantic drift or reordered-row ambiguity?
- Which historical diagnosis variants are safe deterministic equivalents, which are judge context only, and which are too ambiguous?
- What automatic judge agreement rule reproduces historical radiologist decisions with an acceptable false-accept rate?
- Which package completeness, retry, repair, and terminal-zero rules must gate promotion?
- Which counts can become manifest-derived and which roster/display choices must remain explicit configuration?
- Which commits and uncommitted paths must be retained when a clean implementation branch is eventually created?

Wave 2 confirmed the private one-model transaction, prospective-only variant reuse, strict finalizer behavior, optional/privacy-gated public release, and current unified runtime branch `49bf0d6`. It also identified the unresolved clinical rows and user choices listed below.

### Wave 3: incoming Drive artifact intake

Status: waiting for new model files.

Each incoming model package will be checked for:

- exact 200-case identity and uniqueness;
- expected `Diagnosis_`, `Likert_`, provider, returned-model, raw-response, reasoning, token, and request-extra columns;
- promoted-final versus raw/scorer provenance;
- missing, invalid, IDK, abstained, and technical-failure cells;
- provider-routing proof and returned model ID;
- repair/audit bucket counts;
- compatibility with the proposed isolated 200-row append adapter;
- collision with an existing model key, blind label, run ID, or final-master key.

## Closed Requirements After User Decisions

### Official comparator universe

Produce a model ledger with one row per model arm and at least:

    model_key
    display_name
    requested_model_id
    returned_model_id
    runtime_path
    provider_route
    access
    domain
    package_root
    final_wide_sha256
    case_count
    repair_status
    scoring_status
    blind_label
    panel_status
    decision

The response base and scored base are now resolved. The user approved the proposed current active comparator universe and the retained-but-excluded policy. Grok 4.5 and GPT-5.6 become active replacements after admission; the replaced Grok/GPT arms stay in the complete master and become retained-but-excluded.

### Append identity and immutability

The future contract should use stable keys at both stages:

- pre-finalization: `(run_id, Master_Case_ID, model_key)`;
- finalized master: `(Master_Case_ID, model_blinded)` plus retained `candidate/model_key` identity.

Persist `model_key`, display label, and blinded label as separate fields. Allocate blind labels from a stable global versioned collision-checked map; new models receive the next unused `Candidate <letter>` label rather than a fresh per-batch label map.

Existing row order is contractual in the materialized output: preserve every old non-derived value and old key order, then append the new model's 200 rows in numeric case order. Hash both the old-row projection and the scored delta. The output pattern is an immutable 200-row scored delta plus a new fully materialized sibling master.

### Accepted ground-truth variants

Variant reuse is prospective only. Canonical exact matches may auto-accept after normalizer validation; consistent v2-reviewed pairs initially require shadow review; imported V1 pairs and curated clinical aliases are judge context unless later calibration promotes them. Conflicts and semantic qualification changes remain mandatory radiologist review. Existing finalized scores remain frozen regardless of future variant-policy improvements.

### Judge and radiologist policy

The future requirements must specify:

- judge models and prompt/version hashes;
- blinded fields visible to judges;
- deterministic-match evidence;
- agreement/disagreement logic;
- failure and retry semantics;
- mandatory-radiologist conditions;
- radiologist queue schema and sign-off fields;
- final score-source values and precedence.

One terminal-state classifier must cover exact/typo IDK, invalid Likert, blank diagnosis, provider block, parse failure, retry exhaustion, accepted diagnosis, approved exception, and unresolved review. Morning promotion, long conversion, adjudication, and IDK0 must consume the same state semantics. Invalid Likert `8` is already resolved as invalid-zero, not as an open clinical score.

The workflow is transactional: one Morning writer per run root, timestamped staging, atomic promotion, no overwrite, resumable judge cache, and sealed manifests. The judge models should match the previous successful dual-judge workflow, and full dual judging is approved for new model rows that need judging. The radiologist queue is intentionally minimal: case number, blind code, ground truth, candidate diagnosis, and Likert only.

### Dynamic Score1000 and panel contract

Counts should be derived from a lane manifest and independently recomputed by audits. Display registries such as category, label, logo, color, and selected panel membership remain explicit choices. Human backend data must support both pooled and split presentation from the same row-level source.

The active handwritten path for this work is the Score1000 Panel 2/3 wrapper path, not the historical confidence-summary generator.

Public candidate CSV/table ordering should be humans first, active models by Score2000, then excluded models with `excluded = true`. Panels should include active contenders only.

## Remaining Decisions And Clarifications

1. Case 164 remains the only known clinical conflict in v2-reviewed variant evidence. It should not seed deterministic automation until resolved.
2. The three historical overlay values of `8` no longer require clinical reinterpretation: they are invalid-zero. A strict reconstruction should record them as invalid-zero/fallback-provenance rows rather than silent radiologist scores.
3. The "false-accept threshold" means the maximum tolerated rate at which the deterministic/variant matcher would incorrectly mark a wrong answer as correct. Until calibrated, broad semantic auto-acceptance remains disabled; full dual judging plus radiologist queue handles non-exact cases.
4. Public-release generation is approved as a candidate artifact after private admission, but publication still requires a separate recorded privacy approval.
5. Before new Drive results arrive, safe work includes drafting the ExecPlan, implementing schema/manifest validators against synthetic fixtures, preparing roster configuration, identifying previous judge model settings, and adding dry-run/idempotence tests. Actual admission, scoring, and panel regeneration wait for downloaded package hashes.

## Provisional Append Artifact Contract

This is a study hypothesis, not yet locked:

1. `append_input_manifest.json`: identifies promoted final-wide source, code commit, runtime, provider routing, case-set hash, and model roster.
2. `new_model_long_delta.csv`: exactly 200 rows for one model, before adjudication.
3. `accepted_variants_snapshot.csv`: governed case-specific scoring context with provenance and approval state.
4. `judge_worklist.csv` and judge evidence sidecars: only new score-required rows.
5. `radiologist_queue.csv`: unresolved new rows only.
6. `scored_append_delta.csv`: exactly 200 finalized new-model rows with score source.
7. `radle_v2_final_long_master.csv`: old finalized rows unchanged plus the scored delta.
8. `append_manifest.json`: source/output hashes, counts, model identity, old-row immutability proof, queue counts, and validation results.
9. New dated IDK0 Score1000/Score2000 lane and panel-ready summaries derived from the new materialized master.

## ExecPlan Handoff Outline

The final implementation ExecPlan should contain milestones for:

1. Protecting the current dirty work and creating a clean consolidation base.
2. Establishing an approved model-roster and package-manifest contract.
3. Implementing and testing the final-wide-to-new-model-delta adapter.
4. Building governed accepted-variant matching and calibration fixtures.
5. Implementing isolated judge/radiologist adjudication and immutable score carry-forward.
6. Materializing and auditing a new complete final-long-master sibling.
7. Making Score1000/IDK0 expectations manifest-derived while retaining locked score semantics.
8. Extending panel registries and performing structural plus visual QA.
9. Validating Grok 4.5 first, then replaying the same one-model transaction for GPT-5.6 and Meta Muse Spark from the unified runtime head `49bf0d6`.
10. Consolidating branches and preserving evidence artifacts only after the new vertical slice passes.

## Research Log

- 2026-07-10 01:54 +05:30, Codex: created this separate study ledger rather than rewriting the completed narrow IDK0/Morning audit.
- 2026-07-10 01:54 +05:30, Codex: recorded newer adjacent branches for GPT-5.6 and Meta Muse Spark and expanded scope from a Grok-only adapter to a reusable incremental-model contract.
- 2026-07-10, Codex: Wave 1 consolidated branch lineage, 18-model response/scored ancestry, result-package completeness, adjudication lineage, dynamic Score1000/IDK0 contracts, and the three-model normalized runtime schema.
- 2026-07-10, user scope correction: `C:/Users/thehb/Documents/RadLE Stats` is the previous RadLE version and must be ignored for this study even though it uses the same images. Removed its findings from this ledger.
- 2026-07-10 02:24 +05:30, Codex: Wave 2 challenged finalization, variant reuse, package admission, and document consistency; reconciled the findings into one current requirements position.
- 2026-07-10 02:24 +05:30, Codex: recorded the new clean unified runtime head `codex/morning-meta-muse-spark-append@49bf0d6` and changed future consolidation to target it rather than separately merging GPT and Meta development tails.
