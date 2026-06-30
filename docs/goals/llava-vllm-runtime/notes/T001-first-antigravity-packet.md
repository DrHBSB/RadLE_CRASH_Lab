# T001 First Antigravity Coordinator Packet

Created: 2026-07-01 02:43 +05:30

Coordinator board: `docs/goals/llava-vllm-runtime/state.yaml`

Purpose: provide the first coordinator-approved packet for the paired Antigravity Codex extension goal. This packet is checkpoint-first and static-edit-only. Runtime proof must still come from Antigravity GUI notebook evidence pasted back to the coordinator board.

## Paste This Into Antigravity Codex Extension

```text
/goal Follow docs/goals/llava-vllm-antigravity-extension/goal.md.

Coordinator packet from Codex app goal docs/goals/llava-vllm-runtime, task T001.

You are receiving the first coordinator-approved Antigravity edit/push packet. Work only in the paired Antigravity goal. Your current Antigravity board may have T003 active waiting for this packet; record this packet as received, then activate or replace the next Worker task for the bounded slice below.

Scope:
- This is an edit/push slice plus static HF checkpoint metadata verification.
- Do not restart kernels, execute notebook cells, inspect live notebook outputs, or claim runtime success.
- Do not use CLI notebook execution as proof of Workbench/Jupyter behavior.
- If any requested step requires GUI runtime evidence, stop and return a blocked receipt that says exactly what GUI evidence is needed.

Allowed files:
- src/radle_medical_custom_runtime.py
- notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb
- Documents/execplan_llava_vllm_runtime.md
- Documents/execplan_medical_workbench_runtime.md only if its pointer to the child LLaVA-vLLM plan is wrong or stale; otherwise leave it alone.
- docs/goals/llava-vllm-antigravity-extension/state.yaml
- docs/goals/llava-vllm-antigravity-extension/notes/**

No other product files are approved by this packet.

Non-negotiable constraints:
- Keep the official RadLE benchmark path stable.
- Do not touch OctoMed, InternVL, MedGemma, or the abandoned SGLang notebook path.
- Do not reopen SGLang.
- Do not use microsoft/llava-med-v1.5-mistral-7b through vLLM by config relabeling.
- Do not start checkpoint conversion unless the preferred HF checkpoint fails with recorded evidence and the Codex app coordinator explicitly approves fallback conversion in a later packet.
- Do not add text-only controls, image-perturbation controls, extra experimental arms, SGLang shims, sitecustomize hacks, or chat-template hacks.

Work package:
1. Read these files first:
   - docs/goals/llava-vllm-antigravity-extension/goal.md
   - docs/goals/llava-vllm-antigravity-extension/state.yaml
   - docs/goals/llava-vllm-runtime/goal.md
   - Documents/execplan_llava_vllm_runtime.md
   - src/radle_medical_custom_runtime.py
   - notebooks/RadLE_Medical_Workbench_Runtime.ipynb

2. Perform a structural HF Hub metadata gate for chaoyinshe/llava-med-v1.5-mistral-7b-hf without downloading full weights unless your tool needs small index metadata. Use any available hub client, Python huggingface_hub, hf CLI, or direct HF API. Record:
   - resolved revision SHA
   - presence of config.json
   - presence of preprocessor_config.json and/or processor_config.json
   - tokenizer files
   - model.safetensors.index.json and/or safetensor shards
   - config architecture and model_type
   - image_token_index
   - vision_config presence
   - text_config presence

   If this structural gate fails, stop before product edits. Do not convert checkpoints. Do not relabel the Microsoft checkpoint. Return a blocked receipt with the exact missing field/file or error.

3. If the structural gate passes, edit only the LLaVA runtime mapping in src/radle_medical_custom_runtime.py:
   - keep name="llava_med_mistral_7b"
   - set model_id="chaoyinshe/llava-med-v1.5-mistral-7b-hf"
   - set preferred_engine="vllm"
   - leave OctoMed, InternVL, MedGemma, and other entries unchanged.

4. Create notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb from the proven Workbench pattern in notebooks/RadLE_Medical_Workbench_Runtime.ipynb, not from the SGLang notebook. It must use:
   - SELECTED_MODEL_NAME = "llava_med_mistral_7b"
   - SERVER_ENGINE = "vllm"
   - RUN_LABEL_BASE = "medical_full_200_cases"
   - RUN_ID = "llava_med_mistral_7b_medical_full_200_cases" or the equivalent f-string from SELECTED_MODEL_NAME and RUN_LABEL_BASE
   - TEST_LIMIT = None
   - RESUME = True
   - MAX_OUTPUT_TOKENS = 2048
   - EXPECTED_FULL_CASES = 200
   - EXPECTED_FULL_IMAGES = 263
   - MODEL_DTYPE = "float16"
   - MAX_MODEL_LEN = 8192
   - EXTRA_SERVER_ARGS includes "--dtype", MODEL_DTYPE, "--limit-mm-per-prompt", "{\"image\": 5}"

5. Add a non-writing Section 6.5 smoke gate before the full benchmark call. It must:
   - use the standard RadLE prompt and OpenAI-style base64 data URL image payload style from src/radle_benchmark.py
   - use a real benchmark case, preferably a verified 5-image case such as case 156 if available from the dataset metadata
   - not write a row to the run CSV
   - hard-fail on empty output, 1-token EOS, "<image>" echo, prompt echo, non-JSON output, missing diagnosis, diagnosis equal to "I don't know", or placeholder/non-clinical diagnosis
   - require parseable clinical JSON with diagnosis and likert_score in 0..4

6. Preserve the Workbench audit, repair dry-run default, promotion guardrails, public answer-free export, runtime provenance, and GCS sync flow. Do not promote or sync while integrity problems or repair targets remain unless the user explicitly overrides in a later GUI/coordinator loop.

7. Update Documents/execplan_llava_vllm_runtime.md as a living ExecPlan:
   - Current State reflects what you actually completed or blocked.
   - Progress records the HF metadata gate, mapping patch, notebook creation, and validation only if each happened.
   - Surprises & Discoveries or Decision Log captures any structural checkpoint issue.
   - Revision Notes records the edit.
   - Do not mark runtime smoke or full run complete from static edits.

8. Run static validation and include command statuses in your receipt:
   - notebook JSON loads and section headers can be listed
   - forbidden carryover search has no matches:
     rg -n "sglang|sitecustomize|chat_template|llava_mistral|CLIPVisionConfig|MistralConfig positional|image_processor shim" notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb
   - runtime registry search shows the LLaVA name mapped to chaoyinshe/llava-med-v1.5-mistral-7b-hf with preferred_engine="vllm"
   - git diff --check passes
   - git status --short is captured

9. If repository/auth state permits, use branch codex/llava-vllm-runtime, commit the approved changes, and push the branch or create a draft PR. If push or PR creation is blocked, return local branch, diff summary, and exact auth/error evidence instead.

Return this receipt text for the user to paste back into the Codex app coordinator goal:

Antigravity receipt for Codex app goal docs/goals/llava-vllm-runtime T002
- result: done | blocked
- branch:
- commit:
- PR:
- changed_files:
- HF checkpoint metadata:
  - repo:
  - resolved_revision:
  - required_files_present:
  - config_architectures:
  - model_type:
  - image_token_index:
  - vision_config:
  - text_config:
- static_validation:
  - command:
  - status:
  - key_output:
- notebook_structure:
  - cells:
  - section_6_5_present:
  - forbidden_carryover_search:
- runtime_claims: none; GUI notebook execution evidence is still required
- blocked_or_missing:
- git_status_after:
- paste_back_instruction: paste this whole receipt into the Codex app coordinator goal.
```

## Coordinator Next Step

After the user returns the Antigravity receipt, the Codex app board should handle `T002`: ingest and summarize the Antigravity edit/push receipt, accept or reject the evidence, and decide whether to request another edit packet or proceed to Antigravity GUI notebook actions.
