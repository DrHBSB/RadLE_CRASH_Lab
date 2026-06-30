# Coordinate LLaVA-vLLM Workbench GUI Execution From Codex App

## Objective

Run the Codex app side of a two-goal workflow for `Documents/execplan_llava_vllm_runtime.md`. This goal is the PM/coordinator and evidence reviewer. It drives the work by producing exact copy-paste packets for the Antigravity Codex extension goal, asking the user to perform GUI notebook actions in Antigravity when needed, and reviewing pasted outputs, screenshots, errors, commits, or PR links before deciding the next step.

The paired Antigravity editing goal is:

`docs/goals/llava-vllm-antigravity-extension/goal.md`

## Original Request

`$goal-prep C:/Users/thehb/Documents/RadLE v2/Documents/execplan_llava_vllm_runtime.md`, later corrected by the user to require two goals: one here in the Codex app as coordinator, and one in Antigravity's Codex extension as the editor/pusher.

## Intake Summary

- Input shape: `existing_plan`
- Audience: the RadLE medical Workbench experiment owner
- Authority: `requested`
- Proof type: `artifact`
- Completion proof: a final Judge/PM audit maps paired-goal receipts to a completed `llava_med_mistral_7b_medical_full_200_cases` run, including Antigravity-side edit/push evidence, GUI-visible notebook execution evidence, valid audit integrity, guarded promotion, answer-free public exports, runtime provenance, and synced run bundle.
- Goal oracle: the coordinated two-goal loop proves the LLaVA-vLLM route by combining Antigravity Codex edit/push receipts with user-pasted GUI notebook outputs from Antigravity.
- Likely misfire: treating this Codex app as if it can directly control Antigravity/Jupyter/Workbench, or treating the Antigravity Codex extension as if it can restart kernels, run cells, or inspect live notebook output.
- Blind spots considered: the working Jupyter and Workbench extensions live inside Antigravity; terminal/CLI notebook execution has already been tried and should not be the planned path; Antigravity Codex can edit and push but cannot provide live kernel/output evidence; this Codex app must act through copy-paste prompts and user-returned GUI evidence.
- Existing plan facts: preserve `Documents/execplan_llava_vllm_runtime.md`; the parent SSOT `Documents/execplan_medical_workbench_runtime.md` points to that child plan as authoritative; target `chaoyinshe/llava-med-v1.5-mistral-7b-hf`; target notebook `notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb`; keep `name="llava_med_mistral_7b"` and `RUN_ID=llava_med_mistral_7b_medical_full_200_cases`; use vLLM with `--limit-mm-per-prompt {"image": 5}` and `MODEL_DTYPE="float16"` unless vLLM refuses with recorded evidence; keep the standard RadLE prompt and OpenAI-style base64 image payload; do not add text-only controls, image-perturbation controls, SGLang shims, sitecustomize hacks, or chat-template hacks.

## Goal Oracle

The oracle for this goal is:

`The Codex app coordinator can show a receipt chain from paired Antigravity edit/push work plus user-pasted Antigravity GUI notebook evidence proving the LLaVA-vLLM Workbench path produced and audited the model-scoped full RadLE medical run for llava_med_mistral_7b_medical_full_200_cases, with checkpoint/runtime evidence, notebook validation, non-writing clinical JSON smoke evidence, 200-case audit integrity, guarded promotion or explicit owner override, answer-free public release tables, runtime provenance, and synced run bundle.`

The PM must keep comparing task receipts to this oracle. Planning, a pushed notebook, server readiness alone, token-count growth, or unreviewed pasted output is not enough. The goal finishes only when a final Judge/PM audit maps paired-goal receipts and GUI evidence back to this oracle and records `full_outcome_complete: true`.

## Goal Kind

`existing_plan`

## Current Tranche

Coordinate the provided ExecPlan through the first complete LLaVA-vLLM Workbench full run. This Codex app goal does not directly edit notebook/runtime implementation and does not drive notebook execution by CLI. It generates precise instructions for the Antigravity Codex extension goal and for the user's Antigravity GUI actions, then reviews the returned evidence and decides the next packet.

## Two-Goal Operating Model

- Goal A, this board: `docs/goals/llava-vllm-runtime/goal.md`
  - Runs in the Codex app.
  - Acts as PM, reviewer, and copy-paste bridge.
  - Produces exact prompts/instructions for the Antigravity Codex extension goal.
  - Asks the user to run GUI-only notebook actions in Antigravity when needed.
  - Reviews pasted Antigravity outputs, visible errors, screenshots, commit links, PR links, manifests, and notebook results.

- Goal B, paired editor board: `docs/goals/llava-vllm-antigravity-extension/goal.md`
  - Runs in the Antigravity Codex extension.
  - Edits repo/notebook files and pushes changes to GitHub.
  - Cannot restart kernels, execute notebook cells, or inspect live notebook outputs.
  - Must not claim runtime success from static edits alone.
  - Returns edit/push receipts to this Codex app goal through the user.

## Claude Handoff Facts To Preserve

The user supplied a Claude/Opus handoff that is already reflected in the active child ExecPlan and parent SSOT. Treat these as takeover facts for the coordinator loop:

