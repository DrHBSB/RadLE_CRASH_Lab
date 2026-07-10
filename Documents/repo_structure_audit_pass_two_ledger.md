# RadLE v2 Repo Structure Audit Pass Two Ledger

Generated: 2026-07-06 18:16 +05:30, Codex/GPT-5.

This ledger is a read-only audit artifact for `C:\Users\thehb\Documents\RadLE v2`. It consolidates PASS TWO local probes plus six independent read-only scout lanes. It is not a cleanup instruction. No file is disposable, public-safe, or ready to move solely because it appears in a category below; cleanup/publication still requires the gates listed here.

## Method

Baseline commands and probes:

- `git status --short --branch`
- `git status --ignored --short -uall`
- `git log --oneline --decorate -8`
- `git remote -v`
- `git check-ignore -v -- outputs results deliverables vllm_0_23_0 .venv radle_api_keys.env`
- `Get-ChildItem -Force` top-level inventory and bounded recursive counts
- Python CSV/hash probes with `csv.field_size_limit(2147483647)` for large raw-response CSVs
- Recursive SHA256 comparisons for suspected duplicate result trees

Independent scout lanes:

- Manuscript proof chain
- Source/provenance chain
- Model run chain
- Publicability/privacy
- Reproducibility/producer lineage
- Git/workflow state

## Top-Level Classification

| Class | Current candidates | Evidence summary | Gate before action |
| --- | --- | --- | --- |
| Public-repo candidate | `src/radle_benchmark.py`, `notebooks/RadLE_v1_5_Morning.ipynb`, selected sanitized release/export code, selected docs/scripts after redaction | Official benchmark spine is tracked code/notebook; public release export strips diagnoses/raw text/image identifiers by schema | Redact private paths/secrets, decide public file allowlist, run full privacy/content scan |
| Private/internal git material | `Documents/` ExecPlans and handoffs, runtime provenance docs, many notebooks/scripts with local/GCS/Drive execution details | Docs/notebooks contain confidential paths, VM/GCS details, and operational history | Decide what stays in internal repo versus private archive sidecar before public packaging |
| Private archive sidecar material | `outputs/`, `results/`, `deliverables/`, `results/reference`, `results/dataset_manifests`, `results/drive_sources` | Ignored roots contain final proof, source truth, manifests, private raw/final outputs, and public-release candidates | Build manifest/checksum bundles; do not delete or publish without owner decision |
| Local-only cache/vendor/secret | `.venv/`, `vllm_0_23_0/`, `__pycache__/`, `radle_api_keys.env`, `.claude/settings.local.json`, `.claude/worktrees/` | Ignored or excluded local env/vendor/secret/workflow material; `radle_api_keys.env` was intentionally not read | Never stage secrets; compare vendor/worktrees only if unique local patches are suspected |
| Eventual delete candidate pending verification | One copy of duplicate InternVL package; one copy of byte-identical Claude Fable mirror; maybe OctoMed tarball or nested duplicate; selected backup histories; deleted `docs/goals/llava-vllm-*` if intentional | Byte-identical comparisons exist for InternVL and Claude Fable mirror; other candidates are not fully verified | Pick canonical path, verify downstream references and archives, then make a separate cleanup decision |
| Must-preserve manuscript/internal proof | `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147`, `outputs/radle_v2_stats/_stale_archive/final_binary_scoring_20260705_010315`, handwritten figure packages, ground truth/source CSVs, dataset manifests | Final master and summaries have hashes/row counts; binary scoring has audit trail and was archived out of the active outputs path on 2026-07-07; source/provenance inputs are private but load-bearing | Preserve atomically with scripts, manifests, audits, and provenance before any package reshaping |

## Findings

