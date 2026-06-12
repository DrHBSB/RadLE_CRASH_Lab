# Extract RadLE Benchmark Logic Into a Python Module

This work makes RadLE easier to debug and extend without changing how the benchmark is run in Colab. After the change, the notebook remains the Colab runner that mounts Google Drive, loads secrets, chooses Drive input/output paths, and displays results. The reusable benchmark logic moves into `src/radle_benchmark.py`, which can read and write Google Drive paths because Colab exposes mounted Drive as ordinary filesystem paths under `/content/drive/...`.

## Current State

As of 2026-06-12T14:57:33+05:30, implementation is complete and awaiting commit/push. `src/radle_benchmark.py` exists, the notebook has been reduced to 5 Colab runner cells, the original prompt text was verified to match exactly, and syntax/notebook checks passed. The next action is to stage the intended files, commit `Extract RadLE benchmark module`, push to `origin/main`, and confirm the working tree is clean.

## Locked Facts

- Google Drive remains the source of truth for images and result CSVs.
- GitHub remains the source of truth for notebook/code only.
- Drive paths such as `/content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/...` work in `.py` code when Colab has mounted Drive.
- The notebook currently runs `test_limit=1` and writes `RadLE_v1.5_RSNA.csv` plus derived scorer CSVs to Drive.
- The original notebook prompt is preserved exactly in `src/radle_benchmark.py`; verification printed `prompt_same True`.

## Do Not Revisit

- Do not move image data or full outputs into GitHub; closed by user agreement and README workflow.
- Do not add a mixed GitHub/Drive artifact sync layer in this pass; user asked to keep the workflow simple.
- Do not redesign model selection or output schema in this pass; this is behavior-preserving extraction.

## Progress

- [x] 2026-06-12T14:57:33+05:30, Codex GPT-5: Inspected notebook cells and confirmed the refactor target.
- [x] 2026-06-12T14:57:33+05:30, Codex GPT-5: Add `src/radle_benchmark.py` with the current constants, prompt, helper functions, `run_benchmark`, and scorer-view helper.
- [x] 2026-06-12T14:57:33+05:30, Codex GPT-5: Rewrite the notebook as a Colab runner that mounts Drive, loads OpenRouter credentials, imports the module, sets Drive paths, runs the benchmark, and displays scorer view.
- [x] 2026-06-12T14:57:33+05:30, Codex GPT-5: Validate Python syntax, notebook JSON, and expected Drive path usage.
- [ ] 2026-06-12T14:57:33+05:30, Codex GPT-5: Commit and push the refactor to `main`.

## Surprises & Discoveries

- 2026-06-12T14:57:33+05:30, Codex GPT-5: The notebook already uses mounted Drive paths directly; no Google Drive API code is required inside the module.
- 2026-06-12T14:57:33+05:30, Codex GPT-5: Local `exec()` of the module failed because the local Windows Python lacks `pandas`; `python -m py_compile src\radle_benchmark.py` still validated syntax successfully.
- 2026-06-12T14:57:33+05:30, Codex GPT-5: An untracked `radle_api_keys.env` file exists in the repo root; it was not read or staged, and `.gitignore` now ignores `*.env`.

## Decision Log

- 2026-06-12T14:57:33+05:30, Codex GPT-5: Keep work on `main` rather than creating a feature branch because this is a private, early repo and the user explicitly asked for a simple workflow.
- 2026-06-12T14:57:33+05:30, Codex GPT-5: The notebook owns Colab-only concerns (`google.colab.drive`, `google.colab.userdata`, `sys.path`, `display`); the module owns benchmark logic and plain filesystem I/O.
- 2026-06-12T14:57:33+05:30, Codex GPT-5: The notebook includes an optional `GITHUB_TOKEN` Colab secret path for private-repo clone authentication; if the repo is already cloned in `/content/RadLE_CRASH_Lab`, it uses `git pull --ff-only`.

## Revision Notes

- 2026-06-12T14:57:33+05:30, Codex GPT-5: Initial plan created from the live notebook state and user preference for a simple Colab + Drive + GitHub workflow.

## Outcomes & Retrospective

Implementation complete pending commit and push. Verified `py_compile` succeeds, notebook JSON parses as nbformat 4 with 5 cells, the notebook imports `create_scorer_view` and `run_benchmark`, Drive paths are still present, `TEST_LIMIT = 1` is preserved, and the extracted prompt matches the original notebook prompt.

## Suggested Skills By Phase

- Planning: `execplan`, activation `manual`, used because AGENTS.md requires an ExecPlan for significant refactors.
- Implementation: `none`, activation `none`; this is plain Python and notebook JSON editing.
- Verification: `none`, activation `none`; use `py_compile`, notebook JSON parsing, and local git checks.

## Milestones

### Milestone 1: Module Extraction

Create `src/radle_benchmark.py` containing the existing benchmark constants, `MODELS`, `PROMPT`, helper functions, `run_benchmark`, and a new `create_scorer_view(raw_csv)` helper equivalent to the current scorer cell. The module must not import `google.colab` or hard-code Drive paths. Success is `python -m py_compile src/radle_benchmark.py` exiting with code 0.

### Milestone 2: Notebook Runner Rewrite

Replace duplicated benchmark logic in `notebooks/RadLE_v1_5_Morning.ipynb` with compact Colab runner cells: mount Drive, load API key, clone/path setup if needed, import module, create OpenAI client, set Drive paths, run `run_benchmark(..., test_limit=1)`, and run/display `create_scorer_view`. Success is valid notebook JSON and visible Drive path strings preserved in execution cells.

### Milestone 3: Commit and Push

Stage only `Documents/execplan_extract_benchmark_module.md`, `src/radle_benchmark.py`, `notebooks/RadLE_v1_5_Morning.ipynb`, `.gitignore`, and `README.md`. Commit with `Extract RadLE benchmark module` and push to `origin/main`. Success is `git status --short --branch` showing `main...origin/main` with no pending changes after push.
