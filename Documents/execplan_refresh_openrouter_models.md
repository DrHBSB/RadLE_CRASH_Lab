# Refresh OpenRouter Vision Model Defaults

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. The repo has no repo-local `PLANS.md`; the prompt-provided `AGENTS.md` instruction requires repo-local ExecPlans for complex or multi-step work and prefers `Documents/`.

## Purpose / Big Picture

The benchmark roster still contains stale OpenRouter vision model IDs: `qwen/qwen-vl-max` and `mistralai/pixtral-large-2411`. In the user's Colab `TEST_LIMIT=1` run on 2026-06-18, both returned HTTP 404 "No endpoints found", wasting paid benchmark slots and weakening the methodology. This work will replace those defaults with current, image-capable, live-tested OpenRouter models so Qwen and Mistral/Pixtral-side families are represented by defensible current models when compared against Gemini and Claude Opus.

## Current State

Current state (2026-06-18 19:03 +05:30, Codex/GPT-5): README and prior ExecPlans were reviewed. `radle_api_keys.env` is the local secret source, ignored by git. Live OpenRouter metadata, tiny image endpoint probes, and repo-path `run_benchmark` smokes have been run for candidate Qwen and Mistral models. `src/radle_benchmark.py` now points Qwen to `qwen/qwen3.7-plus` and the Mistral/Pixtral-side slot to `mistralai/mistral-large-2512`. The OpenRouter-only roster smoke passed across seven routed models with pandas `PerformanceWarning` promoted to an error. Next: rerun final compile/notebook/diff checks, then wait for explicit commit/push instruction if the user wants the staged change published.

## Locked Facts

- `README.md` says Colab is the execution environment; GitHub stores notebook/code, and Google Drive stores confidential images/full result CSVs.
- `radle_api_keys.env` is ignored by `.gitignore`; it may be read locally for API keys, but secret values must never be printed or committed.
- Prior validation plans use ignored `local_smoke/` outputs for local paid and no-API tests.
- The local smoke image is `local_smoke/openrouter_paid_smoke_images/1.jpg`; `local_smoke/images/55.2.jpg` also exists.
- The user explicitly approved paid local OpenRouter testing for candidate model selection in this thread.
- Current stale defaults are `qwen_vl_max` / `qwen/qwen-vl-max` and `pixtral_large` / `mistralai/pixtral-large-2411`.
- Live candidate endpoint probes on 2026-06-18 succeeded for `qwen/qwen3.7-plus`, `qwen/qwen3.6-plus`, `qwen/qwen3.5-plus-20260420`, `qwen/qwen2.5-vl-72b-instruct`, `mistralai/mistral-large-2512`, `mistralai/mistral-medium-3-5`, `mistralai/mistral-small-2603`, and `mistralai/mistral-small-3.2-24b-instruct`.
- In the tiny red PNG probe, `mistralai/mistral-small-2603` answered `white`; the others answered `red`.
- No current `pixtral` model ID appeared in the live OpenRouter candidate metadata search; current Mistral multimodal models are the practical replacement family.
- Repo-path `run_benchmark` selected-pair smoke on 2026-06-18 wrote `local_smoke/openrouter_candidate_roster_smoke_20260618_183354.csv`: `qwen/qwen3.7-plus` routed to `qwen/qwen3.7-plus-20260602` and returned `Multinodular goiter`; `mistralai/mistral-medium-3-5` routed to `mistralai/mistral-medium-3.5-20260430` and returned valid `I don't know`.
- Repo-path comparison smoke on 2026-06-18 wrote `local_smoke/openrouter_candidate_compare_smoke_20260618_183711.csv`: all five compared candidates returned syntactically valid benchmark rows; `ministral-14b-2512` returned a non-abstention diagnosis but is not selected because it is a smaller Ministral model, not the strongest Mistral multimodal model.
- Repo-path Mistral Large smoke on 2026-06-18 wrote `local_smoke/openrouter_mistral_large_2512_smoke_20260618_184824.csv`: `mistralai/mistral-large-2512` routed to itself and returned `Bilateral orbital fractures involving the medial and inferior orbital walls` with Likert 3.
- Google Drive connector could read `RadLE v2 Master Data` folder metadata but could not enumerate image children by parent ID; local Windows has no Google Drive filesystem mount. Broader 3-5 real-image validation should be done in Colab where Drive is mounted.
- Validation on 2026-06-18 passed: `python -m py_compile src\radle_benchmark.py`, notebook JSON parse with `outputs 0` and `executed 0`, `git diff --check`, and a notebook-source comparison against `HEAD` showing `cell_sources_unchanged True`.
- While fixing OpenRouter issues, do not use native OpenAI, Anthropic, or Gemini APIs again in this task. OpenRouter-only validation should pass `models=[m for m in MODELS if "provider" not in m]` or an equivalent explicit list.
- OpenRouter-only roster smoke on 2026-06-18 wrote `local_smoke/openrouter_only_roster_smoke_20260618_185955.csv`; all seven OpenRouter-routed default models returned usable rows and no pandas `PerformanceWarning` occurred.

