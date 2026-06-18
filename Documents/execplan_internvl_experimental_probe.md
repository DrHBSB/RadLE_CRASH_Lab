# Build Experimental InternVL Probe Path

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` exists. The prompt-provided AGENTS.md instruction requires an ExecPlan for complex features, multi-step analyses, or significant refactors and prefers `Documents/`.

## Purpose / Big Picture

This work evaluates whether InternVL3.5, especially `OpenGVLab/InternVL3_5-8B`, should become a separate experimental RadLE benchmark path. The official RadLE roster in `src/radle_benchmark.py` must remain unchanged so the pushed official Colab run continues to use the current default models. The new path should let a hosted InternVL endpoint be smoke-tested on 1 case and then 3-5 cases, producing RadLE-shaped CSV columns such as `Diagnosis_internvl3_5_8b`, `Likert_internvl3_5_8b`, token, latency, provider, and raw-response fields.

The intended user-visible result is a reproducible local command that points at an OpenAI-compatible InternVL endpoint, sends RadLE image prompts, and writes ignored CSV output under `local_smoke/` without modifying official benchmark defaults or committing confidential data.

## Current State

Current state (2026-06-18 20:22 +05:30, Codex/GPT-5): The separate experimental probe script exists at `scripts/internvl_experimental_probe.py`, and the official files `src/radle_benchmark.py` and `notebooks/RadLE_v1_5_Morning.ipynb` have no diff. Local validation passed for compile, notebook JSON parse, `git diff --check`, and a 1-case dry-run schema smoke using the bundled Codex Python runtime. No `INTERNVL_BASE_URL` or `INTERNVL_API_KEY` was found in the process environment or `radle_api_keys.env`, so live InternVL endpoint reachability is not yet validated. Next: configure a vLLM/SGLang/Hugging Face OpenAI-compatible endpoint and run the 1-case live smoke command in this plan.

## Locked Facts

- Official RadLE execution remains `notebooks/RadLE_v1_5_Morning.ipynb` importing `src/radle_benchmark.py`.
- The official default roster in `src/radle_benchmark.py` must not be altered for this InternVL experiment unless the user explicitly approves later.
- The official OpenRouter replacements already pushed are `qwen_3_7_plus` -> `qwen/qwen3.7-plus` and `mistral_large_3_2512` -> `mistralai/mistral-large-2512`.
- OpenRouter's public model list checked on 2026-06-18 had no `InternVL`, `OpenGVLab`, or lowercase `intern` match.
- `OpenGVLab/InternVL3_5-8B` exists on Hugging Face and is labeled image-text-to-text.
- The Hugging Face model card documents vLLM and SGLang commands that expose `/v1/chat/completions` OpenAI-compatible endpoints for this model.
- Local generated outputs, images, CSVs, and secrets must remain uncommitted.
- `radle_api_keys.env` may be used locally for secrets but secret values must never be printed.
- Local process environment and `radle_api_keys.env` did not contain `INTERNVL_BASE_URL` or `INTERNVL_API_KEY` when checked on 2026-06-18 20:15 +05:30.
- The default `python` on this Windows machine lacks `pandas`; use Colab, install benchmark dependencies, or use the bundled Codex Python runtime for local smoke execution.

## Do Not Revisit

- Do not merge InternVL into the official full-run roster during this task. See Decision Log 2026-06-18.
- Do not rewrite the benchmark architecture for this experiment. See Decision Log 2026-06-18.
- Do not use native OpenAI, Anthropic, or Gemini comparison calls for this task unless the user explicitly requests them. See Decision Log 2026-06-18.
- Do not commit generated smoke outputs or confidential images. See repository README and `.gitignore`.

## Progress

- [x] (2026-06-18 20:15 +05:30, Codex/GPT-5) Read required README and ExecPlan context supplied by the user at the start of the session.
- [x] (2026-06-18 20:15 +05:30, Codex/GPT-5) Re-read `~/.codex/PLANS.md` and the `execplan` skill before drafting this plan.
- [x] (2026-06-18 20:15 +05:30, Codex/GPT-5) Confirmed working tree status is clean on `main...origin/main`.
- [x] (2026-06-18 20:15 +05:30, Codex/GPT-5) Verified OpenRouter public model list currently has no `InternVL`, `OpenGVLab`, or lowercase `intern` match.
- [x] (2026-06-18 20:15 +05:30, Codex/GPT-5) Verified the Hugging Face model card for `OpenGVLab/InternVL3_5-8B` documents image-text-to-text plus OpenAI-compatible vLLM/SGLang serving.
- [x] (2026-06-18 20:22 +05:30, Codex/GPT-5) Added `scripts/internvl_experimental_probe.py` as a side-path runner with dry-run mode and OpenAI-compatible live endpoint mode.
- [x] (2026-06-18 20:22 +05:30, Codex/GPT-5) Validated `python -m py_compile src\radle_benchmark.py scripts\internvl_experimental_probe.py`, notebook JSON parse, `git diff --check`, and no diffs in the official source/notebook files.
- [x] (2026-06-18 20:22 +05:30, Codex/GPT-5) Ran a focused 1-case dry-run schema smoke using the bundled Codex Python runtime; output CSV read back with pandas.
- [x] (2026-06-18 20:22 +05:30, Codex/GPT-5) Confirmed no InternVL endpoint variables are currently configured locally, so live endpoint acceptance remains pending external endpoint setup.

## Surprises & Discoveries

- Observation: The current OpenRouter public model list still has no InternVL-style model entry, so OpenRouter cannot be used as the experimental path today.
  Evidence: `https://openrouter.ai/api/v1/models` was opened and searched for `InternVL`, `OpenGVLab`, and `intern`; there was no match.
  Date/Author: 2026-06-18 20:15 +05:30, Codex/GPT-5.
