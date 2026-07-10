# RadLE v2 Handwritten SVG Panels

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` was found during intake. The user-provided AGENTS instruction says to use an ExecPlan for complex features, multi-step analyses, or significant refactors and to prefer `Documents/` for repo-local plans.

## Purpose / Big Picture

Build a deterministic RadLE v2 visualization pipeline that turns the authoritative final radiologist adjudication master CSV into a handwritten-style SVG panel artifact set for the active `qual` radiologist-versus-trainee comparison. A reader should be able to rerun the scripts from the repo root and get validated summary CSVs, SVG panels, contact sheet, captions, manifest, provenance, reviewer checklist, font-size record, QA notes, and final reconciliation artifacts under the existing final scoring folder.

The active methodology pivot is that score metrics do not belong in the long master. The long master is an adjudication and evidence table: it can carry correctness adjudication (`final_score_authoritative`), source labels, diagnoses, Likert confidence, abstention, technical-failure flags, and rater identity/seniority. It must not carry old weighted-score logic. Scoring now moves to a separate Score1000 CSV lane, where the new Likert-5 rule is applied fresh.

The active user-facing requirement is now the actual 6+6 role split from the current master: board-certified radiologists versus radiology trainees. The earlier `experience` split was deleted because it creates a 5+7 comparison after moving `6mo post-MD` out of the board-certified radiologist comparator and should not be presented as another radiologist-versus-trainee figure.

The active revision now builds only the approved Score1000-native Panel 2/3 pair: Panel 2 is an edge-justified 200-case stacked ledger with full Likert detail, and Panel 3 is the matching one-line 100-unit barcode-style percentage strip. Earlier three-panel and creative-panel designs are historical and must not be regenerated unless the user explicitly re-approves them.

## Current State

Current state (2026-07-07 19:05 +05:30, Codex/GPT-5): [LEGEND ALIGNMENT PASS COMPLETE] Production Panel 2/3 use a left-side row identity block with Score1000 values and publication-formatted reader/model names. The B3 legend below each panel now uses the same horizontal span as the bar/strip above it, sits directly under that data span, and computes group labels, brackets, and endpoint labels from the supplied span. Audit coverage verifies legend/data-span alignment. The package was regenerated and visually inspected.

## Locked Facts

- Repo root is `C:\Users\thehb\Documents\RadLE v2`.
- Current task branch is `codex/radle-v2-handwritten-panels`.
- The checkout had unrelated dirty files before this task began; do not reset, revert, stage, or edit unrelated files.
- Immutable source input is exactly `C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\radle_v2_final_long_master.csv`; scripts may accept the repo-relative form but provenance and audits must resolve this exact file.
- Source master restart verification on 2026-07-07 12:37 +05:30 verified 6000 rows, 20 columns, SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`, `sum(final_score_authoritative)==1255`, and `weighted_score` still present in the immutable snapshot.
- Clean adjudication source for new Score1000/panel work is `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/radle_v2_clean_adjudication_master.csv`: 6000 rows, 19 columns, no `weighted_score`, same row order and all non-score columns preserved, `sum(final_score_authoritative)==1255`, SHA256 `F49AE40BFC99F77DA5C966F33C16D57778331DAC28F4C318B4158116B0859D87`.
- Authoritative correctness/adjudication is `final_score_authoritative`; it remains in both the immutable source master and the clean adjudication artifact because Score1000 needs it to decide whether a diagnosis is correct or wrong. Score-metric columns do not appear in the clean adjudication artifact or generated Score1000 CSV schemas.
- `qual` grouping: `Radiology Trainees = PGY2, PGY3`; `Post-MD Radiologists = 6mo post-MD, 2y post-MD, 3y post-MD, 4y post-MD, 7y post-MD`.
- The earlier `experience` split (`Early Training / Early Practice = PGY2, PGY3, 6mo post-MD`; `Experienced Post-MD = 2y post-MD, 3y post-MD, 4y post-MD, 7y post-MD`) is not an active artifact target after the user's delete instruction.
- Active known anchors from the current master: `qual` Radiology Trainees `458/1200 = 38.17%`; `qual` Post-MD Radiologists `466/1200 = 38.83%`.
- Prior `qual`, `experience`, `qual_human200`, and `_visual_qa` generated roots were cleaned out of the final scoring folder as stale active outputs. The current final scoring root contains only `radle_v2_final_long_master.csv` and `likert5_score1000`.
- The historical `qual_human200` weighted panel lane is no longer present in the final scoring root and must not be used as the source of truth for new Score1000 or panel work.
- Completed Score1000 scoring lane is `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000`.
- The Score1000 lane is scoring, not rescoring: it starts from the clean adjudication artifact in `likert5_score1000`, not from the old `weighted_score`. It must not preserve, copy, rename, or compare against the old `weighted_score`.
- The new Score1000 row fields should use explicit `score1000_*` names, for example `score1000_row_kind`, `score1000_group`, `score1000_display_label`, `score1000_row_weight`, and `score1000_effective_score`. Do not use the older `normalization_*` naming for this lane.
- New Likert-5 score rule: valid Likert `0..4` maps to weight `1..5`; correct diagnosis scores `+weight`, wrong diagnosis scores `-weight`; true `I don't know` abstention including typo `Idon't know` scores `+1`; invalid Likert such as `8` scores `0` and is flagged; `PARSE_FAILED` technical failure scores `0`.
- For effective `n=200` rows, the new Likert-5 total score range is `-1000..+1000`, and an all-`I don't know` reader baseline is `+200`.
- Existing locked metric logic is in `scripts/radle_metrics.py`; new stats code should import `metrics` from there instead of redefining metric blocks.
- Reference-only handwritten panel source is `C:\Users\thehb\Documents\RadLE Stats\outputs\Data visualization\Handwritten SVG Panels`; do not mutate it.
- Repo-local reference-only copy of old handwritten style files is `scripts/reference/radle_stats_handwritten_svg_panels/`; copied files match the external originals by SHA256 and must not be imported by the active RadLE v2 pipeline.
- Existing Score1000 artifacts record the immutable source master SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED` and the clean adjudication master SHA256 `F49AE40BFC99F77DA5C966F33C16D57778331DAC28F4C318B4158116B0859D87`.
- Old reference panel 2 is a full-case confidence-outcome anatomy: Likert 4 wrong, Likert 4 correct, Likert 1-3 cautious, and abstention/deferred.
- Old reference panel 4 is the same primitive outcomes regrouped as verified safe, safe uncertainty, and misleading hazard.
- Old reference panel 5 is conditional PPV among peak-confidence Likert 4 answers only, with the peak-confidence denominator shown as `n=...`.
- Historical panel design after the earlier cutdown was three panels corresponding to old reference panels 2, 4, and 5; that target is superseded for this slice by the approved Score1000-native Panel 2/3 pair.
- Panels 4-6 (`panel_4_creative_confidence_outcomes.svg`, `panel_5_creative_safety_balance.svg`, `panel_6_creative_peak_certainty_trust.svg`) are no longer active artifacts and must be rejected by audit if regenerated.
- Current approved target supersedes the prior three-panel target for this slice: build only Panel 2 and Panel 3 from the Score1000 lane, then stop for user approval before Panel 4/5 or any other panel generation.
- Panel 2 approved design after user clarification: edge-justified stacked horizontal bar spanning exactly 200 effective cases from left edge to right edge. Bin order is `L4 correct`, `L3 correct`, `L2 correct`, `L1 correct`, `L0 correct`, `neutral`, `L0 wrong`, `L1 wrong`, `L2 wrong`, `L3 wrong`, `L4 wrong`; all widths are effective-count proportions of 200.
- Panel 2 shape invariant for the first approved pair: keep all 11 Likert bins visible; the whole row has a rounded outer silhouette, while all internal bin boundaries are square, flush, and have no per-segment rounding, padding, stroke, or dark seam.
- Panel 3 approved design after user clarification: 100-unit percentage strip with the same 11-bin ordering as Panel 2. The display marks are thin vertical rounded capsules, not tiny dots; all comparator rows use deterministic largest-remainder apportionment from exact 200-case bins to exactly 100 displayed units, while exact effective counts remain in summary/metadata and right-side labels.
- Production Panel 2/3 legend is locked to B3: equal-width 11-bin color bar, group labels `Correct, by confidence`, `I don't know`, `Wrong, by confidence`, endpoint labels `L4 high confidence`, `L0 low confidence`, `L0 low confidence`, `L4 high confidence`, and no design-option/meta commentary.
- Production Panel 2/3 B3 legend must align to the data span above it: Panel 2 legend x/width matches the 200-case bar track; Panel 3 legend x/width matches the 100-capsule strip track. Legend label positions derive from that span, not fixed global coordinates.
- Production Panel 2/3 row identity is locked to a left-side `Score1000 + display name` block: scores are a compact numeric column, and display-formatted reader/model names are right-indented next to those scores. Do not show raw model identifiers with underscores or repeated row-level `n=200` metadata in the visible figure.
- Correct + Likert 0 with diagnosis is not neutral; it is the palest blue correct bin. Wrong + Likert 0 with diagnosis is the palest red wrong bin.
- Neutral center means exact `I don't know`, typo `Idon't know`, technical failure, invalid Likert, diagnosis `PARSE_FAILED`, or Likert `PARSE_FAILED`.
- New Panel 2/3 source of truth is `likert5_score1000/score1000_scored_rows.csv`; the old handwritten `confidence_outcome_summary.csv` path is deprecated for this slice.
- User-supplied visible label target from `C:\Users\thehb\AppData\Local\Temp\codex-clipboard-aaa85bac-80e1-4b4f-924f-62f5b9fca54d.png`: human comparison labels should read `Board-certified radiologists` and `Radiology trainees`.
- Figure-facing SVG titles, subtitles, legends, labels, captions, and contact-sheet captions must not contain process/meta phrases such as `strict old-panel equivalent`, `creative companion`, `old panel`, `old-reference`, `variant`, `implementation`, `generator`, or similar internal commentary.
- Figure-facing SVG titles, subtitles, legends, labels, captions, and contact-sheet captions must use reader-neutral confidence-calibration wording. Banned reader-facing AI-safety metaphors include `Deployment Risk`, `deployed`, `hallucination`, `Safety Shield`, `Verified Safe`, `Protected cases`, `protected`, `hazard`, and `Misleading Hazard`.

