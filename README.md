# RadLE CRASH Lab

This repository tracks RadLE notebook and code changes. Google Drive remains the source of truth for the confidential image dataset and benchmark result files.

## Working Model

- Use Colab as the execution environment.
- Keep images and full benchmark outputs in Google Drive.
- Use GitHub for notebook/code versioning.
- Do not commit confidential datasets, full result CSVs, or local image exports.

## Current Notebook

- `notebooks/RadLE_v1_5_Morning.ipynb`

The notebook mounts Google Drive and currently reads/writes under:

- `/content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/`

## Debug Workflow

1. Pull the latest GitHub version in Colab before editing.
2. Run the notebook in Colab, starting with `test_limit=1`.
3. If something fails, share the traceback, push the updated notebook, or provide a Drive link to the relevant result file.
4. Keep image-specific debugging limited to the affected case/image when possible.

## RadLE v2 Direction

Keep the notebook as the Colab runner. Move reusable benchmark logic into Python modules over time so changes are easier to review, test, and debug.