## Do Not Revisit

- Do not restore old OpenRouter-only routing for native GPT, Claude, or Gemini models. See `Documents/execplan_json_audit_repair_implementation.md` Decision Log 2026-06-18 01:17 +05:30.
- Do not commit `radle_api_keys.env`, local smoke CSVs, images, or any generated benchmark output. See `.gitignore` and README.
- Do not choose text-only Qwen or Mistral models for this image benchmark, even if their names look newer.
- Do not keep methodologically misleading model names such as `pixtral_large` if the replacement ID is a Mistral model rather than Pixtral.

## Progress

- [x] (2026-06-18 18:32 +05:30, Codex/GPT-5) Read README, requirements note, and existing ExecPlans for testing conventions.
- [x] (2026-06-18 18:32 +05:30, Codex/GPT-5) Confirmed `radle_api_keys.env` contains `TEST_OPENROUTER_API_KEY` by reporting only variable presence and length.
- [x] (2026-06-18 18:32 +05:30, Codex/GPT-5) Queried OpenRouter live model metadata for Qwen and Mistral image-capable candidates.
- [x] (2026-06-18 18:32 +05:30, Codex/GPT-5) Ran tiny paid image endpoint probes for seven candidate IDs.
- [x] (2026-06-18 18:40 +05:30, Codex/GPT-5) Ran repo-path `run_benchmark` smoke on selected Qwen and Mistral candidates using `local_smoke/openrouter_paid_smoke_images`; output `local_smoke/openrouter_candidate_roster_smoke_20260618_183354.csv`.
- [x] (2026-06-18 18:40 +05:30, Codex/GPT-5) Ran repo-path comparison smoke for older Qwen VL and Mistral alternatives; output `local_smoke/openrouter_candidate_compare_smoke_20260618_183711.csv`.
- [x] (2026-06-18 18:40 +05:30, Codex/GPT-5) Patched `src/radle_benchmark.py` model defaults.
- [x] (2026-06-18 18:45 +05:30, Codex/GPT-5) Cleared stale notebook outputs that contained old `qwen_vl_max` and `pixtral_large` 404 logs.
- [x] (2026-06-18 18:48 +05:30, Codex/GPT-5) Validated compile, notebook JSON, whitespace, stale active references, and notebook source preservation for the first Medium candidate patch.
- [x] (2026-06-18 18:52 +05:30, Codex/GPT-5) Re-checked live OpenRouter Mistral image-capable models after user challenged Medium; found and tested `mistralai/mistral-large-2512`, then patched source to Large.
- [x] (2026-06-18 19:03 +05:30, Codex/GPT-5) Ran OpenRouter-only roster validation without native OpenAI/Anthropic/Gemini API clients; all seven routed models returned usable rows.
- [ ] (2026-06-18 18:32 +05:30, Codex/GPT-5) Commit and push to `origin/main`.

## Surprises & Discoveries

- Observation: `TEST_OPENROUTER_API_KEY` was not in the inherited process/User/Machine environment, but was present in repo-local `radle_api_keys.env`.
  Evidence: PowerShell env checks reported missing, then parsing `radle_api_keys.env` reported `TEST_OPENROUTER_API_KEY present length=73` without printing the value.
  Date/Author: 2026-06-18 18:32 +05:30, Codex/GPT-5.
- Observation: Live endpoint probes show `qwen/qwen3.7-plus` and `mistralai/mistral-medium-3-5` accept image requests and return correct color recognition responses.
  Evidence: probe output included `OK qwen/qwen3.7-plus routed=qwen/qwen3.7-plus-20260602 answer='red'` and `OK mistralai/mistral-medium-3-5 routed=mistralai/mistral-medium-3.5-20260430 answer='red'`.
  Date/Author: 2026-06-18 18:32 +05:30, Codex/GPT-5.
- Observation: Qwen 3.7 Plus can be much slower and more token-heavy than the older explicit Qwen VL model on the local radiology smoke image.
  Evidence: selected-pair smoke printed `qwen_3_7_plus... OK (141.6s | 7591 out / 1403 in)` while the comparison smoke printed `qwen2_5_vl_72b... OK (11.4s | 22 out / 1705 in)`.
  Date/Author: 2026-06-18 18:40 +05:30, Codex/GPT-5.
