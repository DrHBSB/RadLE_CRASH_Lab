#!/usr/bin/env python3
"""Apply the OctoMed-7B post-run cleanup, then re-audit.

Two transforms, both recovering the model's OWN intent from its OWN text (no
re-inference, RadLE prompt/image payload unchanged):

  1. GENERIC (rule-based, not per-case): canonicalize every abstention-variant
     diagnosis (is_abstention_variant, e.g. "I don't know" written with a curly
     apostrophe U+2019) to the straight-quote canonical "I don't know". This is
     glyph/spelling normalization, not a judgment call, so it is applied by rule
     and not listed case-by-case.
  2. ADJUDICATED (explicit sidecar): scripts/radle_octomed_adjudication.json --
     the radiologist-ruled cases (82 "None of the above", 187 "None") where the
     model declined to commit but phrased it non-canonically. Each override is
     applied only after verifying the current value matches the sidecar's "from".

Backs up the raw CSV first, writes in place, then prints a fresh audit so we can
confirm 200/200 accepted before promotion. Idempotent: re-running is a no-op once
values are already canonical.

Usage:
    python scripts/apply_octomed_cleanup.py            # apply + re-audit
    python scripts/apply_octomed_cleanup.py --dry-run  # show planned changes only
"""
import json
import os
import pathlib
import shutil
import sys
from datetime import datetime, timezone

import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import radle_benchmark as rb  # noqa: E402
import radle_medical_custom_runtime as mrt  # noqa: E402

OLLAMA_MODEL = os.environ.get("OLLAMA_OCTOMED_MODEL", "hf.co/mradermacher/OctoMed-7B-GGUF:Q8_0")
MODEL_NAME = "octomed_7b"
RUN_LABEL = "medical_full_200_cases_ollama"
CANONICAL_IDK = "I don't know"
SIDECAR = REPO / "scripts" / "radle_octomed_adjudication.json"


def dataset_root():
    root = os.environ.get("RADLE_LOCAL_DATASET_ROOT") or str(
        pathlib.Path.home() / "radle_dataset" / "RadLE v2 Dataset"
    )
    return pathlib.Path(root)


def main():
    dry_run = "--dry-run" in sys.argv[1:]

    ds = dataset_root()
    run_id = f"{MODEL_NAME}_{RUN_LABEL}"
    paths = mrt.build_medical_run_paths(ds, model_name=MODEL_NAME, run_label=RUN_LABEL, run_id=run_id)
    raw_csv = paths["raw_results_csv"]
    diag_col = f"Diagnosis_{MODEL_NAME}"
    likert_col = f"Likert_{MODEL_NAME}"
    print("Raw CSV:", raw_csv)

    df = pd.read_csv(raw_csv, dtype={"Master_Case_ID": str})
    df["Master_Case_ID"] = df["Master_Case_ID"].apply(rb.normalize_case_id)
    if diag_col not in df.columns:
        raise SystemExit(f"Missing column {diag_col}")

    planned = []

    # 1. Generic abstention-variant canonicalization (curly apostrophe, etc.).
    for i, row in df.iterrows():
        diag = rb.safe_str(row.get(diag_col, ""))
        if rb.is_abstention_variant(diag) and not rb.is_exact_valid_i_dont_know(diag):
            planned.append((row["Master_Case_ID"], "canonicalize", repr(diag), CANONICAL_IDK))
            if not dry_run:
                df.at[i, diag_col] = CANONICAL_IDK
                df.at[i, likert_col] = ""

    # 2. Adjudicated sidecar (explicit, verify 'from').
    sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
    if sidecar.get("model_name") != MODEL_NAME:
        raise SystemExit(f"Sidecar model_name {sidecar.get('model_name')!r} != {MODEL_NAME!r}")
    for ov in sidecar["overrides"]:
        cid = rb.normalize_case_id(ov["master_case_id"])
        mask = df["Master_Case_ID"] == cid
        if not mask.any():
            raise SystemExit(f"Sidecar case {cid} not found in CSV")
        cur = rb.safe_str(df.loc[mask, diag_col].iloc[0])
        if cur.strip() != rb.safe_str(ov["from"]).strip():
            raise SystemExit(
                f"Sidecar case {cid}: current diagnosis {cur!r} != expected 'from' {ov['from']!r}. "
                "Aborting (CSV changed since adjudication)."
            )
        planned.append((cid, "adjudicate", repr(cur), ov["to"]))
        if not dry_run:
            df.loc[mask, diag_col] = ov["to"]
            df.loc[mask, likert_col] = ""

    print(f"\nPlanned changes ({len(planned)}):")
    for cid, kind, frm, to in sorted(planned, key=lambda x: rb.numeric_case_sort_key(x[0])):
        print(f"  case {cid:>4} [{kind:11}] {frm} -> {to!r}")

    if dry_run:
        print("\n--dry-run: no files written.")
        return

    # Backup then write in place.
    backup_dir = pathlib.Path(paths["raw_backup_dir"])
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = backup_dir / f"results_PRE_CLEANUP_{stamp}.csv"
    shutil.copy2(raw_csv, backup)
    print(f"\nBackup written: {backup}")
    df.to_csv(raw_csv, index=False)
    print(f"Wrote cleaned CSV: {raw_csv}")

    # Re-audit.
    idx = rb.build_image_index(paths["master_images_folder"])
    expected = sorted(idx.keys(), key=rb.numeric_case_sort_key)
    models = [{"name": MODEL_NAME, "id": OLLAMA_MODEL, "extra": None}]
    res = rb.audit_benchmark_output(raw_csv, models=models, expected_case_ids=expected)
    print("\n===== POST-CLEANUP BUCKET SUMMARY =====")
    print(res["bucket_summary"].to_string(index=False))
    print("\n===== POST-CLEANUP STATUS SUMMARY =====")
    print(res["status_summary"].to_string(index=False))
    audit = res["audit"]
    n_accepted = int((audit["bucket"] == "accepted").sum())
    print(f"\nAccepted: {n_accepted}/{len(audit)}")
    if n_accepted == len(audit):
        print("ALL ACCEPTED -> clean to promote (no override needed).")
    else:
        print("NOT all accepted -- inspect remaining non-accepted cells before promoting.")
        print(audit[audit["bucket"] != "accepted"][
            ["Master_Case_ID", "bucket", "status", "diagnosis", "likert"]
        ].to_string(index=False))


if __name__ == "__main__":
    main()
