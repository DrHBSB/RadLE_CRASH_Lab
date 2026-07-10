# Isolate IDK0 Score2000 SVG Lane

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. The repo has no repo-local `PLANS.md`.

## Purpose / Big Picture

The user needs the IDK0 experiment to stop contaminating the shared/original Score1000 scripts and outputs. The deliverable is an IDK0-only scoring and SVG lane that uses IDK score 0, a derived `score2000 = final_score1000 + 1000` display column, one pooled `Human Expert Baseline`, and 16 comparator rows. Before applying the fixes, preserve and render the current stale IDK0 SVG state so the user can compare the old Score1000/net-score panels with the corrected Score2000 panels.

## Current State

Current state (2026-07-09 02:50 +05:30, Codex/GPT-5): The official IDK0 lane remains `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0`. The full IDK0 wrapper completes successfully against the official folder. Score2000 vertical bar panels use `Score2000=0` as the bar origin and keep the real score values unchanged; only the SVG value-to-y pixel mapping is kinked. Panels 5.0, 5.1, 5.4, 5.5, 5.6, 6.0, 6.1, 6.2, and 6.3 now use A1 broken-axis ticks `[0, 500, 1000, 2000]`, break after 1000, compress the 1000..2000 region into the top 18% of chart height, draw the y-axis as two vertical segments, and render two diagonal slash marks at the break. Public-facing bar-panel text avoids a visible `Score2000` title/axis: 5.0/5.1/5.4/5.5 use `Confidence-weighted diagnosis correctness`, 5.6 and 6.2 use `Open-access models vs 12 radiologists/trainees`, 6.0 uses `Models through MedGemma vs 12 radiologists/trainees`, 6.1 uses `Closed/API models vs 12 radiologists/trainees`, 6.3 uses `Closed/API + open-access models through MedGemma vs 12 radiologists/trainees`, and all bar panels use y-axis `Confidence-weighted diagnosis score`. The footer spells out `"I don't know"` and explains that those, blanks, and failures score 0 before display shifting; the all-`"I don't know"` displayed baseline is 1000. The promoted 5.4 panel is a real vector SVG overlay with bottom logos, not a one-PNG wrapper, and now uses the same closed/API roster and default locked model colors as 6.1: Human, Claude, Grok, Gemini, GPT-5.5, Qwen, and GLM. Panels 5.6, 6.1, 6.2, and 6.3 exist as first-class IDK0 variants: 6.1 shows the human baseline plus six closed/API generalist models; 5.6 and 6.2 show the human baseline plus nine open-access/open models including the open medical models; 6.3 shows the human baseline plus all closed/API and open-access/open models through MedGemma, excluding Llama, InternVL, and Mistral. The 5.4/5.6/6.x logos/badges bind by `reader_label`, use Palette A from `model_bar_color_contact_sheet.json` where locked, sit below the x-axis names, and now use `human_expert_baseline_deep_crimson_logo.png` for the pooled Human Expert Baseline icon. Score labels now remain above bars unless they would leave the chart top; the Human Expert Baseline `988.7` label in 5.6 and 6.2 sits above the red bar like the model labels. The latest layout pass merges the footer's display-scale sentence onto the same line as the `"I don't know"` shifting sentence, increases visible score labels to 44 px, increases model names to 40 px with 48 px line spacing, moves tick labels left to x=310, and moves the y-axis title left to x=185. The latest vertical-scale pass keeps the 2000 endpoint fixed, keeps the 5.1/5.4/5.5/5.6/6.x bottom axis at y=2150, moves their chart top from y=610 to y=540, grows chart height from 1540 to 1610, expands the 0/500/1000 spacing to 660.1 px, and reduces the header-to-plot whitespace.

Current state update (2026-07-09 03:11 +05:30, Codex/GPT-5): Panel 6.3 now uses the all-in-one public title `Confidence-Weighted Diagnosis Scores: AI Models vs Human Expert Baseline`. The full IDK0 wrapper completed successfully after this title cleanup, the 6.3 roster and logo bindings remain unchanged, and the title fits in the regenerated PNG without touching the header logos or plot.

Current state update (2026-07-09 03:51 +05:30, Codex/GPT-5): Panel 6.4 is now a first-class all-model bottom-logo chart with the title `Confidence-Weighted Diagnosis Scores: All AI Models vs Human Expert Baseline`. It shows the pooled Human Expert Baseline plus all 15 evaluated AI models in score/rank order, including Llama 4 Maverick, InternVL 3.5 8B, and Mistral Large 3 2512. The 6.4 x-axis labels use a panel-local 30 px font and 38 px line spacing so the 16 labels remain readable without changing the other vertical bar panels.

Current state update (2026-07-09 03:56 +05:30, Codex/GPT-5): Panel 6.4 now keeps the standard bottom-logo icon scale at `bar_logo_scale=1.25`, matching Panels 5.6, 6.1, and 6.2. The full IDK0 wrapper and SVG audit pass after the icon-scale change, and visual inspection shows the larger icons remain clear of the x-axis names and footer.

Current state update (2026-07-09 04:31 +05:30, Codex/GPT-5): Panels 6.1, 6.2, and 6.4 now use the requested VLM public titles while staying inside the IDK0 lane. Panel 6.1 is `Proprietary Frontier Vision Language Models (VLMs) vs Human Expert Baseline`, Panel 6.2 is `Open-Weights Vision Language Models (VLMs) vs Human Expert Baseline`, and Panel 6.4 is `Frontier Vision Language Models (VLMs) vs Human Expert Baseline`. The full IDK0 wrapper completed successfully, the SVG audit report result is `pass` at `2026-07-08T23:01:03+00:00`, and XML checks confirmed exact `<title>` plus visible title text matches and zero footer/footer-divider elements for all three panels. The open-model constant was split so Panel 5.6 retains its prior `Open-access models vs 12 radiologists/trainees` title.

Current state update (2026-07-09 04:44 +05:30, Codex/GPT-5): Panels 6.1, 6.2, and 6.4 now use a no-footer chart height of `1700.0`, up from the shared `1610.0`, while keeping the chart top fixed at `540.0`. The bar origin/bottom moves from `2150.0` to `2240.0`, increasing the Human Expert Baseline bar from `1305.2` px to `1378.2` px. XML checks confirm `FooterElements=0` for 6.1, 6.2, and 6.4, and Panel 5.6 remains at the non-requested `1610.0` chart height. The full IDK0 wrapper completed successfully and the stricter SVG audit report result is `pass` at `2026-07-08T23:14:40+00:00`.

Current state update (2026-07-09 05:02 +05:30, Codex/GPT-5): Panel 6.3 now has an opt-in Human-vs-top-AI gap overlay while keeping scoring, ranking, Score2000 values, roster, footer explanation, and broken-axis math unchanged. The top AI is selected dynamically from visible 6.3 rows where `reader_type == "AI model"` and max `score2000`; current metadata records Human Expert Baseline `988.666667`, top AI `claude_fable_5` / `Claude Fable 5` at `758.0`, gap `230.666667`, displayed label `231 point Human-AI gap: July 10, 2026`, human line color `#a61e2e`, and top-AI line color `#d97757`. The overlay is drawn after the y-axis title and before the first bar, and the full IDK0 wrapper completed successfully.

Current state update (2026-07-09 10:33 +05:30, Codex/GPT-5): Panel 6.3 footer text and footer divider are now removed. Its chart height now uses the no-footer `1700.0` px geometry, moving the chart bottom from `2150.0` to `2240.0`; the bottom-logo row moves to y=`2490.0` to preserve label/logo clearance. XML checks confirm `show_footer=False`, `use_variant_footer=False`, footer text count `0`, footer divider count `0`, `chart_h=1700.0`, max x-label y `2366.0`, min logo y `2439.2`, and label/logo clearance `73.2` px. The 6.3 Human-AI gap overlay values remain Human `988.666667`, top AI `claude_fable_5` at `758.0`, and label `231 point Human-AI gap: July 10, 2026`.

## Locked Facts

- The active IDK0 output root is `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0`.
- Current corrected IDK0 artifacts are under `likert5_score1000_IDK0`.
- The before-state snapshot is preserved outside the official folder at `before_state_score1000_net_score_IDK0_20260708_183000`.
- The current corrected implementation is in IDK0-specific script copies and the IDK0 wrapper; shared/original script promotion remains out of scope unless explicitly requested.
- `py -3.11` is the reliable local Python command for this repo.

## Do Not Revisit

- Do not hand-edit generated `.svg` files. Fix or run generators and treat SVGs as build output. See Decision Log 2026-07-08.
- Do not run corrected IDK0 logic through shared/original script paths after the boundary agreement. See Decision Log 2026-07-08.
- Do not overwrite the stale before-state panels; snapshot them into a separate folder first. See Decision Log 2026-07-08.

