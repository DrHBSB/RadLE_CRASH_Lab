import json
import os

filepath = r'c:\Users\thehb\Documents\RadLE v2\notebooks\RadLE_Medical_Workbench_Runtime.ipynb'
with open(filepath, 'r', encoding='utf-8') as f:
    data = json.load(f)

cells = data.get('cells', [])

def get_source(cell):
    return ''.join(cell.get('source', [])) if isinstance(cell.get('source'), list) else cell.get('source', '')

def set_source(cell, text):
    lines = text.split('\n')
    cell['source'] = [line + '\n' for line in lines[:-1]] + ([lines[-1]] if lines[-1] else [])

new_cells = []
for cell in cells:
    if cell.get('cell_type') != 'code':
        new_cells.append(cell)
        continue
    
    source = get_source(cell)
    
    # 1. Update Cell 2: Cache Routing
    if '# 2. PYTHON DEPENDENCIES + CACHE ROUTING' in source:
        old_cache_logic = """RUNTIME_CACHE_ROOT = pathlib.Path(
    os.environ.get("RADLE_RUNTIME_CACHE_ROOT", str(RUNTIME_ROOT / "radle_runtime_cache"))
).expanduser()"""
        new_cache_logic = """ssd_mount = pathlib.Path("/mnt/disks/models_ssd")
if ssd_mount.exists() and os.path.ismount(str(ssd_mount)):
    default_cache_root = ssd_mount
else:
    default_cache_root = RUNTIME_ROOT / "radle_runtime_cache"

RUNTIME_CACHE_ROOT = pathlib.Path(
    os.environ.get("RADLE_RUNTIME_CACHE_ROOT", str(default_cache_root))
).expanduser()"""
        source = source.replace(old_cache_logic, new_cache_logic)
        set_source(cell, source)
        new_cells.append(cell)
        continue

    # 2. Update Cell 4: Config
    if '# 4. MODEL, SERVER, AND RUN CONFIG' in source:
        # GPU check and tokens
        gpu_logic = """TENSOR_PARALLEL_SIZE = 2
import subprocess
try:
    gpu_count_output = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, check=True).stdout.strip()
    gpu_count = len([line for line in gpu_count_output.split("\\n") if line])
except Exception:
    raise RuntimeError("nvidia-smi failed or is missing. Cannot verify GPU count.")
if TENSOR_PARALLEL_SIZE > 1 and gpu_count < TENSOR_PARALLEL_SIZE:
    raise RuntimeError(f"TENSOR_PARALLEL_SIZE is {TENSOR_PARALLEL_SIZE} but only {gpu_count} GPUs detected.")

GPU_MEMORY_UTILIZATION = 0.85  # Cloud Assist recommendation for L4 multimodal models"""
        source = source.replace('TENSOR_PARALLEL_SIZE = 2\nGPU_MEMORY_UTILIZATION = None  # Use each model default; set manually only if needed.', gpu_logic)
        
        source = source.replace('MAX_MODEL_LEN = 4096', 'MAX_MODEL_LEN = 4096\nMAX_OUTPUT_TOKENS = 1024')
        source = source.replace('EXTRA_SERVER_ARGS = ["--dtype", "bfloat16"]', 'EXTRA_SERVER_ARGS = ["--dtype", "bfloat16", "--enforce-eager"]')
        
        # Add lifecycle variables at the end
        lifecycle_vars = """
active_model = [medical_runtime.get_model_config(SELECTED_MODEL_NAME)]
repair_output_csv = run_paths["repair_results_csv"]
repair_call_log_csv = run_paths["repair_call_log_csv"]
repair_plan_csv = run_paths["repair_plan_csv"]
repair_backup_dir = run_paths["repair_backup_dir"]
final_results_csv = run_paths["final_results_csv"]
final_manifest_json = run_paths["final_manifest_json"]
public_release_dir = run_paths["public_release_dir"]
"""
        source = source + lifecycle_vars
        set_source(cell, source)
        new_cells.append(cell)
        continue

    # 3. Update Cell 7: RUN BENCHMARK
    if '# 7. RUN ONE-MODEL MEDICAL RADLE SMOKE' in source:
        source = source.replace('test_limit=TEST_LIMIT,', 'test_limit=TEST_LIMIT,\n    max_output_tokens=MAX_OUTPUT_TOKENS,')
        set_source(cell, source)
        new_cells.append(cell)
        continue
        
    # 4. Update Cell 8: Audit (change title since it defines active_model before)
    if '# 8. SCORER VIEW + READ-ONLY AUDIT' in source:
        # active_model is now defined in cell 4, so remove it here
        source = source.replace('active_model = [medical_runtime.get_model_config(SELECTED_MODEL_NAME)]\n\n', '')
        set_source(cell, source)
        new_cells.append(cell)
        
        # Now append the new cells 9, 10, 11
        
        # Cell 9: TARGETED REPAIR
        repair_cell = {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": """# ==========================================
# 9. TARGETED REPAIR PLAN / RUN
# ==========================================
REPAIR_CONFIRMATION = "NO"

repair_results = radle_benchmark.run_targeted_repair(
    client=endpoint_client,
    openai_client=None,
    anthropic_client=None,
    gemini_client=None,
    image_folder=master_images_folder,
    input_csv=raw_results_csv,
    output_csv=repair_output_csv,
    repair_call_log_csv=repair_call_log_csv,
    repair_plan_csv=repair_plan_csv,
    confirmation=REPAIR_CONFIRMATION,
    models=active_model,
    backup_dir=repair_backup_dir,
    max_output_tokens=MAX_OUTPUT_TOKENS,
)

print("\\nNO-API CLEANUP PLAN PREVIEW:")
display(repair_results["no_paid_cleanup_plan"].head(100))

print("\\nREPAIR PLAN PREVIEW:")
display(repair_results["repair_plan"].head(100))
print("API calls this run:", repair_results["api_calls_this_run"])
print("No-API cleanups applied:", repair_results["no_paid_cleanups_applied"])
print("Repair input CSV:", raw_results_csv)
print("Repair output CSV:", repair_results["output_csv"])
print("Repair call log CSV:", repair_results["repair_call_log_csv"])
"""
        }
        set_source(repair_cell, repair_cell['source'])
        new_cells.append(repair_cell)
        
        # Cell 10: PROMOTE FINAL FILE
        promote_cell = {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": """# ==========================================
# 10. PROMOTE PRIVATE FINAL FILE
# ==========================================
from pathlib import Path

repair_confirmed = globals().get("REPAIR_CONFIRMATION", "NO") != "NO"
repair_output_ready = repair_confirmed and Path(repair_output_csv).exists()
private_final_source_csv = repair_output_csv if repair_output_ready else raw_results_csv
private_final_source_label = "repaired" if repair_output_ready else "raw"

ALLOW_PROMOTE_WITH_PENDING_REPAIRS = False

# Guardrail: Check audit targets before promotion
audit_pre_promote = radle_benchmark.audit_benchmark_output(
    raw_csv=private_final_source_csv, models=active_model, expected_case_ids=None
)
pending_repairs = len(audit_pre_promote["repair_targets"])
if pending_repairs > 0 and not ALLOW_PROMOTE_WITH_PENDING_REPAIRS:
    print(f"\\nWARNING: {pending_repairs} case-model cells still need repair. Promotion halted.")
    print("Run a full repair, or manually set ALLOW_PROMOTE_WITH_PENDING_REPAIRS=True to override.")
else:
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
"""
        }
        set_source(promote_cell, promote_cell['source'])
        new_cells.append(promote_cell)
        
        # Cell 11: EXPORT PUBLIC
        export_cell = {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": """# ==========================================
# 11. EXPORT ANSWER-FREE PUBLIC RELEASE TABLES
# ==========================================
from pathlib import Path

if not Path(final_results_csv).exists():
    print("ERROR: final_results_csv does not exist. Promotion was likely halted.")
else:
    public_results_source_csv = final_results_csv
    public_call_log_csv = repair_call_log_csv if Path(repair_call_log_csv).exists() else None

    public_release_files = radle_benchmark.export_public_release_tables(
        results_csv=public_results_source_csv,
        output_dir=public_release_dir,
        models=active_model,
        call_log_csv=public_call_log_csv,
        run_id=run_paths["run_id"],
    )

    print("Public release source CSV:", public_results_source_csv)
    print("Public case-model CSV:", public_release_files["case_model_csv"])
    print("Public model summary CSV:", public_release_files["summary_csv"])
    print("Public sanitized call log CSV:", public_release_files["sanitized_call_log_csv"])
    print("Public manifest:", public_release_files["manifest_json"])
"""
        }
        set_source(export_cell, export_cell['source'])
        new_cells.append(export_cell)
        
        continue

    # 5. Update Cell 12: STOP LOCAL SERVER (Rename from 9 to 12)
    if '# 9. STOP LOCAL SERVER WHEN DONE' in source:
        source = source.replace('# 9. STOP LOCAL SERVER WHEN DONE', '# 12. STOP LOCAL SERVER WHEN DONE')
        set_source(cell, source)
        new_cells.append(cell)
        continue
    
    new_cells.append(cell)

data['cells'] = new_cells

with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=1)

print('Updated successfully.')
