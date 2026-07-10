# RadLE v2 Score1000 Panel 2 Group-Color Variants

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `AGENTS.md` or `PLANS.md` file was found on 2026-07-07.

## Purpose / Big Picture

Create standalone Score1000 Panel 2-style PNGs that apply the reviewed model-category color/grouping contract and selected non-gray outcome palettes while preserving the current Score1000 data and figure grammar. The current deliverable package contains the original 2.1/3.1 variants plus a 2x2 palette matrix: rank-preserving and grouped layouts for both Option A blue-to-current-red bars and Option C teal-green-to-current-red bars. The production `handwritten_panels/` package must remain unchanged unless a later command explicitly targets it.

## Current State

Current state (2026-07-07 21:55 +05:30, Codex/GPT-5): The user corrected the palette interpretation: the package needs four palette outputs, two blue and two green, not one blue plus one green. The generator now emits six variant SVG/PNG pairs in `handwritten_panels_model_group_color_final`: original 2.1/3.1, blue Option A 2.2/3.2, and green Option C 2.3/3.3. Structural audit, Playwright rendering, visual inspection of the four palette outputs/contact sheet, exact SVG/PNG palette checks, and production-default temp hash checks passed.

## Locked Facts

- Repo root is `C:\Users\thehb\Documents\RadLE v2`.
- Current branch is `codex/radle-v2-handwritten-panels`.
- The checkout is dirty with related and unrelated work; do not reset or revert existing changes.
- Current source package is `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels`.
- Reviewed contract sheet is `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels_model_group_color_options/contact_sheet.png`.
- Final variant output root is `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels_model_group_color_final`.
- Original variant PNGs are `panel_2_score1000_2_1_revised_colored_model_names.png` and `panel_2_score1000_3_1_revised_grouped_bands.png`.
- Category labels and colors are: Human reference `#5f6368`; Closed generalist `#6f43d6`; Open generalist `#00876c`; Open medical `#b04a8a`.
- Closed generalist models are `gpt_5_5`, `claude_fable_5`, `gemini_3_1_pro`, `grok_4_3`, `qwen_3_7_plus`, `glm_5v_turbo`.
- Open generalist models are `gemma_4_31b`, `llama_4_maverick`, `mistral_large_3_2512`, `nemotron_3_omni`, `minimax_m3`, `internvl3_5_8b`.
- Open medical models are `medgemma_1_5_4b`, `octomed_7b`, `lingshu_32b`.
- Production defaults and original 2.1/3.1 current-palette outputs keep their existing outcome color scale. The new 2.2/3.2/2.3/3.3 palette variants deliberately change only outcome colors while preserving B3 legend grammar, bin order, Score1000 scoring, row totals, inside-bar label threshold, and footer text.
- The requested spacing fix applies to both 2.1 and 3.1 final variants. The fix is to move the header/body down, not shrink fonts or rewrite figure text.
- Current final variant category key swatch x positions are Human reference `2109`, Closed generalist `2446`, Open generalist `2817`, and Open medical `3154`, tuned for the larger accessible key labels while keeping the key visually aligned to the chart/bar right edge.
- Current final variant chart geometry is `x=940`, width `2470`, right edge `3410`; this preserves right-edge alignment while creating more room for `40px` left-side labels such as `Board-certified radiologists`.
- Current final variant SVG canvas is `3600x2840`; production default SVGs remain `3600x2700`.
- New 2.2 maps to the 2.1 rank-preserving colored-name layout plus Option A outcome colors: `#08306b`, `#155190`, `#2171b5`, `#6baed6`, `#bdd7e7`, `#deebf7`, `#fee5d9`, `#fcae91`, `#fb6a4a`, `#de2d26`, `#7f0000` in `C L4`, `C L3`, `C L2`, `C L1`, `C L0`, `IDK +1`, `W L0`, `W L1`, `W L2`, `W L3`, `W L4` order.
- New 3.2 maps to the grouped row order/gap layout plus Option A outcome colors: `#08306b`, `#155190`, `#2171b5`, `#6baed6`, `#bdd7e7`, `#deebf7`, `#fee5d9`, `#fcae91`, `#fb6a4a`, `#de2d26`, `#7f0000` in the same legend order.
- New 2.3 maps to the 2.1 rank-preserving colored-name layout plus Option C outcome colors: `#004c3f`, `#006c52`, `#00876c`, `#3fa986`, `#9ad8bd`, `#e5f5e0`, `#fee5d9`, `#fcae91`, `#fb6a4a`, `#de2d26`, `#7f0000` in the same legend order.
- New 3.3 maps to the grouped row order/gap layout plus Option C outcome colors: `#004c3f`, `#006c52`, `#00876c`, `#3fa986`, `#9ad8bd`, `#e5f5e0`, `#fee5d9`, `#fcae91`, `#fb6a4a`, `#de2d26`, `#7f0000` in the same legend order.
- The new 2.2/3.2/2.3/3.3 outcome legend/data bars must not use the old gray neutral `#c7ccd1`; the neutral/IDK bin is the light endpoint immediately before the red side.