## Progress

- [x] (2026-07-08 18:28 +05:30, Codex/GPT-5) Confirmed current IDK0 artifacts are Score1000/net-score, IDK0, negative-axis, split-human outputs.
- [x] (2026-07-08 18:28 +05:30, Codex/GPT-5) Read SVG panel QA, output artifact verifier, ExecPlan rules, and checked that Playwright/Pillow are available.
- [x] (2026-07-08 18:30 +05:30, Codex/GPT-5) Snapshot and render current before-state IDK0 SVGs into `likert5_score1000_IDK0/before_state_score1000_net_score_IDK0_20260708_183000`.
- [x] (2026-07-08 18:31 +05:30, Codex/GPT-5) Create IDK0-only copies/wrapper from the corrected working scripts.
- [x] (2026-07-08 18:32 +05:30, Codex/GPT-5) Restore tracked shared Score1000 scripts to staged/shared baseline so original behavior is not changed by IDK0 work.
- [x] (2026-07-08 18:35 +05:30, Codex/GPT-5) Regenerate corrected IDK0 CSVs and SVG panels only inside `s2k_IDK0`.
- [x] (2026-07-08 18:40 +05:30, Codex/GPT-5) Run focused CSV/SVG structural checks and provide before/after paths for user review.
- [x] (2026-07-08 18:47 +05:30, Codex/GPT-5) Update and rerun `scripts/build_radle_v2_score1000_idk0_pipeline.ps1` with no `-OutDir` override; it completed successfully against `s2k_IDK0`.
- [x] (2026-07-08 18:53 +05:30, Codex/GPT-5) After the file lock was released, move before-state out, recreate `likert5_score1000_IDK0`, rerun the IDK0 pipeline there, rename IDK statuses from `reward` to `zero`, and remove obsolete scratch folders.
- [x] (2026-07-08 20:12 +05:30, Codex/GPT-5) Fix IDK0 Panel 5.4 generation so logo order/scores derive from `score1000_panel23_bins.csv`, promoted 5.4 is a real vector SVG overlay, and `figure_manifest.json` records 5.4.
- [x] (2026-07-08 20:12 +05:30, Codex/GPT-5) Extend the IDK0 SVG audit/report/render path to validate promoted 5.4 structure, order, manifest coverage, and rendered PNG output.
- [x] (2026-07-08 20:12 +05:30, Codex/GPT-5) Rerun downstream IDK0 panel stats, SVG variants, 5.4 promotion, and tightened SVG audit from the existing official IDK0 CSV package.
- [x] (2026-07-08 20:16 +05:30, Codex/GPT-5) Fix promoted 5.4 footer wording from stale row-label language to vertical bar-label language and add an audit guard for the footer text.
- [x] (2026-07-08 20:16 +05:30, Codex/GPT-5) Append promoted 5.4 to the main contact sheet, captions, data provenance, provenance JSON, and reviewer checklist; audit now checks those support files.
- [x] (2026-07-08 20:30 +05:30, Codex/GPT-5) Rerun the full wrapper after `score1000_group_summary.csv` was released so every official CSV and SVG/PNG panel is rewritten in the same pass.
- [x] (2026-07-08 20:30 +05:30, Codex/GPT-5) Correct Panel 5.x Score2000 bar geometry so bars rise from the 0 baseline; add audit guards and independent geometry checks for 5.0, 5.1, 5.5, and promoted 5.4.
- [x] (2026-07-08 20:30 +05:30, Codex/GPT-5) Replace positional 5.4 ribbon placement with `reader_label`-bound placement using parsed SVG bar slots, explicit logo catalog entries, and audit guards for bound bar label, source logo, center x, and guide color.
- [x] (2026-07-08 20:55 +05:30, Codex/GPT-5) Move promoted 5.4 icons from the top ribbon to bottom logos under the x-axis names, remove the ribbon rectangle/guide lines, rerun the full IDK0 wrapper, and verify the fresh SVG/PNG.
- [x] (2026-07-08 21:09 +05:30, Codex/GPT-5) Add Panels 6.1 and 6.2 to the IDK0 generator, support files, manifest, render path, and SVG audit; rerun the full IDK0 wrapper and visually inspect the fresh PNGs.
- [x] (2026-07-08 21:40 +05:30, Codex/GPT-5) Replace the harsh Score2000 reference-line presentation with faint grey 250-point guide lines across all IDK0 Score2000 vertical bar SVGs, update audit/support text, rerun the full wrapper, and visually inspect 5.4, 6.1, and 6.2.
- [x] (2026-07-09 00:38 +05:30, Codex/GPT-5) Replace public-facing bar-panel title, y-axis, footer, captions, manifest variant labels, promoted 5.4 title, and audit expectations with the approved confidence-weighted diagnosis wording; rerun the full IDK0 wrapper and inspect 5.4, 6.0, 6.1, and 6.2.
- [x] (2026-07-09 00:56 +05:30, Codex/GPT-5) Apply the A1 broken-axis pixel mapper to all IDK0 vertical bar panels without changing scores; update 5.4 promotion, audit geometry, manifests/provenance, support text, rerun the full wrapper, and visually inspect 5.4 and 6.2.
- [x] (2026-07-09 01:03 +05:30, Codex/GPT-5) Bring all closed/API models into promoted Panel 5.4 with their logo assets and default locked model-bar colors; rerun the full IDK0 wrapper, pass audit, and verify 5.4 XML/PNG.
- [x] (2026-07-09 01:28 +05:30, Codex/GPT-5) Apply the footer, score-label, model-name, tick-label, and y-axis-title spacing edits across IDK0 vertical bar panels; tighten the audit, rerun the full wrapper, and visually inspect 5.4 plus dense 6.2.
- [x] (2026-07-09 01:33 +05:30, Codex/GPT-5) Compress the A1 1000..2000 top segment from 30% to 18% of chart height; rerun the full wrapper, pass audit, structurally verify promoted 5.4, and visually inspect 5.4 plus dense 6.2.
- [x] (2026-07-09 01:40 +05:30, Codex/GPT-5) Pull the Score2000 vertical bar chart window upward by setting the 5.1/5.4/5.5/6.x chart top to y=540 and the shared chart height to 1610; rerun the full wrapper, pass audit, structurally verify 5.0/5.4/6.2, and visually inspect 5.0, 5.4, and 6.2.
- [x] (2026-07-09 01:47 +05:30, Codex/GPT-5) Add first-class Panel 5.6 as an open-model bottom-logo SVG/PNG using all open/open-access models including the three open medical models; update support text/audit, rerun the full wrapper, visually inspect, and structurally verify roster/logos/badges.
- [x] (2026-07-09 01:52 +05:30, Codex/GPT-5) Update the pooled human baseline icon to `human_expert_baseline_deep_crimson_logo.png` in both IDK0 SVG generation paths, rerun the full wrapper, and visually inspect the two open-model PNGs 5.6 and 6.2.
- [x] (2026-07-09 02:39 +05:30, Codex/GPT-5) Move the Human Expert Baseline score label above the bar in the open-model panels by changing the near-axis-break value-label rule; rerun the full wrapper, pass audit, structurally verify 5.6/6.2 label y positions, and visually inspect both PNGs.
- [x] (2026-07-09 02:50 +05:30, Codex/GPT-5) Add first-class Panel 6.3 as the plain bottom-logo closed/API + open-access through-MedGemma chart; update generator, audit, captions, provenance, checklist, rerun the full wrapper, structurally verify roster/logos/manifest, and visually inspect the PNG.
- [x] (2026-07-09 02:56 +05:30, Codex/GPT-5) Replace Panel 6.3's public title with the standard `Models through MedGemma vs 12 radiologists/trainees` wording; neutralize 6.3 support text, rerun the full wrapper, verify SVG title/roster/logos, and visually inspect the PNG.
- [x] (2026-07-09 03:11 +05:30, Codex/GPT-5) Replace Panel 6.3's public title with the all-in-one `Confidence-Weighted Diagnosis Scores: AI Models vs Human Expert Baseline` wording; rerun the full wrapper, verify SVG title/manifest/roster/logos, and visually inspect the PNG.
- [x] (2026-07-09 03:51 +05:30, Codex/GPT-5) Add first-class Panel 6.4 for all 15 evaluated AI models plus the Human Expert Baseline; update generator, audit, captions, provenance, checklist, rerun the full wrapper, verify 16 bars/logos, and visually inspect the PNG after adding a 6.4-only x-label font override.
- [x] (2026-07-09 03:56 +05:30, Codex/GPT-5) Restore Panel 6.4 to the standard bottom-logo icon scale `1.25`; rerun the full wrapper, verify the 16 logo bindings and metadata, and visually inspect the regenerated PNG.
- [x] (2026-07-09 04:24 +05:30, Codex/GPT-5) Replace Panels 6.1, 6.2, and 6.4 with the requested VLM titles; rerun the full IDK0 wrapper, pass audit, verify exact SVG/visible titles and no-footer structure, and visually inspect all three PNGs.
- [x] (2026-07-09 04:44 +05:30, Codex/GPT-5) Extend only the no-footer 6.1, 6.2, and 6.4 chart area from 1610 px to 1700 px; rerun the full IDK0 wrapper, add a chart-height metadata audit guard, pass the stricter audit, and visually inspect the regenerated PNGs.
- [x] (2026-07-09 05:02 +05:30, Codex/GPT-5) Add the dynamic 6.3 Human Expert Baseline vs best visible AI overlay, audit metadata/data attributes and draw order, rerun the full IDK0 wrapper, verify the exact 231-point current gap, and visually inspect the regenerated PNG.
- [x] (2026-07-09 10:33 +05:30, Codex/GPT-5) Remove the visible footer from Panel 6.3, extend its chart to the no-footer height, move bottom logos down for clearance, rerun the full IDK0 wrapper, verify no footer elements remain, and visually inspect the regenerated PNG.

