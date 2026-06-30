# Run RadLE medical models on Vertex Workbench

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` or `AGENTS.md` file is present in this checkout as of 2026-06-30, but the active user instruction says ExecPlans belong under `Documents/` when that folder exists.

## Purpose / Big Picture

The user is running an experimental RadLE v2 medical-model benchmark path on a Google Vertex Workbench VM. The work is not the official RadLE benchmark path; it is a controlled medical-runtime path that serves one local or Hugging Face vision-language model at a time, writes standard RadLE CSVs, audits and repairs outputs, promotes a final result file, and syncs the run folder to private GCS.

This plan exists so a fresh agent can continue the model sequence without relying on chat memory. It records the completed `medgemma_1_5_4b` full baseline, the frozen dataset snapshot, the local and GCS artifact locations, the current notebook conventions, and the safe next action for running the next model.

## Current State

Current state (2026-06-30 19:54 +05:30, Codex/GPT-5): the `medgemma_1_5_4b` 200-case Workbench run is complete, promoted, synced to GCS, and downloaded locally under `results/medgemma_1_5_4b_medical_full_200_cases/`. The attempted `llava_med_mistral_7b` vLLM run failed because vLLM 0.23.0 / Transformers did not recognize `model_type=llava_mistral`. The first SGLang attempt stopped early because SGLang installed CUDA-13 PyTorch while the existing CUDA-12.9 torchvision from the vLLM path remained installed. Do not pivot to OctoMed without asking the user. The isolated LLaVA copy at `notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb` now removes vLLM in the SGLang path, installs `sglang[all]`, force-reinstalls the matching official PyTorch CUDA-13 trio (`torch==2.11.0`, `torchvision==0.26.0`, `torchaudio==2.11.0` from the `cu130` index), then probes SGLang `LlavaMistralForCausalLM`. It still selects `llava_med_mistral_7b` and keeps `RUN_LABEL_BASE = "medical_full_200_cases"`, model-scoped `RUN_ID`, `TEST_LIMIT = None`, `RESUME = True`, `EXPECTED_FULL_CASES = 200`, `EXPECTED_FULL_IMAGES = 263`, and `MAX_OUTPUT_TOKENS = 2048`. Next: pull latest `main` on Workbench, restart the kernel, reload/open the LLaVA SGLang notebook copy from disk, and rerun from the dependency cell.

## Locked Facts

- The official benchmark path is `notebooks/RadLE_v1_5_Morning.ipynb` plus `src/radle_benchmark.py`; do not change it for medical Workbench runs unless explicitly directed.
- The Workbench entrypoint is `notebooks/RadLE_Medical_Workbench_Runtime.ipynb`.
- The original custom-runtime Colab notebook is `notebooks/RadLE_Medical_Custom_Runtime.ipynb`; Workbench-only behavior belongs in the Workbench fork.
- The helper module is `src/radle_medical_custom_runtime.py`; its current roster includes `medgemma_1_5_4b`, `llava_med_mistral_7b`, `internvl3_5_8b`, and `octomed_7b`.
- The frozen dataset snapshot is `gs://radle-medical-data-toronto/datasets/radle-v2-frozen-2026-06-29/RadLE v2 Master Data`.
- The Workbench local dataset root is `/home/jupyter/radle_dataset/RadLE v2 Dataset`.
- The GCS result root is `gs://radle-medical-data-toronto/runs`.
- The full medical benchmark expects 200 grouped cases and 263 image files.
- Run IDs must be model-scoped: `RUN_ID = f"{SELECTED_MODEL_NAME}_{RUN_LABEL_BASE}"`.
- For full runs, `RUN_LABEL_BASE = "medical_full_200_cases"`, `TEST_LIMIT = None`, and `RESUME = True`.
- `llava_med_mistral_7b` is not a supported Workbench vLLM target in the pinned runtime: vLLM 0.23.0 exited before readiness because Transformers did not recognize `model_type=llava_mistral`.
- The first SGLang probe failed because PyTorch reported CUDA 13.0 while torchvision was compiled for CUDA 12.9; the LLaVA copy must force reinstall matching CUDA-13 PyTorch/torchvision/torchaudio after `sglang[all]`.
- Do not pivot to OctoMed without explicit user approval; the current task is to make LLaVA-Med work.
- The LLaVA-specific notebook copy is `notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb`, using run ID `llava_med_mistral_7b_medical_full_200_cases`.
- The completed baseline run is `medgemma_1_5_4b_medical_full_200_cases`.
- The completed baseline provenance commit is `f7204264d120df37767f22b58ffd6c87e11b21a4`.
- The completed baseline local final CSV is `results/medgemma_1_5_4b_medical_full_200_cases/final/RadLE_v2_results_final.csv`.
- The completed baseline GCS folder is `gs://radle-medical-data-toronto/runs/medgemma_1_5_4b_medical_full_200_cases`.
- The completed baseline final SHA-256 is `05311fd71b64f0cd8f8459a6788b2653efb99d6ded9b2766d0879bbc1c3ae8be`.
- Local verification on 2026-06-30 showed the baseline final CSV has 200 rows, 200 unique cases, 19 columns, and a hash matching the manifest.
- The baseline public summary reports `n_cases=200`, `valid_response_rate=1.0`, and `abstention_rate=0.135`.
- The local result folder contains 109 downloaded files and 93 raw backups for the completed baseline.
- The existing image grouping logic groups companion images such as `50.1.png` and `50.2.png`; do not rewrite grouping without concrete failing evidence.
- `/mnt/disks/models_ssd` was not mounted during the baseline run; the home-disk fallback worked and is acceptable.
- MedGemma required `MODEL_DTYPE = "bfloat16"`; LLaVA-Med stays on `float16`.