## Do Not Revisit

- Do not hand-edit generated SVGs as a fix path. Patch the generator, regenerate, audit, render, and repeat. See Decision Log 2026-07-06.
- Do not use the old `weighted_score` for any new calculation. Use `final_score_authoritative` only as the correctness/adjudication input. See Decision Log 2026-07-07 adjudication-only master pivot.
- Do not recreate `experience` artifacts or label the 5+7 experience split as another radiologist-versus-trainee comparison unless the user explicitly supplies a new master/grouping contract. See Decision Log 2026-07-06.
- Do not silently generate artifacts from hooks. Generation is explicit; gates fail closed. See Decision Log 2026-07-06.
- Do not ship or validate any regenerated six-panel outputs unless the figure-copy gate removes reader-facing meta commentary and applies the user-supplied human labels. See Decision Log 2026-07-06 correction pass.
- Do not trust prior generated summaries for this correction pass; re-read the exact master CSV path and recompute counts before changing the generator. See Decision Log 2026-07-06 correction pass.
- Do not use model-release or AI-hallucination metaphors for reader calibration panels. Radiologists and AI systems should be described as readers, and wrong high-confidence reads should be called `Confident Error`. See Decision Log 2026-07-06 terminology pass.
- Do not create the human-normalized comparator by dropping readers or randomly sampling cases. Use deterministic weights that preserve every original source row and make the effective human denominator `200`. See Decision Log 2026-07-06 human200 pass.
- Do not regenerate or ship the three creative companion panels unless the user explicitly asks for them again. See Decision Log 2026-07-06 three-panel cutdown.
- Do not mutate `radle_v2_final_long_master.csv` in place for Score1000 or panel work. Use the clean adjudication artifact under `likert5_score1000` and keep scoring separate and fresh. See Decision Log 2026-07-07 Score1000 output-lane pivot.
- Do not build Panel 4/5 in this slice. They are planned as later grouped-color replicas of Panel 2/3 only after the user approves the first Panel 2/3 pair. See Decision Log 2026-07-07 Panel 2/3 Score1000 design lock.
- Do not revive `confidence_outcome_summary.csv` as the active data source for the new Panel 2/3 implementation. See Decision Log 2026-07-07 Panel 2/3 Score1000 design lock.
- Do not render Panel 2 as a centerline-anchored diverging bar. The user's reference image means edge-justified 200-case bars. See Decision Log 2026-07-07 Panel 2 edge-justification correction.
- Do not visually club Likert levels in Panel 2 or Panel 3. Clubbed/grouped color grammar belongs to later Panel 4/5 replicas, not the first approved pair. See Decision Log 2026-07-07 Panel 2/3 full-Likert correction.
- Do not render Panel 3 as a two-line 200-dot strip. The user approved a one-line 100-dot percentage strip to preserve left-to-right reading. See Decision Log 2026-07-07 Panel 3 percent-dot correction.
- Do not reintroduce per-segment strokes or dark internal seams in Panel 2. Option B means a rounded row silhouette with seamless square internal fills. See Decision Log 2026-07-07 Option B boundary refinement.
- Do not restore the 7-swatch sampled legend. Panel 2/3 encode 11 visible bins and the production legend must decode that full 11-bin sequence. See Decision Log 2026-07-07 B3 legend lock.
- Do not render the B3 legend as an independently centered ruler. It must be linked to the horizontal span of the chart/strip above it. See Decision Log 2026-07-07 legend alignment pass.
- Do not reintroduce visible raw model identifiers such as `grok_4_3` or repeated row-level `n=200` labels. The visible figure should use formatted model names and a score/name identity block. See Decision Log 2026-07-07 score/name pass.

## Progress

