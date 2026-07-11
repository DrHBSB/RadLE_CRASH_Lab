"""Probe Meta Model API reasoning_effort support for Muse Spark.

Default mode is dry-run only. Use --run to make small paid API calls. The script
records request bodies and usage summaries, but does not print or persist raw
reasoning text.

Examples:
  python scripts/debug_meta_reasoning_probe.py
  python scripts/debug_meta_reasoning_probe.py --run --efforts minimal,high,xhigh
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI


DEFAULT_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_MODEL = "muse-spark-1.1"
DEFAULT_EFFORTS = ("baseline", "minimal", "high", "xhigh")


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_key() -> str | None:
    return os.environ.get("MODEL_API_KEY") or os.environ.get("META_MODEL_API_KEY")


def parse_csv_arg(value: str | None, default: tuple[str, ...]) -> list[str]:
    if not value:
        return list(default)
    return [part.strip() for part in value.split(",") if part.strip()]


def response_to_dict(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json")
    if hasattr(response, "dict"):
        return response.dict()
    return json.loads(response.model_dump_json())


def get_reasoning_tokens(usage: dict[str, Any]) -> int | None:
    details = usage.get("completion_tokens_details")
    if isinstance(details, dict) and details.get("reasoning_tokens") is not None:
        return int(details["reasoning_tokens"])
    if usage.get("reasoning_tokens") is not None:
        return int(usage["reasoning_tokens"])
    return None


def summarize_response(payload: dict[str, Any]) -> dict[str, Any]:
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    choices = payload.get("choices") if isinstance(payload.get("choices"), list) else []
    message = choices[0].get("message", {}) if choices and isinstance(choices[0], dict) else {}
    reasoning = message.get("reasoning")
    reasoning_details = message.get("reasoning_details")
    content = message.get("content")
    return {
        "ok": True,
        "response_id": payload.get("id", ""),
        "returned_model": payload.get("model", ""),
        "provider": payload.get("provider", ""),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "reasoning_tokens": get_reasoning_tokens(usage),
        "finish_reason": choices[0].get("finish_reason", "") if choices else "",
        "content_chars": len(content or "") if isinstance(content, str) else 0,
        "reasoning_present": bool(reasoning) or bool(reasoning_details),
        "reasoning_chars": len(reasoning or "") if isinstance(reasoning, str) else 0,
        "reasoning_details_count": len(reasoning_details) if isinstance(reasoning_details, list) else 0,
    }


def build_kwargs(model: str, effort: str, max_tokens: int) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
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
    if effort != "baseline":
        kwargs["reasoning_effort"] = effort
    return kwargs


def write_outputs(results: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"meta_reasoning_probe_{utc_stamp()}.json"
    csv_path = json_path.with_suffix(".csv")
    json_path.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")

    fields = [
        "model",
        "effort",
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
        "error_type",
        "error",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--efforts", help="Comma-separated efforts, e.g. baseline,minimal,high,xhigh.")
    parser.add_argument("--max-tokens", type=int, default=768)
    parser.add_argument("--run", action="store_true", help="Make paid Meta Model API calls.")
    parser.add_argument("--base-url", default=os.environ.get("META_MODEL_API_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--output-dir", type=Path, default=repo_root() / "review")
    args = parser.parse_args()

    efforts = parse_csv_arg(args.efforts, DEFAULT_EFFORTS)
    client = None
    if args.run:
        key = read_key()
        if not key:
            raise SystemExit("Set MODEL_API_KEY or META_MODEL_API_KEY before using --run.")
        client = OpenAI(base_url=args.base_url, api_key=key)

    results: list[dict[str, Any]] = []
    for effort in efforts:
        kwargs = build_kwargs(args.model, effort, args.max_tokens)
        record: dict[str, Any] = {
            "model": args.model,
            "effort": effort,
            "request_kwargs": kwargs,
        }
        if not args.run:
            record["dry_run"] = True
            print(f"DRY {effort}: {json.dumps(kwargs, sort_keys=True)}")
            results.append(record)
            continue

        try:
            response = client.chat.completions.create(**kwargs)
            record.update(summarize_response(response_to_dict(response)))
            print(
                f"RUN {effort}: ok returned_model={record.get('returned_model')} "
                f"reasoning_tokens={record.get('reasoning_tokens')} "
                f"reasoning_present={record.get('reasoning_present')} "
                f"finish={record.get('finish_reason')}"
            )
        except Exception as exc:
            record.update(
                {
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            print(f"RUN {effort}: ERROR {type(exc).__name__}: {exc}")
        results.append(record)

    json_path, csv_path = write_outputs(results, args.output_dir)
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
