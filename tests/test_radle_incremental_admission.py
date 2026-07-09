from __future__ import annotations

import csv
import json
import subprocess
import unittest
import tempfile
from pathlib import Path

import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from radle_incremental_admission import (
    RADIOLOGIST_QUEUE_FIELDS,
    ValidationError,
    audit_finalized_admission,
    audit_judge_evidence,
    allocate_next_candidate_label,
    audit_prepared_staging,
    classify_terminal_state,
    normalize_diagnosis,
    commit_finalized_admission,
    finalize_incremental_admission,
    prepare_incremental_admission,
    project_one_model_package,
    run_synthetic_dual_judge_delta,
    validate_configs,
)


class IncrementalAdmissionConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads((REPO_ROOT / "config/radle_v2_terminal_states.json").read_text(encoding="utf-8"))

    def test_normalizer_boundaries(self) -> None:
        self.assertEqual(normalize_diagnosis(" I don't-know "), "i don t know")
        self.assertEqual(normalize_diagnosis("Idon't know"), "idon t know")
        self.assertEqual(normalize_diagnosis("Diffuse\u2013esophageal   spasm"), "diffuse esophageal spasm")
        self.assertNotEqual(normalize_diagnosis("unknown"), "i don t know")

    def test_candidate_label_sequence(self) -> None:
        self.assertEqual(allocate_next_candidate_label(["Candidate A"]), "Candidate B")
        self.assertEqual(allocate_next_candidate_label(["Candidate Z"]), "Candidate AA")
        self.assertEqual(allocate_next_candidate_label(["Candidate AD"]), "Candidate AE")

    def test_fixture_terminal_states(self) -> None:
        fixture = REPO_ROOT / "tests/fixtures/radle_incremental_admission/unit_cases.csv"
        with fixture.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                with self.subTest(case=row["Master_Case_ID"]):
                    try:
                        state = classify_terminal_state(row, row["ground_truth"], self.policy)
                    except Exception:
                        state = "ERROR"
                    self.assertEqual(state, row["expected_state"])

    def test_config_validation(self) -> None:
        receipt = validate_configs(
            roster_path=REPO_ROOT / "config/radle_v2_model_roster.json",
            judges_path=REPO_ROOT / "config/radle_v2_judges.json",
            states_path=REPO_ROOT / "config/radle_v2_terminal_states.json",
            fixture_csv=REPO_ROOT / "tests/fixtures/radle_incremental_admission/unit_cases.csv",
            repo_root=REPO_ROOT,
        )
        self.assertEqual(receipt["roster"]["active_count"], 15)
        self.assertEqual(receipt["roster"]["excluded_count"], 3)
        self.assertEqual(receipt["roster"]["pending_count"], 3)
        self.assertEqual(receipt["judges"]["judge_count"], 2)