- Observation: Mistral Medium 3.5 abstained on the local radiology smoke image, while smaller `ministral-14b-2512` returned a diagnosis.
  Evidence: selected-pair smoke validated `Diagnosis_mistral_medium_3_5="I don't know"`; comparison smoke printed `ministral_3_14b_2512 diagnosis='Acute appendicitis with periappendiceal abscess formation'`.
  Date/Author: 2026-06-18 18:40 +05:30, Codex/GPT-5.
- Observation: User correctly challenged the Medium choice because live OpenRouter lists a higher-tier Mistral Large 3 model with image input.
  Evidence: live metadata output listed `mistralai/mistral-large-2512` as `Mistral: Mistral Large 3 2512`, `text+image+file->text`; tiny image probe answered `red`; repo-path smoke returned a valid radiology diagnosis.
  Date/Author: 2026-06-18 18:52 +05:30, Codex/GPT-5.
- Observation: A full default-roster smoke was run before the user clarified not to use the native big-three APIs during OpenRouter fixes.
  Evidence: `local_smoke/full_default_roster_smoke_20260618_185425.csv` was created and all ten model slots validated, but this should not be repeated in this task.
  Date/Author: 2026-06-18 19:00 +05:30, Codex/GPT-5.
- Observation: The pandas fragmentation warning is resolved for the normal benchmark path.
  Evidence: OpenRouter-only roster smoke promoted `pd.errors.PerformanceWarning` to an exception and still completed with `OPENROUTER_ONLY_ROSTER_SMOKE_OK`.
  Date/Author: 2026-06-18 19:03 +05:30, Codex/GPT-5.
- Observation: Local 3-5 real-image testing from Drive was not possible through the current tools.
  Evidence: Drive connector returned folder metadata for `RadLE v2 Master Data`, but parent-ID searches returned no image children; `Get-PSDrive` showed only `C:` and no local Google Drive mount.
  Date/Author: 2026-06-18 18:45 +05:30, Codex/GPT-5.

## Decision Log

- Decision: Use `qwen/qwen3.7-plus` as the leading Qwen candidate unless the repo-path smoke fails.
  Rationale: It is current, image-capable, routed successfully, and answered the image probe correctly. It is newer than `qwen/qwen2.5-vl-72b-instruct`.
  Date/Author: 2026-06-18 18:32 +05:30, Codex/GPT-5.
- Decision: Use `mistralai/mistral-large-2512` as the Mistral/Pixtral-side replacement.
  Rationale: The old Pixtral ID is unavailable and no live Pixtral IDs were found. OpenRouter's live metadata lists `mistralai/mistral-large-2512` as image-capable and it passed both tiny image and repo-path benchmark smokes. It is a fairer highest-tier Mistral replacement than Medium 3.5.
  Date/Author: 2026-06-18 18:52 +05:30, Codex/GPT-5.
- Decision: Rename model keys to match the replacement families (`qwen_3_7_plus`, `mistral_large_3_2512`) instead of preserving stale labels.
  Rationale: Output column names should not imply old or unavailable model families.
  Date/Author: 2026-06-18 18:32 +05:30, Codex/GPT-5.
- Decision: Stay on local `main` and push directly after validation.
  Rationale: The repo's recent workflow has used direct `main` pushes for these private benchmark runner fixes, and the user explicitly asked to push changes.
  Date/Author: 2026-06-18 18:32 +05:30, Codex/GPT-5.
- Decision: From this point forward, validate only OpenRouter-routed models for this task.
  Rationale: The task is fixing OpenRouter model IDs, and the user explicitly said not to use the big-three native APIs while doing so.
  Date/Author: 2026-06-18 19:00 +05:30, Codex/GPT-5.
- Decision: Do not commit/push until the user explicitly approves after reviewing the final staged model changes.
  Rationale: The user explicitly asked for a pre-commit explanation and continued to refine model choices.
  Date/Author: 2026-06-18 19:03 +05:30, Codex/GPT-5.

## Revision Notes

- v7 (2026-06-18 19:03 +05:30, Codex/GPT-5): Recorded successful OpenRouter-only roster validation, pandas warning fix, and the decision to wait for explicit commit approval.

## Outcomes & Retrospective

