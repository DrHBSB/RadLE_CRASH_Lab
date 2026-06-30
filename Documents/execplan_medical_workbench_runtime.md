# Run RadLE medical models on Vertex Workbench

This ExecPlan is a living document. The sections `Current State`, `Locked Facts`, `Do Not Revisit`, `Progress`, `Surprises & Discoveries`, `Decision Log`, `Revision Notes`, `Outcomes & Retrospective`, and `Suggested Skills By Phase` must be kept up to date as work proceeds.

This plan follows `~/.codex/PLANS.md`. No repo-local `PLANS.md` or `AGENTS.md` file is present in this checkout as of 2026-06-30, but the active user instruction says ExecPlans belong under `Documents/` when that folder exists.

## Purpose / Big Picture

The user is running an experimental RadLE v2 medical-model benchmark path on a Google Vertex Workbench VM. The work is not the official RadLE benchmark path; it is a controlled medical-runtime path that serves one local or Hugging Face vision-language model at a time, writes standard RadLE CSVs, audits and repairs outputs, promotes a final result file, and syncs the run folder to private GCS.

This plan exists so a fresh agent can continue the model sequence without relying on chat memory. It records the completed `medgemma_1_5_4b` full baseline, the frozen dataset snapshot, the local and GCS artifact locations, the current notebook conventions, and the safe next action for running the next model.

## Current State

Current state (2026-07-01, Claude/Opus 4.8): the `medgemma_1_5_4b` 200-case Workbench run is complete, promoted, synced to GCS, and downloaded locally under `results/medgemma_1_5_4b_medical_full_200_cases/`. The active path is the LLaVA-Med SGLang notebook (`notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb`), HEAD commit `1d2a84d`. The SGLang server now LOADS and SERVES `llava_med_mistral_7b` — all config-construction shims worked. Root cause of the whole detour: the `sglang[all]` build bundles a `llava.py` written against an OLDER transformers than the pinned runtime ships, so each incompatibility surfaces one line at a time. Cleared in the `sitecustomize.py` shim (written by the §4 config cell into `~/radle_runtime_shims/` and prepended to PYTHONPATH): (1) AutoConfig registers `llava_mistral`->`LlavaMistralConfig(MistralConfig)` with a concrete `pad_token_id`; (2) `_patch_positional_string_config` wraps `CLIPVisionConfig` and `MistralConfig` so a positional model-ID string (llava.py:612 and :614) loads via `from_pretrained`; (3) `LlavaMistralConfig` backfills `vision_feature_layer`/`vision_feature_select_strategy`/`projector_hidden_act`/`multimodal_projector_bias` for HF's `LlavaMultiModalProjector` (llava.py:624); (4) `LlamaTokenizer`/`LlamaTokenizerFast` get an `image_processor` property backed by `CLIPImageProcessor.from_pretrained('openai/clip-vit-large-patch14-336')` because llava-med ships no `preprocessor_config.json`. The §4 SGLang args now include `--chat-template vicuna_v1.1` so images actually enter the prompt.

The first full 200-case run (before the chat-template/image-processor fixes) produced a VOID result set — all 200 `PARSE_FAILED`, empty raw, 1-token EOS, constant 371 prompt tokens — because images were silently dropped. That run was discarded (never promoted/synced). A new non-writing §6.5 MULTIMODAL SMOKE TEST cell now gates the full run: it sends one real image and hard-fails unless prompt_tokens jumps well above ~371 AND the completion is non-empty. The chat-template fix got images into the pipeline (smoke reached the multimodal path); the image_processor fix (commit `1d2a84d`) targets the next error, a 500 `LlamaTokenizer has no attribute image_processor`.

Immediate next step: the user is on Workbench validating `1d2a84d`. They must reload the notebook from disk in VS Code (Revert File — VS Code Jupyter does NOT auto-reload on git pull), restart kernel, re-run §4 and CONFIRM it prints `LlamaTokenizer.image_processor (CLIP) shim applied` (proof the new shim is on disk; `grep -c image_processor ~/radle_runtime_shims/sitecustomize.py` must be >=1), kill any orphaned `sglang.launch_server` process holding GPU0/port 8000 after a kernel restart (`pkill -f sglang.launch_server`), then run §6 (server) -> §6.5 (smoke, MUST pass) -> §7 (full 200).

STOPPING RULE (Opus 4.8, agreed with user): the image_processor shim is the LAST shim to stack on SGLang internals. If §6.5 reveals an 8th break in the image/forward path, STOP shimming and switch LLaVA-Med to a clean serving path — either a local copy of the model with a corrected `llava` config.json + `preprocessor_config.json` served by vLLM's mature multimodal pipeline, or Ollama (needs GGUF + mmproj conversion). Ollama was raised as a legitimate Plan B; it sidesteps the transformers-version-skew but requires converting this non-registry medical model to GGUF.

