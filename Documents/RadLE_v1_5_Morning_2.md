# RadLE_v1_5_Morning (2)

Source notebook: `C:\Users\thehb\Downloads\RadLE_v1_5_Morning (2).ipynb`

This Markdown export was generated from saved notebook JSON only; no cells were executed.

## Cell 1 (code, exec 4)

**Source**

```python
# ==========================================
# 1. COLAB SETUP: DRIVE + REPO CODE
# ==========================================
import os
import pathlib
import subprocess
import sys

from google.colab import drive
from google.colab import userdata

REPO_URL = "https://github.com/DrHBSB/RadLE_CRASH_Lab.git"
REPO_DIR = pathlib.Path("/content/RadLE_CRASH_Lab")
SRC_DIR = REPO_DIR / "src"
MODULE_PATH = SRC_DIR / "radle_benchmark.py"
github_token = None

# Drive remains the home for images and benchmark outputs.
drive.mount("/content/drive")


def run_git(args, check=True):
    """Run git and print useful stderr without leaking the optional token."""
    result = subprocess.run(args, text=True, capture_output=True)
    stdout = result.stdout.replace(github_token, "***") if github_token else result.stdout
    stderr = result.stderr.replace(github_token, "***") if github_token else result.stderr
    if stdout.strip():
        print(stdout)
    if stderr.strip():
        print(stderr)
    if check and result.returncode != 0:
        hint = ""
        if "403" in stderr or "Write access to repository not granted" in stderr:
            hint = (
                " The GITHUB_TOKEN secret exists, but GitHub rejected it. "
                "Create a token that has read access to this private repository "
                "and permission to read repository contents."
            )
        raise RuntimeError(f"Git command failed with exit code {result.returncode}: {args[:2]}.{hint}")
    return result


# Colab does not automatically check out the full GitHub repo when opening a notebook.
# For this private repo, add a Colab secret named GITHUB_TOKEN only if unauthenticated clone fails.
if (REPO_DIR / ".git").exists():
    pull_result = run_git(["git", "-C", str(REPO_DIR), "pull", "--ff-only"], check=False)
    if pull_result.returncode != 0:
        print("WARNING: git pull failed; continuing with the existing Colab checkout.")
elif not MODULE_PATH.exists():
    if REPO_DIR.exists() and any(REPO_DIR.iterdir()):
        raise RuntimeError(
            f"{REPO_DIR} exists but is not a Git checkout and {MODULE_PATH} was not found. "
            "Restart the Colab runtime or remove that folder, then rerun this setup cell."
        )

    try:
        github_token = userdata.get("GITHUB_TOKEN")
    except Exception:
        github_token = None

    if not github_token:
        raise RuntimeError(
            "This private GitHub repo needs a Colab secret named GITHUB_TOKEN "
            "so the Colab runtime can clone src/radle_benchmark.py. "
            "Add the secret, restart or rerun this setup cell, then continue."
        )

    clone_url = REPO_URL.replace("https://", f"https://x-access-token:{github_token}@")
    run_git(["git", "clone", clone_url, str(REPO_DIR)])

if not MODULE_PATH.exists():
    raise RuntimeError(f"Benchmark module not found after setup: {MODULE_PATH}")

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Ensure the Anthropic SDK is available.
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "anthropic", "google-genai"], check=True)
```

**Output 1: `stream`**

_Stream: `stdout`_

```text
Mounted at /content/drive
Cloning into '/content/RadLE_CRASH_Lab'...
```


**Output 2: `execute_result`**

```text
CompletedProcess(args=['/usr/bin/python3', '-m', 'pip', 'install', '-q', 'anthropic', 'google-genai'], returncode=0)
```


## Cell 2 (code, exec 5)

**Source**

```python
# ==========================================
# 2. API CLIENT + BENCHMARK IMPORTS
# ==========================================
import importlib
import inspect

import anthropic
import google.genai as google_genai
from openai import OpenAI

import radle_benchmark

radle_benchmark = importlib.reload(radle_benchmark)
create_scorer_view = radle_benchmark.create_scorer_view
run_benchmark = radle_benchmark.run_benchmark
audit_benchmark_output = radle_benchmark.audit_benchmark_output
run_targeted_repair = radle_benchmark.run_targeted_repair

for _required_param in ("anthropic_client", "gemini_client", "backup_dir"):
    if _required_param not in inspect.signature(run_benchmark).parameters:
        raise RuntimeError(
            f"Loaded stale radle_benchmark missing {_required_param}. "
            "Rerun the setup/import cells after git pull, or restart the runtime."
        )

for _required_function in (
    "audit_benchmark_output",
    "run_targeted_repair",
    "build_run_paths",
    "promote_final_results",
    "export_public_release_tables",
):
    if not hasattr(radle_benchmark, _required_function):
        raise RuntimeError(
            f"Loaded stale radle_benchmark missing {_required_function}. "
            "Rerun the setup/import cells after git pull, or restart the runtime."
        )

print(f"Loaded benchmark module: {radle_benchmark.__file__}")

try:
    os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
except Exception:
    print("ERROR: Could not find OPENAI_API_KEY in Colab Secrets.")

try:
    os.environ["OPENROUTER_API_KEY"] = userdata.get("OPENROUTER_API_KEY")
except Exception:
    print("ERROR: Could not find OPENROUTER_API_KEY in Colab Secrets.")

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

try:
    os.environ["ANTHROPIC_API_KEY"] = userdata.get("ANTHROPIC_API_KEY")
except Exception:
    print("ERROR: Could not find ANTHROPIC_API_KEY in Colab Secrets.")

anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

try:
    os.environ["GEMINI_API_KEY"] = userdata.get("GEMINI_API_KEY")
except Exception:
    print("ERROR: Could not find GEMINI_API_KEY in Colab Secrets.")

gemini_client = google_genai.Client(api_key=os.environ["GEMINI_API_KEY"])

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
```

**Output 1: `stream`**

_Stream: `stdout`_

```text
Loaded benchmark module: /content/RadLE_CRASH_Lab/src/radle_benchmark.py
```


## Cell 3 (code, exec 6)

**Source**

```python
# ==========================================
# 3. DRIVE PATHS + RUN CONFIG
# ==========================================
from pathlib import Path

# Recommended sequence: run TEST_LIMIT=1 first; if syntax/API plumbing passes, run TEST_LIMIT=5.
# Use TEST_LIMIT=None only when ready for the full benchmark.
TEST_LIMIT = None
RUN_LABEL = "radle_v2"  # Examples: test_5_cases, full_200_cases

dataset_root = Path("/content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset")
run_paths = radle_benchmark.build_run_paths(dataset_root, run_label=RUN_LABEL)

master_images_folder = run_paths["master_images_folder"]
final_output_csv = run_paths["raw_results_csv"]
raw_backup_dir = run_paths["raw_backup_dir"]
scorer_csv = run_paths["scorer_view_csv"]
repair_output_csv = run_paths["repair_results_csv"]
repair_call_log_csv = run_paths["repair_call_log_csv"]
repair_plan_csv = run_paths["repair_plan_csv"]
repair_backup_dir = run_paths["repair_backup_dir"]
final_results_csv = run_paths["final_results_csv"]
final_manifest_json = run_paths["final_manifest_json"]
public_release_dir = run_paths["public_release_dir"]

print("Run folder:", run_paths["run_root"])
print("Raw results CSV:", final_output_csv)

# Default is all models. Set DEBUG_MODEL_NAMES=["gpt_5_5"] for a cheap focused run.
DEBUG_MODEL_NAMES = None

if DEBUG_MODEL_NAMES is None:
    ACTIVE_MODELS = list(radle_benchmark.MODELS)
else:
    _available_model_names = {m["name"] for m in radle_benchmark.MODELS}
    _unknown_model_names = sorted(set(DEBUG_MODEL_NAMES) - _available_model_names)
    if _unknown_model_names:
        raise ValueError(f"Unknown model name(s): {_unknown_model_names}")

    ACTIVE_MODELS = [m for m in radle_benchmark.MODELS if m["name"] in DEBUG_MODEL_NAMES]
    if not ACTIVE_MODELS:
        raise ValueError("DEBUG_MODEL_NAMES must include at least one model when set.")

print("Running models:", [m["name"] for m in ACTIVE_MODELS])
```

**Output 1: `stream`**

_Stream: `stdout`_

```text
Run folder: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2
Raw results CSV: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/results.csv
Running models: ['gpt_5_5', 'claude_4_8_opus', 'gemini_3_1_pro', 'grok_4_20', 'qwen_3_7_plus', 'gemma_4_31b', 'llama_4_maverick', 'mistral_large_3_2512', 'glm_4_6v', 'nemotron_3_omni']
```


## Cell 4 (code, exec 27)

**Source**

```python
# ==========================================
# 4. RUN BENCHMARK
# ==========================================
df_final = run_benchmark(
    client=openrouter_client,
    openai_client=openai_client,
    anthropic_client=anthropic_client,
    gemini_client=gemini_client,
    image_folder=master_images_folder,
    output_csv=final_output_csv,
    test_limit=TEST_LIMIT,
    models=ACTIVE_MODELS,
    backup_dir=raw_backup_dir,
)

print("\nFINAL DATAFRAME PREVIEW:")
from IPython.display import display

display(df_final.head())
```

**Output 1: `stream`**

_Stream: `stdout`_