class IncrementalAdmissionPrepareTests(unittest.TestCase):
    def make_fixture(self, tmp_path: Path) -> Path:
        fixture_root = tmp_path / "synthetic_admission"
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "tests/make_radle_incremental_fixture.py"), "--out", str(fixture_root)],
            check=True,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            text=True,
        )
        return fixture_root

    def prepare_args(self, fixture_root: Path, output_root: Path) -> dict[str, object]:
        return {
            "parent_wide": fixture_root / "parent_wide.csv",
            "parent_final_long_master": fixture_root / "parent_final_long_master.csv",
            "parent_authority_manifest": fixture_root / "parent_authority.json",
            "incoming_package": fixture_root / "incoming_package",
            "model_key": "synthetic_model_v1",
            "roster_path": fixture_root / "model_roster.json",
            "variants_path": fixture_root / "accepted_variants.csv",
            "states_path": REPO_ROOT / "config/radle_v2_terminal_states.json",
            "output_root": output_root,
            "repo_root": REPO_ROOT,
        }

    def read_rows(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def write_rows(self, path: Path, rows: list[dict[str, str]]) -> None:
        with path.open("r", encoding="utf-8", newline="") as handle:
            fieldnames = csv.DictReader(handle).fieldnames or []
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def write_radiologist_decisions(self, staging: Path, rows: list[dict[str, str]] | None = None) -> Path:
        if rows is None:
            rows = [
                {
                    "Master_Case_ID": "6",
                    "model_blinded": "Candidate AE",
                    "score_binary": "1",
                    "reviewer_pseudonym": "synthetic_rad",
                    "reviewed_utc": "2026-01-03T00:00:00+00:00",
                    "rationale": "synthetic disagreement decision",
                },
                {
                    "Master_Case_ID": "7",
                    "model_blinded": "Candidate AE",
                    "score_binary": "0",
                    "reviewer_pseudonym": "synthetic_rad",
                    "reviewed_utc": "2026-01-03T00:00:00+00:00",
                    "rationale": "synthetic flag decision",
                },
                {
                    "Master_Case_ID": "164",
                    "model_blinded": "Candidate AE",
                    "score_binary": "0",
                    "reviewer_pseudonym": "synthetic_rad",
                    "reviewed_utc": "2026-01-03T00:00:00+00:00",
                    "rationale": "mandatory review decision",
                },
            ]
        path = staging / "radiologist_decisions.csv"
        fieldnames = ["Master_Case_ID", "model_blinded", "score_binary", "reviewer_pseudonym", "reviewed_utc", "rationale"]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def prepared_with_judges(self, tmp: str) -> tuple[Path, Path]:
        fixture = self.make_fixture(Path(tmp))
        output_root = Path(tmp) / "output"
        receipt = prepare_incremental_admission(**self.prepare_args(fixture, output_root), dry_run=False)
        staging = Path(str(receipt["staging_root"]))
        run_synthetic_dual_judge_delta(
            staging_root=staging,
            judges_path=REPO_ROOT / "config/radle_v2_judges.json",
            out_dir=staging / "judge_evidence",
            repo_root=REPO_ROOT,
            dry_run=False,
        )
        return fixture, staging

    def test_prepare_dry_run_is_idempotent_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.make_fixture(Path(tmp))
            output_root = Path(tmp) / "output"
            args = self.prepare_args(fixture, output_root)
            first = prepare_incremental_admission(**args, dry_run=True)
            second = prepare_incremental_admission(**args, dry_run=True)
            self.assertEqual(first["intake_id"], second["intake_id"])
            self.assertEqual(first["transaction_state"], "DRY_RUN_VALIDATED")
            self.assertFalse(output_root.exists())

    def test_prepare_writes_expected_staging_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.make_fixture(Path(tmp))
            output_root = Path(tmp) / "output"
            args = self.prepare_args(fixture, output_root)
            receipt = prepare_incremental_admission(**args, dry_run=False)
            staging = Path(str(receipt["staging_root"]))
            self.assertEqual(receipt["transaction_state"], "ADJUDICATION_PENDING")
            self.assertEqual(receipt["case_count"], 200)
            self.assertEqual(receipt["judge_worklist_rows"], 194)
            self.assertEqual(receipt["terminal_state_counts"]["invalid_likert"], 2)
            for relative in [
                "requirements_snapshot.json",
                "append_input_manifest.json",
                "canonical_ground_truth_snapshot.csv",
                "provenance/source_manifest.json",
                "audit/promotion_audit.json",
                "one_model_final_wide.csv",
                "combined_wide/RadLE_v2_results_final.csv",
                "scorer/scorer_view.csv",
                "new_model_long_delta.csv",
                "audit/terminal_state_audit.json",
                "accepted_variants_snapshot.csv",
                "judge_worklist.csv",
                "roster/model_roster.json",
                "roster/blind_label_map.json",
            ]:
                self.assertTrue((staging / relative).exists(), relative)
            self.assertFalse((staging / "COMMITTED.json").exists())
            self.assertEqual(len(self.read_rows(staging / "new_model_long_delta.csv")), 200)
            self.assertEqual(len(self.read_rows(staging / "judge_worklist.csv")), 194)
            audit = audit_prepared_staging(staging)
            self.assertEqual(audit["result"], "PASS")
            self.assertEqual(audit["row_counts"]["new_model_long_delta"], 200)
            one_model_header = self.read_rows(staging / "one_model_final_wide.csv")[0].keys()
            self.assertIn("Diagnosis_synthetic_model_v1", one_model_header)
            self.assertNotIn("Diagnosis_existing_model_v1", one_model_header)
            repeated = prepare_incremental_admission(**args, dry_run=False)
            self.assertTrue(repeated["already_prepared"])

    def test_prepare_rejects_metadata_mismatch_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.make_fixture(Path(tmp))
            rows = self.read_rows(fixture / "incoming_package/results.csv")
            rows[0]["Image_SHA256"] = "mismatch"
            self.write_rows(fixture / "incoming_package/results.csv", rows)
            output_root = Path(tmp) / "output"
            with self.assertRaises(ValidationError):
                prepare_incremental_admission(**self.prepare_args(fixture, output_root), dry_run=False)
            self.assertFalse(output_root.exists())

    def test_prepare_rejects_parent_wide_long_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.make_fixture(Path(tmp))
            rows = self.read_rows(fixture / "parent_final_long_master.csv")
            rows[0]["diagnosis"] = "mismatch"
            self.write_rows(fixture / "parent_final_long_master.csv", rows)
            with self.assertRaises(ValidationError):
                prepare_incremental_admission(**self.prepare_args(fixture, Path(tmp) / "output"), dry_run=False)

    def test_prepare_rejects_unprojected_multi_model_incoming(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.make_fixture(Path(tmp))
            incoming = fixture / "incoming_package/results.csv"
            rows = self.read_rows(incoming)
            with incoming.open("r", encoding="utf-8", newline="") as handle:
                fieldnames = list(csv.DictReader(handle).fieldnames or [])
            fieldnames.append("Diagnosis_other_model")
            for row in rows:
                row["Diagnosis_other_model"] = "other"
            with incoming.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaises(ValidationError):
                prepare_incremental_admission(**self.prepare_args(fixture, Path(tmp) / "output"), dry_run=False)

    def test_project_one_model_package_allows_shared_source_then_prepare(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.make_fixture(Path(tmp))
            incoming = fixture / "incoming_package/results.csv"
            rows = self.read_rows(incoming)
            with incoming.open("r", encoding="utf-8", newline="") as handle:
                fieldnames = list(csv.DictReader(handle).fieldnames or [])
            extra_fields = [
                "Diagnosis_other_model",
                "Likert_other_model",
                "Prompt_Tokens_other_model",
                "Total_Tokens_Out_other_model",
                "Reasoning_Tokens_other_model",
                "Latency_other_model",
                "Provider_other_model",
                "Timestamp_UTC_other_model",
                "Reasoning_other_model",
                "Reasoning_Raw_other_model",
                "Reasoning_Details_other_model",
                "Actual_Request_Extra_other_model",
                "Grok_Fallback_Used_other_model",
                "OpenRouter_Response_Model_other_model",
                "Usage_JSON_other_model",
                "Raw_Response_other_model",
            ]
            fieldnames.extend(extra_fields)
            for row in rows:
                for field in extra_fields:
                    row[field] = "other"
            with incoming.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)

            projected = Path(tmp) / "projected_package"
            projection = project_one_model_package(
                source_wide=incoming,
                model_key="synthetic_model_v1",
                output_package=projected,
                dry_run=False,
            )
            self.assertEqual(projection["projection_state"], "PROJECTED")
            self.assertTrue((projected / "SHA256SUMS").exists())
            projected_header = self.read_rows(projected / "results.csv")[0].keys()
            self.assertIn("Diagnosis_synthetic_model_v1", projected_header)
            self.assertNotIn("Diagnosis_other_model", projected_header)

            args = self.prepare_args(fixture, Path(tmp) / "output")
            args["incoming_package"] = projected
            receipt = prepare_incremental_admission(**args, dry_run=True)
            self.assertEqual(receipt["transaction_state"], "DRY_RUN_VALIDATED")

    def test_synthetic_dual_judge_routes_agreements_and_radiologist_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.make_fixture(Path(tmp))
            output_root = Path(tmp) / "output"
            receipt = prepare_incremental_admission(**self.prepare_args(fixture, output_root), dry_run=False)
            staging = Path(str(receipt["staging_root"]))
            dry_run = run_synthetic_dual_judge_delta(
                staging_root=staging,
                judges_path=REPO_ROOT / "config/radle_v2_judges.json",
                out_dir=staging / "judge_evidence",
                repo_root=REPO_ROOT,
                dry_run=True,
            )
            self.assertEqual(dry_run["result"], "DRY_RUN_VALIDATED")
            self.assertEqual(dry_run["base_calls"], 388)
            self.assertEqual(dry_run["worst_case_http_requests"], 2328)
            self.assertFalse((staging / "judge_evidence").exists())

            result = run_synthetic_dual_judge_delta(
                staging_root=staging,
                judges_path=REPO_ROOT / "config/radle_v2_judges.json",
                out_dir=staging / "judge_evidence",
                repo_root=REPO_ROOT,
                dry_run=False,
            )
            self.assertEqual(result["result"], "PASS")
            self.assertEqual(result["judge_result_rows"], 388)
            self.assertEqual(result["locked_agreement_rows"], 192)
            self.assertEqual(result["radiologist_queue_rows"], 3)
            for relative in [
                "judge_evidence/request_payloads.jsonl",
                "judge_evidence/judge_cache.jsonl",
                "judge_evidence/judge_results.jsonl",
                "judge_evidence/judge_evidence_index.json",
                "judge_evidence/agreement_locks.csv",
                "judge_evidence/radiologist_queue_routing_audit.json",
            ]:
                self.assertTrue((staging / relative).exists(), relative)
            queue_path = staging / "radiologist_queue.csv"
            with queue_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, RADIOLOGIST_QUEUE_FIELDS)
                queue_rows = list(reader)
            self.assertEqual({row["Master_Case_ID"] for row in queue_rows}, {"6", "7", "164"})
            audit = audit_judge_evidence(staging)
            self.assertEqual(audit["result"], "PASS")
            self.assertEqual(audit["radiologist_queue_rows"], 3)
            request_text = (staging / "judge_evidence/request_payloads.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("Candidate AE", request_text)
            self.assertNotIn("synthetic_model_v1", request_text)

    def test_finalize_requires_complete_radiologist_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, staging = self.prepared_with_judges(tmp)
            incomplete = self.write_radiologist_decisions(staging, rows=[
                {
                    "Master_Case_ID": "6",
                    "model_blinded": "Candidate AE",
                    "score_binary": "1",
                    "reviewer_pseudonym": "synthetic_rad",
                    "reviewed_utc": "2026-01-03T00:00:00+00:00",
                    "rationale": "missing other decisions",
                }
            ])
            with self.assertRaises(ValidationError):
                finalize_incremental_admission(intake_root=staging, radiologist_decisions=incomplete)

    def test_finalize_commit_and_readback_preserve_parent_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture, staging = self.prepared_with_judges(tmp)
            decisions = self.write_radiologist_decisions(staging)
            receipt = finalize_incremental_admission(intake_root=staging, radiologist_decisions=decisions)
            final_root = Path(str(receipt["final_staging_root"]))
            self.assertEqual(receipt["transaction_state"], "PRECOMMIT_VALIDATED")
            self.assertEqual(receipt["source_counts"]["dual_judge_agreement"], 192)
            self.assertEqual(receipt["source_counts"]["radiologist"], 3)
            audit = audit_finalized_admission(final_root)
            self.assertEqual(audit["result"], "PASS")
            self.assertEqual(audit["scored_delta_rows"], 200)
            parent_bytes = (fixture / "parent_final_long_master.csv").read_bytes()
            final_bytes = (final_root / "final/radle_v2_final_long_master.csv").read_bytes()
            self.assertTrue(final_bytes.startswith(parent_bytes))
            scored_rows = self.read_rows(final_root / "scored_append_delta.csv")
            self.assertEqual(len(scored_rows), 200)
            self.assertEqual({row["final_score"] for row in scored_rows}, {"0", "1"})

            commit = commit_finalized_admission(final_root)
            self.assertEqual(commit["transaction_state"], "FINAL_MASTER_COMMITTED")
            self.assertTrue((final_root / "SHA256SUMS").exists())
            self.assertTrue((final_root / "COMMITTED.json").exists())
            readback = audit_finalized_admission(final_root, require_committed=True)
            self.assertEqual(readback["result"], "PASS")
            self.assertGreater(readback["checksum_rows"], 0)
            second_commit = commit_finalized_admission(final_root)
            self.assertEqual(second_commit["transaction_state"], "ALREADY_ADMITTED")


if __name__ == "__main__":
    unittest.main()
