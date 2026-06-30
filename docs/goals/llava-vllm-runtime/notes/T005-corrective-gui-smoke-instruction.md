# T005 Corrective GUI Smoke Instruction

Created: 2026-07-01 02:58 +05:30

Coordinator board: `docs/goals/llava-vllm-runtime/state.yaml`

## Correction

The visible Antigravity state is on the old SGLang notebook. For the next evidence packet, use the new vLLM notebook only.

## Short Instruction To Follow In Antigravity GUI

1. In Antigravity, stay on branch `codex/llava-vllm-runtime`.

2. Open this exact notebook:

   `notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb`

   Do not use:

   `notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb`

3. Restart the selected Workbench/Jupyter kernel and clear outputs.

4. Run only through:

   `# 6.5. NON-WRITING LLaVA-vLLM SMOKE GATE`

   Stop before:

   `# 7. RUN ONE-MODEL MEDICAL RADLE BENCHMARK`

5. Paste back:

   - visible notebook path and kernel/runtime
   - cell 9 config output: selected model, run id, dtype, max model length, extra server args
   - cell 11 server output: server log path and `/v1/models` response
   - cell 12 smoke output: smoke case id, image count, raw response, parsed `diagnosis`, parsed `likert_score`, and final non-writing smoke pass line
   - confirmation that cell 13 was not run

## Stop Conditions

Stop and paste the traceback/output if dependency install, imports, dataset staging, HF download/auth, vLLM server startup, `/v1/models`, or the Section 6.5 smoke gate fails.

Do not start the 200-case full run until the Codex app coordinator accepts the Section 6.5 smoke evidence.