The InternVL notebook is at commit `16f6628` with the flash_attn probe fix; OctoMed is a parallel Codex-owned track (current OctoMed blocker: vLLM 0.23.0 wants `preprocessor_config.json` but OctoMed ships `processor_config.json`; model card was tested on vLLM 0.11.2/transformers 4.57.1). Do not edit the OctoMed notebook from the LLaVA track.

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
- The second SGLang server attempt failed because the launcher still calls Transformers `AutoConfig` before SGLang model dispatch; the LLaVA copy must prepend a runtime `sitecustomize.py` shim that registers `llava_mistral`.
- The third SGLang server attempt proved `LlavaConfig` is the wrong base for that shim; the shim must register `llava_mistral` as a `MistralConfig` subclass so SGLang's Mistral language model path sees fields such as `pad_token_id`.
- The LLaVA SGLang server cell must rewrite/probe the shim immediately before launch because `/home/jupyter/radle_runtime_shims/sitecustomize.py` can remain stale if Workbench runs only the server cell after a pull.
- OctoMed was explicitly user-approved as a prior isolated next-model path, but it is not the active path for the current LLaVA run.
- The active LLaVA-specific notebook copy is `notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb`, using run ID `llava_med_mistral_7b_medical_full_200_cases`.
- The OctoMed-specific notebook copy is `notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb`, using run ID `octomed_7b_medical_full_200_cases`.
- OctoMed notebook commit `65a774bd6c4be214cbcc70318ba2cbfbe7efc73e` was pushed to `origin/main`; Workbench confirmed it is using short commit `65a774b`.
- OctoMed uses vLLM with `MODEL_DTYPE="bfloat16"`, `TENSOR_PARALLEL_SIZE=2`, `GPU_MEMORY_UTILIZATION=0.8`, `MAX_MODEL_LEN=8192`, `MAX_OUTPUT_TOKENS=2048`, `OCTOMED_SAMPLING_TEMPERATURE=0.6`, and `OCTOMED_TOP_P=0.95`.
- RadLE case `156` is the only 5-image case: `156.1.png`, `156.2.png`, `156.3.png`, `156.4.png`, and `156.5.png`; the OctoMed notebook includes a non-writing case-156 smoke before the full run.
- vLLM 0.23.0 requires `--limit-mm-per-prompt` as JSON such as `{"image": 5}`; the rejected `image=5` form is a CLI syntax error, not an image-count or model-download failure.
- vLLM 0.23.0 imports `llguidance` during OpenAI server startup and depends on `llguidance >=1.7.0,<1.8.0`, `outlines_core==0.2.14`, `tilelang==0.1.9`, and `tokenspeed-mla==0.1.2`; do not remove these for the OctoMed/vLLM path.
- The InternVL-specific notebook copy is `notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb`, using run ID `internvl3_5_8b_medical_full_200_cases`; it is ready to resume from commit `16f6628` when the user returns to InternVL.
- SGLang `llava.py:612` calls `CLIPVisionConfig(mm_vision_tower)` with a positional string arg; the installed transformers enforces keyword-only args and rejects it. The LLaVA shim at commit `c00ecfd` also patches `CLIPVisionConfig.__init__` to intercept that call and use `from_pretrained` instead.
- The bundled `sglang[all]` `llava.py` targets an older transformers than the pinned runtime; serving llava-med requires a layered `sitecustomize.py` shim (config registration, positional-arg interception for CLIP/Mistral configs, LLaVA projector-field backfill, and a CLIP `image_processor` on `LlamaTokenizer`) PLUS `--chat-template vicuna_v1.1`. Current HEAD: commit `1d2a84d`.
- llava-med-v1.5-mistral-7b ships no `preprocessor_config.json`; SGLang loads a plain `LlamaTokenizer` and 500s on image requests unless an `image_processor` is attached. Its vision tower is `openai/clip-vit-large-patch14-336` (CLIP ViT-L/14, 336px).
- `build_sglang_command` in `src/radle_medical_custom_runtime.py` sets no chat template by default; LLaVA image ingestion REQUIRES `--chat-template` carrying the `<image>` placeholder, passed via `EXTRA_SERVER_ARGS`. Without it, images are silently dropped (constant ~371 prompt tokens, 1-token EOS, empty raw) and the entire run is void.
- The LLaVA notebook now has a non-writing §6.5 MULTIMODAL SMOKE TEST cell between §6 (server) and §7 (benchmark). It MUST pass (prompt_tokens >> 371 and non-empty completion) before any full run; it exists specifically to prevent void 200-case runs.
- VS Code Jupyter does NOT auto-reload an open notebook when `git pull` changes it on disk. After every pull, run Command Palette -> "Revert File" (or close/reopen) before running cells, or the kernel runs stale cell source. Proof a fix is live = the new shim's print line appears in §4 output AND `grep -c <marker> ~/radle_runtime_shims/sitecustomize.py` is >=1.
- After a kernel restart, the notebook loses its `server_process` handle, so §6's "stop previous server" cannot kill the prior SGLang server. An orphaned `sglang.launch_server` keeps holding GPU0 (~21 GB) and port 8000; kill it with `pkill -f sglang.launch_server` before starting a new server.
- InternVL notebook commit `16f6628` was pushed to `origin/main`; Workbench must pull/reload this commit before rerunning the dependency and server cells.
- InternVL uses vLLM with `MODEL_DTYPE="bfloat16"`, `MAX_MODEL_LEN=model_runtime.default_max_model_len` (8192 for this helper config), `MAX_OUTPUT_TOKENS=2048`, `TENSOR_PARALLEL_SIZE=1`, and `GPU_MEMORY_UTILIZATION=model_runtime.default_gpu_memory_utilization`.
- InternVL is ungated in `src/radle_medical_custom_runtime.py`; the HF-token cell should not prompt unless `model_runtime.requires_hf_token` is true.
- The observed InternVL startup blocker is an incompatible partial `flash_attn` package: vLLM reaches InternVL/Qwen3 model init and then fails importing `flash_attn.ops.triton.rotary`.
- Commit `16f6628` probes `flash_attn.ops.triton.rotary` during the vLLM dependency cell and uninstalls `flash-attn`/`flash_attn` only if `flash_attn` exists without that rotary module.
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
- Do not diagnose the OctoMed `llguidance` failure as a model download problem; vLLM exited before download/load while importing server modules. See Decision Log 2026-06-30.
- Do not uninstall vLLM shared dependencies such as `llguidance`, `outlines_core`, `tilelang`, or `tokenspeed-mla` to silence stale SGLang dependency warnings. See Decision Log 2026-06-30.
- Do not run the InternVL benchmark until the vLLM server reaches `/v1/models`; the latest failure occurred before readiness and before any benchmark row should be trusted. See Decision Log 2026-06-30.
- Do not leave a local untracked InternVL notebook on Workbench if it blocks `git pull`; move it aside, pull `16f6628` or newer, reload from disk, and restart the kernel. See Decision Log 2026-06-30.
- Do not run the LLaVA full benchmark until the SGLang server reaches readiness after the `CLIPVisionConfig positional-arg shim applied` message appears before `Load weight begin`. See Decision Log 2026-06-30.

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
- [x] (2026-06-30 20:22 +05:30, user on Workbench and Codex/GPT-5) Captured the second SGLang startup failure: CUDA stack and SGLang class import were fixed, but `python -m sglang.launch_server ... --model-path microsoft/llava-med-v1.5-mistral-7b` still exited because Transformers `AutoConfig` did not recognize `model_type=llava_mistral` in the child process.
- [x] (2026-06-30 20:22 +05:30, Codex/GPT-5) Patched the isolated LLaVA SGLang notebook to write `/home/jupyter/radle_runtime_shims/sitecustomize.py`, prepend that directory to `PYTHONPATH`, and run a subprocess `AutoConfig.from_pretrained(...)` probe against the actual LLaVA-Med model expecting `llava_mistral config shim OK` before server startup.
- [x] (2026-06-30 20:55 +05:30, user on Workbench and Codex/GPT-5) Captured the third SGLang startup failure: the server reached `Load weight begin`, then SGLang's Mistral path accessed `config.pad_token_id` and crashed because the shim subclassed `LlavaConfig`.
- [x] (2026-06-30 20:55 +05:30, Codex/GPT-5) Patched the isolated LLaVA SGLang notebook so the runtime shim defines `LlavaMistralConfig(MistralConfig)` and the subprocess preflight asserts `pad_token_id` exists before server startup.
- [x] (2026-06-30 21:09 +05:30, user on Workbench and Codex/GPT-5) Received another Workbench server log with the same `pad_token_id` failure, consistent with a stale shim or skipped config-cell rerun rather than a new SGLang error.
- [x] (2026-06-30 21:09 +05:30, Codex/GPT-5) Hardened the isolated LLaVA notebook: the shim function now explicitly sets `pad_token_id` from `eos_token_id` when absent or `None`, and the server cell reruns the shim/probe immediately before `start_model_server(...)`.
- [x] (2026-06-30, user on Workbench and Claude/Sonnet 4.6) Received fourth SGLang server failure: `pad_token_id` shim is now working (printed `llava_mistral config shim OK: LlavaMistralConfig llava_mistral pad_token_id= 2`) but SGLang's `llava.py:612` calls `CLIPVisionConfig(self.config.mm_vision_tower)` with a positional string, and the installed transformers enforces keyword-only args on `PretrainedConfig.__init__`, raising `ValueError: CLIPVisionConfig accepts only keyword arguments, but found 1 positional args`.
- [x] (2026-06-30, Claude/Sonnet 4.6) Extended the sitecustomize.py shim in `configure_llava_mistral_sglang_shim()` to also monkey-patch `CLIPVisionConfig.__init__`: when called with a positional string arg, calls `_orig_clip_init(self)` for default init then does `from_pretrained(args[0])` and copies `__dict__`, bypassing the keyword-only enforcement. Pushed as commit `c00ecfd`.
- [x] (2026-06-30, user on Workbench and Claude/Opus 4.8) Workbench pulled `ec8a1ac` (contains `c00ecfd`), reran config+server cells, and confirmed `CLIPVisionConfig positional-arg shim applied`. SGLang got past `llava.py:612` and crashed on the very next line, `llava.py:614`: `MistralConfig(self.config._name_or_path)` passes a positional string and hits the same `ValueError: MistralConfig accepts only keyword arguments, but found 1 positional args`.
- [x] (2026-06-30, Claude/Opus 4.8) Generalized the shim into `_patch_positional_string_config(cls)` and applied it to BOTH `CLIPVisionConfig` and `MistralConfig`, so any positional model-ID string loads via `from_pretrained`. Validated notebook + generated sitecustomize.py compile; pushed commit `b47568f`.
- [x] (2026-06-30, user on Workbench and Claude/Opus 4.8) SGLang got past 612/614 and crashed at `llava.py:624` `LlavaMultiModalProjector(config)` with `AttributeError: 'LlavaMistralConfig' object has no attribute 'vision_feature_layer'` — HF's newer projector reads LLaVA config fields a MistralConfig lacks.
- [x] (2026-06-30, Claude/Opus 4.8) Backfilled `vision_feature_layer` (from `mm_vision_select_layer`), `vision_feature_select_strategy`, `projector_hidden_act`, `multimodal_projector_bias` onto `LlavaMistralConfig`. Pushed commit `cc7c4bf` — but this NotebookEdit corrupted the notebook (dropped §6 server + §2.5 Vertex cells, duplicated §4; 20->18 cells).
- [x] (2026-06-30, user caught it + Claude/Opus 4.8) Diagnosed corruption from the actual on-disk cell order, rebuilt the notebook from the clean 20-cell `b47568f` structure and spliced in only the backfilled §4 config cell. Pushed commit `100e8d6`; verified 20 cells, §6 + §2.5 restored, no dup §4, all code compiles.
- [x] (2026-06-30, user on Workbench and Claude/Opus 4.8) With `100e8d6`, SGLang config construction fully succeeded: server LOADED, `/v1/models` answered, and the full 200-case benchmark RAN — but produced a VOID result set (200/200 `PARSE_FAILED`, empty raw, 1-token EOS, constant 371 prompt tokens). Diagnosis: images silently dropped because `build_sglang_command` set no `--chat-template`, so SGLang never injected the `<image>` token. Run discarded; not promoted/synced.
- [x] (2026-06-30, Claude/Opus 4.8) Added `--chat-template vicuna_v1.1` to the §4 LLaVA SGLang args and inserted a non-writing §6.5 MULTIMODAL SMOKE TEST cell that hard-fails unless one image expands prompt_tokens well above ~371 and returns non-empty text. Verified 21-cell structure + compile; pushed commit `35cc99f`.
- [x] (2026-06-30, user on Workbench and Claude/Opus 4.8) The smoke test reached the multimodal path (chat-template fix worked) and surfaced the next error: `500 - LlamaTokenizer has no attribute image_processor` (llava-med ships no `preprocessor_config.json`, so SGLang loaded a text-only tokenizer).
- [x] (2026-07-01, Claude/Opus 4.8) Shimmed `LlamaTokenizer`/`LlamaTokenizerFast` with an `image_processor` property (get+set) backed by `CLIPImageProcessor.from_pretrained('openai/clip-vit-large-patch14-336')`. Extracted the generated `sitecustomize.py` via ast and confirmed it compiles; pushed commit `1d2a84d`. Declared this the last SGLang-internal shim before pivoting (see Stopping Rule in Current State).
- [ ] (next, user on Workbench) Validate `1d2a84d`: reload notebook from disk in VS Code, restart kernel, confirm §4 prints `LlamaTokenizer.image_processor (CLIP) shim applied`, kill orphaned `sglang.launch_server`, run §6 -> §6.5 smoke. If smoke passes, run §7; if an 8th break appears, pivot per the Stopping Rule.
- [x] (2026-06-30 21:16 +05:30, Codex/GPT-5) Researched OctoMed against official Hugging Face/arXiv/vLLM/Qwen sources and prepared `notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb` as an isolated vLLM/Qwen2.5-VL notebook.
- [x] (2026-06-30 21:16 +05:30, Codex/GPT-5) Patched the OctoMed notebook after Workbench rejected `--limit-mm-per-prompt image=5`; vLLM requires JSON `{"image": 5}`. Added a non-writing case-156 smoke cell and pushed commit `65a774bd6c4be214cbcc70318ba2cbfbe7efc73e` to `origin/main`.
- [x] (2026-06-30 21:16 +05:30, user on Workbench and Codex/GPT-5) Workbench pulled commit `65a774b`, confirmed the OctoMed config, and got past the prior CLI parse failure, but vLLM exited before model download/load with `ModuleNotFoundError: No module named 'llguidance'`.
- [x] (2026-06-30 21:16 +05:30, Codex/GPT-5) Researched vLLM 0.23.0 requirements and determined the dependency cleanup must preserve vLLM shared dependencies (`llguidance`, `outlines_core`, `tilelang`, `tokenspeed-mla`) and reinstall pinned vLLM if its import probe fails after cleanup.
- [x] (2026-06-30 21:23 +05:30, user and Codex/GPT-5) Switched the active request to preparing `notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb` as the custom InternVL notebook; researched InternVL3.5 against model config and vLLM support, without editing first.
- [x] (2026-06-30 21:23 +05:30, Codex/GPT-5) Updated the InternVL notebook to select `internvl3_5_8b`, keep `SERVER_ENGINE="vllm"`, use `bfloat16`, use the helper default max model length, avoid HF-token prompting for ungated models, and preserve the 200-case/263-image full-run contract.
- [x] (2026-06-30 21:23 +05:30, user on Workbench and Codex/GPT-5) Workbench confirmed the InternVL config: selected model `internvl3_5_8b`, run ID `internvl3_5_8b_medical_full_200_cases`, 200 cases, 263 images, vLLM endpoint, and `MODEL_DTYPE=bfloat16`.
- [x] (2026-06-30 21:24 +05:30, user on Workbench and Codex/GPT-5) Workbench attempted the InternVL vLLM server and failed before readiness during InternVL/Qwen3 model initialization with `ModuleNotFoundError: No module named 'flash_attn.ops'` while importing `flash_attn.ops.triton.rotary`.
- [x] (2026-06-30 21:24 +05:30, Codex/GPT-5) Patched the InternVL notebook dependency cell to probe `flash_attn.ops.triton.rotary` and uninstall incompatible `flash-attn`/`flash_attn` only if the partial package would make vLLM crash; validated JSON/code cells and pushed commit `16f6628` to `origin/main`.
- [x] (2026-06-30 21:26 +05:30, user and Codex/GPT-5) User caught that this ExecPlan still compressed or omitted several failure/try details and left active runbook sections stale. Reconciled the lower sections from OctoMed to InternVL and added a model-attempt ledger under `Artifacts And Notes`.
- [ ] (next Workbench session, user/Codex) Pull latest `main` on Workbench, verify commit `c00ecfd` or newer, restart the kernel, reload/open `notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb`, rerun the config cell so `sitecustomize.py` is rewritten, rerun the server cell, confirm the log prints `CLIPVisionConfig positional-arg shim applied` before `Load weight begin`, confirm server readiness, and only then start any LLaVA benchmark run.

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

