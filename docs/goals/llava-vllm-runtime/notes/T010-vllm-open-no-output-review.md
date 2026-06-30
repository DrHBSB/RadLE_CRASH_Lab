# T010 vLLM Notebook Evidence Review

## Decision

`request_gui_run`

The correct LLaVA-vLLM notebook is now open in Antigravity, but there is no runtime evidence yet. Opening the notebook is useful orientation, not proof of smoke success.

## Evidence Reviewed

- Screenshot with old SGLang notebook still active before read-only open: `C:\Users\thehb\Pictures\Screenshots\codex-llava-t010-gui-review-20260701-032205.png`
- Screenshot after read-only open of the correct notebook: `C:\Users\thehb\Pictures\Screenshots\codex-llava-t010-vllm-open-readonly-20260701-032335.png`
- Visible active notebook after read-only open: `RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb`
- Visible title: `RadLE Medical Workbench LLaVA-vLLM Runtime`
- Visible checkpoint text: `chaoyinshe/llava-med-v1.5-mistral-7b-hf`
- GUI status: `Select Kernel`; cell 1 of 19.
- Static notebook JSON summary: 19 cells; all code cells have empty `execution_count` and `outputs=0`.

## Missing Evidence

- No selected/restarted kernel evidence.
- No Section `# 4. MODEL, SERVER, AND RUN CONFIG` output.
- No Section `# 6. START OR CONNECT TO LOCAL OPENAI-COMPATIBLE SERVER` output or `/v1/models` response.
- No Section `# 6.5. NON-WRITING LLaVA-vLLM SMOKE GATE` raw response, parsed `diagnosis`, or valid `likert_score`.
- No confirmation that Section `# 7. RUN ONE-MODEL MEDICAL RADLE BENCHMARK` was not run after the smoke gate.

## Ruling

Do not approve the full 200-case run. The next required action is a GUI-only run by the user/Antigravity GUI path: select/restart the correct kernel, clear outputs, run only through Section 6.5, stop before Section 7, and return outputs or the first real error.
