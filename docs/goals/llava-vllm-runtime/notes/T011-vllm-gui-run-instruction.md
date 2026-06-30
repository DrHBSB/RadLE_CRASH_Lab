# T011 vLLM GUI Run Instruction

The correct notebook is now open in Antigravity:

`notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb`

Do not use the SGLang notebook for this goal.

## Required GUI Action

In the open vLLM notebook:

1. Select the intended Workbench/Python kernel.
2. Restart the kernel.
3. Clear outputs.
4. Run from the top only through `# 6.5. NON-WRITING LLaVA-vLLM SMOKE GATE`.
5. Stop before `# 7. RUN ONE-MODEL MEDICAL RADLE BENCHMARK`.

## Return Evidence

Return either the first real visible error, or all of:

- Active notebook title/path showing `RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb`.
- Kernel identity after selection/restart.
- Section `# 4. MODEL, SERVER, AND RUN CONFIG` output showing `llava_med_mistral_7b`, `SERVER_ENGINE=vllm`, `RUN_ID`, `TEST_LIMIT`, `RESUME`, and `MAX_OUTPUT_TOKENS`.
- Section `# 6. START OR CONNECT TO LOCAL OPENAI-COMPATIBLE SERVER` output showing vLLM startup and `/v1/models`.
- Section `# 6.5. NON-WRITING LLaVA-vLLM SMOKE GATE` raw model response plus parsed `diagnosis` and `likert_score`.
- Confirmation that Section 7 was not run and no full-run CSV row was written by smoke.

## Rejection Rules

Still reject:

- SGLang notebook evidence.
- Server readiness alone.
- Token-count growth alone.
- Blank output.
- One-token output.
- Prompt echo.
- `<image>` or `image>` echo.
- Non-JSON output.
- Missing diagnosis.
- `I don't know`.
- Placeholder diagnosis.
- Invalid `likert_score`.

If a real code/notebook defect appears, send the exact error to the Antigravity Codex extension and require a committed and pushed fix before retrying.
