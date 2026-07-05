# RadLE Medical Runtime Provenance Contract

Status: active working contract
Created: 2026-06-30
Project: RadLE v2 medical Workbench path

This document defines the auditable runtime contract for the experimental RadLE
medical model path. Its purpose is to make a benchmark run reproducible enough
to inspect later: the data snapshot, notebook entrypoint, runtime host, model
adapter path, and output expectations must all be explicit before a run is
treated as scientific evidence.

This is not the official RadLE benchmark contract. The official benchmark path
remains separate and should not be changed by medical-runtime experiments.

## Scope

In scope:

- The frozen RadLE v2 image corpus staged to private Google Cloud Storage.
- The Vertex AI Workbench / Colab Enterprise notebook runtime used for medical
  model experiments.
- The medical helper module that serves one local OpenAI-compatible model at a
  time and reuses the standard RadLE CSV schema.
- The provenance fields that must be captured with every run output.

Out of scope:

- Public release packaging.
- Any mutation of the official `src/radle_benchmark.py` benchmark semantics.
- Any claim that a model is leaderboard-ready before its adapter/runtime path
  has a run manifest and scorer-facing output.

## Dataset Snapshot Contract

The medical Workbench notebook must read from this frozen dataset snapshot
unless a future contract explicitly replaces it.

| Field | Value |
| --- | --- |
| Snapshot ID | `radle-v2-frozen-2026-06-29` |
| GCP project | `crashlab-synthetic` |
| Bucket | `gs://radle-medical-data-toronto` |
| Bucket region | `NORTHAMERICA-NORTHEAST2` |
| Expanded dataset | `gs://radle-medical-data-toronto/datasets/radle-v2-frozen-2026-06-29/RadLE v2 Master Data` |
| Source archive | `gs://radle-medical-data-toronto/source_archives/radle-v2-frozen-2026-06-29/RadLE v2 Master Data-20260629T202835Z-3-001.zip` |
| Provenance manifest | `gs://radle-medical-data-toronto/metadata/radle-v2-frozen-2026-06-29/transfer_manifest.json` |
| File manifest | `gs://radle-medical-data-toronto/metadata/radle-v2-frozen-2026-06-29/file_manifest.csv` |

The local mirror of the provenance files is:

`C:\Users\thehb\Documents\RadLE v2\results\dataset_manifests\radle-v2-frozen-2026-06-29\`

The transfer manifest records:

| Check | Value |
| --- | --- |
| Image file count | `263` |
| Extension counts | `134 .jpg`, `129 .png` |
| Expanded dataset bytes | `58,131,904` |
| Source ZIP bytes | `58,197,140` |
| Source ZIP SHA-256 | `6b4d4c1f04660579689c380905c93ab1ea53724a0e335013229fbbb94cd0a47b` |
| Manifest creation time | `2026-06-29T20:33:55.623824+00:00` |

Verification performed while creating this document:

- Local `file_manifest.csv` row count: `263`
- Live GCS image-object count under the expanded dataset prefix: `263`
- Live bucket location: `NORTHAMERICA-NORTHEAST2`
- Live source archive object size: `58,197,140` bytes

The SHA-256 value is recorded in the transfer manifest. If the ZIP object is
downloaded again, verify the local file hash against that value before using it
as a replacement source archive.

## Notebook And Code Contract

| Component | Contract |
| --- | --- |
| Workbench notebook | `notebooks/RadLE_Medical_Workbench_Runtime.ipynb` |
| Colab notebook | `notebooks/RadLE_Medical_Custom_Runtime.ipynb` |
| Helper module | `src/radle_medical_custom_runtime.py` |
| Official benchmark module | `src/radle_benchmark.py` |
| Dataset environment variable | `RADLE_DATASET_GCS_URI` |
| Snapshot environment variable | `RADLE_DATASET_SNAPSHOT_ID` |
| Runtime root override | `RADLE_RUNTIME_ROOT` |
| Runtime cache override | `RADLE_RUNTIME_CACHE_ROOT` |

The Workbench notebook is the expected entrypoint for this contract. It sets the
snapshot ID to `radle-v2-frozen-2026-06-29` and defaults
`RADLE_DATASET_GCS_URI` to the frozen GCS prefix above.

The Colab notebook remains the standard custom-runtime notebook. Workbench-only
behavior belongs in `RadLE_Medical_Workbench_Runtime.ipynb`, not in the Colab
notebook.

At run time, record:

- Git branch and commit used by the notebook.
- Whether the working tree was clean when the run started.
- The notebook path and cell version used for execution.
- The resolved dataset root after GCS copy or mount.
- The exact `RADLE_DATASET_GCS_URI` and `RADLE_DATASET_SNAPSHOT_ID`.

Current local checkout observed while creating this document:

| Field | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `c778b15` |
| Working tree | dirty; contains existing modified and untracked files |

Because the working tree is dirty, this current checkout state is not by itself
a reproducible run identifier. A benchmark run should record both the commit and
any local patch/notebook state used.

## Workbench Runtime Contract

Current Workbench instance verified on 2026-06-30:

| Field | Value |
| --- | --- |
| Instance | `medical-master-radfm` |
| Project | `crashlab-synthetic` |
| Zone | `northamerica-northeast2-b` |
| State | `ACTIVE` / Compute Engine status `RUNNING` |
| Machine type | `g2-standard-24` |
| Accelerators | `2 x NVIDIA_L4` |
| Boot disk | `200 GB PD_BALANCED`, Google-managed encryption |
| Data disk | `100 GB PD_STANDARD`, Google-managed encryption |
| Proxy URI | `769539ba7210760c-dot-northamerica-northeast2.notebooks.googleusercontent.com` |
| External IP | `34.130.137.71` |

Before a scientific run, refresh and record:

- `gcloud workbench instances describe medical-master-radfm`
- `gcloud compute instances describe medical-master-radfm`
- `nvidia-smi`
- Python version and package versions for `torch`, `transformers`, `vllm` or
  `sglang`, `openai`, and `pandas`
- Container image or Workbench base image where available
- CUDA driver/runtime versions reported inside the active kernel

Do not assume that GPU driver version, CUDA version, package versions, or base
image state remain fixed just because the dataset snapshot is fixed.

## Model Execution Contract

The current notebook roster is:

| Runtime name | Model ID |
| --- | --- |
| `medgemma_1_5_4b` | `google/medgemma-1.5-4b-it` |
| `llava_med_mistral_7b` | `microsoft/llava-med-v1.5-mistral-7b` |
| `internvl3_5_8b` | `OpenGVLab/InternVL3_5-8B` |
| `octomed_7b` | `OctoMed/OctoMed-7B` |

Rules:

- Run one selected model at a time.
- Start with a small smoke run before a larger run.
- Use a distinct `RUN_LABEL` for each model and attempt size.
- Stop the local model server or restart the runtime before switching models.
- Preserve raw model outputs and scorer-facing CSVs.

RadFM is a high-priority research target, but it is not part of the current
simple notebook roster. It should enter this contract only through a separate
adapter/runtime section that states how its image inputs, prompts, server
interface, and output schema are mapped into RadLE.

## Output Contract

Every medical run should produce or preserve:

- Raw response CSV in the standard RadLE output schema.
- Scorer-facing CSV view, if generated.
- Run label, selected model name, and model ID.
- Dataset snapshot ID and GCS URI.
- Git commit and notebook path.
- Runtime host fields: project, zone, machine type, GPU type/count, driver,
  CUDA, Python, and package versions.
- Server fields: engine (`vllm` or `sglang`), base URL, tensor parallel size,
  max model length, dtype, and extra server arguments.
- Any failed cases and retry/repair actions.

Outputs should not overwrite earlier runs unless the prior output family has
been archived or the overwrite is explicitly intended and recorded.

## Security And Publication Notes

This document contains private GCP resource names and should be treated as an
internal lab artifact unless redacted.

Do not commit confidential datasets, full result CSVs, local image exports, or
private credentials. The dataset and output artifacts remain outside Git.

Credential mode matters for interpretation:

- Notebook code normally runs under the Workbench VM service account.
- End-user credentials or interactive `gcloud auth login` inside the kernel can
  change which datasets and APIs a run can access.
- Any run that depends on user-specific credentials should record that fact.

## Minimum Pre-Run Checklist

Before treating a run as valid evidence:

- Confirm `RADLE_DATASET_GCS_URI` equals the frozen dataset URI in this document.
- Confirm the local copied dataset contains `263` `.jpg`/`.png` images.
- Confirm `RADLE_DATASET_SNAPSHOT_ID` is `radle-v2-frozen-2026-06-29`.
- Record Git commit, branch, and dirty/clean state.
- Record Workbench instance, zone, machine type, and GPU inventory.
- Record Python/package/CUDA details from inside the active kernel.
- Use a fresh `RUN_LABEL`.
- Preserve raw outputs before any targeted repair or scorer-view conversion.

## Useful Verification Commands

```powershell
gcloud storage ls --recursive "gs://radle-medical-data-toronto/datasets/radle-v2-frozen-2026-06-29/RadLE v2 Master Data/**" |
  Where-Object { $_ -match '\.(jpg|png)$' } |
  Measure-Object

gcloud storage buckets describe gs://radle-medical-data-toronto --format="value(location)"

gcloud storage objects describe "gs://radle-medical-data-toronto/source_archives/radle-v2-frozen-2026-06-29/RadLE v2 Master Data-20260629T202835Z-3-001.zip" --format="value(size)"

gcloud workbench instances describe medical-master-radfm `
  --location=northamerica-northeast2-b `
  --project=crashlab-synthetic

gcloud compute instances describe medical-master-radfm `
  --zone=northamerica-northeast2-b `
  --project=crashlab-synthetic
```