- [x] (2026-07-06 03:06 +05:30, Codex/GPT-5) Performed read-only intake of the final scoring folder, master schema/counts, reference handwritten scripts, existing plans, branch state, and target folder existence.
- [x] (2026-07-06 03:06 +05:30, Codex/GPT-5) Created goal for the full workflow: stats, generator, SVGs, visual QA, iterative fixes, and final audit.
- [x] (2026-07-06 03:06 +05:30, Codex/GPT-5) Ran `git status --short --branch` before branch creation and recorded the dirty checkout receipt in this plan.
- [x] (2026-07-06 03:06 +05:30, Codex/GPT-5) Created branch `codex/radle-v2-handwritten-panels` before task mutations.
- [x] (2026-07-06 03:06 +05:30, Codex/GPT-5) Created this ExecPlan as the first repo-local file mutation.
- [x] (2026-07-06 03:07 +05:30, Codex/GPT-5) Spawned read-only stats and judge subagents with bounded evidence receipts: Stats Scout A `019f3437-6a6f-7693-8ff4-dbdcf64a1ff8`, Stats Scout B `019f3437-b1b3-7012-b06e-2a29f2b70682`, Stats Judge `019f3437-f3a0-7573-8896-b389b3028509`.
- [x] (2026-07-06 03:14 +05:30, Codex/GPT-5) Reconciled subagent receipts: Scout A matched `qual` anchors, Scout B matched `experience` anchors, and Judge approved both contracts plus the critical `6mo post-MD` migration invariant.
- [x] (2026-07-06 03:14 +05:30, Codex/GPT-5) Added and ran `scripts/radle_v2_handwritten_stats.py`; it wrote `group_summary.csv`, `seniority_tier_summary.csv`, and `stats_provenance.json` under both output roots with exact anchor assertions.
- [x] (2026-07-06 03:14 +05:30, Codex/GPT-5) Added deterministic SVG/contact-sheet generator `scripts/make_radle_v2_handwritten_svg_panels.py`; run and audit pending.
- [x] (2026-07-06 03:18 +05:30, Codex/GPT-5) Added explicit read-only gate script `scripts/audit_radle_v2_handwritten_panels.py` and explicit wrapper `scripts/build_radle_v2_handwritten_panels.ps1`.
- [x] (2026-07-06 03:19 +05:30, Codex/GPT-5) Generated complete `qual` and `experience` artifact sets under `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/`.
- [x] (2026-07-06 03:20 +05:30, Codex/GPT-5) Ran the full wrapper end-to-end; all gates passed and fresh visual screenshots were written under `_visual_qa`.
- [x] (2026-07-06 03:20 +05:30, Codex/GPT-5) Inspected the final fresh contact-sheet screenshots and found no visible clipping, hard overlap, unreadable labels, bad legends, or grouping-claim mismatch.
- [x] (2026-07-06 03:20 +05:30, Codex/GPT-5) Ran `py -3.11 -m py_compile` for the three Python scripts and `git diff --check` for task files; both passed.
- [x] (2026-07-06 18:01 +05:30, Codex/GPT-5) Restart verification reran the explicit wrapper; all gates passed against current master SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`.
- [x] (2026-07-06 18:01 +05:30, Codex/GPT-5) Inspected fresh `qual_contact_sheet.png` and `experience_contact_sheet.png`; both rendered cleanly, and the `6mo post-MD` color/group migration was visible and correct.
- [x] (2026-07-06 18:02 +05:30, Codex/GPT-5) Reran `py -3.11 -m py_compile`, `git diff --check`, and a direct trailing-whitespace scan over task text/script files after plan reconciliation; all passed.
- [x] (2026-07-06 18:08 +05:30, Codex/GPT-5) Re-read `~/.codex/PLANS.md`, confirmed no repo-local `AGENTS.md`, ran `git status --short --branch`, and recorded that the branch remains `codex/radle-v2-handwritten-panels` with unrelated dirty files.
- [x] (2026-07-06 18:08 +05:30, Codex/GPT-5) Revised this ExecPlan before script mutation to capture the six-panel scope, old-panel semantics, NEJM-AI-like styling requirement, and path-scoped staging posture.
- [x] (2026-07-06 18:16 +05:30, Codex/GPT-5) Reconciled read-only scout lanes for confidence metrics and old visual grammar; locked non-excluded AI model rows plus two criterion-specific human comparator rows.
- [x] (2026-07-06 18:17 +05:30, Codex/GPT-5) Patched stats generation to emit `confidence_outcome_summary.csv` for model arms and human comparator rows under both `qual` and `experience`.
- [x] (2026-07-06 18:22 +05:30, Codex/GPT-5) Replaced the SVG generator with a six-panel confidence/safety/PPV generator and active-panel cleanup for stale `panel_*.svg` outputs.
- [x] (2026-07-06 18:25 +05:30, Codex/GPT-5) Replaced audit gates to validate six required panel files, reject stale panel outputs, and reconcile SVG metadata/captions/manifest/provenance against `confidence_outcome_summary.csv`.
- [x] (2026-07-06 18:28 +05:30, Codex/GPT-5) Ran the explicit wrapper end-to-end; preflight, stats, post-stats, SVG generation, post-svg, final-reconcile, and visual-qa render passed.
- [x] (2026-07-06 18:28 +05:30, Codex/GPT-5) Inspected fresh contact-sheet screenshots for `qual` and `experience`; after inlining SVGs, all six panels render with no observed blank panels, clipping, hard overlaps, unreadable legends, or grouping-claim mismatch.
- [x] (2026-07-06 18:28 +05:30, Codex/GPT-5) Ran `py -3.11 -m py_compile` for the three Python scripts and `git diff --check` for task paths; both passed.
- [x] (2026-07-06 18:46 +05:30, Codex/GPT-5) Per user correction, marked the previously generated six-panel outputs as blocked pending correction because visible subtitles included process/meta wording and human labels did not match the supplied image.
- [x] (2026-07-06 18:46 +05:30, Codex/GPT-5) Re-read `~/.codex/PLANS.md`, searched relevant memory, ran `git status --short --branch`, and revised this ExecPlan as the first mutation in the correction pass.
- [x] (2026-07-06 18:50 +05:30, Codex/GPT-5) Created a fresh active goal for the correction workflow after tool state showed no active goal, preserving the plan-first mutation order.
- [x] (2026-07-06 18:51 +05:30, Codex/GPT-5) Spawned read-only text/label scout `019f3795-5565-71d1-a34e-0d203a42e2db`; receipt identified visible `Strict old-panel equivalent`, `Creative companion`, and old human group labels in generated SVG/contact/caption text, with no alternate master source path found.
- [x] (2026-07-06 18:52 +05:30, Codex/GPT-5) Re-opened exact master CSV `C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\radle_v2_final_long_master.csv`; verified SHA256 `7641bacc91b1ae9edaca3249507e31a75924624fa8c232685c835af1524f51ed`, shape `(6000, 20)`, and total correct `1255`.
- [x] (2026-07-06 18:53 +05:30, Codex/GPT-5) Patched stats/generator/audit so `confidence_outcome_summary.csv` carries `display_label`, visible labels use `Board-certified radiologists` and `Radiology trainees`, and technical grouping remains available in CSV/provenance/metadata.
- [x] (2026-07-06 18:54 +05:30, Codex/GPT-5) Patched all figure-facing titles/subtitles/captions/contact-sheet captions to remove internal process phrases and added a reader-facing copy gate that rejects banned phrases while ignoring technical metadata.
- [x] (2026-07-06 18:55 +05:30, Codex/GPT-5) Regenerated from the exact master path, reran preflight, post-stats, post-svg, final-reconcile, and visual-qa gates, inspected fresh contact sheets, and confirmed labels/text/numbers are clean.
- [x] (2026-07-06 18:58 +05:30, Codex/GPT-5) Per user screenshot, patched row-label layout so `Board-certified radiologists` and `Radiology trainees` render as single-line labels with a larger `n=` line gap; added a post-SVG structural audit for unwrapped human labels.
- [x] (2026-07-06 18:58 +05:30, Codex/GPT-5) Reran the explicit wrapper from the exact master path; all gates passed and fresh contact sheets show unwrapped human labels with `row-meta` baselines at `y+78`.
- [x] (2026-07-06 19:07 +05:30, Codex/GPT-5) Per user correction, deleted the `experience` artifact root and stale `_visual_qa\experience_contact_sheet.png`; scripts now default to `qual` only and audit fails if the inactive `experience` root exists.
- [x] (2026-07-06 19:07 +05:30, Codex/GPT-5) Reran the explicit wrapper from the exact master path; only `qual` regenerated, and preflight, post-stats, post-svg, final-reconcile, visual-qa, py_compile, and trailing-whitespace checks passed.
- [x] (2026-07-06 19:13 +05:30, Codex/GPT-5) After qual-only plan cleanup, reran the full wrapper successfully and manually inspected the fresh `qual_contact_sheet.png`; no `experience` root or contact sheet was recreated.
- [x] (2026-07-06 19:17 +05:30, Codex/GPT-5) Replaced AI-deployment/safety metaphors in `scripts/make_radle_v2_handwritten_svg_panels.py` with confidence-calibration language, added audit coverage, regenerated active `qual` artifacts, and visually inspected the fresh contact sheet.
- [x] (2026-07-06 22:20 +05:30, Codex/GPT-5) Implemented `qual_human200`: wrote a weighted master/prerequisite CSV with all original master columns plus normalization columns, normalized every count column in group/tier/confidence summaries, regenerated SVGs from normalized summaries, and visually QAed the fresh contact sheet.
- [x] (2026-07-06 22:34 +05:30, Codex/GPT-5) Removed panels 4-6 from the active generator/audit contract, regenerated `qual_human200`, verified stale creative SVGs were deleted, and visually QAed the three-panel contact sheet.
- [x] (2026-07-07 10:55 +05:30, Codex/GPT-5) Looked up the Python path that introduced score-bearing fields: `scripts/radle_llm_judge.py` owns older score application (`weighted_score`, `weighted_score_rule`, and mean weighted summary propagation), while `scripts/radle_v2_finalize_summaries.py` only mutates the already-existing final master for human role/seniority.
- [x] (2026-07-07 10:55 +05:30, Codex/GPT-5) Revised this ExecPlan before the Score1000 pivot; that revision proposed in-place master cleanup, which is now superseded by the completed output-lane clean-master approach recorded below.
- [x] (2026-07-07 12:15 +05:30, Codex/GPT-5) Completed the separate Score1000 lane under `likert5_score1000` via `Documents/execplan_radle_v2_score1000_clean_pipeline.md`: source master stayed unchanged at 6000x20 with SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`; clean adjudication artifact is output-lane-only at 6000x19 with no `weighted_score`; audit passed.
- [x] (2026-07-07 12:23 +05:30, Codex/GPT-5) Cleaned stale generated files from `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147`, leaving only `radle_v2_final_long_master.csv` and `likert5_score1000`.
- [x] (2026-07-07 12:29 +05:30, Codex/GPT-5) Restored the old style-reference split by copying `make_handwritten_svg_panels.py`, `make_handwritten_svg_panels_fixed.py`, and `font_sizes.csv` into `scripts/reference/radle_stats_handwritten_svg_panels/` with matching source SHA256 hashes and a reference-only README.
- [x] (2026-07-07 12:37 +05:30, Codex/GPT-5) Reconciled this handwritten-panel plan to the completed Score1000 lane: no in-place source-master cleanup, no `qual_human200_likert5_score1000`, clean source is `likert5_score1000/radle_v2_clean_adjudication_master.csv`, and future panel rebuilds must start from that lane.
- [x] (2026-07-07 14:53 +05:30, Codex/GPT-5) Locked the approved Score1000-native Panel 2/3 design before code mutation: diverging stacked bar plus matching 200-dot strip, both sourced from `likert5_score1000/score1000_scored_rows.csv`, both totaling 200 effective cases per comparator, and no Panel 4/5 work until user approval.
- [x] (2026-07-07 15:15 +05:30, Codex/GPT-5) Added Score1000-native direction summary generation in `scripts/radle_v2_score1000_panel_stats.py`; it emits `score1000_panel23_bins.csv` plus provenance under `likert5_score1000/handwritten_panels`.
- [x] (2026-07-07 15:19 +05:30, Codex/GPT-5) Added `scripts/make_radle_v2_score1000_panel23_svg.py` to render only Panel 2 and Panel 3, plus contact sheet, captions, manifest, provenance, checklist, font sizes, and QA notes.
- [x] (2026-07-07 15:23 +05:30, Codex/GPT-5) Added `scripts/audit_radle_v2_score1000_panel23.py` and repointed `scripts/build_radle_v2_handwritten_panels.ps1` to the Score1000 Panel 2/3 package.
- [x] (2026-07-07 15:25 +05:30, Codex/GPT-5) Ran the explicit wrapper end-to-end; stats, SVG generation, XML/metadata/data reconciliation, 3400-dot gate, stale-text scan, and Playwright visual QA screenshot all passed.
- [x] (2026-07-07 15:45 +05:30, Codex/GPT-5) User clarified that Panel 2 must be edge-justified like the supplied reference image, not centered around a neutral line; patched generator geometry and added an audit invariant for full-track row span.
- [x] (2026-07-07 15:55 +05:30, Codex/GPT-5) Regenerated and audited the corrected package; Panel 2 now visually spans each row from 0 to 200 effective cases, the stale `Diverging stacked bar ledger` contact-sheet caption is gone, and the visual QA screenshot was refreshed.
- [x] (2026-07-07 16:08 +05:30, Codex/GPT-5) User approved changing Panel 3 to a 100-dot percentage strip because two-line 200-dot wrapping broke the left-to-right color reading; plan locked before code mutation.
- [x] (2026-07-07 16:18 +05:30, Codex/GPT-5) Implemented the 100-dot display contract in stats, generator, audit, captions, provenance, checklist, and filenames; regenerated package; audit confirmed 17 rows x 100 dots = 1700 dots and no row wrapping.
- [x] (2026-07-07 16:32 +05:30, Codex/GPT-5) User approved the Panel 2 row-shape correction: rounded outer row container only, square internal segment cuts; plan locked before code mutation.
- [x] (2026-07-07 16:40 +05:30, Codex/GPT-5) Implemented Panel 2 row-level rounded clip paths and square internal colored segment rectangles; regenerated the package; audit confirmed 17 row clip paths and `rx=0` internal segments.
- [x] (2026-07-07 16:52 +05:30, Codex/GPT-5) User clarified the intended Panel 2 shape as color-family grouping, not row-level rounding: blue block rounded, red block rounded, internal shade cuts square; plan corrected before code mutation.
- [x] (2026-07-07 17:02 +05:30, Codex/GPT-5) Replaced row-level clipping with separate correct-family and wrong-family clip paths; regenerated the package; audit confirmed color-family clips and `rx=0` internal shade rectangles.
- [x] (2026-07-07 17:18 +05:30, Codex/GPT-5) User corrected the scope: Panel 2/3 must keep full Likert-detail grammar, while clubbed/grouped treatments belong to future Panel 4/5; plan revised before code mutation.
- [x] (2026-07-07 17:32 +05:30, Codex/GPT-5) Reverted Panel 2 from color-family clips to row-level clipping with square 11-bin internal cuts; changed Panel 3 from circles to 100 barcode-style capsule bars; regenerated package and visual QA screenshot.
- [x] (2026-07-07 16:20 +05:30, Codex/GPT-5) User selected Option B from the boundary contract sheet: Panel 2 keeps the rounded row silhouette and all 11 Likert bins, but removes per-segment strokes so internal cuts are seamless square fill boundaries; plan locked before code mutation.
- [x] (2026-07-07 16:20 +05:30, Codex/GPT-5) Implemented Option B in `scripts/make_radle_v2_score1000_panel23_svg.py`, tightened `scripts/audit_radle_v2_score1000_panel23.py`, regenerated the package, and inspected the fresh contact sheet. Structural parse confirmed Panel 2 has 118 data segments with `rx=0` and `stroke=none`, plus 17 rounded row outlines.
- [x] (2026-07-07 17:03 +05:30, Codex/GPT-5) User locked B3 from the legend-variant contract sheet for production Panel 2/3; plan updated before code mutation.
- [x] (2026-07-07 17:40 +05:30, Codex/GPT-5) Implemented B3 in `scripts/make_radle_v2_score1000_panel23_svg.py`, added B3-specific audit coverage in `scripts/audit_radle_v2_score1000_panel23.py`, regenerated the package, and inspected the refreshed `score1000_panel23_contact_sheet.png`. Structural parse confirmed both SVGs contain 11 legend bins in the locked order and no old sampled legend labels.
- [x] (2026-07-07 18:04 +05:30, Codex/GPT-5) Fixed Panel 3 right-gutter spacing by moving the totals/header column right, regenerated the package, and re-inspected the fresh contact sheet. The totals no longer overlap or crowd the final barcode capsules.
- [x] (2026-07-07 18:45 +05:30, Codex/GPT-5) Moved visible row identity to a Score1000/display-name block, removed repeated `n=200`, formatted model names for publication-style reading, regenerated the package, and visually inspected the contact sheet.
- [x] (2026-07-07 19:05 +05:30, Codex/GPT-5) Aligned each B3 legend to the exact horizontal span of the data bar/strip above it, computed label positions from that legend span, regenerated the package, and visually inspected the contact sheet.