- `Documents/execplan_llava_vllm_runtime.md` is the active LLaVA task and should begin at Milestone 1.
- `Documents/execplan_medical_workbench_runtime.md` is the parent SSOT and points to the child plan as the authoritative runbook for this pivot.
- SGLang is abandoned from live Workbench HEAD `080ec65` evidence, not because of speculation.
- The SGLang server came up; all shims applied; the canonically-correct Mistral template loaded; image tokens were inserted.
- Exact failure signature: prompt tokens `371 -> 949`, exactly `576` visual tokens; short prompt `24 -> 600`; probe A/B/C empty; probe D returned `image> `.
- The probe/smoke outputs were throwaway and not committed; the SGLang notebook is unchanged at `080ec65`.
- Section 6.5 for the vLLM notebook must hard-fail on empty output, 1-token EOS, `<image>` placeholder echo, and prompt echo. It must require a real clinical JSON diagnosis.
- The original `microsoft/llava-med-v1.5-mistral-7b` is original LLaVA weight layout, not HF `LlavaForConditionalGeneration`; vLLM needs an HF-format checkpoint, not config relabeling.
- Preferred path: verify and use `chaoyinshe/llava-med-v1.5-mistral-7b-hf`.
- Fallback path only after recorded failure: convert the original checkpoint with Transformers `convert_llava_weights_to_hf.py`.

## Non-Negotiable Constraints

- Maintain two separate goals: Codex app coordinator/reviewer here, Antigravity Codex extension editor/pusher in the paired goal.
- Antigravity Codex extension may edit files and push to GitHub, but must not be treated as able to restart kernels, execute cells, or see notebook outputs.
- Notebook kernel restarts, cell execution, Workbench/Jupyter extension behavior, and output inspection happen through the Antigravity GUI with user-pasted evidence back to this goal.
- Do not plan around terminal/CLI notebook execution, because the working Jupyter/Workbench extension path is Antigravity GUI.
- CLI checks in this goal are allowed only for GoalBuddy board health or narrow static repo inspection; they are not proof of notebook runtime success.
- Keep the official RadLE benchmark path stable; isolate this work to the medical Workbench LLaVA-vLLM route.
- Do not touch OctoMed or InternVL notebooks for this goal.
- Do not resume SGLang without explicit new user direction.
- Do not use the original Microsoft checkpoint through vLLM by relabeling alone.
- Do not start checkpoint conversion unless the preferred HF checkpoint path fails with recorded evidence and the coordinator explicitly approves fallback work.
- Do not add text-only controls, image-perturbation controls, or extra experimental arms.
- Do not treat server readiness, token-count growth, blank output, `<image>` echo, prompt echo, or `"I don't know"` as smoke success.
- Do not promote or sync full-run outputs while audit integrity problems or repair targets remain unless the user explicitly overrides.

## Stop Rule

Stop only when a final audit proves the full original outcome is complete.

Do not stop after sending one prompt to Antigravity if safe local coordination can continue. Do not stop after one pushed edit if GUI evidence still has to be collected. If Antigravity GUI access, GPU/Workbench access, GCS credentials, or owner approval blocks a slice, mark that exact task blocked with a receipt and continue any safe coordination, evidence review, or next-packet preparation that can still move the goal.

## Slice Sizing

Safe means bounded, explicit, verified, and reversible. It does not mean tiny.

A good coordinator package here is a complete Antigravity edit packet, a complete pasted-evidence review, a GUI smoke/full-run instruction packet, or a final paired-goal audit. Avoid one task per cell unless the failure is isolated and blocking.

## Board Health

The PM owns board health. If the board looks stale, misleading, offline, or inconsistent, run:

```bash
node C:/Users/thehb/.agents/skills/goalbuddy/scripts/check-goal-state.mjs docs/goals/llava-vllm-runtime/state.yaml
```

If the local board is running, compare `state.yaml` to the live board API. Repair only GoalBuddy control files unless an active Worker or PM task explicitly allows product-file edits.

## Canonical Board

Machine truth lives at:

`docs/goals/llava-vllm-runtime/state.yaml`

If this charter and `state.yaml` disagree, `state.yaml` wins for task status, active task, receipts, verification freshness, and completion truth.

## Run Command

```text
/goal Follow docs/goals/llava-vllm-runtime/goal.md.
```

## PM Loop

On every `/goal` continuation:

1. Read this charter.
2. Read `state.yaml`.
3. Read the paired Antigravity goal charter when a handoff packet or returned receipt is involved.
4. Run the bundled GoalBuddy update checker when available and mention a newer version without blocking.
5. Work only on the active board task.
6. If an edit is needed, produce an exact copy-paste packet for the Antigravity Codex extension goal.
7. If notebook execution evidence is needed, give the user exact GUI actions to perform in Antigravity and ask for specific pasted outputs or screenshots.
8. Review returned evidence before deciding the next packet.
9. Write a compact receipt and update this board.
10. Finish only with a Judge/PM audit receipt that maps paired-goal edit/push receipts and GUI evidence back to the original user outcome and records `full_outcome_complete: true`.
