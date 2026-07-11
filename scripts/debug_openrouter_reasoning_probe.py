"""Probe OpenRouter reasoning/thinking controls for Grok and candidate Muse routes.

Default mode is metadata + dry-run only. It does not make paid model calls unless
--run is supplied.

Examples:
  python scripts/debug_openrouter_reasoning_probe.py
  python scripts/debug_openrouter_reasoning_probe.py --run --variants baseline,high
  python scripts/debug_openrouter_reasoning_probe.py --run --models x-ai/grok-4.5,muse-spark-1.1 --allow-unlisted

The request body shown here is the OpenRouter REST body. When using the OpenAI
SDK, the non-OpenAI fields here are passed through via extra_body.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

DEFAULT_MODELS = ("x-ai/grok-4.5", "muse-spark-1.1")
DEFAULT_VARIANTS = ("baseline", "high")

VARIANT_REASONING: dict[str, dict[str, Any] | None] = {
    "baseline": None,
    "enabled": {"enabled": True},
    "low": {"effort": "low"},
    "medium": {"effort": "medium"},
    "high": {"effort": "high"},
    "xhigh": {"effort": "xhigh"},
    "none": {"effort": "none"},
}


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_key() -> str | None:
    return (
        os.environ.get("TEST_OPENROUTER_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("OPENROUTER_KEY")
    )


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    api_key: str | None = None,
    timeout: int = 60,
) -> tuple[int, dict[str, Any]]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://radle.local/debug-openrouter-reasoning-probe",
        "X-Title": "RadLE OpenRouter Reasoning Probe",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(data) if data else {}
    except urllib.error.HTTPError as exc:
        data = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(data) if data else {}
        except json.JSONDecodeError:
            parsed = {"raw_error": data}
        return exc.code, parsed


def load_model_index() -> dict[str, dict[str, Any]]:
    status, payload = request_json(OPENROUTER_MODELS_URL, timeout=30)
    if status >= 400:
        raise RuntimeError(f"OpenRouter model metadata request failed: HTTP {status}: {payload}")
    models = payload.get("data") or []
    return {str(item.get("id")): item for item in models if item.get("id")}


def parse_csv_arg(value: str | None, default: tuple[str, ...]) -> list[str]:
    if not value:
        return list(default)
    return [part.strip() for part in value.split(",") if part.strip()]


def default_provider_for(model_id: str) -> dict[str, Any] | None:
    if model_id.startswith("x-ai/"):
        return {"only": ["xAI"], "allow_fallbacks": False}
    return None


def build_payload(
    model_id: str,
    variant: str,
    *,
    max_tokens: int,
    include_provider_lock: bool,
    thinking_variant: bool,
) -> dict[str, Any]:
    request_model_id = f"{model_id}:thinking" if thinking_variant else model_id
    payload: dict[str, Any] = {
        "model": request_model_id,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Solve this compact diagnostic-style reasoning task. "
                    "A 7-year-old has a metaphyseal corner fracture pattern after minor trauma. "
                    "Return only JSON: {\"answer\":\"...\",\"confidence\":0-4}."
                ),
            }
        ],
        "max_tokens": max_tokens,
    }

    if variant == "top_level_reasoning_effort_high":
        payload["reasoning_effort"] = "high"
    else:
        reasoning = VARIANT_REASONING[variant]
        if reasoning is not None:
            payload["reasoning"] = reasoning

    provider = default_provider_for(model_id) if include_provider_lock else None
    if provider:
        payload["provider"] = provider

    return payload


def get_reasoning_tokens(usage: dict[str, Any]) -> int | None:
    details = usage.get("completion_tokens_details")
    if isinstance(details, dict) and details.get("reasoning_tokens") is not None:
        return int(details["reasoning_tokens"])
    if usage.get("reasoning_tokens") is not None:
        return int(usage["reasoning_tokens"])
    return None


def summarize_response(status: int, payload: dict[str, Any], elapsed_s: float) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "http_status": status,
        "elapsed_seconds": round(elapsed_s, 3),
        "ok": status < 400,
        "response_id": payload.get("id", ""),
        "returned_model": payload.get("model", ""),
        "provider": payload.get("provider", ""),
    }

    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    summary.update(
        {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "reasoning_tokens": get_reasoning_tokens(usage),
        }
    )

    choices = payload.get("choices") if isinstance(payload.get("choices"), list) else []
    message = choices[0].get("message", {}) if choices and isinstance(choices[0], dict) else {}
    reasoning = message.get("reasoning")
    reasoning_details = message.get("reasoning_details")
    content = message.get("content")
    summary.update(
        {
            "finish_reason": choices[0].get("finish_reason", "") if choices else "",
            "content_chars": len(content or "") if isinstance(content, str) else 0,
            "reasoning_present": bool(reasoning) or bool(reasoning_details),
            "reasoning_chars": len(reasoning or "") if isinstance(reasoning, str) else 0,
            "reasoning_details_count": len(reasoning_details) if isinstance(reasoning_details, list) else 0,
            "error": payload.get("error", payload if status >= 400 else ""),
        }
    )
    return summary


def write_outputs(results: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"openrouter_reasoning_probe_{utc_stamp()}.json"
    csv_path = json_path.with_suffix(".csv")

    json_path.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")

    fields = [
        "model",
        "variant",
        "thinking_variant",
        "listed_in_openrouter_models",
        "metadata_reasoning",
        "http_status",
        "ok",
        "returned_model",
        "provider",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "reasoning_tokens",
        "reasoning_present",
        "reasoning_chars",
        "reasoning_details_count",
        "finish_reason",
        "elapsed_seconds",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for result in results:
            row = dict(result)
            row["metadata_reasoning"] = json.dumps(row.get("metadata_reasoning"), sort_keys=True)
            writer.writerow(row)

    return json_path, csv_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", help="Comma-separated OpenRouter model IDs to probe.")
    parser.add_argument(
        "--variants",
        help=(
            "Comma-separated variants. Supported: "
            + ",".join(sorted((*VARIANT_REASONING.keys(), "top_level_reasoning_effort_high")))
        ),
    )
    parser.add_argument("--max-tokens", type=int, default=768)
    parser.add_argument("--run", action="store_true", help="Make paid OpenRouter chat calls.")
    parser.add_argument(
        "--allow-unlisted",
        action="store_true",
        help="Allow paid probe attempts for model IDs absent from GET /api/v1/models.",
    )
    parser.add_argument(
        "--no-provider-lock",
        action="store_true",
        help="Do not add provider.only routing for xAI models.",
    )
    parser.add_argument(
        "--include-thinking-variant",
        action="store_true",
        help="Also test model IDs with ':thinking' appended.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root() / "review",
        help="Where to write JSON/CSV probe receipts.",
    )
    args = parser.parse_args(argv)

    models = parse_csv_arg(args.models, DEFAULT_MODELS)
    variants = parse_csv_arg(args.variants, DEFAULT_VARIANTS)
    allowed_variants = set(VARIANT_REASONING) | {"top_level_reasoning_effort_high"}
    unknown = [variant for variant in variants if variant not in allowed_variants]
    if unknown:
        raise SystemExit(f"Unknown variants: {', '.join(unknown)}")

    model_index = load_model_index()
    api_key = read_key()
    if args.run and not api_key:
        raise SystemExit("Set TEST_OPENROUTER_API_KEY or OPENROUTER_API_KEY before using --run.")

    results: list[dict[str, Any]] = []
    model_forms = [False, True] if args.include_thinking_variant else [False]
    print(f"OpenRouter metadata loaded: {len(model_index)} models")

    for model_id in models:
        metadata = model_index.get(model_id)
        listed = metadata is not None
        reasoning_meta = metadata.get("reasoning") if metadata else None
        print(f"\nMODEL {model_id}")
        print(f"  listed: {listed}")
        print(f"  reasoning metadata: {json.dumps(reasoning_meta, sort_keys=True)}")

        if args.run and not listed and not args.allow_unlisted:
            print("  skipping paid calls because model is not listed; pass --allow-unlisted to test anyway")

        for thinking_variant in model_forms:
            for variant in variants:
                payload = build_payload(
                    model_id,
                    variant,
                    max_tokens=args.max_tokens,
                    include_provider_lock=not args.no_provider_lock,
                    thinking_variant=thinking_variant,
                )
                record: dict[str, Any] = {
                    "model": model_id,
                    "variant": variant,
                    "thinking_variant": thinking_variant,
                    "listed_in_openrouter_models": listed,
                    "metadata_reasoning": reasoning_meta,
                    "request_payload": payload,
                }

                if not args.run or (not listed and not args.allow_unlisted):
                    record["dry_run"] = True
                    print(f"  DRY {variant} thinking_variant={thinking_variant}: {json.dumps(payload, sort_keys=True)}")
                    results.append(record)
                    continue

                started = time.perf_counter()
                status, response = request_json(
                    OPENROUTER_CHAT_URL,
                    method="POST",
                    payload=payload,
                    api_key=api_key,
                    timeout=120,
                )
                elapsed_s = time.perf_counter() - started
                record.update(summarize_response(status, response, elapsed_s))
                print(
                    "  RUN "
                    f"{variant} thinking_variant={thinking_variant}: "
                    f"HTTP {record['http_status']} "
                    f"returned_model={record.get('returned_model')} "
                    f"reasoning_tokens={record.get('reasoning_tokens')} "
                    f"reasoning_present={record.get('reasoning_present')} "
                    f"finish={record.get('finish_reason')}"
                )
                results.append(record)

    json_path, csv_path = write_outputs(results, args.output_dir)
    print(f"\nWrote {json_path}")
    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