## Do Not Revisit

- Do not merge Workbench-specific behavior into the official benchmark notebook. See Decision Log 2026-06-29.
- Do not use confidential result CSVs, image files, model raw outputs, or downloaded run folders as Git-tracked artifacts. See Decision Log 2026-06-30.
- Do not trust notebook logs alone for completed-run claims; verify actual files, manifests, hashes, and CSV counts. See Decision Log 2026-06-30.
- Do not start the next full run with an unscoped run ID such as `medical_full_200_cases`; model name must be part of `RUN_ID`. See Decision Log 2026-06-30.
- Do not promote or sync a run if audit shows wrong row count, duplicate or missing cases, or pending repair targets. See Decision Log 2026-06-30.
- Do not assume the next model is ready just because it is in the roster; inspect current notebook/helper code and any model-specific runtime constraints first. See Decision Log 2026-06-30.

## Progress

- [x] (2026-06-29 16:47 +05:30, Codex/GPT-5) Created the original Workbench-prep plan after identifying that the Colab medical notebook could not be used directly in Workbench.
- [x] (2026-06-29 17:10 +05:30, Codex/GPT-5) Corrected scope by restoring `notebooks/RadLE_Medical_Custom_Runtime.ipynb` and keeping Workbench behavior in `notebooks/RadLE_Medical_Workbench_Runtime.ipynb`.
- [x] (2026-06-29 20:35 +05:30, Codex/GPT-5) Staged and documented the frozen dataset snapshot in private GCS with 263 image files.
- [x] (2026-06-30, Codex/GPT-5 and user) Updated the Workbench notebook for full-run defaults, expected counts, model-scoped run IDs, runtime artifacts, promotion guardrails, public export, and GCS sync.
- [x] (2026-06-30, user on Workbench with Codex guidance) Ran `medgemma_1_5_4b` full benchmark to 200 validated rows using `MAX_OUTPUT_TOKENS=2048` and `MODEL_DTYPE=bfloat16`.
- [x] (2026-06-30, user on Workbench with Codex guidance) Audited the full MedGemma run: 200 rows, 200 unique cases, accepted 196, repair targets 4 before cleanup.
- [x] (2026-06-30, user on Workbench with Codex guidance) Ran targeted repair for cases 44, 48, 54, and 113; all repair attempts returned `I don't know` and remained parse-failed until no-API cleanup.
- [x] (2026-06-30, user on Workbench with Codex guidance) Converted the four exact `Raw_Response == "I don't know"` parse-failed repair rows to accepted abstentions in `repair/repaired_results.csv`; audit then showed accepted 200 and repair targets 0.
- [x] (2026-06-30, user on Workbench with Codex guidance) Promoted the repaired MedGemma output, exported public tables, archived runtime artifacts, synced to GCS, and stopped/cleaned up the run.
- [x] (2026-06-30 18:02 +05:30, Codex/GPT-5) Verified actual GCS objects and manifests for the completed baseline, including final, public release, raw, repair, scorer, logs, and provenance folders.
- [x] (2026-06-30 18:07 +05:30, Codex/GPT-5) Downloaded the completed baseline GCS folder to `results/medgemma_1_5_4b_medical_full_200_cases/` and verified local row counts, unique cases, manifest hash, public summary, and provenance commit.
- [x] (2026-06-30 18:20 +05:30, Codex/GPT-5) Reconciled this ExecPlan from stale Workbench-prep state into a current model-sequence handoff.
- [x] (2026-06-30 18:56 +05:30, Codex/GPT-5) Inspected `src/radle_medical_custom_runtime.py` and `notebooks/RadLE_Medical_Workbench_Runtime.ipynb`; verified roster order is `medgemma_1_5_4b`, `llava_med_mistral_7b`, `internvl3_5_8b`, `octomed_7b`.
- [x] (2026-06-30 18:57 +05:30, Codex/GPT-5) Updated only `notebooks/RadLE_Medical_Workbench_Runtime.ipynb` defaults to select `llava_med_mistral_7b`; all full-run guardrails remained unchanged.
- [x] (2026-06-30 18:57 +05:30, Codex/GPT-5) Ran local sanity checks: `py_compile` on helper modules, notebook JSON parse, all 16 code cells compiled, extracted config matched the expected LLaVA-Med full-run values, and `git diff --check` exited 0.
- [x] (2026-06-30 19:04 +05:30, user on Workbench) Tried the committed LLaVA-Med vLLM path; config printed 200 cases, 263 images, model-scoped run ID, and `MAX_OUTPUT_TOKENS=2048`, but vLLM exited before readiness with `model_type=llava_mistral` unrecognized by Transformers.
- [x] (2026-06-30 19:41 +05:30, Codex/GPT-5) Rejected the OctoMed pivot after user correction, restored the main notebook to the normal committed path, created `notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb`, and made that copy the isolated LLaVA/SGLang experiment.
- [x] (2026-06-30 19:43 +05:30, Codex/GPT-5) Validated the LLaVA copy locally: both Workbench notebooks parse and compile, helper modules compile, copied notebook extracts `SERVER_ENGINE=sglang`, selected model `llava_med_mistral_7b`, run ID `llava_med_mistral_7b_medical_full_200_cases`, `TEST_LIMIT=None`, `RESUME=True`, expected 200 cases, expected 263 images, and `MAX_OUTPUT_TOKENS=2048`.
- [x] (2026-06-30 19:54 +05:30, user on Workbench and Codex/GPT-5) Captured the first SGLang dependency failure: SGLang import reached `torchvision.io.decode_jpeg`, then failed because PyTorch was CUDA 13.0 while torchvision was CUDA 12.9. Patched the LLaVA copy to uninstall vLLM in the SGLang path and force reinstall matching `torch==2.11.0`, `torchvision==0.26.0`, and `torchaudio==2.11.0` from `https://download.pytorch.org/whl/cu130` before the SGLang LLaVA probe.
- [ ] (next Workbench session, user/Codex) Pull latest `main` on Workbench, restart kernel, open/reload `notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb` from disk, run cells top-to-bottom, and audit actual files before promoting or syncing.