| ID | Path(s) | Claim | Evidence | Confidence | Class | Public/private status | Unresolved question / next verification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SPINE-001 | `README.md`, `src/radle_benchmark.py`, `notebooks/RadLE_v1_5_Morning.ipynb` | The official benchmark spine remains README plus benchmark module plus Morning notebook, but README is not public-clean as-is. | Prior repo convention and current code locate core logic in `src/radle_benchmark.py`; privacy scout found README references to confidential Drive paths and `GITHUB_TOKEN`. | High | public-repo candidate after redaction | Needs redaction | Build public README variant and rerun path/secret scan. |
| SPINE-002 | `src/radle_medical_custom_runtime.py`, Workbench notebooks, `scripts/*probe*.py`, `scripts/promote_*`, model handoff docs | Medical VLM/Workbench work is experimental/internal sidecar material, not the official benchmark spine. | Producer-lineage scout mapped model-scoped run IDs, VM/GCS provenance, probe/promotion scripts, and public-release reuse. | High | private/internal git material | Internal, selected scripts may later be public after scrub | Decide which runtime scripts are reproducibility sidecars versus public tooling. |
| MP-001 | `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/radle_v2_final_long_master.csv`; `final_scoring_audit.json` | Final radiologist master is the authoritative manuscript scoring table and must be preserved atomically with its audit. | Master rows=6000, cols=20, SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`; audit row_count=6000, duplicate_keys=0, final_score_distribution 0=4745 and 1=1255. | High | must-preserve manuscript/internal proof | Private/internal proof | Locate original radiologist review workbook path; audit records hash but not path. |
| MP-002 | `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147` | Final radiologist folder is a compact preservation unit. | 49 files, 2,217,195 bytes. Includes final master, summary CSVs, audit, seniority PNGs, handwritten package folders, and visual QA. | High | must-preserve directory unit | Mixed proof/public-candidate figures | Determine whether seniority PNGs are manuscript figures or exploratory proof. |
| MP-003 | `model_summary.csv`, `provider_summary.csv`, `access_summary.csv`, `domain_summary.csv`, `human_role_summary.csv`, `seniority_summary.csv`, `appendix_within_provider_deltas.csv`, `SUMMARY_SPEC.md` under final scoring folder | Summary CSVs are manuscript statistics derived from the final master and must stay with `SUMMARY_SPEC.md` and metrics scripts. | `SUMMARY_SPEC.md` states locked metrics core, master 6000 rows/20 cols, global n_correct=1255, non-excluded n=5400 correct=1224; audit records output hashes. | High | must-preserve manuscript stats | Mostly aggregate, still internal until curated | Map summaries to manuscript table/appendix targets. |
| MP-004 | `outputs/radle_v2_stats/_stale_archive/final_binary_scoring_20260705_010315` | Binary scoring folder is a required internal proof precursor, not the final authoritative score source; it was moved out of the active outputs path on 2026-07-07. | 31 files, 3,598,422 bytes; input and output rows each 6000; 30 candidates; no duplicate row keys; README and handoff say Codex sole-scorer is third opinion and finalization ignores `score_binary`. | High | must-preserve internal proof precursor | Private/internal proof | Validate all shard audit JSONs against one schema before archive sealing. |
| MP-005 | `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/experience`; `.../qual`; `.../_visual_qa` | Handwritten experience and qualification figure packages are manuscript-facing sidecars and must be preserved atomically with manifests, support CSVs, QA, and generator scripts. | Each package has 13 files; manifests cite schema `radle_v2_handwritten_figure_manifest_v1`, master SHA `7641BACC...`, generator `make_radle_v2_handwritten_svg_panels.py`, and 2400x1700 canvas. | High | must-preserve figure package | Mixed: SVG/captions likely public candidate; provenance/QA internal | Check manuscript source/submission package before calling final public figures. |
| SP-001 | `deliverables/radle_v2_long_format_2026-07-04/source/ground_truth_RadLE_RSNA_Diagnosis_Scoring_key.csv`; `results/reference/RadLE_RSNA_Diagnosis_Scoring_key.csv` | Deliverable ground truth is byte-identical to repository reference scoring key and is private/restricted. | Both files: 61,935 bytes, 200 rows, 25 columns, SHA256 `5d26771da27cf8fef1a7f48204257c65b8e1f7b41423763f2e45cb384fb738d4`; includes ground truth, image filenames/hashes, reviewer notes. | High | private source/provenance | Private/restricted | Decide whether any ground truth can be public in a separate policy review. |
| SP-002 | `deliverables/radle_v2_long_format_2026-07-04/source/combined_final_18models_wide.csv`; `results/radle_v2_combined/final/RadLE_v2_results_final.csv` | The 18-model wide source/final file is private and contains raw model fields. | 36,804,740 bytes, 200 rows, 291 columns, SHA256 `7d9ce5c66fbecb6ff9b72edb6676ca8ce4f9e5e3dcaf621610437a703efde17f`; includes `Associated_Images`, `Image_SHA256`, `Raw_Response_*`, request/usage fields, and 18 model groups. | High | private archive sidecar | Private/internal | No same-folder deliverable manifest explains exact merge lineage; create or locate one. |
| SP-003 | `results/dataset_manifests/radle-v2-frozen-2026-06-29/transfer_manifest.json`; `file_manifest.csv` | Dataset provenance manifest identifies a frozen GCS snapshot and must be preserved. | Snapshot `radle-v2-frozen-2026-06-29`; GCS dataset URI; source archive SHA256 `6b4d4c1f04660579689c380905c93ab1ea53724a0e335013229fbbb94cd0a47b`; 263 images, 134 `.jpg`, 129 `.png`; file manifest rows=263. | High | private source/provenance | Private/restricted unless dataset policy permits release | Verify bucket/IAM/license and whether image hashes/filenames can be public. |
| SP-004 | `results/drive_sources/radle_v2` | Drive source `radle_v2` is a richer private source tree than local `results/radle_v2`. | Drive final/raw CSVs are 35,602,148 bytes, 200 rows, 211 columns, SHA256 `2dcc083520d11c13031e2247f65e7b81139ba1a19de0f4f2bb720d30a2c10053`; manifest uses CONFIDENTIAL Google Drive paths; drive tree has final/public_release absent from `results/radle_v2`. | High | private archive sidecar | Mixed private plus public-release candidates | Decide whether `drive_sources/radle_v2` is authoritative for missing companions. |
| SP-005 | `deliverables/radle_v2_long_format_2026-07-04` | Deliverable folder lacks a local manifest despite containing source truth. | Recursive listing found only `source/combined_final_18models_wide.csv` and `source/ground_truth_RadLE_RSNA_Diagnosis_Scoring_key.csv`. | High | private archive sidecar | Private | Locate or create provenance manifest before packaging. |
| MR-001 | `results/internvl3_5_8b_medical_full_200_cases_ollama`; `results/internvl_ollama_outputs/internvl3_5_8b_medical_full_200_cases_ollama` | The two InternVL trees are byte-identical duplicates. | Both have 29 files and 1,592,046 bytes; same relative file list; recursive SHA256 diff count=0; final CSV SHA256 `23a285d00e51676971ee78abebc412c071c83c5ac1aca4ee5d128ef237a54095`. | High | duplicate candidate pending owner choice | Mixed private/public-release | Pick canonical path only after checking downstream references. |
| MR-002 | `results/radle_v2_combined` | Combined result tree is final-only and missing expected companions. | Files=2, bytes=36,805,917; has only `final/`; missing `raw/`, `repair/`, `scorer/`, `runtime_artifacts/`, `public_release/`, `stats_verify/`; manifest says appended `lingshu_32b`. | High | derived output preserve until companions decided | Private/internal final CSV only | Decide whether to generate companions/public_release or keep as final-only derived artifact. |
| MR-003 | `results/medgemma_1_5_4b_medical_full_200_cases` | MedGemma is the most complete root-level run package observed. | Has final/raw/repair/scorer/public_release/runtime_artifacts; files=109; final manifest rows=200, source_label=`repaired`, SHA256 `05311fd71b64f0cd8f8459a6788b2653efb99d6ded9b2766d0879bbc1c3ae8be`. | High | private archive sidecar with public-release candidate | Mixed | Determine whether missing `stats_verify` is acceptable or optional. |
| MR-004 | `results/claude_fable_5_full_200_cases-20260702T040252Z-3-001/...`; `results/drive_sources/claude_fable_5_full_200_cases` | Claude Fable timestamped wrapper and `drive_sources` mirror are byte-identical. | Nested package has 92 files and 9,959,267 bytes; comparison with drive_sources mirror has diff=0; raw and final SHA256 `816a634d70507cdfc7609b44ae0a4fce891c539e05327443b9a18a7c5ebbb520`. | High | duplicate/mirror candidate pending canonical path | Mixed | Decide canonical copy before archive/delete. |
| MR-005 | `results/radle_v2`; `results/drive_sources/radle_v2` | `results/radle_v2` is incomplete relative to `drive_sources/radle_v2`. | `results/radle_v2` has 15 files and only raw/scorer; `drive_sources/radle_v2` has 105 files and includes final/public_release; relative hash diff=92. | High | do-not-delete without source-of-truth decision | Private/raw-heavy plus mixed drive source | Audit sync/copy logs and decide authoritative tree. |
| MR-006 | `results/llava_med_ollama_outputs/llava_med_mistral_7b_medical_full_200_cases_ollama` | LLaVA-Med package is final/public-release only and locally lacks raw/provenance companions. | Files=5; has final and public_release only; manifest references `/home/jupyter/.../raw/results.csv` and `scripts/radle_llava_med_adjudication.json`, absent under package. | High | incomplete package preserve pending raw lookup | Mostly final/public locally, private source elsewhere | Search expected raw/adjudication sources before classifying. |
| MR-007 | `results/lingshu_ollama_outputs` | Lingshu has final/raw/public_release but lacks scorer/repair/runtime_artifacts/stats_verify. | Files=32; raw/final/public_release present; raw `results.csv`, raw backups, and final CSV share SHA256 prefix `629793B087419486`. | High | partial package preserve | Mixed | Determine if scorer was intentionally skipped before combined append. |
| MR-008 | `results/octomed_ollama_outputs` | OctoMed root is wrapper plus tarball; nested package is mostly complete but has empty repair/scorer and no runtime/stats_verify. | Root includes nested package plus `octomed_7b_medical_full_200_cases_ollama.tar.gz` size=1,595,973; nested final/raw/public_release present; repair/scorer folders have zero files. | High | wrapper/archive candidate pending tarball compare | Mixed | List tarball contents and compare before keeping/deleting either copy. |
| PUB-001 | `results/**/public_release/RadLE_v2_public_model_results.csv`; `RadLE_v2_public_model_summary.csv`; `RadLE_v2_public_sanitized_call_log.csv` | Public-release CSV schemas omit obvious diagnosis/raw/image/source columns. | Header probes found case UID, model/provider, validity, abstention, Likert, token, latency, score, and coarse error columns; no `Diagnosis`, `Raw_Response`, `Associated_Images`, or `Image_SHA256` columns. | High | public release candidate | Candidate public after review | Full-cell PHI/source leakage scan and manual sample review still required. |
| PUB-002 | `results/**/public_release/RadLE_v2_public_manifest.json` | Public manifests document sanitization intent but no completed privacy review. | All 9 manifests have `privacy_notes`; none had `privacy_review` or `publicability_review` approval fields. | High | release manifest | Review required | Add or require explicit privacy approval artifact before publication. |
| PUB-003 | `README.md`, notebooks, selected `Documents/`, `scripts/write_audit.py`, `notebooks/update_nb_v2.py` | Candidate public docs/scripts/notebooks are not public-clean as-is. | Regex/scout found CONFIDENTIAL Drive paths, `/content/`, `/home/jupyter`, local `C:/Users/thehb/...`, `GITHUB_TOKEN`/`HF_TOKEN` handling, and local radiologist workbook paths. | High | public-repo candidate needing redaction | Private or needs redaction | Build public allowlist and redact/exclude internal execution transcripts. |
| GIT-001 | Repository root | Current branch/worktree is dirty and not a safe cleanup baseline. | Branch `codex/radle-v2-handwritten-panels`; origin `https://github.com/DrHBSB/RadLE_CRASH_Lab.git`; status includes modified README/ExecPlans/notebooks/scripts, deleted `docs/goals/llava-vllm-*`, and untracked handwritten-panel scripts/ExecPlans. | High | mixed | Mixed | Review file ownership before commit/cleanup/public claims. |
| GIT-002 | `.gitignore`; `.git/info/exclude` | Ignore/exclude policy hides both disposable local material and important proof sidecars. | `.gitignore` ignores `.env`, `.venv`, `outputs/`, `results/`, `deliverables/`, `*.csv`, `*.xlsx`, `*.jsonl`, medical image extensions, `vllm_0_23_0/`; `.git/info/exclude` excludes `.claude/worktrees/` and Claude runtime state. | High | repo policy plus local workflow policy | Tracked policy plus private local excludes | Do not treat ignored proof roots as disposable. |
| GIT-003 | `radle_api_keys.env` | Local secret file exists and is ignored; contents were intentionally not read. | File size 567 bytes; ignored by `.gitignore:8:*.env`. | High | local-only secret | Private | Never stage; inspect only variable names with non-printing parser if needed. |
| GIT-004 | `.claude/settings.local.json`; `.claude/worktrees/*`; `.codex/`; `.agents/` | `.claude` is private local workflow sidecar; `.codex` and `.agents` appear empty in this checkout. | `.claude` inventory found settings plus two worktrees, 19 items/186,226 bytes; `.codex` and `.agents` inventory zero items. | High for `.claude`, medium for empty dirs | local-only/private internal | Private local | Inspect worktree git states only if unique unmerged work matters. |
| GIT-005 | `docs/goals/llava-vllm-runtime/**`; `docs/goals/llava-vllm-antigravity-extension/**` | Deleted GoalBuddy board files are tracked history and should not be accepted as cleanup without a decision. | Git status shows many `D` entries; `docs/goals` missing in worktree; `git show HEAD:.../state.yaml` can retrieve prior board contents. | High | eventual delete pending verification | Private/internal workflow material | Decide restore, archive-private, or delete with explicit rationale. |
| GIT-006 | `Documents/execplan_radle_v2_handwritten_panels.md`; handwritten panel scripts | Untracked handwritten producer scripts and plan are reproducibility-relevant because outputs already exist. | Git status shows untracked `scripts/radle_v2_handwritten_stats.py`, `make_radle_v2_handwritten_svg_panels.py`, `audit_radle_v2_handwritten_panels.py`, `build_radle_v2_handwritten_panels.ps1`, and panel ExecPlan. | High | public/internal repo candidate pending review | Not public unless staged/pushed | Preserve or stage only after separate review; do not lose while outputs depend on them. |