## Surprises & Discoveries

- Observation: The staged/shared baseline predates IDK0 and therefore cannot faithfully regenerate the current IDK0 before-state by itself.
  Evidence: `git show :scripts/make_radle_v2_likert5_score1000_csvs.py` still describes all-IDK baseline `+200`, while current IDK0 output README says all-IDK baseline `0`.
  Date/Author: 2026-07-08, Codex/GPT-5
- Observation: The original `likert5_score1000_IDK0` output folder could not be safely overwritten because `score1000_group_summary.csv` was locked by another process.
  Evidence: PowerShell reported that the process could not access the file because it was being used by another process.
  Date/Author: 2026-07-08, Codex/GPT-5
- Observation: The longer corrected folder name exceeded Windows path limits during SVG generation.
  Evidence: SVG generation failed when a promoted Panel 5.4 path reached 263 characters.
  Date/Author: 2026-07-08, Codex/GPT-5
- Observation: After switching IDK scoring to 0, the status label `abstention_idk_reward` was semantically stale even though the numeric score was already 0.
  Evidence: Final rerun now emits `abstention_idk_zero` and `abstention_idk_typo_zero`, with the same row counts 688 and 5.
  Date/Author: 2026-07-08, Codex/GPT-5
- Observation: The old promoted 5.4 SVG could pass package existence checks while still being wrong.
  Evidence: It was a single embedded PNG wrapper, and the main manifest/audit report did not include 5.4; the first vector-promotion XML audit reported text=23, bars=6, ticks=5, ribbon logos=6.
  Date/Author: 2026-07-08, Codex/GPT-5
- Observation: The 5.4 logo bug was caused by stale hardcoded series order/scores in the promotion helper.
  Evidence: The then-current six-entry CSV rank was Human, Claude, Grok, Gemini, GPT, OctoMed; old helper order put Grok before Claude. The regenerated SVG logo order matches the bar order.
  Date/Author: 2026-07-08, Codex/GPT-5
- Observation: The CSV output folder is again locked at `score1000_group_summary.csv`.
  Evidence: Exclusive open fails with "because it is being used by another process"; full wrapper stops at the Score1000 IDK0 CSV generation step.
  Date/Author: 2026-07-08, Codex/GPT-5
- Observation: Promoted 5.4 inherited stale footer language from a row-oriented panel.
  Evidence: The rendered 5.4 footer said "Score2000 (left of each reader/model)" even though the vertical chart shows bar-value labels; regenerated footer now starts "Bar labels show Score2000...".
  Date/Author: 2026-07-08, Codex/GPT-5
- Observation: 5.4 was still omitted from support files after manifest/report coverage was fixed.
  Evidence: `captions.md`, `data_provenance.md`, `data_provenance.json`, `reviewer_checklist.md`, and `contact_sheet.html` lacked promoted 5.4 before the latest promotion-helper update.
  Date/Author: 2026-07-08, Codex/GPT-5
- Observation: The Score2000 labels/axis were shifted, but Panel 5.x bar geometry still used the old `Score2000=1000` reference as the bar origin.
  Evidence: Generator code used `bar_y = min(score_y, zero_y)` and `abs(score_y - zero_y)`. Regenerated 5.x SVGs now match `bar_y = score_y` and `bar_h = origin_0_y - score_y`; 5.4 human bar height is 761.3 px from origin 2150.0 to score y 1388.7.
  Date/Author: 2026-07-08, Codex/GPT-5
- Observation: Correct order alone is not enough to prevent future logo swaps.
  Evidence: The previous 5.4 helper could derive slots by index; it now parses `data-score1000-bar` elements and emits `data-reader-label`, `data-reader-key`, `data-bound-bar-label`, and `data-source-logo` on ribbon logos/guides. A simulated in-memory Claude/Grok slot swap produced matching swapped logo order and centers.
  Date/Author: 2026-07-08, Codex/GPT-5
- Observation: The user wanted the icons under names, not in a separate top ribbon.
  Evidence: The regenerated 5.4 SVG uses one `panel-5-4-bottom-logos` group, zero `score1000-logo-ribbon` rectangles, and zero `score1000-ribbon-guide` lines; after the closed/API update it has seven `score1000-bottom-logo` images.
  Date/Author: 2026-07-08, Codex/GPT-5
- Observation: The current CSV has three open/open-weight rows without locked logo assets in `scripts/assets/radle_score1000_logos`: `llama_4_maverick`, `internvl3_5_8b`, and `mistral_large_3_2512`.
  Evidence: The locked color/logo contact sheet JSON lists 12 model logo assets, while `score1000_panel23_bins.csv` has 15 AI rows. Panel 6.2 renders those three as explicit SVG text badges and records `logo_kind=svg_text_badge`.
  Date/Author: 2026-07-08, Codex/GPT-5
- Observation: The old `Score2000=1000` shifted-zero guide was visually too strong for the current 0..2000 bar presentation.
  Evidence: The regenerated vertical bar SVGs now expose tick metadata at 0, 250, 500, 750, 1000, 1250, 1500, 1750, and 2000, and every tick line including the shifted 1000 reference has class `score2000-grid`.
  Date/Author: 2026-07-08, Codex/GPT-5
- Observation: Public readers do not need to see `Score2000` as the title or y-axis label, but provenance still needs the shifted-scale formula.
  Evidence: The regenerated bar SVG text now uses `Confidence-weighted diagnosis correctness` / `Confidence-weighted diagnosis score` or the approved 6.x comparison titles; XML extraction found no visible `Score2000`, `Diagnostic performance`, or `IDK` in title/axis/footer text, while provenance retains `Score2000 = Score1000 + 1000`.
  Date/Author: 2026-07-09, Codex/GPT-5
- Observation: The A1 kink is a rendering transform, not a score transform.
  Evidence: Regenerated value labels remain unchanged by the kink; after the closed/API update promoted 5.4 shows `988.7`, `758`, `666`, `660`, `651`, `472`, and `409`; XML checks show every vertical bar SVG now has ticks `[0, 500, 1000, 2000]` and two `data-score2000-axis-break-mark` slash marks.
  Date/Author: 2026-07-09, Codex/GPT-5
- Observation: Promoted 5.4 was still sourcing the old six-entry Panel 5 set, while the closed/API comparison needed the same roster as Panel 6.1.
  Evidence: The 5.4 helper now calls `panel_5_score1000_bar_chart(...)` with `SCORE1000_BAR_CLOSED_READER_LABELS` and `SCORE1000_BAR_COLORS_PALETTE_A`, and the regenerated SVG has seven bars/logos: Human, Claude, Grok, Gemini, GPT-5.5, Qwen, and GLM.
  Date/Author: 2026-07-09, Codex/GPT-5

## Decision Log

- Decision: Preserve before-state by snapshotting/rendering existing current IDK0 SVG artifacts instead of reconstructing a lost intermediate generator.
  Rationale: Existing artifacts are the faithful current before-state; the staged/shared generator is older than IDK0.
  Date/Author: 2026-07-08, Codex/GPT-5
- Decision: IDK0 work must use explicit IDK0 script copies/wrappers, not shared script paths.
  Rationale: User stated IDK0 changes stay isolated unless explicitly promoted.
  Date/Author: 2026-07-08, user and Codex/GPT-5