## Surprises & Discoveries

- Observation: The Workbench/Jupyter session can disconnect or dispose the kernel while vLLM is still running or while the notebook cell state is confusing.
  Evidence: User saw `Cannot execute code, session has been disposed` and later checked `nvidia-smi` to see whether `VLLM::EngineCore` was still present.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Observation: `nvidia-smi` with no `VLLM::EngineCore` process means the model server is dead; rerunning the benchmark cell alone will not work until the server cell starts vLLM again.
  Evidence: The user observed GPU memory drop from about 19.5 GiB on GPU 0 to 0 MiB after a failed run.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Observation: For MedGemma, raw responses of exactly `I don't know` may be semantically valid abstentions while the parser can still label them `PARSE_FAILED` when no JSON fields are present.
  Evidence: Cases 44, 48, 54, and 113 each had raw preview `I don't know`, 6 completion tokens, failed targeted repair twice, and were later accepted as abstentions after exact no-API cleanup.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Observation: The targeted repair function reported `Remaining repair targets: 0`, but the promotion guard still halted because its audit path did not count repair attempts unless the repair call log was supplied.
  Evidence: The user saw `Remaining repair targets: 0` followed by `WARNING: 4 case-model cells still need repair. Promotion halted.`
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Observation: The previous Workbench ExecPlan was not maintained during the full baseline run, so it became stale even though the run itself succeeded.
  Evidence: Before this revision, `Current State` still asked for a live GPU smoke and did not mention the completed 200-case MedGemma run.
  Date/Author: 2026-06-30, Codex/GPT-5

- Observation: LLaVA-Med cannot be made to work by simply rerunning the vLLM server cell in the pinned Workbench runtime.
  Evidence: Workbench vLLM 0.23.0 server exited before readiness for `microsoft/llava-med-v1.5-mistral-7b` with `Value error, The checkpoint you are trying to load has model type llava_mistral but Transformers does not recognize this architecture.`
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Observation: SGLang import can fail before model startup if the old vLLM CUDA-12.9 torchvision wheel remains after SGLang installs CUDA-13 PyTorch.
  Evidence: Workbench dependency cell printed `PyTorch has CUDA Version=13.0 and torchvision has CUDA Version=12.9. Please reinstall the torchvision that matches your PyTorch install.`
  Date/Author: 2026-06-30, user and Codex/GPT-5

## Decision Log