## Do Not Revisit

- Do not redesign the figure beyond category coloring/grouping and header spacing. See Decision Log 2026-07-07.
- Do not recompute Score1000 data or alter `score1000_panel23_bins.csv`. See Decision Log 2026-07-07.
- Do not hand-edit generated SVGs or PNGs. Patch the generator, regenerate, audit, render, and visually inspect. See Decision Log 2026-07-07.
- Do not reintroduce the black human-comparator marker. See Decision Log 2026-07-07.
- Do not overwrite the existing production `handwritten_panels/` outputs. See Decision Log 2026-07-07.

## Progress

- [x] (2026-07-07 18:57 +05:30, Codex/GPT-5) Re-read `~/.codex/PLANS.md`, checked for repo-local `AGENTS.md`/`PLANS.md`, recorded dirty branch state, and created this ExecPlan as the first mutation for the slice.
- [x] (2026-07-07 19:01 +05:30, Codex/GPT-5) Reconciled read-only scout receipts for data, contract/layout, and implementation/audit mapping.
- [x] (2026-07-07 19:03 +05:30, Codex/GPT-5) Patched generator with non-default `model-group-color-final` mode.
- [x] (2026-07-07 19:05 +05:30, Codex/GPT-5) Patched audit/render script with matching mode and structural checks.
- [x] (2026-07-07 19:12 +05:30, Codex/GPT-5) Generated, audited, rendered, and visually inspected final PNG artifacts.
- [x] (2026-07-07 19:16 +05:30, Codex/GPT-5) Applied user-requested layout correction: lock category key to the contract-sheet right indentation, lower header/key baseline to `y=430`, and shift rows down as a unit.
- [x] (2026-07-07 19:18 +05:30, Codex/GPT-5) Verified production default behavior in a temp directory: regenerated production Panel 2 and Panel 3 SVGs hash-match the existing production SVGs.
- [x] (2026-07-07 19:37 +05:30, Codex/GPT-5) Added user-supplied top logos to the final variant mode only: KCDH-A/Ashoka on the left and cropped transparent CRASH Lab PNG on the right.
- [x] (2026-07-07 19:39 +05:30, Codex/GPT-5) Added audit enforcement that both final variant panels use the exact visible panel title `Diagnostic outcomes stratified by confidence`.
- [x] (2026-07-07 19:45 +05:30, Codex/GPT-5) Shifted the final variant panel content block down by `48px` while leaving the top logos and centered figure title fixed; this increases logo breathing room and tightens the x-axis-to-bottom-legend spacing.
- [x] (2026-07-07 19:49 +05:30, Codex/GPT-5) Shifted the top category key right by `364px`; Chromium measured the `Open medical` label ending at `x=3410.17`, aligned to the chart/bar right edge `x=3410`.
- [x] (2026-07-07 19:56 +05:30, Codex/GPT-5) Applied user-requested accessibility pass: larger/darker variant small text, horizontally compressed variant bars, taller variant canvas and larger wrapped footer, and right-shifted 3.1 category group headers. Regenerated/audited/rendered the final package and verified production default SVG hashes still match.
- [x] (2026-07-07 19:56 +05:30, Codex/GPT-5) Refined 3.1 category header geometry after user crop: group labels now start at `x=170`, and rules run from `x=150` to `x=760`, avoiding both the score column and the bar/count area.
- [x] (2026-07-07 19:56 +05:30, Codex/GPT-5) Softened the enlarged footer by keeping the `34px` size but changing `variant-micro` to regular weight (`400`) and the same dark ink color as reader/model labels; regenerated/audited/rendered the package.
- [x] (2026-07-07 19:56 +05:30, Codex/GPT-5) Applied requested final font changes: variant `.figure-title` override to `78px`, `.variant-row-label` to `40px`, `.variant-micro` to `40px`, plus `14px` extra title/subtitle gap. Recompressed variant bars to `x=940`, width `2470` to preserve clearance for the larger labels.
- [x] (2026-07-07 19:56 +05:30, Codex/GPT-5) Increased the final variant left count-to-bar gutter from `6px` to `18px` in both 2.1 and 3.1, regenerated/audited/rendered, and visually checked the updated PNGs.
- [x] (2026-07-07 20:20 +05:30, Codex/GPT-5) Nudged the final variant Score column from `x=130` to `x=134` in both 2.1 and 3.1, regenerated/audited/rendered, visually checked the PNGs, and confirmed the SVG score labels/header emit at `x=134.0`.
- [x] (2026-07-07 21:20 +05:30, Codex/GPT-5) Initially added only 2.2/3.2 as additive SVG/PNG outputs in `model-group-color-final`; this two-output palette interpretation was later corrected by the user at 21:55.
- [x] (2026-07-07 21:20 +05:30, Codex/GPT-5) Initially extended the variant audit for the two-output palette pass; the final audit now covers the corrected four palette outputs.
- [x] (2026-07-07 21:20 +05:30, Codex/GPT-5) Initially regenerated the package for the two-output palette pass; superseded by the 21:55 six-variant package regeneration.
- [x] (2026-07-07 21:46 +05:30, Codex/GPT-5) Applied the no-left-group-header treatment to the then-new grouped palette output: grouped order/gaps stay, left group headers/rules hide, and all 17 reader/model names carry category color.
- [x] (2026-07-07 21:46 +05:30, Codex/GPT-5) Regenerated the then-four-file package and verified targeted SVG counts for the then-current 2.2/3.2 outputs; superseded by the 21:55 four-palette-output matrix.
- [x] (2026-07-07 21:55 +05:30, Codex/GPT-5) Per user correction, fixed the palette matrix from two new outputs to four: 2.2/3.2 use Option A blue-to-current-red bars, and 2.3/3.3 use Option C teal-green-to-current-red bars.
- [x] (2026-07-07 21:55 +05:30, Codex/GPT-5) Regenerated the six-variant package, ran full structural audit plus Playwright rendering, visually inspected the four palette PNGs and contact sheet, verified exact legend fills/no-gray/PNG dimensions for all four palette outputs, and reconfirmed production default Panel 2/3 SVG hashes match existing outputs from a temp run.