- Observation: Importing `LlavaMistralForCausalLM` from SGLang is necessary but not sufficient; server launch still asks Transformers `AutoConfig` to parse the Hugging Face config before SGLang dispatch.
  Evidence: Workbench server log printed `SGLang LLaVA-Mistral support OK: LlavaMistralForCausalLM` earlier, then the later server cell exited with `KeyError: 'llava_mistral'` and `ValueError: The checkpoint you are trying to load has model type llava_mistral but Transformers does not recognize this architecture.`
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Observation: The LLaVA-Med Mistral shim must be Mistral-based, not LLaVA-based.
  Evidence: After the `LlavaConfig` shim got past `AutoConfig`, SGLang reached `Load weight begin` and then crashed in `sglang/srt/models/llama.py` at `self.padding_idx = config.pad_token_id` with `AttributeError: 'LlavaMistralConfig' object has no attribute 'pad_token_id'.`
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Observation: Workbench can keep a stale runtime shim across notebook pulls or partial cell reruns.
  Evidence: The same `AttributeError: 'LlavaMistralConfig' object has no attribute 'pad_token_id'` appeared again after the MistralConfig fix was committed, and the server log did not show the updated preflight output with `pad_token_id=`.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Observation: vLLM 0.23.0 rejects `--limit-mm-per-prompt image=5` before model startup because the argument is parsed with `json.loads`.
  Evidence: Workbench server log ended with `api_server.py: error: argument --limit-mm-per-prompt: Value image=5 cannot be converted to <function loads ...>` and exit code 2. After commit `65a774b`, the config printed `--limit-mm-per-prompt`, `{"image": 5}` and passed that parser step.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Observation: The OctoMed `llguidance` failure is a local vLLM dependency break introduced by cleanup, not a model download failure.
  Evidence: Workbench server log at commit `65a774b` failed while importing `/opt/micromamba/lib/python3.12/site-packages/vllm/v1/structured_output/backend_guidance.py`, before any Hugging Face download or safetensors loading, with `ModuleNotFoundError: No module named 'llguidance'`.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Observation: SGLang conflict cleanup and vLLM dependency cleanup cannot share one delete list.
  Evidence: vLLM 0.23.0 requirements list `llguidance >=1.7.0,<1.8.0`, `outlines_core==0.2.14`, `tilelang==0.1.9`, and `tokenspeed-mla==0.1.2`; SGLang had complained about different versions of some of those packages, but removing them breaks vLLM.
  Date/Author: 2026-06-30, Codex/GPT-5