- Decision: Keep Workbench-specific notebook behavior in `notebooks/RadLE_Medical_Workbench_Runtime.ipynb` and keep `notebooks/RadLE_Medical_Custom_Runtime.ipynb` as the standard custom-runtime Colab path.
  Rationale: The user explicitly corrected an earlier attempt that edited the Colab notebook and asked for Workbench work to live in a new notebook.
  Date/Author: 2026-06-29, Codex/GPT-5 and user

- Decision: Treat `Documents/runtime_provenance_contract_radle_medical.md` as a useful contract reference, but do not trust stale checkout facts inside it without current verification.
  Rationale: It records durable dataset and roster facts, but its observed checkout section predates the completed `f720426` baseline.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: Use model-scoped run IDs for all medical full runs.
  Rationale: Model-scoped IDs prevent collisions across different models using the same run label and make GCS/local artifact folders unambiguous.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Decision: Preserve and verify artifacts outside the VM before considering a run complete.
  Rationale: Workbench VMs can be stopped or lost; completed scientific evidence must exist in GCS and, when requested, in a local Windows mirror with manifest and hash verification.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Decision: For parse-failed rows whose raw response is exactly `I don't know`, convert only those exact rows to accepted abstentions after failed paid repair attempts, rather than forcing more API repair calls.
  Rationale: The model returned a valid abstention phrase, repeated repair calls reproduced the same output, and promotion should distinguish a true abstention from a malformed diagnosis.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Decision: Select `llava_med_mistral_7b` as the next full Workbench model.
  Rationale: Current file inspection shows the helper-module roster order is `medgemma_1_5_4b`, then `llava_med_mistral_7b`, then `internvl3_5_8b`, then `octomed_7b`. The local model config does not mark LLaVA-Med as gated and does not override the default max output token policy.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: Keep LLaVA-Med as the target and isolate its serving workaround in a copied notebook instead of pivoting to OctoMed.
  Rationale: The user explicitly rejected moving to OctoMed before asking. The LLaVA-Med failure is a serving-stack issue, not a dataset/run-contract issue, so a separate copy lets the project try LLaVA-specific SGLang or native-adapter changes without contaminating the normal Workbench notebook for the other roster models.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Decision: Stay on `main` in the local checkout unless the next model change expands beyond notebook/doc defaults.
  Rationale: The user is using `git pull` directly on Workbench. A short, reviewed commit to `main` keeps the remote execution path simple.
  Date/Author: 2026-06-30, Codex/GPT-5

## Revision Notes

- v1-v3 (2026-06-29, Codex/GPT-5): Original Workbench-prep plan created, validated locally, and corrected after the Colab notebook was restored and the Workbench fork became the owned target.
- v4 (2026-06-30, Codex/GPT-5): Rewrote the plan after the completed MedGemma full run. Added verified baseline artifacts, GCS/local evidence, next-model workflow, repair lessons, and stricter acceptance rules so a fresh session can resume without chat history.
- v5 (2026-06-30, Codex/GPT-5): Replaced the generic skills table with an operational skill-routing matrix that names triggers, evidence requirements, non-use cases, and activation mode for each phase.
- v6 (2026-06-30, Codex/GPT-5): Recorded `llava_med_mistral_7b` as the next prepared full-run model, updated validation receipts, and shifted the next action to Workbench execution.
- v7 (2026-06-30, Codex/GPT-5): Reconciled the live vLLM failure and user correction. Recorded that LLaVA remains the target, OctoMed requires explicit approval, and the LLaVA workaround now lives in `notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb`.
- v8 (2026-06-30, Codex/GPT-5): Recorded the SGLang torch/torchvision CUDA mismatch and patched the copied notebook to force reinstall the official PyTorch CUDA-13 trio before probing SGLang LLaVA support.

## Outcomes & Retrospective

Completed outcome: the Workbench medical path has produced one verified full 200-case baseline for `medgemma_1_5_4b`. The run has a model-scoped folder in GCS, a downloaded local mirror, final/private CSV with matching SHA-256, public release tables, scorer view, raw backups, repair artifacts, runtime logs, and provenance JSON.

Remaining work: run `llava_med_mistral_7b` from the copied LLaVA SGLang notebook. The next Workbench session should rely on the notebook's guardrails: expected 200 cases, expected 263 image files, resume enabled, audit before repair, no promotion with repair targets, export/sync only after a clean audit.

Reusable lesson: for VM-hosted benchmark runs, artifact readiness should be proven by independent storage and file audits, not by notebook logs. This is broadly reusable, but no global skill update has been made. Ask the user before promoting it into a reusable skill.

## Suggested Skills By Phase