## Surprises & Discoveries

- Observation: SVG CSS classes overrode plain `fill` attributes on category-colored text.
  Evidence: Initial render showed model names/group headers still black until color was moved into scoped inline `style` attributes and audited.
  Date/Author: 2026-07-07, Codex/GPT-5

- Observation: The first grouped 3.1 render had visible dead space below `Lingshu 32B`; the user preferred moving the plot body down and making the extra whitespace live above the header/body area.
  Evidence: User crop of the 3.1 bottom gap, followed by the instruction to retain right-key indentation and create the top breathing room; final render uses `VARIANT_HEADER_Y = 430`.
  Date/Author: 2026-07-07, Codex/GPT-5

- Observation: The user-supplied CRASH Lab PNG has an RGBA transparent background and a non-transparent content box `(156, 573, 1329, 991)`.
  Evidence: The logo was cropped to `scripts/assets/radle_score1000_logos/crash_lab_logo.png` before embedding so it does not carry excess transparent padding.
  Date/Author: 2026-07-07, Codex/GPT-5

- Observation: The first palette implementation incorrectly produced only two palette outputs, one blue and one green, instead of the requested four-output 2x2 matrix.
  Evidence: User correction: "nope, i wanted 4 options / 2 with blue and 2 with green bars"; fixed package now contains blue 2.2/3.2 and green 2.3/3.3 palette outputs.
  Date/Author: 2026-07-07, Codex/GPT-5

## Decision Log