## Unresolved Decisions

1. Canonical result root: decide how `results/radle_v2_combined/final`, `outputs/radle_v2_stats/_stale_archive/final_binary_scoring_20260705_010315`, and `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147` relate for manuscript/public packaging.
2. InternVL duplicate: choose canonical path between flat `results/internvl3_5_8b_medical_full_200_cases_ollama` and wrapper `results/internvl_ollama_outputs/...`.
3. Claude Fable duplicate/mirror: choose canonical copy between timestamped wrapper and `results/drive_sources/claude_fable_5_full_200_cases`.
4. `results/radle_v2` versus `results/drive_sources/radle_v2`: decide whether the former is intentionally trimmed or missing copied companions.
5. `results/radle_v2_combined`: decide whether public/scorer/raw companions must be generated before any release.
6. Public release approval: define where completed privacy/publicability review is recorded.
7. Public repo allowlist: decide which docs/notebooks/scripts are public candidates versus internal-only.
8. Deleted `docs/goals/llava-vllm-*`: decide restore, archive-private, or delete explicitly.
9. Handwritten scripts: decide whether to preserve/stage untracked producer scripts after validation.
10. Deliverable manifest: locate or create lineage manifest for `deliverables/radle_v2_long_format_2026-07-04`.

## Cleanup Gates For PASS THREE