## Surprises & Discoveries

- Observation: The old reference audit/generator files show mojibake in comments/docstrings when read in this shell, so the v2 audit must scan generated artifacts for mojibake and keep console output ASCII-safe.
  Evidence: `audit_panels.py` displayed strings such as `SVG Panel Audit â€” structural QA`.
  Date/Author: 2026-07-06, Codex/GPT-5

- Observation: Earlier read-only subagent lanes confirmed the grouping invariant, but their recorded `qual` anchors were stale relative to the current master verified during restart.
  Evidence: The 2026-07-06 18:01 wrapper run reported master SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`, `qual` Trainees `458/1200=38.17%`, `qual` Post-MD `466/1200=38.83%`, `experience` Early `524/1400=37.43%`, and `experience` Experienced `400/1000=40.00%`.
  Date/Author: 2026-07-06, Codex/GPT-5 and subagents `019f3437-6a6f-7693-8ff4-dbdcf64a1ff8`, `019f3437-b1b3-7012-b06e-2a29f2b70682`, `019f3437-f3a0-7573-8896-b389b3028509`

- Observation: The first post-SVG audit caught stale reference wording in generated reviewer checklist text.
  Evidence: `post-svg` failed on `reviewer_checklist.md: stale marker 'RadLE Stats'`. The generator wording was patched and regeneration made `post-svg` pass.
  Date/Author: 2026-07-06, Codex/GPT-5

- Observation: Fresh screenshot review caught long-label collisions that XML parsing alone did not flag.
  Evidence: Early contact sheets showed group/member labels kissing chart labels in Panel 2/3. Generator helper copy/layout was patched to compact member labels, wrap `Early Training / Early Practice`, and remove redundant row-level strict/attempted labels.
  Date/Author: 2026-07-06, Codex/GPT-5

- Observation: Restart verification caught stale ExecPlan prose even though the scripts and generated artifacts were already pinned to the current master SHA and anchors.
  Evidence: `scripts/radle_v2_handwritten_stats.py`, `scripts/audit_radle_v2_handwritten_panels.py`, and `scripts/make_radle_v2_handwritten_svg_panels.py` all contain expected SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`; the plan still contained SHA256 `83D469...` and old `qual` anchors until this revision.
  Date/Author: 2026-07-06, Codex/GPT-5

- Observation: Full-page contact-sheet screenshot initially rendered panels 1-2 but left panels 3-6 blank when the sheet used offscreen `<object>` embeds.
  Evidence: Fresh `qual_contact_sheet.png` and `experience_contact_sheet.png` showed blank figure frames for panels 3-6 despite valid SVG XML and individual SVG source. The generator was patched to inline the current SVG source in `contact_sheet.html`; wrapper rerun then rendered all six panels.
  Date/Author: 2026-07-06, Codex/GPT-5

- Observation: User caught figure-facing implementation commentary and label mismatch in the generated panels.
  Evidence: User wrote that graph labels should say `radiologist and trainee` and supplied an image with `Board-certified radiologists` and `Radiology trainees`; user also objected to subtitle text such as `strict old-panel` appearing inside the image itself.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Observable mirror check: The contradicting artifacts are the generated SVG/contact-sheet text under `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147\qual` and `...\experience`, plus the user-supplied image `C:\Users\thehb\AppData\Local\Temp\codex-clipboard-aaa85bac-80e1-4b4f-924f-62f5b9fca54d.png`.
  Missed verification: The prior visual QA checked render completeness, clipping, and grouping but did not include a reader-facing copy audit that bans implementation/process terms or verifies exact human comparator wording against the supplied image.
  User view: The user saw `strict old-panel` wording in the figure subtitle and expected the human labels `Board-certified radiologists` and `Radiology trainees`.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Observation: The correction scout found the expected bad visible copy and no evidence of an alternate master source path.
  Evidence: Scout `019f3795-5565-71d1-a34e-0d203a42e2db` flagged `Strict old-panel equivalent`, `Creative companion`, `Post-MD Radiologists`, `Radiology Trainees`, `Experienced Post-MD`, and `Early Training / Early Practice` in generated visible text; it also reported the expected final long master path in provenance/manifests.
  Date/Author: 2026-07-06, Codex/GPT-5 and scout `019f3795-5565-71d1-a34e-0d203a42e2db`

- Observation: A broad text scan after regeneration still matches technical metadata strings in embedded SVG metadata inside contact sheets.
  Evidence: `rg` finds old technical group names in `<metadata id="radle-panel-data">`, while the new audit's reader-facing parser skips metadata/style/script and passed `post-svg` plus `final-reconcile`.
  Date/Author: 2026-07-06, Codex/GPT-5

- Observation: User screenshot caught cramped two-line wrapping of `Board-certified radiologists` near the left marker, with the `n=` metadata line too close under the label block.
  Evidence: User supplied `C:\Users\thehb\AppData\Local\Temp\codex-clipboard-22505ce7-c7a7-4df3-802d-6b065f9f9d83.png`. Generator `row_label_lines()` was simplified to one-line labels, `row-meta` baseline moved from `y+66` to `y+78`, and the human-row left marker height increased from `72` to `84`.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Observation: The current master at the specified path has a 6+6 role split for `Radiologist` versus `Trainee`, while the earlier `experience` comparator was 5+7 because `6mo post-MD` moved into the early-practice side.
  Evidence: `human_role_summary.csv` reports Radiologist `n_raters=6`, `n=1200`, `n_correct=466` and Trainee `n_raters=6`, `n=1200`, `n_correct=458`. The generated `experience` summary before deletion had Experienced Post-MD `n_raters=5` and Early Training / Early Practice `n_raters=7`, making it unsuitable for identical radiologist/trainee labels.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Observation: Human-normalized bar widths are coherent only after every count-like column is divided by the six-reader denominator, not just the headline `n`.
  Evidence: `qual_human200` group rows show Board-certified radiologists `77.666667/200 = 38.83%` from source `466/1200` and Radiology trainees `76.333333/200 = 38.17%` from source `458/1200`. Panel 2 effective segments for Board-certified radiologists are `32.5`, `148.333333`, and `19.166667`, summing to `200`; trainee segments are `31.5`, `152.333333`, and `16.166667`, also summing to `200`.
  Date/Author: 2026-07-06, Codex/GPT-5

- Observation: The score-bearing column in the current long master comes from the older judge/apply scoring layer, not from the role/seniority finalization script.
  Evidence: `scripts/radle_llm_judge.py` defines `weighted_score(score_binary, likert)` and propagates `weighted_score`, `weighted_score_rule`, and `mean_weighted_score` into long/public outputs. `scripts/radle_v2_finalize_summaries.py` reads `radle_v2_final_long_master.csv`, adds only `rater_seniority` and `rater_seniority_rank`, remaps human `candidate` labels, and writes the same master path back out.
  Date/Author: 2026-07-07, Codex/GPT-5