```text
Resuming existing benchmark output: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/results.csv | rows=100
Processing 200 unique cases across 10 models...

[1/200] Case ID: 1 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[2/200] Case ID: 2 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[3/200] Case ID: 3 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[4/200] Case ID: 4 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[5/200] Case ID: 5 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[6/200] Case ID: 6 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[7/200] Case ID: 7 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[8/200] Case ID: 8 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[9/200] Case ID: 9 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[10/200] Case ID: 10 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
  Checkpoint saved after 10 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0012.csv
[11/200] Case ID: 11 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[12/200] Case ID: 12 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_i_dont_know)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[13/200] Case ID: 13 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... OK (16.0s | 822 out / 603 in | 51.4 tok/sec)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[14/200] Case ID: 14 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[15/200] Case ID: 15 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... OK (11.7s | 333 out / 598 in | 28.5 tok/sec)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[16/200] Case ID: 16 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[17/200] Case ID: 17 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[18/200] Case ID: 18 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[19/200] Case ID: 19 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_i_dont_know)
  -> gemma_4_31b... SKIP (accepted_i_dont_know)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (2.0s | 30 out / 1111 in | 15.0 tok/sec)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[20/200] Case ID: 20 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... OK (7.1s | 652 out / 608 in | 91.8 tok/sec)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (2.4s | 37 out / 1110 in | 15.4 tok/sec)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
  Checkpoint saved after 20 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0013.csv
[21/200] Case ID: 21 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (3.7s | 34 out / 1361 in | 9.2 tok/sec)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[22/200] Case ID: 22 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (3.3s | 34 out / 1325 in | 10.3 tok/sec)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[23/200] Case ID: 23 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[24/200] Case ID: 24 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (4.9s | 30 out / 831 in | 6.1 tok/sec)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[25/200] Case ID: 25 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (1.8s | 23 out / 857 in | 12.8 tok/sec)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[26/200] Case ID: 26 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[27/200] Case ID: 27 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[28/200] Case ID: 28 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[29/200] Case ID: 29 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[30/200] Case ID: 30 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
  Checkpoint saved after 30 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0014.csv
[31/200] Case ID: 31 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[32/200] Case ID: 32 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[33/200] Case ID: 33 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_i_dont_know)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[34/200] Case ID: 34 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_i_dont_know)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (1.7s | 27 out / 891 in | 15.9 tok/sec)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[35/200] Case ID: 35 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... OK (21.4s | 567 out / 598 in | 26.5 tok/sec)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[36/200] Case ID: 36 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (1.8s | 35 out / 815 in | 19.4 tok/sec)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[37/200] Case ID: 37 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_i_dont_know)
  -> mistral_large_3_2512... OK (1.8s | 30 out / 1059 in | 16.7 tok/sec)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[38/200] Case ID: 38 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... OK (73.4s | 3257 out / 594 in | 44.4 tok/sec)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (2.2s | 27 out / 1039 in | 12.3 tok/sec)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[39/200] Case ID: 39 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (3.7s | 44 out / 1086 in | 11.9 tok/sec)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[40/200] Case ID: 40 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (2.8s | 22 out / 1117 in | 7.9 tok/sec)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (abstention_variant_preserve_raw)
  Checkpoint saved after 40 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0015.csv
[41/200] Case ID: 41 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[42/200] Case ID: 42 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (2.1s | 28 out / 1117 in | 13.3 tok/sec)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[43/200] Case ID: 43 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... OK (3.9s | 355 out / 1100 in | 91.0 tok/sec)
[44/200] Case ID: 44 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (2.2s | 40 out / 1143 in | 18.2 tok/sec)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[45/200] Case ID: 45 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_i_dont_know)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[46/200] Case ID: 46 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (2.4s | 31 out / 1221 in | 12.9 tok/sec)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[47/200] Case ID: 47 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[48/200] Case ID: 48 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[49/200] Case ID: 49 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[50/200] Case ID: 50 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_i_dont_know)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (2.4s | 28 out / 1735 in | 11.7 tok/sec)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
  Checkpoint saved after 50 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0016.csv
[51/200] Case ID: 51 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... OK (3.5s | 33 out / 3770 in | 9.4 tok/sec)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[52/200] Case ID: 52 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[53/200] Case ID: 53 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... OK (25.8s | 1369 out / 599 in | 53.1 tok/sec)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[54/200] Case ID: 54 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... OK (26.6s | 482 out / 865 in | 18.1 tok/sec)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[55/200] Case ID: 55 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[56/200] Case ID: 56 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[57/200] Case ID: 57 (4 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[58/200] Case ID: 58 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[59/200] Case ID: 59 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[60/200] Case ID: 60 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_i_dont_know)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
  Checkpoint saved after 60 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0017.csv
[61/200] Case ID: 61 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[62/200] Case ID: 62 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[63/200] Case ID: 63 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[64/200] Case ID: 64 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[65/200] Case ID: 65 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[66/200] Case ID: 66 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_i_dont_know)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[67/200] Case ID: 67 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (abstention_variant_preserve_raw)
[68/200] Case ID: 68 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[69/200] Case ID: 69 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[70/200] Case ID: 70 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
  Checkpoint saved after 70 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0018.csv
[71/200] Case ID: 71 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[72/200] Case ID: 72 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[73/200] Case ID: 73 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[74/200] Case ID: 74 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[75/200] Case ID: 75 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_i_dont_know)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[76/200] Case ID: 76 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[77/200] Case ID: 77 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[78/200] Case ID: 78 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_i_dont_know)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[79/200] Case ID: 79 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[80/200] Case ID: 80 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
  Checkpoint saved after 80 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0019.csv
[81/200] Case ID: 81 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... OK (25.9s | 637 out / 614 in | 24.6 tok/sec)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[82/200] Case ID: 82 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[83/200] Case ID: 83 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[84/200] Case ID: 84 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[85/200] Case ID: 85 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[86/200] Case ID: 86 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[87/200] Case ID: 87 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[88/200] Case ID: 88 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[89/200] Case ID: 89 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... OK (5.1s | 1067 out / 666 in | 209.2 tok/sec)
[90/200] Case ID: 90 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
  Checkpoint saved after 90 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0020.csv
[91/200] Case ID: 91 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[92/200] Case ID: 92 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[93/200] Case ID: 93 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[94/200] Case ID: 94 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[95/200] Case ID: 95 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[96/200] Case ID: 96 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_i_dont_know)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[97/200] Case ID: 97 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_clean_diagnosis)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... OK (1.4s | 158 out / 723 in | 112.9 tok/sec)
[98/200] Case ID: 98 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_i_dont_know)
  -> nemotron_3_omni... SKIP (accepted_i_dont_know)
[99/200] Case ID: 99 (1 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... SKIP (accepted_clean_diagnosis)
[100/200] Case ID: 100 (2 images)
  -> gpt_5_5... SKIP (accepted_clean_diagnosis)
  -> claude_4_8_opus... SKIP (accepted_clean_diagnosis)
  -> gemini_3_1_pro... SKIP (accepted_clean_diagnosis)
  -> grok_4_20... SKIP (accepted_i_dont_know)
  -> qwen_3_7_plus... SKIP (accepted_clean_diagnosis)
  -> gemma_4_31b... SKIP (accepted_clean_diagnosis)
  -> llama_4_maverick... SKIP (accepted_clean_diagnosis)
  -> mistral_large_3_2512... SKIP (accepted_clean_diagnosis)
  -> glm_4_6v... SKIP (accepted_clean_diagnosis)
  -> nemotron_3_omni... OK (10.1s | 2109 out / 860 in | 208.8 tok/sec)
  Checkpoint saved after 100 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0021.csv
[101/200] Case ID: 101 (2 images)
  -> gpt_5_5... OK (12.9s | 541 out / 636 in | 41.9 tok/sec)
  -> claude_4_8_opus... OK (3.9s | 139 out / 885 in | 35.6 tok/sec)
  -> gemini_3_1_pro... OK (14.1s | 24 out / 2508 in | 1.7 tok/sec)
  -> grok_4_20... OK (0.7s | 16 out / 689 in | 22.9 tok/sec)
  -> qwen_3_7_plus... OK (70.2s | 3697 out / 596 in | 52.7 tok/sec)
  -> gemma_4_31b... OK (44.4s | 1185 out / 861 in | 26.7 tok/sec)
  -> llama_4_maverick... OK (5.8s | 342 out / 1473 in | 59.0 tok/sec)
  -> mistral_large_3_2512... OK (1.3s | 31 out / 714 in | 23.8 tok/sec)
  -> glm_4_6v... OK (13.1s | 664 out / 668 in | 50.7 tok/sec)
  -> nemotron_3_omni... OK (4.0s | 959 out / 868 in | 239.8 tok/sec)
[102/200] Case ID: 102 (2 images)
  -> gpt_5_5... OK (12.5s | 541 out / 691 in | 43.3 tok/sec)
  -> claude_4_8_opus... OK (5.0s | 239 out / 940 in | 47.8 tok/sec)
  -> gemini_3_1_pro... OK (11.6s | 23 out / 2516 in | 2.0 tok/sec)
  -> grok_4_20... OK (0.6s | 15 out / 736 in | 25.0 tok/sec)
  -> qwen_3_7_plus... OK (181.1s | 9985 out / 654 in | 55.1 tok/sec)
  -> gemma_4_31b... OK (66.9s | 636 out / 865 in | 9.5 tok/sec)
  -> llama_4_maverick... OK (3.5s | 184 out / 1763 in | 52.6 tok/sec)
  -> mistral_large_3_2512... OK (1.6s | 27 out / 775 in | 16.9 tok/sec)
  -> glm_4_6v... OK (21.1s | 1393 out / 692 in | 66.0 tok/sec)
  -> nemotron_3_omni... OK (3.8s | 1108 out / 885 in | 291.6 tok/sec)
[103/200] Case ID: 103 (1 images)
  -> gpt_5_5... OK (7.2s | 311 out / 809 in | 43.2 tok/sec)
  -> claude_4_8_opus... OK (3.1s | 46 out / 1049 in | 14.8 tok/sec)
  -> gemini_3_1_pro... OK (30.9s | 23 out / 1379 in | 0.7 tok/sec)
  -> grok_4_20... OK (0.7s | 16 out / 832 in | 22.9 tok/sec)
  -> qwen_3_7_plus... OK (117.2s | 5902 out / 722 in | 50.4 tok/sec)
  -> gemma_4_31b... OK (68.6s | 1804 out / 591 in | 26.3 tok/sec)
  -> llama_4_maverick... OK (3.2s | 195 out / 1326 in | 60.9 tok/sec)
  -> mistral_large_3_2512... OK (1.7s | 35 out / 872 in | 20.6 tok/sec)
  -> glm_4_6v... OK (13.8s | 837 out / 811 in | 60.7 tok/sec)
  -> nemotron_3_omni... OK (2.8s | 415 out / 738 in | 148.2 tok/sec)
[104/200] Case ID: 104 (1 images)
  -> gpt_5_5... OK (79.6s | 4063 out / 773 in | 51.0 tok/sec)
  -> claude_4_8_opus... OK (1.8s | 24 out / 1015 in | 13.3 tok/sec)
  -> gemini_3_1_pro... OK (13.1s | 22 out / 1392 in | 1.7 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 802 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (92.8s | 4680 out / 690 in | 50.4 tok/sec)
  -> gemma_4_31b... OK (22.5s | 1084 out / 589 in | 48.2 tok/sec)
  -> llama_4_maverick... OK (2.4s | 101 out / 1326 in | 42.1 tok/sec)
  -> mistral_large_3_2512... OK (1.5s | 31 out / 836 in | 20.7 tok/sec)
  -> glm_4_6v... OK (27.4s | 951 out / 791 in | 34.7 tok/sec)
  -> nemotron_3_omni... OK (2.7s | 421 out / 708 in | 155.9 tok/sec)
[105/200] Case ID: 105 (2 images)
  -> gpt_5_5... OK (23.6s | 1059 out / 846 in | 44.9 tok/sec)
  -> claude_4_8_opus... OK (5.3s | 234 out / 1102 in | 44.2 tok/sec)
  -> gemini_3_1_pro... OK (20.2s | 23 out / 2490 in | 1.1 tok/sec)
  -> grok_4_20... OK (0.6s | 15 out / 864 in | 25.0 tok/sec)
  -> qwen_3_7_plus... OK (83.4s | 4498 out / 742 in | 53.9 tok/sec)
  -> gemma_4_31b... OK (44.8s | 633 out / 865 in | 14.1 tok/sec)
  -> llama_4_maverick... OK (2.3s | 104 out / 1473 in | 45.2 tok/sec)
  -> mistral_large_3_2512... OK (1.7s | 35 out / 946 in | 20.6 tok/sec)
  -> glm_4_6v... OK (9.9s | 593 out / 858 in | 59.9 tok/sec)
  -> nemotron_3_omni... OK (2.2s | 287 out / 878 in | 130.5 tok/sec)
[106/200] Case ID: 106 (2 images)
  -> gpt_5_5... OK (9.0s | 381 out / 695 in | 42.3 tok/sec)
  -> claude_4_8_opus... OK (1.8s | 28 out / 914 in | 15.6 tok/sec)
  -> gemini_3_1_pro... OK (104.4s | 22 out / 2497 in | 0.2 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 739 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (69.2s | 3669 out / 632 in | 53.0 tok/sec)
  -> gemma_4_31b... OK (147.7s | 1941 out / 884 in | 13.1 tok/sec)
  -> llama_4_maverick... OK (2.6s | 146 out / 1763 in | 56.2 tok/sec)
  -> mistral_large_3_2512... OK (1.7s | 29 out / 745 in | 17.1 tok/sec)
  -> glm_4_6v... OK (9.4s | 462 out / 695 in | 49.1 tok/sec)
  -> nemotron_3_omni... OK (6.4s | 869 out / 874 in | 135.8 tok/sec)
[107/200] Case ID: 107 (3 images)
  -> gpt_5_5... OK (125.6s | 6634 out / 751 in | 52.8 tok/sec)
  -> claude_4_8_opus... OK (4.4s | 228 out / 984 in | 51.8 tok/sec)
  -> gemini_3_1_pro... OK (17.5s | 23 out / 3559 in | 1.3 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 786 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (51.0s | 2722 out / 667 in | 53.4 tok/sec)
  -> gemma_4_31b... OK (74.1s | 1372 out / 735 in | 18.5 tok/sec)
  -> llama_4_maverick... OK (4.2s | 342 out / 1620 in | 81.4 tok/sec)
  -> mistral_large_3_2512... OK (2.6s | 30 out / 817 in | 11.5 tok/sec)
  -> glm_4_6v... OK (17.1s | 565 out / 719 in | 33.0 tok/sec)
  -> nemotron_3_omni... OK (6.1s | 617 out / 1143 in | 101.1 tok/sec)
[108/200] Case ID: 108 (1 images)
  -> gpt_5_5... OK (3.9s | 155 out / 773 in | 39.7 tok/sec)
  -> claude_4_8_opus... OK (4.8s | 213 out / 1030 in | 44.4 tok/sec)
  -> gemini_3_1_pro... OK (8.0s | 23 out / 1392 in | 2.9 tok/sec)
  -> grok_4_20... OK (0.7s | 29 out / 802 in | 41.4 tok/sec)
  -> qwen_3_7_plus... OK (34.7s | 1834 out / 720 in | 52.9 tok/sec)
  -> gemma_4_31b... OK (37.6s | 970 out / 588 in | 25.8 tok/sec)
  -> llama_4_maverick... OK (1.0s | 59 out / 1326 in | 59.0 tok/sec)
  -> mistral_large_3_2512... OK (1.7s | 34 out / 851 in | 20.0 tok/sec)
  -> glm_4_6v... OK (22.2s | 998 out / 791 in | 45.0 tok/sec)
  -> nemotron_3_omni... OK (5.2s | 1031 out / 708 in | 198.3 tok/sec)
[109/200] Case ID: 109 (2 images)
  -> gpt_5_5... OK (8.5s | 344 out / 618 in | 40.5 tok/sec)
  -> claude_4_8_opus... OK (1.5s | 39 out / 853 in | 26.0 tok/sec)
  -> gemini_3_1_pro... OK (11.0s | 27 out / 2515 in | 2.5 tok/sec)
  -> grok_4_20... OK (0.6s | 15 out / 674 in | 25.0 tok/sec)
  -> qwen_3_7_plus... OK (119.7s | 6542 out / 579 in | 54.7 tok/sec)
  -> gemma_4_31b... OK (44.0s | 2022 out / 874 in | 46.0 tok/sec)
  -> llama_4_maverick... OK (3.9s | 333 out / 1183 in | 85.4 tok/sec)
  -> mistral_large_3_2512... OK (1.4s | 30 out / 686 in | 21.4 tok/sec)
  -> glm_4_6v... OK (16.2s | 844 out / 632 in | 52.1 tok/sec)
  -> nemotron_3_omni... OK (2.7s | 446 out / 881 in | 165.2 tok/sec)
[110/200] Case ID: 110 (2 images)
  -> gpt_5_5... OK (5.1s | 193 out / 759 in | 37.8 tok/sec)
  -> claude_4_8_opus... OK (1.6s | 31 out / 1004 in | 19.4 tok/sec)
  -> gemini_3_1_pro... OK (9.7s | 24 out / 2498 in | 2.5 tok/sec)
  -> grok_4_20... OK (0.6s | 15 out / 792 in | 25.0 tok/sec)
  -> qwen_3_7_plus... OK (26.3s | 1361 out / 696 in | 51.7 tok/sec)
  -> gemma_4_31b... OK (5.4s | 512 out / 868 in | 94.8 tok/sec)
  -> llama_4_maverick... OK (1.6s | 91 out / 1763 in | 56.9 tok/sec)
  -> mistral_large_3_2512... OK (2.0s | 34 out / 839 in | 17.0 tok/sec)
  -> glm_4_6v... OK (6.3s | 289 out / 781 in | 45.9 tok/sec)
  -> nemotron_3_omni... OK (2.8s | 348 out / 874 in | 124.3 tok/sec)
  Checkpoint saved after 110 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0022.csv
[111/200] Case ID: 111 (1 images)
  -> gpt_5_5... OK (59.5s | 3082 out / 2154 in | 51.8 tok/sec)
  -> claude_4_8_opus... OK (2.5s | 34 out / 2569 in | 13.6 tok/sec)
  -> gemini_3_1_pro... OK (24.5s | 23 out / 1406 in | 0.9 tok/sec)
  -> grok_4_20... OK (0.8s | 17 out / 1966 in | 21.2 tok/sec)
  -> qwen_3_7_plus... OK (28.6s | 1499 out / 1884 in | 52.4 tok/sec)
  -> gemma_4_31b... OK (69.0s | 1205 out / 593 in | 17.5 tok/sec)
  -> llama_4_maverick... OK (2.7s | 120 out / 2776 in | 44.4 tok/sec)
  -> mistral_large_3_2512... OK (5.0s | 34 out / 2423 in | 6.8 tok/sec)
  -> glm_4_6v... OK (14.9s | 806 out / 2331 in | 54.1 tok/sec)
  -> nemotron_3_omni... OK (26.3s | 4838 out / 1872 in | 184.0 tok/sec)
[112/200] Case ID: 112 (1 images)
  -> gpt_5_5... OK (21.3s | 1059 out / 1237 in | 49.7 tok/sec)
  -> claude_4_8_opus... OK (8.6s | 391 out / 1537 in | 45.5 tok/sec)
  -> gemini_3_1_pro... OK (107.0s | 23 out / 1421 in | 0.2 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 1189 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (52.7s | 2835 out / 1107 in | 53.8 tok/sec)
  -> gemma_4_31b... OK (37.3s | 753 out / 602 in | 20.2 tok/sec)
  -> llama_4_maverick... OK (0.7s | 18 out / 1616 in | 25.7 tok/sec)
  -> mistral_large_3_2512... OK (1.4s | 30 out / 1367 in | 21.4 tok/sec)
  -> glm_4_6v... OK (12.8s | 757 out / 1323 in | 59.1 tok/sec)
  -> nemotron_3_omni... OK (2.3s | 273 out / 1095 in | 118.7 tok/sec)
[113/200] Case ID: 113 (1 images)
  -> gpt_5_5... OK (72.6s | 3649 out / 1637 in | 50.3 tok/sec)
  -> claude_4_8_opus... OK (2.2s | 37 out / 1933 in | 16.8 tok/sec)
  -> gemini_3_1_pro... OK (20.2s | 25 out / 1394 in | 1.2 tok/sec)
  -> grok_4_20... OK (1.2s | 17 out / 1522 in | 14.2 tok/sec)
  -> qwen_3_7_plus... OK (161.3s | 8821 out / 1374 in | 54.7 tok/sec)
  -> gemma_4_31b... OK (53.0s | 614 out / 590 in | 11.6 tok/sec)
  -> llama_4_maverick... OK (2.3s | 101 out / 2196 in | 43.9 tok/sec)
  -> mistral_large_3_2512... OK (3.4s | 31 out / 1773 in | 9.1 tok/sec)
  -> glm_4_6v... OK (7.6s | 281 out / 1701 in | 37.0 tok/sec)
  -> nemotron_3_omni... OK (2.5s | 460 out / 1428 in | 184.0 tok/sec)
[114/200] Case ID: 114 (1 images)
  -> gpt_5_5... OK (22.1s | 1056 out / 1237 in | 47.8 tok/sec)
  -> claude_4_8_opus... OK (1.9s | 32 out / 1513 in | 16.8 tok/sec)
  -> gemini_3_1_pro... OK (13.3s | 21 out / 1421 in | 1.6 tok/sec)
  -> grok_4_20... OK (0.5s | 15 out / 1189 in | 30.0 tok/sec)
  -> qwen_3_7_plus... OK (121.1s | 6613 out / 1086 in | 54.6 tok/sec)
  -> gemma_4_31b... OK (34.7s | 1599 out / 603 in | 46.1 tok/sec)
  -> llama_4_maverick... OK (3.2s | 94 out / 1616 in | 29.4 tok/sec)
  -> mistral_large_3_2512... OK (1.7s | 33 out / 1343 in | 19.4 tok/sec)
  -> glm_4_6v... OK (24.6s | 1101 out / 1299 in | 44.8 tok/sec)
  -> nemotron_3_omni... OK (1.8s | 206 out / 1095 in | 114.4 tok/sec)
[115/200] Case ID: 115 (1 images)
  -> gpt_5_5... OK (17.5s | 751 out / 1992 in | 42.9 tok/sec)
  -> claude_4_8_opus... OK (4.0s | 166 out / 2397 in | 41.5 tok/sec)
  -> gemini_3_1_pro... OK (16.1s | 23 out / 1377 in | 1.4 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 1818 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (82.1s | 4469 out / 1736 in | 54.4 tok/sec)
  -> gemma_4_31b... OK (55.0s | 1323 out / 594 in | 24.1 tok/sec)
  -> llama_4_maverick... OK (2.0s | 80 out / 2776 in | 40.0 tok/sec)
  -> mistral_large_3_2512... OK (2.2s | 31 out / 2247 in | 14.1 tok/sec)
  -> glm_4_6v... OK (12.8s | 539 out / 2121 in | 42.1 tok/sec)
  -> nemotron_3_omni... OK (7.8s | 991 out / 1724 in | 127.1 tok/sec)
[116/200] Case ID: 116 (1 images)
  -> gpt_5_5... OK (13.2s | 541 out / 1244 in | 41.0 tok/sec)
  -> claude_4_8_opus... OK (4.0s | 179 out / 1495 in | 44.8 tok/sec)
  -> gemini_3_1_pro... OK (107.6s | 23 out / 1409 in | 0.2 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 1195 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (104.2s | 5565 out / 1058 in | 53.4 tok/sec)
  -> gemma_4_31b... OK (26.0s | 592 out / 610 in | 22.8 tok/sec)
  -> llama_4_maverick... OK (2.6s | 106 out / 1761 in | 40.8 tok/sec)
  -> mistral_large_3_2512... OK (3.1s | 26 out / 1334 in | 8.4 tok/sec)
  -> glm_4_6v... OK (13.5s | 692 out / 1275 in | 51.3 tok/sec)
  -> nemotron_3_omni... OK (6.3s | 752 out / 1101 in | 119.4 tok/sec)
[117/200] Case ID: 117 (1 images)
  -> gpt_5_5... OK (13.0s | 542 out / 1903 in | 41.7 tok/sec)
  -> claude_4_8_opus... OK (4.3s | 144 out / 2227 in | 33.5 tok/sec)
  -> gemini_3_1_pro... OK (12.0s | 23 out / 1409 in | 1.9 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 1744 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (64.1s | 3455 out / 1590 in | 53.9 tok/sec)
  -> gemma_4_31b... OK (57.3s | 1594 out / 610 in | 27.8 tok/sec)
  -> llama_4_maverick... OK (2.3s | 79 out / 2776 in | 34.3 tok/sec)
  -> mistral_large_3_2512... OK (2.0s | 29 out / 2074 in | 14.5 tok/sec)
  -> glm_4_6v... OK (11.2s | 550 out / 1995 in | 49.1 tok/sec)
  -> nemotron_3_omni... OK (2.9s | 214 out / 1650 in | 73.8 tok/sec)
[118/200] Case ID: 118 (1 images)
  -> gpt_5_5... OK (133.1s | 6758 out / 1637 in | 50.8 tok/sec)
  -> claude_4_8_opus... OK (3.5s | 121 out / 1967 in | 34.6 tok/sec)
  -> gemini_3_1_pro... OK (13.1s | 24 out / 1394 in | 1.8 tok/sec)
  -> grok_4_20... OK (1.2s | 18 out / 1522 in | 15.0 tok/sec)
  -> qwen_3_7_plus... OK (77.5s | 4226 out / 1403 in | 54.5 tok/sec)
  -> gemma_4_31b... OK (9.9s | 518 out / 590 in | 52.3 tok/sec)
  -> llama_4_maverick... OK (8.1s | 351 out / 2196 in | 43.3 tok/sec)
  -> mistral_large_3_2512... OK (2.1s | 32 out / 1807 in | 15.2 tok/sec)
  -> glm_4_6v... OK (11.1s | 612 out / 1701 in | 55.1 tok/sec)
  -> nemotron_3_omni... OK (2.9s | 505 out / 1428 in | 174.1 tok/sec)
[119/200] Case ID: 119 (1 images)
  -> gpt_5_5... OK (153.2s | 8404 out / 1346 in | 54.9 tok/sec)
  -> claude_4_8_opus... OK (5.1s | 262 out / 1625 in | 51.4 tok/sec)
  -> gemini_3_1_pro... OK (18.6s | 22 out / 1406 in | 1.2 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 1280 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (55.2s | 2962 out / 1198 in | 53.7 tok/sec)
  -> gemma_4_31b... OK (50.2s | 867 out / 593 in | 17.3 tok/sec)
  -> llama_4_maverick... OK (0.7s | 20 out / 1761 in | 28.6 tok/sec)
  -> mistral_large_3_2512... OK (2.2s | 27 out / 1463 in | 12.3 tok/sec)
  -> glm_4_6v... OK (9.0s | 251 out / 1435 in | 27.9 tok/sec)
  -> nemotron_3_omni... OK (2.2s | 169 out / 1186 in | 76.8 tok/sec)
[120/200] Case ID: 120 (2 images)
  -> gpt_5_5... OK (12.1s | 502 out / 1712 in | 41.5 tok/sec)
  -> claude_4_8_opus... OK (6.3s | 329 out / 2042 in | 52.2 tok/sec)
  -> gemini_3_1_pro... OK (19.8s | 22 out / 2508 in | 1.1 tok/sec)
  -> grok_4_20... OK (1.0s | 15 out / 1586 in | 15.0 tok/sec)
  -> qwen_3_7_plus... OK (124.3s | 6714 out / 1436 in | 54.0 tok/sec)
  -> gemma_4_31b... OK (224.6s | 3967 out / 860 in | 17.7 tok/sec)
  -> llama_4_maverick... OK (3.5s | 133 out / 2923 in | 38.0 tok/sec)
  -> mistral_large_3_2512... OK (3.0s | 40 out / 1895 in | 13.3 tok/sec)
  -> glm_4_6v... OK (210.4s | 12312 out / 1787 in | 58.5 tok/sec)
  -> nemotron_3_omni... OK (3.4s | 362 out / 1535 in | 106.5 tok/sec)
  Checkpoint saved after 120 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0023.csv
[121/200] Case ID: 121 (2 images)
  -> gpt_5_5... OK (63.9s | 3134 out / 742 in | 49.0 tok/sec)
  -> claude_4_8_opus... OK (5.0s | 245 out / 988 in | 49.0 tok/sec)
  -> gemini_3_1_pro... OK (26.7s | 23 out / 2495 in | 0.9 tok/sec)
  -> grok_4_20... OK (0.7s | 18 out / 778 in | 25.7 tok/sec)
  -> qwen_3_7_plus... OK (70.8s | 3837 out / 683 in | 54.2 tok/sec)
  -> gemma_4_31b... OK (32.4s | 920 out / 851 in | 28.4 tok/sec)
  -> llama_4_maverick... OK (2.8s | 85 out / 1763 in | 30.4 tok/sec)
  -> mistral_large_3_2512... OK (1.5s | 35 out / 821 in | 23.3 tok/sec)
  -> glm_4_6v... OK (14.6s | 579 out / 782 in | 39.7 tok/sec)
  -> nemotron_3_omni... OK (26.9s | 6396 out / 856 in | 237.8 tok/sec)
[122/200] Case ID: 122 (1 images)
  -> gpt_5_5... OK (25.5s | 1057 out / 651 in | 41.5 tok/sec)
  -> claude_4_8_opus... OK (2.0s | 27 out / 885 in | 13.5 tok/sec)
  -> gemini_3_1_pro... OK (20.1s | 23 out / 1410 in | 1.1 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 701 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (123.6s | 6775 out / 602 in | 54.8 tok/sec)
  -> gemma_4_31b... OK (27.5s | 565 out / 594 in | 20.5 tok/sec)
  -> llama_4_maverick... OK (1.0s | 20 out / 1036 in | 20.0 tok/sec)
  -> mistral_large_3_2512... OK (1.6s | 29 out / 710 in | 18.1 tok/sec)
  -> glm_4_6v... OK (4.4s | 305 out / 676 in | 69.3 tok/sec)
  -> nemotron_3_omni... OK (38.3s | 9498 out / 607 in | 248.0 tok/sec)
[123/200] Case ID: 123 (1 images)
  -> gpt_5_5... OK (8.4s | 375 out / 710 in | 44.6 tok/sec)
  -> claude_4_8_opus... OK (1.5s | 29 out / 955 in | 19.3 tok/sec)
  -> gemini_3_1_pro... OK (12.4s | 25 out / 1402 in | 2.0 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 750 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (43.6s | 2316 out / 668 in | 53.1 tok/sec)
  -> gemma_4_31b... OK (17.1s | 613 out / 591 in | 35.8 tok/sec)
  -> llama_4_maverick... OK (4.8s | 122 out / 1326 in | 25.4 tok/sec)
  -> mistral_large_3_2512... OK (1.9s | 38 out / 776 in | 20.0 tok/sec)
  -> glm_4_6v... OK (13.8s | 648 out / 765 in | 47.0 tok/sec)
  -> nemotron_3_omni... OK (4.6s | 718 out / 656 in | 156.1 tok/sec)
[124/200] Case ID: 124 (2 images)
  -> gpt_5_5... OK (86.0s | 4172 out / 742 in | 48.5 tok/sec)
  -> claude_4_8_opus... OK (2.3s | 29 out / 972 in | 12.6 tok/sec)
  -> gemini_3_1_pro... OK (15.6s | 22 out / 2494 in | 1.4 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 778 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (145.7s | 7983 out / 668 in | 54.8 tok/sec)
  -> gemma_4_31b... OK (29.5s | 757 out / 867 in | 25.7 tok/sec)
  -> llama_4_maverick... OK (2.3s | 82 out / 1763 in | 35.7 tok/sec)
  -> mistral_large_3_2512... OK (1.9s | 27 out / 807 in | 14.2 tok/sec)
  -> glm_4_6v... OK (16.0s | 571 out / 765 in | 35.7 tok/sec)
  -> nemotron_3_omni... OK (3.3s | 771 out / 874 in | 233.6 tok/sec)
[125/200] Case ID: 125 (2 images)
  -> gpt_5_5... OK (43.1s | 2101 out / 728 in | 48.7 tok/sec)
  -> claude_4_8_opus... OK (5.9s | 311 out / 976 in | 52.7 tok/sec)
  -> gemini_3_1_pro... OK (17.8s | 24 out / 2492 in | 1.3 tok/sec)
  -> grok_4_20... OK (1.1s | 15 out / 766 in | 13.6 tok/sec)
  -> qwen_3_7_plus... OK (139.1s | 7612 out / 662 in | 54.7 tok/sec)
  -> gemma_4_31b... OK (57.7s | 1062 out / 598 in | 18.4 tok/sec)
  -> llama_4_maverick... OK (3.3s | 131 out / 1763 in | 39.7 tok/sec)
  -> mistral_large_3_2512... OK (2.0s | 35 out / 805 in | 17.5 tok/sec)
  -> glm_4_6v... OK (5.4s | 346 out / 737 in | 64.1 tok/sec)
  -> nemotron_3_omni... OK (6.1s | 1106 out / 876 in | 181.3 tok/sec)
[126/200] Case ID: 126 (1 images)
  -> gpt_5_5... OK (234.2s | 11936 out / 1592 in | 51.0 tok/sec)
  -> claude_4_8_opus... OK (8.1s | 434 out / 1924 in | 53.6 tok/sec)
  -> gemini_3_1_pro... OK (19.4s | 28 out / 1423 in | 1.4 tok/sec)
  -> grok_4_20... OK (0.9s | 23 out / 1485 in | 25.6 tok/sec)
  -> qwen_3_7_plus... OK (151.6s | 8292 out / 1366 in | 54.7 tok/sec)
  -> gemma_4_31b... OK (26.8s | 733 out / 604 in | 27.4 tok/sec)
  -> llama_4_maverick... OK (5.4s | 240 out / 2196 in | 44.4 tok/sec)
  -> mistral_large_3_2512... OK (2.6s | 35 out / 1763 in | 13.5 tok/sec)
  -> glm_4_6v... OK (22.7s | 1150 out / 1659 in | 50.7 tok/sec)
  -> nemotron_3_omni... OK (2.4s | 227 out / 1391 in | 94.6 tok/sec)
[127/200] Case ID: 127 (1 images)
  -> gpt_5_5... OK (9.7s | 322 out / 823 in | 33.2 tok/sec)
  -> claude_4_8_opus... OK (1.8s | 43 out / 1065 in | 23.9 tok/sec)
  -> gemini_3_1_pro... OK (8.6s | 25 out / 1413 in | 2.9 tok/sec)
  -> grok_4_20... OK (0.6s | 15 out / 844 in | 25.0 tok/sec)
  -> qwen_3_7_plus... OK (67.7s | 3648 out / 738 in | 53.9 tok/sec)
  -> gemma_4_31b... OK (15.6s | 388 out / 604 in | 24.9 tok/sec)
  -> llama_4_maverick... OK (1.7s | 63 out / 1326 in | 37.1 tok/sec)
  -> mistral_large_3_2512... OK (1.5s | 26 out / 899 in | 17.3 tok/sec)
  -> glm_4_6v... OK (12.8s | 543 out / 855 in | 42.4 tok/sec)
  -> nemotron_3_omni... OK (3.4s | 539 out / 750 in | 158.5 tok/sec)
[128/200] Case ID: 128 (2 images)
  -> gpt_5_5... OK (13.8s | 539 out / 2104 in | 39.1 tok/sec)
  -> claude_4_8_opus... OK (7.5s | 391 out / 2468 in | 52.1 tok/sec)
  -> gemini_3_1_pro... OK (55.2s | 27 out / 2483 in | 0.5 tok/sec)
  -> grok_4_20... OK (1.1s | 15 out / 1913 in | 13.6 tok/sec)
  -> qwen_3_7_plus... OK (107.0s | 5845 out / 1784 in | 54.6 tok/sec)
  -> gemma_4_31b... OK (34.9s | 873 out / 848 in | 25.0 tok/sec)
  -> llama_4_maverick... OK (11.2s | 304 out / 3213 in | 27.1 tok/sec)
  -> mistral_large_3_2512... OK (2.6s | 29 out / 2327 in | 11.2 tok/sec)
  -> glm_4_6v... OK (12.3s | 784 out / 2235 in | 63.7 tok/sec)
  -> nemotron_3_omni... OK (1.8s | 199 out / 1969 in | 110.6 tok/sec)
[129/200] Case ID: 129 (3 images)
  -> gpt_5_5... OK (142.3s | 7033 out / 619 in | 49.4 tok/sec)
  -> claude_4_8_opus... OK (3.5s | 95 out / 871 in | 27.1 tok/sec)
  -> gemini_3_1_pro... OK (9.9s | 25 out / 3556 in | 2.5 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 676 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (30.7s | 1608 out / 584 in | 52.4 tok/sec)
  -> gemma_4_31b... OK (152.4s | 3464 out / 1128 in | 22.7 tok/sec)
  -> llama_4_maverick... OK (11.8s | 332 out / 750 in | 28.1 tok/sec)
  -> mistral_large_3_2512... OK (1.8s | 30 out / 707 in | 16.7 tok/sec)
  -> glm_4_6v... OK (25.0s | 874 out / 627 in | 35.0 tok/sec)
  -> nemotron_3_omni... OK (3.1s | 432 out / 1123 in | 139.4 tok/sec)
[130/200] Case ID: 130 (1 images)
  -> gpt_5_5... OK (13.4s | 540 out / 758 in | 40.3 tok/sec)
  -> claude_4_8_opus... OK (5.4s | 253 out / 1009 in | 46.9 tok/sec)
  -> gemini_3_1_pro... OK (13.4s | 23 out / 1401 in | 1.7 tok/sec)
  -> grok_4_20... OK (0.5s | 15 out / 790 in | 30.0 tok/sec)
  -> qwen_3_7_plus... OK (90.4s | 4915 out / 708 in | 54.4 tok/sec)
  -> gemma_4_31b... OK (74.3s | 1966 out / 608 in | 26.5 tok/sec)
  -> llama_4_maverick... OK (1.2s | 18 out / 1036 in | 15.0 tok/sec)
  -> mistral_large_3_2512... OK (1.2s | 27 out / 836 in | 22.5 tok/sec)
  -> glm_4_6v... OK (15.7s | 336 out / 795 in | 21.4 tok/sec)
  -> nemotron_3_omni... OK (1.6s | 167 out / 696 in | 104.4 tok/sec)
  Checkpoint saved after 130 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0024.csv
[131/200] Case ID: 131 (1 images)
  -> gpt_5_5... OK (66.0s | 3131 out / 1459 in | 47.4 tok/sec)
  -> claude_4_8_opus... OK (1.9s | 30 out / 1765 in | 15.8 tok/sec)
  -> gemini_3_1_pro... OK (13.5s | 21 out / 1413 in | 1.6 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 1374 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (25.1s | 1263 out / 1292 in | 50.3 tok/sec)
  -> gemma_4_31b... OK (8.9s | 374 out / 604 in | 42.0 tok/sec)
  -> llama_4_maverick... OK (2.3s | 117 out / 2196 in | 50.9 tok/sec)
  -> mistral_large_3_2512... OK (1.9s | 32 out / 1601 in | 16.8 tok/sec)
  -> glm_4_6v... OK (19.3s | 556 out / 1575 in | 28.8 tok/sec)
  -> nemotron_3_omni... OK (2.1s | 120 out / 1280 in | 57.1 tok/sec)
[132/200] Case ID: 132 (1 images)
  -> gpt_5_5... OK (21.5s | 1051 out / 2125 in | 48.9 tok/sec)
  -> claude_4_8_opus... OK (3.2s | 150 out / 2483 in | 46.9 tok/sec)
  -> gemini_3_1_pro... OK (15.7s | 24 out / 1409 in | 1.5 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 1929 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (38.1s | 2016 out / 1810 in | 52.9 tok/sec)
  -> gemma_4_31b... OK (13.2s | 453 out / 610 in | 34.3 tok/sec)
  -> llama_4_maverick... OK (4.1s | 68 out / 2776 in | 16.6 tok/sec)
  -> mistral_large_3_2512... OK (2.4s | 32 out / 2335 in | 13.3 tok/sec)
  -> glm_4_6v... OK (26.3s | 1069 out / 2247 in | 40.6 tok/sec)
  -> nemotron_3_omni... OK (3.1s | 476 out / 1835 in | 153.5 tok/sec)
[133/200] Case ID: 133 (2 images)
  -> gpt_5_5... OK (116.6s | 5202 out / 1736 in | 44.6 tok/sec)
  -> claude_4_8_opus... OK (5.5s | 293 out / 2080 in | 53.3 tok/sec)
  -> gemini_3_1_pro... OK (21.3s | 25 out / 2473 in | 1.2 tok/sec)
  -> grok_4_20... OK (0.9s | 15 out / 1606 in | 16.7 tok/sec)
  -> qwen_3_7_plus... OK (157.6s | 8666 out / 1500 in | 55.0 tok/sec)
  -> gemma_4_31b... OK (101.6s | 1691 out / 604 in | 16.6 tok/sec)
  -> llama_4_maverick... OK (12.3s | 342 out / 2923 in | 27.8 tok/sec)
  -> mistral_large_3_2512... OK (2.2s | 31 out / 1929 in | 14.1 tok/sec)
  -> glm_4_6v... OK (18.9s | 818 out / 1843 in | 43.3 tok/sec)
  -> nemotron_3_omni... OK (4.7s | 489 out / 1638 in | 104.0 tok/sec)
[134/200] Case ID: 134 (2 images)
  -> gpt_5_5... OK (145.0s | 7048 out / 792 in | 48.6 tok/sec)
  -> claude_4_8_opus... OK (3.9s | 157 out / 1018 in | 40.3 tok/sec)
  -> gemini_3_1_pro... OK (15.4s | 22 out / 2489 in | 1.4 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 819 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (40.4s | 2177 out / 696 in | 53.9 tok/sec)
  -> gemma_4_31b... OK (53.2s | 957 out / 882 in | 18.0 tok/sec)
  -> llama_4_maverick... OK (9.3s | 265 out / 1763 in | 28.5 tok/sec)
  -> mistral_large_3_2512... OK (1.5s | 23 out / 855 in | 15.3 tok/sec)
  -> glm_4_6v... OK (19.2s | 863 out / 827 in | 44.9 tok/sec)
  -> nemotron_3_omni... OK (60.3s | 16384 out / 872 in | 271.7 tok/sec)
[135/200] Case ID: 135 (2 images)
  -> gpt_5_5... OK (11.4s | 547 out / 759 in | 48.0 tok/sec)
  -> claude_4_8_opus... OK (1.7s | 38 out / 972 in | 22.4 tok/sec)
  -> gemini_3_1_pro... OK (16.8s | 21 out / 2498 in | 1.2 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 792 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (59.9s | 2582 out / 657 in | 43.1 tok/sec)
  -> gemma_4_31b... OK (46.9s | 1691 out / 868 in | 36.1 tok/sec)
  -> llama_4_maverick... OK (3.9s | 103 out / 1763 in | 26.4 tok/sec)
  -> mistral_large_3_2512... OK (1.5s | 36 out / 807 in | 24.0 tok/sec)
  -> glm_4_6v... OK (24.7s | 851 out / 752 in | 34.5 tok/sec)
  -> nemotron_3_omni... OK (4.1s | 819 out / 858 in | 199.8 tok/sec)
[136/200] Case ID: 136 (4 images)
  -> gpt_5_5... OK (30.4s | 1578 out / 678 in | 51.9 tok/sec)
  -> claude_4_8_opus... OK (1.6s | 28 out / 908 in | 17.5 tok/sec)
  -> gemini_3_1_pro... OK (19.2s | 21 out / 4683 in | 1.1 tok/sec)
  -> grok_4_20... OK (0.6s | 15 out / 727 in | 25.0 tok/sec)
  -> qwen_3_7_plus... OK (105.5s | 5762 out / 645 in | 54.6 tok/sec)
  -> gemma_4_31b... OK (47.7s | 908 out / 1400 in | 19.0 tok/sec)
  -> llama_4_maverick... OK (6.8s | 194 out / 1187 in | 28.5 tok/sec)
  -> mistral_large_3_2512... OK (1.5s | 31 out / 742 in | 20.7 tok/sec)
  -> glm_4_6v... OK (7.8s | 519 out / 672 in | 66.5 tok/sec)
  -> nemotron_3_omni... OK (7.4s | 1054 out / 1426 in | 142.4 tok/sec)
[137/200] Case ID: 137 (3 images)
  -> gpt_5_5... OK (73.6s | 3433 out / 723 in | 46.6 tok/sec)
  -> claude_4_8_opus... OK (3.2s | 150 out / 987 in | 46.9 tok/sec)
  -> gemini_3_1_pro... OK (16.5s | 24 out / 3591 in | 1.5 tok/sec)
  -> grok_4_20... OK (0.9s | 15 out / 764 in | 16.7 tok/sec)
  -> qwen_3_7_plus... OK (163.8s | 9027 out / 670 in | 55.1 tok/sec)
  -> gemma_4_31b... OK (16.1s | 574 out / 1140 in | 35.7 tok/sec)
  -> llama_4_maverick... OK (5.8s | 242 out / 1910 in | 41.7 tok/sec)
  -> mistral_large_3_2512... OK (2.0s | 34 out / 829 in | 17.0 tok/sec)
  -> glm_4_6v... OK (10.9s | 365 out / 767 in | 33.5 tok/sec)
  -> nemotron_3_omni... OK (2.2s | 362 out / 1155 in | 164.5 tok/sec)
[138/200] Case ID: 138 (3 images)
  -> gpt_5_5... OK (13.9s | 543 out / 738 in | 39.1 tok/sec)
  -> claude_4_8_opus... OK (4.2s | 132 out / 1015 in | 31.4 tok/sec)
  -> gemini_3_1_pro... OK (16.9s | 24 out / 3562 in | 1.4 tok/sec)
  -> grok_4_20... OK (0.6s | 15 out / 776 in | 25.0 tok/sec)
  -> qwen_3_7_plus... OK (22.8s | 1190 out / 694 in | 52.2 tok/sec)
  -> gemma_4_31b... OK (12.3s | 325 out / 1136 in | 26.4 tok/sec)
  -> llama_4_maverick... OK (4.1s | 137 out / 1910 in | 33.4 tok/sec)
  -> mistral_large_3_2512... OK (1.8s | 30 out / 857 in | 16.7 tok/sec)
  -> glm_4_6v... OK (19.8s | 848 out / 748 in | 42.8 tok/sec)
  -> nemotron_3_omni... OK (5.9s | 889 out / 1145 in | 150.7 tok/sec)
[139/200] Case ID: 139 (2 images)
  -> gpt_5_5... OK (12.6s | 541 out / 958 in | 42.9 tok/sec)
  -> claude_4_8_opus... OK (3.3s | 35 out / 1211 in | 10.6 tok/sec)
  -> gemini_3_1_pro... OK (14.6s | 23 out / 2489 in | 1.6 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 958 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (129.7s | 7088 out / 844 in | 54.6 tok/sec)
  -> gemma_4_31b... OK (61.1s | 1439 out / 882 in | 23.6 tok/sec)
  -> llama_4_maverick... OK (3.6s | 143 out / 1763 in | 39.7 tok/sec)
  -> mistral_large_3_2512... OK (1.7s | 26 out / 1052 in | 15.3 tok/sec)
  -> glm_4_6v... OK (9.9s | 646 out / 965 in | 65.3 tok/sec)
  -> nemotron_3_omni... OK (2.1s | 252 out / 906 in | 120.0 tok/sec)
[140/200] Case ID: 140 (1 images)
  -> gpt_5_5... OK (44.8s | 2075 out / 1548 in | 46.3 tok/sec)
  -> claude_4_8_opus... OK (1.9s | 30 out / 1881 in | 15.8 tok/sec)
  -> gemini_3_1_pro... OK (11.5s | 25 out / 1385 in | 2.2 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 1448 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (41.5s | 2188 out / 1329 in | 52.7 tok/sec)
  -> gemma_4_31b... OK (15.7s | 306 out / 604 in | 19.5 tok/sec)
  -> llama_4_maverick... OK (1.1s | 21 out / 2196 in | 19.1 tok/sec)
  -> mistral_large_3_2512... OK (2.2s | 37 out / 1719 in | 16.8 tok/sec)
  -> glm_4_6v... OK (16.0s | 793 out / 1617 in | 49.6 tok/sec)
  -> nemotron_3_omni... OK (5.1s | 1175 out / 1354 in | 230.4 tok/sec)
  Checkpoint saved after 140 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0025.csv
[141/200] Case ID: 141 (1 images)
  -> gpt_5_5... OK (96.3s | 4223 out / 1548 in | 43.9 tok/sec)
  -> claude_4_8_opus... OK (2.1s | 24 out / 1838 in | 11.4 tok/sec)
  -> gemini_3_1_pro... OK (8.5s | 22 out / 1413 in | 2.6 tok/sec)
  -> grok_4_20... OK (0.9s | 15 out / 1448 in | 16.7 tok/sec)
  -> qwen_3_7_plus... OK (45.2s | 2435 out / 1329 in | 53.9 tok/sec)
  -> gemma_4_31b... OK (56.4s | 894 out / 469 in | 15.9 tok/sec)
  -> llama_4_maverick... OK (3.2s | 193 out / 2196 in | 60.3 tok/sec)
  -> mistral_large_3_2512... OK (2.7s | 38 out / 1675 in | 14.1 tok/sec)
  -> glm_4_6v... OK (8.4s | 400 out / 1617 in | 47.6 tok/sec)
  -> nemotron_3_omni... OK (5.7s | 1008 out / 1354 in | 176.8 tok/sec)
[142/200] Case ID: 142 (2 images)
  -> gpt_5_5... OK (29.0s | 1400 out / 939 in | 48.3 tok/sec)
  -> claude_4_8_opus... OK (2.0s | 24 out / 1211 in | 12.0 tok/sec)
  -> gemini_3_1_pro... OK (15.2s | 24 out / 2497 in | 1.6 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 942 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (117.4s | 6430 out / 828 in | 54.8 tok/sec)
  -> gemma_4_31b... OK (28.5s | 1369 out / 884 in | 48.0 tok/sec)
  -> llama_4_maverick... OK (13.4s | 372 out / 1763 in | 27.8 tok/sec)
  -> mistral_large_3_2512... OK (1.7s | 29 out / 1052 in | 17.1 tok/sec)
  -> glm_4_6v... OK (9.6s | 532 out / 965 in | 55.4 tok/sec)
  -> nemotron_3_omni... OK (2.7s | 340 out / 874 in | 125.9 tok/sec)
[143/200] Case ID: 143 (1 images)
  -> gpt_5_5... OK (28.8s | 1058 out / 570 in | 36.7 tok/sec)
  -> claude_4_8_opus... OK (2.3s | 39 out / 805 in | 17.0 tok/sec)
  -> gemini_3_1_pro... OK (11.9s | 24 out / 1385 in | 2.0 tok/sec)
  -> grok_4_20... OK (0.6s | 29 out / 633 in | 48.3 tok/sec)
  -> qwen_3_7_plus... OK (124.6s | 6809 out / 534 in | 54.6 tok/sec)
  -> gemma_4_31b... OK (54.1s | 1364 out / 604 in | 25.2 tok/sec)
  -> llama_4_maverick... OK (2.8s | 137 out / 1036 in | 48.9 tok/sec)
  -> mistral_large_3_2512... OK (1.2s | 25 out / 626 in | 20.8 tok/sec)
  -> glm_4_6v... OK (10.6s | 683 out / 581 in | 64.4 tok/sec)
  -> nemotron_3_omni... OK (7.2s | 1259 out / 584 in | 174.9 tok/sec)
[144/200] Case ID: 144 (1 images)
  -> gpt_5_5... OK (119.1s | 5145 out / 859 in | 43.2 tok/sec)
  -> claude_4_8_opus... OK (4.6s | 34 out / 1080 in | 7.4 tok/sec)
  -> gemini_3_1_pro... OK (45.7s | 25 out / 1409 in | 0.5 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 874 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (66.1s | 3459 out / 750 in | 52.3 tok/sec)
  -> gemma_4_31b... OK (9.9s | 529 out / 610 in | 53.4 tok/sec)
  -> llama_4_maverick... OK (1.5s | 72 out / 1326 in | 48.0 tok/sec)
  -> mistral_large_3_2512... OK (1.7s | 32 out / 909 in | 18.8 tok/sec)
  -> glm_4_6v... OK (9.3s | 685 out / 867 in | 73.7 tok/sec)
  -> nemotron_3_omni... OK (4.2s | 742 out / 780 in | 176.7 tok/sec)
[145/200] Case ID: 145 (1 images)
  -> gpt_5_5... OK (88.3s | 4020 out / 809 in | 45.5 tok/sec)
  -> claude_4_8_opus... OK (1.6s | 24 out / 1034 in | 15.0 tok/sec)
  -> gemini_3_1_pro... OK (18.9s | 24 out / 1410 in | 1.3 tok/sec)
  -> grok_4_20... OK (0.9s | 15 out / 832 in | 16.7 tok/sec)
  -> qwen_3_7_plus... OK (189.3s | 10409 out / 730 in | 55.0 tok/sec)
  -> gemma_4_31b... OK (12.5s | 1102 out / 594 in | 88.2 tok/sec)
  -> llama_4_maverick... OK (1.5s | 30 out / 1036 in | 20.0 tok/sec)
  -> mistral_large_3_2512... OK (1.9s | 32 out / 863 in | 16.8 tok/sec)
  -> glm_4_6v... OK (11.8s | 586 out / 844 in | 49.7 tok/sec)
  -> nemotron_3_omni... OK (5.5s | 1075 out / 738 in | 195.5 tok/sec)
[146/200] Case ID: 146 (1 images)
  -> gpt_5_5... OK (193.6s | 9797 out / 929 in | 50.6 tok/sec)
  -> claude_4_8_opus... OK (2.3s | 30 out / 1195 in | 13.0 tok/sec)
  -> gemini_3_1_pro... OK (44.9s | 25 out / 1423 in | 0.6 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 932 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (86.8s | 4733 out / 850 in | 54.5 tok/sec)
  -> gemma_4_31b... OK (76.4s | 605 out / 604 in | 7.9 tok/sec)
  -> llama_4_maverick... OK (3.2s | 77 out / 1326 in | 24.1 tok/sec)
  -> mistral_large_3_2512... OK (24.6s | 34 out / 1024 in | 1.4 tok/sec)
  -> glm_4_6v... OK (14.5s | 641 out / 975 in | 44.2 tok/sec)
  -> nemotron_3_omni... OK (4.3s | 729 out / 838 in | 169.5 tok/sec)
[147/200] Case ID: 147 (1 images)
  -> gpt_5_5... OK (50.6s | 2094 out / 689 in | 41.4 tok/sec)
  -> claude_4_8_opus... OK (1.5s | 29 out / 942 in | 19.3 tok/sec)
  -> gemini_3_1_pro... OK (8.0s | 26 out / 1431 in | 3.2 tok/sec)
  -> grok_4_20... OK (1.1s | 15 out / 732 in | 13.6 tok/sec)
  -> qwen_3_7_plus... OK (20.2s | 1010 out / 650 in | 50.0 tok/sec)
  -> gemma_4_31b... OK (88.7s | 1115 out / 608 in | 12.6 tok/sec)
  -> llama_4_maverick... OK (3.8s | 122 out / 1036 in | 32.1 tok/sec)
  -> mistral_large_3_2512... OK (2.0s | 34 out / 771 in | 17.0 tok/sec)
  -> glm_4_6v... OK (10.8s | 376 out / 729 in | 34.8 tok/sec)
  -> nemotron_3_omni... OK (10.6s | 2286 out / 638 in | 215.7 tok/sec)
[148/200] Case ID: 148 (2 images)
  -> gpt_5_5... OK (90.5s | 4696 out / 1035 in | 51.9 tok/sec)
  -> claude_4_8_opus... OK (5.8s | 311 out / 1306 in | 53.6 tok/sec)
  -> gemini_3_1_pro... OK (13.9s | 22 out / 2489 in | 1.6 tok/sec)
  -> grok_4_20... OK (1.2s | 15 out / 1022 in | 12.5 tok/sec)
  -> qwen_3_7_plus... OK (91.6s | 4978 out / 908 in | 54.3 tok/sec)
  -> gemma_4_31b... OK (33.9s | 828 out / 604 in | 24.4 tok/sec)
  -> llama_4_maverick... OK (2.8s | 91 out / 1763 in | 32.5 tok/sec)
  -> mistral_large_3_2512... OK (2.2s | 35 out / 1151 in | 15.9 tok/sec)
  -> glm_4_6v... OK (30.1s | 1441 out / 1073 in | 47.9 tok/sec)
  -> nemotron_3_omni... OK (83.6s | 16384 out / 938 in | 196.0 tok/sec)
[149/200] Case ID: 149 (2 images)
  -> gpt_5_5... OK (78.9s | 3647 out / 829 in | 46.2 tok/sec)
  -> claude_4_8_opus... OK (4.5s | 184 out / 1080 in | 40.9 tok/sec)
  -> gemini_3_1_pro... OK (14.6s | 24 out / 2539 in | 1.6 tok/sec)
  -> grok_4_20... OK (0.9s | 15 out / 851 in | 16.7 tok/sec)
  -> qwen_3_7_plus... OK (77.9s | 4217 out / 750 in | 54.1 tok/sec)
  -> gemma_4_31b... OK (14.7s | 718 out / 879 in | 48.8 tok/sec)
  -> llama_4_maverick... OK (3.2s | 183 out / 1763 in | 57.2 tok/sec)
  -> mistral_large_3_2512... OK (1.6s | 24 out / 927 in | 15.0 tok/sec)
  -> glm_4_6v... OK (19.5s | 762 out / 842 in | 39.1 tok/sec)
  -> nemotron_3_omni... OK (1.7s | 21 out / 889 in | 12.4 tok/sec)
[150/200] Case ID: 150 (2 images)
  -> gpt_5_5... OK (40.1s | 1575 out / 1035 in | 39.3 tok/sec)
  -> claude_4_8_opus... OK (2.4s | 27 out / 1282 in | 11.2 tok/sec)
  -> gemini_3_1_pro... OK (12.4s | 23 out / 2489 in | 1.9 tok/sec)
  -> grok_4_20... OK (0.9s | 15 out / 1022 in | 16.7 tok/sec)
  -> qwen_3_7_plus... OK (78.4s | 4222 out / 924 in | 53.9 tok/sec)
  -> gemma_4_31b... OK (34.4s | 776 out / 600 in | 22.6 tok/sec)
  -> llama_4_maverick... OK (13.0s | 331 out / 2053 in | 25.5 tok/sec)
  -> mistral_large_3_2512... OK (4.5s | 27 out / 1121 in | 6.0 tok/sec)
  -> glm_4_6v... OK (17.2s | 790 out / 1091 in | 45.9 tok/sec)
  -> nemotron_3_omni... OK (47.0s | 8997 out / 970 in | 191.4 tok/sec)
  Checkpoint saved after 150 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0026.csv
[151/200] Case ID: 151 (1 images)
  -> gpt_5_5... OK (164.8s | 8315 out / 1334 in | 50.5 tok/sec)
  -> claude_4_8_opus... OK (5.7s | 230 out / 1645 in | 40.4 tok/sec)
  -> gemini_3_1_pro... OK (8.3s | 25 out / 1394 in | 3.0 tok/sec)
  -> grok_4_20... OK (1.0s | 15 out / 1270 in | 15.0 tok/sec)
  -> qwen_3_7_plus... OK (56.4s | 2975 out / 1162 in | 52.7 tok/sec)
  -> gemma_4_31b... OK (41.9s | 1097 out / 591 in | 26.2 tok/sec)
  -> llama_4_maverick... OK (6.3s | 198 out / 2196 in | 31.4 tok/sec)
  -> mistral_large_3_2512... OK (2.6s | 29 out / 1481 in | 11.2 tok/sec)
  -> glm_4_6v... OK (11.6s | 507 out / 1425 in | 43.7 tok/sec)
  -> nemotron_3_omni... OK (3.0s | 316 out / 1176 in | 105.3 tok/sec)
[152/200] Case ID: 152 (1 images)
  -> gpt_5_5... OK (8.8s | 360 out / 713 in | 40.9 tok/sec)
  -> claude_4_8_opus... OK (4.1s | 194 out / 965 in | 47.3 tok/sec)
  -> gemini_3_1_pro... OK (12.6s | 23 out / 1401 in | 1.8 tok/sec)
  -> grok_4_20... OK (0.9s | 15 out / 752 in | 16.7 tok/sec)
  -> qwen_3_7_plus... OK (102.7s | 5556 out / 670 in | 54.1 tok/sec)
  -> gemma_4_31b... OK (214.5s | 2057 out / 608 in | 9.6 tok/sec)
  -> llama_4_maverick... OK (3.3s | 140 out / 1036 in | 42.4 tok/sec)
  -> mistral_large_3_2512... OK (2.9s | 22 out / 794 in | 7.6 tok/sec)
  -> glm_4_6v... OK (13.0s | 614 out / 752 in | 47.2 tok/sec)
  -> nemotron_3_omni... OK (4.4s | 621 out / 658 in | 141.1 tok/sec)
[153/200] Case ID: 153 (1 images)
  -> gpt_5_5... OK (43.6s | 2096 out / 881 in | 48.1 tok/sec)
  -> claude_4_8_opus... OK (3.3s | 109 out / 1121 in | 33.0 tok/sec)
  -> gemini_3_1_pro... OK (14.6s | 22 out / 1394 in | 1.5 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 892 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (213.6s | 11769 out / 786 in | 55.1 tok/sec)
  -> gemma_4_31b... OK (9.4s | 326 out / 590 in | 34.7 tok/sec)
  -> llama_4_maverick... OK (2.6s | 91 out / 1326 in | 35.0 tok/sec)
  -> mistral_large_3_2512... OK (6.4s | 24 out / 949 in | 3.8 tok/sec)
  -> glm_4_6v... OK (6.4s | 221 out / 909 in | 34.5 tok/sec)
  -> nemotron_3_omni... OK (7.6s | 1546 out / 798 in | 203.4 tok/sec)
[154/200] Case ID: 154 (1 images)
  -> gpt_5_5... OK (89.1s | 4172 out / 761 in | 46.8 tok/sec)
  -> claude_4_8_opus... OK (10.2s | 657 out / 988 in | 64.4 tok/sec)
  -> gemini_3_1_pro... OK (13.4s | 24 out / 1409 in | 1.8 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 792 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (69.5s | 3415 out / 672 in | 49.1 tok/sec)
  -> gemma_4_31b... OK (164.2s | 627 out / 610 in | 3.8 tok/sec)
  -> llama_4_maverick... OK (1.5s | 20 out / 1036 in | 13.3 tok/sec)
  -> mistral_large_3_2512... OK (2.4s | 24 out / 817 in | 10.0 tok/sec)
  -> glm_4_6v... OK (8.1s | 375 out / 777 in | 46.3 tok/sec)
  -> nemotron_3_omni... OK (5.5s | 1381 out / 698 in | 251.1 tok/sec)
[155/200] Case ID: 155 (1 images)
  -> gpt_5_5... OK (33.2s | 1573 out / 582 in | 47.4 tok/sec)
  -> claude_4_8_opus... OK (4.6s | 258 out / 793 in | 56.1 tok/sec)
  -> gemini_3_1_pro... OK (12.3s | 21 out / 1402 in | 1.7 tok/sec)
  -> grok_4_20... OK (1.2s | 15 out / 643 in | 12.5 tok/sec)
  -> qwen_3_7_plus... OK (94.8s | 4815 out / 540 in | 50.8 tok/sec)
  -> gemma_4_31b... OK (27.2s | 319 out / 591 in | 11.7 tok/sec)
  -> llama_4_maverick... OK (1.9s | 25 out / 746 in | 13.2 tok/sec)
  -> mistral_large_3_2512... OK (3.9s | 39 out / 623 in | 10.0 tok/sec)
  -> glm_4_6v... OK (19.4s | 845 out / 603 in | 43.6 tok/sec)
  -> nemotron_3_omni... OK (2.1s | 261 out / 594 in | 124.3 tok/sec)
[156/200] Case ID: 156 (5 images)
  -> gpt_5_5... OK (27.3s | 1061 out / 1641 in | 38.9 tok/sec)
  -> claude_4_8_opus... OK (8.2s | 456 out / 1931 in | 55.6 tok/sec)
  -> gemini_3_1_pro... OK (10.8s | 26 out / 5720 in | 2.4 tok/sec)
  -> grok_4_20... OK (1.1s | 15 out / 1532 in | 13.6 tok/sec)
  -> qwen_3_7_plus... OK (98.2s | 4480 out / 1374 in | 45.6 tok/sec)
  -> gemma_4_31b... OK (356.6s | 1507 out / 1630 in | 4.2 tok/sec)
  -> llama_4_maverick... OK (7.1s | 341 out / 3654 in | 48.0 tok/sec)
  -> mistral_large_3_2512... OK (2.4s | 28 out / 1839 in | 11.7 tok/sec)
  -> glm_4_6v... OK (30.2s | 905 out / 1697 in | 30.0 tok/sec)
  -> nemotron_3_omni... OK (28.0s | 5592 out / 1760 in | 199.7 tok/sec)
[157/200] Case ID: 157 (2 images)
  -> gpt_5_5... OK (88.3s | 3650 out / 1040 in | 41.3 tok/sec)
  -> claude_4_8_opus... OK (7.1s | 218 out / 1327 in | 30.7 tok/sec)
  -> gemini_3_1_pro... OK (30.6s | 22 out / 2508 in | 0.7 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 1026 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (137.8s | 6678 out / 926 in | 48.5 tok/sec)
  -> gemma_4_31b... OK (21.2s | 491 out / 604 in | 23.2 tok/sec)
  -> llama_4_maverick... OK (2.2s | 150 out / 1763 in | 68.2 tok/sec)
  -> mistral_large_3_2512... OK (2.3s | 30 out / 1172 in | 13.0 tok/sec)
  -> glm_4_6v... OK (69.4s | 397 out / 1057 in | 5.7 tok/sec)
  -> nemotron_3_omni... OK (2.8s | 291 out / 956 in | 103.9 tok/sec)
[158/200] Case ID: 158 (1 images)
  -> gpt_5_5... OK (78.6s | 3658 out / 1334 in | 46.5 tok/sec)
  -> claude_4_8_opus... OK (6.2s | 253 out / 1645 in | 40.8 tok/sec)
  -> gemini_3_1_pro... OK (119.4s | 23 out / 1394 in | 0.2 tok/sec)
  -> grok_4_20... OK (1.3s | 15 out / 1270 in | 11.5 tok/sec)
  -> qwen_3_7_plus... OK (65.7s | 3558 out / 1162 in | 54.2 tok/sec)
  -> gemma_4_31b... OK (43.8s | 771 out / 590 in | 17.6 tok/sec)
  -> llama_4_maverick... OK (2.4s | 83 out / 2196 in | 34.6 tok/sec)
  -> mistral_large_3_2512... OK (5.9s | 30 out / 1481 in | 5.1 tok/sec)
  -> glm_4_6v... OK (17.7s | 843 out / 1425 in | 47.6 tok/sec)
  -> nemotron_3_omni... OK (5.3s | 1375 out / 1176 in | 259.4 tok/sec)
[159/200] Case ID: 159 (3 images)
  -> gpt_5_5... OK (86.5s | 3647 out / 2316 in | 42.2 tok/sec)
  -> claude_4_8_opus... OK (8.8s | 178 out / 2720 in | 20.2 tok/sec)
  -> gemini_3_1_pro... OK (17.1s | 26 out / 3602 in | 1.5 tok/sec)
  -> grok_4_20... OK (1.3s | 15 out / 2092 in | 11.5 tok/sec)
  -> qwen_3_7_plus... OK (83.3s | 4524 out / 1939 in | 54.3 tok/sec)
  -> gemma_4_31b... OK (47.9s | 3651 out / 1140 in | 76.2 tok/sec)
  -> llama_4_maverick... OK (2.4s | 69 out / 4230 in | 28.8 tok/sec)
  -> mistral_large_3_2512... OK (3.9s | 33 out / 2603 in | 8.5 tok/sec)
  -> glm_4_6v... OK (16.9s | 685 out / 2394 in | 40.5 tok/sec)
  -> nemotron_3_omni... OK (3.6s | 342 out / 2013 in | 95.0 tok/sec)
[160/200] Case ID: 160 (3 images)
  -> gpt_5_5... OK (260.4s | 11251 out / 1394 in | 43.2 tok/sec)
  -> claude_4_8_opus... OK (5.4s | 235 out / 1715 in | 43.5 tok/sec)
  -> gemini_3_1_pro... OK (11.2s | 24 out / 3566 in | 2.1 tok/sec)
  -> grok_4_20... OK (1.0s | 15 out / 1323 in | 15.0 tok/sec)
  -> qwen_3_7_plus... OK (102.4s | 5570 out / 1222 in | 54.4 tok/sec)
  -> gemma_4_31b... OK (19.3s | 547 out / 1127 in | 28.3 tok/sec)
  -> llama_4_maverick... OK (3.4s | 166 out / 2490 in | 48.8 tok/sec)
  -> mistral_large_3_2512... OK (3.3s | 36 out / 1582 in | 10.9 tok/sec)
  -> glm_4_6v... OK (18.8s | 807 out / 1448 in | 42.9 tok/sec)
  -> nemotron_3_omni... OK (2.7s | 338 out / 1244 in | 125.2 tok/sec)
  Checkpoint saved after 160 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0027.csv
[161/200] Case ID: 161 (1 images)
  -> gpt_5_5... OK (108.9s | 5206 out / 1334 in | 47.8 tok/sec)
  -> claude_4_8_opus... OK (2.1s | 24 out / 1615 in | 11.4 tok/sec)
  -> gemini_3_1_pro... OK (34.9s | 22 out / 1394 in | 0.6 tok/sec)
  -> grok_4_20... OK (1.0s | 15 out / 1270 in | 15.0 tok/sec)
  -> qwen_3_7_plus... OK (44.8s | 2348 out / 1130 in | 52.4 tok/sec)
  -> gemma_4_31b... OK (26.7s | 537 out / 590 in | 20.1 tok/sec)
  -> llama_4_maverick... OK (2.9s | 171 out / 2196 in | 59.0 tok/sec)
  -> mistral_large_3_2512... OK (2.6s | 24 out / 1451 in | 9.2 tok/sec)
  -> glm_4_6v... OK (16.7s | 435 out / 1388 in | 26.0 tok/sec)
  -> nemotron_3_omni... OK (2.5s | 222 out / 1176 in | 88.8 tok/sec)
[162/200] Case ID: 162 (2 images)
  -> gpt_5_5... OK (217.8s | 9867 out / 1050 in | 45.3 tok/sec)
  -> claude_4_8_opus... OK (3.6s | 144 out / 1278 in | 40.0 tok/sec)
  -> gemini_3_1_pro... OK (27.3s | 24 out / 2498 in | 0.9 tok/sec)
  -> grok_4_20... OK (1.3s | 15 out / 1034 in | 11.5 tok/sec)
  -> qwen_3_7_plus... OK (131.2s | 7091 out / 902 in | 54.0 tok/sec)
  -> gemma_4_31b... OK (40.1s | 1740 out / 861 in | 43.4 tok/sec)
  -> llama_4_maverick... OK (4.6s | 419 out / 1763 in | 91.1 tok/sec)
  -> mistral_large_3_2512... OK (3.2s | 33 out / 1125 in | 10.3 tok/sec)
  -> glm_4_6v... OK (39.0s | 854 out / 1065 in | 21.9 tok/sec)
  -> nemotron_3_omni... OK (7.0s | 2055 out / 950 in | 293.6 tok/sec)
[163/200] Case ID: 163 (2 images)
  -> gpt_5_5... OK (37.0s | 1575 out / 1081 in | 42.6 tok/sec)
  -> claude_4_8_opus... OK (4.7s | 162 out / 1368 in | 34.5 tok/sec)
  -> gemini_3_1_pro... OK (9.2s | 22 out / 2508 in | 2.4 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 1060 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (131.9s | 7196 out / 944 in | 54.6 tok/sec)
  -> gemma_4_31b... OK (15.8s | 770 out / 861 in | 48.7 tok/sec)
  -> llama_4_maverick... OK (4.4s | 209 out / 2053 in | 47.5 tok/sec)
  -> mistral_large_3_2512... OK (1.8s | 34 out / 1211 in | 18.9 tok/sec)
  -> glm_4_6v... OK (10.7s | 619 out / 1115 in | 57.9 tok/sec)
  -> nemotron_3_omni... OK (6.4s | 1227 out / 991 in | 191.7 tok/sec)
[164/200] Case ID: 164 (1 images)
  -> gpt_5_5... OK (29.2s | 1058 out / 1334 in | 36.2 tok/sec)
  -> claude_4_8_opus... OK (7.0s | 159 out / 1578 in | 22.7 tok/sec)
  -> gemini_3_1_pro... OK (9.9s | 22 out / 1394 in | 2.2 tok/sec)
  -> grok_4_20... OK (0.9s | 15 out / 1270 in | 16.7 tok/sec)
  -> qwen_3_7_plus... OK (33.7s | 1659 out / 1130 in | 49.2 tok/sec)
  -> gemma_4_31b... OK (19.6s | 247 out / 469 in | 12.6 tok/sec)
  -> llama_4_maverick... OK (2.2s | 80 out / 2196 in | 36.4 tok/sec)
  -> mistral_large_3_2512... OK (6.8s | 31 out / 1413 in | 4.6 tok/sec)
  -> glm_4_6v... OK (10.1s | 622 out / 1388 in | 61.6 tok/sec)
  -> nemotron_3_omni... OK (5.1s | 903 out / 1176 in | 177.1 tok/sec)
[165/200] Case ID: 165 (1 images)
  -> gpt_5_5... OK (49.6s | 2092 out / 473 in | 42.2 tok/sec)
  -> claude_4_8_opus... OK (4.2s | 190 out / 685 in | 45.2 tok/sec)
  -> gemini_3_1_pro... OK (8.5s | 23 out / 1385 in | 2.7 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 552 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (172.7s | 9464 out / 460 in | 54.8 tok/sec)
  -> gemma_4_31b... OK (248.0s | 16384 out / 604 in | 66.1 tok/sec)
  -> llama_4_maverick... OK (2.6s | 71 out / 746 in | 27.3 tok/sec)
  -> mistral_large_3_2512... OK (2.3s | 26 out / 506 in | 11.3 tok/sec)
  -> glm_4_6v... OK (23.2s | 921 out / 480 in | 39.7 tok/sec)
  -> nemotron_3_omni... OK (6.4s | 1364 out / 584 in | 213.1 tok/sec)
[166/200] Case ID: 166 (1 images)
  -> gpt_5_5... OK (13.0s | 540 out / 665 in | 41.5 tok/sec)
  -> claude_4_8_opus... OK (7.4s | 363 out / 897 in | 49.1 tok/sec)
  -> gemini_3_1_pro... OK (14.6s | 21 out / 1425 in | 1.4 tok/sec)
  -> grok_4_20... OK (1.5s | 16 out / 712 in | 10.7 tok/sec)
  -> qwen_3_7_plus... OK (41.8s | 2114 out / 618 in | 50.6 tok/sec)
  -> gemma_4_31b... OK (48.4s | 879 out / 602 in | 18.2 tok/sec)
  -> llama_4_maverick... OK (3.4s | 106 out / 1326 in | 31.2 tok/sec)
  -> mistral_large_3_2512... OK (1.8s | 35 out / 717 in | 19.4 tok/sec)
  -> glm_4_6v... OK (22.1s | 1401 out / 679 in | 63.4 tok/sec)
  -> nemotron_3_omni... OK (28.0s | 4111 out / 618 in | 146.8 tok/sec)
[167/200] Case ID: 167 (1 images)
  -> gpt_5_5... OK (12.8s | 542 out / 593 in | 42.3 tok/sec)
  -> claude_4_8_opus... OK (1.6s | 28 out / 802 in | 17.5 tok/sec)
  -> gemini_3_1_pro... OK (11.7s | 24 out / 1413 in | 2.1 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 652 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (120.3s | 6556 out / 570 in | 54.5 tok/sec)
  -> gemma_4_31b... OK (53.4s | 1131 out / 598 in | 21.2 tok/sec)
  -> llama_4_maverick... OK (4.2s | 187 out / 891 in | 44.5 tok/sec)
  -> mistral_large_3_2512... OK (2.1s | 41 out / 619 in | 19.5 tok/sec)
  -> glm_4_6v... OK (15.2s | 544 out / 612 in | 35.8 tok/sec)
  -> nemotron_3_omni... OK (71.3s | 16384 out / 593 in | 229.8 tok/sec)
[168/200] Case ID: 168 (1 images)
  -> gpt_5_5... OK (25.5s | 1027 out / 477 in | 40.3 tok/sec)
  -> claude_4_8_opus... OK (5.5s | 187 out / 694 in | 34.0 tok/sec)
  -> gemini_3_1_pro... OK (22.3s | 23 out / 1392 in | 1.0 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 556 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (82.0s | 4465 out / 474 in | 54.5 tok/sec)
  -> gemma_4_31b... OK (37.7s | 1571 out / 589 in | 41.7 tok/sec)
  -> llama_4_maverick... OK (4.1s | 137 out / 746 in | 33.4 tok/sec)
  -> mistral_large_3_2512... OK (1.5s | 40 out / 509 in | 26.7 tok/sec)
  -> glm_4_6v... OK (22.4s | 835 out / 495 in | 37.3 tok/sec)
  -> nemotron_3_omni... OK (51.1s | 16384 out / 582 in | 320.6 tok/sec)
[169/200] Case ID: 169 (1 images)
  -> gpt_5_5... OK (64.3s | 3131 out / 657 in | 48.7 tok/sec)
  -> claude_4_8_opus... OK (2.3s | 31 out / 865 in | 13.5 tok/sec)
  -> gemini_3_1_pro... OK (13.6s | 22 out / 1387 in | 1.6 tok/sec)
  -> grok_4_20... OK (1.1s | 15 out / 706 in | 13.6 tok/sec)
  -> qwen_3_7_plus... OK (44.9s | 2329 out / 590 in | 51.9 tok/sec)
  -> gemma_4_31b... OK (401.2s | 16384 out / 598 in | 40.8 tok/sec)
  -> llama_4_maverick... OK (3.1s | 92 out / 1036 in | 29.7 tok/sec)
  -> mistral_large_3_2512... OK (3.1s | 28 out / 686 in | 9.0 tok/sec)
  -> glm_4_6v... OK (8.9s | 157 out / 660 in | 17.6 tok/sec)
  -> nemotron_3_omni... OK (56.5s | 16384 out / 612 in | 290.0 tok/sec)
[170/200] Case ID: 170 (1 images)
  -> gpt_5_5... OK (13.7s | 541 out / 1285 in | 39.5 tok/sec)
  -> claude_4_8_opus... OK (6.8s | 32 out / 1534 in | 4.7 tok/sec)
  -> gemini_3_1_pro... OK (16.3s | 23 out / 1392 in | 1.4 tok/sec)
  -> grok_4_20... OK (1.3s | 15 out / 1229 in | 11.5 tok/sec)
  -> qwen_3_7_plus... OK (55.5s | 2880 out / 1104 in | 51.9 tok/sec)
  -> gemma_4_31b... OK (27.5s | 975 out / 588 in | 35.5 tok/sec)
  -> llama_4_maverick... OK (2.8s | 78 out / 1906 in | 27.9 tok/sec)
  -> mistral_large_3_2512... OK (2.6s | 28 out / 1361 in | 10.8 tok/sec)
  -> glm_4_6v... OK (13.0s | 436 out / 1344 in | 33.5 tok/sec)
  -> nemotron_3_omni... OK (13.1s | 3117 out / 1135 in | 237.9 tok/sec)
  Checkpoint saved after 170 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0028.csv
[171/200] Case ID: 171 (1 images)
  -> gpt_5_5... OK (35.0s | 1438 out / 377 in | 41.1 tok/sec)
  -> claude_4_8_opus... OK (2.5s | 41 out / 582 in | 16.4 tok/sec)
  -> gemini_3_1_pro... OK (8.3s | 23 out / 1396 in | 2.8 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 472 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (38.4s | 1643 out / 407 in | 42.8 tok/sec)
  -> gemma_4_31b... OK (70.8s | 820 out / 590 in | 11.6 tok/sec)
  -> llama_4_maverick... OK (2.5s | 104 out / 456 in | 41.6 tok/sec)
  -> mistral_large_3_2512... OK (7.4s | 35 out / 399 in | 4.7 tok/sec)
  -> glm_4_6v... OK (15.3s | 917 out / 381 in | 59.9 tok/sec)
  -> nemotron_3_omni... OK (6.7s | 1450 out / 604 in | 216.4 tok/sec)
[172/200] Case ID: 172 (1 images)
  -> gpt_5_5... OK (75.4s | 3128 out / 506 in | 41.5 tok/sec)
  -> claude_4_8_opus... OK (4.4s | 44 out / 713 in | 10.0 tok/sec)
  -> gemini_3_1_pro... OK (12.5s | 26 out / 1401 in | 2.1 tok/sec)
  -> grok_4_20... OK (0.9s | 18 out / 580 in | 20.0 tok/sec)
  -> qwen_3_7_plus... OK (120.1s | 6471 out / 473 in | 53.9 tok/sec)
  -> gemma_4_31b... OK (22.4s | 930 out / 608 in | 41.5 tok/sec)
  -> llama_4_maverick... OK (4.3s | 141 out / 1036 in | 32.8 tok/sec)
  -> mistral_large_3_2512... OK (1.7s | 28 out / 532 in | 16.5 tok/sec)
  -> glm_4_6v... OK (13.1s | 524 out / 510 in | 40.0 tok/sec)
  -> nemotron_3_omni... OK (6.7s | 1155 out / 588 in | 172.4 tok/sec)
[173/200] Case ID: 173 (2 images)
  -> gpt_5_5... OK (167.5s | 7793 out / 1335 in | 46.5 tok/sec)
  -> claude_4_8_opus... OK (6.3s | 37 out / 1608 in | 5.9 tok/sec)
  -> gemini_3_1_pro... OK (25.1s | 25 out / 2491 in | 1.0 tok/sec)
  -> grok_4_20... OK (1.2s | 15 out / 1272 in | 12.5 tok/sec)
  -> qwen_3_7_plus... OK (54.2s | 2753 out / 1130 in | 50.8 tok/sec)
  -> gemma_4_31b... OK (23.0s | 515 out / 850 in | 22.4 tok/sec)
  -> llama_4_maverick... OK (2.2s | 87 out / 2343 in | 39.5 tok/sec)
  -> mistral_large_3_2512... OK (2.2s | 34 out / 1461 in | 15.5 tok/sec)
  -> glm_4_6v... OK (16.3s | 655 out / 1349 in | 40.2 tok/sec)
  -> nemotron_3_omni... OK (5.1s | 484 out / 1188 in | 94.9 tok/sec)
[174/200] Case ID: 174 (1 images)
  -> gpt_5_5... OK (12.3s | 502 out / 413 in | 40.8 tok/sec)
  -> claude_4_8_opus... OK (1.6s | 34 out / 615 in | 21.2 tok/sec)
  -> gemini_3_1_pro... OK (7.5s | 29 out / 1406 in | 3.9 tok/sec)
  -> grok_4_20... OK (0.6s | 15 out / 502 in | 25.0 tok/sec)
  -> qwen_3_7_plus... OK (97.5s | 5270 out / 402 in | 54.1 tok/sec)
  -> gemma_4_31b... OK (25.7s | 555 out / 593 in | 21.6 tok/sec)
  -> llama_4_maverick... OK (2.5s | 219 out / 456 in | 87.6 tok/sec)
  -> mistral_large_3_2512... OK (3.1s | 30 out / 432 in | 9.7 tok/sec)
  -> glm_4_6v... OK (18.7s | 1120 out / 425 in | 59.9 tok/sec)
  -> nemotron_3_omni... OK (2.9s | 543 out / 590 in | 187.2 tok/sec)
[175/200] Case ID: 175 (1 images)
  -> gpt_5_5... OK (123.4s | 6088 out / 397 in | 49.3 tok/sec)
  -> claude_4_8_opus... OK (6.7s | 346 out / 589 in | 51.6 tok/sec)
  -> gemini_3_1_pro... OK (18.2s | 24 out / 1396 in | 1.3 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 489 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (36.3s | 1920 out / 407 in | 52.9 tok/sec)
  -> gemma_4_31b... OK (25.1s | 430 out / 590 in | 17.1 tok/sec)
  -> llama_4_maverick... OK (2.2s | 73 out / 456 in | 33.2 tok/sec)
  -> mistral_large_3_2512... OK (1.2s | 22 out / 407 in | 18.3 tok/sec)
  -> glm_4_6v... OK (20.2s | 861 out / 399 in | 42.6 tok/sec)
  -> nemotron_3_omni... OK (12.2s | 2470 out / 591 in | 202.5 tok/sec)
[176/200] Case ID: 176 (1 images)
  -> gpt_5_5... OK (41.3s | 1578 out / 539 in | 38.2 tok/sec)
  -> claude_4_8_opus... OK (5.6s | 196 out / 760 in | 35.0 tok/sec)
  -> gemini_3_1_pro... OK (9.7s | 26 out / 1401 in | 2.7 tok/sec)
  -> grok_4_20... OK (1.0s | 17 out / 607 in | 17.0 tok/sec)
  -> qwen_3_7_plus... OK (78.2s | 4053 out / 498 in | 51.8 tok/sec)
  -> gemma_4_31b... OK (20.1s | 1084 out / 608 in | 53.9 tok/sec)
  -> llama_4_maverick... OK (5.6s | 104 out / 1036 in | 18.6 tok/sec)
  -> mistral_large_3_2512... OK (1.6s | 28 out / 581 in | 17.5 tok/sec)
  -> glm_4_6v... OK (17.7s | 525 out / 539 in | 29.7 tok/sec)
  -> nemotron_3_omni... OK (1.9s | 156 out / 588 in | 82.1 tok/sec)
[177/200] Case ID: 177 (1 images)
  -> gpt_5_5... OK (25.8s | 1201 out / 485 in | 46.6 tok/sec)
  -> claude_4_8_opus... OK (2.3s | 30 out / 692 in | 13.0 tok/sec)
  -> gemini_3_1_pro... OK (19.1s | 26 out / 1428 in | 1.4 tok/sec)
  -> grok_4_20... OK (1.2s | 15 out / 562 in | 12.5 tok/sec)
  -> qwen_3_7_plus... OK (167.2s | 8854 out / 456 in | 53.0 tok/sec)
  -> gemma_4_31b... OK (29.0s | 527 out / 598 in | 18.2 tok/sec)
  -> llama_4_maverick... OK (14.0s | 287 out / 746 in | 20.5 tok/sec)
  -> mistral_large_3_2512... OK (2.1s | 33 out / 509 in | 15.7 tok/sec)
  -> glm_4_6v... OK (17.0s | 1199 out / 491 in | 70.5 tok/sec)
  -> nemotron_3_omni... OK (5.1s | 954 out / 578 in | 187.1 tok/sec)
[178/200] Case ID: 178 (1 images)
  -> gpt_5_5... OK (12.7s | 546 out / 1017 in | 43.0 tok/sec)
  -> claude_4_8_opus... OK (4.8s | 177 out / 1282 in | 36.9 tok/sec)
  -> gemini_3_1_pro... OK (8.8s | 27 out / 1401 in | 3.1 tok/sec)
  -> grok_4_20... OK (0.8s | 18 out / 1006 in | 22.5 tok/sec)
  -> qwen_3_7_plus... OK (53.3s | 2829 out / 906 in | 53.1 tok/sec)
  -> gemma_4_31b... OK (107.4s | 1928 out / 459 in | 18.0 tok/sec)
  -> llama_4_maverick... OK (5.5s | 115 out / 1616 in | 20.9 tok/sec)
  -> mistral_large_3_2512... OK (2.0s | 32 out / 1109 in | 16.0 tok/sec)
  -> glm_4_6v... OK (7.5s | 247 out / 1055 in | 32.9 tok/sec)
  -> nemotron_3_omni... OK (2.9s | 230 out / 912 in | 79.3 tok/sec)
[179/200] Case ID: 179 (1 images)
  -> gpt_5_5... OK (14.4s | 541 out / 401 in | 37.6 tok/sec)
  -> claude_4_8_opus... OK (5.1s | 32 out / 615 in | 6.3 tok/sec)
  -> gemini_3_1_pro... OK (9.1s | 24 out / 1406 in | 2.6 tok/sec)
  -> grok_4_20... OK (0.9s | 15 out / 492 in | 16.7 tok/sec)
  -> qwen_3_7_plus... OK (50.7s | 2285 out / 402 in | 45.1 tok/sec)
  -> gemma_4_31b... OK (16.2s | 884 out / 471 in | 54.6 tok/sec)
  -> llama_4_maverick... OK (3.7s | 74 out / 456 in | 20.0 tok/sec)
  -> mistral_large_3_2512... OK (1.1s | 22 out / 432 in | 20.0 tok/sec)
  -> glm_4_6v... OK (29.8s | 967 out / 405 in | 32.4 tok/sec)
  -> nemotron_3_omni... OK (2.4s | 153 out / 588 in | 63.8 tok/sec)
[180/200] Case ID: 180 (1 images)
  -> gpt_5_5... OK (48.6s | 2093 out / 473 in | 43.1 tok/sec)
  -> claude_4_8_opus... OK (1.6s | 32 out / 681 in | 20.0 tok/sec)
  -> gemini_3_1_pro... OK (19.1s | 23 out / 1413 in | 1.2 tok/sec)
  -> grok_4_20... OK (1.2s | 15 out / 552 in | 12.5 tok/sec)
  -> qwen_3_7_plus... OK (64.9s | 3064 out / 460 in | 47.2 tok/sec)
  -> gemma_4_31b... OK (12.1s | 1046 out / 604 in | 86.4 tok/sec)
  -> llama_4_maverick... OK (6.0s | 132 out / 746 in | 22.0 tok/sec)
  -> mistral_large_3_2512... OK (1.5s | 30 out / 503 in | 20.0 tok/sec)
  -> glm_4_6v... OK (11.4s | 520 out / 480 in | 45.6 tok/sec)
  -> nemotron_3_omni... OK (3.5s | 321 out / 584 in | 91.7 tok/sec)
  Checkpoint saved after 180 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0029.csv
[181/200] Case ID: 181 (1 images)
  -> gpt_5_5... OK (11.6s | 544 out / 492 in | 46.9 tok/sec)
  -> claude_4_8_opus... OK (4.0s | 187 out / 700 in | 46.8 tok/sec)
  -> gemini_3_1_pro... OK (18.0s | 27 out / 1406 in | 1.5 tok/sec)
  -> grok_4_20... OK (0.7s | 17 out / 568 in | 24.3 tok/sec)
  -> qwen_3_7_plus... OK (47.4s | 2405 out / 462 in | 50.7 tok/sec)
  -> gemma_4_31b... OK (333.8s | 16384 out / 594 in | 49.1 tok/sec)
  -> llama_4_maverick... OK (12.9s | 102 out / 1036 in | 7.9 tok/sec)
  -> mistral_large_3_2512... OK (3.0s | 28 out / 521 in | 9.3 tok/sec)
  -> glm_4_6v... OK (19.1s | 1002 out / 497 in | 52.5 tok/sec)
  -> nemotron_3_omni... OK (6.8s | 1119 out / 590 in | 164.6 tok/sec)
[182/200] Case ID: 182 (1 images)
  -> gpt_5_5... OK (14.6s | 540 out / 641 in | 37.0 tok/sec)
  -> claude_4_8_opus... OK (1.9s | 33 out / 873 in | 17.4 tok/sec)
  -> gemini_3_1_pro... OK (11.5s | 23 out / 1413 in | 2.0 tok/sec)
  -> grok_4_20... OK (0.6s | 15 out / 692 in | 25.0 tok/sec)
  -> qwen_3_7_plus... OK (29.0s | 1498 out / 610 in | 51.7 tok/sec)
  -> gemma_4_31b... OK (163.2s | 6771 out / 604 in | 41.5 tok/sec)
  -> llama_4_maverick... OK (2.2s | 81 out / 1036 in | 36.8 tok/sec)
  -> mistral_large_3_2512... OK (1.4s | 24 out / 695 in | 17.1 tok/sec)
  -> glm_4_6v... OK (12.5s | 437 out / 667 in | 35.0 tok/sec)
  -> nemotron_3_omni... OK (2.7s | 429 out / 598 in | 158.9 tok/sec)
[183/200] Case ID: 183 (2 images)
  -> gpt_5_5... OK (171.2s | 8314 out / 1105 in | 48.6 tok/sec)
  -> claude_4_8_opus... OK (2.4s | 38 out / 1365 in | 15.8 tok/sec)
  -> gemini_3_1_pro... OK (14.2s | 25 out / 2493 in | 1.8 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 1080 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (143.8s | 7855 out / 962 in | 54.6 tok/sec)
  -> gemma_4_31b... OK (26.9s | 285 out / 598 in | 10.6 tok/sec)
  -> llama_4_maverick... OK (16.1s | 117 out / 2053 in | 7.3 tok/sec)
  -> mistral_large_3_2512... OK (2.2s | 30 out / 1203 in | 13.6 tok/sec)
  -> glm_4_6v... OK (17.4s | 682 out / 1133 in | 39.2 tok/sec)
  -> nemotron_3_omni... OK (2.0s | 100 out / 996 in | 50.0 tok/sec)
[184/200] Case ID: 184 (1 images)
  -> gpt_5_5... OK (9.4s | 318 out / 542 in | 33.8 tok/sec)
  -> claude_4_8_opus... OK (2.1s | 29 out / 765 in | 13.8 tok/sec)
  -> gemini_3_1_pro... OK (22.5s | 28 out / 1413 in | 1.2 tok/sec)
  -> grok_4_20... OK (1.0s | 15 out / 610 in | 15.0 tok/sec)
  -> qwen_3_7_plus... OK (92.8s | 4951 out / 517 in | 53.4 tok/sec)
  -> gemma_4_31b... OK (66.1s | 1049 out / 611 in | 15.9 tok/sec)
  -> llama_4_maverick... OK (3.2s | 143 out / 1036 in | 44.7 tok/sec)
  -> mistral_large_3_2512... OK (1.3s | 30 out / 584 in | 23.1 tok/sec)
  -> glm_4_6v... OK (19.4s | 853 out / 555 in | 44.0 tok/sec)
  -> nemotron_3_omni... OK (6.1s | 1147 out / 591 in | 188.0 tok/sec)
[185/200] Case ID: 185 (1 images)
  -> gpt_5_5... OK (78.0s | 3652 out / 434 in | 46.8 tok/sec)
  -> claude_4_8_opus... OK (1.5s | 37 out / 635 in | 24.7 tok/sec)
  -> gemini_3_1_pro... OK (9.1s | 23 out / 1413 in | 2.5 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 520 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (90.4s | 4930 out / 418 in | 54.5 tok/sec)
  -> gemma_4_31b... OK (112.8s | 2370 out / 469 in | 21.0 tok/sec)
  -> llama_4_maverick... OK (4.6s | 81 out / 746 in | 17.6 tok/sec)
  -> mistral_large_3_2512... OK (1.6s | 30 out / 454 in | 18.8 tok/sec)
  -> glm_4_6v... OK (11.5s | 637 out / 432 in | 55.4 tok/sec)
  -> nemotron_3_omni... OK (6.0s | 942 out / 584 in | 157.0 tok/sec)
[186/200] Case ID: 186 (2 images)
  -> gpt_5_5... OK (13.4s | 545 out / 632 in | 40.7 tok/sec)
  -> claude_4_8_opus... OK (3.7s | 141 out / 859 in | 38.1 tok/sec)
  -> gemini_3_1_pro... OK (12.8s | 22 out / 2493 in | 1.7 tok/sec)
  -> grok_4_20... OK (1.4s | 18 out / 686 in | 12.9 tok/sec)
  -> qwen_3_7_plus... OK (37.6s | 1978 out / 585 in | 52.6 tok/sec)
  -> gemma_4_31b... OK (29.7s | 1716 out / 875 in | 57.8 tok/sec)
  -> llama_4_maverick... OK (4.2s | 185 out / 1473 in | 44.0 tok/sec)
  -> mistral_large_3_2512... OK (3.4s | 28 out / 693 in | 8.2 tok/sec)
  -> glm_4_6v... OK (19.0s | 835 out / 637 in | 43.9 tok/sec)
  -> nemotron_3_omni... OK (2.7s | 326 out / 870 in | 120.7 tok/sec)
[187/200] Case ID: 187 (1 images)
  -> gpt_5_5... OK (24.1s | 1062 out / 539 in | 44.1 tok/sec)
  -> claude_4_8_opus... OK (1.9s | 24 out / 760 in | 12.6 tok/sec)
  -> gemini_3_1_pro... OK (10.8s | 29 out / 1406 in | 2.7 tok/sec)
  -> grok_4_20... OK (1.1s | 15 out / 607 in | 13.6 tok/sec)
  -> qwen_3_7_plus... OK (56.3s | 2992 out / 512 in | 53.1 tok/sec)
  -> gemma_4_31b... OK (18.0s | 1227 out / 593 in | 68.2 tok/sec)
  -> llama_4_maverick... OK (7.1s | 146 out / 1036 in | 20.6 tok/sec)
  -> mistral_large_3_2512... OK (2.2s | 36 out / 583 in | 16.4 tok/sec)
  -> glm_4_6v... OK (27.9s | 1117 out / 555 in | 40.0 tok/sec)
  -> nemotron_3_omni... OK (10.4s | 1966 out / 590 in | 189.0 tok/sec)
[188/200] Case ID: 188 (1 images)
  -> gpt_5_5... OK (119.4s | 5316 out / 413 in | 44.5 tok/sec)
  -> claude_4_8_opus... OK (1.6s | 30 out / 615 in | 18.8 tok/sec)
  -> gemini_3_1_pro... OK (7.8s | 23 out / 1409 in | 2.9 tok/sec)
  -> grok_4_20... OK (0.8s | 15 out / 502 in | 18.8 tok/sec)
  -> qwen_3_7_plus... OK (65.4s | 3541 out / 411 in | 54.1 tok/sec)
  -> gemma_4_31b... OK (49.7s | 1779 out / 611 in | 35.8 tok/sec)
  -> llama_4_maverick... OK (2.1s | 103 out / 456 in | 49.0 tok/sec)
  -> mistral_large_3_2512... OK (1.6s | 29 out / 432 in | 18.1 tok/sec)
  -> glm_4_6v... OK (18.2s | 942 out / 415 in | 51.8 tok/sec)
  -> nemotron_3_omni... OK (5.7s | 1559 out / 590 in | 273.5 tok/sec)
[189/200] Case ID: 189 (1 images)
  -> gpt_5_5... OK (12.6s | 474 out / 1595 in | 37.6 tok/sec)
  -> claude_4_8_opus... OK (1.9s | 32 out / 1877 in | 16.8 tok/sec)
  -> gemini_3_1_pro... OK (19.1s | 28 out / 1421 in | 1.5 tok/sec)
  -> grok_4_20... OK (1.0s | 15 out / 1487 in | 15.0 tok/sec)
  -> qwen_3_7_plus... OK (124.6s | 6803 out / 1362 in | 54.6 tok/sec)
  -> gemma_4_31b... OK (43.0s | 1025 out / 602 in | 23.8 tok/sec)
  -> llama_4_maverick... OK (5.4s | 144 out / 2631 in | 26.7 tok/sec)
  -> mistral_large_3_2512... OK (2.7s | 34 out / 1711 in | 12.6 tok/sec)
  -> glm_4_6v... OK (17.8s | 661 out / 1687 in | 37.1 tok/sec)
  -> nemotron_3_omni... OK (2.4s | 172 out / 1393 in | 71.7 tok/sec)
[190/200] Case ID: 190 (1 images)
  -> gpt_5_5... OK (88.7s | 4034 out / 521 in | 45.5 tok/sec)
  -> claude_4_8_opus... OK (1.5s | 41 out / 743 in | 27.3 tok/sec)
  -> gemini_3_1_pro... OK (14.7s | 23 out / 1394 in | 1.6 tok/sec)
  -> grok_4_20... OK (0.8s | 16 out / 592 in | 20.0 tok/sec)
  -> qwen_3_7_plus... OK (57.7s | 3079 out / 510 in | 53.4 tok/sec)
  -> gemma_4_31b... OK (18.0s | 391 out / 590 in | 21.7 tok/sec)
  -> llama_4_maverick... OK (3.7s | 94 out / 1036 in | 25.4 tok/sec)
  -> mistral_large_3_2512... OK (2.6s | 33 out / 566 in | 12.7 tok/sec)
  -> glm_4_6v... OK (15.2s | 606 out / 536 in | 39.9 tok/sec)
  -> nemotron_3_omni... OK (2.0s | 207 out / 588 in | 103.5 tok/sec)
  Checkpoint saved after 190 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0030.csv
[191/200] Case ID: 191 (1 images)
  -> gpt_5_5... OK (104.2s | 4770 out / 523 in | 45.8 tok/sec)
  -> claude_4_8_opus... OK (4.9s | 210 out / 745 in | 42.9 tok/sec)
  -> gemini_3_1_pro... OK (14.6s | 23 out / 1409 in | 1.6 tok/sec)
  -> grok_4_20... OK (0.7s | 15 out / 594 in | 21.4 tok/sec)
  -> qwen_3_7_plus... OK (135.5s | 7427 out / 512 in | 54.8 tok/sec)
  -> gemma_4_31b... OK (18.0s | 346 out / 610 in | 19.2 tok/sec)
  -> llama_4_maverick... OK (8.3s | 19 out / 1036 in | 2.3 tok/sec)
  -> mistral_large_3_2512... OK (2.4s | 27 out / 567 in | 11.2 tok/sec)
  -> glm_4_6v... OK (14.1s | 607 out / 555 in | 43.0 tok/sec)
  -> nemotron_3_omni... OK (1.8s | 177 out / 590 in | 98.3 tok/sec)
[192/200] Case ID: 192 (1 images)
  -> gpt_5_5... OK (25.7s | 1011 out / 506 in | 39.3 tok/sec)
  -> claude_4_8_opus... OK (1.5s | 35 out / 729 in | 23.3 tok/sec)
  -> gemini_3_1_pro... OK (8.7s | 23 out / 1401 in | 2.6 tok/sec)
  -> grok_4_20... OK (0.9s | 18 out / 580 in | 20.0 tok/sec)
  -> qwen_3_7_plus... OK (61.6s | 3321 out / 498 in | 53.9 tok/sec)
  -> gemma_4_31b... OK (15.1s | 343 out / 608 in | 22.7 tok/sec)
  -> llama_4_maverick... OK (13.5s | 187 out / 1036 in | 13.9 tok/sec)
  -> mistral_large_3_2512... OK (2.6s | 27 out / 551 in | 10.4 tok/sec)
  -> glm_4_6v... OK (28.5s | 967 out / 523 in | 33.9 tok/sec)
  -> nemotron_3_omni... OK (4.3s | 653 out / 588 in | 151.9 tok/sec)
[193/200] Case ID: 193 (1 images)
  -> gpt_5_5... OK (14.5s | 540 out / 819 in | 37.2 tok/sec)
  -> claude_4_8_opus... OK (3.7s | 119 out / 1037 in | 32.2 tok/sec)
  -> gemini_3_1_pro... OK (11.1s | 23 out / 1421 in | 2.1 tok/sec)
  -> grok_4_20... OK (0.9s | 15 out / 841 in | 16.7 tok/sec)
  -> qwen_3_7_plus... OK (70.0s | 3432 out / 726 in | 49.0 tok/sec)
  -> gemma_4_31b... OK (111.1s | 3465 out / 472 in | 31.2 tok/sec)
  -> llama_4_maverick... OK (2.6s | 143 out / 1616 in | 55.0 tok/sec)
  -> mistral_large_3_2512... OK (3.7s | 33 out / 857 in | 8.9 tok/sec)
  -> glm_4_6v... OK (22.8s | 1152 out / 847 in | 50.5 tok/sec)
  -> nemotron_3_omni... OK (2.0s | 207 out / 747 in | 103.5 tok/sec)
[194/200] Case ID: 194 (1 images)
  -> gpt_5_5... OK (14.1s | 543 out / 521 in | 38.5 tok/sec)
  -> claude_4_8_opus... OK (4.8s | 256 out / 743 in | 53.3 tok/sec)
  -> gemini_3_1_pro... OK (15.0s | 24 out / 1431 in | 1.6 tok/sec)
  -> grok_4_20... OK (0.9s | 15 out / 592 in | 16.7 tok/sec)
  -> qwen_3_7_plus... OK (116.1s | 5989 out / 498 in | 51.6 tok/sec)
  -> gemma_4_31b... OK (40.3s | 547 out / 608 in | 13.6 tok/sec)
  -> llama_4_maverick... OK (0.9s | 19 out / 1036 in | 21.1 tok/sec)
  -> mistral_large_3_2512... OK (1.7s | 32 out / 563 in | 18.8 tok/sec)
  -> glm_4_6v... OK (12.8s | 577 out / 523 in | 45.1 tok/sec)
  -> nemotron_3_omni... OK (8.0s | 1594 out / 588 in | 199.2 tok/sec)
[195/200] Case ID: 195 (1 images)
  -> gpt_5_5... OK (14.0s | 540 out / 819 in | 38.6 tok/sec)
  -> claude_4_8_opus... OK (4.4s | 200 out / 1037 in | 45.5 tok/sec)
  -> gemini_3_1_pro... OK (16.7s | 25 out / 1401 in | 1.5 tok/sec)
  -> grok_4_20... OK (0.7s | 18 out / 841 in | 25.7 tok/sec)
  -> qwen_3_7_plus... OK (60.3s | 3168 out / 726 in | 52.5 tok/sec)
  -> gemma_4_31b... OK (30.6s | 787 out / 608 in | 25.7 tok/sec)
  -> llama_4_maverick... OK (18.8s | 539 out / 1616 in | 28.7 tok/sec)
  -> mistral_large_3_2512... OK (1.6s | 30 out / 857 in | 18.8 tok/sec)
  -> glm_4_6v... OK (9.8s | 472 out / 847 in | 48.2 tok/sec)
  -> nemotron_3_omni... OK (1.7s | 41 out / 747 in | 24.1 tok/sec)
[196/200] Case ID: 196 (1 images)
  -> gpt_5_5... OK (13.7s | 540 out / 758 in | 39.4 tok/sec)
  -> claude_4_8_opus... OK (1.8s | 29 out / 985 in | 16.1 tok/sec)
  -> gemini_3_1_pro... OK (112.8s | 23 out / 1401 in | 0.2 tok/sec)
  -> grok_4_20... OK (0.9s | 18 out / 790 in | 20.0 tok/sec)
  -> qwen_3_7_plus... OK (133.2s | 7143 out / 687 in | 53.6 tok/sec)
  -> gemma_4_31b... OK (40.3s | 880 out / 608 in | 21.8 tok/sec)
  -> llama_4_maverick... OK (2.6s | 107 out / 1036 in | 41.2 tok/sec)
  -> mistral_large_3_2512... OK (1.9s | 29 out / 811 in | 15.3 tok/sec)
  -> glm_4_6v... OK (12.0s | 584 out / 795 in | 48.7 tok/sec)
  -> nemotron_3_omni... OK (5.0s | 842 out / 696 in | 168.4 tok/sec)
[197/200] Case ID: 197 (1 images)
  -> gpt_5_5... OK (16.2s | 546 out / 621 in | 33.7 tok/sec)
  -> claude_4_8_opus... OK (7.2s | 326 out / 869 in | 45.3 tok/sec)
  -> gemini_3_1_pro... OK (13.4s | 29 out / 1399 in | 2.2 tok/sec)
  -> grok_4_20... OK (0.8s | 18 out / 676 in | 22.5 tok/sec)
  -> qwen_3_7_plus... OK (88.0s | 4542 out / 594 in | 51.6 tok/sec)
  -> gemma_4_31b... OK (12.4s | 501 out / 602 in | 40.4 tok/sec)
  -> llama_4_maverick... OK (1.9s | 63 out / 1326 in | 33.2 tok/sec)
  -> mistral_large_3_2512... OK (1.6s | 28 out / 688 in | 17.5 tok/sec)
  -> glm_4_6v... OK (18.9s | 783 out / 639 in | 41.4 tok/sec)
  -> nemotron_3_omni... OK (4.7s | 605 out / 582 in | 128.7 tok/sec)
[198/200] Case ID: 198 (1 images)
  -> gpt_5_5... OK (84.9s | 4050 out / 539 in | 47.7 tok/sec)
  -> claude_4_8_opus... OK (3.6s | 141 out / 760 in | 39.2 tok/sec)
  -> gemini_3_1_pro... OK (20.8s | 22 out / 1406 in | 1.1 tok/sec)
  -> grok_4_20... OK (0.9s | 15 out / 607 in | 16.7 tok/sec)
  -> qwen_3_7_plus... OK (75.8s | 4111 out / 512 in | 54.2 tok/sec)
  -> gemma_4_31b... OK (18.4s | 863 out / 594 in | 46.9 tok/sec)
  -> llama_4_maverick... OK (1.5s | 19 out / 1036 in | 12.7 tok/sec)
  -> mistral_large_3_2512... OK (1.5s | 23 out / 581 in | 15.3 tok/sec)
  -> glm_4_6v... OK (20.5s | 830 out / 555 in | 40.5 tok/sec)
  -> nemotron_3_omni... OK (9.2s | 1644 out / 590 in | 178.7 tok/sec)
[199/200] Case ID: 199 (1 images)
  -> gpt_5_5... OK (77.9s | 3615 out / 823 in | 46.4 tok/sec)
  -> claude_4_8_opus... OK (6.4s | 335 out / 1094 in | 52.3 tok/sec)
  -> gemini_3_1_pro... OK (14.7s | 25 out / 1439 in | 1.7 tok/sec)
  -> grok_4_20... OK (1.4s | 15 out / 844 in | 10.7 tok/sec)
  -> qwen_3_7_plus... OK (27.9s | 1375 out / 746 in | 49.3 tok/sec)
  -> gemma_4_31b... OK (27.1s | 743 out / 611 in | 27.4 tok/sec)
  -> llama_4_maverick... OK (6.8s | 179 out / 1326 in | 26.3 tok/sec)
  -> mistral_large_3_2512... OK (6.3s | 29 out / 919 in | 4.6 tok/sec)
  -> glm_4_6v... OK (12.1s | 612 out / 855 in | 50.6 tok/sec)
  -> nemotron_3_omni... OK (6.6s | 638 out / 750 in | 96.7 tok/sec)
[200/200] Case ID: 200 (1 images)
  -> gpt_5_5... OK (21.8s | 815 out / 788 in | 37.4 tok/sec)
  -> claude_4_8_opus... OK (1.7s | 37 out / 1009 in | 21.8 tok/sec)
  -> gemini_3_1_pro... OK (32.0s | 22 out / 1434 in | 0.7 tok/sec)
  -> grok_4_20... OK (0.9s | 18 out / 815 in | 20.0 tok/sec)
  -> qwen_3_7_plus... OK (79.7s | 4308 out / 702 in | 54.1 tok/sec)
  -> gemma_4_31b... OK (118.7s | 3334 out / 598 in | 28.1 tok/sec)
  -> llama_4_maverick... OK (7.8s | 201 out / 1326 in | 25.8 tok/sec)
  -> mistral_large_3_2512... OK (1.9s | 28 out / 829 in | 14.7 tok/sec)
  -> glm_4_6v... OK (18.1s | 877 out / 805 in | 48.5 tok/sec)
  -> nemotron_3_omni... OK (2.7s | 527 out / 721 in | 195.2 tok/sec)
  Checkpoint saved after 200 cases: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0031.csv

Complete! Data saved to /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/results.csv
Final numbered backup: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/backups/results_BACKUP_0032.csv
API calls made this run: 1029

FINAL DATAFRAME PREVIEW:
```


