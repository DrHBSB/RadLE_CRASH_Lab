#!/usr/bin/env python3
"""Promote the Lingshu-32B Ollama run to final + public tables.

Structurally a parametrized copy of promote_internvl_ollama.py. Guarded:
re-audits first and refuses to promote if any cell is non-accepted, EXCEPT for a
narrowly documented single-cell override (PROMOTE_OVERRIDE_CASES). A flagged case
passes ONLY if it is in that allowlist AND fails for the expected invalid-likert
reason AND still carries a committed (non-empty) diagnosis; every other
non-accepted cell (e.g. a truncated case with no complete JSON -> PARSE_FAILED)
still blocks and must be handled via the standard audit/repair path first. The
override mutates NO data -- the raw cell is frozen and the override + rationale is
recorded in the final manifest (see PROMOTE_OVERRIDE_CASES for the case-119
ruling: out-of-range likert kept as-is, treated as blank-weight by the scorer).

KEY DIFFERENCE vs the InternVL/OctoMed promote scripts: this passes
max_output_tokens=MAX_OUTPUT_TOKENS (1024) to audit_benchmark_output. The other
promote scripts omit it and the audit silently uses the module default (16384)
for its truncation check (execplan latent-bug note). Lingshu is the first model
that routinely hits finish_reason=length (its repetition tendency + the 1024
cap), so the audit must be told the real cap to label truncation honestly.

WHY THIS DOES NOT CHANGE ANY SCORE (verified against classify_cell_for_audit):
`hit_max_tokens` is consulted in exactly ONE place -- inside the PARSE_FAILED
branch (radle_benchmark.py:979) -- and only to pick a diagnostic DETAIL label
(`parse_failed_hit_max_tokens` vs `parse_failed_raw_not_recoverable`). It never
moves a cell into the repair bucket and is NEVER consulted for a cell that
extracted a valid diagnosis. A truncated Lingshu loop-case still has a complete
JSON early in the response, so extract_json_safely (take-last) yields a valid
diagnosis/abstention and the cell is `accepted` regardless of truncation. So
passing 1024 only makes the audit's truncation LABEL/column honest; it cannot
turn a clean run into a needs-override run. Take-last genuinely makes truncation
a non-issue for scoring; a truncated case with NO complete JSON correctly falls
through to PARSE_FAILED -> repair target (not a silent accept).

Steps:
  1. Re-audit raw CSV (with the real 1024 cap); require all cells accepted
     except the documented single-cell override(s).
  2. promote_final_results: raw -> final + manifest.
  3. export_public_release_tables: final -> public_release/ (no diagnoses/raw).
  4. Print the public model summary + final sha256.

Usage:
    python scripts/promote_lingshu_ollama.py
"""
import os
import pathlib
import sys

import pandas as pd

pd.set_option("display.max_colwidth", 60)
pd.set_option("display.width", 220)

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import radle_benchmark as rb  # noqa: E402
import radle_medical_custom_runtime as mrt  # noqa: E402

# The served model is the Modelfile-derived, context-capped tag (num_ctx=8192),
# built over hf.co/mradermacher/Lingshu-32B-GGUF:Q8_0.
OLLAMA_MODEL = os.environ.get("OLLAMA_LINGSHU_MODEL", "lingshu-32b-8k")
OLLAMA_BASE_TAG = os.environ.get("OLLAMA_LINGSHU_BASE_TAG", "hf.co/mradermacher/Lingshu-32B-GGUF:Q8_0")
MODEL_NAME = "lingshu_32b"
RUN_LABEL = "medical_full_200_cases_ollama"
# Must match the generation budget the run used (run_lingshu_32b_ollama.py) so the
# audit's truncation check reflects the actual cap, not the module default.
MAX_OUTPUT_TOKENS = int(os.environ.get("LINGSHU_MAX_OUTPUT_TOKENS", "1024"))

