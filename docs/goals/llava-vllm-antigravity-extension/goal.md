# Antigravity Codex Extension Edits For LLaVA-vLLM Workbench

## Objective

Run the Antigravity Codex extension side of the LLaVA-vLLM Workbench workflow. This goal edits repo/notebook files and pushes changes to GitHub when instructed by the Codex app coordinator goal. It does not restart kernels, execute notebook cells, or inspect live notebook outputs.

The paired Codex app coordinator goal is:

`docs/goals/llava-vllm-runtime/goal.md`

## Original Request

The user clarified that two goals are required: this Antigravity-side goal for editing and pushing files, and the Codex app goal for coordinating GUI evidence through copy-paste.

## Intake Summary

- Input shape: `existing_plan`
- Audience: the RadLE medical Workbench experiment owner
- Authority: `requested`
- Proof type: `artifact`
- Completion proof: Antigravity Codex returns specific edit/push receipts that the Codex app coordinator can combine with GUI notebook evidence to prove the LLaVA-vLLM run outcome.
- Goal oracle: this goal is successful only when its file edits and push receipts are specific enough for the paired Codex app goal to review and use in the GUI evidence loop.
- Likely misfire: claiming that edited notebook files prove runtime success, or attempting to restart kernels, execute cells, or inspect outputs from Antigravity Codex.
- Blind spots considered: the working Jupyter/Workbench execution path is GUI/user-driven; this extension is an editor/pusher, not the notebook runtime witness.
- Existing plan facts: preserve `Documents/execplan_llava_vllm_runtime.md`; the parent SSOT `Documents/execplan_medical_workbench_runtime.md` points to that child plan as the authoritative runbook; target `chaoyinshe/llava-med-v1.5-mistral-7b-hf`; target notebook `notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb`; keep `name="llava_med_mistral_7b"` and `RUN_ID=llava_med_mistral_7b_medical_full_200_cases`; use vLLM with `--limit-mm-per-prompt {"image": 5}` and `MODEL_DTYPE="float16"` unless vLLM refusal is recorded by the GUI/runtime evidence loop; keep the standard RadLE prompt and OpenAI-style base64 image payload; do not add text-only controls, image-perturbation controls, SGLang shims, sitecustomize hacks, or chat-template hacks.

## Goal Oracle

The oracle for this goal is:

`The Antigravity Codex extension produces bounded, reviewable file edits and GitHub push evidence requested by the Codex app coordinator, without claiming notebook runtime success or attempting GUI-only kernel/cell/output actions.`

This goal is not complete because a notebook file exists. It is complete for a slice only when it returns concrete edit/push evidence to the paired Codex app goal.

## Goal Kind

`existing_plan`

## Current Tranche

Wait for a coordinator packet from `docs/goals/llava-vllm-runtime/goal.md`, then perform only the requested edit/push slice in Antigravity. Return exact evidence to the user so it can be pasted back into the Codex app coordinator goal.

## Claude Handoff Facts To Preserve

The user provided this handoff as source context for the Antigravity editing goal. Treat it as inherited plan context, not as runtime proof created by this goal.

- `Documents/execplan_llava_vllm_runtime.md` is the active LLaVA task and begins at Milestone 1.
- `Documents/execplan_medical_workbench_runtime.md` is the parent SSOT and now points to the child LLaVA-vLLM plan instead of duplicating it.
- SGLang is dead based on live Workbench HEAD `080ec65` evidence: all shims applied, the canonically-correct Mistral template loaded cleanly, and image tokens were spliced into the prompt, but generation never used the image.
- Exact failure signature to preserve for future smoke calibration: prompt tokens expanded `371 -> 949`, exactly `576` visual tokens; short prompt `24 -> 600`; 4-way probe results were A/B/C empty and D returned `image> `.
- The probe/smoke outputs were throwaway and not committed; the SGLang notebook is unchanged at `080ec65`.
- The new Section 6.5 vLLM smoke must hard-fail on empty output, 1-token EOS, `<image>` placeholder echo, and prompt echo. It must require a real clinical JSON diagnosis.
- The original `microsoft/llava-med-v1.5-mistral-7b` checkpoint is original LLaVA weight layout, not HF `LlavaForConditionalGeneration`; vLLM needs an HF-format checkpoint, not config relabeling.
- Preferred path: verify and use `chaoyinshe/llava-med-v1.5-mistral-7b-hf`.
- Fallback path only after recorded failure: convert the original checkpoint with Transformers `convert_llava_weights_to_hf.py`.

## Non-Negotiable Constraints

- This goal runs in the Antigravity Codex extension.
- Antigravity Codex may edit files and push to GitHub.
- Antigravity Codex must not be treated as able to restart kernels, execute notebook cells, or inspect live notebook outputs.
- Do not claim runtime success from static edits, notebook JSON structure, or a pushed commit.
- Notebook runtime evidence must come from the Antigravity GUI/user loop and be reviewed by the paired Codex app goal.
- Do not use CLI notebook execution as proof of Workbench/Jupyter behavior.
- Do not edit outside the coordinator-approved file scope.
- Do not reopen or repair the abandoned SGLang route unless the coordinator goal gets explicit new user direction.
- Do not treat `microsoft/llava-med-v1.5-mistral-7b` plus config relabeling as the vLLM solution.
- Do not start local checkpoint conversion unless the coordinator goal has recorded preferred HF checkpoint failure and explicitly approves fallback conversion work.
- Keep the official RadLE benchmark path stable; isolate this work to the medical Workbench LLaVA-vLLM route.
- Do not touch OctoMed or InternVL notebooks unless the coordinator explicitly changes scope.
- Do not resume SGLang without explicit new user direction.
- Do not add text-only controls, image-perturbation controls, or extra experimental arms.

## Stop Rule

Stop after each coordinator-approved edit/push slice with a receipt that the user can paste back into the Codex app goal. Stop immediately if a requested action requires kernel restart, cell execution, live output inspection, Workbench GUI state, or files outside the approved scope.

## Slice Sizing

Safe means bounded, explicit, verified, and reversible. For this goal, a good Worker package is one complete coordinator-approved edit/push slice, not a GUI runtime attempt.

## Board Health

The PM owns board health. If the board looks stale, misleading, offline, or inconsistent, run:

```bash
node C:/Users/thehb/.agents/skills/goalbuddy/scripts/check-goal-state.mjs docs/goals/llava-vllm-antigravity-extension/state.yaml
```

Repair only GoalBuddy control files unless an active Worker or PM task explicitly allows product-file edits.

## Canonical Board

Machine truth lives at:

`docs/goals/llava-vllm-antigravity-extension/state.yaml`

If this charter and `state.yaml` disagree, `state.yaml` wins for task status, active task, receipts, verification freshness, and completion truth.

## Run Command

```text
/goal Follow docs/goals/llava-vllm-antigravity-extension/goal.md.
```

## PM Loop

On every `/goal` continuation:

1. Read this charter.
2. Read `state.yaml`.
3. Confirm the user has pasted a coordinator packet from the Codex app goal.
4. Work only on the active task and only inside the coordinator-approved file scope.
5. Edit/push files as requested.
6. Do not restart kernels, run cells, inspect notebook outputs, or claim runtime success.
7. Return a compact receipt with changed files, commit/branch/PR link if available, static validation evidence, and any blocked reason.
8. Tell the user to paste that receipt back into the Codex app coordinator goal.
