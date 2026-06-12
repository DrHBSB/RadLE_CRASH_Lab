# RadLE CRASH Lab

This repository tracks RadLE notebook and code changes. Google Drive remains the source of truth for the confidential image dataset and benchmark result files.

## Working Model

- Use Colab as the execution environment.
- Keep images and full benchmark outputs in Google Drive.
- Use GitHub for notebook/code versioning.
- Do not commit confidential datasets, full result CSVs, or local image exports.

## Current Notebook

- `notebooks/RadLE_v1_5_Morning.ipynb`
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