- Observation: The plan's active path can drift when model-specific notebooks are prepared in quick succession.
  Evidence: Before this revision, `Current State`, `Plan Of Work`, and `Validation And Acceptance` still described the OctoMed dependency repair as the active next step, while the user was actively running the InternVL notebook and asking to update the plan for that path.
  Date/Author: 2026-06-30, Codex/GPT-5

- Observation: The previous plan update failed the observable mirror check required after user-caught errors.
  Evidence: Contradicting artifact: `Documents/execplan_medical_workbench_runtime.md` had InternVL in `Current State` and `Progress`, but OctoMed in `Plan Of Work`, `Concrete Steps`, `Validation And Acceptance`, and recovery guidance. Missed verification: the update did not grep the active model name across every runbook section before finishing. User view: the user reread the chat and pointed out that multiple failures and tries were still not reflected.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Observation: After the `MistralConfig` shim fixed `pad_token_id`, SGLang's `llava.py:612` calls `CLIPVisionConfig(self.config.mm_vision_tower)` with a positional model-ID string, which newer transformers now rejects with `ValueError: CLIPVisionConfig accepts only keyword arguments`.
  Evidence: Server log showed `llava_mistral config shim OK` (previous fix worked), then reached `Load weight begin`, then crashed inside `sglang/srt/models/llava.py` at `CLIPVisionConfig(self.config.mm_vision_tower)`. This is a transformers API-break: older versions silently accepted positional args on `PretrainedConfig.__init__`, the installed version does not.
  Date/Author: 2026-06-30, user and Claude/Sonnet 4.6

- Observation: A passing SGLang server and a "complete" 200-case run can still be scientifically VOID. The benchmark reported 200/200 OK, but every cell was `PARSE_FAILED` with empty raw, 1 completion token, and a constant 371 prompt tokens — the images were never in the prompt.
  Evidence: `--chat-template` was unset, so SGLang dropped the OpenAI `image_url` payloads; a working LLaVA forward expands one image into ~576 visual tokens, which never appeared. The §6.5 smoke gate was added so this can never reach a full run again.
  Date/Author: 2026-06-30, user and Claude/Opus 4.8

- Observation: A `NotebookEdit` targeting a cell id can clobber the wrong cell after the notebook's source format/ids shift across earlier edits — here it dropped the §6 server and §2.5 Vertex cells and duplicated §4 (commit `cc7c4bf`).
  Evidence: On-disk cell-order audit showed 18 cells with §4 twice and no §6; the user spotted "5 is above 4." Fixed by rebuilding from the clean `b47568f` structure and splicing only the changed §4 (commit `100e8d6`). Lesson: after any notebook edit, verify full cell structure (count, headers, no dup/missing) before committing.
  Date/Author: 2026-06-30, user and Claude/Opus 4.8

- Observation: InternVL/vLLM reached model initialization but failed on a partial or incompatible FlashAttention package, not on dataset staging or model selection.
  Evidence: The server log entered `vllm/model_executor/models/internvl.py`, then Qwen3 rotary embedding construction, then failed importing `flash_attn.ops.triton.rotary` with `ModuleNotFoundError: No module named 'flash_attn.ops'`. The config cell had already printed `internvl3_5_8b`, 200 cases, 263 images, and `bfloat16`.
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