- Decision: Use the short corrected output child folder `s2k_IDK0`.
  Rationale: It avoids the locked stale folder and prevents Windows path-length failures in generated SVG/PNG names.
  Date/Author: 2026-07-08, Codex/GPT-5
- Decision: Once the lock was released, restore `likert5_score1000_IDK0` as the official corrected folder and remove the temporary scratch folders.
  Rationale: The user wanted the IDK0 folder corrected, and keeping duplicate generated lanes with older status labels would invite drift.
  Date/Author: 2026-07-08, user and Codex/GPT-5
- Decision: Promote Panel 5.4 by generating a vector overlay from the base SVG, then appending 5.4 to the main manifest and audit report.
  Rationale: A PNG-wrapper SVG prevents structural QA from catching logo/bar mismatches; vector overlay keeps the generated panel inspectable.
  Date/Author: 2026-07-08, Codex/GPT-5
- Decision: Keep promoted 5.4 support-file updates in the p5 promotion helper rather than the base variant generator.
  Rationale: The base generator intentionally cleans unknown promoted outputs before p5 runs; the promotion helper is the source of truth for post-promotion artifacts.
  Date/Author: 2026-07-08, Codex/GPT-5
- Decision: Treat `Score2000=0` as the Panel 5.x bar origin and `Score2000=1000` as a reference line only.
  Rationale: Score2000 is a shifted 0..2000 display scale; using 1000 as the bar origin visually reintroduced negative bars.
  Date/Author: 2026-07-08, Codex/GPT-5
- Decision: Bind 5.4 ribbon logos by stable `reader_label` and parsed source SVG bar slots, not by positional zip/index.
  Rationale: A future RadLE rank/order change should move the matching logo with its bar, and a missing logo mapping should fail loudly instead of reusing another model's icon.
  Date/Author: 2026-07-08, Codex/GPT-5
- Decision: Keep the 5.4 identity binding but render logos below x-axis names, with no decorative ribbon or guide lines.
  Rationale: This satisfies the requested visual layout while preserving the binding guard that prevents future logo/model swaps.
  Date/Author: 2026-07-08, Codex/GPT-5
- Decision: Panel 6.1 and 6.2 should use the full current comparator CSV membership, not only the subset represented by locked logo assets.
  Rationale: The user requested all closed models and all open models, including medical open models. Omitting the three open rows without locked logo assets would make Panel 6.2 incomplete.
  Date/Author: 2026-07-08, Codex/GPT-5
- Decision: Use bottom-under-label logos/badges for Panels 6.1 and 6.2.
  Rationale: Several open-model bars are short; bottom placement avoids inside-bar icon collisions and follows the latest requested icon placement direction.
  Date/Author: 2026-07-08, Codex/GPT-5
- Decision: Use faint grey guide lines every 250 points for IDK0 Score2000 vertical bar panels.
  Rationale: 250-point spacing gives useful visual reference on the 0..2000 scale without making the plot read as dense graph paper; styling the shifted 1000 reference the same way removes the harsh midline while preserving metadata for audit.
  Date/Author: 2026-07-08, Codex/GPT-5
- Decision: Keep `Score2000` as technical provenance only, and use public-facing confidence-weighted diagnosis wording in bar-panel titles, y-axis labels, captions, and footer text.
  Rationale: The user rejected raw `Score2000` as public figure wording; the final text must be understandable as a standalone shared image while still explaining the shifted display scale in the footer/provenance.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Implement the A1 kink by changing only `score1000_bar_scaled_y(...)` usage/specs, not scores.
  Rationale: The intended effect is visual compression of the empty 1000..2000 region: 0..1000 maps into the lower axis segment, 1000..2000 maps into the compressed upper segment, and both ticks and bars use the same mapper.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Make promoted 5.4 a closed/API-model panel by deriving its source chart from `SCORE1000_BAR_CLOSED_READER_LABELS` and the default locked model-bar palette.
  Rationale: This keeps 5.4 consistent with the closed-model view while preserving the existing `reader_label` logo binding so future sequence changes do not swap logos.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Reduce the A1 top compressed segment from 30% to 18% while keeping the 2000 endpoint fixed.
  Rationale: The user wanted less unused visual range after 1000, with the 0/500/1000 ticks spread out and bars pulled upward/lengthened without changing scores.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Reduce vertical header-to-plot whitespace by moving the Score2000 bar chart top upward while preserving the lower label/logo/footer stack.
  Rationale: Visual inspection showed the remaining inefficient gap was above the plot, not below it. Moving 5.1/5.4/5.5/6.x chart_y from 610 to 540 and chart height from 1540 to 1610 keeps their bottom axis fixed at 2150 while giving the bars more vertical presence.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Add the all-open-model bottom-logo chart as first-class Panel 5.6 rather than a copied SVG.
  Rationale: Keeping it generated, audited, manifested, and rendered with the wrapper avoids stale one-off copies and preserves the model-to-logo binding checks.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Use `human_expert_baseline_deep_crimson_logo.png` as the pooled Human Expert Baseline icon in the IDK0 bottom-logo/bar-panel generators.
  Rationale: The crimson icon matches the current Human Expert Baseline bar color and keeps the shared-reader icon visually distinct from the older navy board-certified radiologist marker.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Keep score labels above the bar unless the label would run above the chart top; do not move the Human Expert Baseline label inside the bar merely because it is close to the A1 break.
  Rationale: The user wants the human score to follow the same visible convention as model scores. The chart-top guard still prevents out-of-frame labels for future very high values.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Add Panel 6.3 as a plain bottom-logo through-MedGemma chart instead of reusing Panel 6.0.
  Rationale: Panel 6.0 already has the combined through-MedGemma roster but includes barcode overlays; 6.3 provides the same roster in the cleaner visual grammar of 6.1 and 6.2.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Use the standard neutral public title `Models through MedGemma vs 12 radiologists/trainees` for Panel 6.3.
  Rationale: The category split is useful internally for selecting the roster, but the public-facing title should stand alone without `closed/API` or `open-access` wording.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Replace the interim 6.3 title with a single all-in-one title: `Confidence-Weighted Diagnosis Scores: AI Models vs Human Expert Baseline`.
  Rationale: The title should state both the metric family and the comparison target in one public-facing line, without meta commentary about roster construction.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Add the all-15-model chart as Panel 6.4 instead of changing Panel 6.3 in place.
  Rationale: Panel 6.3 already documents the through-MedGemma slice; a sibling 6.4 keeps that artifact stable while making the full comparator set explicit.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Use a 6.4-only x-label override of 30 px font size and 38 px line spacing.
  Rationale: Sixteen x-axis labels at the shared 40 px size visually crowded together; the override fixes the full-model panel without shrinking labels in existing panels.
  Date/Author: 2026-07-09, Codex/GPT-5
- Decision: Use a 6.4-only bottom-logo scale of `1.40`.
  Rationale: A `1.40` trial makes the 16-panel logos optically closer to bar width while retaining clear horizontal separation; Panel 5.6 remains at the standard `1.25` scale.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Suppress the visible footer on Panels 6.1, 6.2, and 6.4 and use the lower row for larger model identities.
  Rationale: The requested standalone panels should not carry the explanatory footer; the freed vertical space is used by moving bottom logos to y=`2490.0`, increasing 6.1/6.2 logo scale to `1.55`, and increasing 6.1/6.2 model-name text to `46.0` px.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Use explicit public VLM category titles for Panels 6.1, 6.2, and 6.4.
  Rationale: These no-footer panels are intended to stand alone; the title should tell readers whether the figure shows proprietary frontier VLMs, open-weights VLMs, or the full frontier VLM set against the Human Expert Baseline.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Use a panel-local `score_chart_h=1700.0` for Panels 6.1, 6.2, and 6.4 only.
  Rationale: Removing the visible footer freed lower-page space; extending the chart bottom from `2150.0` to `2240.0` gives the bars more vertical presence while keeping model names and logos visible. Panel 5.6 remains unchanged because the request targeted only 6.1, 6.2, and 6.4.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Make the 6.3 Human-vs-top-AI gap overlay opt-in and data-driven from the visible selected 6.3 rows.
  Rationale: The overlay must follow future RadLE rank changes without hard-coding Claude Fable 5, while preserving the existing Score2000 values, roster, footer, and broken-axis mapper.
  Date/Author: 2026-07-09, user and Codex/GPT-5
- Decision: Remove the visible Panel 6.3 footer and reuse the no-footer chart-height geometry.
  Rationale: The user explicitly rejected the footer and wanted more room for the graph; setting `show_footer=False` and `score_chart_h=1700.0` gives the bars/plot area more vertical space without changing scores, ordering, roster, or the gap overlay calculation.
  Date/Author: 2026-07-09, user and Codex/GPT-5