- Observation: The default local `python` cannot run the probe because it lacks `pandas`, although it can still perform `py_compile`.
  Evidence: `python scripts\internvl_experimental_probe.py --dry-run ...` exited with `ModuleNotFoundError: No module named 'pandas'`; the bundled Codex runtime completed the same smoke successfully.
  Date/Author: 2026-06-18 20:22 +05:30, Codex/GPT-5.

## Decision Log

- Decision: Keep the experiment outside `src/radle_benchmark.py` defaults and use a separate script plus an explicit model list.
  Rationale: The user explicitly wants the official run preserved and only an experimental side path evaluated.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Decision: Prefer an OpenAI-compatible hosted endpoint over direct local Transformers inference for the first implementation.
  Rationale: vLLM, SGLang, and Hugging Face endpoints can expose the same chat-completions interface already supported by the benchmark logic; direct local Transformers would require GPU-heavy dependencies and a separate image preprocessing path.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Decision: Stay on local `main` without committing or pushing unless the user asks.
  Rationale: The requested change is an experimental side path, the official run is already pushed, and the user has not requested a git handoff for this work.
  Date/Author: 2026-06-18, Codex/GPT-5.
- Decision: Treat the no-endpoint dry-run as schema validation only, not endpoint acceptance.
  Rationale: The user asked for actual image-input endpoint reachability; a fake client can prove local CSV plumbing but cannot prove hosted InternVL behavior.
  Date/Author: 2026-06-18, Codex/GPT-5.

## Revision Notes

- v2 (2026-06-18, Codex/GPT-5): Updated after implementation and validation; recorded script path, dry-run output, official-file no-diff check, and missing endpoint blocker.

## Outcomes & Retrospective

Implemented the experimental side path and completed local non-live validation. The official benchmark defaults were not modified. Live endpoint validation is pending because no InternVL OpenAI-compatible endpoint variables are configured locally. No reusable skill should be created; this is project-specific benchmark plumbing.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | Repo instructions require a durable plan for multi-step work. | `manual` |
| OpenRouter/HF verification | `none` | Direct public model metadata and model-card checks are sufficient. | `none` |
| Experimental script | `none` | This is ordinary Python script work around existing benchmark helpers. | `none` |
| Validation | `none` | Use `py_compile`, notebook JSON parse, focused local smoke, and diff checks. | `none` |

## Context And Orientation

`src/radle_benchmark.py` owns the official benchmark logic, including the default `MODELS` roster, RadLE prompt, OpenAI-style image message construction, response parsing, CSV schema, checkpoint saves, audit, and repair helpers. The Colab notebook `notebooks/RadLE_v1_5_Morning.ipynb` should remain a thin runner.

InternVL3.5 is not currently available through OpenRouter based on the public models list checked during this task. The Hugging Face model `OpenGVLab/InternVL3_5-8B` exists and can be served by vLLM or SGLang behind an OpenAI-compatible `/v1/chat/completions` API. Therefore this plan creates a side-path probe that accepts an explicit endpoint and model ID instead of adding InternVL to official defaults.

## Plan Of Work

Create `scripts/internvl_experimental_probe.py`. The script should:

- load optional secrets from `radle_api_keys.env` without printing values;
- verify OpenRouter model metadata for InternVL matches as an informational preflight;
- accept `--base-url`, `--api-key-env`, `--model-id`, `--image-folder`, `--output-csv`, and `--test-limit` arguments;
- default `--model-id` to `OpenGVLab/InternVL3_5-8B`, `--model-name` to `internvl3_5_8b`, `--test-limit` to `1`, and output under `local_smoke/`;
- instantiate an OpenAI-compatible client only when a base URL is supplied;
- reuse `radle_benchmark.run_benchmark` with `models=[{"name": model_name, "id": model_id, "extra": None}]`;
- print only paths, model IDs, counts, and non-secret status;
- read the resulting CSV back with pandas and validate that `Diagnosis_<model_name>`, `Likert_<model_name>`, and `Raw_Response_<model_name>` exist.

The script must not import or mutate the default `MODELS` roster, must not run native OpenAI/Anthropic/Gemini clients, and must write generated CSVs only under `local_smoke/` by default.

## Milestones

Milestone 1, using `execplan` for planning and `none` for implementation: create the separate script and ensure it compiles. At the end, `python -m py_compile scripts\internvl_experimental_probe.py src\radle_benchmark.py` should pass.