- Decision (superseded): Select `llava_med_mistral_7b` as the next full Workbench model.
  Rationale: This was correct before the LLaVA serving failures and before the user approved OctoMed. Current file inspection showed the helper-module roster order was `medgemma_1_5_4b`, then `llava_med_mistral_7b`, then `internvl3_5_8b`, then `octomed_7b`, and the local LLaVA model config did not mark it as gated.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision (superseded): Keep LLaVA-Med as the target and isolate its serving workaround in a copied notebook instead of pivoting to OctoMed.
  Rationale: This was a point-in-time correction before OctoMed was explicitly approved. The LLaVA-Med failure is a serving-stack issue, not a dataset/run-contract issue, so a separate copy lets the project try LLaVA-specific SGLang or native-adapter changes without contaminating the normal Workbench notebook for the other roster models.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Decision (superseded): After explicit user approval, make `octomed_7b` the active next Workbench model in an isolated OctoMed notebook.
  Rationale: This was correct for the OctoMed session. The current active request has since moved to InternVL, but keeping OctoMed in `notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb` preserves the official path and the LLaVA experiment while allowing vLLM/Qwen2.5-VL-specific settings if the user returns to OctoMed.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Decision: For OctoMed/vLLM, pass the multi-image limit as JSON and smoke-test the only 5-image RadLE case before the full run.
  Rationale: vLLM 0.23.0 parses `--limit-mm-per-prompt` with JSON loading, so `{"image": 5}` is the valid form. The value `5` comes from the dataset contract because case `156` has five images in one grouped case; it is not a download setting and not evidence of a model cap failure.
  Date/Author: 2026-06-30, Codex/GPT-5 and user

- Decision: For the OctoMed vLLM path, preserve vLLM shared dependencies and repair vLLM by reinstalling the pinned wheel if the import probe fails.
  Rationale: Workbench showed the server exits before model download/load if `llguidance` is removed. vLLM 0.23.0 depends on `llguidance`, `outlines_core`, `tilelang`, and `tokenspeed-mla`, so the cleanup cell must not delete them just because SGLang previously reported resolver conflicts.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: Make `internvl3_5_8b` the active current Workbench path in an isolated InternVL notebook.
  Rationale: The user explicitly asked to prepare `notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb` as the custom InternVL notebook. Keeping InternVL in its own copy preserves the official path, the LLaVA experiment, and the OctoMed experiment while allowing InternVL/vLLM-specific dtype, token, and dependency handling.
  Date/Author: 2026-06-30, user and Codex/GPT-5

- Decision: For InternVL/vLLM, treat missing `flash_attn.ops.triton.rotary` as an incompatible optional dependency and remove `flash-attn` only when the exact rotary probe fails.
  Rationale: vLLM failed during InternVL/Qwen3 rotary embedding setup because the installed `flash_attn` package did not expose the path vLLM attempted to import. The notebook fix is narrow: probe the path, uninstall `flash-attn`/`flash_attn` only if the partial package is present, and otherwise leave the environment alone.
  Date/Author: 2026-06-30, Codex/GPT-5

- Decision: Keep an explicit model-attempt ledger in `Artifacts And Notes` when a model path has multiple failed server tries.
  Rationale: The user needs a fresh agent to understand which failures were already tested and why a later notebook branch exists. Progress checkboxes alone were too compressed and let important evidence fall out of the active plan.
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
- v9 (2026-06-30, Codex/GPT-5): Recorded the later LLaVA SGLang startup lessons: SGLang imports are not enough because `AutoConfig` parses first, `llava_mistral` must be registered as a Mistral-derived config with a concrete `pad_token_id`, and the server cell must rewrite/probe the runtime shim immediately before launch to avoid stale Workbench state.
- v10 (2026-06-30 21:19 +05:30, Codex/GPT-5): Updated the plan for the approved OctoMed path after commit `65a774b`. Recorded that JSON `{"image": 5}` fixed the vLLM CLI syntax error, that the current blocker is missing `llguidance` from cleanup before model download/load, and that the next edit must preserve vLLM dependencies and verify/reinstall pinned vLLM.
- v11 (2026-06-30 21:26 +05:30, Codex/GPT-5): Reconciled the plan from the prior OctoMed-active state to the current InternVL-active state. Recorded commit `16f6628`, the successful InternVL config checks, the `flash_attn.ops.triton.rotary` startup failure, and the pushed dependency-cell probe/cleanup fix.
- v12 (2026-06-30 21:26 +05:30, Codex/GPT-5): Corrected the user-caught stale lower sections and expanded the failure/try history. `Plan Of Work`, `Milestones`, `Concrete Steps`, `Validation And Acceptance`, and recovery guidance now match the InternVL-active path; `Artifacts And Notes` now includes a model-attempt ledger for LLaVA, OctoMed, and InternVL.
- v13 (2026-06-30 21:26 +05:30, Codex/GPT-5): Reconciled the parent SSOT after newer LLaVA work moved the active path from InternVL back to LLaVA. Lower runbook sections now point to the `c00ecfd` CLIPVisionConfig shim retry, and the model-specific child ExecPlans are listed under `Context And Orientation`.

## Outcomes & Retrospective

Completed outcome: the Workbench medical path has produced one verified full 200-case baseline for `medgemma_1_5_4b`. The run has a model-scoped folder in GCS, a downloaded local mirror, final/private CSV with matching SHA-256, public release tables, scorer view, raw backups, repair artifacts, runtime logs, and provenance JSON.

Remaining work: retry the active LLaVA SGLang notebook from commit `c00ecfd` or newer. The next Workbench session should kill any stale server, pull latest `main`, restart/reload `notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb`, rerun the config cell so the runtime shim is rewritten, rerun the server cell, confirm `CLIPVisionConfig positional-arg shim applied` appears before `Load weight begin`, confirm server readiness, and only then proceed to benchmark execution with the same audit, repair, promotion, export, and sync guardrails. InternVL remains resumable from commit `16f6628` when the user returns to it.

Reusable lesson: for VM-hosted benchmark runs, artifact readiness should be proven by independent storage and file audits, not by notebook logs. This is broadly reusable, but no global skill update has been made. Ask the user before promoting it into a reusable skill.

## Suggested Skills By Phase

This section is a routing matrix, not a menu. Use a skill only when its trigger fires, and require a concrete receipt from that skill. For ordinary command execution, file inspection, small Python checks, `git`, and `gcloud storage`, use direct tools rather than wrapping the work in a skill.

