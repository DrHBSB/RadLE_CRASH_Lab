from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from radle_incremental_admission import (
    ValidationError,
    audit_judge_evidence,
    canonical_json_sha256,
    canonical_text_sha256,
    prepare_incremental_admission,
    read_csv_table,
    sha256_file,
)
from radle_openrouter_judge import (
    AGREEMENT_EVIDENCE_HASH_FIELDS,
    run_openrouter_dual_judge_delta,
    validate_agreement_results,
)
from scripts.radle_v2_dual_judge_delta import main as judge_main
from tests.make_radle_incremental_fixture import make_fixture


NOW = datetime(2026, 7, 10, 8, 0, tzinfo=timezone.utc)
JUDGES_PATH = REPO_ROOT / "config/radle_v2_judges.json"


class FakeTransport:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def complete(self, *, payload: dict[str, object], timeout_seconds: float) -> dict[str, object]:
        self.calls.append({"payload": copy.deepcopy(payload), "timeout_seconds": timeout_seconds})
        if not self.responses:
            raise AssertionError("unexpected fake transport call")
        return self.responses.pop(0)


def judge_response(model: str, *, score: int = 1, flag: bool = False, content: str | None = None, cost: str = "0.001") -> dict[str, object]:
    content = content or json.dumps({
        "score": score,
        "matched_entity": "synthetic diagnosis",
        "reason": "Equivalent principal diagnosis",
        "confidence": "high",
        "flag_for_review": flag,
    })
    return {
        "id": f"fake-{model}",
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"cost": cost},
    }


class OpenRouterJudgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._class_tmp = tempfile.TemporaryDirectory()
        root = Path(cls._class_tmp.name)
        cls.fixture = root / "fixture"
        make_fixture(cls.fixture)
        receipt = prepare_incremental_admission(
            parent_wide=cls.fixture / "parent_wide.csv",
            parent_final_long_master=cls.fixture / "parent_final_long_master.csv",
            parent_authority_manifest=cls.fixture / "parent_authority.json",
            blind_map_path=cls.fixture / "blind_label_map.csv",
            incoming_package=cls.fixture / "incoming_package",
            model_key="grok_4_5",
            roster_path=cls.fixture / "roster.json",
            variants_path=cls.fixture / "accepted_variants.csv",
            states_path=REPO_ROOT / "config/radle_v2_terminal_states.json",
            output_root=root / "prepared",
            repo_root=REPO_ROOT,
            dry_run=False,
        )
        cls.template = Path(str(receipt["staging_root"]))
        cls.judges = json.loads(JUDGES_PATH.read_text(encoding="utf-8"))
        cls.judge_ids = [judge["requested_model_id"] for judge in cls.judges["judges"]]
        cls.worklist_count = len(read_csv_table(cls.template / "judge_worklist.csv")[1])

    @classmethod
    def tearDownClass(cls) -> None:
        cls._class_tmp.cleanup()

    def make_staging(self, root: Path) -> Path:
        staging = root / "staging"
        shutil.copytree(self.template, staging)
        return staging

    def authorization_payload(self, staging: Path, **overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "intake_id": json.loads((staging / "append_input_manifest.json").read_text(encoding="utf-8"))["intake_id"],
            "judge_ids": self.judge_ids,
            "prompt_sha256": canonical_text_sha256(REPO_ROOT / self.judges["prompt_file"]),
            "judge_config_sha256": canonical_json_sha256(JUDGES_PATH),
            "judge_worklist_sha256": sha256_file(staging / "judge_worklist.csv"),
            "max_http_requests": self.worklist_count * 2 * int(self.judges["max_retries"]),
            "max_cost_usd": "10.00",
            "approver": "mock-test-approver",
            "approval_utc": "2026-07-10T07:00:00+00:00",
            "expiry_utc": "2026-07-11T07:00:00+00:00",
        }
        payload.update(overrides)
        return payload

    def write_authorization(self, staging: Path, **overrides: object) -> Path:
        path = staging / "paid_judge_authorization.json"
        path.write_text(json.dumps(self.authorization_payload(staging, **overrides), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def success_responses(self) -> list[dict[str, object]]:
        return [judge_response(model) for _ in range(self.worklist_count) for model in self.judge_ids]

    def run_real(self, staging: Path, transport: FakeTransport, *, api_key: str = "fake-key") -> dict[str, object]:
        return run_openrouter_dual_judge_delta(
            staging_root=staging,
            judges_path=JUDGES_PATH,
            out_dir=staging / "judge_evidence",
            repo_root=REPO_ROOT,
            authorization_path=staging / "paid_judge_authorization.json",
            api_key=api_key,
            transport=transport,
            clock=lambda: NOW,
            sleeper=lambda _: None,
        )

    def test_mocked_real_success_is_fully_auditable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            staging = self.make_staging(Path(tmp))
            self.write_authorization(staging)
            transport = FakeTransport(self.success_responses())
            receipt = self.run_real(staging, transport)
            self.assertEqual(receipt["locked_agreement_rows"], self.worklist_count)
            self.assertEqual(receipt["radiologist_queue_rows"], 1)
            self.assertEqual(receipt["http_requests"], self.worklist_count * 2)
            self.assertEqual(len(transport.calls), self.worklist_count * 2)
            self.assertEqual(audit_judge_evidence(staging)["result"], "PASS")
            request_text = (staging / "judge_evidence/request_payloads.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("grok_4_5", request_text)
            self.assertNotIn("Candidate AE", request_text)
            index = json.loads((staging / "judge_evidence/judge_evidence_index.json").read_text(encoding="utf-8"))
            self.assertEqual(index["files"]["paid_judge_authorization"]["path"], "paid_judge_authorization.json")

    def test_authorization_failures_make_zero_transport_calls(self) -> None:
        scenarios = {
            "missing": None,
            "expired": {"expiry_utc": "2026-07-10T08:00:00+00:00"},
            "intake": {"intake_id": "wrong"},
            "judges": {"judge_ids": [self.judge_ids[0], "wrong/model"]},
            "prompt": {"prompt_sha256": "0" * 64},
            "config": {"judge_config_sha256": "1" * 64},
            "worklist": {"judge_worklist_sha256": "2" * 64},
            "cap": {"max_http_requests": 1},
        }
        for name, overrides in scenarios.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                staging = self.make_staging(Path(tmp))
                if overrides is not None:
                    self.write_authorization(staging, **overrides)
                transport = FakeTransport([])
                with self.assertRaises(ValidationError):
                    self.run_real(staging, transport)
                self.assertEqual(transport.calls, [])

    def test_missing_api_key_and_returned_model_mismatch_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            staging = self.make_staging(Path(tmp))
            self.write_authorization(staging)
            transport = FakeTransport([])
            with self.assertRaisesRegex(ValidationError, "OPENROUTER_API_KEY"):
                self.run_real(staging, transport, api_key="")
            self.assertEqual(transport.calls, [])
        with tempfile.TemporaryDirectory() as tmp:
            staging = self.make_staging(Path(tmp))
            self.write_authorization(staging)
            transport = FakeTransport([judge_response("provider/substituted")])
            with self.assertRaisesRegex(ValidationError, "returned model mismatch"):
                self.run_real(staging, transport)
            self.assertEqual(len(transport.calls), 1)

    def test_parse_failure_routes_to_radiologist_and_audits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            staging = self.make_staging(Path(tmp))
            self.write_authorization(staging)
            responses = self.success_responses()
            responses[0] = judge_response(self.judge_ids[0], content="not-json")
            receipt = self.run_real(staging, FakeTransport(responses))
            self.assertEqual(receipt["locked_agreement_rows"], self.worklist_count - 1)
            self.assertEqual(receipt["radiologist_queue_rows"], 2)
            self.assertEqual(audit_judge_evidence(staging)["result"], "PASS")

    def test_cache_replay_is_append_only_and_makes_zero_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            staging = self.make_staging(Path(tmp))
            self.write_authorization(staging)
            self.run_real(staging, FakeTransport(self.success_responses()))
            cache = staging / "judge_evidence/judge_cache.jsonl"
            before = cache.read_bytes()
            replay = FakeTransport([])
            receipt = self.run_real(staging, replay)
            self.assertEqual(receipt["cache_hits"], self.worklist_count * 2)
            self.assertEqual(receipt["http_requests"], 0)
            self.assertEqual(replay.calls, [])
            self.assertEqual(cache.read_bytes(), before)

    def test_duplicate_or_forged_agreement_is_rejected(self) -> None:
        configured = [
            {"judge_key": "gemini", "requested_model_id": self.judge_ids[0]},
            {"judge_key": "glm", "requested_model_id": self.judge_ids[1]},
        ]
        common = {field: "A" * 64 for field in AGREEMENT_EVIDENCE_HASH_FIELDS}
        result = {
            **common,
            "judge_key": "gemini",
            "requested_judge_model_id": self.judge_ids[0],
            "returned_judge_model_id": self.judge_ids[0],
            "parse_status": "parsed",
            "score": 1,
            "flag_for_review": False,
        }
        valid, reason = validate_agreement_results([result, dict(result)], configured)
        self.assertFalse(valid)
        self.assertEqual(reason, "duplicate_judge_identity")

    def test_default_cli_mode_is_dry_run_and_never_opens_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            staging = self.make_staging(Path(tmp))
            with patch("radle_openrouter_judge.urllib.request.urlopen") as urlopen:
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    code = judge_main(["--staging-root", str(staging), "--config", str(JUDGES_PATH)])
                urlopen.assert_not_called()
            self.assertEqual(code, 0)
            self.assertFalse((staging / "judge_evidence").exists())


if __name__ == "__main__":
    unittest.main()