Milestone 2, using `none`: run a no-endpoint local dry-run or fake-client smoke under `local_smoke/` to prove the script writes a schema-shaped CSV and reads it back with pandas without contacting a paid service.

Milestone 3, using `none`: if `INTERNVL_BASE_URL` and the configured API key are present, run a 1-case live smoke. If that succeeds and cost/stability is acceptable, run 3-5 cases by setting `--test-limit 3` or `--test-limit 5`. If no endpoint is configured, report the live reachability acceptance criteria as blocked by missing endpoint rather than pretending it passed.

## Concrete Steps (Commands)

From repo root:

    python -m py_compile src\radle_benchmark.py scripts\internvl_experimental_probe.py

Expected: exits 0 with no output.

From repo root:

    python -c "import json, pathlib; json.loads(pathlib.Path('notebooks/RadLE_v1_5_Morning.ipynb').read_text(encoding='utf-8')); print('notebook JSON parse OK')"

Expected:

    notebook JSON parse OK

From repo root, no-endpoint validation:

    python scripts\internvl_experimental_probe.py --dry-run --image-folder local_smoke\images --test-limit 1

Expected: script writes a CSV under `local_smoke/`, reads it back, and prints that dry-run validation passed.

On this local Windows machine, use the bundled runtime because default `python` lacks `pandas`:

    C:\Users\thehb\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts\internvl_experimental_probe.py --dry-run --skip-openrouter-check --image-folder local_smoke\images --test-limit 1 --no-resume

From repo root, live 1-case endpoint validation after an endpoint is configured:

    python scripts\internvl_experimental_probe.py --base-url <OPENAI_COMPATIBLE_BASE_URL> --api-key-env INTERNVL_API_KEY --image-folder local_smoke\images --test-limit 1

Expected: endpoint call succeeds, output CSV reads back with pandas, and diagnosis/Likert/raw-response columns exist.

From repo root, live 3-5 case validation after the 1-case smoke passes:

    python scripts\internvl_experimental_probe.py --base-url <OPENAI_COMPATIBLE_BASE_URL> --api-key-env INTERNVL_API_KEY --image-folder local_smoke\images --test-limit 3

Expected: same as 1-case smoke, with 3 rows if 3 local case IDs exist.

## Validation And Acceptance

Acceptance for this task requires:

- OpenRouter availability is checked and the result is recorded.
- Official `src/radle_benchmark.py` default `MODELS` are unchanged.
- The experimental script compiles.
- The notebook JSON still parses.
- A focused local smoke writes under `local_smoke/` and reads back with pandas.
- `git diff --check` passes.
- If an InternVL endpoint is available, a 1-case live smoke proves it accepts image input and returns parseable RadLE JSON.
- If the endpoint is stable/cost-acceptable, a 3-5 case smoke also passes.
- If no endpoint is available, the final handoff clearly says live endpoint acceptance is not complete and gives the exact command to run once an endpoint is configured.

Actual validation transcript:

    python -m py_compile src\radle_benchmark.py scripts\internvl_experimental_probe.py
    # exited 0

    python -c "import json, pathlib; json.loads(pathlib.Path('notebooks/RadLE_v1_5_Morning.ipynb').read_text(encoding='utf-8')); print('notebook JSON parse OK')"
    notebook JSON parse OK

    git diff --check
    # exited 0

    git diff -- src\radle_benchmark.py notebooks\RadLE_v1_5_Morning.ipynb
    # no output

    C:\Users\thehb\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts\internvl_experimental_probe.py --dry-run --skip-openrouter-check --image-folder local_smoke\images --test-limit 1 --no-resume
    Output CSV read-back OK with pandas: rows=1

Dry-run artifact:

    local_smoke/internvl3_5_8b_probe_20260618_202234.csv
    local_smoke/internvl3_5_8b_probe_20260618_202234_BACKUP.csv
    local_smoke/internvl3_5_8b_probe_20260618_202234_BACKUP_0001.csv

## Idempotence And Recovery

The script should be safe to rerun because every output path defaults to a timestamped CSV under `local_smoke/`. If a live run partially fails, rerun with a fresh output path or `--resume false` if the script exposes that option. Generated smoke CSVs and backups are ignored by `.gitignore` and must not be staged.

If the endpoint returns HTTP 404 or model unavailable, do not change official defaults. Record the endpoint/model mismatch and rerun only after the hosted service is corrected.

## Artifacts And Notes

OpenRouter check:

    Source: https://openrouter.ai/api/v1/models
    Search terms: InternVL, OpenGVLab, intern
    Result: no matching text found for intern-style model names.

Hugging Face check:

    Source: https://huggingface.co/OpenGVLab/InternVL3_5-8B
    Relevant facts: task label image-text-to-text; vLLM and SGLang examples call /v1/chat/completions with image_url content.

## Interfaces And Dependencies

The experimental script depends on:

- Python standard library: `argparse`, `datetime`, `json`, `os`, `pathlib`, `sys`, `urllib.request`.
- Existing project module: `src/radle_benchmark.py`.
- Existing project dependencies already needed by the benchmark: `pandas` and `openai` for live endpoint calls.
- Optional local secret file: `radle_api_keys.env`, parsed only for environment variables and never printed.