Do not delete, move, rename, stage, commit, or push until all relevant gates pass:

1. Canonical path selected and recorded for each duplicate/wrapper pair.
2. Recursive hash comparison completed for each proposed duplicate deletion, including tarballs where relevant.
3. Downstream references searched for every proposed path removal.
4. Private archive sidecar manifest created with hashes for must-preserve packages.
5. Public release privacy review completed and recorded outside vague `privacy_notes`.
6. Ground truth/image/hash release policy decided explicitly.
7. Dirty tracked work reviewed by owner or lane.
8. Secret/local env files confirmed ignored and unstaged.
9. Generated/public artifacts regenerated or verified from preserved producer scripts.
10. ExecPlan updated with the exact action list before cleanup begins.

## Commands Worth Reusing

From repo root:

    git status --short --branch
    git status --ignored --short -uall
    git check-ignore -v -- outputs results deliverables vllm_0_23_0 .venv radle_api_keys.env
    git ls-tree -r --name-only HEAD docs/goals
    rg -n -i "C:\\Users|/home/jupyter|/content/|GITHUB_TOKEN|HF_TOKEN|OPENAI_API_KEY|ANTHROPIC_API_KEY|OPENROUTER_API_KEY|GEMINI_API_KEY|CONFIDENTIAL|private GCP" README.md Documents notebooks scripts src

Use a Python CSV/hash probe with `csv.field_size_limit(2147483647)` for wide raw-response files, because the default CSV field limit fails on large `Raw_Response_*` fields.
