# T007 LLaVA-vLLM GUI Smoke Instruction

## Send / Use This GUI Instruction

The current visible notebook is still the old SGLang notebook. Do not run or judge that notebook for this goal.

In Antigravity GUI:

1. Open exactly `notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb`.
2. Confirm the branch is `codex/llava-vllm-runtime`.
3. Restart the notebook kernel and clear outputs for this vLLM notebook.
4. Run only from the top through `# 6.5. NON-WRITING LLaVA-vLLM SMOKE GATE`.
5. Stop before `# 7. RUN ONE-MODEL MEDICAL RADLE BENCHMARK` / cell 13.

Return evidence to the Codex app coordinator:

- Visible active notebook path/title proving this is `RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb`.
- Branch and kernel shown in the GUI.
- Cell 9 configuration output, including `SELECTED_MODEL_NAME`, `RUN_ID`, `TEST_LIMIT`, `RESUME`, and `MAX_OUTPUT_TOKENS`.
- Cell 11 vLLM server log path plus `/v1/models` response.
- Cell 12 raw smoke response plus parsed JSON fields, especially `diagnosis` and `likert_score`.
- Explicit confirmation that Section 7/cell 13 was not run and no full-run CSV row was written by smoke.

Stop and return the first visible error if any notebook import, dataset, Hugging Face, vLLM server, `/v1/models`, or smoke gate step fails.

## Rejection Rules

Do not treat any of the following as success:

- Evidence from `RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb`
- Server readiness alone
- Token-count growth alone
- Blank output
- One-token output
- Prompt echo
- `<image>` or `image>` echo
- Non-JSON output
- Missing diagnosis
- `I don't know`
- Placeholder diagnosis
- Invalid `likert_score`

If a real cell/output error appears, send the exact failing cell and traceback/error text back to the Antigravity Codex extension for a fix, then require a commit and push before retrying.