- Decision: Add a non-default generator/audit mode instead of changing production defaults.
  Rationale: The request asks for new standalone variant PNGs while preserving the existing production Panel 2/3 package.
  Date/Author: 2026-07-07, Codex/GPT-5

- Decision: Implement the spacing fix as layout movement, not font shrinkage or text edits.
  Rationale: The user showed the `Score` header was too tight against the group header and requested more space above `Score` while keeping text/formatting otherwise as-is.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Decision: Keep all writing in the main thread while using subagents only for read-only scouting.
  Rationale: The generator and audit scripts are shared files, so single-writer implementation avoids conflicting edits.
  Date/Author: 2026-07-07, Codex/GPT-5

- Decision: Lock the category key to the reviewed 2.1 right-side swatch x positions and audit those coordinates.
  Rationale: The user asked to take the key back to the right indentation used in the reviewed contract sheet.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Decision: Keep the new logos scoped to `model-group-color-final` and embed them as data URIs in the generated SVGs.
  Rationale: The requested deliverables are standalone PNGs, while embedding keeps the source SVGs renderable without depending on external image files at view time.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Decision: Move the final variant content block down as one unit instead of moving only the title or only the axis.
  Rationale: The user wanted more space around the top logos and less awkward empty space between the x-axis labels and the bottom legend; shifting title/subtitle/header/body/x-axis together preserves layout relationships while closing the lower gap.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Decision: Align the top category key to the chart/bar right edge rather than the older contract-sheet absolute x positions.
  Rationale: After the final panel layout and chart geometry were in place, the user wanted the key visually indented to the same right edge as the bars.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Decision: Use a taller variant-only canvas and compressed horizontal bar span for readability instead of shrinking text.
  Rationale: The user wanted subtitle, model names, score labels, and especially footer text to survive social-media compression; shortening the bar span and increasing the canvas height created room for larger text without changing Score1000 data or production outputs.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Decision: Move 3.1 category group headers to `x=170` and limit separator rules to `x=150..760`.
  Rationale: The user-supplied crops first showed category labels occupying the score column, then showed the longer rules extending awkwardly toward the bars; this geometry keeps group labels in the reader/model area while keeping rules away from the count/bar lane.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Decision: Interpret the corrected palette request as a 2x2 matrix: 2.2 and 3.2 use selected Option A blue-to-current-red outcome colors; 2.3 and 3.3 use selected Option C teal-green-to-current-red outcome colors.
  Rationale: The user clarified they wanted four options: two blue and two green. This preserves the existing 2.x rank-preserving and 3.x grouped layout lineage while applying both selected palettes to both layout families.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

- Decision: For the newer Blue/Green outputs, keep the top category key but hide left-side group header text and separator rules wherever that left grouping treatment appears.
  Rationale: The user chose Option A after the mirror check: the crop-targeted left group labels/rules should vanish, the top key should remain, group gaps should stay, and reader/model names should carry category color.
  Date/Author: 2026-07-07, Codex/GPT-5 and user

## Revision Notes

- v1 (2026-07-07, Codex/GPT-5): Created the plan from the user-approved implementation plan and the requested header-spacing correction.
- v2 (2026-07-07, Codex/GPT-5): Recorded final implementation, right-key indentation lock, lower top spacing, audit/render/visual verification, and generated artifacts.
- v3 (2026-07-07, Codex/GPT-5): Added header logos to the final variant mode and enforced identical visible panel title text across both final PNGs.
- v4 (2026-07-07, Codex/GPT-5): Shifted final variant panel content down as a unit and added audit checks for title y-position and x-axis-to-legend spacing.
- v5 (2026-07-07, Codex/GPT-5): Shifted the top category key to align its rendered right edge with the bar/chart right edge.
- v6 (2026-07-07, Codex/GPT-5): Added the accessibility pass, larger final font sizes, shorter horizontal bars, taller footer canvas, regular-weight footer text, grouped-header and grouped-rule position audits, and refreshed validation evidence.
- v7 (2026-07-07, Codex/GPT-5): Added the `18px` left count-to-bar gutter requested from the cropped visual review and refreshed final variant PNGs.
- v8 (2026-07-07, Codex/GPT-5): Moved the variant Score column 4px right, from `x=130` to `x=134`, to add a little more left-side padding while keeping row labels and bars fixed.
- v9 (2026-07-07, Codex/GPT-5): Reopened the plan for additive 2.2/3.2 palette variants and recorded the Option A/Option C mapping plus no-gray IDK endpoint invariant before editing scripts.
- v10 (2026-07-07, Codex/GPT-5): Recorded completed 2.2/3.2 implementation, regenerated artifact names, palette validation evidence, visual QA, and production-default hash proof.
- v11 (2026-07-07, Codex/GPT-5): Recorded the no-left-category treatment for 3.2 and the confirmation that 2.2 already matches the newer Blue no-left-category behavior.
- v12 (2026-07-07, Codex/GPT-5): Reconciled the user correction that the palette slice must be four outputs, not two; recorded blue 2.2/3.2 and green 2.3/3.3 artifacts plus fresh validation.