In progress. Candidate probing, corrected Large source patch, notebook output clearing, pandas warning fix, and OpenRouter-only roster validation are complete. Remaining work is final non-API validation and user-approved commit/push.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | Repo instructions require durable planning for multi-step methodology changes. | `manual` |
| Candidate API probes | `none` | Direct OpenRouter HTTP calls and repo Python are sufficient. | `none` |
| Module edit | `none` | Direct Python constant edit in `src/radle_benchmark.py`. | `none` |
| Validation | `none` | Compile, notebook JSON parse, and local smoke CSV checks match prior repo practice. | `none` |

## Context And Orientation

`src/radle_benchmark.py` defines the default `MODELS` list used by the Colab notebook and audit/repair workflows. `notebooks/RadLE_v1_5_Morning.ipynb` imports `radle_benchmark.MODELS` into `ACTIVE_MODELS` unless `DEBUG_MODEL_NAMES` is set. Changing model `name` values changes CSV column prefixes for new runs, which is appropriate here because the old names point to unavailable or misleading models.

OpenRouter model metadata can say a model accepts images, but the benchmark needs live proof that the endpoint accepts the same OpenAI-style image payload. Therefore validation must include real chat completion calls with `image_url` content, not only metadata.

## Plan Of Work

First, run a focused `run_benchmark` smoke using `local_smoke/openrouter_paid_smoke_images/1.jpg`, `TEST_OPENROUTER_API_KEY` from `radle_api_keys.env`, and only the two selected OpenRouter candidates. The smoke should write an ignored CSV under `local_smoke/`, return non-error diagnoses for both model slots, and produce a reloadable CSV.

Second, patch `src/radle_benchmark.py` so the old Qwen and Pixtral entries become:

- `name`: `qwen_3_7_plus`, `id`: `qwen/qwen3.7-plus`, `extra`: `None`
- `name`: `mistral_large_3_2512`, `id`: `mistralai/mistral-large-2512`, `extra`: `None`

Third, validate with:

    python -m py_compile src\radle_benchmark.py
    python -c "import json, pathlib; json.loads(pathlib.Path('notebooks/RadLE_v1_5_Morning.ipynb').read_text(encoding='utf-8')); print('notebook JSON parse OK')"
    git diff --check

Finally, stage only the plan and source file, commit, push, and report the tested IDs and outputs.

## Validation And Acceptance

Acceptance requires:

- Live OpenRouter endpoint proof for candidate replacements using image input.
- Repo-path `run_benchmark` proof for the selected replacements, not only standalone HTTP proof.
- `py_compile` passes.
- notebook JSON parse passes.
- `git diff --check` passes for the working tree.
- `git status --short --branch` is clean and synced after push.

Expected smoke behavior:

- `run_benchmark` prints `Processing 1 unique cases across 2 models`.
- Both selected model rows print `OK`.
- The smoke CSV contains `Diagnosis_qwen_3_7_plus` and `Diagnosis_mistral_large_3_2512` after the source patch, or candidate-equivalent names before the patch.

## Idempotence And Recovery

The endpoint probes are paid calls and should not be repeated unless needed. The `local_smoke/` output files are ignored and may be overwritten or left in place. If a chosen candidate fails the repo-path smoke, do not patch defaults to that candidate; instead select the next best already-probed image-capable candidate and record the failure in `Surprises & Discoveries`.

If git push is rejected because remote `main` advanced, fetch, inspect divergence, rebase local commits onto `origin/main`, rerun validation, and push again.

## Artifacts And Notes

Tiny endpoint probe transcript:

    OK qwen/qwen3.7-plus routed=qwen/qwen3.7-plus-20260602 answer='red'
    OK qwen/qwen3.6-plus routed=qwen/qwen3.6-plus-04-02 answer='red'
    OK qwen/qwen3.5-plus-20260420 routed=qwen/qwen3.5-plus-20260420 answer='red'
    OK qwen/qwen2.5-vl-72b-instruct routed=qwen/qwen2.5-vl-72b-instruct answer='red'
    OK mistralai/mistral-medium-3-5 routed=mistralai/mistral-medium-3.5-20260430 answer='red'
    OK mistralai/mistral-large-2512 routed=mistralai/mistral-large-2512 answer='red'
    OK mistralai/mistral-small-2603 routed=mistralai/mistral-small-2603 answer='white'
    OK mistralai/mistral-small-3.2-24b-instruct routed=mistralai/mistral-small-3.2-24b-instruct-2506 answer='red'

## Interfaces And Dependencies

No new runtime dependency is planned. Local paid tests use Python standard library HTTP or the existing `openai` package if available, plus `pandas` already used by `src/radle_benchmark.py`. The Colab notebook continues to instantiate `openrouter_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["TEST_OPENROUTER_API_KEY"])`.
