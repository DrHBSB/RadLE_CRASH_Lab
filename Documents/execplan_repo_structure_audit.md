# RadLE v2 Repo Structure And Preservation Audit

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `AGENTS.md` or `PLANS.md` was found by `rg --files -g AGENTS.md -g PLANS.md`; the applicable repo instruction is the user-provided AGENTS.md instruction to use ExecPlans for complex analyses and prefer `Documents/`.

## Purpose / Big Picture

The user wants a preservation-first map of `C:\Users\thehb\Documents\RadLE v2` before any cleanup, public packaging, or repository reshaping. The useful outcome is an evidence-backed classification of what is public-repo candidate, private/internal git material, private archive sidecar material, local-only cache/vendor/secret material, eventual delete candidate pending verification, and must-preserve manuscript/internal proof.

This plan intentionally does not move, delete, rename, stage, commit, push, publicize, or rewrite project artifacts. The only permitted writes during PASS TWO were this ExecPlan and a separate read-only audit ledger under `Documents/`.

## Current State

Current state (2026-07-06 18:20 +05:30, Codex/GPT-5): PASS TWO read-only audit is consolidated and final-judge checked. Six independent scout lanes plus local probes re-derived the core findings, and `Documents/repo_structure_audit_pass_two_ledger.md` now records the pass-two evidence matrix, classification, unresolved decisions, and cleanup gates. Next: report the ledger and revised plan to the user; any cleanup or public packaging must be a separate PASS THREE plan.

## Locked Facts