- Observation: The generator can use exact Fraction arithmetic internally, but CSV export rounds fractional human bins, so the audit must allow tight numeric tolerance when re-reading CSV summaries.
  Evidence: The first Panel 2/3 audit failed because Board-certified radiologists summed to `200000001/1000000` after decimal CSV round-trip. The audit now uses tight tolerance for exported summary totals while independently recomputing all bins from `score1000_scored_rows.csv`.
  Date/Author: 2026-07-07, Codex/GPT-5

- Observation: The phrase `correct reads left, neutral outcomes center, wrong reads right` was interpreted too literally as a center-anchored diverging geometry.
  Evidence: User supplied `C:\Users\thehb\AppData\Local\Temp\codex-clipboard-c9216043-a0c5-4335-a129-5cc20fc973d5.png`, showing bars justified to the left and right edges with neutral as a middle segment inside a full-width 200-case row.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Observation: A strict 200-dot display in Panel 3 creates a misleading wrap artifact.
  Evidence: User supplied `C:\Users\thehb\AppData\Local\Temp\codex-clipboard-b0ae4842-619a-4b32-93cd-070cf45648c0.png`; the second line restarts at the left edge, so red/wrong dots visually appear on the left even though they are logically late in the ordered sequence.
  Date/Author: 2026-07-07, user and Codex/GPT-5

## Decision Log

- Decision: Create a new task branch from the dirty checkout and preserve unrelated changes.
  Rationale: The user requested branch posture before mutation, but the checkout already had unrelated dirty files. A new branch gives task identity without resetting or discarding work.
  Date/Author: 2026-07-06, Codex/GPT-5

- Decision: Keep staging path-scoped for this task.
  Rationale: The pre-branch status showed unrelated notebook, document, and README changes already present in the checkout. Any eventual stage/commit operation must include only this task's files and outputs.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Decision: Build new repo-local scripts instead of adapting the old reference files in place.
  Rationale: The old handwritten panel generator is hardwired to old RadLE Stats paths and data shapes. The v2 workflow needs deterministic scripts rooted in the final scoring master and the v2 grouping contract.
  Date/Author: 2026-07-06, Codex/GPT-5

- Decision: Import `metrics` from `scripts/radle_metrics.py` for summary metric blocks.
  Rationale: The repo already defines locked accuracy, attempted accuracy, Wilson intervals, non-answer decomposition, and weighted-score mean. Reimplementing would create divergence risk.
  Date/Author: 2026-07-06, Codex/GPT-5

- Decision: Generation remains explicit; gates audit and stop bad artifacts.
  Rationale: The user asked that hooks/gates not silently generate unexplained state. Wrapper commands may run explicit phases, but validation scripts should not mutate source truth unexpectedly.
  Date/Author: 2026-07-06, Codex/GPT-5

- Decision: Record master CSV SHA256 in both provenance and manifest artifacts.
  Rationale: Future readers must know exactly which master generated the panels, independent of folder names or timestamps.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Decision: Fix visual defects through the generator only.
  Rationale: Generated SVG files are build outputs and direct edits disappear on regeneration. SVG Panel QA requires generator patch, regenerate all panels, audit XML, then fresh visual render.
  Date/Author: 2026-07-06, Codex/GPT-5

- Decision: Replace the earlier three generated RadLE v2 summary panels with six confidence/safety/PPV panels per criterion for this revision.
  Rationale: The user explicitly asked to create new old-panel-2/4/5 equivalents from the RadLE v2 master and then requested six panels: three strict old-reference versions and three creative-but-conceptually-equivalent versions. Keeping the active artifact set to those six panels avoids stale mixed semantics in the contact sheet and manifest.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Decision: Keep the old visual grammar but tune typography and spacing toward restrained medical-AI publication figures.
  Rationale: The user approved aligned scientific legends/captions and asked to keep font styles good for NEJM AI while using the same graph grammar.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Decision: Use non-excluded AI model arms plus two criterion-specific human comparator rows for the six-panel figures.
  Rationale: `SUMMARY_SPEC.md` defines `access=='excluded'` as duplicate-provider AI twins outside the non-excluded universe. The user request centered on adding radiologist/trainee comparator rows, so the figure universe is the 15 non-excluded AI model arms plus the two human comparator rows for each criterion.
  Date/Author: 2026-07-06, Codex/GPT-5

- Decision: Scale stacked bar widths by each row's denominator while preserving raw count labels and metadata.
  Rationale: Model arms have `n=200`; human comparator rows have `n=1000`, `1200`, or `1400` depending on criterion. Percent-width bars keep rows visually comparable while raw counts and denominators remain visible and reconciled in metadata/captions.
  Date/Author: 2026-07-06, Codex/GPT-5

- Decision: Add a figure-copy correction pass before accepting any regenerated artifact.
  Rationale: Reader-facing scientific figures should not expose build process, variant names, or old-reference implementation notes. Such language belongs, if anywhere, in provenance or manifest metadata, not visible SVG subtitles or captions.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Decision: Use the user-supplied image wording for visible human comparator labels.
  Rationale: The figure should present the human comparators as `Board-certified radiologists` and `Radiology trainees`. Technical group names can remain in support CSVs/provenance when needed for audit, but visible figure text should match the intended reader-facing labels.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Decision: Re-read the exact master path and recompute all counts before patching number logic.
  Rationale: The user stated the numbers were supposed to be different and explicitly supplied the source file path. The correction pass must prove whether the mismatch comes from stale generated summaries, source-path handling, label/group aggregation, or actual master contents.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Decision: Delete the `experience` artifact set and make `qual` the only active handwritten-panel target.
  Rationale: The current master supports the 6+6 radiologist-versus-trainee split through `qual`; the `experience` split is 5+7 and should not be published with the same human labels.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Decision: Replace AI-safety metaphors with reader-neutral confidence-calibration language.
  Rationale: The figures compare whether a reader's stated confidence matches correctness. Terms such as `Deployment Risk`, `hallucination`, `Safety Shield`, `Verified Safe`, and `Misleading Hazard` imply model deployment or release gating and do not apply cleanly to radiologists.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Decision: Implement human normalization as a weighted `qual_human200` lane, not by mutating the master or sampling rows.
  Rationale: The user wants average radiologist and trainee comparators that behave as if each reviewed 200 cases, like model rows. Weighting every original human row by `1 / group_n_raters` preserves all source evidence and all original master columns while making the effective denominator `200` for each human comparator.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Decision: Remove the three creative companion panels and keep only the three old-reference-style panels.
  Rationale: The user explicitly asked to delete the last three creative panels. The generator and audit should encode the smaller active set so stale panels 4-6 cannot silently remain in SVGs, contact sheets, manifests, captions, or provenance.
  Date/Author: 2026-07-06, Codex/GPT-5 and user

- Decision: Keep `radle_v2_final_long_master.csv` immutable for this slice and use an output-lane clean adjudication artifact for Score1000 and future panel work.
  Rationale: The user pivoted scoring out of the long master, but the safer implemented method keeps the original final master unchanged and writes `likert5_score1000/radle_v2_clean_adjudication_master.csv` with only `weighted_score` removed. Fresh Score1000 logic applies only in new `score1000_*` outputs.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Decision: Do not preserve old weighted score semantics under any alternate column name.
  Rationale: Carrying `source_weighted_score`, `normalization_*`, or copied old `weighted_score` fields would keep the retired methodology alive inside the new lane. Provenance should record only the pre-cleanup and post-cleanup hashes and the fact that score metrics were intentionally removed from the master before Score1000 scoring.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Decision: Keep a repo-local reference-only copy of the old RadLE Stats handwritten generator beside the new RadLE v2 generator.
  Rationale: The old script should remain available for visual grammar and style reference, but the RadLE v2 pipeline must use its own deterministic generator and should not mutate or import the old reference files.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Build only Score1000-native Panel 2 and Panel 3 in this slice.
  Rationale: The user approved a new meaning and visual grammar: Panel 2 is an edge-justified correctness/confidence ledger and Panel 3 is the compact percentage-mark equivalent. Panel 4/5 will be grouped-color replicas only after this first pair is approved.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Classify all valid Likert 0-4 diagnosed rows by correctness, not by whether confidence is nonzero.
  Rationale: The user explicitly chose pale blue/pale red for Likert 0 with a diagnosis. Neutral is reserved for IDK, typo IDK, technical failure, invalid Likert, and parse failures.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Panel 2 segment widths and Panel 3 display units encode effective case distribution, not Score1000 contribution.
  Rationale: The user asked for a 200-case distribution ledger across correctness, neutral outcomes, and Likert levels. `final_score1000` remains a row metric in the summary/metadata, but the visual primitive is the effective-case distribution. Panel 2 bar lengths reconcile to 200 effective cases; Panel 3 display units reconcile to 100 percentage units derived from those exact 200-case bins.
  Date/Author: 2026-07-07, Codex/GPT-5

