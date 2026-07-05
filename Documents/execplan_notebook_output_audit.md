# Audit RadLE Notebook Saved Outputs

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md` and the repo instruction to place ExecPlans under `Documents/` when present.

## Purpose / Big Picture

The user asked to audit the saved outputs in `C:\Users\thehb\Downloads\RadLE_v1_5_Morning (2).ipynb`. The goal is to identify output-level defects without rerunning the notebook or changing source data. The audit inspects saved cell outputs, execution freshness, table payloads, export messages, and self-reported repair/audit flags.

## Current State

Current state (2026-06-19 23:06 +05:30, Codex/GPT-5): Audit completed from saved notebook JSON, parsed display tables, a localhost browser render of `Documents/RadLE_v1_5_Morning_2_saved_outputs_audit.html`, and a direct read of `Documents/RadLE_v1_5_Morning_2.md`. The temporary localhost server has been stopped. Next: report Markdown-read findings to the user.

## Locked Facts

- Source notebook audited: `C:\Users\thehb\Downloads\RadLE_v1_5_Morning (2).ipynb`, last modified 2026-06-19 22:49:23 local time.
- The notebook has 10 cells and no saved Python traceback outputs.
- Cell 4 has execution count 27, while cells 5 through 9 have execution counts 7 through 11, so downstream scorer/audit/export outputs are older than the saved benchmark-run output.
- Cell 4 reports resuming `raw/results.csv` at 100 rows, completing 200 cases, making 1029 API calls, and saving final raw output and backups.
- Cell 6 saved audit tables report 10 `paid_repair` cells and 5 `analysis_flag` cells.
- Cell 7 saved output has `REPAIR_CONFIRMATION = "NO"` behavior: no API calls, no cleanups, and no files written.
- Cell 8 promotes the private final file from `raw/results.csv`, not from `repair/repaired_results.csv`.
- Cell 9 prints an empty value after `Public sanitized call log CSV:`.
- Localhost browser render at `http://127.0.0.1:8766/RadLE_v1_5_Morning_2_saved_outputs_audit.html` loaded successfully with 10 sections, no page-level horizontal overflow, and scrollable wide table containers.
- Visual table metrics show horizontal overflow in Cell 4 output 2, Cell 5 output 2, Cell 6 outputs 8/10/12/14, and Cell 7 output 4; Cell 5 output 2 and Cell 7 output 4 also have vertical overflow.
- Markdown export `Documents/RadLE_v1_5_Morning_2.md` was generated from saved notebook JSON without executing cells; size 169902 bytes, last modified 2026-06-19 23:06 local time.
- Direct Markdown review confirms the generated `.md` preserves saved output streams and display tables, but tables that were already truncated by notebook display still contain ellipses and are not full data exports.

## Do Not Revisit

- Do not treat a successful notebook run as proof that downstream exported artifacts are fresh; execution counts contradict that. See Decision Log 2026-06-19.
- Do not claim the wide tables are fully visible by default; key columns require horizontal scrolling in multiple saved outputs. See Decision Log 2026-06-19.

## Progress

- [x] (2026-06-19 22:50 +05:30, Codex/GPT-5) Confirmed the notebook exists in Downloads and read the output-artifact verification workflow.
- [x] (2026-06-19 22:52 +05:30, Codex/GPT-5) Parsed notebook JSON with the bundled Python runtime and inventoried cell output types, execution counts, and media/table payloads.
- [x] (2026-06-19 22:54 +05:30, Codex/GPT-5) Generated `Documents/RadLE_v1_5_Morning_2_saved_outputs_audit.html` as a derived local HTML render of saved outputs.
- [x] (2026-06-19 22:55 +05:30, Codex/GPT-5) Attempted in-app browser inspection of the local HTML render; blocked by browser policy for `file://` URLs.
- [x] (2026-06-19 22:57 +05:30, Codex/GPT-5) Parsed saved display tables with pandas to extract repair targets, analysis flags, dataset summary, and export messages.
- [x] (2026-06-19 22:58 +05:30, Codex/GPT-5) Recorded audit evidence and prepared final findings.
- [x] (2026-06-19 23:01 +05:30, Codex/GPT-5) Served the audit HTML from `Documents/` over `http://127.0.0.1:8766/` and confirmed HTTP 200 for the render.
- [x] (2026-06-19 23:03 +05:30, Codex/GPT-5) Opened the localhost render in the in-app browser, captured viewport screenshots, and recorded visual table overflow metrics.
- [x] (2026-06-19 23:06 +05:30, Codex/GPT-5) Generated `Documents/RadLE_v1_5_Morning_2.md` from saved notebook JSON, verified key lines, stopped the temporary localhost server, and removed transient server logs.
- [x] (2026-06-19 23:06 +05:30, Codex/GPT-5) Read the Markdown export directly and checked audit-relevant line anchors for execution counts, repair targets, final promotion, public export, and missing outputs.

