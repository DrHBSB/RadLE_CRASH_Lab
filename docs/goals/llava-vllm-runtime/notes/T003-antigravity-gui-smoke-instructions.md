# T003 Antigravity GUI Smoke Instructions

Created: 2026-07-01 02:56 +05:30

Coordinator board: `docs/goals/llava-vllm-runtime/state.yaml`

## Purpose

Collect the first runtime evidence for the LLaVA-vLLM Workbench path. This is a GUI-only Antigravity notebook action. It is not a full 200-case run.

The next gate is the non-writing Section 6.5 smoke gate in:

`notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb`

## Exact GUI Steps For Antigravity

1. In Antigravity IDE, make sure the repo is on branch `codex/llava-vllm-runtime`.

2. Open:

   `notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb`

3. Select the intended Workbench/Jupyter Python kernel for this runtime. Restart the kernel and clear outputs before the smoke run.

4. Run cells sequentially from the top through cell 12 only:

   - cell 1: title markdown
   - cell 2: data staging contract markdown
   - cell 3: `# 0. DATA STAGING CONFIG`
   - cell 4: cache dataset markdown
   - cell 5: cache dataset code
   - cell 6: `# 1. RUNTIME SETUP: REPO CODE ONLY`
   - cell 7: `# 2. PYTHON DEPENDENCIES + CACHE ROUTING`
   - cell 8: `# 3. IMPORT MEDICAL RUNTIME HELPERS`
   - cell 9: `# 4. MODEL, SERVER, AND RUN CONFIG`
   - cell 10: `# 5. HUGGING FACE ACCESS`
   - cell 11: `# 6. START OR CONNECT TO LOCAL OPENAI-COMPATIBLE SERVER`
   - cell 12: `# 6.5. NON-WRITING LLaVA-vLLM SMOKE GATE`

5. Stop before cell 13:

   `# 7. RUN ONE-MODEL MEDICAL RADLE BENCHMARK`

   Do not start the full benchmark until this coordinator board accepts the smoke evidence.

## Evidence To Paste Back

Paste text output and/or screenshots for these exact fields:

1. Branch/kernel context:
   - visible branch is `codex/llava-vllm-runtime`
   - notebook path is `notebooks/RadLE_Medical_Workbench_LLaVA_vLLM_Runtime.ipynb`
   - selected kernel/runtime name

2. Cell 9 config output:
   - `Selected model`
   - `Run ID`
   - `Test limit`
   - `Max output tokens`
   - `Model dtype`
   - `Max model length`
   - `Extra server args`

3. Cell 11 server evidence:
   - server log path
   - `/v1/models` or `/models` response
   - whether the served model is `chaoyinshe/llava-med-v1.5-mistral-7b-hf`

4. Cell 12 smoke evidence:
   - smoke case id
   - smoke image count
   - raw model response
   - parsed `diagnosis`
   - parsed `likert_score`
   - final line: `Non-writing smoke gate passed. No benchmark CSV row was written by this cell.`

5. Stop confirmation:
   - confirm cell 13 was not run
   - confirm no full-run CSV row was written by the smoke step

## Stop Conditions

Stop immediately and paste the visible error/traceback if any of these happen:

- notebook cannot open or the kernel cannot be selected
- dependency install or import fails
- dataset staging cannot find the frozen dataset
- HF download/auth fails
- vLLM refuses the checkpoint or `MODEL_DTYPE="float16"`
- server never reaches `/v1/models`
- smoke output is empty, one-token, prompt echo, `<image>`/`image>` echo, non-JSON, missing `diagnosis`, `"I don't know"`, placeholder diagnosis, or invalid `likert_score`
- cell 13 starts accidentally

If cell 11 fails, also paste the last visible server log lines from the notebook output. If cell 12 fails, paste the entire traceback and the raw smoke response if present.

## Coordinator Next Step

After the user returns this evidence, the coordinator board should use `T004` to judge whether the GUI smoke evidence is sufficient. If the smoke passes, the next coordinator packet can ask for the bounded full-run GUI action. If the smoke fails, the next packet should route back to Antigravity editing only with the exact failure evidence.
