# Native Anthropic Claude 4.8 Opus migration

This ExecPlan is a living document. Sections must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. Stored in `Documents/` per repo instructions.

## Purpose / Big Picture

Migrate `claude_4_8_opus` from OpenRouter (`anthropic/claude-opus-4.7` via OpenAI SDK) to the
native Anthropic Messages API (`claude-opus-4-8` via `anthropic` SDK). All other models remain
on OpenRouter. Proof of success: local 1-case smoke test writing a valid CSV and scorer-view CSV,
followed by a commit pushed to `origin/main` for Colab validation.

## Current State

2026-06-12, Claude Sonnet 4.6 (Claude Code): Implementation complete. Local smoke test passed
(`diagnosis='Thyroid goiter' provider='Anthropic'`). Committed and pushed to `origin/main`.
Handing back for Colab validation.

## Locked Facts

- `src/radle_benchmark.py` owns benchmark logic; `notebooks/RadLE_v1_5_Morning.ipynb` is the Colab runner.
- Native model ID: `claude-opus-4-8`. Model name in CSV: `claude_4_8_opus`.
- Extended thinking: `thinking={"type": "adaptive"}` + `output_config={"effort": "high"}` — **not** `type=enabled`
  (Claude 4.x API change; `type=enabled` returns 400).
- `temperature` must be absent when extended thinking is used.
- Anthropic usage object: `.usage.input_tokens` / `.usage.output_tokens` — NOT `.prompt_tokens` / `.completion_tokens`.
- `radle_api_keys.env` is ignored; `ANTHROPIC_API_KEY` already present locally.
- Colab secret: `ANTHROPIC_API_KEY`. Notebook installs `anthropic` via pip in Cell 1.
- Local smoke image: `local_smoke/images/55.2.jpg`. Live output: `local_smoke/radle_native_anthropic_live.csv` (ignored).

## Do Not Revisit

- Do not migrate non-Claude models in this pass.
- Do not change the benchmark prompt, Drive paths, TEST_LIMIT, or CSV schema.

## Progress

- [x] (2026-06-12, Claude Sonnet 4.6) Inspected repo, read GPT-5.5 exec plan, confirmed anthropic==0.105.2 installed.
- [x] (2026-06-12, Claude Sonnet 4.6) Added `import anthropic`, updated MODELS, NO_TEMPERATURE_MODELS.
- [x] (2026-06-12, Claude Sonnet 4.6) Added `uses_native_anthropic`, `_convert_content_for_anthropic`, updated `build_api_params`, `get_api_client`, `run_benchmark`.
- [x] (2026-06-12, Claude Sonnet 4.6) Updated notebook Cells 1, 2, 4 (pip install, ANTHROPIC_API_KEY, anthropic_client, assertion, run_benchmark call).
- [x] (2026-06-12, Claude Sonnet 4.6) Syntax check passed; no-network routing validation passed.
- [x] (2026-06-12, Claude Sonnet 4.6) Live smoke test passed: `OK (4.4s | 179 out / 1924 in)`.
- [x] (2026-06-12, Claude Sonnet 4.6) Raw CSV and scorer-view CSV validated with pandas.
- [x] (2026-06-12, Claude Sonnet 4.6) Committed and pushed to `origin/main`.

## Surprises & Discoveries

- (2026-06-12, Claude Sonnet 4.6) `thinking.type="enabled"` rejected with 400 for `claude-opus-4-8`.
  Claude 4.x uses `{"type": "adaptive"}` + `output_config={"effort": "high"}` instead of
  `{"type": "enabled", "budget_tokens": N}` (Claude 3.x format).
- (2026-06-12, Claude Sonnet 4.6) Anthropic usage object uses `.input_tokens`/`.output_tokens`,
  not `.prompt_tokens`/`.completion_tokens` (OpenAI naming). Reasoning tokens are not separately
  reported; `Reasoning_Tokens_claude_4_8_opus` will be 0.

## Decision Log

- (2026-06-12, Claude Sonnet 4.6) Provider adapter approach: branch on `uses_native_anthropic(model)`
  at the API call site and response parsing site; keep OpenAI/OpenRouter path completely unchanged.
- (2026-06-12, Claude Sonnet 4.6) `Actual_Request_Extra_*` column records `{thinking, output_config}`
  for Anthropic (vs `extra_body` for OpenRouter); column name kept per schema-unchanged constraint.
- (2026-06-12, Claude Sonnet 4.6) `Reasoning_Tokens_*` = 0 for Anthropic (token breakdown not in usage object).

## Outcomes & Retrospective

- Syntax check: `py -3.11 -m py_compile src/radle_benchmark.py` → OK
- No-network routing: all 6 assertions passed
- Live run: `OK (4.4s | 179 out / 1924 in | 40.7 tok/sec)`
- Raw CSV shape: (1, 19). Required columns present. `provider=Anthropic`. `diagnosis='Thyroid goiter'`.
- Scorer-view shape: (1, 4). `Diagnosis_claude_4_8_opus='Thyroid goiter'`, `Likert=1`.
