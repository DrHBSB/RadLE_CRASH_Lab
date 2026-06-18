# RadLE CRASH Lab

This repository tracks RadLE notebook and code changes. Google Drive remains the source of truth for the confidential image dataset and benchmark result files.

## Working Model

- Use Colab as the execution environment.
- Keep images and full benchmark outputs in Google Drive.
- Use GitHub for notebook/code versioning.
- Do not commit confidential datasets, full result CSVs, or local image exports.

## Current Notebook

- `notebooks/RadLE_v1_5_Morning.ipynb`
- Colab: https://colab.research.google.com/github/DrHBSB/RadLE_CRASH_Lab/blob/main/notebooks/RadLE_v1_5_Morning.ipynb
- `src/radle_benchmark.py`

The notebook mounts Google Drive and currently reads/writes under:

- `/content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/`

In Colab, the notebook clones or updates this GitHub repo under `/content/RadLE_CRASH_Lab` so it can import `src/radle_benchmark.py`. Because this repo is private, add a Colab secret named `GITHUB_TOKEN` if the clone step needs GitHub authentication.

## Debug Workflow

1. Pull the latest GitHub version in Colab before editing.
2. Run the notebook in Colab, starting with `test_limit=1`.
3. If something fails, share the traceback, push the updated notebook, or provide a Drive link to the relevant result file.
4. Keep image-specific debugging limited to the affected case/image when possible.

## Code Structure

Keep the notebook as the Colab runner. The reusable benchmark logic lives in `src/radle_benchmark.py`, which works with Google Drive because Colab exposes mounted Drive as ordinary filesystem paths.

## Experimental Medical Custom Runtime

- Notebook: `notebooks/RadLE_Medical_Custom_Runtime.ipynb`
- Colab: https://colab.research.google.com/github/DrHBSB/RadLE_CRASH_Lab/blob/main/notebooks/RadLE_Medical_Custom_Runtime.ipynb
- Helper module: `src/radle_medical_custom_runtime.py`

This path is separate from the official benchmark roster. It is for GCP-backed
custom Colab runtimes that serve one local OpenAI-compatible medical model at a
time with vLLM or SGLang, then reuse the standard RadLE CSV schema.

Current experimental medical models:

- `medgemma_1_5_4b` -> `google/medgemma-1.5-4b-it`
- `llava_med_mistral_7b` -> `microsoft/llava-med-v1.5-mistral-7b`
- `internvl3_5_8b` -> `OpenGVLab/InternVL3_5-8B`

Run sequence:

1. Attach a GPU custom runtime, preferably starting with an L4/G2 runtime.
2. Open the experimental Colab link.
3. Rerun the first code cell to clone or pull the latest GitHub code, then rerun dependency/import cells.
4. Select one `SELECTED_MODEL_NAME`.
5. Start with `TEST_LIMIT=1`, then `TEST_LIMIT=3` or `TEST_LIMIT=5`.
6. Stop the local model server or restart the runtime before switching models.

The notebook routes Hugging Face, Transformers, vLLM, and pip caches under
`/content/radle_runtime_cache` so model weights do not fill the custom runtime's
root disk. If your custom runtime image already includes vLLM or SGLang, set
`INSTALL_SERVER_PACKAGES = False` in the dependency cell.

Colab Enterprise does not support `google.colab.drive.mount()`. For Enterprise,
mount or copy the RadLE dataset to a Cloud Storage/local path and set
`DATASET_ROOT_OVERRIDE` in cell 4, or set `RADLE_DATASET_ROOT`, to the folder
that contains `RadLE v2 Master Data`. Standard Colab can still use the default
Drive path.