- Decision: Panel 2 bars must be edge-justified, not centerline anchored.
  Rationale: The user's reference image shows each row as one continuous 200-case ledger. Correct bins start at the left edge, neutral sits after the correct bins, and wrong bins continue to the right edge. This preserves the same bins and counts but changes the visual grammar away from a symmetric diverging chart.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Panel 3 displays 100 percentage units, not 200 effective-case dots.
  Rationale: The 200-dot display was exact but visually wrapped, causing wrong/red dots to restart on the left edge of the second row. A 100-dot single-line strip preserves the same bin order and communicates percentage composition while exact 200-case counts remain available in labels, CSV, provenance, and SVG metadata.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Panel 2 uses a row-level rounded clip path and square internal segment rectangles.
  Rationale: The user wants a pill-shaped overall bar without mini-rounded colored segments. A rounded clip path gives only the outside silhouette rounded corners, while internal segment rectangles with `rx=0` create straight, flush vertical boundaries.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Supersede row-level rounding with color-family rounding for Panel 2.
  Rationale: The user clarified that the visual grouping should club blues and reds separately. The blue correct family and red wrong family should each have a rounded group silhouette, while shade cuts inside the blue or red family stay straight and square. Neutral is not part of either rounded family.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Panel 2/3 keep full Likert detail; clubbing is deferred to Panel 4/5.
  Rationale: The user clarified that permission was for five visible Likert levels in the first pair. Any grouped or clubbed blue/red grammar belongs to the later replica panels. Panel 2 should therefore use a row-level outer clip to avoid per-segment rounded bubbles while preserving every internal bin cut. Panel 3 should keep the same 11-bin sequence but render 100 units as thin barcode capsules instead of tiny dots.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Panel 3 uses barcode-style capsule bars for the 100 percentage units.
  Rationale: The dot marks were too small, and increasing dot radius would lengthen the row. Thin vertical capsules preserve the same row width while making each percentage unit more legible.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Panel 2 uses Option B flush internal boundaries.
  Rationale: The boundary-options contract sheet showed that per-segment strokes create dark seams at internal cuts. Option B preserves the full 11-bin Likert data and the rounded row silhouette, while using unstroked segment fills plus a single outer outline so internal boundaries stay square, flush, and visually quiet.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Use B3 as the production Panel 2/3 legend.
  Rationale: The prior production legend sampled only 7 swatches while the panels encode 11 visible bins. The user selected B3 after reviewing the Option B variants because it preserves space for labels while explaining direction through group labels and endpoint confidence labels. The production legend should be an equal-width key, not data-proportional, and should avoid design-option/meta commentary.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Use Score1000 plus display names as the visible row identifier.
  Rationale: The raw model identifiers were visually noisy and scientifically underformatted. Repeated `n=200` metadata is redundant because titles, axes, and captions already state the denominator. A compact score/name block keeps ranking context near the row identity and leaves the mark area cleaner.
  Date/Author: 2026-07-07, user and Codex/GPT-5

- Decision: Link the B3 legend span to each panel's data span.
  Rationale: The legend should read as the key for the bars immediately above it, not as a separate centered graphic. Computing group labels, brackets, and endpoint labels from the same x/width as the data span keeps the visual grammar consistent after future geometry changes.
  Date/Author: 2026-07-07, user and Codex/GPT-5

## Revision Notes

- v1 (2026-07-06, Codex/GPT-5): Initial plan created after read-only intake and branch creation. It captures verified anchors, script/output targets, subagent lanes, validation gates, and iteration rules.
- v2 (2026-07-06, Codex/GPT-5): Recorded the pre-branch dirty status receipt, clarified that the ExecPlan was the first file mutation, added path-scoped staging as a task rule, and added the master-SHA provenance/manifest gate.
- v3 (2026-07-06, Codex/GPT-5): Recorded subagent reconciliation, stats script creation/run, generated stats support files, and SVG generator creation.
- v4 (2026-07-06, Codex/GPT-5): Recorded generator/audit/wrapper completion, caught-and-fixed stale wording and visual label collisions, and added final validation evidence.
- v5 (2026-07-06, Codex/GPT-5): Reconciled stale plan SHA and `qual` anchors against a fresh wrapper run and fresh contact-sheet inspection during restart verification.
- v6 (2026-07-06, Codex/GPT-5): Reopened the plan for the user's six-panel revision: strict old panel 2/4/5 equivalents plus creative companion panels, all driven by RadLE v2 confidence-outcome summaries with human comparator rows.
- v7 (2026-07-06, Codex/GPT-5): Recorded six-panel implementation, confidence CSV outputs, active-panel cleanup, contact-sheet inline SVG rendering fix, wrapper success, visual inspection, compile, and diff-check validation.
- v8 (2026-07-06, Codex/GPT-5): Reopened the plan for a user-caught correction pass. Added blocked current state, observable mirror check, exact master path requirement, image-derived human labels, banned figure-facing meta text, scout lane, recomputation requirement, and audit-gate updates.
- v9 (2026-07-06, Codex/GPT-5): Completed the correction pass. Added `display_label` support, cleaned visible figure copy, added reader-facing banned phrase and label gates, regenerated all outputs from the exact master path, inspected fresh contact sheets, and recorded clean validation.
- v10 (2026-07-06, Codex/GPT-5): Completed the label-wrap visual fix. Human comparator labels now render on one line, `n=` metadata has larger line gap, and `post-svg` asserts the required human labels appear as complete row-label lines.
- v11 (2026-07-06, Codex/GPT-5): Deleted the `experience` artifact set, changed scripts to active `qual` only, added an inactive-root audit guard, reran the qual-only wrapper, and recorded the 6+6 role split evidence.
- v12 (2026-07-06, Codex/GPT-5): Cleaned stale active `experience` references from the plan, reran the full qual-only wrapper, and recorded final manual contact-sheet inspection.
- v13 (2026-07-06, Codex/GPT-5): Opened a terminology correction pass to replace AI-deployment/safety metaphors with reader-neutral confidence-calibration language and audit guards before regeneration.
- v14 (2026-07-06, Codex/GPT-5): Completed the terminology correction pass; visible titles, subtitles, legends, captions, and contact-sheet labels now use calibration wording and the stricter copy gate passed.
- v15 (2026-07-06, Codex/GPT-5): Opened the human200 normalization pass and locked the separate `qual_human200` weighted-lane design before script mutation.
- v16 (2026-07-06, Codex/GPT-5): Completed the human200 normalization pass; stats, generator, audit, provenance, manifest, and visual QA now target `qual_human200` with effective human `n=200` rows and source-count reconciliation for all normalized count columns.
- v17 (2026-07-06, Codex/GPT-5): Opened the three-panel cutdown after the user asked to delete the last three creative panels; active artifacts should now be panels 1-3 only.
- v18 (2026-07-06, Codex/GPT-5): Completed the three-panel cutdown; `qual_human200` now emits and audits only panels 1-3, with captions, manifest, provenance, checklist, contact sheet, and visual QA aligned to the smaller set.
- v19 (2026-07-07, Codex/GPT-5): Opened the stats-only Likert-5 score1000 pass; new CSV lane should be generated before any SVG or figure redesign.
- v20 (2026-07-07, Codex/GPT-5): Reconciled the plan with the locked adjudication-only master pivot. This revision was superseded by the later output-lane clean-master implementation and is retained only as historical context.
- v21 (2026-07-07, Codex/GPT-5): Recorded the reference split fix. Old RadLE Stats handwritten generator files were copied into `scripts/reference/radle_stats_handwritten_svg_panels/` for style reference only, while `scripts/make_radle_v2_handwritten_svg_panels.py` remains the active v2 generator.
- v22 (2026-07-07, Codex/GPT-5): Reconciled stale plan text after Score1000 completion and root cleanup. The plan now points future panel work at `likert5_score1000/radle_v2_clean_adjudication_master.csv`, treats `radle_v2_final_long_master.csv` as immutable source, removes the obsolete `qual_human200_likert5_score1000` target, and records that stale generated panel outputs are no longer present.
- v23 (2026-07-07, Codex/GPT-5): Locked the user-approved Score1000-native Panel 2/3 implementation before code mutation. The plan now supersedes the old three-panel target for this slice and specifies the diverging bar plus 200-dot designs from `likert5_score1000/score1000_scored_rows.csv`.
- v24 (2026-07-07, Codex/GPT-5): Completed the approved Score1000 Panel 2/3 slice. Added the bin summary generator, SVG generator, audit gate, and wrapper wiring; generated the package under `likert5_score1000/handwritten_panels`; rendered the visual QA screenshot; and stopped before Panel 4/5.
- v25 (2026-07-07, Codex/GPT-5): Opened and patched the Panel 2 edge-justification correction. The generator now treats Panel 2 as a full-width 200-case stacked ledger, and the audit checks that segments span each track from left edge to right edge with no centerline.
- v26 (2026-07-07, Codex/GPT-5): Opened the Panel 3 percentage-dot correction. The plan now specifies a one-line 100-dot percentage strip with exact 200-case counts retained outside the display dots.
- v27 (2026-07-07, Codex/GPT-5): Completed the Panel 3 percentage-dot correction. The display-dot target is now 100, old 200-dot filenames are stale, Panel 3 audit requires 1700 total circles with no row wrapping, and the visual QA screenshot was refreshed.
- v28 (2026-07-07, Codex/GPT-5): Opened the Panel 2 outer-radius correction. The plan now requires row-level rounded clipping and square internal segment rectangles, with audit coverage for the internal-corner invariant.
- v29 (2026-07-07, Codex/GPT-5): Completed the Panel 2 outer-radius correction. The generator now clips each row to a rounded outer container while all internal data segments use square corners; the audit enforces both requirements.
- v30 (2026-07-07, Codex/GPT-5): Corrected the Panel 2 shape plan from row-level rounding to color-family rounding after user clarification. The next implementation must clip blue and red families separately and keep neutral square.
- v31 (2026-07-07, Codex/GPT-5): Completed the Panel 2 color-family rounding correction. The generator now clips correct and wrong families separately, keeps neutral square, and the audit enforces family clip ids plus square internal shade segments.
- v32 (2026-07-07, Codex/GPT-5): Opened the full-Likert revision. The plan now supersedes color-family clubbing for Panel 2/3, restores row-level outer rounding with internal 11-bin cuts for Panel 2, and changes Panel 3 from tiny dots to barcode-style percentage capsules.
- v33 (2026-07-07, Codex/GPT-5): Completed the full-Likert revision. Panel 2/3 now preserve all 11 bins; Panel 3 renders 100 barcode capsules; audit rejects circle dots and color-family Panel 2 clip ids.
- v34 (2026-07-07, Codex/GPT-5): Opened the Option B boundary refinement after the contract-sheet review. The plan now requires Panel 2 data segments to be unstroked so the internal Likert cuts are seamless square fill boundaries, with only the row silhouette carrying the outline.
- v35 (2026-07-07, Codex/GPT-5): Completed the Option B boundary refinement. The generator emits unstroked Panel 2 data segments, adds one subtle rounded row outline per comparator, and the audit now fails if internal segments regain a stroke.
- v36 (2026-07-07, Codex/GPT-5): Opened the B3 production legend pass. The plan now locks the equal-width 11-bin B3 legend and requires audit coverage for all encoded bins.
- v37 (2026-07-07, Codex/GPT-5): Completed the B3 production legend pass. The generator and audit now enforce the equal-width 11-bin B3 legend for Panels 2/3, and the regenerated contact sheet was visually reviewed.
- v38 (2026-07-07, Codex/GPT-5): Opened a visual QA spacing fix for Panel 3 because the right-side totals column sits too close to the final barcode capsules.
- v39 (2026-07-07, Codex/GPT-5): Completed the Panel 3 right-gutter visual QA fix. The generator preserves the barcode strip geometry and shifts the totals/header column right for a clear gutter.
- v40 (2026-07-07, Codex/GPT-5): Completed the row identity pass: Score1000/display-name labels, no repeated row-level `n=200`, and no visible raw underscore model IDs.
- v41 (2026-07-07, Codex/GPT-5): Completed the legend alignment pass. B3 legend geometry is parameterized from each panel's data span instead of using fixed centered coordinates, and the audit verifies the alignment.