## Outcomes & Retrospective

Implemented. Final artifacts are in `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels_model_group_color_final/`. Structural audit and Playwright rendering passed after the final layout correction. Visual inspection confirmed the 2.1 rank-preserving colored-name output and the 3.1 grouped output keep the requested category treatment without changing Score1000 data, labels, captions, or scoring logic. The corrected 2.2/3.2/2.3/3.3 outputs preserve the same Score1000 data, bin order, and single-line B3 legend grammar while applying the two selected non-gray outcome palettes across both layout families.

The 2026-07-07 21:55 +05:30 corrected palette matrix pass added/verified these four palette outputs:

- `panel_2_score1000_2_2_option_a_blue_to_red_colored_model_names.svg` and `.png`: rank-preserving 2.1 layout with Option A colors `#08306b`, `#155190`, `#2171b5`, `#6baed6`, `#bdd7e7`, `#deebf7`, `#fee5d9`, `#fcae91`, `#fb6a4a`, `#de2d26`, `#7f0000`.
- `panel_2_score1000_3_2_option_a_blue_to_red_grouped_bands.svg` and `.png`: grouped row order/gap layout with hidden left group headers/rules, category-colored reader/model names, and the same Option A colors.
- `panel_2_score1000_2_3_option_c_teal_green_to_red_colored_model_names.svg` and `.png`: rank-preserving 2.1 layout with Option C colors `#004c3f`, `#006c52`, `#00876c`, `#3fa986`, `#9ad8bd`, `#e5f5e0`, `#fee5d9`, `#fcae91`, `#fb6a4a`, `#de2d26`, `#7f0000`.
- `panel_2_score1000_3_3_option_c_teal_green_to_red_grouped_bands.svg` and `.png`: grouped row order/gap layout with hidden left group headers/rules, category-colored reader/model names, and the same Option C colors.

Validation evidence for the corrected palette matrix pass:

    py -3.11 -m py_compile scripts/make_radle_v2_score1000_panel23_svg.py scripts/audit_radle_v2_score1000_panel23.py
    # exited 0

    py -3.11 scripts/make_radle_v2_score1000_panel23_svg.py --mode model-group-color-final --source-panel-dir outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels --out-dir outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels_model_group_color_final
    # [PASS] generated Score1000 Panel 2 group-color variants ...

    py -3.11 scripts/audit_radle_v2_score1000_panel23.py --mode model-group-color-final --source-panel-dir outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels --out-dir outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels_model_group_color_final
    # [PASS] audited Score1000 Panel 2 group-color package ...
    # [PASS] rendered ...panel_2_score1000_2_2_option_a_blue_to_red_colored_model_names.png
    # [PASS] rendered ...panel_2_score1000_3_2_option_a_blue_to_red_grouped_bands.png
    # [PASS] rendered ...panel_2_score1000_2_3_option_c_teal_green_to_red_colored_model_names.png
    # [PASS] rendered ...panel_2_score1000_3_3_option_c_teal_green_to_red_grouped_bands.png

    # Explicit SVG/PNG palette check:
    # 2.2 blue rank and 3.2 blue grouped legend_fills = #08306b,#155190,#2171b5,#6baed6,#bdd7e7,#deebf7,#fee5d9,#fcae91,#fb6a4a,#de2d26,#7f0000; forbidden_gray_roles = []; png_dimensions = 3600x2840.
    # 2.3 green rank and 3.3 green grouped legend_fills = #004c3f,#006c52,#00876c,#3fa986,#9ad8bd,#e5f5e0,#fee5d9,#fcae91,#fb6a4a,#de2d26,#7f0000; forbidden_gray_roles = []; png_dimensions = 3600x2840.

    # Production default temp run:
    # panel_2_score1000_edge_justified_ledger.svg hash_match = True
    # panel_3_score1000_100_barcode_percentage_strip.svg hash_match = True

