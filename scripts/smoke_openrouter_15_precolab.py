"""One-request-per-arm synthetic OpenRouter readiness smoke for the 15-arm RadLE roster.

No clinical data is sent. Outputs are private and ignored by Git. A rerun must
use a new directory; the script never retries an inference request.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
API = "https://openrouter.ai/api/v1"
KEY_NAME = "OPENROUTER_API_KEY"
ENV_FILE = ROOT / "radle_api_keys.env"
PROMPT = (
    "This is a deliberately synthetic, non-medical API check. Describe the "
    "simple geometric shapes in the attached image if present; otherwise "
    "describe the word CIRCLE. Return only a JSON object with exactly two "
    "keys: diagnosis (a nonempty string) and likert_score (an integer 0 to 4 "
    "indicating confidence). Do not make a medical diagnosis."
)
# id, target effort, endpoint tag, expected provider, ZDR, output-token parameter.
# Qwen Flash has no OpenRouter effort control. Alibaba documents native xhigh as
# its default; the receipt keeps that separate from a proven explicit effort.
ARMS = [('qwen/qwen3.8-flash', None, 'alibaba', 'Alibaba', False, 'max_tokens'),
 ('deepseek/deepseek-v4-flash-vision-exp', 'max', 'deepinfra/fp8', 'DeepInfra', True, 'max_tokens'),
 ('meta/muse-spark-1.3', 'max', 'meta', 'Meta', False, 'max_tokens'),
 ('z-ai/glm-5.3-flash', 'max', 'z-ai/fp8', 'Z.AI', True, 'max_tokens'),
 ('qwen/qwen3.8-max-prime', 'xhigh', 'alibaba', 'Alibaba', False, 'max_tokens'),
 ('anthropic/claude-sonnet-5.5', 'max', 'anthropic', 'Anthropic', False, 'max_tokens'),
 ('anthropic/claude-opus-5.5', 'max', 'anthropic', 'Anthropic', False, 'max_tokens'),
 ('deepseek/deepseek-v4.1-flash', 'max', 'fireworks', 'Fireworks', True, 'max_tokens'),
 ('google/gemini-3.7-flash', 'high', 'google-vertex/global', 'Google', True, 'max_tokens'),
 ('meta/muse-spark-1.2', 'xhigh', 'meta', 'Meta', False, 'max_tokens'),
 ('moonshotai/kimi-k3', 'max', 'moonshotai/mxfp4', 'Moonshot AI', True, 'max_tokens'),
 ('openai/gpt-6.1-sol-pro', 'max', 'openai', 'OpenAI', False, 'max_tokens'),
 ('openai/gpt-6-sol', 'max', 'openai', 'OpenAI', False, 'max_tokens'),
 ('x-ai/grok-4.7', 'xhigh', 'xai/zdr', 'xAI', True, 'max_tokens'),
 ('z-ai/glm-5.3-flashx', 'max', 'z-ai/fp8', 'Z.AI', True, 'max_tokens')]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_key() -> str:
    pattern = re.compile(r"^\s*" + re.escape(KEY_NAME) + r"\s*=\s*(.*?)\s*$")
    values = []
    for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        match = pattern.match(line)
        if match:
            values.append(match.group(1).strip().strip('"').strip("'"))
    if not values or not values[-1]:
        raise RuntimeError(f"{KEY_NAME} is absent or empty in {ENV_FILE}")
    return values[-1]


def request_json(url: str, key: str | None = None, payload: dict | None = None,
                 timeout: int = 40) -> tuple[int, dict]:
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    if payload is not None:
        headers["Content-Type"] = "application/json"
        headers["X-OpenRouter-Cache"] = "false"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        if key:
            raw = raw.replace(key, "[REDACTED]")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"error": {"message": raw[:600]}}


def synthetic_png() -> bytes:
    width = height = 32
    pixels = bytearray()
    for y in range(height):
        pixels.append(0)
        for x in range(width):
            blue_circle = (x - 16) ** 2 + (y - 16) ** 2 < 100
            pixels.extend((45, 105, 220) if blue_circle else (255, 255, 255))
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(pixels), 9))
            + chunk(b"IEND", b""))


def readable_reasoning(message: dict) -> tuple[str, str]:
    direct = message.get("reasoning")
    if isinstance(direct, str) and direct.strip():
        return direct.strip(), "message.reasoning"
    found = []
    def walk(value: object) -> None:
        if isinstance(value, dict):
            if any(token in str(value.get("type", "")).lower() for token in ("encrypted", "redacted")):
                return
            for key, child in value.items():
                if key.lower() in {"text", "summary", "thinking", "reasoning_content"} and isinstance(child, str):
                    if child.strip():
                        found.append(child.strip())
                elif key.lower() not in {"data", "signature"}:
                    walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(message.get("reasoning_details"))
    return ("\n\n".join(found), "message.reasoning_details" if found else "unavailable")


def preflight(key: str) -> list[dict]:
    status, catalog = request_json(API + "/models")
    if status != 200:
        raise RuntimeError(f"Public model catalog returned HTTP {status}")
    status, zdr_result = request_json(API + "/endpoints/zdr", key)
    if status != 200:
        raise RuntimeError(f"Authenticated ZDR list returned HTTP {status}")
    models = {item["id"]: item for item in catalog["data"]}
    zdr_keys = {(item["model_id"], item["tag"], item["name"]) for item in zdr_result["data"]}
    prepared = []
    for model_id, effort, tag, provider_name, zdr_required, token_param in ARMS:
        model = models.get(model_id)
        if not model:
            raise RuntimeError(f"{model_id}: exact model absent from public catalog")
        status, result = request_json(API + "/models/" + model_id + "/endpoints")
        if status != 200:
            raise RuntimeError(f"{model_id}: endpoints returned HTTP {status}")
        matches = [e for e in result["data"]["endpoints"] if e["tag"] == tag and e["provider_name"] == provider_name]
        if len(matches) != 1:
            raise RuntimeError(f"{model_id}: expected one exact {tag} endpoint; found {len(matches)}")
        endpoint = matches[0]
        parameters = set(endpoint["supported_parameters"])
        required = {"reasoning", "response_format", token_param}
        if effort is not None:
            required.add("reasoning_effort")
            if effort not in (model.get("reasoning") or {}).get("supported_efforts", []):
                raise RuntimeError(f"{model_id}: {effort} absent from current catalog supported_efforts")
        else:
            if model_id != "qwen/qwen3.8-flash":
                raise RuntimeError(f"{model_id}: unexpected default-effort arm")
            if not (model.get("reasoning") or {}).get("default_enabled"):
                raise RuntimeError(f"{model_id}: default reasoning no longer advertised")
        missing = required - parameters
        if missing:
            raise RuntimeError(f"{model_id}: {tag} lacks {sorted(missing)}")
        zdr_listed = (model_id, tag, endpoint["name"]) in zdr_keys
        if zdr_required and not zdr_listed:
            raise RuntimeError(f"{model_id}: {tag} is no longer ZDR listed")
        if not zdr_required and (model_id, tag, endpoint["name"]) in zdr_keys:
            raise RuntimeError(f"{model_id}: Selected official route became ZDR listed; enable ZDR before inference")
        modalities = (model.get("architecture") or {}).get("input_modalities") or []
        if "text" not in modalities:
            raise RuntimeError(f"{model_id}: text input not advertised")
        prepared.append({
            "id": model_id, "effort": effort, "tag": tag, "provider": provider_name,
            "zdr": zdr_required, "zdr_listed": zdr_listed, "token_param": token_param,
            "image": "image" in modalities, "endpoint_name": endpoint["name"],
            "pricing": endpoint.get("pricing"), "parameters": sorted(parameters),
        })
    return prepared


def generation_metadata(key: str, generation_id: str) -> dict:
    url = API + "/generation?" + urllib.parse.urlencode({"id": generation_id})
    for attempt in range(3):
        status, result = request_json(url, key)
        if status == 200 and isinstance(result.get("data"), dict):
            return result["data"]
        if attempt < 2:
            time.sleep(2)
    raise RuntimeError(f"Generation metadata unavailable: HTTP {status}")


def run_one(arm: dict, key: str, folder: pathlib.Path, image: bytes, max_tokens: int) -> dict:
    model_id = arm["id"]
    provider = {
        "only": [arm["tag"]],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "deny",
    }
    if arm["zdr"]:
        provider["zdr"] = True
    content = [{"type": "text", "text": PROMPT}]
    if arm["image"]:
        content.append({"type": "image_url", "image_url": {
            "url": "data:image/png;base64," + base64.b64encode(image).decode("ascii")
        }})
    reasoning = {"exclude": False}
    if arm["effort"] is not None:
        reasoning["effort"] = arm["effort"]
    else:
        reasoning["enabled"] = True
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": content}],
        "provider": provider,
        "reasoning": reasoning,
        "response_format": {"type": "json_object"},
        arm["token_param"]: max_tokens,
    }
    slug = re.sub(r"[^a-z0-9]+", "_", model_id)
    folder = folder / slug
    folder.mkdir()
    receipt = {
        "started_at_utc": utc_now(), "key_name": KEY_NAME,
        "requested_model": model_id, "requested_provider_tag": arm["tag"],
        "expected_provider": arm["provider"], "zdr_requested": arm["zdr"],
        "zdr_listed": arm["zdr_listed"], "data_collection": "deny",
        "fallbacks_allowed": False, "require_parameters": True,
        "response_cache": "false", "requested_reasoning": reasoning,
        "qwen_flash_native_default_xhigh_documented": model_id == "qwen/qwen3.8-flash",
        "explicit_xhigh_proven": False if model_id == "qwen/qwen3.8-flash" else None,
        "response_format": "json_object", "output_token_parameter": arm["token_param"],
        "output_token_cap": max_tokens, "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(),
        "synthetic_image_sha256": hashlib.sha256(image).hexdigest() if arm["image"] else None,
        "image_sent": arm["image"], "endpoint_name": arm["endpoint_name"],
        "pass": False,
    }
    save_json(folder / "request_preview.json", receipt)
    save_json(folder / "state.json", {"state": "STARTED", "at_utc": utc_now()})
    started = time.monotonic()
    status, response = request_json(API + "/chat/completions", key, payload, timeout=240)
    receipt["http_status"] = status
    receipt["elapsed_seconds"] = round(time.monotonic() - started, 2)
    if status != 200:
        receipt["error"] = str((response.get("error") or {}).get("message", ""))[:600]
        save_json(folder / "receipt.json", receipt)
        save_json(folder / "state.json", {"state": "FAILED", "at_utc": utc_now()})
        return receipt
    save_json(folder / "raw_openrouter_response.json", response)
    choices = response.get("choices") or []
    choice = choices[0] if choices else {}
    message = choice.get("message") or {}
    content_text = message.get("content") or ""
    if not isinstance(content_text, str):
        content_text = json.dumps(content_text, ensure_ascii=False)
    reasoning_text, reasoning_source = readable_reasoning(message)
    (folder / "reasoning_summary.txt").write_text(reasoning_text, encoding="utf-8")
    receipt["returned_model"] = response.get("model")
    receipt["returned_provider"] = response.get("provider")
    receipt["finish_reason"] = choice.get("finish_reason")
    receipt["reasoning_source"] = reasoning_source
    receipt["reasoning_characters"] = len(reasoning_text)
    receipt["final_characters"] = len(content_text)
    receipt["usage"] = response.get("usage")
    receipt["response_cost_usd"] = (response.get("usage") or {}).get("cost")
    receipt["generation_id"] = response.get("id")
    try:
        parsed = json.loads(content_text)
        schema_valid = (
            isinstance(parsed, dict) and set(parsed) == {"diagnosis", "likert_score"}
            and isinstance(parsed["diagnosis"], str) and bool(parsed["diagnosis"].strip())
            and type(parsed["likert_score"]) is int and 0 <= parsed["likert_score"] <= 4
        )
    except (ValueError, TypeError):
        schema_valid = False
    receipt["schema_valid"] = schema_valid
    try:
        generation = generation_metadata(key, response["id"])
        receipt["generation_model"] = generation.get("model")
        receipt["generation_provider"] = generation.get("provider_name")
        receipt["generation_cost_usd"] = generation.get("total_cost")
    except (RuntimeError, KeyError) as exc:
        receipt["generation_error"] = str(exc)
    receipt["pass"] = bool(
        receipt["returned_model"] == model_id
        and receipt.get("returned_provider") == arm["provider"]
        and receipt.get("generation_model") in (None, model_id)
        and receipt.get("generation_provider") in (None, arm["provider"])
        and choice.get("finish_reason") == "stop"
        and schema_valid and reasoning_text.strip()
    )
    save_json(folder / "receipt.json", receipt)
    save_json(folder / "state.json", {"state": "PASS" if receipt["pass"] else "FAILED", "at_utc": utc_now()})
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="Issue one paid synthetic request per arm after metadata preflight")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--output-dir", type=pathlib.Path)
    parser.add_argument("--resume", action="store_true", help="Continue a saved run without replaying any started arm")
    args = parser.parse_args()
    if not 512 <= args.max_tokens <= 8192:
        parser.error("--max-tokens must be 512..8192")
    key = load_key()
    prepared = preflight(key)
    print(f"Metadata preflight: {len(prepared)} exact models/routes, {sum(a['zdr'] for a in prepared)} ZDR, {sum(not a['zdr'] for a in prepared)} non-ZDR")
    if not args.run:
        for arm in prepared:
            print(f"{arm['id']} tag={arm['tag']} zdr={arm['zdr']} effort={arm['effort'] or 'native-default'} image={arm['image']}")
        return 0
    folder = args.output_dir or ROOT / "outputs" / ("openrouter_15_precolab_smoke_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    folder = folder.resolve()
    image = synthetic_png()
    if args.resume:
        if not args.output_dir or not folder.is_dir():
            raise RuntimeError("--resume requires an existing --output-dir")
        prior = json.loads((folder / "metadata_preflight.json").read_text(encoding="utf-8"))
        comparable = lambda rows: [(a["id"], a["effort"], a["tag"], a["zdr"], a["token_param"], a["image"]) for a in rows]
        if comparable(prior) != comparable(prepared):
            raise RuntimeError("Live route contract differs from saved run; resume refused")
        summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
        if summary["key_name"] != KEY_NAME or summary["expected"] != len(prepared):
            raise RuntimeError("Saved summary contract mismatch")
    else:
        if folder.exists():
            raise RuntimeError(f"Output directory already exists: {folder}")
        folder.mkdir(parents=True)
        (folder / "synthetic_shapes.png").write_bytes(image)
        save_json(folder / "metadata_preflight.json", prepared)
        summary = {"started_at_utc": utc_now(), "expected": len(prepared), "key_name": KEY_NAME,
                   "results": [], "complete": False, "stopped": False}
        save_json(folder / "summary.json", summary)
    for arm in prepared:
        if args.resume and any(r["model"] == arm["id"] for r in summary["results"]):
            cell = folder / re.sub(r"[^a-z0-9]+", "_", arm["id"])
            receipt = json.loads((cell / "receipt.json").read_text(encoding="utf-8"))
            if not receipt.get("pass") or not (cell / "raw_openrouter_response.json").exists():
                raise RuntimeError(f"{arm['id']}: existing attempt is unresolved; inference replay refused")
            for row in summary["results"]:
                if row["model"] == arm["id"]:
                    row["pass"] = True
                    row["cost_usd"] = receipt.get("generation_cost_usd") or receipt.get("response_cost_usd")
            summary["stopped"] = False
            save_json(folder / "summary.json", summary)
            print(f"Preserved prior {arm['id']} without replay", flush=True)
            continue
        print(f"Starting {arm['id']} via {arm['tag']} (zdr={arm['zdr']})", flush=True)
        receipt = run_one(arm, key, folder, image, args.max_tokens)
        summary["results"].append({"model": arm["id"], "pass": receipt["pass"],
                                   "http_status": receipt.get("http_status"),
                                   "reasoning_characters": receipt.get("reasoning_characters", 0),
                                   "cost_usd": receipt.get("generation_cost_usd")})
        summary["stopped"] = not receipt["pass"]
        summary["complete"] = len(summary["results"]) == len(prepared) and all(x["pass"] for x in summary["results"])
        save_json(folder / "summary.json", summary)
        print(f"{arm['id']}: {'PASS' if receipt['pass'] else 'STOP'} HTTP {receipt.get('http_status')}", flush=True)
        if not receipt["pass"]:
            print(f"Stopped. Private receipt: {folder / re.sub(r'[^a-z0-9]+', '_', arm['id']) / 'receipt.json'}")
            return 2
    print(f"All {len(prepared)} synthetic smokes passed. Private summary: {folder / 'summary.json'}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Stopped before or between inference requests: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)