# Documented single-cell guardrail override (user + radiologist ruling 2026-07-03).
# Case 119 spiraled into a repetition loop whose self-confidence counter ratcheted
# PAST the 0-4 Likert scale (recorded raw value 8), so the audit correctly flags it
# invalid_or_missing_likert. Per ruling the raw cell is FROZEN -- NOT repaired, NOT
# converted to an abstention: the committed diagnosis is retained as a genuine
# attempt, and the out-of-range likert is treated by the scorer as unmeasured
# (blank weighted score -- invalidate-not-clamp, a pre-registered general rule for
# any value outside 0-4, NOT a case-119 patch). This override only lets promotion
# proceed; it changes no data. It is NARROW: a flagged case is allowed through ONLY
# if it fails for the expected invalid-likert reason AND still has a committed
# (non-empty, non-PARSE_FAILED) diagnosis -- any other failure still blocks.
PROMOTE_OVERRIDE_CASES = {
    "119": (
        "Out-of-range likert (raw=8) from a degenerate repetition spiral confirmed "
        "non-convergent at 8192 ctx (scripts/probe_lingshu_highcap_case.py). "
        "Diagnosis retained as an attempt; likert treated as blank-weight by the "
        "scorer (invalidate-not-clamp). Raw cell frozen, not repaired/abstained."
    ),
}
OVERRIDE_REASON_SUBSTR = "invalid_or_missing_likert"
_NON_DIAG_TOKENS = {"", "nan", "none", "parse_failed", "json_missing_key"}


def dataset_root():
    root = os.environ.get("RADLE_LOCAL_DATASET_ROOT") or str(
        pathlib.Path.home() / "radle_dataset" / "RadLE v2 Dataset"
    )
    return pathlib.Path(root)