## Outcomes & Retrospective

The correction, label-wrap, qual-only deletion, terminology, human200 normalization, and three-panel cutdown passes are complete. Regenerated active artifacts use the exact master CSV path, have recomputed and reconciled numbers, display `Board-certified radiologists` and `Radiology trainees` as unwrapped 6+6 human labels, normalize both human comparator rows to effective `n=200`, contain no reader-facing process/meta commentary or AI-safety metaphor language, and pass fresh visual QA render plus manual contact-sheet inspection. The active `qual_human200` contact sheet now contains only panels 1-3; panels 4-6 have been deleted and are rejected as stale extra panel outputs. The `experience` output root and rendered contact sheet have been deleted; audit now fails if the inactive root reappears. No reusable skill should be promoted without explicit user approval; the useful process lessons remain covered by the existing `svg-panel-qa` and `output-artifact-verifier` skills.

The old style-reference split is restored. The external RadLE Stats reference folder remains untouched, and the repo now has a reference-only copy under `scripts/reference/radle_stats_handwritten_svg_panels/`; active panel generation remains in `scripts/make_radle_v2_handwritten_svg_panels.py`.

The Score1000 handoff is reconciled. The completed source lane is `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000`; its clean adjudication master is the source for future scoring-aware panel work. The immutable source master still has 20 columns and remains unchanged. The final scoring root no longer contains generated handwritten panel outputs after cleanup, so any panel package must be explicitly regenerated and audited before use.

The current figure target is implemented and intentionally stopped at the first approved pair. The Score1000-native Panel 2/3 package lives under `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels`; it contains the generated bin summary, Panel 2 SVG, Panel 3 SVG, contact sheet, captions, manifest, provenance, reviewer checklist, font-size record, QA notes, and audit report. Panel 2 is an edge-justified 200-case ledger with a rounded row silhouette and square, flush, unstroked internal 11-bin boundaries. Panel 3 is a one-line 100-unit barcode-capsule percentage strip that preserves exact 200-case counts in labels, CSV, and metadata. Panel 4/5 grouped-color replicas remain deferred until the user approves this first pair.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning and living plan maintenance | `execplan` | Required by user and global plan standard for this multi-step workflow | `auto-suggest` |
| Score1000 source handoff | `none` | Completed clean source and summaries already exist under `likert5_score1000`; future work should consume them rather than mutate the master | `none` |
| Score1000 CSV generation | `none` | Completed in the separate Score1000 plan; rerun the wrapper only if the source snapshot changes intentionally | `none` |
| Score1000 reconciliation | `data-analytics:analyze-data-quality` | Use only if row/status/count reconciliation becomes ambiguous or contradictory | `manual` |
| SVG structure and generator iteration | `svg-panel-qa` | Later only, if the user asks to redraw panels from Score1000 outputs | `manual` |
| Fresh render visual verification | `output-artifact-verifier` | Later only, if new visual artifacts are generated | `manual` |
| Final code review | `none` | Main thread owns final reconciliation; use direct review unless a later defect warrants a specialist | `none` |

## Context And Orientation

This repo contains RadLE v2 benchmark, adjudication, scoring, summary, and handwritten-panel scripts. The final radiologist folder at `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/` was cleaned on 2026-07-07 and now contains only the immutable source master plus the completed `likert5_score1000` scoring lane. The immutable source master still has the retired `weighted_score` column, but the clean adjudication artifact inside `likert5_score1000` removes it and is the active source for future Score1000-aware panel work.

The Score1000 implementation belongs to the separate plan `Documents/execplan_radle_v2_score1000_clean_pipeline.md`. This handwritten-panel plan should not restate an alternate Score1000 pipeline. Its job from here is to preserve the visual grammar decisions and to guide future panel regeneration from the completed `likert5_score1000` lane when the user requests figures again.

The old handwritten SVG panels under `C:\Users\thehb\Documents\RadLE Stats\outputs\Data visualization\Handwritten SVG Panels` are only a visual and structural reference. A repo-local reference copy exists at `scripts/reference/radle_stats_handwritten_svg_panels/`, but those files are not v2-aware and must not be imported by the active RadLE v2 pipeline.

## Plan Of Work

First, keep the source master immutable. Do not patch `scripts/radle_v2_finalize_summaries.py` merely to drop `weighted_score` from `radle_v2_final_long_master.csv`. The clean adjudication source already exists in the Score1000 lane.

Second, use the completed Score1000 lane as the handoff point for any future panel rebuild. The relevant files are:

- `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/radle_v2_clean_adjudication_master.csv`
- `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/score1000_source_rows.csv`
- `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/score1000_scored_rows.csv`
- `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/score1000_group_summary.csv`
- `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/score1000_model_summary.csv`
- `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/score1000_human_comparator_summary.csv`

Third, when the user asks to rebuild panels, patch the active RadLE v2 scripts, not the reference files. The active files are `scripts/radle_v2_handwritten_stats.py`, `scripts/make_radle_v2_handwritten_svg_panels.py`, `scripts/audit_radle_v2_handwritten_panels.py`, and `scripts/build_radle_v2_handwritten_panels.ps1`. The generator should be adapted to the `likert5_score1000` summaries and should continue the three-panel design target unless the user changes the figure scope.

Fourth, regenerate explicitly and run gates. Do not rely on hooks and do not hand-edit SVGs. The expected future path is generator patch, wrapper run, SVG/XML audit, caption/manifest/provenance reconciliation, visual render/contact-sheet QA, then final report.

## Milestones

Milestone 1 uses `execplan`. Outcome: this plan now matches the completed Score1000 lane and no longer instructs in-place master cleanup or the obsolete `qual_human200_likert5_score1000` target.

Milestone 2 uses `none`. Outcome: path-scoped staging preserves reproducibility scripts, plans, and reference-only old style files without staging unrelated dirty work.

Milestone 3 uses `none` for future implementation. Outcome, only after a future explicit request: active RadLE v2 panel scripts consume the `likert5_score1000` lane and emit the expected three-panel artifact package.

Milestone 4 uses `svg-panel-qa` and `output-artifact-verifier` only after panels are regenerated. Outcome: visual artifacts render, labels do not overlap, captions/numbers reconcile, and no stale panel files are present.

## Concrete Steps (Commands)

Run from repo root to confirm the current source/clean handoff:

    py -3.11 -c "import hashlib, pathlib, pandas as pd; root=pathlib.Path(r'outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147'); master=root/'radle_v2_final_long_master.csv'; clean=root/'likert5_score1000'/'radle_v2_clean_adjudication_master.csv'; df=pd.read_csv(master); cdf=pd.read_csv(clean); print('master_rows', len(df)); print('master_cols', len(df.columns)); print('master_has_weighted_score', 'weighted_score' in df.columns); print('master_sha', hashlib.sha256(master.read_bytes()).hexdigest().upper()); print('clean_rows', len(cdf)); print('clean_cols', len(cdf.columns)); print('clean_has_weighted_score', 'weighted_score' in cdf.columns); print('clean_sha', hashlib.sha256(clean.read_bytes()).hexdigest().upper())"

Expected excerpt:

    master_rows 6000
    master_cols 20
    master_has_weighted_score True
    master_sha 7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED
    clean_rows 6000
    clean_cols 19
    clean_has_weighted_score False
    clean_sha F49AE40BFC99F77DA5C966F33C16D57778331DAC28F4C318B4158116B0859D87

Run the Score1000 audit gate when the scoring lane needs a fresh check:

    py -3.11 scripts/audit_radle_v2_likert5_score1000_csvs.py --out-dir outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000

