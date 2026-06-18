"""Experimental InternVL probe for RadLE.

This script intentionally does not modify or import the official MODELS roster.
It runs one explicit OpenAI-compatible model config against the existing
benchmark helper path and writes generated outputs under local_smoke/ by default.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import sys
import time
import types
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from types import SimpleNamespace


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
DEFAULT_MODEL_ID = "OpenGVLab/InternVL3_5-8B"
DEFAULT_MODEL_NAME = "internvl3_5_8b"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
INTERNVL_SEARCH_TERMS = ("internvl", "opengvlab", "intern")


def install_optional_provider_stubs() -> None:
    """Let radle_benchmark import when native provider SDKs are absent locally."""
    if importlib.util.find_spec("anthropic") is None:
        sys.modules["anthropic"] = types.ModuleType("anthropic")

    try:
        from google import genai as _google_genai  # noqa: F401
        from google.genai import types as _google_genai_types  # noqa: F401
        return
    except Exception:
        pass

    google_mod = sys.modules.get("google")
    if google_mod is None:
        google_mod = types.ModuleType("google")
        google_mod.__path__ = []

    genai_mod = types.ModuleType("google.genai")
    genai_types_mod = types.ModuleType("google.genai.types")
    genai_mod.types = genai_types_mod
    google_mod.genai = genai_mod

    sys.modules["google"] = google_mod
    sys.modules["google.genai"] = genai_mod
    sys.modules["google.genai.types"] = genai_types_mod


def import_benchmark_module():
    """Import benchmark helpers after making src importable."""
    sys.path.insert(0, str(SRC_DIR))
    install_optional_provider_stubs()
    try:
        import radle_benchmark as rb  # pylint: disable=import-error,import-outside-toplevel
    except ModuleNotFoundError as exc:
        if exc.name == "pandas":
            raise SystemExit(
                "Missing pandas in this Python environment. Use the Colab runtime, "
                "install the benchmark dependencies, or run with the bundled Codex "
                "Python runtime for local smoke validation."
            ) from exc
        raise

    return rb


def load_env_file(path: pathlib.Path) -> bool:
    """Load KEY=VALUE lines into os.environ without printing secret values."""
    if not path.exists():
        return False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    return True


def timestamped_default_output(model_name: str) -> pathlib.Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return REPO_ROOT / "local_smoke" / f"{model_name}_probe_{stamp}.csv"


def fetch_openrouter_internvl_matches(timeout_seconds: float = 20.0) -> list[dict]:
    """Return OpenRouter model rows whose id/name/HF id look InternVL-related."""
    with urllib.request.urlopen(OPENROUTER_MODELS_URL, timeout=timeout_seconds) as response:
        payload = json.loads(response.read().decode("utf-8"))

    matches = []
    for item in payload.get("data", []):
        searchable = " ".join(
            str(item.get(key, ""))
            for key in ("id", "canonical_slug", "hugging_face_id", "name")
        ).lower()
        if any(term in searchable for term in INTERNVL_SEARCH_TERMS):
            matches.append({
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "hugging_face_id": item.get("hugging_face_id", ""),
                "modality": item.get("architecture", {}).get("modality", ""),
            })
    return matches


def print_openrouter_preflight(skip: bool) -> None:
    if skip:
        print("OpenRouter metadata preflight: skipped by flag.")
        return

    try:
        matches = fetch_openrouter_internvl_matches()
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        print(f"OpenRouter metadata preflight: unavailable ({type(exc).__name__}).")
        return

    if not matches:
        print("OpenRouter metadata preflight: no InternVL/OpenGVLab/intern matches.")
        return

    print(f"OpenRouter metadata preflight: {len(matches)} potential match(es).")
    for match in matches:
        print(
            "  "
            f"id={match['id']} | name={match['name']} | "
            f"hf={match['hugging_face_id']} | modality={match['modality']}"
        )


def is_local_base_url(base_url: str) -> bool:
    parsed = urllib.parse.urlparse(base_url)
    return parsed.hostname in {"localhost", "127.0.0.1", "::1"}


def resolve_api_key(base_url: str, api_key_env: str, allow_empty_api_key: bool) -> str:
    api_key = os.environ.get(api_key_env, "")
    if api_key:
        return api_key
    if allow_empty_api_key or is_local_base_url(base_url):
        return "EMPTY"
    raise SystemExit(
        f"Missing API key env var {api_key_env}. "
        "Set it in the environment or radle_api_keys.env, or pass --allow-empty-api-key "
        "for an unauthenticated local endpoint."
    )


class DryRunOpenAICompatibleClient:
    """Small fake OpenAI-compatible client for local schema validation."""

    def __init__(self, model_id: str):
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self.create_completion)
        )
        self.model_id = model_id

    def create_completion(self, **kwargs):
        model = kwargs.get("model", self.model_id)
        raw = '{"diagnosis": "I don\'t know", "likert_score": null}'
        message = SimpleNamespace(content=raw, model_extra={})
        usage = SimpleNamespace(
            prompt_tokens=123,
            completion_tokens=12,
            completion_tokens_details=SimpleNamespace(reasoning_tokens=0),
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message)],
            usage=usage,
            model=model,
            model_extra={"provider": "DRY_RUN_FAKE"},
        )


def build_client(args):
    if args.dry_run:
        return DryRunOpenAICompatibleClient(args.model_id)

    if not args.base_url:
        raise SystemExit(
            "Live probe requires --base-url or INTERNVL_BASE_URL. "
            "Use --dry-run for local schema validation without an endpoint."
        )

    api_key = resolve_api_key(args.base_url, args.api_key_env, args.allow_empty_api_key)
    from openai import OpenAI  # pylint: disable=import-error,import-outside-toplevel

    return OpenAI(base_url=args.base_url, api_key=api_key)


def validate_output_csv(rb, output_csv: pathlib.Path, model_name: str) -> int:
    df = rb.pd.read_csv(output_csv, dtype={"Master_Case_ID": str})
    required = [
        "Master_Case_ID",
        "Associated_Images",
        "Image_SHA256",
        f"Diagnosis_{model_name}",
        f"Likert_{model_name}",
        f"Prompt_Tokens_{model_name}",
        f"Total_Tokens_Out_{model_name}",
        f"Latency_{model_name}",
        f"Provider_{model_name}",
        f"Raw_Response_{model_name}",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise SystemExit(f"Output CSV missing required columns: {missing}")

    bad_rows = []
    for idx, row in df.iterrows():
        diagnosis = rb.safe_str(row.get(f"Diagnosis_{model_name}", "")).strip()
        likert = row.get(f"Likert_{model_name}", "")
        if diagnosis in {"", "API_ERROR", "PARSE_FAILED", "JSON_MISSING_KEY"}:
            bad_rows.append((idx, diagnosis or "EMPTY_DIAGNOSIS"))
            continue
        if rb.is_exact_valid_i_dont_know(diagnosis) or rb.is_abstention_variant(diagnosis):
            continue
        if not rb.is_valid_likert_value(likert):
            bad_rows.append((idx, f"INVALID_LIKERT:{rb.safe_str(likert)}"))

    if bad_rows:
        preview = ", ".join(f"row {idx}={reason}" for idx, reason in bad_rows[:5])
        raise SystemExit(f"Output CSV contains unparseable/invalid rows: {preview}")

    return len(df)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an experimental InternVL RadLE probe through an OpenAI-compatible endpoint."
    )
    parser.add_argument("--base-url", default=os.environ.get("INTERNVL_BASE_URL", ""))
    parser.add_argument("--api-key-env", default="INTERNVL_API_KEY")
    parser.add_argument("--allow-empty-api-key", action="store_true")
    parser.add_argument("--model-id", default=os.environ.get("INTERNVL_MODEL_ID", DEFAULT_MODEL_ID))
    parser.add_argument("--model-name", default=os.environ.get("INTERNVL_MODEL_NAME", DEFAULT_MODEL_NAME))
    parser.add_argument("--image-folder", default=str(REPO_ROOT / "local_smoke" / "images"))
    parser.add_argument("--output-csv", default="")
    parser.add_argument("--test-limit", type=int, default=1)
    parser.add_argument("--max-output-tokens", type=int, default=16384)
    parser.add_argument("--temperature", type=float, default=0.01)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-openrouter-check", action="store_true")
    parser.add_argument("--env-file", default=str(REPO_ROOT / "radle_api_keys.env"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    rb = import_benchmark_module()

    env_loaded = load_env_file(pathlib.Path(args.env_file))
    if env_loaded:
        print("Loaded local env file variables (values hidden).")

    print_openrouter_preflight(skip=args.skip_openrouter_check)

    output_csv = pathlib.Path(args.output_csv) if args.output_csv else timestamped_default_output(args.model_name)
    output_csv = output_csv if output_csv.is_absolute() else REPO_ROOT / output_csv
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    image_folder = pathlib.Path(args.image_folder)
    image_folder = image_folder if image_folder.is_absolute() else REPO_ROOT / image_folder
    if not image_folder.exists():
        raise SystemExit(f"Image folder not found: {image_folder}")

    model = {
        "name": args.model_name,
        "id": args.model_id,
        "extra": None,
    }
    mode = "dry-run fake client" if args.dry_run else "live endpoint"
    print(f"InternVL experimental probe mode: {mode}")
    print(f"Model id: {args.model_id}")
    print(f"Model name: {args.model_name}")
    print(f"Image folder: {image_folder}")
    print(f"Output CSV: {output_csv}")
    print(f"Test limit: {args.test_limit}")

    client = build_client(args)
    t0 = time.time()
    rb.run_benchmark(
        client=client,
        image_folder=str(image_folder),
        output_csv=str(output_csv),
        test_limit=args.test_limit,
        models=[model],
        max_output_tokens=args.max_output_tokens,
        universal_temperature=args.temperature,
        resume=not args.no_resume,
    )
    elapsed = round(time.time() - t0, 1)

    row_count = validate_output_csv(rb, output_csv, args.model_name)
    print(f"Output CSV read-back OK with pandas: rows={row_count}")
    print(f"Probe complete in {elapsed}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