## Revision Notes

- v1 (2026-07-08, Codex/GPT-5): Created the IDK0 isolation and SVG regeneration plan after user approved the boundary.
- v2 (2026-07-08, Codex/GPT-5): Recorded the 5.4 vector-promotion fix, audit coverage, and current CSV file-lock blocker.
- v3 (2026-07-08, Codex/GPT-5): Recorded 5.4 footer and support-file coverage fixes.
- v4 (2026-07-08, Codex/GPT-5): Recorded completed full wrapper rerun and Panel 5.x positive Score2000 bar-origin fix.
- v5 (2026-07-08, Codex/GPT-5): Recorded identity-bound 5.4 logo placement and sequence-change simulation evidence.
- v6 (2026-07-08, Codex/GPT-5): Recorded bottom-logo 5.4 layout, removed ribbon/guide elements, and fresh wrapper/audit evidence.
- v7 (2026-07-08, Codex/GPT-5): Recorded 6.1 closed-model and 6.2 open-model panel generation, fallback badge handling, visual inspection, and audit evidence.
- v8 (2026-07-08, Codex/GPT-5): Recorded 250-point faint grey Score2000 guide lines, softened shifted-zero styling, wrapper rerun, XML tick checks, and visual inspection evidence.
- v9 (2026-07-09, Codex/GPT-5): Recorded approved public-facing confidence-weighted diagnosis wording, `"I don't know"` footer spelling, full wrapper rerun, XML text checks, and visual inspection evidence.
- v10 (2026-07-09, Codex/GPT-5): Recorded A1 broken-axis implementation across all IDK0 vertical bar panels, promoted 5.4 support, audit updates, full wrapper pass, XML checks, and visual inspection evidence.
- v11 (2026-07-09, Codex/GPT-5): Recorded promoted 5.4 closed/API roster update, Qwen/GLM logo catalog entries, default locked model-bar colors, full wrapper pass, XML checks, and visual inspection evidence.
- v12 (2026-07-09, Codex/GPT-5): Recorded footer merge, larger score and model labels, y-axis tick/title spacing changes, tightened audit checks, full wrapper pass, XML checks, and visual inspection evidence.
- v13 (2026-07-09, Codex/GPT-5): Recorded the tighter A1 top-region compression from 30% to 18%, wrapper rerun, XML tick-gap evidence, hashes, and visual inspection.
- v14 (2026-07-09, Codex/GPT-5): Recorded upward chart-window adjustment, full wrapper rerun, XML geometry evidence, refreshed hashes, and visual inspection of 5.0, 5.4, and 6.2.
- v15 (2026-07-09, Codex/GPT-5): Recorded Panel 5.6 open-model bottom-logo variant, support text/audit updates, wrapper pass, XML roster evidence, hashes, and visual inspection.
- v16 (2026-07-09, Codex/GPT-5): Recorded the deep-crimson Human Expert Baseline icon update, full wrapper pass, XML source-logo checks, refreshed hashes, and visual inspection of 5.6 and 6.2.
- v17 (2026-07-09, Codex/GPT-5): Recorded the above-bar Human Expert Baseline score-label fix, updated audit geometry, full wrapper pass, refreshed hashes, and visual inspection of 5.6 and 6.2.
- v18 (2026-07-09, Codex/GPT-5): Recorded Panel 6.3 closed/API + open-access through-MedGemma variant, support text/audit updates, wrapper pass, XML roster evidence, hashes, and visual inspection.
- v19 (2026-07-09, Codex/GPT-5): Recorded Panel 6.3 public-title cleanup to the standard through-MedGemma title, neutral support text, wrapper pass, XML title/roster evidence, hashes, and visual inspection.
- v20 (2026-07-09, Codex/GPT-5): Recorded Panel 6.3 all-in-one public title, wrapper pass, XML title/manifest/roster evidence, hashes, and visual inspection.
- v21 (2026-07-09, Codex/GPT-5): Recorded Panel 6.4 all-15-model chart, 6.4-only x-label override, wrapper pass, XML title/roster/logo evidence, hashes, support-file checks, and visual inspection.
- v22 (2026-07-09, Codex/GPT-5): Recorded Panel 6.4 standard icon-scale restoration, wrapper pass, XML logo-scale evidence, refreshed hashes, and visual inspection.
- v23 (2026-07-09, Codex/GPT-5): Recorded Panel 6.4 icon-scale trial at `1.40`, corrected the first pass that had targeted Panel 5.6, restored 5.6 to `1.25`, reran the full wrapper, and captured XML clearance, hashes, and visual inspection.
- v24 (2026-07-09, Codex/GPT-5): Recorded footer suppression for Panels 6.1, 6.2, and 6.4, enlarged 6.1/6.2 bottom logos and model-name text, moved the bottom-logo row lower, reran the full wrapper, and captured XML footer/logo/font checks, hashes, and visual inspection.
- v25 (2026-07-09, Codex/GPT-5): Recorded requested VLM titles for 6.1, 6.2, and 6.4, split the open-model title constant so 5.6 stays unchanged, full wrapper rerun, audit pass, no-footer XML checks, rendered hashes, and visual inspection.
- v26 (2026-07-09, Codex/GPT-5): Recorded no-footer chart-height increase for 6.1, 6.2, and 6.4, stricter chart-height metadata audit guard, full wrapper pass, XML geometry checks, hashes, and visual inspection.
- v27 (2026-07-09, Codex/GPT-5): Recorded the dynamic 6.3 Human-AI gap overlay, full wrapper pass, metadata/data-attribute checks, draw-order check, and visual inspection.
- v28 (2026-07-09, Codex/GPT-5): Recorded Panel 6.3 footer removal, no-footer chart height, bottom-logo clearance, full wrapper pass, XML checks, and visual inspection.

## Outcomes & Retrospective

Completed for this turn. Before-state snapshot: `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/before_state_score1000_net_score_IDK0_20260708_183000`. Corrected output lane: `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0`.

Validation completed:

- `py -3.11 -m py_compile scripts/audit_radle_v2_score1000_panel23_IDK0.py`
- `py -3.11 -m py_compile scripts/make_radle_v2_score1000_panel23_svg_IDK0.py scripts/make_radle_v2_score1000_panel5_logo_placement_contact_sheet_IDK0.py scripts/audit_radle_v2_score1000_panel23_IDK0.py`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_radle_v2_score1000_idk0_pipeline.ps1`
- Latest 6.3 gap-overlay compile: `py -3.11 -m py_compile scripts/make_radle_v2_score1000_panel23_svg_IDK0.py scripts/audit_radle_v2_score1000_panel23_IDK0.py`.
- Latest 6.3 gap-overlay wrapper run completed successfully end-to-end: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_radle_v2_score1000_idk0_pipeline.ps1`.
- Latest 6.3 gap-overlay XML check: `include_score_gap_overlay=True`; Human Expert Baseline score `988.666667`; top AI `claude_fable_5` / `Claude Fable 5`; top AI score `758.0`; gap `230.666667`; rounded label `231 point Human-AI gap: July 10, 2026`; data attributes include `data-human-score=988.666667`, `data-top-ai-label=claude_fable_5`, `data-top-ai-score=758`, `data-gap-value=230.666667`, and `data-gap-rounded=231`; draw order is y-axis title index `22`, overlay index `23`, first bar index `24`.
- Latest 6.3 gap-overlay visual inspection opened `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0/handwritten_panels_model_group_color_final_IDK0/panel_2_score1000_6_3_closed_open_through_medgemma_score1000_bar_chart.png`; dashed human/top-AI guide lines, blue double-arrow, and label render clearly without obvious overlap.
- Latest 6.3 footer-removal compile: `py -3.11 -m py_compile scripts/make_radle_v2_score1000_panel23_svg_IDK0.py scripts/audit_radle_v2_score1000_panel23_IDK0.py`.
- Latest 6.3 footer-removal wrapper run completed successfully end-to-end: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_radle_v2_score1000_idk0_pipeline.ps1`.
- Latest 6.3 footer-removal XML check: `show_footer=False`; `use_variant_footer=False`; `chart_y=540.0`; `chart_h=1700.0`; `chart_bottom=2240.0`; `bottom_logo_center_y=2490.0`; footer text count `0`; footer divider count `0`; max x-label y `2366.0`; min logo y `2439.2`; label/logo clearance `73.2` px; gap overlay label remains `231 point Human-AI gap: July 10, 2026`.
- Latest 6.3 footer-removal visual inspection opened `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0/handwritten_panels_model_group_color_final_IDK0/panel_2_score1000_6_3_closed_open_through_medgemma_score1000_bar_chart.png`; the footer is gone, the plot area is taller, and model labels/logos remain readable.
- `powershell -ExecutionPolicy Bypass -File scripts/build_radle_v2_score1000_idk0_pipeline.ps1 -OutDir outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0`
- `py -3.11 -m py_compile scripts/make_radle_v2_likert5_score1000_csvs_IDK0.py scripts/audit_radle_v2_likert5_score1000_csvs_IDK0.py scripts/radle_v2_score1000_panel_stats_IDK0.py scripts/audit_radle_v2_score1000_panel23_IDK0.py`
- CSV sanity: 16 rows, `score2000` present, one `Human Expert Baseline`; top five are `Human Expert Baseline` 988.666667, `claude_fable_5` 758.0, `grok_4_3` 666.0, `gemini_3_1_pro` 660.0, `gpt_5_5` 651.0.
- Stale-text checks found no old split-human labels, no negative Score1000 tick metadata, no `earns +1`, no all-IDK `+200` baseline, and no stale `abstention_idk_reward` / `abstention_idk_typo_reward` statuses in the corrected lane.
- Latest 5.4 XML check: one `panel-5-4-bottom-logos` group, seven `score1000-bottom-logo` images, zero ribbon rectangles, and zero guide lines; bar order and logo order both match Human, Claude, Grok, Gemini, GPT-5.5, Qwen, GLM.
- Latest 5.4 identity-binding check: every bottom logo has matching `data-reader-label`, `data-reader-key`, `data-bound-bar-label`, and source logo; logo centers equal the same-labeled bar center.
- Sequence-change simulation: swapping Claude and Grok source bar slots in memory produced swapped logo order, with each logo centered on the matching swapped bar. This binding remains valid after the closed/API 5.4 update because logos are attached by stable `reader_label`, not by positional assumptions.
- Positive bar geometry check passed for Panel 5.0, 5.1, 5.5, and promoted 5.4 with max y/height delta 0.040 px. For the latest 5.4: origin y=2150.0, reference1000 y=829.8, human bar y=844.8 and height=1305.2.
- Latest 5.4 rendered PNG: `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0/handwritten_panels_model_group_color_final_IDK0/panel_2_score1000_5_4_icon_ribbon_score1000_bar_chart.png`.
- Latest 5.4 rendered hashes: SVG `BBE16A8388D312E7CB25943D93154B8CF8FA625A6BA5534804FBA90B7B581036`; PNG `98BB7355CE666617542ACA85EA4A55554218C0AE8EB42C5B507317979528FFD8`.
- Latest support-file check: `captions.md`, `data_provenance.md`, and `reviewer_checklist.md` each include exactly one promoted 5.4 support block; `data_provenance.json` includes `promoted_variant_5_4`; `figure_manifest.json` tracks refreshed hashes for support files.
- Full wrapper rerun completed successfully against the official IDK0 folder after the file lock was released.
- Latest full wrapper rerun completed successfully after adding Panels 6.1 and 6.2. The audit report result is `pass`, with panels `2.1`, `3.1`, `2.2`, `3.2`, `2.3`, `3.3`, `2.4`, `3.4`, `2.5`, `3.5`, `5.0`, `5.1`, `5.5`, `6.1`, `6.2`, and promoted `5.4`.
- Latest 6.1 XML check: bars and asset logos are `Human Expert Baseline`, `claude_fable_5`, `grok_4_3`, `gemini_3_1_pro`, `gpt_5_5`, `qwen_3_7_plus`, and `glm_5v_turbo`; no fallback badges.
- Latest 6.2 XML check: bars are `Human Expert Baseline`, `octomed_7b`, `nemotron_3_omni`, `minimax_m3`, `gemma_4_31b`, `lingshu_32b`, `medgemma_1_5_4b`, `llama_4_maverick`, `internvl3_5_8b`, and `mistral_large_3_2512`; asset logos cover the first seven and fallback badges cover Llama, InternVL, and Mistral.
- Latest 6.1 rendered hashes: SVG `D3E7304DDC20AD88E59766A518625DEBE15764C34466CC87CC6B0166A854A052`; PNG `9F7FFCE57F856E3F6EFE43EF8A0CD8C68410D128BEFCB3C53707E85102B99111`.
- Latest 6.2 rendered hashes: SVG `BE3BF0E576749D200337756E0DE16E8B65BF3C4E8B40ACEC6208DEE38D6B5F8E`; PNG `E871C303FC21B831C62281EC069B043F0EF163AE59FE5F8B1A4624D5548DF1BD`.
- Latest grid/tick update: `SCORE1000_BAR_TICKS` is `[0, 250, 500, 750, 1000, 1250, 1500, 1750, 2000]`; SVG CSS class `.score2000-grid` renders the guides as faint grey; audit rejects any Score2000 tick line or shifted 1000 reference line that is not `score2000-grid`.
- Latest structural tick check passed for 5.5, 6.2, and promoted 5.4: each SVG had ticks `0, 250, 500, 750, 1000, 1250, 1500, 1750, 2000`, only class `score2000-grid`, and one shifted-zero line with class `score2000-grid`.
- Latest full wrapper rerun completed successfully after the grid update, including CSV regeneration, panel stats, SVG generation, 5.4 promotion, audit, and PNG rendering.
- Latest visual inspection opened the regenerated PNGs for promoted 5.4, 6.1, and 6.2; the 250-point grey guide lines are visible but subdued, and the old harsh 1000 midline is gone.
- Latest full wrapper rerun completed successfully after the public-text update, including CSV regeneration, panel stats, SVG generation, 5.4 promotion, audit, and PNG rendering.
- Latest SVG audit report: `score1000_panel2_group_color_audit_report.json` result is `pass`, rows `16`, panels include `5.4`, `5.6`, `6.0`, `6.1`, `6.2`, `6.3`, and `6.4`, generated at `2026-07-08T22:46:55+00:00`.
- Latest XML text extraction for 5.0, 5.1, 5.4, 5.5, 6.0, 6.1, and 6.2 found the approved titles, y-axis `Confidence-weighted diagnosis score`, four-line footer with `"I don't know"` spelled out, and no visible title/axis/footer stale strings `Score2000`, `Diagnostic performance`, or `IDK`.
- Latest shifted-value check found no visible negative numeric labels in the seven bar SVGs. Promoted 5.4 value labels are `988.7`, `758`, `666`, `660`, `651`, `472`, and `409`.
- Latest visual inspection opened the regenerated PNGs for promoted 5.4, 6.0, 6.1, and 6.2. Titles, y-axis labels, bottom logos/badges, values, footer text, and 250-point grey guide lines render without obvious overlap.
- Latest generated-doc check found no stale public phrases `all-IDK`, `gray IDK`, `exact or typo IDK`, `non-IDK`, `Score2000 by reader/model`, `Score2000 for`, `open/open-weight`, `Score2000 footer`, `Diagnostic performance`, or `Diagnostic score` in README, manual, captions, provenance, or checklist.
- Latest A1-kink wrapper run completed successfully end-to-end: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_radle_v2_score1000_idk0_pipeline.ps1`.
- Latest A1-kink XML check found ticks `[0, 500, 1000, 2000]`, two slash marks, and unchanged visible score labels for 5.0, 5.1, 5.4, 5.5, 6.0, 6.1, and 6.2.
- Latest A1-kink visual inspection opened promoted 5.4 and 6.2. Both show the compressed 1000..2000 region with the gap/slashes above 1000, and labels/logos remain aligned.
- Latest compressed-top-axis XML check for promoted 5.4: `axis_break_top_fraction` is `0.18`; ticks are `(0, 2150.0)`, `(500, 1518.6)`, `(1000, 887.2)`, and `(2000, 610.0)`; the 0..500 and 500..1000 gaps are both 631.4 px, the 1000..2000 compressed gap is 277.2 px, and there are two axis-break slash marks.
- Latest compressed-top-axis visual inspection opened promoted 5.4 and dense open-model Panel 6.2. Both render taller sub-1000 bars without obvious overlap in score labels, model names, y-axis labels, bottom logos/badges, or footer text.
- Latest upward chart-window XML check: promoted 5.4 and Panel 6.2 now have `chart_y=540.0`, ticks `(0, 2150.0)`, `(500, 1489.9)`, `(1000, 829.8)`, and `(2000, 540.0)`, 0..500 and 500..1000 gaps of 660.1 px, and 1000..2000 compressed gap of 289.8 px. Panel 5.0 uses `chart_y=520.0`, bottom y=2130.0, and the same 660.1 px lower tick gaps.
- Latest upward chart-window visual inspection opened regenerated 5.0, promoted 5.4, and dense open-model Panel 6.2. The header-to-plot gap is reduced, bars are taller, and score labels, model names, bottom logos/badges, y-axis labels, and footer text render without obvious overlap.
- Latest closed/API 5.4 wrapper run completed successfully end-to-end: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_radle_v2_score1000_idk0_pipeline.ps1`.
- Latest closed/API 5.4 XML check: bar count `7`; bar/logo order `Human Expert Baseline`, `claude_fable_5`, `grok_4_3`, `gemini_3_1_pro`, `gpt_5_5`, `qwen_3_7_plus`, `glm_5v_turbo`; fills `#a61e2e`, `#d97757`, `#3f464c`, `#4285f4`, `#10a37f`, `#7b61e7`, `#155ad6`; `colors_match=True`; ticks `[0, 500, 1000, 2000]`; axis-break marks `2`.
- Latest closed/API 5.4 rendered PNG inspected: `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0/handwritten_panels_model_group_color_final_IDK0/panel_2_score1000_5_4_icon_ribbon_score1000_bar_chart.png`.
- Latest layout XML check for promoted 5.4: footer count `3`; merged footer line is `"I don't know"/blank/failed responses score 0 before display shifting. Displayed score = raw + 1000; 1000 is the all-"I don't know" baseline.`; score label styles include `font-size:44.0px`; tick labels are at x=`310.0`; x-label tspan dy values are `0.0` and `48.0`; y-axis title transform is `translate(185.0 1380.0) rotate(-90)`.
- Latest layout visual inspection opened promoted 5.4 and dense open-model Panel 6.2 after the shared font/axis changes. Footer, score labels, model names, y-axis tick labels, logos/badges, and bars render without obvious overlap.
- Latest Panel 5.6 XML check: bar order is `Human Expert Baseline`, `octomed_7b`, `nemotron_3_omni`, `minimax_m3`, `gemma_4_31b`, `lingshu_32b`, `medgemma_1_5_4b`, `llama_4_maverick`, `internvl3_5_8b`, and `mistral_large_3_2512`; open medical rows OctoMed, Lingshu, and MedGemma are present; asset logos cover Human, OctoMed, Nemotron, MiniMax, Gemma, Lingshu, and MedGemma; fallback badges cover Llama, InternVL, and Mistral; `chart_y=540.0`; ticks are `(0, 2150.0)`, `(500, 1489.9)`, `(1000, 829.8)`, and `(2000, 540.0)`; `manifest_has_5_6=True`.
- Latest Panel 5.6 rendered hashes: SVG `032698F1892857B5F4308088B0C6E2FCA744F148B6215C05F3B6D10EB335BCFA`; PNG `E871C303FC21B831C62281EC069B043F0EF163AE59FE5F8B1A4624D5548DF1BD`.
- Latest Panel 5.6 visual inspection opened the regenerated PNG in `handwritten_panels_model_group_color_final_IDK0`; title, y-axis labels, bottom logos/badges, values, footer text, and kinked axis render without obvious overlap.
- Latest human-icon XML check: Panel 5.6 and Panel 6.2 each have the Human Expert Baseline bottom-logo source `scripts\assets\radle_score1000_logos\human_expert_baseline_deep_crimson_logo.png`; promoted Panel 5.4 has source `human_expert_baseline_deep_crimson_logo.png`.
- Latest human-icon rendered hashes: Panel 5.6 SVG `8A8DEB9E70C1EEFCE27DC83EB7EE470DBD4D9B370576ACD155BAC733726AB5FE`, Panel 5.6 PNG `FE18A9452BCDDB68E2AE0E8BD9EA43978A1398C7F0E3FD1F78F30915DD41460E`; Panel 6.2 SVG `07E418A70B14397133E26AB97657FA5155E6DFB0C67C9D085E4487072FBE06B2`, Panel 6.2 PNG `FE18A9452BCDDB68E2AE0E8BD9EA43978A1398C7F0E3FD1F78F30915DD41460E`; promoted 5.4 SVG `4470096423E8A2A8624DBDE4117E227093AF1BD3B9B8F83A1818E9C89F346DB9`, promoted 5.4 PNG `D0104D6858CDE021AE804CDADFDC513B941E082AF1B3AE2C4BFF07A7A8048209`.
- Latest human-icon visual inspection opened regenerated Panel 5.6 and Panel 6.2 PNGs. Both show the red Human Expert Baseline icon under the x-axis label with no obvious overlap or logo/name drift.
- Latest human score-label XML check: Panel 5.6 and Panel 6.2 each have Human Expert Baseline bar top `y=844.8`, visible score label `988.7` at `y=802.8`, and label style `fill:#a61e2e;font-size:59.4px`; `value_above_bar=True` for both.
- Latest human score-label rendered hashes: Panel 5.6 SVG `EC856EB4C186D3252ABE7A58BCA4A24A3F487D3B3C22BE5B4D8F6815A8D55717`, Panel 5.6 PNG `7B084A62ACE4A4E5B885CE0C953E7C8E0E1C33FA19285E1D21053BDB9341A77F`; Panel 6.2 SVG `85ACF41748DA84B9885FD2C46FE139B1485F9406E9DD17CB1275230B1F99960A`, Panel 6.2 PNG `7B084A62ACE4A4E5B885CE0C953E7C8E0E1C33FA19285E1D21053BDB9341A77F`.
- Latest human score-label visual inspection opened regenerated Panel 5.6 and Panel 6.2 PNGs. Both show `988.7` above the Human Expert Baseline bar, not inside it.
- Latest Panel 6.3 XML check: title and manifest title are `Confidence-Weighted Diagnosis Scores: AI Models vs Human Expert Baseline`; bar order and logo order are `Human Expert Baseline`, `claude_fable_5`, `grok_4_3`, `gemini_3_1_pro`, `gpt_5_5`, `octomed_7b`, `nemotron_3_omni`, `qwen_3_7_plus`, `glm_5v_turbo`, `minimax_m3`, `gemma_4_31b`, `lingshu_32b`, and `medgemma_1_5_4b`.
- Latest Panel 6.3 rendered hashes: SVG `32E60A77584F2194045FC1BBA349270E85AC5113FB912D32088FCAF0DB534501`; PNG `3D0F3A399DB3507486E8BE5053293CE197BB33A2BF2BECABB484E03C3CD5906E`.
- Latest Panel 6.3 support-file check: `captions.md`, `data_provenance.md`, and `reviewer_checklist.md` include 6.3, the through-MedGemma roster, the exclusion of Llama, InternVL, and Mistral, and no public 6.3 title using `closed/API`, `open-access`, or `through MedGemma`.
- Latest Panel 6.3 visual inspection opened the regenerated PNG in `handwritten_panels_model_group_color_final_IDK0`; the 13-bar layout, all-in-one title, y-axis label, score labels, bottom logos, and footer render without obvious overlap.
- Latest Panel 6.1 XML check: footer count `0`, footer-divider count `0`, model-name style `font-size:46.0px;`, logo center y `2490.0`, logo widths `148.8` and `192.2` px, minimum horizontal logo gap `269.5` px, and max logo bottom `2586.1`.
- Latest Panel 6.1 rendered hashes: SVG `C3B5318EFBC82495E047355C0C019753CE9DAE95C0B366B2C3872A2DF9CD1940`; PNG `BB6A9AEFF99A61732592318BB5B3BF8DB66B71D49AE8C1ED6184FA445CCE48BF`.
- Latest Panel 6.2 XML check: footer count `0`, footer-divider count `0`, model-name style `font-size:46.0px;`, logo center y `2490.0`, logo widths `148.8`, `178.6`, and `192.2` px, minimum horizontal logo gap `122.6` px, and max logo bottom `2586.1`.
- Latest Panel 6.2 rendered hashes: SVG `51AEC57F1F5DEE37349FED64140A0141E64D5DDBAB8C2E0ADE4FDEE0A17A2839`; PNG `4C8AB2231A150C17BFAA277FA4F28251757287C7B868E9AD806DE99D02249AC7`.
- Latest Panel 6.4 XML check: title and manifest title are `Confidence-Weighted Diagnosis Scores: All AI Models vs Human Expert Baseline`; bar order and logo order are `Human Expert Baseline`, `claude_fable_5`, `grok_4_3`, `gemini_3_1_pro`, `gpt_5_5`, `octomed_7b`, `nemotron_3_omni`, `qwen_3_7_plus`, `glm_5v_turbo`, `minimax_m3`, `gemma_4_31b`, `lingshu_32b`, `medgemma_1_5_4b`, `llama_4_maverick`, `internvl3_5_8b`, and `mistral_large_3_2512`; footer count `0`; footer-divider count `0`; x-axis label style is `font-size:30.0px;` with tspan dy values `0.0` and `38.0`; `bar_logo_scale` is `1.40`; rendered logo widths are `134.4`, `161.3`, and `173.6` px; minimum horizontal logo gap is `38.5` px.
- Latest Panel 6.4 rendered hashes: SVG `11B9425F672A677630F379ED12C3F46A55714AD573FFC845786C0971A522CC0B`; PNG `484266B1AA13ED6C180075A1B980539E906B20FE07ED7C729E522C6038A9ADC4`.
- Latest Panel 6.4 support-file check: `captions.md`, `data_provenance.md`, `reviewer_checklist.md`, and `figure_manifest.json` include 6.4 as the all-15-model panel.
- Latest Panel 6.1, 6.2, and 6.4 visual inspection opened regenerated PNGs in `handwritten_panels_model_group_color_final_IDK0`; the no-footer layouts, score labels, bottom logos, y-axis labels, and model-name labels render without obvious overlap.
- Latest Panel 6.1 title update XML check: SVG title and visible title are `Proprietary Frontier Vision Language Models (VLMs) vs Human Expert Baseline`; footer elements `0`; rendered hashes: SVG `35DF5E9BABEA2036DD709B0AA04D3A4B734F4650035A106519AA692299B86DD2`; PNG `58FC11680554B665F89D747C43151A457204D4BB52283F31CC9E96FE4BAB4C1E`.
- Latest Panel 6.2 title update XML check: SVG title and visible title are `Open-Weights Vision Language Models (VLMs) vs Human Expert Baseline`; footer elements `0`; rendered hashes: SVG `14FD67A6754AA4B689044430A453DA1DB2DD675769F36626DE25FD112E362FFD`; PNG `8CFDACB04684E0698EED0066B2E111C3A34A04554585208D569FCCB3B9001103`.
- Latest Panel 6.4 title update XML check: SVG title and visible title are `Frontier Vision Language Models (VLMs) vs Human Expert Baseline`; footer elements `0`; rendered hashes: SVG `38A03912D11DF6A29E515AD00E298C0A7465826D7359F203C58F7B603077C355`; PNG `C85705AAD8A30BBEC8F132078E5D36C2EB129F1E6A3CA6FB575B6350A2F882AE`.
- Latest Panel 5.6 title guard XML check: SVG title and visible title remain `Open-access models vs 12 radiologists/trainees`; rendered hashes: SVG `12421C2A37858AF783EAF7BCA955A9E4ECABB42988F92A9D8BB1F67DF314CA67`; PNG `4C8AB2231A150C17BFAA277FA4F28251757287C7B868E9AD806DE99D02249AC7`.
- Latest title-update SVG audit report: `score1000_panel2_group_color_audit_report.json` result is `pass`, rows `16`, panels include `5.6`, `6.1`, `6.2`, `6.4`, and promoted `5.4`, generated at `2026-07-08T23:01:03+00:00`.
- Latest title-update visual inspection opened regenerated 6.1, 6.2, and 6.4 PNGs in `handwritten_panels_model_group_color_final_IDK0`; the requested titles fit and the no-footer layouts remain clear.
- Latest no-footer chart-height XML check: Panel 5.6 remains at metadata/chart height `1610.0`; Panels 6.1, 6.2, and 6.4 each report metadata/chart height `1700.0`, chart top `540.0`, chart bottom `2240.0`, and footer elements `0`.
- Latest no-footer chart-height bar check: the tallest bar height in Panels 6.1, 6.2, and 6.4 is now `1378.2` px, compared with `1305.2` px in unchanged Panel 5.6.
- Latest no-footer chart-height rendered hashes: Panel 6.1 SVG `DC13AFD750C6AAE99CEB5D8419AA13FEFA6C3356D1E392D5AB9EFA747F89899B`, PNG `3116F43BC69DC39F0F30E3BBB37D93A992F943095AA07F4E679799C8A13A013C`; Panel 6.2 SVG `AFFAB6BA5ABDD39CC5EA25D96051E611AC6E3BB82C1248B6BE2C9C2047AD4E27`, PNG `0868686A4EF72EF4B44DD926AE6962C4E9E9368ABB5A3E2C1405DCB145F55462`; Panel 6.4 SVG `DFF7A4FC7244A5ACFC66F6AF8175EA11BFC36CA8CE207D6DBBA22DA6D2946BFF`, PNG `488647DBDDE3CAE62868C3834DB4C55BFF1F47D51D613EEF537F38E779F90A98`.
- Latest no-footer chart-height SVG audit report: `score1000_panel2_group_color_audit_report.json` result is `pass`, generated at `2026-07-08T23:14:40+00:00`; the audit now checks `chart_h` metadata in addition to rendered tick/bar geometry.
- Latest no-footer chart-height visual inspection opened regenerated 6.1, 6.2, and 6.4 PNGs; bars are visibly taller and the label/logo rows remain readable without footer text.

