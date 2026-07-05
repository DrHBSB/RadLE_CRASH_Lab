# Add Grok 4.3 MiniMax M3 GLM5V Morning Smoke Notebook

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` or applicable root `AGENTS.md` was found; the user-provided AGENTS instruction requires ExecPlans for complex multi-step work.

## Purpose / Big Picture

Create a Colab smoke notebook copied from `notebooks/RadLE_v1_5_Morning.ipynb` that runs only three OpenRouter models for five cases: `grok_4_3`, `minimax_m3`, and `glm_5v_turbo`. The benchmark implementation remains stable; only the model registry and the copied smoke notebook are changed and committed.

## Current State

Current state (2026-07-02 10:36 +05:30, Codex/GPT-5): The smoke notebook and registry entries were validated, committed as `5546c8e`, and pushed to `origin/codex/llava-vllm-runtime`. This ExecPlan file remains unstaged because the user requested staging only `src/radle_benchmark.py` and the new notebook. Next: run the pushed notebook in Colab if runtime smoke evidence is needed.

## Locked Facts

- `src/radle_benchmark.py` is the model registry source of truth.
- `grok_4_20` must remain as `x-ai/grok-4.20`.
- `glm_5v_turbo` must remain `z-ai/glm-5v-turbo` with `extra` reasoning enabled.
- Commit scope is limited to `src/radle_benchmark.py` and the new notebook.
- Commit `5546c8e` on `codex/llava-vllm-runtime` contains the requested registry and notebook changes.

## Do Not Revisit

- Do not change prompt, image payload construction, audit, repair, scoring, or provider-client code for this smoke notebook. See Decision Log 2026-07-02.
- Do not create a new branch unless the current branch is not `codex/llava-vllm-runtime`. See Decision Log 2026-07-02.

## Progress

- [x] (2026-07-02 10:31 +05:30, Codex/GPT-5) Verified current branch and dirty-file boundary.
- [x] (2026-07-02 10:32 +05:30, Codex/GPT-5) Add `grok_4_3` and `minimax_m3` registry entries.
- [x] (2026-07-02 10:33 +05:30, Codex/GPT-5) Copy and surgically edit `notebooks/RadLE_v1_5_Morning_Grok43_MiniMaxM3_GLM5V_5case.ipynb`.
- [x] (2026-07-02 10:34 +05:30, Codex/GPT-5) Run requested validation commands.
- [x] (2026-07-02 10:36 +05:30, Codex/GPT-5) Stage only the requested files, commit, and push.

## Surprises & Discoveries

- None yet.

## Decision Log

- Decision: Stay on `codex/llava-vllm-runtime` instead of creating a child branch.
  Rationale: The repo is already on the requested push branch and the user explicitly requested pushing this branch.
  Date/Author: 2026-07-02, Codex/GPT-5
- Decision: Keep implementation scoped to model entries and the copied notebook.
  Rationale: The user explicitly prohibited benchmark prompt, payload, audit, repair, scoring, and client-code changes unless strictly required.
  Date/Author: 2026-07-02, Codex/GPT-5

## Revision Notes

- v1 (2026-07-02, Codex/GPT-5): Initial plan created before edits.

## Outcomes & Retrospective

Completed in commit `5546c8e`, pushed to `origin/codex/llava-vllm-runtime`. Validation passed for `py_compile`, notebook JSON parsing, registry membership, and `build_api_params` model-id / GLM reasoning assertions. No reusable skill lesson needs promotion.

## Suggested Skills By Phase

| Phase / Milestone | Recommended Skill(s) | Why This Helps | Activation Mode |
| --- | --- | --- | --- |
| Planning | `execplan` | Required by user-provided AGENTS instruction for multi-step work. | `auto-suggest` |
| Implementation | `none` | Direct Python/JSON edits are sufficient. | `none` |
| Validation | `none` | Requested checks are local Python/git commands. | `none` |
| Git publication | `none` | Direct `git add`, `git commit`, and `git push` are sufficient. | `none` |

## Context And Orientation

`notebooks/RadLE_v1_5_Morning.ipynb` is a Colab orchestration notebook over `src/radle_benchmark.py`. The new smoke notebook must preserve the Morning workflow but set `TEST_LIMIT = 5`, a smoke-specific `RUN_LABEL`, and `DEBUG_MODEL_NAMES` to the three requested OpenRouter model names. The repaired Fable notebook pattern shows how to pin Colab setup to `REPO_REF = "codex/llava-vllm-runtime"` and print the checked-out branch plus commit.

## Plan Of Work

Add two OpenRouter registry entries in `src/radle_benchmark.py`: `grok_4_3` with id `x-ai/grok-4.3` and `extra` set to `None`, and `minimax_m3` with id `minimax/minimax-m3` and `extra` set to `None`. Keep `glm_5v_turbo` unchanged.

Create `notebooks/RadLE_v1_5_Morning_Grok43_MiniMaxM3_GLM5V_5case.ipynb` from the current working copy of `notebooks/RadLE_v1_5_Morning.ipynb`, then modify only the setup/config/audit lines needed by the user request.

## Concrete Steps (Commands)

From the repo root:

    py -3.11 -m py_compile src/radle_benchmark.py
    py -3.11 -c "<parse notebook and model assertions>"
    git diff -- src/radle_benchmark.py notebooks/RadLE_v1_5_Morning_Grok43_MiniMaxM3_GLM5V_5case.ipynb
    git add src/radle_benchmark.py notebooks/RadLE_v1_5_Morning_Grok43_MiniMaxM3_GLM5V_5case.ipynb
    git commit -m "Add Grok 4.3 MiniMax M3 GLM5V Morning smoke notebook"
    git push origin codex/llava-vllm-runtime

## Validation And Acceptance

Success requires `py_compile` to pass, the new notebook JSON to parse, all three model names to exist in `radle_benchmark.MODELS`, request params to map to the exact OpenRouter ids, and `glm_5v_turbo` to build `extra_body.reasoning.enabled == True`.

## Idempotence And Recovery

The notebook copy can be regenerated from `notebooks/RadLE_v1_5_Morning.ipynb` if local editing fails. If validation fails after registry edits, inspect only `src/radle_benchmark.py` and the copied notebook; do not repair unrelated dirty files.

## Artifacts And Notes

- `py -3.11 -m py_compile src/radle_benchmark.py` completed with exit code 0.
- Notebook parse check printed `notebook_json_ok ... cells 9`.
- Model request assertion check printed ids for `grok_4_3`, `minimax_m3`, and `glm_5v_turbo`.
- `git diff --cached --check` completed with exit code 0.

## Interfaces And Dependencies

The only code interface used for validation is `radle_benchmark.build_api_params(model, content_array, max_output_tokens, universal_temperature)`.
