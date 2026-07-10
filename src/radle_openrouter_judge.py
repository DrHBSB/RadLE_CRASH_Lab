from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

import radle_incremental_admission as admission
from radle_incremental_admission import ValidationError


AUTHORIZATION_REQUIRED_FIELDS = {
    "intake_id",
    "judge_ids",
    "prompt_sha256",
    "judge_config_sha256",
    "judge_worklist_sha256",
    "max_http_requests",
    "approver",
    "approval_utc",
    "expiry_utc",
}
AGREEMENT_EVIDENCE_HASH_FIELDS = (
    "case_fingerprint_sha256",
    "case_payload_sha256",
    "worklist_row_sha256",
    "judge_config_sha256",
    "prompt_sha256",
    "normalizer_code_sha256",
    "terminal_policy_sha256",
    "variants_snapshot_sha256",
    "judge_worklist_sha256",
    "manifest_input_hashes_sha256",
)


class JudgeTransport(Protocol):
    def complete(self, *, payload: Mapping[str, Any], timeout_seconds: float) -> Mapping[str, Any]:
        """Return one decoded OpenRouter chat-completions response."""


class JudgeTransportError(RuntimeError):
    """Raised when a transport attempt fails before a usable response exists."""


class OpenRouterJudgeTransport:
    def __init__(self, *, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"

    def complete(self, *, payload: Mapping[str, Any], timeout_seconds: float) -> Mapping[str, Any]:
        body = _canonical_json(payload).encode("utf-8")
        request = urllib.request.Request(
            self._endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise JudgeTransportError(f"OpenRouter HTTP status {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise JudgeTransportError(f"OpenRouter transport failure: {type(exc).__name__}") from exc
        if not isinstance(decoded, dict):
            raise JudgeTransportError("OpenRouter response is not a JSON object")
        return decoded


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _json_sha256(value: object) -> str:
    return admission.sha256_bytes(_canonical_json(value).encode("utf-8"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clock_utc(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError("judge clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"paid judge authorization {field} must be a UTC timestamp")
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError as exc:
        raise ValidationError(f"paid judge authorization {field} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValidationError(f"paid judge authorization {field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _require_sha256_match(authorization: Mapping[str, Any], field: str, expected: str) -> None:
    actual = authorization.get(field)
    if not isinstance(actual, str) or actual.upper() != expected.upper():
        raise ValidationError(f"paid judge authorization {field} mismatch")


def validate_paid_judge_authorization(
    *,
    authorization_path: Path,
    intake_id: str,
    judge_ids: Sequence[str],
    prompt_sha256: str,
    judge_config_sha256: str,
    judge_worklist_sha256: str,
    required_http_requests: int,
    now: datetime,
) -> dict[str, Any]:
    if not authorization_path.exists() or not authorization_path.is_file():
        raise ValidationError(f"paid judge authorization missing: {authorization_path}")
    try:
        authorization = admission.read_json(authorization_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"paid judge authorization is unreadable: {authorization_path}") from exc
    missing = sorted(AUTHORIZATION_REQUIRED_FIELDS - set(authorization))
    if missing:
        raise ValidationError(f"paid judge authorization missing fields: {missing}")
    if authorization.get("intake_id") != intake_id:
        raise ValidationError("paid judge authorization intake_id mismatch")
    authorized_judges = authorization.get("judge_ids")
    if not isinstance(authorized_judges, list) or authorized_judges != list(judge_ids):
        raise ValidationError("paid judge authorization judge_ids mismatch")
    if len(set(authorized_judges)) != 2:
        raise ValidationError("paid judge authorization requires two distinct judge_ids")
    _require_sha256_match(authorization, "prompt_sha256", prompt_sha256)
    _require_sha256_match(authorization, "judge_config_sha256", judge_config_sha256)
    _require_sha256_match(authorization, "judge_worklist_sha256", judge_worklist_sha256)

    max_http_requests = authorization.get("max_http_requests")
    if isinstance(max_http_requests, bool) or not isinstance(max_http_requests, int) or max_http_requests < 0:
        raise ValidationError("paid judge authorization max_http_requests must be a non-negative integer")
    if max_http_requests < required_http_requests:
        raise ValidationError(
            "paid judge authorization max_http_requests is smaller than the retry-inclusive request ceiling"
        )

    approver = authorization.get("approver")
    if not isinstance(approver, str) or not approver.strip():
        raise ValidationError("paid judge authorization approver must be non-empty")
    approval_utc = _parse_utc(authorization.get("approval_utc"), "approval_utc")
    expiry_utc = _parse_utc(authorization.get("expiry_utc"), "expiry_utc")
    if approval_utc > now:
        raise ValidationError("paid judge authorization approval_utc is in the future")
    if expiry_utc <= approval_utc:
        raise ValidationError("paid judge authorization expiry_utc must follow approval_utc")
    if now >= expiry_utc:
        raise ValidationError("paid judge authorization is expired")

    max_cost = authorization.get("max_cost_usd")
    if max_cost is not None:
        if isinstance(max_cost, bool):
            raise ValidationError("paid judge authorization max_cost_usd must be positive")
        try:
            parsed_cost = Decimal(str(max_cost))
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError("paid judge authorization max_cost_usd must be positive") from exc
        if not parsed_cost.is_finite() or parsed_cost <= 0:
            raise ValidationError("paid judge authorization max_cost_usd must be positive")
    return authorization


def _judge_specs(judges_config: Mapping[str, Any]) -> list[dict[str, str]]:
    specs = [
        {
            "judge_key": str(judge.get("judge_key", "")),
            "requested_model_id": str(judge.get("requested_model_id", "")),
        }
        for judge in judges_config.get("judges", [])
        if isinstance(judge, dict)
    ]
    keys = [spec["judge_key"] for spec in specs]
    ids = [spec["requested_model_id"] for spec in specs]
    if len(specs) != 2 or len(set(keys)) != 2 or len(set(ids)) != 2 or not all(keys) or not all(ids):
        raise ValidationError("judge config requires two distinct judge keys and model IDs")
    return specs


def _http_payload(*, requested_model_id: str, prompt: str, case_payload: Mapping[str, str], temperature: int) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": _canonical_json(case_payload)},
        ],
        "model": requested_model_id,
        "temperature": temperature,
    }


def _cache_material(
    *,
    requested_model_id: str,
    returned_model_id: str,
    exact_request_payload_sha256: str,
    context: Mapping[str, Any],
    case: Mapping[str, Any],
) -> dict[str, str]:
    return {
        "requested_model_id": requested_model_id,
        "returned_model_id": returned_model_id,
        "exact_request_payload_sha256": exact_request_payload_sha256,
        "judge_config_sha256": str(context["judge_config_sha256"]),
        "prompt_sha256": str(context["prompt_sha256"]),
        "normalizer_code_sha256": str(context["normalizer_code_sha256"]),
        "terminal_policy_sha256": str(context["terminal_policy_sha256"]),
        "case_fingerprint_sha256": str(case["case_fingerprint_sha256"]),
        "variants_snapshot_sha256": str(context["variants_snapshot_sha256"]),
        "judge_worklist_sha256": str(context["judge_worklist_sha256"]),
        "manifest_input_hashes_sha256": str(context["manifest_input_hashes_sha256"]),
    }


def _read_cache(path: Path) -> tuple[dict[str, dict[str, Any]], int]:
    entries: dict[str, dict[str, Any]] = {}
    malformed = 0
    if not path.exists():
        return entries, malformed
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if not isinstance(entry, dict) or not isinstance(entry.get("cache_key"), str):
                raise ValueError("invalid cache entry")
        except (json.JSONDecodeError, ValueError):
            malformed += 1
            continue
        entries[str(entry["cache_key"])] = entry
    return entries, malformed


def _usable_cache_result(
    entry: Mapping[str, Any] | None,
    *,
    expected_key: str,
    expected_material: Mapping[str, str],
    exact_request_payload: Mapping[str, Any],
) -> dict[str, Any] | None:
    if entry is None or entry.get("cache_key") != expected_key:
        return None
    if entry.get("cache_material") != dict(expected_material):
        return None
    if _json_sha256(entry.get("cache_material")) != expected_key:
        return None
    if entry.get("exact_request_payload") != dict(exact_request_payload):
        return None
    raw_response = entry.get("raw_response")
    if not isinstance(raw_response, dict) or entry.get("raw_response_sha256") != _json_sha256(raw_response):
        return None
    result = entry.get("result")
    if not isinstance(result, dict) or result.get("cache_key") != expected_key:
        return None
    for field, expected in expected_material.items():
        result_field = {
            "requested_model_id": "requested_judge_model_id",
            "returned_model_id": "returned_judge_model_id",
        }.get(field, field)
        if result.get(result_field) != expected:
            return None
    return dict(result)


def _append_cache_entry(path: Path, entry: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_newline = False
    if path.exists() and path.stat().st_size:
        with path.open("rb") as handle:
            handle.seek(-1, os.SEEK_END)
            needs_newline = handle.read(1) != b"\n"
    with path.open("a", encoding="utf-8", newline="") as handle:
        if needs_newline:
            handle.write("\n")
        handle.write(_canonical_json(entry))
        handle.write("\n")
        handle.flush()


def _parse_verdict(response: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str]:
    try:
        choices = response["choices"]
        content = choices[0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("message content is not text")
        verdict = json.loads(content.strip())
        if not isinstance(verdict, dict):
            raise ValueError("verdict is not an object")
        score = verdict.get("score")
        if isinstance(score, bool) or not isinstance(score, int) or score not in {0, 1}:
            raise ValueError("score is not binary")
        if not isinstance(verdict.get("matched_entity"), str):
            raise ValueError("matched_entity is not text")
        reason = verdict.get("reason")
        if not isinstance(reason, str) or len(reason.split()) > 25:
            raise ValueError("reason is invalid")
        if verdict.get("confidence") not in {"high", "medium", "low"}:
            raise ValueError("confidence is invalid")
        if not isinstance(verdict.get("flag_for_review"), bool):
            raise ValueError("flag_for_review is not boolean")
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return None, str(exc)
    return verdict, ""


def _response_cost(response: Mapping[str, Any]) -> Decimal | None:
    usage = response.get("usage")
    if not isinstance(usage, dict) or usage.get("cost") is None:
        return None
    try:
        cost = Decimal(str(usage["cost"]))
    except (InvalidOperation, ValueError):
        return None
    if not cost.is_finite() or cost < 0:
        return None
    return cost


def validate_agreement_results(
    results: Sequence[Mapping[str, Any]], configured_judges: Sequence[Mapping[str, str]]
) -> tuple[bool, str]:
    if len(results) != 2:
        return False, "missing_judge_result"
    configured_keys = {judge["judge_key"] for judge in configured_judges}
    configured_ids = {judge["requested_model_id"] for judge in configured_judges}
    result_keys = [str(result.get("judge_key", "")) for result in results]
    requested_ids = [str(result.get("requested_judge_model_id", "")) for result in results]
    returned_ids = [str(result.get("returned_judge_model_id", "")) for result in results]
    if len(set(result_keys)) != 2 or len(set(requested_ids)) != 2 or len(set(returned_ids)) != 2:
        return False, "duplicate_judge_identity"
    if set(result_keys) != configured_keys or set(requested_ids) != configured_ids:
        return False, "unconfigured_judge_identity"
    if any(requested != returned for requested, returned in zip(requested_ids, returned_ids)):
        return False, "returned_judge_identity_mismatch"
    if any(result.get("parse_status") != "parsed" for result in results):
        return False, "judge_parse_or_api_failure"
    scores = [result.get("score") for result in results]
    if any(isinstance(score, bool) or not isinstance(score, int) or score not in {0, 1} for score in scores):
        return False, "non_binary_judge_verdict"
    if scores[0] != scores[1]:
        return False, "judge_disagreement"
    if any(result.get("flag_for_review") is not False for result in results):
        return False, "judge_review_flag"
    for field in AGREEMENT_EVIDENCE_HASH_FIELDS:
        values = [result.get(field) for result in results]
        if not all(isinstance(value, str) and value for value in values) or len(set(values)) != 1:
            return False, f"evidence_hash_mismatch:{field}"
    return True, "equal_unflagged_binary_verdicts"


def _build_context(*, staging_root: Path, judges_path: Path, out_dir: Path, repo_root: Path) -> dict[str, Any]:
    admission.audit_prepared_staging(staging_root)
    manifest = admission.read_json(staging_root / "append_input_manifest.json")
    judges_config = admission.read_json(judges_path)
    admission.validate_judges(judges_config, repo_root)
    judges = _judge_specs(judges_config)
    prompt_path = repo_root / str(judges_config.get("prompt_file", ""))
    prompt = admission.canonical_text_bytes(prompt_path).decode("utf-8")
    worklist_path = staging_root / "judge_worklist.csv"
    worklist_fields, worklist_rows = admission.read_csv_table(worklist_path)
    admission.require_columns(worklist_fields, admission.RADIOLOGIST_QUEUE_FIELDS, "judge worklist")
    terminal_policy_path = staging_root / "inputs" / "terminal_states.json"
    variants_path = staging_root / "accepted_variants_snapshot.csv"
    normalizer_path = staging_root / "provenance" / "normalizer_source.py"
    context: dict[str, Any] = {
        "manifest": manifest,
        "judges_config": judges_config,
        "judges": judges,
        "prompt": prompt,
        "prompt_sha256": admission.canonical_text_sha256(prompt_path),
        "judge_config_sha256": admission.canonical_json_sha256(judges_path),
        "judge_worklist_sha256": admission.sha256_file(worklist_path),
        "terminal_policy_sha256": admission.canonical_json_sha256(terminal_policy_path),
        "variants_snapshot_sha256": admission.sha256_file(variants_path),
        "normalizer_code_sha256": admission.canonical_text_sha256(normalizer_path),
        "manifest_input_hashes_sha256": _json_sha256(manifest.get("input_hashes", {})),
        "worklist_rows": worklist_rows,
        "cache_path": out_dir / "judge_cache.jsonl",
    }
    cases: list[dict[str, Any]] = []
    for row in worklist_rows:
        case_payload = {
            "candidate_diagnosis": row.get("diagnosis", ""),
            "reference_diagnosis": row.get("Ground_Truth_Diagnosis", ""),
        }
        case = {
            "case_id": row[admission.CASE_KEY],
            "row": row,
            "case_payload": case_payload,
            "case_payload_sha256": admission.sha256_bytes(json.dumps(case_payload, sort_keys=True).encode("utf-8")),
            "case_fingerprint_sha256": _json_sha256(
                [row[admission.CASE_KEY], case_payload["reference_diagnosis"], case_payload["candidate_diagnosis"]]
            ),
            "case_triplet_sha256": manifest.get("intake_identity", {}).get("case_triplet_sha256", ""),
            "worklist_row_sha256": admission.row_sha256(row, admission.RADIOLOGIST_QUEUE_FIELDS),
        }
        requests: list[dict[str, Any]] = []
        for judge in judges:
            payload = _http_payload(
                requested_model_id=judge["requested_model_id"],
                prompt=prompt,
                case_payload=case_payload,
                temperature=int(judges_config.get("temperature", 0)),
            )
            payload_sha = _json_sha256(payload)
            material = _cache_material(
                requested_model_id=judge["requested_model_id"],
                returned_model_id=judge["requested_model_id"],
                exact_request_payload_sha256=payload_sha,
                context=context,
                case=case,
            )
            requests.append(
                {
                    "judge": judge,
                    "payload": payload,
                    "exact_request_payload_sha256": payload_sha,
                    "cache_material": material,
                    "cache_key": _json_sha256(material),
                }
            )
        case["requests"] = requests
        cases.append(case)
    context["cases"] = cases
    return context


def _result_base(
    *,
    context: Mapping[str, Any],
    case: Mapping[str, Any],
    request: Mapping[str, Any],
    started_utc: str,
    completed_utc: str,
    returned_model_id: str,
    retry_count: int,
) -> dict[str, Any]:
    judge = request["judge"]
    return {
        "schema_version": "radle_v2_judge_result.v1",
        "intake_id": context["manifest"].get("intake_id"),
        admission.CASE_KEY: case["case_id"],
        "case_fingerprint_sha256": case["case_fingerprint_sha256"],
        "case_triplet_sha256": case["case_triplet_sha256"],
        "case_payload_sha256": case["case_payload_sha256"],
        "worklist_row_sha256": case["worklist_row_sha256"],
        "judge_key": judge["judge_key"],
        "requested_judge_model_id": judge["requested_model_id"],
        "returned_judge_model_id": returned_model_id,
        "exact_request_payload_sha256": request["exact_request_payload_sha256"],
        "judge_config_sha256": context["judge_config_sha256"],
        "prompt_sha256": context["prompt_sha256"],
        "normalizer_code_sha256": context["normalizer_code_sha256"],
        "terminal_policy_sha256": context["terminal_policy_sha256"],
        "variants_snapshot_sha256": context["variants_snapshot_sha256"],
        "judge_worklist_sha256": context["judge_worklist_sha256"],
        "manifest_input_hashes_sha256": context["manifest_input_hashes_sha256"],
        "cache_key": request["cache_key"],
        "started_utc": started_utc,
        "completed_utc": completed_utc,
        "retry_count": retry_count,
    }


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(f"{_canonical_json(row)}\n" for row in rows)
    path.write_text(text, encoding="utf-8", newline="")


def _write_evidence(
    *,
    staging_root: Path,
    out_dir: Path,
    context: Mapping[str, Any],
    results: list[dict[str, Any]],
    cache_hits: int,
    cache_misses: int,
    http_requests: int,
    actual_cost: Decimal,
    authorization_path: Path,
    malformed_cache_lines: int,
) -> dict[str, Any]:
    by_case: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_case.setdefault(str(result[admission.CASE_KEY]), []).append(result)
    worklist_by_case = {str(row[admission.CASE_KEY]): row for row in context["worklist_rows"]}
    locked_rows: list[dict[str, object]] = []
    queue_rows: list[dict[str, object]] = []
    routing_rows: list[dict[str, object]] = []
    queued_ids: set[str] = set()
    for case_id, case_results in sorted(by_case.items(), key=lambda item: admission.case_sort_key(item[0])):
        locked, reason = validate_agreement_results(case_results, context["judges"])
        if locked:
            locked_rows.append(
                {
                    admission.CASE_KEY: case_id,
                    "score": case_results[0]["score"],
                    "score_source": "ai_judges",
                    "judge_count": 2,
                }
            )
            route = "dual_judge_agreement"
        else:
            queue_rows.append(
                {
                    field: worklist_by_case[case_id].get(field, "")
                    for field in admission.RADIOLOGIST_QUEUE_FIELDS
                }
            )
            queued_ids.add(case_id)
            route = "radiologist_queue"
        routing_rows.append({admission.CASE_KEY: case_id, "route": route, "reason": reason})

    _, delta_rows = admission.read_csv_table(staging_root / "new_model_long_delta.csv")
    _, state_rows = admission.read_csv_table(staging_root / "adjudication_state.csv")
    delta_by_key = {(row[admission.CASE_KEY], row["model_blinded"]): row for row in delta_rows}
    for state_row in state_rows:
        case_id = str(state_row.get(admission.CASE_KEY, ""))
        if state_row.get("requires_radiologist") == "True" and case_id not in queued_ids:
            row = delta_by_key[(case_id, state_row["model_blinded"])]
            queue_rows.append({field: row.get(field, "") for field in admission.RADIOLOGIST_QUEUE_FIELDS})
            queued_ids.add(case_id)
            routing_rows.append(
                {
                    admission.CASE_KEY: case_id,
                    "route": "radiologist_queue",
                    "reason": "mandatory_radiologist",
                }
            )

    request_rows = [
        {
            "schema_version": "radle_v2_judge_request.v1",
            admission.CASE_KEY: case["case_id"],
            "request_payload_sha256": case["case_payload_sha256"],
            "payload": case["case_payload"],
        }
        for case in context["cases"]
    ]
    request_path = out_dir / "request_payloads.jsonl"
    _write_jsonl(request_path, request_rows)
    _write_jsonl(out_dir / "judge_request_payloads.jsonl", request_rows)
    results_path = out_dir / "judge_results.jsonl"
    _write_jsonl(results_path, results)
    cache_path = context["cache_path"]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.open("a", encoding="utf-8").close()
    admission.write_csv_table(
        out_dir / "agreement_locks.csv",
        [admission.CASE_KEY, "score", "score_source", "judge_count"],
        locked_rows,
    )
    admission.write_csv_table(
        out_dir / "dual_judge_agreements.csv",
        [admission.CASE_KEY, "score", "score_source", "judge_count"],
        locked_rows,
    )
    admission.write_csv_table(staging_root / "radiologist_queue.csv", admission.RADIOLOGIST_QUEUE_FIELDS, queue_rows)
    routing_path = out_dir / "radiologist_queue_routing_audit.json"
    admission.write_json(
        routing_path,
        {
            "schema_version": "radle_v2_radiologist_queue_routing_audit.v1",
            "routing_rows": routing_rows,
        },
    )
    summary = {
        "schema_version": "radle_v2_dual_judge_summary.v1",
        "mode": "real",
        "intake_id": context["manifest"].get("intake_id"),
        "worklist_rows": len(context["worklist_rows"]),
        "judge_result_rows": len(results),
        "locked_agreement_rows": len(locked_rows),
        "radiologist_queue_rows": len(queue_rows),
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "http_requests": http_requests,
        "actual_cost_usd": str(actual_cost),
        "prompt_sha256": context["prompt_sha256"],
        "judge_config_sha256": context["judge_config_sha256"],
        "judge_worklist_sha256": context["judge_worklist_sha256"],
        "paid_judge_authorization_sha256": admission.sha256_file(authorization_path),
        "request_payloads_sha256": admission.sha256_file(request_path),
        "judge_cache_sha256": admission.sha256_file(cache_path),
        "judge_results_sha256": admission.sha256_file(results_path),
    }
    admission.write_json(out_dir / "judge_summary.json", summary)
    config_snapshot = out_dir / "judge_config.json"
    admission.write_json(config_snapshot, context["judges_config"])
    prompt_snapshot = out_dir / "judge_prompt.txt"
    prompt_snapshot.write_text(str(context["prompt"]), encoding="utf-8", newline="")
    authorization_snapshot = out_dir / "paid_judge_authorization.json"
    authorization_snapshot.write_bytes(authorization_path.read_bytes())
    index = {
        "schema_version": "radle_v2_judge_evidence_index.v1",
        "summary": summary,
        "files": {
            "request_payloads": {"path": "request_payloads.jsonl", "sha256": admission.sha256_file(request_path)},
            "judge_cache": {"path": "judge_cache.jsonl", "sha256": admission.sha256_file(cache_path)},
            "judge_results": {"path": "judge_results.jsonl", "sha256": admission.sha256_file(results_path)},
            "agreement_locks": {
                "path": "agreement_locks.csv",
                "sha256": admission.sha256_file(out_dir / "agreement_locks.csv"),
            },
            "radiologist_queue": {
                "path": "../radiologist_queue.csv",
                "sha256": admission.sha256_file(staging_root / "radiologist_queue.csv"),
            },
            "routing_audit": {"path": routing_path.name, "sha256": admission.sha256_file(routing_path)},
            "judge_config": {"path": "judge_config.json", "sha256": admission.sha256_file(config_snapshot)},
            "judge_prompt": {"path": "judge_prompt.txt", "sha256": admission.sha256_file(prompt_snapshot)},
            "paid_judge_authorization": {
                "path": "paid_judge_authorization.json",
                "sha256": admission.sha256_file(authorization_snapshot),
            },
        },
        "malformed_cache_line_count": malformed_cache_lines,
        "authorization": {
            "sha256": admission.sha256_file(authorization_snapshot),
            "content_sha256": admission.content_only_json_sha256(authorization_snapshot),
        },
    }
    admission.write_json(out_dir / "judge_evidence_index.json", index)
    return summary


def run_openrouter_dual_judge_delta(
    *,
    staging_root: Path,
    judges_path: Path,
    out_dir: Path,
    repo_root: Path,
    authorization_path: Path | None = None,
    api_key: str | None = None,
    transport: JudgeTransport | None = None,
    clock: Callable[[], datetime] = _utc_now,
    sleeper: Callable[[float], None] = time.sleep,
    dry_run: bool = False,
) -> dict[str, Any]:
    context = _build_context(
        staging_root=staging_root,
        judges_path=judges_path,
        out_dir=out_dir,
        repo_root=repo_root,
    )
    cache, malformed_cache_lines = _read_cache(context["cache_path"])
    planned: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]] = []
    cache_hits = 0
    cache_misses = 0
    for case in context["cases"]:
        for request in case["requests"]:
            cached_result = _usable_cache_result(
                cache.get(request["cache_key"]),
                expected_key=request["cache_key"],
                expected_material=request["cache_material"],
                exact_request_payload=request["payload"],
            )
            planned.append((case, request, cached_result))
            if cached_result is None:
                cache_misses += 1
            else:
                cache_hits += 1
    max_attempts = int(context["judges_config"].get("max_retries", 1))
    worst_case_http_requests = cache_misses * max_attempts
    receipt: dict[str, Any] = {
        "phase": "dual_judge_delta",
        "mode": "dry-run" if dry_run else "real",
        "intake_id": context["manifest"].get("intake_id"),
        "judge_ids": [judge["requested_model_id"] for judge in context["judges"]],
        "worklist_rows": len(context["worklist_rows"]),
        "judge_count": len(context["judges"]),
        "logical_judge_calls": len(planned),
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "base_calls": cache_misses,
        "worst_case_http_requests": worst_case_http_requests,
        "prompt_sha256": context["prompt_sha256"],
        "judge_config_sha256": context["judge_config_sha256"],
        "judge_worklist_sha256": context["judge_worklist_sha256"],
        "malformed_cache_line_count": malformed_cache_lines,
    }
    if dry_run:
        receipt["result"] = "DRY_RUN_VALIDATED"
        return receipt

    authorization_path = authorization_path or staging_root / "paid_judge_authorization.json"
    now = _clock_utc(clock)
    authorization = validate_paid_judge_authorization(
        authorization_path=authorization_path,
        intake_id=str(context["manifest"].get("intake_id", "")),
        judge_ids=receipt["judge_ids"],
        prompt_sha256=context["prompt_sha256"],
        judge_config_sha256=context["judge_config_sha256"],
        judge_worklist_sha256=context["judge_worklist_sha256"],
        required_http_requests=worst_case_http_requests,
        now=now,
    )
    resolved_api_key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY")
    if not isinstance(resolved_api_key, str) or not resolved_api_key.strip():
        raise ValidationError("OPENROUTER_API_KEY is required for --real")
    active_transport = transport or OpenRouterJudgeTransport(
        api_key=resolved_api_key.strip(),
        base_url=str(context["judges_config"].get("base_url", "")),
    )

    max_http_requests = int(authorization["max_http_requests"])
    max_cost = Decimal(str(authorization["max_cost_usd"])) if authorization.get("max_cost_usd") is not None else None
    authorization_expiry = _parse_utc(authorization["expiry_utc"], "expiry_utc")
    actual_cost = Decimal("0")
    http_requests = 0
    results: list[dict[str, Any]] = []
    for case, request, cached_result in planned:
        if cached_result is not None:
            cached_result["cache_status"] = "hit"
            results.append(cached_result)
            continue

        started = _format_utc(_clock_utc(clock))
        response: Mapping[str, Any] | None = None
        last_error = ""
        attempt = 0
        for attempt in range(1, max_attempts + 1):
            if _clock_utc(clock) >= authorization_expiry:
                raise ValidationError("paid judge authorization expired during the real run")
            if http_requests >= max_http_requests:
                raise ValidationError("paid judge authorization HTTP request cap exhausted")
            http_requests += 1
            try:
                response = active_transport.complete(
                    payload=request["payload"],
                    timeout_seconds=float(context["judges_config"].get("timeout_seconds", 90)),
                )
                if not isinstance(response, Mapping):
                    raise JudgeTransportError("judge transport returned a non-object response")
                break
            except Exception as exc:  # The injected transport defines its own retryable failures.
                last_error = f"{type(exc).__name__}: transport attempt failed"
                if attempt < max_attempts:
                    sleeper(min(float(2 ** (attempt - 1)), 30.0))
        completed = _format_utc(_clock_utc(clock))
        if response is None:
            result = _result_base(
                context=context,
                case=case,
                request=request,
                started_utc=started,
                completed_utc=completed,
                returned_model_id="",
                retry_count=max(0, attempt - 1),
            )
            result.update(
                {
                    "terminal_api_status": "error",
                    "raw_response_sha256": "",
                    "score": None,
                    "matched_entity": "",
                    "reason": "",
                    "confidence": "",
                    "flag_for_review": True,
                    "parse_status": "api_error",
                    "api_status": "error",
                    "parse_error": "",
                    "api_error": last_error,
                    "cache_status": "miss",
                }
            )
            results.append(result)
            continue

        returned_model_id = response.get("model")
        requested_model_id = request["judge"]["requested_model_id"]
        if returned_model_id != requested_model_id:
            raise ValidationError(
                f"OpenRouter returned model mismatch for {requested_model_id}: {returned_model_id!r}"
            )
        response_cost = _response_cost(response)
        if max_cost is not None and response_cost is None:
            raise ValidationError("OpenRouter response omitted a usable cost under max_cost_usd authorization")
        if response_cost is not None:
            actual_cost += response_cost
        if max_cost is not None and actual_cost > max_cost:
            raise ValidationError("paid judge authorization max_cost_usd exceeded")

        verdict, parse_error = _parse_verdict(response)
        raw_response = dict(response)
        raw_response_sha = _json_sha256(raw_response)
        result = _result_base(
            context=context,
            case=case,
            request=request,
            started_utc=started,
            completed_utc=completed,
            returned_model_id=str(returned_model_id),
            retry_count=max(0, attempt - 1),
        )
        if verdict is None:
            result.update(
                {
                    "score": None,
                    "matched_entity": "",
                    "reason": "",
                    "confidence": "",
                    "flag_for_review": True,
                    "parse_status": "parse_error",
                    "parse_error": parse_error,
                }
            )
        else:
            result.update(verdict)
            result.update({"parse_status": "parsed", "parse_error": ""})
        result.update(
            {
                "terminal_api_status": "success",
                "raw_response_sha256": raw_response_sha,
                "api_status": "success",
                "api_error": "",
                "cache_status": "miss",
            }
        )
        entry = {
            "schema_version": "radle_v2_judge_cache_entry.v1",
            "cache_key": request["cache_key"],
            "cache_material": request["cache_material"],
            "exact_request_payload": request["payload"],
            "raw_response_sha256": raw_response_sha,
            "raw_response": raw_response,
            "result": result,
        }
        _append_cache_entry(context["cache_path"], entry)
        results.append(result)

    summary = _write_evidence(
        staging_root=staging_root,
        out_dir=out_dir,
        context=context,
        results=results,
        cache_hits=cache_hits,
        cache_misses=cache_misses,
        http_requests=http_requests,
        actual_cost=actual_cost,
        authorization_path=authorization_path,
        malformed_cache_lines=malformed_cache_lines,
    )
    receipt.update(summary)
    receipt["result"] = "PASS"
    return receipt
