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
    ValidationError,
    allocate_next_candidate_label,
    audit_prepared_staging,
    classify_terminal_state,
    normalize_diagnosis,
    prepare_incremental_admission,
    project_one_model_package,
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


if __name__ == "__main__":
    unittest.main()
