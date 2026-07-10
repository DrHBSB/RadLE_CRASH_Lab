"""Hosted Meta Model API runner helpers for RadLE Colab notebooks.

This module keeps Muse Spark out of the default RadLE roster while letting a
collaborator-owned Meta Model API account run the normal benchmark pipeline.
It assumes an OpenAI-compatible hosted endpoint and delegates execution to
``radle_benchmark.run_benchmark``.
"""

from __future__ import annotations

import os
import pathlib

import pandas as pd

import radle_benchmark


MODEL_NAME = "muse_spark_1_1"
HIGH_REASONING_MODEL_NAME = "muse_spark_1_1_high"
MODEL_ID = "muse-spark-1.1"
DEFAULT_BASE_URL = "https://api.meta.ai/v1"
META_MAX_OUTPUT_TOKENS = 2048
META_PROVIDER_LABEL = "Meta Model API"


def get_secret(name: str, *fallback_env_names: str) -> str | None:
    """Read a secret from environment variables or Colab Secrets."""
    names = (name, *fallback_env_names)
    for env_name in names:
        value = os.environ.get(env_name)
        if value:
            return value

    try:
        from google.colab import userdata
    except Exception:
        return None

    for secret_name in names:
        try:
            value = userdata.get(secret_name)
        except Exception:
            value = None
        if value:
            return value
    return None


def configure_benchmark_runtime() -> None:
    """Patch in runtime-only compatibility for the hosted Meta endpoint."""
    radle_benchmark.NO_TEMPERATURE_MODELS.add(MODEL_ID)


def get_model_config() -> dict:
    """Return a radle_benchmark-compatible one-model config."""
    configure_benchmark_runtime()
    return {
        "name": MODEL_NAME,
        "id": MODEL_ID,
        "provider": "meta_model_api",
        "extra": None,
    }


def get_high_reasoning_model_config() -> dict:
    """Return a separate high-reasoning Muse Spark config for append runs."""
    configure_benchmark_runtime()
    return {
        "name": HIGH_REASONING_MODEL_NAME,
        "id": MODEL_ID,
        "provider": "meta_model_api",
        "extra": {"reasoning_effort": "high"},
    }


def make_openai_client(
    api_key: str | None = None,
    base_url: str | None = None,
):
    """Create an OpenAI SDK client pointed at the Meta Model API endpoint."""
    from openai import OpenAI

    resolved_key = api_key or get_secret("MODEL_API_KEY", "META_MODEL_API_KEY")
    if not resolved_key:
        raise RuntimeError(
            "Missing Meta Model API key. Add a Colab secret named MODEL_API_KEY "
            "or META_MODEL_API_KEY; do not paste the key into this notebook."
        )

    resolved_base_url = base_url or os.environ.get("META_MODEL_API_BASE_URL", DEFAULT_BASE_URL)
    return OpenAI(base_url=resolved_base_url, api_key=resolved_key)


def text_probe(client, model_id: str = MODEL_ID, max_tokens: int = 512) -> str:
    """Make a small text-only call to verify key, endpoint, and model access."""
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {
                "role": "user",
                "content": (
                    "Return exactly this JSON object and no extra text: "
                    '{"diagnosis":"probe_ok","likert_score":0}'
                ),
            }
        ],
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


def build_meta_run_paths(
    dataset_root,
    run_label: str = "meta_muse_spark_1case",
    run_id: str | None = None,
):
    """Build run paths scoped to the hosted Meta Muse Spark model."""
    safe_label = f"{MODEL_NAME}_{run_label}"
    return radle_benchmark.build_run_paths(
        dataset_root,
        run_label=safe_label,
        run_id=run_id,
    )


def stamp_meta_provider_columns(df, output_csv=None):
    """Stamp hosted Meta provider metadata without changing model answers."""
    provider_col = f"Provider_{MODEL_NAME}"
    if provider_col in df.columns:
        values = df[provider_col].fillna("").astype(str).str.strip()
        mask = values.isin(["", "UNKNOWN"])
        if mask.any():
            df.loc[mask, provider_col] = META_PROVIDER_LABEL

    if output_csv is not None:
        if hasattr(radle_benchmark, "atomic_to_csv"):
            radle_benchmark.atomic_to_csv(df, str(output_csv))
        else:
            df.to_csv(output_csv, index=False)
    return df


def run_meta_model_benchmark(
    client,
    image_folder,
    output_csv,
    test_limit: int | None = 1,
    backup_dir=None,
    resume: bool = True,
    max_output_tokens: int = META_MAX_OUTPUT_TOKENS,
    universal_temperature: float = radle_benchmark.UNIVERSAL_TEMPERATURE,
):
    """Run RadLE for Muse Spark through a hosted OpenAI-compatible endpoint."""
    configure_benchmark_runtime()
    model_config = get_model_config()
    df = radle_benchmark.run_benchmark(
        client=client,
        meta_client=client,
        image_folder=str(image_folder),
        output_csv=str(output_csv),
        test_limit=test_limit,
        models=[model_config],
        backup_dir=backup_dir,
        resume=resume,
        max_output_tokens=max_output_tokens,
        universal_temperature=universal_temperature,
    )
    return stamp_meta_provider_columns(df, output_csv=output_csv)


def count_existing_rows(output_csv) -> int:
    """Return the existing output row count, or zero when no CSV exists."""
    path = pathlib.Path(output_csv)
    if not path.exists():
        return 0
    df = pd.read_csv(path, dtype={"Master_Case_ID": str})
    return len(df)


def print_model_roster() -> None:
    """Print a compact non-secret roster summary for the notebook."""
    print(f"{MODEL_NAME}: {MODEL_ID} | provider={META_PROVIDER_LABEL}")
