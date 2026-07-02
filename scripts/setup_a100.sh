#!/usr/bin/env bash
#
# setup_a100.sh -- one-shot environment setup for running the Ollama medical-VLM
# benchmark on a fresh GCP Workbench A100 box (e.g. radle-pro-a100-*).
#
# Run this AFTER you have already cloned the repo with your token and checked out
# the branch, i.e. from inside the repo:
#
#     git clone https://x-access-token:<PAT>@github.com/DrHBSB/RadLE_CRASH_Lab.git
#     cd RadLE_CRASH_Lab && git checkout codex/llava-vllm-runtime
#     git remote set-url origin https://github.com/DrHBSB/RadLE_CRASH_Lab.git  # drop token
#     bash scripts/setup_a100.sh
#
# It does NOT clone the repo (you're already in it) and does NOT touch your token.
# It installs Ollama, the API-client Python deps, stages the FROZEN image snapshot
# GCS->VM (byte-identical to prior models -- manuscript parity), and builds the
# context-capped Lingshu model. The probe / shakedown / full run stay MANUAL so
# you eyeball the image-conditioning output and the TEST MODE line before
# committing to 200 cases.
#
# Idempotent: safe to re-run. Overridable via the env vars below.
set -euo pipefail

# ---- Config (override by exporting before running) -------------------------
GCS_BUCKET="${RADLE_GCS_BUCKET:-radle-medical-data-toronto}"
DATASET_SNAPSHOT_ID="${RADLE_DATASET_SNAPSHOT_ID:-radle-v2-frozen-2026-06-29}"
DATASET_ROOT="${RADLE_LOCAL_DATASET_ROOT:-$HOME/radle_dataset/RadLE v2 Dataset}"
BASE_MODEL_TAG="${OLLAMA_LINGSHU_BASE_TAG:-hf.co/mradermacher/Lingshu-32B-GGUF:Q8_0}"
CAPPED_MODEL="${OLLAMA_LINGSHU_MODEL:-lingshu-32b-8k}"
NUM_CTX="${OLLAMA_NUM_CTX:-8192}"
EXPECTED_IMAGES=263

MASTER_SRC="gs://${GCS_BUCKET}/datasets/${DATASET_SNAPSHOT_ID}/RadLE v2 Master Data"
MASTER_DST="${DATASET_ROOT}/RadLE v2 Master Data"

echo "==================================================================="
echo " RadLE A100 setup"
echo "   host:            $(hostname)"
echo "   dataset root:    ${DATASET_ROOT}"
echo "   image snapshot:  ${MASTER_SRC}"
echo "   capped model:    ${CAPPED_MODEL} (num_ctx=${NUM_CTX}) <- ${BASE_MODEL_TAG}"
echo "==================================================================="

# ---- 0. Sanity-check the GPU (warn only) -----------------------------------
echo "[0/5] GPU check"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
  if ! nvidia-smi --query-gpu=name --format=csv,noheader | grep -qi "A100"; then
    echo "  WARN: this does not look like an A100 box. Lingshu Q8 needs ~37GB;"
    echo "        on <40GB single-GPU it may OOM. Continuing anyway."
  fi
else
  echo "  WARN: nvidia-smi not found; cannot verify GPU."
fi

# ---- 1. Ollama (bundles its own CUDA runtime) ------------------------------
echo "[1/5] Ollama"
if command -v ollama >/dev/null 2>&1; then
  echo "  ollama already installed: $(ollama --version 2>/dev/null | head -1)"
else
  curl -fsSL https://ollama.com/install.sh | sh
fi
# Wait for the service to answer before pulling.
for i in $(seq 1 30); do
  if ollama list >/dev/null 2>&1; then break; fi
  echo "  waiting for ollama service... (${i}/30)"; sleep 2
done

# ---- 2. Python deps (API client only -- no torch/vllm) ---------------------
# anthropic + google-genai are REAL installs, not stubs: src/radle_benchmark.py
# imports them at module load, and the standalone scripts import radle_benchmark
# before radle_medical_custom_runtime can install its stubs. No API calls made.
echo "[2/5] Python deps"
python -m pip install --quiet --upgrade openai pandas anthropic google-genai
echo "  installed: openai pandas anthropic google-genai"

# ---- 3. Stage the FROZEN image snapshot GCS -> VM --------------------------
echo "[3/5] Dataset staging (GCS -> VM)"
mkdir -p "${DATASET_ROOT}"
staged_count=0
if [ -d "${MASTER_DST}" ]; then
  staged_count=$(find "${MASTER_DST}" -type f | wc -l | tr -d ' ')
fi
if [ "${staged_count}" -eq "${EXPECTED_IMAGES}" ]; then
  echo "  already staged: ${staged_count} files -- skipping download"
else
  echo "  copying snapshot (${staged_count} present, expecting ${EXPECTED_IMAGES})..."
  gcloud storage cp -r "${MASTER_SRC}" "${DATASET_ROOT}/"
  staged_count=$(find "${MASTER_DST}" -type f | wc -l | tr -d ' ')
fi
echo "  image files present: ${staged_count} (expected ${EXPECTED_IMAGES})"
if [ "${staged_count}" -ne "${EXPECTED_IMAGES}" ]; then
  echo "  ERROR: image count mismatch -- do NOT trust a run until this is ${EXPECTED_IMAGES}." >&2
  exit 1
fi

# ---- 4. Build the context-capped Lingshu model -----------------------------
echo "[4/5] Ollama model (${CAPPED_MODEL})"
ollama pull "${BASE_MODEL_TAG}"
MODELFILE="$(mktemp /tmp/Lingshu_cap.XXXX.Modelfile)"
printf 'FROM %s\nPARAMETER num_ctx %s\n' "${BASE_MODEL_TAG}" "${NUM_CTX}" > "${MODELFILE}"
ollama create "${CAPPED_MODEL}" -f "${MODELFILE}"
rm -f "${MODELFILE}"
echo "  created ${CAPPED_MODEL} (num_ctx=${NUM_CTX})"

# ---- 5. Next steps (manual on purpose) -------------------------------------
echo "[5/5] Setup complete. Next steps (run manually, one line at a time):"
cat <<EOF

  export RADLE_LOCAL_DATASET_ROOT="${DATASET_ROOT}"

  # a) Image-conditioning + single-GPU-fit probe (watch nvidia-smi: ~37GB, no OOM)
  python scripts/ollama_lingshu_probe.py

  # b) Shakedown -- run on its OWN line, no trailing comment. Confirm the output
  #    prints "TEST MODE: Running on first 8 cases only." (if it says
  #    "Cases this run: 200", Ctrl-C and re-issue).
  python scripts/run_lingshu_32b_ollama.py --limit=8

  # c) Full 200-case run (~30 min on the A100)
  python scripts/run_lingshu_32b_ollama.py

  # d) Then: audit -> promote -> export -> sync run folder to
  #    gs://${GCS_BUCKET}/runs/... -> relay to local + verify sha256.
EOF
