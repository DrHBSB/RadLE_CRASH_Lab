import sys
import os
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(r"c:\Users\thehb\Documents\RadLE v2\src")))

import radle_medical_custom_runtime
import radle_benchmark

print("Starting Pre-Flight Tests...\n")

# 1. Mock Data Setup
smoke_dir = Path(r"c:\Users\thehb\Documents\RadLE v2\local_smoke\mock_images")
smoke_dir.mkdir(parents=True, exist_ok=True)
images = ["1.jpg", "2.jpg", "3.1.jpg", "3.2.jpg", "4.jpg"]
for img in images:
    (smoke_dir / img).touch()

output_csv = r"c:\Users\thehb\Documents\RadLE v2\local_smoke\test_output.csv"
if os.path.exists(output_csv):
    os.remove(output_csv)

model_name = "medgemma_1_5_4b"
client = radle_medical_custom_runtime.DryRunOpenAICompatibleClient(model_id=model_name)
model_cfg = radle_medical_custom_runtime.get_model_config(model_name)

# Test 1: Single Image Smoke Test (TEST_LIMIT = 1)
print("--- TEST 1: Single Image Smoke Test ---")
df_1 = radle_medical_custom_runtime.run_medical_model_benchmark(
    client=client,
    model_name=model_name,
    image_folder=str(smoke_dir),
    output_csv=output_csv,
    test_limit=1,
    resume=False
)
assert len(df_1) == 1, f"Expected 1 row, got {len(df_1)}"
print("Test 1 Passed: Successfully processed a single image.")

# Test 2: Multi-Image Grouping Test (TEST_LIMIT = 3)
print("\n--- TEST 2: Multi-Image Grouping Test ---")
df_2 = radle_medical_custom_runtime.run_medical_model_benchmark(
    client=client,
    model_name=model_name,
    image_folder=str(smoke_dir),
    output_csv=output_csv,
    test_limit=3,
    resume=False
)
assert len(df_2) == 3, f"Expected 3 rows, got {len(df_2)}"
case_3 = df_2[df_2["Master_Case_ID"] == "3"].iloc[0]
images_3 = case_3["Associated_Images"]
assert "3.1.jpg" in images_3 and "3.2.jpg" in images_3, f"Grouping failed: {images_3}"
print("Test 2 Passed: Successfully grouped 3.1 and 3.2 into Case 3.")

# Test 3: Schema Validation
print("\n--- TEST 3: Schema Validation ---")
scorer_csv = output_csv.replace(".csv", "_SCORER.csv")
df_scorer, _, _ = radle_benchmark.create_scorer_view(output_csv, scorer_csv=scorer_csv)
assert f"Diagnosis_{model_name}" in df_scorer.columns, "Missing Diagnosis column in scorer view"

audit = radle_benchmark.audit_benchmark_output(
    raw_csv=output_csv,
    models=[model_cfg],
    expected_case_ids=None
)
assert len(audit["repair_targets"]) == 0, "Expected 0 repair targets for mock data"
print("Test 3 Passed: CSV schemas are exact and audit passes.")

# Test 4: Resume/Statefulness Test
print("\n--- TEST 4: Resume/Statefulness Test ---")
# Reset API call counter on client if it exists, or just verify the dataframe
df_4 = radle_medical_custom_runtime.run_medical_model_benchmark(
    client=client,
    model_name=model_name,
    image_folder=str(smoke_dir),
    output_csv=output_csv,
    test_limit=5,
    resume=True
)
assert len(df_4) == 4, f"Expected 4 rows total after resume, got {len(df_4)}"
print("Test 4 Passed: Resume successfully skipped processed cases and appended case 4.")

print("\nALL TESTS PASSED SUCCESSFULLY!")