This section is a routing matrix, not a menu. Use a skill only when its trigger fires, and require a concrete receipt from that skill. For ordinary command execution, file inspection, small Python checks, `git`, and `gcloud storage`, use direct tools rather than wrapping the work in a skill.

| Workflow Gate | Trigger For Using A Skill | Skill To Use | Required Receipt / Evidence | Do Not Use It For | Activation |
| --- | --- | --- | --- | --- | --- |
| Long-lived state and handoff | The run target, dataset contract, promotion rules, repair policy, or completed-run evidence changes. | `execplan` | Updated `Current State`, `Locked Facts`, `Progress`, `Decision Log`, and `Artifacts And Notes` with exact paths, counts, hashes, and next action. | Routine status replies, simple command output, or one-off notebook cell guidance. | `auto-suggest` |
| Notebook mutation | Editing `notebooks/RadLE_Medical_Workbench_Runtime.ipynb`, changing defaults, adding cells, or touching notebook JSON. | `jupyter-notebook` | Notebook parses as JSON, code cells compile, config grep shows expected model/run settings, and diff is scoped to intended cells. | Purely reading a notebook or giving the user run instructions without editing. | `auto-suggest` |
| Model feasibility research | Current helper/notebook files are insufficient to decide whether a roster model can run under vLLM on 2 x L4, needs gated access, a different dtype, a different engine, or a specific model revision. | `hugging-face:hf-cli` for Hub metadata and files; use web/primary sources only if the skill or local files cannot answer. | Exact model repo ID, relevant config fields, gated/access status, model card/runtime caveats, and any dtype/context/GPU-memory implications recorded in this plan or the commit message. | Re-checking known local roster order, downloading weights, or doing broad model shopping. | `manual` |
| Workbench and GCS operations | Verifying remote run artifacts, copying results, checking object metadata, or confirming dataset snapshot objects. | `none`; use `gcloud storage` or the available gcloud MCP directly. | GCS object paths, object sizes/timestamps where useful, manifest contents, and local hash/row-count checks after download. | Treating notebook rsync logs as proof of persistence. | `none` |
| Run audit and repair decision | Audit results affect whether to repair, clean up, promote, export, or sync. | `data-analytics:analyze-data-quality` when the evidence spans multiple CSVs/manifests or conflicting counts; otherwise `none` with direct Python/CSV checks. | Dataset integrity table, row count, unique case count, missing/extra/duplicate cases, bucket/status summaries, repair-target table, final manifest hash, public summary alignment. | Cosmetic summaries or dashboard/report generation. | `manual` |
| Public release/privacy validation | Export logic changes, public tables are being shared, or private/public files disagree. | `data-analytics:validate-data` | Public files contain no diagnosis columns, raw responses, reasoning text, image filenames, image hashes, or private case IDs; public summary reconciles with final/private manifest. | Re-validating an unchanged public export already covered by manifest and row-count checks. | `manual` |
| Git publication | Opening a PR, addressing PR review, or using GitHub metadata is required. | `github:yeet` for PR-style publishing; otherwise `none` and use direct `git add`, `git commit`, `git push`. | Commit SHA, pushed branch, PR link if applicable, and scoped staged diff. | Simple main-branch commits for notebook default changes when the user expects Workbench to `git pull main`. | `manual` |
| Live user-guided Workbench run | The user is actively running cells and needs next commands, recovery logic, or interpretation of `nvidia-smi`, audit tables, repair plans, and sync results. | `none` | Concise operational instructions tied to the user's current output, with exact next cell/action and stop conditions. | Delegating to an orchestrator or making unattended runtime changes on the VM without evidence. | `none` |
| Multi-agent orchestration | Only if the user explicitly asks for agent orchestration or the run becomes multi-branch, review-gated, and too broad for a single Codex session. | Do not use by default. `agency-agents` only if explicitly requested. | Written agent roles, boundaries, receipts, and handoff criteria. | Normal sequential model runs, notebook edits, or artifact audits. | `manual` |

## Context And Orientation

This repository contains RadLE v2 benchmark notebooks and helper modules. The official benchmark path remains separate from the experimental medical Workbench path. The medical path is meant to run one selected vision-language model at a time through an OpenAI-compatible local server, usually vLLM, and reuse the standard RadLE output shape.

Important paths:

- `notebooks/RadLE_Medical_Workbench_Runtime.ipynb`: Workbench notebook to edit for next medical model runs.
- `src/radle_medical_custom_runtime.py`: model roster, server startup helpers, OpenAI-compatible client setup, medical benchmark wrapper, and CSV validation helpers.
- `src/radle_benchmark.py`: shared benchmark/audit/repair/promote/export logic.
- `Documents/runtime_provenance_contract_radle_medical.md`: internal contract for dataset snapshot, Workbench host, model roster, and provenance expectations; useful but partly stale and should be verified.
- `results/medgemma_1_5_4b_medical_full_200_cases/`: local mirror of the completed baseline; do not commit this data.