| Workflow Gate | Trigger For Using A Skill | Skill To Use | Required Receipt / Evidence | Do Not Use It For | Activation |
| --- | --- | --- | --- | --- | --- |
| Long-lived state and handoff | The run target, dataset contract, promotion rules, repair policy, or completed-run evidence changes. | `execplan` | Updated `Current State`, `Locked Facts`, `Progress`, `Decision Log`, and `Artifacts And Notes` with exact paths, counts, hashes, and next action. | Routine status replies, simple command output, or one-off notebook cell guidance. | `auto-suggest` |
| Notebook mutation | Editing `notebooks/RadLE_Medical_Workbench_Runtime.ipynb`, `notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb`, `notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb`, `notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb`, changing defaults, adding cells, or touching notebook JSON. | `jupyter-notebook` | Notebook parses as JSON, code cells compile, config grep shows expected model/run settings, and diff is scoped to intended cells. | Purely reading a notebook or giving the user run instructions without editing. | `auto-suggest` |
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
- `notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb`: isolated LLaVA-Med SGLang experiment; active current path after commit `c00ecfd`.
- `notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb`: isolated OctoMed vLLM/Qwen2.5-VL notebook; not the active next run unless the user returns to OctoMed.
- `notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb`: isolated InternVL3.5 vLLM notebook; ready to resume from commit `16f6628` when the user returns to InternVL.
- `Documents/execplan_llava_sglang_runtime.md`: child ExecPlan for LLaVA-specific SGLang/CUDA/shim failures; use this for active LLaVA details.
- `Documents/execplan_octomed_runtime.md`: child ExecPlan for OctoMed-specific vLLM JSON image-limit and `llguidance` cleanup work.
- `Documents/execplan_internvl_runtime.md`: child ExecPlan for InternVL-specific FlashAttention rotary failure and `16f6628` recovery steps.
- `src/radle_medical_custom_runtime.py`: model roster, server startup helpers, OpenAI-compatible client setup, medical benchmark wrapper, and CSV validation helpers.
- `src/radle_benchmark.py`: shared benchmark/audit/repair/promote/export logic.
- `Documents/runtime_provenance_contract_radle_medical.md`: internal contract for dataset snapshot, Workbench host, model roster, and provenance expectations; useful but partly stale and should be verified.
- `results/medgemma_1_5_4b_medical_full_200_cases/`: local mirror of the completed baseline; do not commit this data.

The Workbench VM used for the baseline was `medical-master-radfm` in GCP project `crashlab-synthetic`, zone `northamerica-northeast2-b`, with `2 x NVIDIA L4`. The baseline server used vLLM for `google/medgemma-1.5-4b-it` with dtype `bfloat16`.

## Plan Of Work

First, orient against current files. Read `notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb`, `Documents/execplan_llava_sglang_runtime.md`, the model roster in `src/radle_medical_custom_runtime.py`, and `git status --short --branch`. Expect unrelated dirty files in this checkout; do not revert them.

Second, keep `llava_med_mistral_7b` as the active current model because the parent SSOT and latest Workbench failure are on the LLaVA SGLang path. Preserve the LLaVA run contract: model-scoped run ID `llava_med_mistral_7b_medical_full_200_cases`, 200 cases, 263 image files, SGLang, `float16`, max model length 4096 in the notebook, max output tokens 2048, `TEST_LIMIT=None`, and `RESUME=True`.

Third, for the current blocker, do not edit the benchmark wrapper or dataset logic. The pushed notebook fix lives in `configure_llava_mistral_sglang_shim()`: it registers `llava_mistral` as a Mistral-derived config, ensures `pad_token_id`, and monkey-patches `CLIPVisionConfig.__init__` so SGLang's positional `CLIPVisionConfig(mm_vision_tower)` call loads the model ID through `from_pretrained`. If a later Workbench run still fails, inspect the new SGLang log and patch only the narrow shim/dependency behavior that explains that log.

Fourth, validate locally after any future edit. Parse the LLaVA notebook JSON, compile its code cells, compile the helper modules, and run a focused config/shim-string extraction. Do not start a real model server locally.

Fifth, commit and push only the intended LLaVA notebook fix and intentional documentation updates. Because the Workbench run uses `git pull`, any future fix must be pushed before the user restarts the Workbench kernel.

Sixth, give the user an exact Workbench runbook. It should include killing any stale server, pulling latest repo, restarting the kernel, reloading the LLaVA notebook from disk, rerunning the config cell so `sitecustomize.py` is rewritten, starting SGLang, confirming the log contains `CLIPVisionConfig positional-arg shim applied` before `Load weight begin`, confirming server readiness, running the benchmark only after readiness, auditing, inspecting repair targets before repair, promoting/exporting/syncing only after zero repair targets or a documented narrow cleanup, and stopping the server.

## Milestones

Milestone 1, LLaVA notebook readiness, uses `jupyter-notebook`: The LLaVA notebook selects `llava_med_mistral_7b`, uses SGLang and float16, repairs the CUDA-13 torch/torchvision/torchaudio stack, rewrites the child-process `sitecustomize.py` shim, and contains both the MistralConfig/pad_token_id shim and CLIPVisionConfig positional-arg shim. Evidence is a local notebook parse/config/shim check and a focused diff or commit.

Milestone 2, repository handoff, uses `execplan`: The notebook change, this plan, and the LLaVA child plan are reconciled so a fresh session can understand the completed baseline, OctoMed detour, InternVL resumable state, active LLaVA target, and current CLIPVisionConfig shim blocker. Evidence is `git diff --check`, status, and a commit on `main`.

Milestone 3, live LLaVA Workbench run, uses `none`: The user runs the LLaVA SGLang notebook on the Workbench VM, confirms the config, starts SGLang, confirms the shim messages and endpoint readiness, completes the benchmark with resume enabled, and gets 200 validated output rows. Evidence is audit output plus files in the run folder, not logs alone.

Milestone 4, completed-run verification, uses `data-analytics:analyze-data-quality` optionally: Verify final/private CSV rows and unique cases, public summary, manifest hash, GCS object presence, and local download if requested. Evidence is literal row counts, SHA-256, and GCS/local paths.

## Concrete Steps (Commands)

From repo root, inspect state:

    git status --short --branch
    git rev-parse --short HEAD

Expected on 2026-06-30 after the LLaVA CLIPVisionConfig shim fix:

    ## main...origin/main
    c00ecfd

There may be unrelated modified and untracked files. Do not revert user work.

Inspect roster, LLaVA defaults, and shim terms:

    rg -n "MEDICAL_CUSTOM_RUNTIME_MODELS|name=|llava_med_mistral_7b|SELECTED_MODEL_NAME|RUN_LABEL_BASE|RUN_ID|TEST_LIMIT|RESUME|MAX_OUTPUT_TOKENS|MODEL_DTYPE|MAX_MODEL_LEN|SERVER_ENGINE|sglang|sitecustomize|llava_mistral|MistralConfig|pad_token_id|CLIPVisionConfig|positional-arg shim" src/radle_medical_custom_runtime.py notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb

Expected current model names include:

    medgemma_1_5_4b
    llava_med_mistral_7b
    internvl3_5_8b
    octomed_7b

Expected LLaVA-specific facts include:

    selected_model: llava_med_mistral_7b
    model_scoped_run_id: llava_med_mistral_7b_medical_full_200_cases
    server_engine: sglang
    model_dtype: float16
    max_model_len: 4096
    llava_mistral MistralConfig shim
    pad_token_id preflight
    CLIPVisionConfig positional-arg shim

Validate Python modules after notebook edits:

    py -3.11 -m py_compile src/radle_medical_custom_runtime.py src/radle_benchmark.py

Expected: no output and exit code 0.

Validate LLaVA notebook JSON and code-cell compilation:

    py -3.11 -c "import ast,json,pathlib; nb=json.loads(pathlib.Path('notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb').read_text(encoding='utf-8-sig')); cells=[c for c in nb['cells'] if c.get('cell_type')=='code']; [compile(''.join(c.get('source',[])), f'llava_cell_{i}', 'exec') for i,c in enumerate(cells,1)]; print('compiled LLaVA code cells', len(cells))"