Reusable process lesson: for generated Windows SVG/PNG lanes, keep output folder names short before attempting full panel variants.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | The task spans output snapshots, script isolation, CSV regeneration, and SVG generation. | `manual` |
| SVG generation and audit | `svg-panel-qa`, `output-artifact-verifier` | SVG metadata, geometry, stale-render, and visual-artifact checks are central to the deliverable. | `auto-suggest` |
| CSV/scoring validation | `none` | Local Python scripts and focused CSV checks are sufficient. | `none` |

## Context And Orientation

Relevant scripts live under `scripts/`. The current corrected IDK0 implementation lives in `_IDK0` script copies. The IDK0 output root is `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0`; its current generated child `likert5_score1000_IDK0` is the corrected deliverable.

## Plan Of Work

First, copy the existing stale SVG output directory to a clearly named before-state snapshot and render at least the contact sheet and Panel 5.4 to PNG for immediate visual review. Second, copy the corrected working shared scripts to IDK0-specific names. Third, restore the shared scripts to their staged/shared versions. Fourth, run the corrected IDK0 scripts against the IDK0 master to regenerate CSVs, panel stats, and SVG variants in the IDK0 output root only. Finally, validate that corrected CSVs have 16 rows, one `Human Expert Baseline`, `score2000`, IDK0 metadata, and SVG axis/footer text uses Score2000 0..2000.