The Workbench VM used for the baseline was `medical-master-radfm` in GCP project `crashlab-synthetic`, zone `northamerica-northeast2-b`, with `2 x NVIDIA L4`. The baseline server used vLLM for `google/medgemma-1.5-4b-it` with dtype `bfloat16`.

## Plan Of Work

First, orient against current files. Read the Workbench notebook config cell and the model roster in `src/radle_medical_custom_runtime.py`. Confirm `HEAD`, branch, and working tree state. Confirm whether `Documents/runtime_provenance_contract_radle_medical.md` or this ExecPlan needs an update for the next model.

Second, select the next model conservatively. Current file inspection verified that the roster lists `llava_med_mistral_7b` after `medgemma_1_5_4b`, then `internvl3_5_8b`, then `octomed_7b`. The selected next model is `llava_med_mistral_7b`; its local model config does not require a Hugging Face token and does not override the default max output token policy.

Third, edit only the Workbench notebook defaults needed for the next run. Preserve `RUN_LABEL_BASE = "medical_full_200_cases"`, `RUN_ID = f"{SELECTED_MODEL_NAME}_{RUN_LABEL_BASE}"`, `TEST_LIMIT = None`, `RESUME = True`, `EXPECTED_FULL_CASES = 200`, `EXPECTED_FULL_IMAGES = 263`, and `MAX_OUTPUT_TOKENS = 2048` unless inspection proves a different safe value is needed. Keep the completed MedGemma result folder untouched.

Fourth, validate locally. Parse the notebook JSON, compile notebook code cells, compile the helper modules, and run a focused config extraction if possible. Do not start a real model server locally.

Fifth, commit and push. Because the Workbench run uses `git pull`, the notebook change must be pushed before the user restarts the Workbench kernel. Include this ExecPlan or provenance contract in the commit only if they were intentionally updated and should travel with the repo.

Sixth, give the user an exact Workbench runbook. It should include pulling latest repo, restarting kernel, reloading notebook from disk, confirming the printed config, starting vLLM, running the benchmark, auditing, inspecting repair targets before repair, promoting/exporting/syncing only after zero repair targets, and stopping the server.

## Milestones

Milestone 1, next-model preparation, uses `jupyter-notebook`: The Workbench notebook defaults point to the verified next model and print a model-scoped full-run config for 200 cases and 263 image files. Evidence is a local notebook parse/config check and a focused diff.

Milestone 2, repository handoff, uses `execplan`: The notebook change, this plan, and any provenance-contract update are reconciled so a fresh session can understand the completed baseline and next model target. Evidence is `git diff --check`, status, and a commit on `main`.

Milestone 3, live Workbench run, uses `none`: The user runs the notebook on the Workbench VM, confirms the config, starts vLLM, completes the benchmark with resume enabled, and gets 200 validated output rows. Evidence is audit output plus files in the run folder, not logs alone.

Milestone 4, completed-run verification, uses `data-analytics:analyze-data-quality` optionally: Verify final/private CSV rows and unique cases, public summary, manifest hash, GCS object presence, and local download if requested. Evidence is literal row counts, SHA-256, and GCS/local paths.

## Concrete Steps (Commands)

From repo root, inspect state:

    git status --short --branch
    git rev-parse --short HEAD

Expected on 2026-06-30 before the next-model edit:

    ## main...origin/main
    f720426

There may be unrelated modified and untracked files. Do not revert user work.

Inspect roster and notebook defaults:

    rg -n "MEDICAL_CUSTOM_RUNTIME_MODELS|name=|SELECTED_MODEL_NAME|RUN_LABEL_BASE|RUN_ID|TEST_LIMIT|RESUME|MAX_OUTPUT_TOKENS|MODEL_DTYPE" src/radle_medical_custom_runtime.py notebooks/RadLE_Medical_Workbench_Runtime.ipynb

Expected current model names include:

    medgemma_1_5_4b
    llava_med_mistral_7b
    internvl3_5_8b
    octomed_7b

Validate Python modules after notebook/default edits:

    py -3.11 -m py_compile src/radle_medical_custom_runtime.py src/radle_benchmark.py

Expected: no output and exit code 0.

Validate notebook JSON and code-cell compilation:

    py -3.11 -c "import ast,json,pathlib; nb=json.loads(pathlib.Path('notebooks/RadLE_Medical_Workbench_Runtime.ipynb').read_text(encoding='utf-8-sig')); cells=[c for c in nb['cells'] if c.get('cell_type')=='code']; [compile(''.join(c.get('source',[])), f'cell_{i}', 'exec') for i,c in enumerate(cells,1)]; print('compiled code cells', len(cells))"