Fresh visual inspection used:

- `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels_model_group_color_final/panel_2_score1000_2_2_option_a_blue_to_red_colored_model_names.png`
- `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels_model_group_color_final/panel_2_score1000_3_2_option_a_blue_to_red_grouped_bands.png`
- `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels_model_group_color_final/panel_2_score1000_2_3_option_c_teal_green_to_red_colored_model_names.png`
- `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels_model_group_color_final/panel_2_score1000_3_3_option_c_teal_green_to_red_grouped_bands.png`
- `outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels_model_group_color_final/contact_sheet.png`

Production default behavior was checked without touching the production output directory: after seeding a temp directory with the required production CSV/provenance, the default generator produced hash-identical `panel_2_score1000_edge_justified_ledger.svg` and `panel_3_score1000_100_barcode_percentage_strip.svg`.

Final variant outputs now include embedded top logos. The logo source assets are `scripts/assets/radle_score1000_logos/kcdha_logo.svg` and `scripts/assets/radle_score1000_logos/crash_lab_logo.png`; their hashes are stored in SVG metadata, `data_provenance.json`, and `figure_manifest.json`. The variant audit verifies the logo positions, embedded data-image URIs, logo hashes, and the exact shared title `Diagnostic outcomes stratified by confidence` on both panels.

The final variant content block is shifted down by `48px` relative to the previous logo render. The centered figure title and logos remain fixed, while the panel title, subtitle, `Score` / `Reader / model` header, category key, grouped headers, bars, and x-axis move down together. The bottom B3 legend remains fixed, which reduces the x-axis tick-label-to-legend gap and removes the loose lower whitespace without changing score/data logic.

The count labels immediately left of the bars now use an `18px` gutter before the bar start in both 2.1 and 3.1. This restores breathing room similar to the right-side totals while retaining the compressed horizontal bar length and the larger reader/model text.

The Score column in both 2.1 and 3.1 now uses the shared `VARIANT_SCORE_X = 134`, moving the Score header and score values 4px toward the reader/model labels. The row-label anchor remains `x=820`, so the visual change is limited to adding a little more left-side padding.

The latest accessibility pass keeps the category key visually aligned to the chart edge while using larger key labels. Current swatch x positions are Human reference `2109`, Closed generalist `2446`, Open generalist `2817`, and Open medical `3154`. Variant chart geometry is now `x=940`, width `2470`, right edge `3410`, which creates visible clearance around the long `Board-certified radiologists` row label and its adjacent count even after row labels were increased to `40px`. Browser client-rect measurement after regeneration showed both 2.1 and 3.1 have about `88.6px` score-to-name clearance and `45.8px` name-to-left-count clearance for the fragile board-certified row.

The variant canvas is now `3600x2840`, allowing the footer to render at `34px` with a wrapped three-line note. The grouped 3.1 category labels start at `x=170`, while separator rules run from `x=150` to `x=760`, out of the score column and before the count/bar lane. The structural audit checks the taller variant canvas, compressed bar span, accessible text classes, grouped header x-position, and grouped rule span. Production default behavior was rechecked after the accessibility pass: the generated production Panel 2 and Panel 3 SVG hashes still match the existing production SVGs (`41C5D8357240767036CE89D5BDF753CDAD05B90D52AD4DDA49C83FF6B5990CA9` and `AABB572710AA694BD302E3EFFDF58963C961C3A239AFEEA9074B6B126DFF9782`).

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning and living state | `execplan` | Required for this multi-step generated-artifact workflow | `auto-suggest` |
| SVG implementation/audit | `svg-panel-qa` | Structural SVG geometry checks catch header-spacing and color-scope regressions before visual review | `auto-suggest` |
| Visual QA | `output-artifact-verifier` | Final acceptance depends on fresh PNG render inspection, not exit codes alone | `auto-suggest` |
| Data reconciliation | `none` | Existing Score1000 CSV and panel package are already the source; this slice must not recompute data | `none` |