## Surprises & Discoveries

- (2026-06-19 22:55 +05:30, Codex/GPT-5) The in-app browser blocked direct local `file://` inspection. Static structural audit continued without attempting to route around the browser policy.
- (2026-06-19 22:57 +05:30, Codex/GPT-5) The saved outputs simultaneously show a completed benchmark run and stale downstream export outputs, because the benchmark cell was re-run later than the audit/export cells.
- (2026-06-19 23:03 +05:30, Codex/GPT-5) Serving the already-generated audit HTML over localhost allowed browser inspection without using the blocked `file://` route.
- (2026-06-19 23:03 +05:30, Codex/GPT-5) The render itself is readable and has no page-level horizontal overflow, but the key DataFrame outputs rely on horizontal scrollbars and hide right-side fields by default.
- (2026-06-19 23:06 +05:30, Codex/GPT-5) `nbconvert` and `tabulate` were not installed in available Python runtimes, so the Markdown export used a small local converter with a custom Markdown table writer.
- (2026-06-19 23:06 +05:30, Codex/GPT-5) The Markdown export is easier to search than notebook JSON, but it cannot recover hidden DataFrame columns/cells that the notebook output itself serialized as truncated display text.

## Decision Log

- (2026-06-19 22:52 +05:30, Codex/GPT-5) Use saved-output inspection only; do not rerun API-bearing notebook cells.
- (2026-06-19 22:55 +05:30, Codex/GPT-5) After browser policy blocked the local file render, continue with JSON/table/static evidence instead of alternate browser routing.
- (2026-06-19 22:58 +05:30, Codex/GPT-5) Treat stale execution order as the highest-priority output defect because it can invalidate every downstream scorer, final, and public release output.
- (2026-06-19 23:03 +05:30, Codex/GPT-5) Treat scroll-contained wide tables as a presentation defect for audit/review use, not as a data-integrity defect.
- (2026-06-19 23:06 +05:30, Codex/GPT-5) Generate Markdown from saved notebook JSON only and preserve saved output streams/tables without rerunning API-bearing cells.

## Revision Notes

- (2026-06-19 22:58 +05:30, Codex/GPT-5) Initial ExecPlan created after audit evidence was collected, to preserve the multi-step audit trail per repo instructions.
- (2026-06-19 23:03 +05:30, Codex/GPT-5) Updated after the user granted full access and localhost browser verification completed.
- (2026-06-19 23:06 +05:30, Codex/GPT-5) Updated after the requested Markdown export was created and verified.

## Outcomes & Retrospective

The audit found no saved Python traceback, but did find material output problems: stale downstream outputs, unrepaired paid-repair targets, preserved analysis flags, a raw-results final promotion despite skipped repair, and an empty public sanitized call-log path. Visual browser QA also found that the largest saved DataFrame outputs are scroll-contained and hide important right-side columns by default, which weakens their usefulness as review artifacts. A Markdown export now exists for easier text review. No reusable skill change is proposed; the existing output-artifact-verifier skill covered the workflow.

## Suggested Skills By Phase

- Phase 1, saved-output audit: `output-artifact-verifier`, activation `auto-suggest`, because the request was to audit generated notebook outputs.
- Phase 2, browser render check: `browser:control-in-app-browser`, activation `auto-suggest`, completed by serving the render over localhost after direct `file://` navigation was blocked.
- Phase 3, reporting: `none`, activation `none`, because findings can be reported directly from parsed notebook evidence.
