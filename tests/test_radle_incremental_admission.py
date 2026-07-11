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
    audit_package_sha256sums,
    audit_finalized_admission,
    audit_idk0_score_lane,
    audit_judge_evidence,
    audit_prepared_staging,
    build_idk0_score_lane,
    commit_finalized_admission,
    finalize_incremental_admission,
    prepare_incremental_admission,
    project_one_model_package,
    read_csv_table,
    run_synthetic_dual_judge_delta,
    sha256_file,
    split_combined_radiologist_scores,
    validate_radiologist_decisions,
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

    def combined_score_rows(self, staging: Path, *, score: str = "1") -> list[dict[str, object]]:
        _, queue = read_csv_table(staging / "radiologist_queue.csv")
        rows: list[dict[str, object]] = []
        for row in queue:
            combined = {field: row.get(field, "") for field in ["Master_Case_ID", "model_blinded", "Ground_Truth_Diagnosis", "diagnosis", "likert"]}
            if str(combined["likert"]).endswith(".0"):
                combined["likert"] = str(combined["likert"])[:-2]
            combined["human_score"] = score
            rows.append(combined)
        return rows

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

    def clone_package_for_model(
        self,
        source: Path,
        destination: Path,
        *,
        source_model: str,
        target_model: str,
        provider: str,
        returned_model: str,
    ) -> None:
        shutil.copytree(source, destination)
        fields, rows = read_csv_table(destination / "results.csv")
        renamed_fields = [field.replace(f"_{source_model}", f"_{target_model}") for field in fields]
        renamed_rows: list[dict[str, object]] = []
        for row in rows:
            renamed = {
                field.replace(f"_{source_model}", f"_{target_model}"): value
                for field, value in row.items()
            }
            renamed[f"Provider_{target_model}"] = provider
            renamed[f"OpenRouter_Response_Model_{target_model}"] = returned_model
            renamed[f"Actual_Request_Extra_{target_model}"] = json.dumps(
                {"provider": {"only": [provider], "allow_fallbacks": False}},
                sort_keys=True,
            )
            renamed_rows.append(renamed)
        self.write_csv(destination / "results.csv", renamed_fields, renamed_rows)
        for name in ["source_manifest.json", "promotion_audit.json", "repair_evidence.json"]:
            path = destination / name
            payload = json.loads(path.read_text(encoding="utf-8"))
            if "model_key" in payload:
                payload["model_key"] = target_model
            if name == "source_manifest.json":
                payload["run_label"] = f"radle_v2_fixture_full_{target_model}"
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.reseal_package(destination)

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

    def test_projection_requires_real_runtime_sha_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture"
            make_fixture(fixture)
            source = fixture / "incoming_package" / "results.csv"
            with self.assertRaisesRegex(ValidationError, "must not be the source wide CSV hash"):
                project_one_model_package(
                    source_wide=source,
                    model_key="grok_4_5",
                    output_package=root / "bad_projection",
                    runtime_sha=sha256_file(source).lower(),
                    dry_run=True,
                )

            projected = root / "projection"
            receipt = project_one_model_package(
                source_wide=source,
                model_key="grok_4_5",
                output_package=projected,
                runtime_sha="8029ad46d90b7bc8ab67af1e805ffaa2619b85a2",
                runtime_sha_status="inferred",
                runtime_sha_note="fixture mirrors the handoff metadata-only runtime SHA caveat",
                source_manifest_path=fixture / "incoming_package" / "source_manifest.json",
            )
            self.assertEqual(receipt["projection_state"], "PROJECTED")
            manifest = json.loads((projected / "source_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["runtime_sha"], "8029ad46d90b7bc8ab67af1e805ffaa2619b85a2")
            self.assertEqual(manifest["runtime_sha_status"], "inferred")
            self.assertEqual(manifest["source_manifest_evidence"]["source_manifest_test_limit"], None)
            audit_package_sha256sums(projected)

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

    def test_previous_authoritative_same_case_score_is_reused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture"
            make_fixture(fixture)
            fields, rows = read_csv_table(fixture / "parent_final_long_master.csv")
            for row in rows:
                if row["Master_Case_ID"] == "7" and row["candidate"] == "Radiologist":
                    row["diagnosis"] = "Candidate alternate"
                    row["final_score_authoritative"] = "0"
                    row["final_score_source"] = "fixture_prior_radiologist"
                    break
            else:
                self.fail("fixture human prior row not found")
            self.write_csv(fixture / "parent_final_long_master.csv", FINAL_LONG_MASTER_FIELDS, rows)
            authority_path = fixture / "parent_authority.json"
            authority = json.loads(authority_path.read_text(encoding="utf-8"))
            authority["base_final_long_master"]["sha256"] = sha256_file(fixture / "parent_final_long_master.csv")
            authority_path.write_text(json.dumps(authority, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            staging = self.prepare(root, fixture)
            _, state_rows = read_csv_table(staging / "adjudication_state.csv")
            case7 = next(row for row in state_rows if row["Master_Case_ID"] == "7")
            self.assertEqual(case7["terminal_state"], "previous_authoritative_score")
            self.assertEqual(case7["automatic_score"], "0")
            _, worklist_rows = read_csv_table(staging / "judge_worklist.csv")
            self.assertNotIn("7", {row["Master_Case_ID"] for row in worklist_rows})
            self.assertEqual(audit_prepared_staging(staging)["result"], "PASS")

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

    def test_finalize_rejects_malformed_radiologist_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            staging = self.prepare_with_judges(Path(tmp))
            decisions = self.write_decisions(staging)
            _, valid_rows = read_csv_table(decisions)
            scenarios = {
                "invalid timestamp": (
                    RADIOLOGIST_DECISION_FIELDS,
                    [{**row, "reviewed_utc": "not-a-timestamp"} for row in valid_rows],
                    "not a valid timestamp",
                ),
                "reordered header": (
                    [RADIOLOGIST_DECISION_FIELDS[1], RADIOLOGIST_DECISION_FIELDS[0], *RADIOLOGIST_DECISION_FIELDS[2:]],
                    valid_rows,
                    "exact ordered schema",
                ),
                "extra column": (
                    [*RADIOLOGIST_DECISION_FIELDS, "unexpected"],
                    [{**row, "unexpected": "forged"} for row in valid_rows],
                    "exact ordered schema",
                ),
            }
            for name, (fields, rows, error) in scenarios.items():
                with self.subTest(name=name):
                    self.write_csv(decisions, fields, rows)
                    with self.assertRaisesRegex(ValidationError, error):
                        finalize_incremental_admission(intake_root=staging, radiologist_decisions=decisions)

    def test_split_combined_radiologist_scores_for_multi_model_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_staging = self.prepare_with_judges(root / "first")
            first_final = Path(str(finalize_incremental_admission(
                intake_root=first_staging,
                radiologist_decisions=self.write_decisions(first_staging),
            )["final_staging_root"]))
            commit_finalized_admission(first_final)
            second_package = root / "gpt_package"
            self.clone_package_for_model(
                self.fixture / "incoming_package",
                second_package,
                source_model="grok_4_5",
                target_model="gpt_5_6_sol_pro",
                provider="OpenAI",
                returned_model="openai/gpt-5.6-sol-pro",
            )
            second = prepare_incremental_admission(
                parent_wide=first_final / "combined_wide/RadLE_v2_results_final.csv",
                parent_final_long_master=first_final / "final/radle_v2_final_long_master.csv",
                parent_authority_manifest=first_final / "COMMITTED.json",
                blind_map_path=first_final / "roster/blind_label_map.csv",
                incoming_package=second_package,
                model_key="gpt_5_6_sol_pro",
                roster_path=self.fixture / "roster.json",
                variants_path=self.fixture / "accepted_variants.csv",
                states_path=REPO_ROOT / "config/radle_v2_terminal_states.json",
                output_root=root / "second",
                repo_root=REPO_ROOT,
                dry_run=False,
            )
            second_staging = Path(str(second["staging_root"]))
            run_synthetic_dual_judge_delta(
                staging_root=second_staging,
                judges_path=REPO_ROOT / "config/radle_v2_judges.json",
                out_dir=second_staging / "judge_evidence",
                repo_root=REPO_ROOT,
                dry_run=False,
            )
            combined_path = root / "combined_scores.csv"
            self.write_csv(
                combined_path,
                ["Master_Case_ID", "model_blinded", "Ground_Truth_Diagnosis", "diagnosis", "likert", "human_score"],
                self.combined_score_rows(first_staging) + self.combined_score_rows(second_staging, score="0.0"),
            )
            receipt = split_combined_radiologist_scores(
                combined_scores=combined_path,
                staging_roots=[first_staging, second_staging],
                output_root=root / "split",
                reviewer_pseudonym="fixture_rad",
                reviewed_utc="2026-07-10T08:00:00+00:00",
            )
            queue_counts = [
                len(read_csv_table(first_staging / "radiologist_queue.csv")[1]),
                len(read_csv_table(second_staging / "radiologist_queue.csv")[1]),
            ]
            self.assertEqual(receipt["expected_rows"], sum(queue_counts))
            self.assertEqual([row["radiologist_queue_rows"] for row in receipt["per_model"]], queue_counts)
            for item, staging in zip(receipt["per_model"], [first_staging, second_staging]):
                fields, decision_rows = read_csv_table(Path(item["decisions_path"]))
                self.assertEqual(fields, RADIOLOGIST_DECISION_FIELDS)
                _, queue_rows = read_csv_table(staging / "radiologist_queue.csv")
                validate_radiologist_decisions(queue_rows, Path(item["decisions_path"]))
                self.assertEqual(len(decision_rows), len(queue_rows))
            second_output = next(row for row in receipt["per_model"] if row["model_key"] == "gpt_5_6_sol_pro")
            finalized = finalize_incremental_admission(
                intake_root=second_staging,
                radiologist_decisions=Path(second_output["decisions_path"]),
            )
            self.assertEqual(finalized["source_counts"]["radiologist"], queue_counts[1])

    def test_split_combined_radiologist_scores_rejects_bad_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging = self.prepare_with_judges(root)
            valid_rows = self.combined_score_rows(staging)
            valid_fields = ["Master_Case_ID", "model_blinded", "Ground_Truth_Diagnosis", "diagnosis", "likert", "human_score"]
            scenarios = {
                "missing": (valid_rows[:-1], "missing expected queue keys"),
                "duplicate": (valid_rows + [dict(valid_rows[0])], "duplicate combined radiologist row"),
                "nonbinary": ([{**row, "human_score": "2"} if idx == 0 else row for idx, row in enumerate(valid_rows)], "must be binary"),
                "mismatch": ([{**row, "diagnosis": "wrong row"} if idx == 0 else row for idx, row in enumerate(valid_rows)], "do not match queue evidence"),
            }
            for name, (rows, error) in scenarios.items():
                with self.subTest(name=name):
                    combined_path = root / f"combined_{name}.csv"
                    self.write_csv(combined_path, valid_fields, rows)
                    with self.assertRaisesRegex(ValidationError, error):
                        split_combined_radiologist_scores(
                            combined_scores=combined_path,
                            staging_roots=[staging],
                            output_root=root / f"split_{name}",
                            reviewer_pseudonym="fixture_rad",
                            reviewed_utc="2026-07-10T08:00:00+00:00",
                        )

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
            summary_fields, summary_rows = read_csv_table(lane / "public_candidate_summary.csv")
            summary_rows[0]["score1000"] = "123"
            summary_rows[0]["score2000"] = "1123"
            self.write_csv(lane / "public_candidate_summary.csv", summary_fields, summary_rows)
            manifest_path = lane / "score_lane_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["outputs"]["public_candidate_summary"]["sha256"] = sha256_file(
                lane / "public_candidate_summary.csv"
            )
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "does not independently rederive"):
                audit_idk0_score_lane(lane)

    def test_second_admission_validates_committed_parent_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_staging = self.prepare_with_judges(root / "first")
            first_final = Path(str(finalize_incremental_admission(
                intake_root=first_staging,
                radiologist_decisions=self.write_decisions(first_staging),
            )["final_staging_root"]))
            first_commit = commit_finalized_admission(first_final)
            second_package = root / "gpt_package"
            self.clone_package_for_model(
                self.fixture / "incoming_package",
                second_package,
                source_model="grok_4_5",
                target_model="gpt_5_6_sol_pro",
                provider="OpenAI",
                returned_model="openai/gpt-5.6-sol-pro",
            )
            second = prepare_incremental_admission(
                parent_wide=first_final / "combined_wide/RadLE_v2_results_final.csv",
                parent_final_long_master=first_final / "final/radle_v2_final_long_master.csv",
                parent_authority_manifest=first_final / "COMMITTED.json",
                blind_map_path=first_final / "roster/blind_label_map.csv",
                incoming_package=second_package,
                model_key="gpt_5_6_sol_pro",
                roster_path=self.fixture / "roster.json",
                variants_path=self.fixture / "accepted_variants.csv",
                states_path=REPO_ROOT / "config/radle_v2_terminal_states.json",
                output_root=root / "second",
                repo_root=REPO_ROOT,
                dry_run=False,
            )
            self.assertEqual(second["parent_chain_id"], first_commit["finalization_id"])
            second_staging = Path(str(second["staging_root"]))
            self.assertEqual(audit_prepared_staging(second_staging)["result"], "PASS")
            _, second_delta = read_csv_table(second_staging / "new_model_long_delta.csv")
            self.assertEqual({row["model_blinded"] for row in second_delta}, {"Candidate AF"})
            _, second_blind = read_csv_table(second_staging / "roster/blind_label_map.csv")
            self.assertEqual(len(second_blind), 32)

    def test_muse_projection_can_rename_high_effort_source_family(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_package = root / "muse_high_source"
            self.clone_package_for_model(
                self.fixture / "incoming_package",
                source_package,
                source_model="grok_4_5",
                target_model="muse_spark_1_1_high",
                provider="Meta Model API",
                returned_model="muse-spark-1.1",
            )
            bad_package = root / "muse_projected_bad"
            project_one_model_package(
                source_wide=source_package / "results.csv",
                source_model_key="muse_spark_1_1_high",
                model_key="muse_spark_1_1",
                output_package=bad_package,
                runtime_sha="8029ad46d90b7bc8ab67af1e805ffaa2619b85a2",
                runtime_sha_status="inferred",
                runtime_sha_note="fixture high-effort source family projects into normal Muse identity",
            )
            args = {
                **self.prepare_args(self.fixture, root / "out"),
                "incoming_package": bad_package,
                "model_key": "muse_spark_1_1",
            }
            with self.assertRaisesRegex(ValidationError, "required request-extra mismatch"):
                prepare_incremental_admission(**args, dry_run=True)

            fields, rows = read_csv_table(source_package / "results.csv")
            for row in rows:
                row["Actual_Request_Extra_muse_spark_1_1_high"] = json.dumps(
                    {"reasoning_effort": "high"},
                    sort_keys=True,
                )
            self.write_csv(source_package / "results.csv", fields, rows)
            self.reseal_package(source_package)
            good_package = root / "muse_projected_good"
            projection = project_one_model_package(
                source_wide=source_package / "results.csv",
                source_model_key="muse_spark_1_1_high",
                model_key="muse_spark_1_1",
                output_package=good_package,
                runtime_sha="8029ad46d90b7bc8ab67af1e805ffaa2619b85a2",
                runtime_sha_status="inferred",
                runtime_sha_note="fixture high-effort source family projects into normal Muse identity",
            )
            self.assertEqual(projection["source_model_key"], "muse_spark_1_1_high")
            projected_fields, _ = read_csv_table(good_package / "results.csv")
            self.assertIn("Actual_Request_Extra_muse_spark_1_1", projected_fields)
            self.assertNotIn("Actual_Request_Extra_muse_spark_1_1_high", projected_fields)
            args["incoming_package"] = good_package
            receipt = prepare_incremental_admission(**args, dry_run=True)
            self.assertEqual(receipt["model_blinded"], "Candidate AG")
            self.assertEqual(receipt["transaction_state"], "DRY_RUN_VALIDATED")

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