## Context And Orientation

The active generator is `scripts/make_radle_v2_score1000_panel23_svg.py`. It currently writes Panel 2 and Panel 3 SVG/support artifacts into `handwritten_panels/` by default. The active audit/render script is `scripts/audit_radle_v2_score1000_panel23.py`; it validates the generated package and uses Playwright to render PNGs.

The reviewed option folder contains SVG-only prototypes and a contact sheet. They are contract references, not final source files to hand-edit. The final implementation must regenerate source-backed SVGs and PNGs from the current Score1000 panel CSV/provenance.

## Plan Of Work

Add a `--mode` CLI option to both scripts. The default `production` mode preserves existing behavior. The new `model-group-color-final` mode reads `score1000_panel23_bins.csv` and `score1000_likert_direction_provenance.json` from `--source-panel-dir`, writes final variant files to `--out-dir`, and renders only the two Panel 2-style variants.

The rank-preserving 2.1 variant keeps the current row order and colors only the visible model/human names by category. The grouped 3.1 variant orders groups as Human reference, Closed generalist, Open generalist, Open medical, preserving original Score1000 rank order within each group. Both variants keep the current Panel 2 outcome bars, scale, labels, and footer note.

Header layout in final variant mode places the `Score` / `Reader / model` baseline at `y=478` after the later content shift. The category key aligns to that header line and uses the current accessible key x positions. In 3.1 the first group header remains at least `48px` below that header baseline, with grouped body rows shifted down as a unit, grouped category text starting at `x=170`, and grouped separator rules ending at `x=760`.

## Concrete Steps

From repo root, compile scripts:

    py -3.11 -m py_compile scripts/make_radle_v2_score1000_panel23_svg.py scripts/audit_radle_v2_score1000_panel23.py

Generate variant outputs:

    py -3.11 scripts/make_radle_v2_score1000_panel23_svg.py --mode model-group-color-final --source-panel-dir outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels --out-dir outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels_model_group_color_final

Audit and render variant outputs:

    py -3.11 scripts/audit_radle_v2_score1000_panel23.py --mode model-group-color-final --source-panel-dir outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels --out-dir outputs/radle_v2_stats/final_scoring_radiologist_20260706_001147/likert5_score1000/handwritten_panels_model_group_color_final

## Validation And Acceptance

Acceptance requires:

- `py_compile` exits 0 for the edited scripts.
- Existing no-arg production generator/audit behavior remains available and unchanged by default.
- Variant generation writes both SVGs and both PNGs under `handwritten_panels_model_group_color_final`.
- Variant audit verifies source hashes, row/bin reconciliation, rank-preserving 2.1 order, grouped 3.1 order, exact category colors, and color-scope limits.
- Category color appears only in reader/model names, group headers, and category key.
- Category color does not appear inside outcome bars or the B3 outcome legend.
- No per-row category subtext appears.
- No black human-comparator marker appears.
- Fresh PNG render inspection finds no hard overlap or crowding around `Score`, `Reader / model`, or the first group header.
- Fresh PNG render inspection confirms the enlarged footer fits inside the `3600x2840` variant canvas and 3.1 category group labels no longer sit in score territory.

## Idempotence And Recovery

The variant generator owns only the final variant output directory. It is safe to rerun and overwrite files in `handwritten_panels_model_group_color_final`. If audit or visual QA fails, patch only the generator/audit scripts, rerun generation, rerun audit/render, and reinspect the fresh PNGs. Do not patch emitted SVGs or PNGs directly.

## Artifacts And Notes

Initial dirty-tree evidence from 2026-07-07 18:57 +05:30:

    ## codex/radle-v2-handwritten-panels
    AM scripts/audit_radle_v2_score1000_panel23.py
    AM scripts/make_radle_v2_score1000_panel23_svg.py
    ... additional unrelated and related dirty files omitted here; rerun git status before staging.

## Interfaces And Dependencies

Use Python 3.11 via `py -3.11`. The audit/render path depends on Playwright Chromium, matching the existing `render_visual_outputs` implementation in `scripts/audit_radle_v2_score1000_panel23.py`.
