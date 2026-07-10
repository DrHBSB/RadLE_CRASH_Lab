# RadLE v2 Temporary Final Scoring Version

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `AGENTS.md` or `PLANS.md` file was found in this repository; the user-provided AGENTS instruction says to place ExecPlans under `Documents/` when available.

## Purpose / Big Picture

The goal is to create a sibling candidate version of `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147` for temporary 3.5 / 5.4 style follow-on work without mutating the official final scoring folder. The candidate folder should contain its own `radle_v2_final_long_master.csv`, receipt metadata, and derived `likert5_score1000/` outputs so later figure/stat scripts can point at the new folder as if it were a normal final-scoring version.

## Current State

Current state (2026-07-08 16:44 +05:30, Codex/GPT-5): Candidate folder `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0` exists with a copied `radle_v2_final_long_master.csv`, root receipt, and regenerated `likert5_score1000_IDK0/` lane. The earlier temp folder `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_temp_3_5_5_4` has been deleted by the user and is no longer active. Next: point any 3.5 / 5.4 figure or stats scripts only at the IDK0-named sibling folder.

## Locked Facts

- Official source master path is `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/radle_v2_final_long_master.csv`.
- The official source master has 6000 rows and the locked SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`.
- The existing Score1000 wrapper accepts `-InputMaster` and `-OutDir`, so it can target a sibling candidate folder.
- The new candidate folder must be a sibling under `outputs/radle_v2_stats/`, not a child of the official folder.
- Candidate master SHA matches the official master SHA: `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`.
- IDK0 candidate folder `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0` was initialized on 2026-07-08 16:25 +05:30.
- IDK0 canonical output lane is `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0`.
- The earlier temp folder `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_temp_3_5_5_4` has been deleted by the user and should not be referenced as an active source.
- In the canonical IDK0 lane, 693 exact/typo IDK rows have unique raw score `[0]`, effective score sum `0.0`, provenance `idk_exact_or_typo` `0`, and all-IDK baseline `0`.
- Canonical IDK0 audit report has `"result": "pass"`.

## Do Not Revisit

- Do not mutate or rename `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147`; use a sibling candidate folder. See Decision Log 2026-07-08.
- Do not copy stale derived outputs as authoritative; regenerate derived `likert5_score1000/` files from the candidate master. See Decision Log 2026-07-08.
- Do not leave README-only IDK0 changes without regenerated CSVs; the row-level CSV, summaries, provenance, manifest, and audit must all be regenerated with `--idk-score 0`. See Decision Log 2026-07-08 IDK0.

## Progress

- [x] (2026-07-08 16:14 +05:30, Codex/GPT-5) Read the ExecPlan standard and confirmed no repo-local `AGENTS.md` or `PLANS.md` files exist.
- [x] (2026-07-08 16:14 +05:30, Codex/GPT-5) Verified the existing Score1000 wrapper can take custom input and output paths.
- [x] (2026-07-08 16:15 +05:30, Codex/GPT-5) Added `scripts/build_radle_v2_temp_final_scoring_version.py` for conservative sibling-folder initialization.
- [x] (2026-07-08 16:15 +05:30, Codex/GPT-5) Ran the builder and created `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_temp_3_5_5_4`.
- [x] (2026-07-08 16:16 +05:30, Codex/GPT-5) Ran Score1000 generation and audit against the candidate folder.
- [x] (2026-07-08 16:18 +05:30, Codex/GPT-5) Recorded final artifact paths and validation evidence in this plan.
- [x] (2026-07-08 16:24 +05:30, Codex/GPT-5) Parameterized Score1000 generator and audit with `--idk-score`, defaulting to old `1` but enabling IDK0.
- [x] (2026-07-08 16:26 +05:30, Codex/GPT-5) Added `scripts/build_radle_v2_score1000_idk0_pipeline.ps1` and ran it into `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0`.
- [x] (2026-07-08 16:30 +05:30, Codex/GPT-5) Re-ran the IDK0 wrapper into the earlier temp folder's `likert5_score1000` lane so README/provenance/CSVs all agree.
- [x] (2026-07-08 16:31 +05:30, Codex/GPT-5) Verified both IDK0 lanes: audit pass, 693 IDK rows, IDK raw score `[0]`, IDK effective score sum `0.0`, all-IDK baseline `0`.
- [x] (2026-07-08 16:44 +05:30, Codex/GPT-5) Verified the user-deleted temp folder is absent and the canonical IDK0 folder/lane remain present and audited.

## Surprises & Discoveries

- Observation: `scripts/radle_v2_finalize_summaries.py` is only the later human role/seniority fixer and is not the workbook-to-master builder.
  Evidence: The script reads and rewrites `radle_v2_final_long_master.csv` in place and only adds/remaps `candidate`, `rater_seniority`, and `rater_seniority_rank`.
  Date/Author: 2026-07-08, Codex/GPT-5

## Decision Log

- Decision: Create a sibling folder under `outputs/radle_v2_stats/` instead of any `_temp` subdirectory.
  Rationale: The user explicitly preferred a new version of `final_scoring_radiologist_20260706_001147`; a sibling folder behaves like a normal candidate version while preserving the official folder.
  Date/Author: 2026-07-08, user and Codex/GPT-5

- Decision: Initialize the candidate master by byte-copying the official master first, then regenerate downstream Score1000 outputs in the candidate folder.
  Rationale: The exact new overlay rows are not yet specified in a machine-readable source, but later scripts need a structurally valid candidate lane now. Regenerating downstream outputs avoids treating old derived files as current.
  Date/Author: 2026-07-08, Codex/GPT-5

- Decision: Make IDK0 a parameterized scoring mode instead of overwriting the old default mode.
  Rationale: The old +1 lane remains reproducible by default, while the new IDK0 lane can regenerate every dependent CSV/provenance/audit artifact with a consistent raw IDK score and all-IDK baseline of 0.
  Date/Author: 2026-07-08, user and Codex/GPT-5

## Revision Notes

- v1 (2026-07-08, Codex/GPT-5): Created this plan for the temp final-scoring sibling lane.

## Outcomes & Retrospective

Pending. At completion, record the exact candidate folder path, whether Score1000 audit passed, and whether any reusable lesson should be promoted to a skill.

Outcome (2026-07-08 16:18 +05:30, Codex/GPT-5): The sibling candidate lane was created and validated. The exact folder is `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_temp_3_5_5_4`. The candidate master has 6000 rows, 20 columns, correct total 1255, and SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`. The generated Score1000 audit report has `"result": "pass"`. No reusable cross-project skill lesson was identified.