Expected: prints `compiled LLaVA code cells` followed by a positive count.

Extract shim guardrails after the fix:

    py -3.11 -c "import json,pathlib; p=pathlib.Path('notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb'); src='\n'.join(''.join(c.get('source',[])) for c in json.loads(p.read_text(encoding='utf-8-sig'))['cells'] if c.get('cell_type')=='code'); [print(term, term in src) for term in ['llava_mistral','MistralConfig','pad_token_id','CLIPVisionConfig','positional-arg shim applied','SELECTED_MODEL_NAME = \"llava_med_mistral_7b\"']]"

Expected: all six checks print `True`.

When the user reruns on Workbench, the config/server setup should rewrite the shim before server launch. Useful log evidence is:

    SGLang llava_mistral AutoConfig shim: /home/jupyter/radle_runtime_shims/sitecustomize.py
    CLIPVisionConfig positional-arg shim applied
    llava_mistral config shim OK: LlavaMistralConfig llava_mistral pad_token_id= 2

Expected: the CLIP shim message appears before any `Load weight begin` line in the server log.

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

Local acceptance for the active LLaVA shim repair:

- The LLaVA SGLang notebook parses as JSON and all code cells compile.
- `src/radle_medical_custom_runtime.py` and `src/radle_benchmark.py` compile.
- A focused grep or notebook inspection shows `SELECTED_MODEL_NAME = "llava_med_mistral_7b"`, model-scoped `RUN_ID`, `TEST_LIMIT = None`, `RESUME = True`, expected 200 cases, expected 263 image files, `MAX_OUTPUT_TOKENS = 2048`, SGLang, and `float16`.
- The shim logic registers `llava_mistral`, derives from `MistralConfig`, ensures `pad_token_id`, and patches `CLIPVisionConfig.__init__` for positional model-ID strings.
- The server cell rewrites/probes the runtime shim before `start_model_server(...)`.
- `git diff --check` is clean.
- The completed MedGemma result folder is not modified.

Live acceptance for the active LLaVA run:

- The notebook prints the current repo commit after pull.
- The config printout shows `llava_med_mistral_7b`, `medical_full_200_cases`, model-scoped run ID, full mode, expected 200 cases, expected 263 image files, `MAX_OUTPUT_TOKENS=2048`, SGLang, and `float16`.
- The config/server setup prints `CLIPVisionConfig positional-arg shim applied` before `Load weight begin`.
- The server cell reaches an OpenAI-compatible readiness endpoint before the benchmark cell runs.
- The benchmark cell validates exactly 200 output rows.
- The audit reports 200 rows, 200 unique cases, no missing or extra case IDs, and zero repair targets before promotion. If repair targets exist, inspect them before repair.
- Promotion/export/sync runs only after the final audit is clean or after an explicitly recorded, narrow cleanup decision.
- Completed-run claims are verified by files: final manifest, final CSV row count, public summary, GCS object listing, and local mirror when requested.

## Idempotence And Recovery

The notebook setup cells are intended to be rerunnable. If Workbench asks whether to reload from disk after `git pull`, reload from disk and do not overwrite a newer file.

If Workbench has a stale LLaVA server process, kill it before rerunning the server cell. A stale server can keep old shim behavior alive even after `git pull`.

After pulling commit `c00ecfd` or newer, reload the LLaVA notebook from disk and restart the kernel. Rerun the config cell so `/home/jupyter/radle_runtime_shims/sitecustomize.py` is rewritten with the CLIPVisionConfig patch before the server starts.

If the log does not show `CLIPVisionConfig positional-arg shim applied`, do not continue to benchmark execution. Reload, restart, rerun the config cell, and inspect the server log again.

If the Jupyter session is disposed but a server process is still running, reconnect the kernel and test the endpoint before restarting the server. If no server process remains, rerun the server cell before rerunning the benchmark cell.

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

Model-attempt ledger as of 2026-06-30 21:26 +05:30:

    1. MedGemma baseline succeeded.
       Notebook path: notebooks/RadLE_Medical_Workbench_Runtime.ipynb
       Model: medgemma_1_5_4b / google/medgemma-1.5-4b-it
       Engine/dtype: vLLM / bfloat16
       Result: 200-case run completed, repaired exact "I don't know" rows as abstentions, promoted, exported, synced, and locally verified.

    2. LLaVA-Med vLLM path failed before server readiness.
       Notebook path: notebooks/RadLE_Medical_Workbench_Runtime.ipynb at the time
       Model: llava_med_mistral_7b / microsoft/llava-med-v1.5-mistral-7b
       Engine/dtype: vLLM / float16
       Try: selected LLaVA-Med as the next roster model after MedGemma.
       Failure: vLLM 0.23.0 exited before readiness because Transformers did not recognize `model_type=llava_mistral`.
       Consequence: do not retry LLaVA-Med under the pinned vLLM runtime without a model-adapter change.

    3. LLaVA-Med SGLang copy failed first on a CUDA vision stack mismatch.
       Notebook path: notebooks/RadLE_Medical_Workbench_LLaVA_SGLang_Runtime.ipynb
       Try: isolated LLaVA into an SGLang notebook copy.
       Failure: SGLang import reached `torchvision.io.decode_jpeg`, then failed because PyTorch reported CUDA 13.0 while torchvision was compiled for CUDA 12.9.
       Patch tried: uninstall vLLM in the SGLang path and force reinstall `torch==2.11.0`, `torchvision==0.26.0`, and `torchaudio==2.11.0` from the official `cu130` PyTorch wheel index.

    4. LLaVA-Med SGLang copy then failed because server launch still used Transformers AutoConfig.
       Try: after the CUDA stack fix, probe `sglang.srt.models.llava.LlavaMistralForCausalLM`.
       Success within try: SGLang class import succeeded.
       Failure: `python -m sglang.launch_server ... --model-path microsoft/llava-med-v1.5-mistral-7b` still called Transformers `AutoConfig` and failed with `KeyError`/`ValueError` for `llava_mistral`.
       Patch tried: write `/home/jupyter/radle_runtime_shims/sitecustomize.py`, prepend it to `PYTHONPATH`, register `llava_mistral`, and run a subprocess `AutoConfig.from_pretrained(...)` probe before server startup.

    5. LLaVA-Med SGLang copy then failed after weight loading began because the first shim used the wrong config base.
       Try: sitecustomize registered `llava_mistral` as a LLaVA-derived config.
       Failure: server reached `Load weight begin`, then SGLang's Mistral path accessed `config.pad_token_id` and crashed with `AttributeError: 'LlavaMistralConfig' object has no attribute 'pad_token_id'`.
       Patch tried: change the shim to subclass `MistralConfig`, assert `pad_token_id` exists, and later set `pad_token_id` from `eos_token_id` if absent.
       Extra Workbench lesson: the same `pad_token_id` error recurred when Workbench appeared to be using a stale shim, so the server cell now rewrites/probes the shim immediately before launch.

    6. OctoMed first failed on vLLM CLI syntax, not image-count capacity or model download.
       Notebook path: notebooks/RadLE_Medical_Workbench_OctoMed_Runtime.ipynb
       Model: octomed_7b / OctoMed/OctoMed-7B
       Engine/dtype: vLLM / bfloat16
       Try: pass one grouped RadLE case at a time, allowing up to five images because the dataset has one 5-image grouped case, case 156.
       Failure: `--limit-mm-per-prompt image=5` exited with `api_server.py: error: argument --limit-mm-per-prompt: Value image=5 cannot be converted to <function loads ...>`.
       Patch tried: use JSON form `--limit-mm-per-prompt '{"image": 5}'` and add a non-writing case-156 smoke before the full benchmark.

    7. OctoMed then failed because cleanup removed a vLLM dependency before model download/load.
       Try: Workbench pulled commit `65a774b`; config printed `octomed_7b`, 200 cases, 263 images, `bfloat16`, tensor parallel size 2, `MAX_MODEL_LEN=8192`, and JSON `{"image": 5}`.
       Failure: vLLM got past the CLI parser but exited during OpenAI server imports with `ModuleNotFoundError: No module named 'llguidance'`.
       Root cause: the dependency cleanup list removed packages such as `llguidance`, `tilelang`, `tokenspeed-mla`, and `outlines` while trying to clear stale SGLang conflicts; vLLM 0.23.0 itself requires the shared vLLM packages.
       Consequence: OctoMed fix, if resumed, must preserve vLLM shared dependencies and reinstall/probe pinned vLLM rather than treating this as model download trouble.

    8. InternVL became the active path and first failed on a partial FlashAttention package.
       Notebook path: notebooks/RadLE_Medical_Workbench_Internvl_Runtime.ipynb
       Model: internvl3_5_8b / OpenGVLab/InternVL3_5-8B
       Engine/dtype: vLLM / bfloat16
       Try: Workbench confirmed `internvl3_5_8b`, run ID `internvl3_5_8b_medical_full_200_cases`, 200 cases, 263 images, vLLM endpoint, and `MODEL_DTYPE=bfloat16`.
       Failure: server reached InternVL/Qwen3 model initialization, then failed importing `flash_attn.ops.triton.rotary` with `ModuleNotFoundError: No module named 'flash_attn.ops'`.
       Patch tried: commit `16f6628` probes `flash_attn.ops.triton.rotary` during the dependency cell and uninstalls `flash-attn`/`flash_attn` only if the installed package is partial/incompatible.

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