- The checkout root is `C:\Users\thehb\Documents\RadLE v2`.
- The current branch is `codex/radle-v2-handwritten-panels`; `origin` is `https://github.com/DrHBSB/RadLE_CRASH_Lab.git`.
- The current tree is dirty: tracked README/ExecPlans/notebooks/scripts are modified, tracked `docs/goals/llava-vllm-*` files are deleted from the worktree, and handwritten-panel scripts/ExecPlans are untracked.
- `.gitignore` ignores `.env`, `*.env`, `.venv/`, `outputs/`, `results/`, `deliverables/`, `*.csv`, `*.xlsx`, `*.jsonl`, medical-image extensions, and `vllm_0_23_0/`.
- `.git/info/exclude` excludes `.claude/worktrees/` and several Claude local runtime state paths.
- `radle_api_keys.env` exists, is ignored by `.gitignore:8:*.env`, and was intentionally not read.
- `src/radle_benchmark.py` and `notebooks/RadLE_v1_5_Morning.ipynb` remain the official benchmark spine.
- `src/radle_medical_custom_runtime.py`, Workbench notebooks, probe scripts, promotion scripts, and model handoffs are experimental/internal runtime sidecars unless separately reviewed for public release.
- `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/radle_v2_final_long_master.csv` is the authoritative final manuscript scoring master found in this audit: 6000 rows, 20 columns, SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`.
- The final scoring audit reports duplicate_keys=0 and final_score_distribution 0=4745 and 1=1255.
- `outputs/radle_v2_stats/_stale_archive/final_binary_scoring_20260705_010315` is must-preserve internal proof and a third-opinion precursor, not the final authoritative score source; it was moved out of the active outputs path on 2026-07-07.
- Handwritten `experience` and `qual` figure packages under the final scoring folder each contain 13 files and reference the final master SHA through `figure_manifest.json`.
- `deliverables/radle_v2_long_format_2026-07-04/source/ground_truth_RadLE_RSNA_Diagnosis_Scoring_key.csv` and `results/reference/RadLE_RSNA_Diagnosis_Scoring_key.csv` are byte-identical private ground-truth/reference files with SHA256 `5d26771da27cf8fef1a7f48204257c65b8e1f7b41423763f2e45cb384fb738d4`.
- `deliverables/radle_v2_long_format_2026-07-04/source/combined_final_18models_wide.csv` and `results/radle_v2_combined/final/RadLE_v2_results_final.csv` share SHA256 `7d9ce5c66fbecb6ff9b72edb6676ca8ce4f9e5e3dcaf621610437a703efde17f` and are private 18-model wide/source files with raw-response and image-identifier columns.
- `results/dataset_manifests/radle-v2-frozen-2026-06-29` records a frozen GCS snapshot with 263 image files, archive SHA256 `6b4d4c1f04660579689c380905c93ab1ea53724a0e335013229fbbb94cd0a47b`, and private/restricted provenance paths.
- `results/internvl3_5_8b_medical_full_200_cases_ollama` and `results/internvl_ollama_outputs/internvl3_5_8b_medical_full_200_cases_ollama` are byte-identical: 29 files, 1,592,046 bytes, recursive SHA256 diff count 0.
- `results/claude_fable_5_full_200_cases-20260702T040252Z-3-001/claude_fable_5_full_200_cases` and `results/drive_sources/claude_fable_5_full_200_cases` are byte-identical mirrors.
- `results/radle_v2_combined` is final-only: it has `final/` with two files and lacks `raw/`, `repair/`, `scorer/`, `runtime_artifacts/`, `public_release/`, and `stats_verify/`.
- `results/radle_v2` has only `raw/` and `scorer/`; `results/drive_sources/radle_v2` has richer final/public_release/private source material and differs by 92 relative hashes/paths.
- `results/**/public_release` CSV schemas omit obvious diagnosis, raw-response, image-filename, and image-hash columns, but no inspected public manifest records completed privacy/publicability approval.
- `README.md`, several notebooks/docs, `scripts/write_audit.py`, and `notebooks/update_nb_v2.py` contain confidential/local paths or secret-loading context and are not public-clean as-is.
- `Documents/repo_structure_audit_pass_two_ledger.md` is the current detailed PASS TWO evidence ledger.

## Do Not Revisit

- Do not perform cleanup in this phase. See Decision Log 2026-07-06.
- Do not classify ignored generated artifacts as disposable merely because they are ignored. See Decision Log 2026-07-06.
- Do not call `public_release/` artifacts public-safe without a completed privacy review artifact or approval field. See Decision Log 2026-07-06.
- Do not accept the deleted `docs/goals/llava-vllm-*` state as intentional cleanup without a separate restore/archive/delete decision. See Decision Log 2026-07-06.
- Do not treat `results/radle_v2_combined` as a complete release package; it is currently final-only. See Decision Log 2026-07-06.
- Do not delete either InternVL duplicate, either Claude Fable duplicate/mirror, or the OctoMed tarball/nested tree until canonical path, downstream references, and hashes are checked. See Decision Log 2026-07-06.
- Do not infer GitHub repository visibility from the remote URL alone. See Decision Log 2026-07-06.

## Progress

- [x] (2026-07-06 11:25 +05:30, Codex/GPT-5) Completed pass-one shallow repo survey with `rg --files`, top-level file counts, `.gitignore`, branch/status, git first-add dates, and ignored folder counts.
- [x] (2026-07-06 15:08 +05:30, Codex/GPT-5) Integrated pass-one scout receipts into a high-level folder-by-folder, chronology, and package-boundary playback.
- [x] (2026-07-06 17:50 +05:30, Codex/GPT-5) Began PASS TWO by re-reading this ExecPlan, `~/.codex/PLANS.md`, the user task brief, git status, `.gitignore`, top-level inventory, ignored roots, remotes, and recent log.
- [x] (2026-07-06 17:55 +05:30, Codex/GPT-5) Launched six read-only scout lanes: manuscript proof, source/provenance, model run chain, publicability/privacy, reproducibility/producer lineage, and git/workflow state.
- [x] (2026-07-06 18:10 +05:30, Codex/GPT-5) Ran local structured probes for package shapes, public-release schemas, manifest keys, wide/source CSV row/column counts, SHA256 hashes, and duplicate comparisons.
- [x] (2026-07-06 18:16 +05:30, Codex/GPT-5) Created `Documents/repo_structure_audit_pass_two_ledger.md` with consolidated evidence, classifications, unresolved decisions, and cleanup gates.
- [x] (2026-07-06 18:16 +05:30, Codex/GPT-5) Revised this ExecPlan so pass-two findings supersede pass-one broad claims and a fresh agent can resume without chat context.
- [x] (2026-07-06 18:20 +05:30, Codex/GPT-5) Final sanity check completed by a read-only judge: no blockers; the docs avoid unsupported disposable/public-safe claims, gate `public_release/` on privacy review, preserve proof bundles atomically, and defer cleanup to PASS THREE.

## Surprises & Discoveries

- Observation: Public-release manifests contain sanitization notes but no completed privacy-review/publicability-review field.
  Evidence: Publicability scout inspected 9 `RadLE_v2_public_manifest.json` files; all had `privacy_notes`, none had an explicit approval field.
  Date/Author: 2026-07-06, Codex/GPT-5

- Observation: `results/radle_v2_combined` is final-only despite another ExecPlan claiming combined public-release paths.
  Evidence: `Test-Path results/radle_v2_combined/public_release` returned false; local probes found only `final/` with two files.
  Date/Author: 2026-07-06, Codex/GPT-5

- Observation: `deliverables/radle_v2_long_format_2026-07-04` contains private source truth but no same-folder manifest.
  Evidence: Recursive listing found only `source/combined_final_18models_wide.csv` and `source/ground_truth_RadLE_RSNA_Diagnosis_Scoring_key.csv`.
  Date/Author: 2026-07-06, Codex/GPT-5

- Observation: The handwritten figure outputs already exist while their producer scripts and plan are still untracked.
  Evidence: Git status shows untracked `scripts/radle_v2_handwritten_stats.py`, `scripts/make_radle_v2_handwritten_svg_panels.py`, `scripts/audit_radle_v2_handwritten_panels.py`, `scripts/build_radle_v2_handwritten_panels.ps1`, and `Documents/execplan_radle_v2_handwritten_panels.md`; figure manifests exist in final scoring output folders.
  Date/Author: 2026-07-06, Codex/GPT-5

- Observation: The apparent disorder is concentrated in ignored evidence/output roots, not only tracked code.
  Evidence: `.gitignore` hides `outputs/`, `results/`, `deliverables/`, and bulk CSV/JSONL artifacts, while pass two found authoritative proof, private source, manifests, public-release candidates, and duplicates in those ignored roots.
  Date/Author: 2026-07-06, Codex/GPT-5

## Decision Log

- Decision: Keep PASS TWO read-only except for `Documents/execplan_repo_structure_audit.md` and `Documents/repo_structure_audit_pass_two_ledger.md`.
  Rationale: The task explicitly prohibited cleanup/mutation and requested documentation/refinement.
  Date/Author: 2026-07-06, user and Codex/GPT-5

- Decision: Use the six-class preservation taxonomy for all findings: public-repo candidate, private/internal git material, private archive sidecar, local-only cache/vendor/secret, eventual delete candidate pending verification, and must-preserve manuscript/internal proof.
  Rationale: This matches the user request and avoids mixing current folder location with future packaging role.
  Date/Author: 2026-07-06, Codex/GPT-5

- Decision: Treat `public_release/` as candidate-public only, not publication-approved.
  Rationale: Headers and manifests support sanitization intent, but manifests lack explicit completed privacy review and docs/notebooks/scripts still contain private context.
  Date/Author: 2026-07-06, Codex/GPT-5

- Decision: Treat duplicate byte-identical packages as cleanup candidates only after canonical-path and reference checks.
  Rationale: Hash identity alone does not decide which path downstream docs/scripts/manifests expect.
  Date/Author: 2026-07-06, Codex/GPT-5

- Decision: Preserve final radiologist scoring and binary-scoring precursor as separate atomic proof packages.
  Rationale: Final radiologist master is authoritative, while binary scoring preserves third-opinion lineage and should not be flattened into final output.
  Date/Author: 2026-07-06, Codex/GPT-5

## Revision Notes

- v3 (2026-07-06, Codex/GPT-5): PASS TWO revision. Added current ledger path, hard row/hash evidence, public-review gates, duplicate/incomplete package findings, and cleanup/publication prohibitions.
- v2 (2026-07-06, Codex/GPT-5): Marked pass-one scout swarm complete, added package-boundary findings, and locked cleanup gates before user-facing playback.
- v1 (2026-07-06, Codex/GPT-5): Created after the user approved launching the audit swarm following a quick repo name pass and two read-only scout receipts.

## Outcomes & Retrospective

PASS TWO outcome: the audit now has a concrete ledger and a self-contained handoff plan. The strongest conclusions are preservation-oriented: final scoring/radiologist proof, binary-scoring precursor, handwritten packages, private source CSVs, dataset manifests, and result package manifests must be preserved atomically. The strongest constraints are safety-oriented: ignored roots are not disposable, public-release schemas are not privacy approval, and duplicate directories are not safe to delete until canonical path and downstream references are settled.

No reusable global skill should be created from this pass without explicit user permission.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Plan setup and revision | `execplan` | Required by user instruction and needed for compaction-safe audit state | `auto-suggest` |
| Read-only evidence gathering | `none` plus bounded subagents when explicitly authorized | Direct filesystem/git inspection is sufficient; subagents are useful only for parallel lanes | `manual` |
| Public/privacy review | `none` | Needs local regex/content review and human policy approval, not a special skill | `none` |
| Cleanup PASS THREE | `execplan` | Cleanup would be a separate high-risk, multi-step plan with gates | `auto-suggest` |
| Visual/public figure QA | `output-artifact-verifier` if regenerating visual artifacts | Required only if generating or altering visual outputs | `manual` |

## Context And Orientation

The repo is a RadLE v2 benchmark and runtime workspace. It contains official benchmark code, Colab/Workbench notebooks, medical VLM runtime scripts, scoring/statistics scripts, planning documents, local run outputs, source/deliverable bundles, public-release candidate outputs, and private ground-truth/source material.

Important top-level folders:

- `src/`: benchmark/runtime modules and templates.
- `notebooks/`: Colab and Workbench execution surfaces. Several notebooks contain private path/secret-loading context and are not public-clean as-is.
- `scripts/`: runners, probes, promotion/repair scripts, scoring/statistics, audit, and figure-generation tools.
- `Documents/`: ExecPlans, handoffs, requirements, audits, provenance notes. Mixed public-candidate and internal-only material.
- `outputs/`: stats/scoring/manuscript proof and operational logs. Must be treated as private archive sidecar unless explicitly curated.
- `results/`: model run trees with raw/final/public_release/repair/scorer/runtime artifacts plus source/reference subtrees. Mixed private archive sidecar and candidate-public exports.
- `deliverables/`: source bundle for long-format/final scoring work; currently private and lacking a same-folder manifest.
- `notes/`: research notes.
- `.claude/`, `.codex/`, `.agents/`, `docs/goals`: orchestration/tooling state. `.claude` is ignored private local workflow state; `.codex` and `.agents` appear empty; `docs/goals` tracked LLaVA/vLLM boards are currently deleted.
- `.venv/`, `vllm_0_23_0/`, `__pycache__/`: local environment/vendor/cache material.

## Plan Of Work

PASS TWO is now complete. PASS THREE, if requested, should be a separate cleanup/package ExecPlan and must start from this order:

1. Re-open this plan and `Documents/repo_structure_audit_pass_two_ledger.md`.
2. Re-run `git status --short --branch` and `git status --ignored --short -uall`.
3. Confirm whether the user wants cleanup, public packaging, private archive sealing, or only more audit.
4. Resolve canonical-path decisions for byte-identical duplicate packages.
5. Resolve public/privacy-review policy before publishing anything under `public_release/`.
6. Build or locate missing manifests for `deliverables/radle_v2_long_format_2026-07-04` and `results/radle_v2_combined`.
7. Only then propose moves/deletes/staging in a new plan.

## Milestones

Milestone 1: PASS TWO evidence ledger exists. Skill: `execplan` for plan state; no special skill for filesystem/git evidence. Complete: `Documents/repo_structure_audit_pass_two_ledger.md` exists.

Milestone 2: PASS TWO ExecPlan revision exists. Skill: `execplan`. Complete: this file records the current state, locked facts, decisions, and cleanup gates.

Milestone 3: Final user playback exists. Skill: none. Pending: summarize audited scope, link ledger/plan, provide improved classification, list unresolved decisions, and confirm no cleanup was performed.

## Concrete Steps (Commands)

Useful read-only commands from repo root:

    git status --short --branch
    git status --ignored --short -uall
    git log --oneline --decorate -8
    git remote -v
    git check-ignore -v -- outputs results deliverables vllm_0_23_0 .venv radle_api_keys.env
    git ls-tree -r --name-only HEAD docs/goals
    rg -n -i "C:\\Users|/home/jupyter|/content/|GITHUB_TOKEN|HF_TOKEN|OPENAI_API_KEY|ANTHROPIC_API_KEY|OPENROUTER_API_KEY|GEMINI_API_KEY|CONFIDENTIAL|private GCP" README.md Documents notebooks scripts src

For wide raw-response CSVs, use Python with:

    csv.field_size_limit(2147483647)

The default CSV field limit fails on some `Raw_Response_*` fields.

## Validation And Acceptance

PASS TWO is acceptable when a fresh agent can answer these without chat context:

- Where are the final manuscript/internal proof packages?
- Which source/provenance files must stay private?
- Which result trees are complete, partial, duplicate, or final-only?
- Which public-release artifacts are merely candidate-public versus privacy-approved?
- Which dirty git/workflow states block cleanup?
- What exact gates must pass before PASS THREE cleanup?

No visual artifact is generated by this audit plan itself.

## Idempotence And Recovery

All PASS TWO audit commands are read-only and can be rerun. If future evidence conflicts with this plan, reconcile this plan in place and add a `Surprises & Discoveries` entry naming the exact conflicting file/path/hash. Do not perform cleanup recovery with `git reset --hard` or `git checkout --` unless the user explicitly asks.

## Artifacts And Notes

Primary PASS TWO artifact:

- `Documents/repo_structure_audit_pass_two_ledger.md`

Key proof snippets:

- Final master: `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/radle_v2_final_long_master.csv`, rows=6000, columns=20, SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`.
- Binary precursor: `outputs/radle_v2_stats/_stale_archive/final_binary_scoring_20260705_010315`, files=31, bytes=3,598,422.
- Ground truth reference: SHA256 `5d26771da27cf8fef1a7f48204257c65b8e1f7b41423763f2e45cb384fb738d4` in both deliverable source and `results/reference`.
- Wide 18-model source/final: SHA256 `7d9ce5c66fbecb6ff9b72edb6676ca8ce4f9e5e3dcaf621610437a703efde17f`.
- InternVL duplicate pair: 29 files, 1,592,046 bytes, recursive SHA256 diff count 0.
- Public-release manifests inspected: 9; approval field found: none.

## Interfaces And Dependencies

This audit depends only on local filesystem and git metadata. It does not require network access, cloud access, API keys, notebooks to execute, or generated artifacts to be opened beyond lightweight metadata/content inspection. Future cleanup/public packaging may require GitHub visibility checks, Drive/GCS policy checks, and manuscript/source-package owner decisions, but those were not needed for PASS TWO.
