from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from radle_incremental_admission import (
    allocate_next_candidate_label,
    classify_terminal_state,
    normalize_diagnosis,
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


if __name__ == "__main__":
    unittest.main()
