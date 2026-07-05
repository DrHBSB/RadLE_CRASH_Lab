# RadLE Stats Script Audit For New `radle_v2` Results

Date: 2026-06-30

Imported script:

- `scripts/radle_rsna_analysis.py`
- Source: `C:\Users\thehb\Documents\RadLE Stats\radle_rsna_analysis.py`
- Import status: byte-identical copy; `py -3.11 -m py_compile scripts\radle_rsna_analysis.py` passes.

Latest result artifact audited:

- `results/radle_v2/final/RadLE_v2_results_final.csv`
- Manifest: `run_id=radle_v2`, `test_limit=full`, `rows=200`, `columns=163`, `case_count=200`
- Manifest SHA-256: `53543631d657349e848b38ea57632d07efbc33c22b72a24733ae107bc84d3d9c`

## Current Script Contract

The imported script is a manuscript-stage scored-analysis script. It expects two human-reviewed wide CSVs:

- scored diagnosis file with `Master_Case_ID`, `Ground_Truth_Diagnosis`, `Diagnosis_Model_A` through `Diagnosis_Model_J`, and `Score_Model_A` through `Score_Model_J`
- Likert review file with `Master_Case_ID`, `Diagnosis_Model_A` through `Diagnosis_Model_J`, and `Likert_Model_A` through `Likert_Model_J`

It then melts those files to long format and computes accuracy, coverage, abstention, calibration, Spearman correlation, high-confidence error rate, and very-high-confidence error rate.

## New `radle_v2` Result Contract

The new full CSV is raw machine output. It has 200 rows and 163 columns with model-name suffixes:

- `gpt_5_5`
- `claude_4_8_opus`
- `gemini_3_1_pro`
- `grok_4_20`
- `qwen_3_7_plus`
- `gemma_4_31b`
- `llama_4_maverick`
- `mistral_large_3_2512`
- `glm_4_6v`
- `nemotron_3_omni`

For each model it has columns like `Diagnosis_<model>`, `Likert_<model>`, `Prompt_Tokens_<model>`, `Latency_<model>`, `Provider_<model>`, and raw response fields.

It does not contain:

- `Ground_Truth_Diagnosis`
- `Score_Model_A` through `Score_Model_J`
- any populated `score_binary` or `score_likert` fields in the public case-model release

## Hard Blockers Before It Can Produce Final Stats

1. Add or join a scoring source.

   The current script cannot compute accuracy, very-high-confidence error, ECE, or Spearman rho from the raw `radle_v2` file alone. The full/scorer files have diagnoses and Likerts but no ground truth and no correctness scores. The public case-model file has `score_binary` and `score_likert` columns, but both are blank for all 2,000 model-case rows.

2. Replace the Model A-J input contract.

   The script currently hard-codes `MODEL_LETTERS = A..J` and expects `Diagnosis_Model_A`, `Score_Model_A`, and `Likert_Model_A` style columns. The new run uses suffix columns like `Diagnosis_gpt_5_5` and `Likert_claude_4_8_opus`.

3. Update the roster.

   The old Stats roster included `Claude Opus 4.7`, `Qwen VL Max`, and `Pixtral Large`. The new run uses `Claude Opus 4.8`, `Qwen 3.7 Plus`, and `Mistral Large 3 2512`. Treat this as a run-specific roster config, not a string replace scattered through the script.

4. Normalize case IDs deliberately.

   The full raw file uses `Master_Case_ID` values like `1` through `200`. The public release uses anonymized IDs like `case_001`. Any scoring join must define one canonical key and test for one-to-one coverage before metrics run.

5. Extend technical-failure classification.

   The raw file contains `PARSE_FAILED` diagnoses. The public case-model file also exposes `response_valid=False` and coarse `error_class` values such as malformed JSON or other errors. A future adapter should classify technical failures from explicit validity/error fields when available, not only from diagnosis text.

6. Derive denominators from data.

   The old script text hard-codes manuscript language like "Across 2,000 model-case interpretations" and assumes 200 cases per model. The implementation mostly uses observed per-model row counts, but all prose and validation should derive from `case_count * model_count` and manifest values.

7. Decide whether provider splits matter.

   The raw full CSV is one column family per model, but providers vary within some models: `gemma_4_31b`, `llama_4_maverick`, and `glm_4_6v` have multiple providers. Existing model-level stats aggregate these rows by model. Provider-level analysis should be a separate output, not mixed into the manuscript table by accident.

## What Can Be Computed Now Without Scoring

From the latest raw/public files, a safe unscored summary can compute:

- response validity rate
- abstention rate
- mean/median Likert among non-abstained valid responses
- latency and token summaries
- provider distribution by model
- parse-failure/error-class counts

It cannot compute:

- diagnostic accuracy
- high-confidence error rate
- very-high-confidence error rate
- ordinal ECE
- Spearman confidence-correctness correlation
- abstract/manuscript claims about correctness

## Recommended Adaptation Shape

Do not mutate `RadLE_v2_results_final.csv`.

Build the adaptation in two layers:

1. A raw-to-canonical adapter that reads the full raw CSV and emits a long, run-native table with:

   - `run_id`
   - `Master_Case_ID`
   - `model_key`
   - `model_name`
   - `provider`
   - `diagnosis`
   - `likert`
   - `response_valid`
   - `abstained`
   - `technical_failure`
   - token/latency fields

2. A scored-analysis layer that joins the canonical long table to a scoring file containing:

   - `Master_Case_ID`
   - `model_key`
   - binary correctness score
   - optional reviewer notes or graded-score fields

Only the scored-analysis layer should compute accuracy, ECE, Spearman rho, and high-confidence error metrics.

## Minimal Code Changes Needed Later

In `scripts/radle_rsna_analysis.py`:

- replace `MODEL_LETTERS` and `UNBLIND_MAP` with a run-specific `MODEL_CONFIG` keyed by raw suffix
- add a `--raw-results` input mode or a separate adapter command
- stop requiring `Diagnosis_Model_*`, `Likert_Model_*`, and `Score_Model_*` when running in raw-results mode
- add explicit scoring-file input for correctness metrics
- derive `n_total`, total interpretations, and output prose from observed data and manifest values
- update `TECH_FAIL_PATTERN` or add structured failure detection from `response_valid` / `error_class`
- write outputs under a run-specific folder such as `outputs/radle_v2_stats/`

## Validation Gates For Future Implementation

Before accepting adapted stats:

- the raw adapter must prove 200 cases x 10 models = 2,000 long rows
- every `(Master_Case_ID, model_key)` pair must be unique
- all 10 expected model keys must be present exactly once per case
- scoring join must prove no missing or duplicate scored pairs before final metrics
- unscored mode must refuse to write accuracy/error/ECE outputs
- scored mode must refuse final manuscript outputs if any answered diagnosis lacks a correctness score