Expected: prints `compiled code cells` followed by a positive count.

Check whitespace:

    git diff --check

Expected: no output.

Verify completed baseline local mirror if needed:

    $root='C:\Users\thehb\Documents\RadLE v2\results\medgemma_1_5_4b_medical_full_200_cases'
    $manifest=Get-Content -Raw -Path (Join-Path $root 'final\RadLE_v2_results_final_manifest.json') | ConvertFrom-Json
    $hash=(Get-FileHash -Algorithm SHA256 -Path (Join-Path $root 'final\RadLE_v2_results_final.csv')).Hash.ToLowerInvariant()
    $hash -eq $manifest.sha256

Expected:

    True

Verify completed baseline GCS if needed:

    gcloud storage ls --recursive "gs://radle-medical-data-toronto/runs/medgemma_1_5_4b_medical_full_200_cases"
    gcloud storage cat "gs://radle-medical-data-toronto/runs/medgemma_1_5_4b_medical_full_200_cases/final/RadLE_v2_results_final_manifest.json"

Expected: the listing includes `final/`, `public_release/`, `raw/`, `repair/`, `runtime_artifacts/`, and `scorer/`; the manifest reports 200 rows and 200 cases.

## Validation And Acceptance

Local acceptance for the next-model prep:

- The Workbench notebook parses as JSON and all code cells compile.
- `src/radle_medical_custom_runtime.py` and `src/radle_benchmark.py` compile.
- A focused grep or notebook inspection shows the intended next `SELECTED_MODEL_NAME`, model-scoped `RUN_ID`, `TEST_LIMIT = None`, `RESUME = True`, expected 200 cases, expected 263 image files, and `MAX_OUTPUT_TOKENS = 2048` unless explicitly changed.
- `git diff --check` is clean.
- The completed MedGemma result folder is not modified.

Live acceptance for a next full run:

- The notebook prints the current repo commit after pull.
- The config printout shows the selected next model, `medical_full_200_cases`, model-scoped run ID, full mode, expected 200 cases, expected 263 image files, and the selected dtype.
- The server cell reaches `/v1/models` and `nvidia-smi` shows `VLLM::EngineCore` before the benchmark cell runs.
- The benchmark cell validates exactly 200 output rows.
- The audit reports 200 rows, 200 unique cases, no missing or extra case IDs, and zero repair targets before promotion. If repair targets exist, inspect them before repair.
- Promotion/export/sync runs only after the final audit is clean or after an explicitly recorded, narrow cleanup decision.
- Completed-run claims are verified by files: final manifest, final CSV row count, public summary, GCS object listing, and local mirror when requested.

## Idempotence And Recovery

The notebook setup cells are intended to be rerunnable. If Workbench asks whether to reload from disk after `git pull`, reload from disk and do not overwrite a newer file.

If the Jupyter session is disposed but `nvidia-smi` still shows `VLLM::EngineCore`, reconnect the kernel and test the endpoint before restarting the server. If `nvidia-smi` shows no vLLM process, rerun the server cell before rerunning the benchmark cell.

If a full run is interrupted, keep the same `SELECTED_MODEL_NAME`, `RUN_LABEL_BASE`, and model-scoped `RUN_ID`, leave `RESUME = True`, restart the server if needed, and rerun the benchmark cell. The raw CSV and numbered backups are the recovery anchor.

If repair targets appear, run the targeted repair plan first with confirmation `NO` to inspect targets. Use the notebook's required confirmation string for actual repair, not a plain `YES`. For the current repair implementation, valid confirmations have included `YES_REPAIR_10` and `YES_REPAIR_ALL`; verify current code before use.

If promotion halts, do not override by setting `ALLOW_PROMOTE_WITH_PENDING_REPAIRS=True` unless the row-level audit is understood and documented. Prefer fixing the audit/repair input or making a narrow no-API cleanup when the raw response is semantically valid and exactly matches the intended abstention.

## Artifacts And Notes

Completed baseline local verification transcript from 2026-06-30:

    LocalRoot               : C:\Users\thehb\Documents\RadLE v2\results\medgemma_1_5_4b_medical_full_200_cases
    LocalFiles              : 109
    RawBackups              : 93
    ManifestRows            : 200
    ManifestCaseCount       : 200
    ManifestExpectedImages  : 263
    FinalCsvRows            : 200
    FinalUniqueCases        : 200
    FinalColumns            : 19
    ManifestSha256          : 05311fd71b64f0cd8f8459a6788b2653efb99d6ded9b2766d0879bbc1c3ae8be
    LocalFinalSha256        : 05311fd71b64f0cd8f8459a6788b2653efb99d6ded9b2766d0879bbc1c3ae8be
    LocalRepairSha256       : 05311fd71b64f0cd8f8459a6788b2653efb99d6ded9b2766d0879bbc1c3ae8be
    FinalMatchesManifest    : True
    FinalMatchesRepair      : True
    PublicSummaryNCases     : 200
    PublicValidResponseRate : 1.0
    PublicAbstentionRate    : 0.135
    ProvenanceCommit        : f7204264d120df37767f22b58ffd6c87e11b21a4
    ProvenanceRemoteRoot    : gs://radle-medical-data-toronto/runs/medgemma_1_5_4b_medical_full_200_cases

