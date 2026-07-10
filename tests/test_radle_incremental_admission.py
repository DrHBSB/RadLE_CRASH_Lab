from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from radle_incremental_admission import (
    ADJUDICATION_STATE_FIELDS,
    FINAL_LONG_MASTER_FIELDS,
    RADIOLOGIST_DECISION_FIELDS,
    ValidationError,
    audit_finalized_admission,
    audit_idk0_score_lane,
    audit_judge_evidence,
    audit_prepared_staging,
    build_idk0_score_lane,
    commit_finalized_admission,
    finalize_incremental_admission,
    prepare_incremental_admission,
    read_csv_table,
    run_synthetic_dual_judge_delta,
    sha256_file,
)
from tests.make_radle_incremental_fixture import make_fixture


class IncrementalAdmissionProductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._class_tmp = tempfile.TemporaryDirectory()
        cls.class_root = Path(cls._class_tmp.name)
        cls.fixture = cls.class_root / "fixture"
        make_fixture(cls.fixture)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._class_tmp.cleanup()

    def prepare_args(self, fixture: Path, output_root: Path) -> dict[str, object]:
        return {
            "parent_wide": fixture / "parent_wide.csv",
            "parent_final_long_master": fixture / "parent_final_long_master.csv",
            "parent_authority_manifest": fixture / "parent_authority.json",
            "blind_map_path": fixture / "blind_label_map.csv",
            "incoming_package": fixture / "incoming_package",
            "model_key": "grok_4_5",
            "roster_path": fixture / "roster.json",
            "variants_path": fixture / "accepted_variants.csv",
            "states_path": REPO_ROOT / "config/radle_v2_terminal_states.json",
            "output_root": output_root,
            "repo_root": REPO_ROOT,
        }

    def prepare(self, root: Path, fixture: Path | None = None) -> Path:
        fixture = fixture or self.fixture
        receipt = prepare_incremental_admission(**self.prepare_args(fixture, root / "admissions"), dry_run=False)
        return Path(str(receipt["staging_root"]))

    def prepare_with_judges(self, root: Path, fixture: Path | None = None) -> Path:
        staging = self.prepare(root, fixture)
        run_synthetic_dual_judge_delta(
            staging_root=staging,
            judges_path=REPO_ROOT / "config/radle_v2_judges.json",
            out_dir=staging / "judge_evidence",
            repo_root=REPO_ROOT,
            dry_run=False,
        )
        return staging

    def write_decisions(self, staging: Path, *, incomplete: bool = False) -> Path:
        _, queue = read_csv_table(staging / "radiologist_queue.csv")
        if incomplete:
            queue = queue[:1]
        rows = [
            {
                "Master_Case_ID": row["Master_Case_ID"],
                "model_blinded": row["model_blinded"],
                "score_binary": "1",
                "reviewer_pseudonym": "fixture_rad",
                "reviewed_utc": "2026-07-10T08:00:00+00:00",
                "rationale": "fixture decision",
            }
            for row in queue
        ]
        path = staging / ("radiologist_decisions_incomplete.csv" if incomplete else "radiologist_decisions.csv")
        self.write_csv(path, RADIOLOGIST_DECISION_FIELDS, rows)
        return path

    @staticmethod
    def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def reseal_package(package: Path) -> None:
        results = package / "results.csv"
        manifest_path = package / "source_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["results_csv_sha256"] = sha256_file(results)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        files = sorted(path for path in package.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
        (package / "SHA256SUMS").write_text(
            "".join(f"{sha256_file(path).lower()}  {path.relative_to(package).as_posix()}\n" for path in files),
            encoding="utf-8",
        )

    def test_production_shape_and_oversized_csv_field(self) -> None:
        wide_fields, wide_rows = read_csv_table(self.fixture / "parent_wide.csv")
        long_fields, long_rows = read_csv_table(self.fixture / "parent_final_long_master.csv")
        self.assertEqual((len(wide_rows), len(wide_fields)), (200, 291))
        self.assertEqual((len(long_rows), len(long_fields)), (6000, 20))
        self.assertEqual(long_fields, FINAL_LONG_MASTER_FIELDS)
        self.assertGreater(len(wide_rows[0]["Raw_Response_gpt_5_5"]), 131_072)

    def test_prepare_is_path_independent_and_uses_exact_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture_a = root / "a" / "fixture"
            fixture_b = root / "different" / "nested" / "fixture"
            make_fixture(fixture_a)
            make_fixture(fixture_b)
            first = prepare_incremental_admission(**self.prepare_args(fixture_a, root / "out_a"), dry_run=False)
            second = prepare_incremental_admission(**self.prepare_args(fixture_b, root / "out_b"), dry_run=False)
            self.assertEqual(first["intake_id"], second["intake_id"])
            staging = Path(str(first["staging_root"]))
            delta_fields, delta_rows = read_csv_table(staging / "new_model_long_delta.csv")
            state_fields, state_rows = read_csv_table(staging / "adjudication_state.csv")
            self.assertEqual(delta_fields, FINAL_LONG_MASTER_FIELDS)
            self.assertEqual(state_fields, ADJUDICATION_STATE_FIELDS)
            self.assertEqual(len(delta_rows), 200)
            self.assertEqual(len(state_rows), 200)
            self.assertTrue(all(not row["final_score_authoritative"] and not row["final_score_source"] for row in delta_rows))
            self.assertEqual(audit_prepared_staging(staging)["result"], "PASS")
            repeated = prepare_incremental_admission(**self.prepare_args(fixture_a, root / "out_a"), dry_run=False)
            self.assertTrue(repeated["already_prepared"])

    def test_prepare_rejects_authority_package_routing_and_repair_tamper(self) -> None:
        scenarios = ["authority", "checksum", "missing_file", "unsorted_inventory", "routing", "repair", "smoke"]
        for scenario in scenarios:
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                fixture = root / "fixture"
                make_fixture(fixture)
                if scenario == "authority":
                    rows = read_csv_table(fixture / "parent_final_long_master.csv")[1]
                    rows[0]["diagnosis"] = "tampered"
                    self.write_csv(fixture / "parent_final_long_master.csv", FINAL_LONG_MASTER_FIELDS, rows)
                elif scenario == "checksum":
                    (fixture / "incoming_package/results.csv").write_text("tampered", encoding="utf-8")
                elif scenario == "missing_file":
                    (fixture / "incoming_package/repair_evidence.json").unlink()
                elif scenario == "unsorted_inventory":
                    path = fixture / "incoming_package/SHA256SUMS"
                    path.write_text("\n".join(reversed(path.read_text(encoding="utf-8").splitlines())) + "\n", encoding="utf-8")
                elif scenario == "routing":
                    fields, rows = read_csv_table(fixture / "incoming_package/results.csv")
                    rows[0]["Provider_grok_4_5"] = "Wrong Provider"
                    self.write_csv(fixture / "incoming_package/results.csv", fields, rows)
                    self.reseal_package(fixture / "incoming_package")
                elif scenario == "repair":
                    path = fixture / "incoming_package/repair_evidence.json"
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    payload["unresolved_cells"] = 1
                    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    self.reseal_package(fixture / "incoming_package")
                elif scenario == "smoke":
                    path = fixture / "incoming_package/source_manifest.json"
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    payload["test_limit"] = 5
                    payload["run_label"] = "smoke_5case"
                    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    self.reseal_package(fixture / "incoming_package")
                with self.assertRaises(ValidationError):
                    prepare_incremental_admission(**self.prepare_args(fixture, root / "out"), dry_run=False)
                self.assertFalse((root / "out").exists())

    def test_same_logical_key_different_content_gets_new_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture_a = root / "fixture_a"
            fixture_b = root / "fixture_b"
            make_fixture(fixture_a)
            shutil.copytree(fixture_a, fixture_b)
            fields, rows = read_csv_table(fixture_b / "incoming_package/results.csv")
            rows[20]["Diagnosis_grok_4_5"] = "Different candidate content"
            self.write_csv(fixture_b / "incoming_package/results.csv", fields, rows)
            self.reseal_package(fixture_b / "incoming_package")
            first = prepare_incremental_admission(**self.prepare_args(fixture_a, root / "out"), dry_run=True)
            second = prepare_incremental_admission(**self.prepare_args(fixture_b, root / "out"), dry_run=True)
            self.assertNotEqual(first["intake_id"], second["intake_id"])

    def test_prepared_tamper_is_detected_even_when_manifest_hash_is_forged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            staging = self.prepare(Path(tmp))
            fields, rows = read_csv_table(staging / "adjudication_state.csv")
            rows[0]["terminal_state"] = "judge_required"
            self.write_csv(staging / "adjudication_state.csv", fields, rows)
            manifest_path = staging / "append_input_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["outputs"]["adjudication_state"]["sha256"] = sha256_file(staging / "adjudication_state.csv")
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "classification mismatch"):
                audit_prepared_staging(staging)

    def test_forged_agreement_lock_is_detected_after_index_rehash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            staging = self.prepare_with_judges(Path(tmp))
            fields, rows = read_csv_table(staging / "judge_evidence/agreement_locks.csv")
            rows[0]["score"] = "1" if rows[0]["score"] == "0" else "0"
            self.write_csv(staging / "judge_evidence/agreement_locks.csv", fields, rows)
            index_path = staging / "judge_evidence/judge_evidence_index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["files"]["agreement_locks"]["sha256"] = sha256_file(staging / "judge_evidence/agreement_locks.csv")
            index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "do not derive"):
                audit_judge_evidence(staging)

    def test_finalize_requires_complete_radiologist_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            staging = self.prepare_with_judges(Path(tmp))
            decisions = self.write_decisions(staging, incomplete=True)
            with self.assertRaisesRegex(ValidationError, "missing queue keys"):
                finalize_incremental_admission(intake_root=staging, radiologist_decisions=decisions)

    def test_full_commit_readback_and_idk0_lane(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging = self.prepare_with_judges(root)
            decisions = self.write_decisions(staging)
            receipt = finalize_incremental_admission(intake_root=staging, radiologist_decisions=decisions)
            final_root = Path(str(receipt["final_staging_root"]))
            self.assertEqual(receipt["source_counts"], {
                "ai_judges": 191,
                "auto_score_not_required": 5,
                "canonical_exact": 1,
                "radiologist": 3,
            })
            audit = audit_finalized_admission(final_root)
            self.assertEqual(audit["output_row_count"], 6200)
            commit = commit_finalized_admission(final_root)
            self.assertEqual(commit["transaction_state"], "FINAL_MASTER_COMMITTED")
            self.assertEqual(commit_finalized_admission(final_root)["transaction_state"], "ALREADY_ADMITTED")
            self.assertEqual(audit_finalized_admission(final_root, require_committed=True)["result"], "PASS")

            lane = root / "lane"
            lane_receipt = build_idk0_score_lane(
                committed_root=final_root,
                output_root=lane,
                human_presentation="pooled12",
                states_path=REPO_ROOT / "config/radle_v2_terminal_states.json",
            )
            self.assertEqual(lane_receipt["counts"]["complete_model_count"], 19)
            self.assertEqual(lane_receipt["counts"]["active_model_count"], 15)
            self.assertEqual(lane_receipt["counts"]["excluded_model_count"], 4)
            self.assertEqual(lane_receipt["counts"]["human_backend_readers"], 12)
            self.assertEqual(lane_receipt["counts"]["active_score_rows"], 5400)
            self.assertEqual(audit_idk0_score_lane(lane)["result"], "PASS")
            _, score_rows = read_csv_table(lane / "score_rows.csv")
            case5 = next(row for row in score_rows if row["Master_Case_ID"] == "5" and row["model_key"] == "grok_4_5")
            self.assertEqual(case5["terminal_state"], "invalid_likert")
            self.assertEqual(case5["score1000_component"], "0")
            panel_keys = {row["comparator_key"] for row in read_csv_table(lane / "panel_order.csv")[1]}
            self.assertNotIn("grok_4_3", panel_keys)
            self.assertIn("grok_4_5", panel_keys)

    def test_committed_tamper_and_roster_tamper_block_readback(self) -> None:
        for target in ["scored_append_delta.csv", "roster/model_roster.json", "roster/blind_label_map.csv"]:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                staging = self.prepare_with_judges(root)
                final_root = Path(str(finalize_incremental_admission(
                    intake_root=staging,
                    radiologist_decisions=self.write_decisions(staging),
                )["final_staging_root"]))
                commit_finalized_admission(final_root)
                path = final_root / target
                path.write_bytes(path.read_bytes() + b" ")
                with self.assertRaises(ValidationError):
                    audit_finalized_admission(final_root, require_committed=True)


if __name__ == "__main__":
    unittest.main()