OctoMed Workbench config transcript from commit `65a774b`:

    Selected model: octomed_7b
    Model ID: OctoMed/OctoMed-7B
    Run label base: medical_full_200_cases
    Model-scoped run ID: octomed_7b_medical_full_200_cases
    Expected cases this run: 200
    Expected image files this run: 263
    Multi-image grouped cases: 50
    Max images per grouped case: 5
    Tensor parallel size: 2
    GPU memory utilization: 0.8
    Max model len: 8192
    Model dtype: bfloat16
    Extra server args: ['--dtype', 'bfloat16', '--limit-mm-per-prompt', '{"image": 5}', '--mm-processor-kwargs', '{"min_pixels": 262144, "max_pixels": 262144}']

OctoMed server failure transcript from commit `65a774b`:

    $ /opt/micromamba/bin/python3 -m vllm.entrypoints.openai.api_server ... --limit-mm-per-prompt {"image": 5} ...
    ModuleNotFoundError: No module named 'llguidance'

vLLM dependency research note for the OctoMed fix:

    vLLM 0.23.0 requirements include llguidance >=1.7.0,<1.8.0 and outlines_core==0.2.14 in common requirements.
    vLLM 0.23.0 CUDA requirements include tilelang==0.1.9 and tokenspeed-mla==0.1.2.
    Therefore the OctoMed dependency cleanup must not remove llguidance, outlines_core, tilelang, or tokenspeed-mla.

InternVL notebook local validation transcript from commit `16f6628`:

    compiled code cells 16
    src/radle_medical_custom_runtime.py and src/radle_benchmark.py compiled with py -3.11 -m py_compile
    notebook title: RadLE Medical Workbench InternVL Runtime
    server_engine: vllm
    selected_model: internvl3_5_8b
    model_scoped_run_id: internvl3_5_8b_medical_full_200_cases
    model_dtype: bfloat16
    max_model_len: model_runtime.default_max_model_len
    dependency probe: flash_attn.ops.triton.rotary

InternVL Workbench config transcript before the FlashAttention fix:

    Selected model: internvl3_5_8b
    Run label base: medical_full_200_cases
    Model-scoped run ID: internvl3_5_8b_medical_full_200_cases
    Test limit: full
    Expected cases this run: 200
    Expected image files this run: 263
    Multi-image grouped cases: 50
    Dataset GCS URI: gs://radle-medical-data-toronto/datasets/radle-v2-frozen-2026-06-29/RadLE v2 Master Data
    Run folder: /home/jupyter/radle_dataset/RadLE v2 Dataset/Runs/internvl3_5_8b_medical_full_200_cases
    Raw results CSV: /home/jupyter/radle_dataset/RadLE v2 Dataset/Runs/internvl3_5_8b_medical_full_200_cases/raw/results.csv
    Max output tokens: 2048
    Model dtype: bfloat16
    Endpoint: http://127.0.0.1:8000/v1

InternVL server failure transcript before commit `16f6628`:

    Starting vllm server for internvl3_5_8b...
    Server process started. Log path: /home/jupyter/internvl3_5_8b_vllm_server.log
    ModuleNotFoundError: No module named 'flash_attn.ops'

InternVL dependency fix note:

    Commit 16f6628 probes importlib.util.find_spec('flash_attn.ops.triton.rotary') after vLLM install/import.
    If flash_attn exists but that rotary path is missing, the notebook uninstalls flash-attn and flash_attn, then prints the post-cleanup flash_attn spec.
    The intent is to let vLLM use its fallback path instead of crashing on a partial FlashAttention package.

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

OctoMed vLLM dependency expectations:

- `vllm` server startup imports structured-output backends before model download/load.
- `llguidance` must be importable for vLLM 0.23.0 OpenAI server startup.
- `outlines_core`, `tilelang`, and `tokenspeed-mla` are also vLLM 0.23.0 dependencies in this runtime family.
- The OctoMed setup cell may remove stale `sglang` if needed, but must not share the LLaVA/SGLang cleanup list.

InternVL vLLM dependency expectations:

- `OpenGVLab/InternVL3_5-8B` is served through the vLLM OpenAI-compatible path with `--trust-remote-code` supplied by `src/radle_medical_custom_runtime.py` when `needs_trust_remote_code=True`.
- InternVL3.5 uses `bfloat16`; keep the notebook's `BF16_MODELS` entry for `internvl3_5_8b`.
- A partial `flash_attn` install can be worse than no `flash_attn` install for this runtime because vLLM may attempt `flash_attn.ops.triton.rotary` and crash before readiness.
- The current InternVL notebook fix removes `flash-attn` only when that exact rotary module is absent; do not broaden this cleanup without a new server log that proves the next failure.