Completed baseline final manifest excerpt:

    "run_id": "medgemma_1_5_4b_medical_full_200_cases"
    "source_label": "repaired"
    "rows": 200
    "columns": 19
    "case_count": 200
    "sha256": "05311fd71b64f0cd8f8459a6788b2653efb99d6ded9b2766d0879bbc1c3ae8be"
    "expected_case_count": 200
    "expected_image_file_count": 263
    "max_output_tokens": 2048

Completed baseline public summary:

    run_id,model,provider,n_cases,valid_response_rate,abstention_rate,mean_likert_score,mean_latency_seconds,mean_prompt_tokens,mean_completion_tokens,mean_reasoning_tokens,mean_score_binary,mean_score_likert
    medgemma_1_5_4b_medical_full_200_cases,medgemma_1_5_4b,UNKNOWN,200,1.0,0.135,3.2254335260115607,15.847999999999999,670.585,463.56,0.0,,

Next-model prep local validation transcript from 2026-06-30:

    notebook: notebooks\RadLE_Medical_Workbench_Runtime.ipynb
    code_cells_compiled: 16
    selected_model: llava_med_mistral_7b
    model_scoped_run_id: llava_med_mistral_7b_medical_full_200_cases
    test_limit: None
    resume: True
    expected_cases: 200
    expected_image_files: 263
    max_output_tokens: 2048

LLaVA SGLang copy local validation transcript from 2026-06-30:

    compiled notebooks\RadLE_Medical_Workbench_Runtime.ipynb 16
    compiled notebooks\RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb 16
    llava_copy_selected_model: llava_med_mistral_7b
    llava_copy_server_engine: sglang
    llava_copy_run_id: llava_med_mistral_7b_medical_full_200_cases
    llava_copy_test_limit: None
    llava_copy_resume: True
    llava_copy_expected_cases: 200
    llava_copy_expected_images: 263
    llava_copy_max_output_tokens: 2048

Internet research notes for the LLaVA copy:

    Microsoft LLaVA-Med README documents the native LLaVA-Med serving path with controller/model_worker and `--model-path microsoft/llava-med-v1.5-mistral-7b`.
    Current SGLang source registers `LlavaMistralForCausalLM` in `sglang.srt.models.llava`, so the copied notebook probes for that class immediately after SGLang install.

Important user preference:

    "dont trust on logs, see and audit files"

Honor this literally for future run completion claims.

## Interfaces And Dependencies

The Workbench notebook must continue to use these helper interfaces unless a deliberate refactor updates the notebook and helper together:

- `medical_runtime.build_medical_run_paths(dataset_root, model_name, run_label)`
- `medical_runtime.start_model_server(...)`
- `medical_runtime.wait_for_openai_server(...)`
- `medical_runtime.make_openai_client(BASE_URL)`
- `medical_runtime.run_medical_model_benchmark(...)`
- `medical_runtime.validate_output_csv(raw_results_csv, SELECTED_MODEL_NAME)`
- `radle_benchmark.audit_benchmark_output(...)`
- `radle_benchmark.run_targeted_repair(...)`
- `radle_benchmark.promote_repaired_or_raw_results(...)`
- public export helpers in `src/radle_benchmark.py`

Environment and credential expectations:

- `RADLE_DATASET_GCS_URI`: should resolve to the frozen dataset prefix unless a future contract replaces it.
- `RADLE_DATASET_ROOT`: optional local or mounted dataset root containing `RadLE v2 Master Data`.
- `RADLE_RUNTIME_ROOT`: optional writable runtime root.
- `RADLE_RUNTIME_CACHE_ROOT`: optional cache root override.
- `RADLE_RESULTS_GCS_URI`: should resolve to `gs://radle-medical-data-toronto/runs`.
- `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN`: needed for gated Hugging Face models.
- `GITHUB_TOKEN`: needed if Workbench must clone or pull the private GitHub repo.

Workbench run environment observed for the completed baseline:

- Python: `/opt/micromamba/bin/python3`, Python 3.12.13.
- GPUs: `2 x NVIDIA L4`.
- vLLM for MedGemma used dtype `bfloat16`.
- Home-disk fallback was used because `/mnt/disks/models_ssd` was not mounted.