Expected excerpt:

    [PASS] preflight clean adjudication master and source snapshot
    [PASS] stale-score schema gate
    [PASS] cohort and human200 gates
    [PASS] score1000 status and row-score gates
    [PASS] final summary reconciliation
    [PASS] provenance and manifest gates

Before any future panel rebuild, verify the final scoring root is intentionally minimal:

    Get-ChildItem -LiteralPath "outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147" -Force

Expected root entries:

    radle_v2_final_long_master.csv
    likert5_score1000

## Validation And Acceptance

Acceptance for the current reconciliation requires all of the following:

- This plan no longer instructs a future agent to mutate `radle_v2_final_long_master.csv` in place for Score1000.
- This plan no longer names `qual_human200_likert5_score1000` as the active or target Score1000 output.
- The completed Score1000 lane is named `likert5_score1000`.
- The clean adjudication source for new scoring/panel work is `likert5_score1000/radle_v2_clean_adjudication_master.csv`.
- The immutable source master remains 6000 rows, 20 columns, SHA256 `7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED`, with `weighted_score` still present only as historical source metadata.
- The clean adjudication artifact remains 6000 rows, 19 columns, SHA256 `F49AE40BFC99F77DA5C966F33C16D57778331DAC28F4C318B4158116B0859D87`, with `weighted_score` absent.
- The final scoring root contains only `radle_v2_final_long_master.csv` and `likert5_score1000` after stale-output cleanup.
- The repo-local old-panel files under `scripts/reference/radle_stats_handwritten_svg_panels/` are documented as reference-only and not part of the active RadLE v2 pipeline.
- Any staged files are path-scoped to the agreed Score1000, plan, and reference files; unrelated dirty work remains unstaged.

Acceptance for future panel regeneration, when explicitly requested later, will require:

- Active RadLE v2 panel scripts read the `likert5_score1000` lane, not the old `qual_human200` generated outputs.
- SVG panels are regenerated by the generator, not hand-edited.
- Post-SVG XML/metadata checks, final reconciliation, and visual QA pass.
- Reader-facing text continues to use `Board-certified radiologists` and `Radiology trainees`, contains no process/meta commentary, and avoids AI-deployment/safety metaphors.

## Idempotence And Recovery

The source master is not a cleanup target for this slice. If a future run needs to recreate the clean adjudication artifact, rerun the Score1000 wrapper:

    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_radle_v2_score1000_pipeline.ps1

The Score1000 maker owns files under `likert5_score1000`; the audit owns only `score1000_audit_report.json` and `score1000_audit_report.md`. If an audit fails, stop, patch the relevant generator or audit script, rerun the wrapper, and record the evidence in `Documents/execplan_radle_v2_score1000_clean_pipeline.md`.

Future panel generation should be idempotent only after the active RadLE v2 scripts are patched to consume `likert5_score1000`. Until then, do not run the handwritten-panel wrapper as a substitute for this reconciliation. If branch switching or staging is needed later, first run `git status --short --branch` and stage only files belonging to this task. Preserve unrelated dirty files.

## Artifacts And Notes

Read-only intake command evidence:

    ## codex/llava-vllm-runtime...origin/codex/llava-vllm-runtime [ahead 2]
     M Documents/execplan_medical_custom_runtime_colab.md
     M Documents/execplan_medical_workbench_runtime.md
     M README.md
     M notebooks/RadLE_Medical_Custom_Runtime.ipynb
     M notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb
     M notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb
     M notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb
     M notebooks/RadLE_Medical_Workbench_Runtime.ipynb
     M notebooks/RadLE_v1_5_Morning.ipynb

    rows 6000
    cols 20
    sum_final_score_authoritative 1255
    qual Radiology Trainees n=1200 correct=458 accuracy=38.17%
    qual Post-MD Radiologists n=1200 correct=466 accuracy=38.83%

Stats script run evidence:

    [PASS] preflight rows=6000 cols=20 correct=1255
    [PASS] qual Radiology Trainees 458/1200 38.17%
    [PASS] qual Post-MD Radiologists 466/1200 38.83%
    [PASS] wrote stats C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\qual
    [PASS] stats generation complete

Final wrapper evidence (rerun 2026-07-06 19:17 +05:30):

    [RUN] preflight gate
    [PASS] master rows=6000 cols=20 correct=1255 sha256=7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED
    [RUN] stats generation
    [PASS] qual Radiology Trainees 458/1200 38.17%
    [PASS] qual Post-MD Radiologists 466/1200 38.83%
    [RUN] post-stats gate
    [PASS] qual confidence rows: 15 model + 2 human comparator rows
    [RUN] SVG generation
    [PASS] generated confidence panels C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\qual
    [RUN] post-svg gate
    [PASS] qual panel_1_strict_confidence_outcomes.svg XML/metadata/hash
    [PASS] qual panel_2_strict_safety_shield.svg XML/metadata/hash
    [PASS] qual panel_3_strict_peak_certainty_ppv.svg XML/metadata/hash
    [PASS] qual panel_4_creative_confidence_outcomes.svg XML/metadata/hash
    [PASS] qual panel_5_creative_safety_balance.svg XML/metadata/hash
    [PASS] qual panel_6_creative_peak_certainty_trust.svg XML/metadata/hash
    [RUN] final-reconcile gate
    [PASS] qual captions, manifest, provenance, and SVG metadata reconcile to confidence CSV
    [RUN] visual-qa render gate
    [PASS] rendered C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\_visual_qa\qual_contact_sheet.png
    [PASS] RadLE v2 handwritten panel build complete

Human200 wrapper evidence (rerun 2026-07-06 22:20 +05:30):

    [RUN] preflight gate
    [PASS] master rows=6000 cols=20 correct=1255 sha256=7641BACC91B1AE9EDACA3249507E31A75924624FA8C232685C835AF1524F51ED
    [RUN] stats generation
    [PASS] qual_human200 Radiology Trainees 76.33/200.00 38.17%
    [PASS] qual_human200 Post-MD Radiologists 77.67/200.00 38.83%
    [RUN] post-stats gate
    [PASS] qual_human200 confidence rows: 15 model + 2 human comparator rows
    [RUN] SVG generation
    [PASS] generated confidence panels C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\qual_human200
    [RUN] post-svg gate
    [PASS] qual_human200 panel_1_strict_confidence_outcomes.svg XML/metadata/hash
    [PASS] qual_human200 panel_2_strict_safety_shield.svg XML/metadata/hash
    [PASS] qual_human200 panel_3_strict_peak_certainty_ppv.svg XML/metadata/hash
    [PASS] qual_human200 panel_4_creative_confidence_outcomes.svg XML/metadata/hash
    [PASS] qual_human200 panel_5_creative_safety_balance.svg XML/metadata/hash
    [PASS] qual_human200 panel_6_creative_peak_certainty_trust.svg XML/metadata/hash
    [RUN] final-reconcile gate
    [PASS] qual_human200 captions, manifest, provenance, and SVG metadata reconcile to confidence CSV
    [RUN] visual-qa render gate
    [PASS] rendered C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\_visual_qa\qual_human200_contact_sheet.png
    [PASS] RadLE v2 handwritten panel build complete

Human200 visual inspection evidence:

    Latest contact sheet reviewed at C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\_visual_qa\qual_human200_contact_sheet.png.
    Human rows are labeled `n=200 avg (6 readers)`.
    Panel 2 Board-certified radiologists segments are 32.5, 148.3, and 19.2 out of 200.
    Panel 2 Radiology trainees segments are 31.5, 152.3, and 16.2 out of 200.

Three-panel cutdown evidence (rerun 2026-07-06 22:34 +05:30):

    [RUN] post-svg gate
    [PASS] qual_human200 panel_1_strict_confidence_outcomes.svg XML/metadata/hash
    [PASS] qual_human200 panel_2_strict_safety_shield.svg XML/metadata/hash
    [PASS] qual_human200 panel_3_strict_peak_certainty_ppv.svg XML/metadata/hash
    [RUN] final-reconcile gate
    [PASS] qual_human200 captions, manifest, provenance, and SVG metadata reconcile to confidence CSV
    [RUN] visual-qa render gate
    [PASS] rendered C:\Users\thehb\Documents\RadLE v2\outputs\radle_v2_stats\final_scoring_radiologist_20260706_001147\_visual_qa\qual_human200_contact_sheet.png
    [PASS] RadLE v2 handwritten panel build complete

The output folder now contains exactly:

    panel_1_strict_confidence_outcomes.svg
    panel_2_strict_safety_shield.svg
    panel_3_strict_peak_certainty_ppv.svg

Manual visual inspection of the fresh contact sheet found only the three retained panels, with no obvious clipping, hard overlap, or unreadable labels.

Final code checks:

    py -3.11 -m py_compile scripts/radle_v2_handwritten_stats.py scripts/make_radle_v2_handwritten_svg_panels.py scripts/audit_radle_v2_handwritten_panels.py
    Select-String -Path <task text/script files> -Pattern '[ \t]+$'

All checks exited 0 after the 2026-07-06 19:17 terminology confirmation pass. `git diff --check` was not used as the primary whitespace gate because the task files are untracked; the direct trailing-whitespace scan covered the task text and script files.

## Interfaces And Dependencies

New Python scripts should use the standard library plus existing repo dependencies. `scripts/radle_v2_handwritten_stats.py` may use pandas because existing stats scripts do. Visual rendering may use browser/SVG tooling available locally; if a dependency is missing, the audit should record that visual rendering could not be completed rather than pretending structural XML checks are enough.