Outcome (2026-07-08 16:31 +05:30, Codex/GPT-5): IDK0 scoring is implemented and regenerated. The canonical IDK0 folder is `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0`, with Score1000 outputs in `likert5_score1000_IDK0`. The previous temp lane was also regenerated with IDK0 to avoid inconsistent README/CSV evidence. Both audit reports pass.

Outcome (2026-07-08 16:44 +05:30, Codex/GPT-5): The user deleted `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_temp_3_5_5_4`. Verification confirmed it is absent, while `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0` and `likert5_score1000_IDK0` remain present. The canonical lane still audits as pass with IDK raw score `[0]` and all-IDK baseline `0`.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | The user asked for a multi-step data artifact lane where state must survive context compaction. | `manual` |
| Implementation | `none` | Direct Python and PowerShell work is sufficient. | `none` |
| Validation | `none` | Existing repo scripts provide the validation gates. | `none` |

## Context And Orientation

The RadLE v2 stats artifacts live under `outputs/radle_v2_stats/`. The official final-scoring folder is `final_scoring_radiologist_20260706_001147`; the active sibling candidate folder is `final_scoring_radiologist_20260708_161500_IDK0`.

The candidate folder starts with a copy of `radle_v2_final_long_master.csv`. The existing Score1000 pipeline is then run with:

    powershell -ExecutionPolicy Bypass -File scripts/build_radle_v2_score1000_pipeline.ps1 -InputMaster <candidate>/radle_v2_final_long_master.csv -OutDir <candidate>/likert5_score1000

## Plan Of Work

Add `scripts/build_radle_v2_temp_final_scoring_version.py`. The script will validate the official master, create a new sibling folder, copy the master, write `temp_final_scoring_version_receipt.json`, and write a short root `README.md`. It will not run downstream scoring itself.

Run the existing `scripts/build_radle_v2_score1000_pipeline.ps1` against the candidate master and candidate `likert5_score1000` out-dir.

## Concrete Steps (Commands)

From repo root:

    py -3.11 -m py_compile scripts/build_radle_v2_temp_final_scoring_version.py
    py -3.11 scripts/build_radle_v2_temp_final_scoring_version.py --dest-name final_scoring_radiologist_20260708_161500_IDK0
    powershell -ExecutionPolicy Bypass -File scripts/build_radle_v2_score1000_idk0_pipeline.ps1 -InputMaster outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/radle_v2_final_long_master.csv -OutDir outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0

Expected proof:

    [PASS] initialized temp final scoring version
    [PASS] RadLE v2 Score1000 IDK0 pipeline complete

## Validation And Acceptance

Success means the new sibling folder exists, contains a 6000-row `radle_v2_final_long_master.csv` with the same SHA as the official source master, contains a receipt JSON naming both source and destination, and contains a complete `likert5_score1000/` lane that passes the existing Score1000 audit.

## Idempotence And Recovery

The builder refuses to overwrite an existing candidate folder. If a run is interrupted after folder creation but before Score1000 generation, rerun only the Score1000 wrapper with the same `-InputMaster` and `-OutDir`. To create a fresh candidate, use a new `--dest-name`.

## Artifacts And Notes

Builder output:

    [PASS] initialized temp final scoring version
    folder outputs\radle_v2_stats\final_scoring_radiologist_20260708_161500_IDK0
    master outputs\radle_v2_stats\final_scoring_radiologist_20260708_161500_IDK0\radle_v2_final_long_master.csv
    sha256 7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED
    rows 6000

Score1000 IDK0 wrapper output ended with:

    [PASS] audited outputs\radle_v2_stats\final_scoring_radiologist_20260708_161500_IDK0\likert5_score1000_IDK0
    [PASS] RadLE v2 Score1000 IDK0 pipeline complete

Final verification:

    deleted_temp_folder_present False
    idk0_folder_present True
    idk0_lane_present True
    master_sha 7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED
    audit pass
    idk_rows 693
    idk_raw_unique [0]
    idk_effective_sum 0.0
    provenance_idk_rule 0
    all_idk_baseline 0
    group_rows 17

## Interfaces And Dependencies

The builder depends on Python 3.11, pandas, and the existing source master at `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/radle_v2_final_long_master.csv`.