def main():
    ds = dataset_root()
    run_id = f"{MODEL_NAME}_{RUN_LABEL}"
    paths = mrt.build_medical_run_paths(ds, model_name=MODEL_NAME, run_label=RUN_LABEL, run_id=run_id)
    raw_csv = paths["raw_results_csv"]
    models = [{"name": MODEL_NAME, "id": OLLAMA_MODEL, "extra": None}]

    idx = rb.build_image_index(paths["master_images_folder"])
    expected = sorted(idx.keys(), key=rb.numeric_case_sort_key)

    # 1. Guard: must be 200/200 accepted. Pass the REAL cap so truncation is
    #    labeled honestly (see module docstring -- does not change any bucket).
    res = rb.audit_benchmark_output(
        raw_csv,
        models=models,
        expected_case_ids=expected,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    audit = res["audit"]
    n_accepted = int((audit["bucket"] == "accepted").sum())
    print(f"Pre-promote audit: {n_accepted}/{len(audit)} accepted (cap={MAX_OUTPUT_TOKENS})")

    # Partition non-accepted cells into (a) documented single-cell overrides and
    # (b) everything else. Only (a) is allowed through; any (b) blocks promotion.
    non_accepted = audit[audit["bucket"] != "accepted"]
    overridden = []
    unexpected = []
    for _, r in non_accepted.iterrows():
        cid = str(r["Master_Case_ID"])
        cell_status = str(r.get("status", ""))
        diag = str(r.get("diagnosis", "")).strip()
        allowlisted = cid in PROMOTE_OVERRIDE_CASES
        reason_ok = OVERRIDE_REASON_SUBSTR in cell_status
        has_diag = diag.lower() not in _NON_DIAG_TOKENS
        if allowlisted and reason_ok and has_diag:
            overridden.append({"case": cid, "status": cell_status, "diagnosis": diag})
        else:
            unexpected.append({"case": cid, "status": cell_status, "diagnosis": diag})

    if unexpected:
        print("\nNon-accepted cells OUTSIDE the documented override -> BLOCKING:")
        print(
            non_accepted[non_accepted["Master_Case_ID"].astype(str).isin(
                [u["case"] for u in unexpected]
            )][["Master_Case_ID", "bucket", "status", "diagnosis", "likert"]].to_string(index=False)
        )
        raise SystemExit("Refusing to promote: non-accepted cells outside the documented override.")

    if overridden:
        print("\nSINGLE-CELL GUARDRAIL OVERRIDE(S) APPLIED (documented; raw data unchanged):")
        for o in overridden:
            print(f"  case {o['case']}: status={o['status']} diag={o['diagnosis']!r}")
            print(f"    -> {PROMOTE_OVERRIDE_CASES[o['case']]}")

    status = res["status_summary"].set_index("status")["cells"].to_dict()
    n_diag = int(status.get("accepted_clean_diagnosis", 0))
    n_idk = int(status.get("accepted_i_dont_know", 0))
    # Committed attempts held under override (e.g. 119) are accepted diagnoses for
    # accuracy but sit outside the accepted bucket, so add them to the attempt count.
    n_diag_override = sum(1 for o in overridden if o["diagnosis"].lower() not in _NON_DIAG_TOKENS)

    # 2. Promote raw -> final with a rich manifest.
    metadata = {
        "model": MODEL_NAME,
        "served_via": "Ollama (OpenAI-compatible endpoint)",
        "ollama_model_tag": OLLAMA_MODEL,
        "ollama_base_tag": OLLAMA_BASE_TAG,
        "quantization": "Q8_0 GGUF (LM) + mmproj (vision projector)",
        "base_model": "Lingshu-32B (Qwen2.5-VL-32B-Instruct medical fine-tune)",
        "temperature": rb.UNIVERSAL_TEMPERATURE,
        "temperature_note": (
            "Ran at UNIVERSAL_TEMPERATURE (0.01) for manuscript parity. q8 quant "
            "+ 0.01 temp are serving differences vs the cloud/vLLM models; record "
            "in methods. No per-model prompt, image payload, sampling, or retry "
            "changes were used."
        ),
        "context_window_note": (
            "num_ctx capped to 8192 via a Modelfile-derived model (lingshu-32b-8k) "
            "-- Ollama's OpenAI endpoint ignores extra_body num_ctx, and the raw "
            "tag's default 32768 context OOMs the vision compute buffer on a 40GB "
            "GPU. Mirrors the vLLM MAX_MODEL_LEN=8192 used for OctoMed/InternVL."
        ),
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "max_output_tokens_note": (
            "Generation budget capped at 1024 (resource cap, not a parity change): "
            "Lingshu emits its answer JSON first and short (largest genuine answer "
            "~172 tokens) but has a repetition tendency that would otherwise burn "
            "the budget. Take-last scoring is unchanged by the cap."
        ),
        "output_format_note": (
            "Lingshu often emits MULTIPLE JSON objects per response (commits a "
            "diagnosis, then a second JSON abstaining). extract_json_safely takes "
            "the LAST valid JSON; per radiologist ruling 2026-07-02 the model's "
            "FINAL JSON counts, so a commit-then-abstain response is a genuine "
            "abstention. No adjudication sidecar or take-first exception was used."
        ),
        "audit_result": (
            f"{n_accepted}/{len(audit)} accepted"
            + (
                f"; {len(overridden)} documented single-cell override(s): "
                + ", ".join(o["case"] for o in overridden)
                if overridden
                else " (no guardrail override needed)"
            )
        ),
        "guardrail_override": (
            {
                "cases": {o["case"]: PROMOTE_OVERRIDE_CASES[o["case"]] for o in overridden},
                "rationale": (
                    "Raw cells frozen per user + radiologist ruling 2026-07-03: the "
                    "committed diagnosis is kept as an attempt and the out-of-range "
                    "likert is treated as unmeasured (blank weighted score, "
                    "invalidate-not-clamp). No data was mutated; the override only "
                    "permits promotion past the all-accepted guard."
                ),
            }
            if overridden
            else None
        ),
        "committed_diagnoses": n_diag + n_diag_override,
        "committed_diagnoses_accepted": n_diag,
        "committed_diagnoses_under_override": n_diag_override,
        "abstentions_i_dont_know": n_idk,
        "cleanup_ref": None,
        "adjudication_ref": None,
    }
    manifest = rb.promote_final_results(
        source_csv=raw_csv,
        final_csv=paths["final_results_csv"],
        manifest_json=paths["final_manifest_json"],
        run_id=run_id,
        source_label="raw_clean",
        metadata=metadata,
    )
    print("\nPromoted -> final:")
    print("  final_csv:", paths["final_results_csv"])
    print("  manifest :", paths["final_manifest_json"])
    print("  sha256   :", manifest["sha256"])
    print(
        f"  split    : {n_diag + n_diag_override} committed diagnoses "
        f"({n_diag} accepted + {n_diag_override} under override) / {n_idk} abstentions"
    )

    # 3. Export public release tables from the final CSV.
    rb.export_public_release_tables(
        results_csv=paths["final_results_csv"],
        output_dir=paths["public_release_dir"],
        models=models,
        run_id=run_id,
    )
    print("\nPublic release dir:", paths["public_release_dir"])

    # 4. Show the public summary.
    summary_csv = os.path.join(paths["public_release_dir"], "RadLE_v2_public_model_summary.csv")
    summ = pd.read_csv(summary_csv)
    print("\n===== PUBLIC MODEL SUMMARY =====")
    print(summ.to_string(index=False))
    print("\nDone. Next: verify stats pipeline, then relay final + public_release off the VM via GCS.")


if __name__ == "__main__":
    main()