**Output 2: `display_data`**

| Unnamed: 0 | Master_Case_ID | Associated_Images | Image_SHA256 | Diagnosis_gpt_5_5 | Likert_gpt_5_5 | Prompt_Tokens_gpt_5_5 | Total_Tokens_Out_gpt_5_5 | Reasoning_Tokens_gpt_5_5 | Latency_gpt_5_5 | Provider_gpt_5_5 | ... | Provider_nemotron_3_omni | Timestamp_UTC_nemotron_3_omni | Reasoning_nemotron_3_omni | Reasoning_Raw_nemotron_3_omni | Reasoning_Details_nemotron_3_omni | Actual_Request_Extra_nemotron_3_omni | Grok_Fallback_Used_nemotron_3_omni | OpenRouter_Response_Model_nemotron_3_omni | Usage_JSON_nemotron_3_omni | Raw_Response_nemotron_3_omni |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1 | 1.png | 6c737472aac9d936 | Carotid-cavernous fistula | 4 | 1284 | 311 | 279 | 10.9 | OpenAI | ... | Nvidia | 2026-06-18T15:31:32.967199+00:00 | The user wants a diagnosis based on the provid... | The user wants a diagnosis based on the provid... | [{"type": "reasoning.text", "text": "The user ... | {"reasoning": {"enabled": true}} |  | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning-... | {"completion_tokens": 11008, "prompt_tokens": ... | {"diagnosis": "Glomus Jugulare Tumor", "likert... |
| 1 | 2 | 2.png | 8d62d1d2ae0e582b | Cerebral autosomal dominant arteriopathy with ... | 3 | 995 | 557 | 512 | 17.2 | OpenAI | ... | Nvidia | 2026-06-18T15:34:26.708547+00:00 | So, let's look at the MRI images. These are br... | So, let's look at the MRI images. These are br... | [{"type": "reasoning.text", "text": "So, let's... | {"reasoning": {"enabled": true}} |  | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning-... | {"completion_tokens": 326, "prompt_tokens": 89... | {"diagnosis": "I don't know", "likert_score": ... |
| 2 | 3 | 3.png | eb8f8768c2407298 | Dysplastic cerebellar gangliocytoma | 4 | 1271 | 354 | 321 | 11.0 | OpenAI | ... | Nvidia | 2026-06-18T15:36:39.364489+00:00 | So, let's analyze the images. The left image i... | So, let's analyze the images. The left image i... | [{"type": "reasoning.text", "text": "So, let's... | {"reasoning": {"enabled": true}} |  | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning-... | {"completion_tokens": 1004, "prompt_tokens": 1... | {"diagnosis": "pilocytic astrocytoma", "likert... |
| 3 | 4 | 4.png | f72d9953cf3a6068 | Anterior sacral meningocele | 4 | 1243 | 449 | 420 | 16.8 | OpenAI | ... | Nvidia | 2026-06-18T15:39:32.960719+00:00 | So, let's look at the MRI images. The images s... | So, let's look at the MRI images. The images s... | [{"type": "reasoning.text", "text": "So, let's... | {"reasoning": {"enabled": true}} |  | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning-... | {"completion_tokens": 677, "prompt_tokens": 11... | {"diagnosis": "Sacrococcygeal teratoma", "like... |
| 4 | 5 | 5.png | 9cfe77862e65dbbc | Baastrup disease | 3 | 1326 | 2094 | 2048 | 65.4 | OpenAI | ... | Nvidia | 2026-06-18T15:43:27.976854+00:00 | So, let's look at the images. These are MRI sc... | So, let's look at the images. These are MRI sc... | [{"type": "reasoning.text", "text": "So, let's... | {"reasoning": {"enabled": true}} |  | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning-... | {"completion_tokens": 1254, "prompt_tokens": 1... | {"diagnosis": "I don't know", "likert_score": ... |


## Cell 5 (code, exec 7)

**Source**

```python
# ==========================================
# 5. SCORER'S VIEW & PIVOT
# ==========================================
df_scorer, display_df, scorer_csv = create_scorer_view(final_output_csv, scorer_csv=scorer_csv)

print(f"Scorer version saved to: {scorer_csv}")
print("\nTRANSPOSED CONSENSUS VIEW:")
display(display_df)
```

**Output 1: `stream`**

_Stream: `stdout`_

```text
Scorer version saved to: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/scorer/scorer_view.csv

TRANSPOSED CONSENSUS VIEW:
```


**Output 2: `display_data`**

| Master_Case_ID | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | ... | 191 | 192 | 193 | 194 | 195 | 196 | 197 | 198 | 199 | 200 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Associated_Images | 1.png | 2.png | 3.png | 4.png | 5.png | 6.png | 7.png | 8.png | 9.png | 10.png | ... | 191.png | 192.png | 193.png | 194.png | 195.png | 196.png | 197.png | 198.png | 199.png | 200.png |
| Diagnosis_gpt_5_5 | Carotid-cavernous fistula | Cerebral autosomal dominant arteriopathy with ... | Dysplastic cerebellar gangliocytoma | Anterior sacral meningocele | Baastrup disease | Rathke cleft cyst | Bilateral retinoblastoma | Eagle syndrome | Calcaneal intraosseous lipoma | Calcaneonavicular coalition | ... | Azygos lobe | Moyamoya disease | Tuberous sclerosis complex | Left slipped capital femoral epiphysis | Right-sided aortic arch | Splenic laceration | Rhizomelic chondrodysplasia punctata | Trichorhinophalangeal syndrome | Bilateral superior semicircular canal dehiscence | Low-flow venous malformation |
| Diagnosis_claude_4_8_opus | Carotid-cavernous fistula with dilated superio... | Brainstem (pontine) glioma | Hemangioblastoma | Myxopapillary ependymoma | Lumbar spondylolisthesis with spinal canal ste... | Rathke cleft cyst | Left orbital cavernous hemangioma | Eagle syndrome | Intraosseous lipoma of the calcaneus | Avulsion fracture of the navicular tuberosity | ... | I don't know | Cerebral arteriovenous malformation | Tuberous sclerosis complex | Ovarian mature cystic teratoma (dermoid cyst) | Thoracic aortic aneurysm | Hepatomegaly | Rickets | Normal hand radiograph | Middle ear cholesteatoma | Myxoid liposarcoma |
| Diagnosis_gemini_3_1_pro | Carotid-cavernous fistula | Multiple system atrophy | Lhermitte-Duclos disease | Lipomyelomeningocele | Tethered cord syndrome | Pituitary apoplexy | Orbital emphysema | Eagle syndrome | Intraosseous lipoma | Calcaneonavicular coalition | ... | Situs inversus | Moyamoya disease | Tuberous sclerosis | Proximal focal femoral deficiency | Brachiocephalic artery aneurysm | Transient hepatic attenuation difference | Rhizomelic chondrodysplasia punctata | Scleroderma | Petrous apex cholesterol granuloma | Venous malformation |
| Diagnosis_grok_4_20 | I don't know | Glioblastoma | I don't know | I don't know | I don't know | Chiari one malformation | I don't know | I don't know | Osteoid osteoma | I don't know | ... | I don't know | Cerebral arteriovenous malformation | I don't know | I don't know | Pulmonary arteriovenous malformation | Hepatic hemangioma | Metaphyseal dysplasia | I don't know | I don't know | Myxoid liposarcoma |
| Diagnosis_qwen_3_7_plus | Carotid cavernous fistula | Multiple system atrophy | Lhermitte-Duclos disease | Anterior sacral meningocele | Kummell disease | Rathke's cleft cyst | Squamous cell carcinoma | Eagle syndrome | Intraosseous lipoma | Calcaneonavicular coalition | ... | Cardiomegaly | Meningioma | Multiplesclerosis | Slipped capital femoral epiphysis | Ascending aortic aneurysm | Hepatocellular carcinoma | Rhizomelic chondrodysplasia punctata | Pseudohypoparathyroidism | Cholesterol granuloma | Varicose veins |
| Diagnosis_gemma_4_31b | Carotid-cavernous fistula | Ependymoma | Hemangioblastoma | Tailgut cyst | Tethered cord syndrome | Rathke cleft cyst | Mucormycosis | Fibrodysplasia ossificans progressiva | Aneurysmal bone cyst | Talar neck fracture | ... | Situs inversus totalis | Moyamoya disease | Multiple Sclerosis | Avascular necrosis of the femoral head | Thymoma | Cirrhosis | Rhizomelic Chondrodysplasia Punctata | Albright hereditary osteodystrophy | Cholesterol granuloma of the petrous apex | Ganglion cyst |
| Diagnosis_llama_4_maverick | Mucocele | Pontine Glioma | Hemangioblastoma | Tethered Cord Syndrome | Lumbar disc herniation | Rathke cleft cyst | Cavernous hemangioma | Mandible fracture | Intraosseous Lipoma | Os trigonum syndrome | ... | Left lower lobe collapse | Moyamoya disease | Multiple Sclerosis | Femoral neck fracture | Substernal Thyroid Goiter | Splenic laceration | Langerhans cell histiocytosis | Rheumatoid arthritis | Cochlear Dysplasia | Subcutaneous Schwannoma |
| Diagnosis_mistral_large_3_2512 | Renal artery aneurysm | Acute ischemic stroke involving the posterior ... | Hepatocellular carcinoma with diffusion restri... | Lumbar spondylolisthesis with degenerative cha... | Lumbar spinal osteomyelitis with epidural abscess | Hepatic hemangioma | Maxillary sinus fungal ball (mycetoma) | Mandibular ameloblastoma | Renal cell carcinoma | Fifth metatarsal base fracture (Jones fracture) | ... | Bilateral pulmonary edema | Cerebral arteriovenous malformation | Chronic subdural hematoma with midline shift | Bilateral avascular necrosis of the femoral heads | Mediastinal teratoma | Hepatic hemangioma | Osteogenesis imperfecta | Rheumatoid arthritis | Middle ear cholesteatoma | Pericardial cyst |
| Diagnosis_glm_4_6v | Carotid-cavernous fistula | I don't know | Cerebellar pilocytic astrocytoma | Lumbar disc herniation | Vertebral hemangioma | Pituitary adenoma | Chronic sinusitis | I don't know | I don't know | Navicular fracture | ... | Left pleural effusion | Cerebral artery stenosis | Subependymal giant cell astrocytoma | Total hip arthroplasty | Thoracic aortic aneurysm | I don't know | Rickets | Polydactyly | Cholesteatoma | I don't know |
| Diagnosis_nemotron_3_omni | Glomus Jugulare Tumor | I don't know | pilocytic astrocytoma | Sacrococcygeal teratoma | I don't know | Neurocysticercosis | Maxillary sinusitis | Vestibular schwannoma | Osteochondroma | distal tibial fracture | ... | I don't know | Glomus jugulare tumor | Multiple Sclerosis | femoral fracture | I don't know | Livermetastasis | Osteopetrosis | normal | Cholesteatoma | Lipoma |
| Likert_gpt_5_5 | 4 | 3 | 4 | 4 | 3 | 3 | 4 | 4 | 4 | 4 | ... | 4 | 4 | 4 | 4 | 3 | 3 | 4 | 3 | 3 | 3 |
| Likert_claude_4_8_opus | 2.0 | 1.0 | 2.0 | 1.0 | 1.0 | 2.0 | 1.0 | 3.0 | 4.0 | 2.0 | ... |  | 2.0 | 2.0 | 3.0 | 1.0 | 1.0 | 2.0 | 1.0 | 1.0 | 1.0 |
| Likert_gemini_3_1_pro | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | ... | 4 | 4 | 4 | 4 | 3 | 4 | 4 | 4 | 3 | 3 |
| Likert_grok_4_20 |  | 3.0 |  |  |  | 4.0 |  |  | 4.0 |  | ... |  | 4.0 |  |  | 4.0 | 4.0 | 2.0 |  |  | 2.0 |
| Likert_qwen_3_7_plus | 4.0 | 4.0 | 4.0 | 3.0 | 3.0 | 3.0 | 2.0 | 3.0 | 4.0 | 4.0 | ... | 3.0 | 3.0 | 4.0 | 3.0 | 4.0 | 3.0 | 4.0 | 3.0 | 3.0 | 3.0 |
| Likert_gemma_4_31b | 3 | 2 | 4 | 3 | 3 | 3 | 2 | 3 | 3 | 4 | ... | 4 | 4 | 3 | 3 | 3 | 3 | 4 | 3 | 3 | 3 |
| Likert_llama_4_maverick | 3.0 | 4.0 | 4.0 | 3.0 | 4.0 | 4.0 | 3.0 | 4.0 | 4.0 | 3.0 | ... | 3.0 | 4.0 | 3.0 | 4.0 | 3.0 | 4.0 | 3.0 | 4.0 | 3.0 | 3.0 |
| Likert_mistral_large_3_2512 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | ... | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 | 3.0 |
| Likert_glm_4_6v | 2.0 |  | 2.0 | 3.0 | 3.0 | 3.0 | 3.0 |  |  | 3.0 | ... | 3.0 | 2.0 | 2.0 | 4.0 | 2.0 |  | 4.0 | 3.0 | 3.0 |  |
| Likert_nemotron_3_omni | 3 |  | 4 | 4 |  | 4 | 3 | 4 | 4 | 4 | ... |  | 4 | 4 | 4 |  | 2 | 4 | 4 | 3 | 4 |


## Cell 6 (code, exec 8)

**Source**

```python
# ==========================================
# 6. READ-ONLY OUTPUT AUDIT
# ==========================================
audit_results = audit_benchmark_output(
    raw_csv=final_output_csv,
    models=ACTIVE_MODELS,
    expected_case_ids=None,  # Use range(1, 201) when auditing the full 200-case dataset.
)

print("DATASET INTEGRITY:")
display(audit_results["dataset_integrity"])

print("\nBUCKET SUMMARY:")
display(audit_results["bucket_summary"])

print("\nSTATUS SUMMARY:")
display(audit_results["status_summary"])

print("\nNO-API CLEANUP TARGETS:")
display(audit_results["no_paid_cleanup"].head(100))

print("\nREPAIR TARGETS:")
display(audit_results["repair_targets"].head(100))

print("\nANALYSIS FLAGS")
display(audit_results["analysis_flags"].head(100))

print("\nPROVIDER CONTENT BLOCKS:")
display(audit_results["provider_content_blocks"].head(100))
```

**Output 1: `stream`**

_Stream: `stdout`_

```text
DATASET INTEGRITY:
```


**Output 2: `display_data`**

| Unnamed: 0 | metric | value |
| --- | --- | --- |
| 0 | rows | 200 |
| 1 | unique_cases | 200 |
| 2 | columns | 163 |
| 3 | models_audited | 10 |
| 4 | expected_case_model_cells | 2000 |
| 5 | duplicate_case_ids | none |
| 6 | missing_expected_case_ids | none |
| 7 | extra_case_ids | none |


**Output 3: `stream`**

_Stream: `stdout`_

```text

BUCKET SUMMARY:
```


**Output 4: `display_data`**

| Unnamed: 0 | bucket | cells |
| --- | --- | --- |
| 0 | accepted | 1985 |
| 1 | paid_repair | 10 |
| 2 | analysis_flag | 5 |


**Output 5: `stream`**

_Stream: `stdout`_

```text

STATUS SUMMARY:
```


**Output 6: `display_data`**

| Unnamed: 0 | status | cells |
| --- | --- | --- |
| 0 | accepted_clean_diagnosis | 1652 |
| 1 | accepted_i_dont_know | 333 |
| 2 | repair_target_parse_failed_empty_raw | 9 |
| 3 | analysis_flag_abstention_variant | 5 |
| 4 | repair_target_parse_failed_raw_not_recoverable | 1 |


**Output 7: `stream`**

_Stream: `stdout`_

```text

NO-API CLEANUP TARGETS:
```


**Output 8: `display_data`**

| Unnamed: 0 | Master_Case_ID | Associated_Images | Image_SHA256 | model | bucket | status | reason | needs_api_repair | repair_attempts_so_far | max_attempts | ... | timestamp_utc | completion_tokens | prompt_tokens | reasoning_tokens | raw_len | hit_max_tokens | raw_preview | rescued_diag | rescued_likert | rescue_method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |


**Output 9: `stream`**

_Stream: `stdout`_

```text

REPAIR TARGETS:
```


**Output 10: `display_data`**

| Unnamed: 0 | Master_Case_ID | Associated_Images | Image_SHA256 | model | bucket | status | reason | needs_api_repair | repair_attempts_so_far | max_attempts | ... | timestamp_utc | completion_tokens | prompt_tokens | reasoning_tokens | raw_len | hit_max_tokens | raw_preview | rescued_diag | rescued_likert | rescue_method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1339 | 134 | 134.1.jpg, 134.2.jpg | 7be71f40da8f0cdf, f59a3797ef0997a2 | nemotron_3_omni | paid_repair | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | True | 0 | 2 | ... | 2026-06-19T10:12:23.894467+00:00 | 16384.0 | 872.0 | 15269.0 | 0 | True |  |  |  |  |
| 1479 | 148 | 148.1.png, 148.2.png | bc43b06dacb68009, 7e55b40f125ef222 | nemotron_3_omni | paid_repair | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | True | 0 | 2 | ... | 2026-06-19T11:10:25.777566+00:00 | 16384.0 | 938.0 | 16442.0 | 0 | True |  |  |  |  |
| 1489 | 149 | 149.1.png, 149.2.png | a5cd9a7a11a76bd5, 4a6d98330ff5c70d | nemotron_3_omni | paid_repair | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | True | 0 | 2 | ... | 2026-06-19T11:14:03.984420+00:00 | 21.0 | 889.0 | 16.0 | 0 | False |  |  |  |  |
| 1645 | 165 | 165.png | 2037eb299a572661 | gemma_4_31b | paid_repair | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | True | 0 | 2 | ... | 2026-06-19T12:42:58.807834+00:00 | 16384.0 | 604.0 | 13928.0 | 0 | True |  |  |  |  |
| 1669 | 167 | 167.png | 80fc3f2bf25ea517 | nemotron_3_omni | paid_repair | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | True | 0 | 2 | ... | 2026-06-19T12:51:29.924864+00:00 | 16384.0 | 593.0 | 1.0 | 0 | True |  |  |  |  |
| 1679 | 168 | 168.png | 994ba0ade5fcb7a0 | nemotron_3_omni | paid_repair | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | True | 0 | 2 | ... | 2026-06-19T12:55:43.280641+00:00 | 16384.0 | 582.0 | 17963.0 | 0 | True |  |  |  |  |
| 1685 | 169 | 169.png | 0a866cb696e6234f | gemma_4_31b | paid_repair | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | True | 0 | 2 | ... | 2026-06-19T13:04:31.050241+00:00 | 16384.0 | 598.0 | 16383.0 | 0 | True |  |  |  |  |
| 1689 | 169 | 169.png | 0a866cb696e6234f | nemotron_3_omni | paid_repair | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | True | 0 | 2 | ... | 2026-06-19T13:05:42.613122+00:00 | 16384.0 | 612.0 | 15023.0 | 0 | True |  |  |  |  |
| 1805 | 181 | 181.png | b6315cd44e2d4dff | gemma_4_31b | paid_repair | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | True | 0 | 2 | ... | 2026-06-19T13:51:09.381882+00:00 | 16384.0 | 594.0 | 15828.0 | 0 | True |  |  |  |  |
| 1829 | 183 | 183.1.png, 183.2.png | fde731d440fe23a7, 0d9a2f7dd51be06c | nemotron_3_omni | paid_repair | repair_target_parse_failed_raw_not_recoverable | parse_failed_raw_not_recoverable | True | 0 | 2 | ... | 2026-06-19T14:02:29.088238+00:00 | 100.0 | 996.0 | 2.0 | 12 | False | I don’t know |  |  |  |


**Output 11: `stream`**

_Stream: `stdout`_

```text

ANALYSIS FLAGS
```


**Output 12: `display_data`**

| Unnamed: 0 | Master_Case_ID | Associated_Images | Image_SHA256 | model | bucket | status | reason | needs_api_repair | repair_attempts_so_far | max_attempts | ... | timestamp_utc | completion_tokens | prompt_tokens | reasoning_tokens | raw_len | hit_max_tokens | raw_preview | rescued_diag | rescued_likert | rescue_method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 399 | 40 | 40.png | 51c956cf17fd45e0 | nemotron_3_omni | analysis_flag | analysis_flag_abstention_variant | abstention_variant_preserve_raw | False | 0 | 0 | ... | 2026-06-18T19:13:07.645153+00:00 | 243.0 | 916.0 | 233.0 | 50 | False | {"diagnosis": "Idon't know", "likert_score": n... |  |  |  |
| 669 | 67 | 67.png | ab1d6b2570ca4471 | nemotron_3_omni | analysis_flag | analysis_flag_abstention_variant | abstention_variant_preserve_raw | False | 0 | 0 | ... | 2026-06-18T21:36:54.502462+00:00 | 383.0 | 663.0 | 412.0 | 50 | False | {"diagnosis": "Idon't know", "likert_score": n... |  |  |  |
| 1119 | 112 | 112.jpg | 3932a75e70a61ccc | nemotron_3_omni | analysis_flag | analysis_flag_abstention_variant | abstention_variant_preserve_raw | False | 0 | 0 | ... | 2026-06-19T08:31:09.014450+00:00 | 273.0 | 1095.0 | 278.0 | 50 | False | {"diagnosis": "Idon't know", "likert_score": n... |  |  |  |
| 1639 | 164 | 164.png | 97b44fda3a00474c | nemotron_3_omni | analysis_flag | analysis_flag_abstention_variant | abstention_variant_preserve_raw | False | 0 | 0 | ... | 2026-06-19T12:34:54.771185+00:00 | 903.0 | 1176.0 | 984.0 | 50 | False | {"diagnosis": "Idon't know", "likert_score": n... |  |  |  |
| 1739 | 174 | 174.png | 3227e478d15054ce | nemotron_3_omni | analysis_flag | analysis_flag_abstention_variant | abstention_variant_preserve_raw | False | 0 | 0 | ... | 2026-06-19T13:23:45.801559+00:00 | 543.0 | 590.0 | 547.0 | 50 | False | {"diagnosis": "Idon't know", "likert_score": n... |  |  |  |


**Output 13: `stream`**

_Stream: `stdout`_

```text

PROVIDER CONTENT BLOCKS:
```


**Output 14: `display_data`**

| Unnamed: 0 | Master_Case_ID | Associated_Images | Image_SHA256 | model | bucket | status | reason | needs_api_repair | repair_attempts_so_far | max_attempts | ... | timestamp_utc | completion_tokens | prompt_tokens | reasoning_tokens | raw_len | hit_max_tokens | raw_preview | rescued_diag | rescued_likert | rescue_method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |


## Cell 7 (code, exec 9)

**Source**

```python
# ==========================================
# 7. TARGETED REPAIR PLAN / RUN
# ==========================================
# Keep REPAIR_CONFIRMATION="NO" to preview the repair plan without API calls or file writes.
# Change to "YES_REPAIR_10" for a capped repair test or "YES_REPAIR_ALL" for all eligible targets.
REPAIR_CONFIRMATION = "NO"

repair_results = run_targeted_repair(
    client=openrouter_client,
    openai_client=openai_client,
    anthropic_client=anthropic_client,
    gemini_client=gemini_client,
    image_folder=master_images_folder,
    input_csv=final_output_csv,
    output_csv=repair_output_csv,
    repair_call_log_csv=repair_call_log_csv,
    repair_plan_csv=repair_plan_csv,
    confirmation=REPAIR_CONFIRMATION,
    models=ACTIVE_MODELS,
    backup_dir=repair_backup_dir,
)

print("\nNO-API CLEANUP PLAN PREVIEW:")
display(repair_results["no_paid_cleanup_plan"].head(100))

print("\nREPAIR PLAN PREVIEW:")
display(repair_results["repair_plan"].head(100))
print("API calls this run:", repair_results["api_calls_this_run"])
print("No-API cleanups applied:", repair_results["no_paid_cleanups_applied"])
print("Repair input CSV:", final_output_csv)
print("Repair output CSV:", repair_results["output_csv"])
print("Repair call log CSV:", repair_results["repair_call_log_csv"])
```

**Output 1: `stream`**

_Stream: `stdout`_

```text

=== TARGETED REPAIR PLAN ===
Input CSV: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/results.csv
Output CSV: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/repair/repaired_results.csv
Repair call log: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/repair/repair_call_log.csv
No-API cleanup rows / affected cells: 0
Repair plan rows / affected cells: 10
Repair reasons:
reason
parse_failed_empty_raw              9
parse_failed_raw_not_recoverable    1
confirmation was NO. No API calls were made, no cleanups were applied, and no files were written.

NO-API CLEANUP PLAN PREVIEW:
```


**Output 2: `display_data`**

```text
Empty DataFrame
Columns: []
Index: []
```


**Output 3: `stream`**

_Stream: `stdout`_

```text

REPAIR PLAN PREVIEW:
```


**Output 4: `display_data`**

| Unnamed: 0 | Master_Case_ID | model | model_id | status | reason | repair_attempts_so_far | max_attempts | remaining_attempts | has_images |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 134 | nemotron_3_omni | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:... | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | 0 | 2 | 2 | True |
| 1 | 148 | nemotron_3_omni | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:... | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | 0 | 2 | 2 | True |
| 2 | 149 | nemotron_3_omni | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:... | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | 0 | 2 | 2 | True |
| 3 | 165 | gemma_4_31b | google/gemma-4-31b-it | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | 0 | 2 | 2 | True |
| 4 | 167 | nemotron_3_omni | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:... | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | 0 | 2 | 2 | True |
| 5 | 168 | nemotron_3_omni | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:... | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | 0 | 2 | 2 | True |
| 6 | 169 | gemma_4_31b | google/gemma-4-31b-it | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | 0 | 2 | 2 | True |
| 7 | 169 | nemotron_3_omni | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:... | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | 0 | 2 | 2 | True |
| 8 | 181 | gemma_4_31b | google/gemma-4-31b-it | repair_target_parse_failed_empty_raw | parse_failed_empty_raw | 0 | 2 | 2 | True |
| 9 | 183 | nemotron_3_omni | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:... | repair_target_parse_failed_raw_not_recoverable | parse_failed_raw_not_recoverable | 0 | 2 | 2 | True |


**Output 5: `stream`**

_Stream: `stdout`_

```text
API calls this run: 0
No-API cleanups applied: 0
Repair input CSV: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/results.csv
Repair output CSV: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/repair/repaired_results.csv
Repair call log CSV: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/repair/repair_call_log.csv
```


## Cell 8 (code, exec 10)

**Source**

```python
# ==========================================
# 8. PROMOTE PRIVATE FINAL FILE
# ==========================================
repair_confirmed = globals().get("REPAIR_CONFIRMATION", "NO") != "NO"
repair_output_ready = repair_confirmed and Path(repair_output_csv).exists()
private_final_source_csv = repair_output_csv if repair_output_ready else final_output_csv
private_final_source_label = "repaired" if repair_output_ready else "raw"

final_manifest = radle_benchmark.promote_final_results(
    source_csv=private_final_source_csv,
    final_csv=final_results_csv,
    manifest_json=final_manifest_json,
    run_id=run_paths["run_id"],
    source_label=private_final_source_label,
    metadata={
        "run_label": RUN_LABEL,
        "test_limit": TEST_LIMIT if TEST_LIMIT is not None else "full",
    },
)

print("Private final source:", private_final_source_csv)
print("Private final CSV:", final_results_csv)
print("Private final manifest:", final_manifest_json)
print("Private final SHA256:", final_manifest["sha256"])
```

**Output 1: `stream`**

_Stream: `stdout`_

```text
Private final source: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/raw/results.csv
Private final CSV: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/final/RadLE_v2_results_final.csv
Private final manifest: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/final/RadLE_v2_results_final_manifest.json
Private final SHA256: 53543631d657349e848b38ea57632d07efbc33c22b72a24733ae107bc84d3d9c
```


## Cell 9 (code, exec 11)

**Source**

```python
# ==========================================
# 9. EXPORT ANSWER-FREE PUBLIC RELEASE TABLES
# ==========================================
public_results_source_csv = final_results_csv if Path(final_results_csv).exists() else final_output_csv
public_call_log_csv = repair_call_log_csv if Path(repair_call_log_csv).exists() else None

public_release_files = radle_benchmark.export_public_release_tables(
    results_csv=public_results_source_csv,
    output_dir=public_release_dir,
    models=ACTIVE_MODELS,
    call_log_csv=public_call_log_csv,
    run_id=run_paths["run_id"],
)

print("Public release source CSV:", public_results_source_csv)
print("Public case-model CSV:", public_release_files["case_model_csv"])
print("Public model summary CSV:", public_release_files["summary_csv"])
print("Public sanitized call log CSV:", public_release_files["sanitized_call_log_csv"])
print("Public manifest:", public_release_files["manifest_json"])
```

**Output 1: `stream`**

_Stream: `stdout`_

```text
Public release source CSV: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/final/RadLE_v2_results_final.csv
Public case-model CSV: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/public_release/RadLE_v2_public_model_results.csv
Public model summary CSV: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/public_release/RadLE_v2_public_model_summary.csv
Public sanitized call log CSV: 
Public manifest: /content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset/Runs/radle_v2/public_release/RadLE_v2_public_manifest.json
```


## Cell 10 (code, exec None)

_No source._

**Outputs**

_No saved outputs._