## Concrete Steps (Commands)

Run from repo root `C:\Users\thehb\Documents\RadLE v2`.

    py -3.11 <idk0 scoring script> --clean-master <...> --clean-receipt <...> --out-dir <IDK0 score root> --idk-score 0

The successful corrected run used:

    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_radle_v2_score1000_idk0_pipeline.ps1

The focused visual/SVG audit used:

    py -3.11 scripts/audit_radle_v2_score1000_panel23_IDK0.py --mode model-group-color-final --score-root outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0 --out-dir outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0/handwritten_panels_model_group_color_final_IDK0 --idk-score 0

## Validation And Acceptance

Acceptance requires:

- Before-state snapshot exists separately and contains rendered PNGs/contact sheet for user inspection.
- Corrected `score1000_group_summary.csv` has 16 rows, one human row labeled `Human Expert Baseline`, and a `score2000` column.
- Corrected SVG/provenance/captions mention Score2000 display scale and no longer use negative y-axis ticks for Panel 5 charts.
- Shared/original scripts no longer carry the IDK0 Score2000/pooled-human working edits.

Fresh-render evidence must include the rendered before-state path and the corrected after-state path.

## Idempotence And Recovery

Before-state snapshots are additive and safe to rerun with a new timestamped folder. Corrected IDK0 generation is safe to rerun only against the IDK0 output root. If regeneration fails, keep the before-state snapshot and inspect the IDK0 copied script that failed; do not fall back to shared scripts.

## Artifacts And Notes

Before-state preview:

- `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/before_state_score1000_net_score_IDK0_20260708_183000/panel_2_score1000_5_4_icon_ribbon_score1000_bar_chart.before_state.png`
- `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/before_state_score1000_net_score_IDK0_20260708_183000/contact_sheet.before_state.png`

Corrected after-state preview:

- `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0/handwritten_panels_model_group_color_final_IDK0/panel_2_score1000_5_4_icon_ribbon_score1000_bar_chart.png`
- `outputs/radle_v2_stats/final_scoring_radiologist_20260708_161500_IDK0/likert5_score1000_IDK0/handwritten_panels_model_group_color_final_IDK0/contact_sheet.png`

## Interfaces And Dependencies

Required local commands/libraries: `py -3.11`, `pandas`, `playwright`, and `Pillow`. Playwright and Pillow were detected as available on 2026-07-08 18:28 +05:30.
