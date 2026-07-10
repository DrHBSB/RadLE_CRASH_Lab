"""Experimental medical-model runner for a Colab custom runtime.

This module keeps the official RadLE roster unchanged. It defines a small
medical/open model roster and helpers for serving one selected model through a
local OpenAI-compatible endpoint, then delegates benchmark execution to
radle_benchmark.run_benchmark.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time
import types
import urllib.error
import urllib.request
from dataclasses import dataclass
from types import SimpleNamespace

import importlib.util


def _install_optional_provider_stubs() -> None:
    """Allow local dry-run imports when native provider SDKs are absent."""
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


_install_optional_provider_stubs()
import radle_benchmark


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_BASE_URL = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/v1"
DEFAULT_CACHE_ROOT = "/content/radle_runtime_cache"
MEDICAL_MAX_OUTPUT_TOKENS = 2048


def _path_is_writable(path: pathlib.Path) -> bool:
    """Return True when path exists and a small temp file can be written."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".radle_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def detect_runtime_root(env_var: str = "RADLE_RUNTIME_ROOT") -> pathlib.Path:
    """Choose a writable runtime root for Colab, Workbench, or local runs."""
    override = os.environ.get(env_var)
    if override:
        root = pathlib.Path(override).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        return root

    candidates = [pathlib.Path("/content"), pathlib.Path.home(), pathlib.Path.cwd()]
    for candidate in candidates:
        if candidate.exists() and _path_is_writable(candidate):
            return candidate

    raise RuntimeError(
        f"Could not find a writable runtime root. Set {env_var} to a writable path."
    )


def get_secret(name: str, *fallback_env_names: str) -> str | None:
    """Read a secret from environment variables or Colab Secrets when available."""
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


def is_colab_enterprise() -> bool:
    """Return True when the notebook is running in Colab Enterprise."""
    return os.environ.get("VERTEX_PRODUCT") == "COLAB_ENTERPRISE"


def is_standard_colab() -> bool:
    """Return True when standard Colab APIs appear available."""
    if is_colab_enterprise():
        return False
    try:
        import google.colab  # noqa: F401
        return True
    except Exception:
        return False


@dataclass(frozen=True)
class MedicalRuntimeModel:
    """Configuration for one experimental medical/open VLM."""

    name: str
    model_id: str
    preferred_engine: str
    requires_hf_token: bool = False
    needs_trust_remote_code: bool = True
    default_max_model_len: int = 8192
    default_gpu_memory_utilization: float = 0.9
    request_extra_body: dict | None = None
    notes: str = ""

    def benchmark_config(self) -> dict:
        """Return the explicit model config consumed by radle_benchmark."""
        return {
            "name": self.name,
            "id": self.model_id,
            "extra": self.request_extra_body,
        }


MEDICAL_CUSTOM_RUNTIME_MODELS = [
    MedicalRuntimeModel(
        name="medgemma_1_5_4b",
        model_id="google/medgemma-1.5-4b-it",
        preferred_engine="vllm",
        requires_hf_token=True,
        notes="Gated Google medical model; accept HF terms and set HF_TOKEN.",
    ),
    MedicalRuntimeModel(
        name="llava_med_mistral_7b",
        model_id="chaoyinshe/llava-med-v1.5-mistral-7b-hf",
        preferred_engine="vllm",
        # min_tokens=16 ONLY. Evidence: with NO extra_body, IMAGE cases emit EOS
        # immediately (completion_tokens=1, empty), while text-only probes generate
        # fine -- this checkpoint EOS-terminates on multimodal input at the first
        # token. min_tokens forces it past that, after which it decodes a real
        # diagnosis and stops on its own (case 156 -> 21 tokens). The other former
        # guards were harmful: logit_bias blocked newlines (-> "1. 1. 1." collapse)
        # and bad_words blocked EOS (-> whitespace loop). Neither is used now.
        request_extra_body={"min_tokens": 16},
        notes=(
            "HF-format LLaVA-Med Mistral 7B checkpoint for vLLM; "
            "do not route the original Microsoft checkpoint through vLLM by config relabeling."
        ),
    ),
    MedicalRuntimeModel(
        name="internvl3_5_8b",
        model_id="OpenGVLab/InternVL3_5-8B",
        preferred_engine="vllm",
        notes="Strong open general VLM control; not medical-specific.",
    ),
    MedicalRuntimeModel(
        name="octomed_7b",
        model_id="OctoMed/OctoMed-7B",
        preferred_engine="vllm",
        default_gpu_memory_utilization=0.8,
        notes="Qwen2.5-VL-based open medical multimodal reasoning model.",
    ),
]


MODEL_BY_NAME = {model.name: model for model in MEDICAL_CUSTOM_RUNTIME_MODELS}
LLAVA_MED_MISTRAL_CHAT_TEMPLATE_PATH = (
    pathlib.Path(__file__).parent
    / "templates"
    / "llava_med_mistral_vllm_chat_template.jinja"
)


def _extend_args_if_missing(args: list[str], additions: list[str]) -> list[str]:
    """Append CLI flag/value pairs unless the flag is already present."""
    merged = list(args)
    for idx in range(0, len(additions), 2):
        flag = additions[idx]
        value = additions[idx + 1]
        if flag not in merged:
            merged.extend([flag, value])
    return merged


def configure_cache_environment(cache_root: str = DEFAULT_CACHE_ROOT) -> dict:
    """Route model and package caches to a large writable runtime disk."""
    cache_root_path = pathlib.Path(cache_root)
    paths = {
        "HF_HOME": cache_root_path / "huggingface",
        "HUGGINGFACE_HUB_CACHE": cache_root_path / "huggingface" / "hub",
        "TRANSFORMERS_CACHE": cache_root_path / "huggingface" / "transformers",
        "PIP_CACHE_DIR": cache_root_path / "pip",
        "VLLM_CACHE_ROOT": cache_root_path / "vllm",
        "XDG_CACHE_HOME": cache_root_path / "xdg",
    }
    for key, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(path)
    return {key: str(path) for key, path in paths.items()}


def print_runtime_resources() -> None:
    """Print compact GPU and disk diagnostics in Colab/custom runtimes."""
    print("Python:", sys.version.split()[0])
    df_targets = ["/"]
    if pathlib.Path("/content").exists():
        df_targets.append("/content")

    for command in (
        ["nvidia-smi"],
        ["df", "-h", *df_targets],
    ):
        try:
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            print(f"\n$ {' '.join(command)}")
            if result.stdout.strip():
                print(result.stdout)
            if result.stderr.strip():
                print(result.stderr)
        except FileNotFoundError:
            print(f"Command not found: {' '.join(command)}")


def read_log_tail(path, lines: int = 80) -> str:
    """Return the last lines of a text log for failed server startup debugging."""
    path = pathlib.Path(path)
    if not path.exists():
        return f"Log file not found: {path}"
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])


def list_model_names() -> list[str]:
    """Return supported experimental medical model names."""
    return [model.name for model in MEDICAL_CUSTOM_RUNTIME_MODELS]


def get_model(model_name: str) -> MedicalRuntimeModel:
    """Return one model config by friendly name."""
    try:
        return MODEL_BY_NAME[model_name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown medical model {model_name!r}. "
            f"Choose one of: {list_model_names()}"
        ) from exc


def get_model_config(model_name: str) -> dict:
    """Return the radle_benchmark-compatible config for one medical model."""
    return get_model(model_name).benchmark_config()


def build_medical_run_paths(
    dataset_root,
    model_name: str,
    run_label: str = "medical_test_1_case",
    run_id: str | None = None,
):
    """Build Drive/local run paths scoped to a selected medical model."""
    safe_label = f"{model_name}_{run_label}"
    return radle_benchmark.build_run_paths(
        dataset_root,
        run_label=safe_label,
        run_id=run_id,
    )


def _env_with_hf_token(hf_token: str | None = None) -> dict:
    env = os.environ.copy()
    token = hf_token or env.get("HF_TOKEN") or env.get("HUGGING_FACE_HUB_TOKEN")
    if token:
        env["HF_TOKEN"] = token
        env["HUGGING_FACE_HUB_TOKEN"] = token

    # Cloud Assist L4/G2 NCCL Stability Fixes
    env.setdefault("NCCL_P2P_DISABLE", "1")
    env.setdefault("NCCL_IB_DISABLE", "1")
    env.setdefault("NCCL_DEBUG", "WARN")

    return env


def verify_vllm_importable() -> None:
    """Fail fast when the installed vLLM wheel does not match the runtime CUDA libs."""
    command = [
        sys.executable,
        "-c",
        (
            "from vllm.platforms import current_platform; "
            "import vllm; "
            "print('vLLM import OK:', vllm.__version__, vllm.__file__, current_platform)"
        ),
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        details = "\n".join(
            part
            for part in (result.stdout.strip(), result.stderr.strip())
            if part
        )
        raise RuntimeError(
            "vLLM failed to import before server startup. This usually means the "
            "installed vLLM wheel does not match the Colab CUDA runtime. Rerun the "
            "dependency cell so it uninstalls stale vLLM and installs the explicit "
            "CUDA-12.9 wheel, then retry.\n\n"
            f"{details}"
        )


def patch_vllm_rotary_flash_attn_fallback() -> None:
    """Patch vLLM's optional FlashAttention rotary import to use native fallback."""
    patch_code = r"""
import importlib.util
from pathlib import Path

spec = importlib.util.find_spec("vllm.model_executor.layers.rotary_embedding.common")
if spec is None or spec.origin is None:
    raise SystemExit("Could not locate vLLM rotary common.py")

path = Path(spec.origin)
text = path.read_text(encoding="utf-8")
needle = "\n".join([
    "        self.apply_rotary_emb_flash_attn = None",
    "        if not current_platform.is_cpu() and find_spec(\"flash_attn\") is not None:",
    "            from flash_attn.ops.triton.rotary import apply_rotary",
    "",
    "            self.apply_rotary_emb_flash_attn = apply_rotary",
    "",
])
replacement = "\n".join([
    "        self.apply_rotary_emb_flash_attn = None",
    "        if not current_platform.is_cpu() and find_spec(\"flash_attn\") is not None:",
    "            try:",
    "                from flash_attn.ops.triton.rotary import apply_rotary",
    "            except ModuleNotFoundError as exc:",
    "                if exc.name is None or not exc.name.startswith(\"flash_attn\"):",
    "                    raise",
    "                apply_rotary = None",
    "",
    "            if apply_rotary is not None:",
    "                self.apply_rotary_emb_flash_attn = apply_rotary",
    "",
])

if "except ModuleNotFoundError as exc:" in text:
    print("vLLM rotary optional flash_attn patch already present:", path)
elif needle in text:
    path.write_text(text.replace(needle, replacement, 1), encoding="utf-8")
    print("Patched vLLM rotary optional flash_attn fallback:", path)
else:
    raise SystemExit("Expected vLLM rotary flash_attn block not found in " + str(path))

for pyc_path in path.parent.joinpath("__pycache__").glob("common*.pyc"):
    pyc_path.unlink(missing_ok=True)
"""
    print("Preflight vLLM rotary optional flash_attn fallback patch...")
    result = subprocess.run(
        [sys.executable, "-c", patch_code],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    if result.returncode != 0:
        raise RuntimeError(
            "Failed to patch vLLM rotary optional flash_attn fallback before "
            "server startup."
        )


def build_vllm_command(
    model_name: str,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    tensor_parallel_size: int = 1,
    gpu_memory_utilization: float | None = None,
    max_model_len: int | None = None,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build a vLLM OpenAI-compatible server command for one model."""
    model = get_model(model_name)
    command = [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--host",
        host,
        "--port",
        str(port),
        "--model",
        model.model_id,
        "--served-model-name",
        model.model_id,
        "--tensor-parallel-size",
        str(tensor_parallel_size),
        "--gpu-memory-utilization",
        str(gpu_memory_utilization or model.default_gpu_memory_utilization),
        "--max-model-len",
        str(max_model_len or model.default_max_model_len),
    ]
    if model.needs_trust_remote_code:
        command.append("--trust-remote-code")
    if extra_args:
        command.extend(extra_args)
    if model.name == "llava_med_mistral_7b":
        command = _extend_args_if_missing(
            command,
            [
                "--chat-template",
                str(LLAVA_MED_MISTRAL_CHAT_TEMPLATE_PATH),
                "--chat-template-content-format",
                "openai",
                "--generation-config",
                "vllm",
            ],
        )
    return command


def build_sglang_command(
    model_name: str,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    tp_size: int = 1,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build an SGLang OpenAI-compatible server command for one model."""
    model = get_model(model_name)
    command = [
        sys.executable,
        "-m",
        "sglang.launch_server",
        "--host",
        host,
        "--port",
        str(port),
        "--model-path",
        model.model_id,
        "--tensor-parallel-size",
        str(tp_size),
    ]
    if model.needs_trust_remote_code:
        command.append("--trust-remote-code")
    if extra_args:
        command.extend(extra_args)
    return command


def start_model_server(
    model_name: str,
    engine: str = "vllm",
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    hf_token: str | None = None,
    tensor_parallel_size: int = 1,
    gpu_memory_utilization: float | None = None,
    max_model_len: int | None = None,
    extra_args: list[str] | None = None,
    log_path: str | os.PathLike | None = None,
):
    """Start a local OpenAI-compatible server for one selected model."""
    model = get_model(model_name)
    if model.requires_hf_token and not (
        hf_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    ):
        raise RuntimeError(
            f"{model_name} requires Hugging Face access. Accept the model terms "
            "and set a Colab secret named HF_TOKEN before starting the server."
        )

    if engine == "vllm":
        verify_vllm_importable()
        patch_vllm_rotary_flash_attn_fallback()
        command = build_vllm_command(
            model_name=model_name,
            host=host,
            port=port,
            tensor_parallel_size=tensor_parallel_size,
            gpu_memory_utilization=gpu_memory_utilization,
            max_model_len=max_model_len,
            extra_args=extra_args,
        )
    elif engine == "sglang":
        command = build_sglang_command(
            model_name=model_name,
            host=host,
            port=port,
            tp_size=tensor_parallel_size,
            extra_args=extra_args,
        )
    else:
        raise ValueError("engine must be 'vllm' or 'sglang'.")

    stdout = subprocess.PIPE
    stderr = subprocess.STDOUT
    log_handle = None
    if log_path:
        log_path = pathlib.Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = open(log_path, "w", encoding="utf-8")
        print("$ " + " ".join(command), file=log_handle, flush=True)
        stdout = log_handle
        stderr = subprocess.STDOUT

    process = subprocess.Popen(
        command,
        env=_env_with_hf_token(hf_token),
        stdout=stdout,
        stderr=stderr,
        text=True,
    )
    process._radle_log_handle = log_handle  # type: ignore[attr-defined]
    return process


def stop_model_server(process, timeout_seconds: float = 30.0) -> None:
    """Terminate a server process started by start_model_server."""
    if process is None:
        return
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout_seconds)
    log_handle = getattr(process, "_radle_log_handle", None)
    if log_handle is not None:
        log_handle.close()


def wait_for_openai_server(
    base_url: str = DEFAULT_BASE_URL,
    timeout_seconds: float = 900.0,
    poll_seconds: float = 5.0,
    process=None,
    log_path: str | os.PathLike | None = None,
    log_tail_lines: int = 120,
) -> dict:
    """Wait until an OpenAI-compatible /models endpoint responds."""
    deadline = time.time() + timeout_seconds
    models_url = base_url.rstrip("/") + "/models"
    last_error = ""

    while time.time() < deadline:
        if process is not None and process.poll() is not None:
            log_tail = read_log_tail(log_path, lines=log_tail_lines) if log_path else ""
            raise RuntimeError(
                "OpenAI-compatible server exited before readiness "
                f"with code {process.returncode}.\n"
                f"Last server log lines:\n{log_tail}"
            )
        try:
            with urllib.request.urlopen(models_url, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
            print(f"Endpoint ready: {models_url}")
            return payload
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(poll_seconds)

    raise TimeoutError(
        f"OpenAI-compatible endpoint did not become ready at {models_url}. "
        f"Last error: {last_error}"
    )


def make_openai_client(base_url: str = DEFAULT_BASE_URL, api_key: str = "EMPTY") -> OpenAI:
    """Create an OpenAI SDK client for a local or hosted compatible endpoint."""
    from openai import OpenAI

    return OpenAI(base_url=base_url, api_key=api_key or "EMPTY")


class DryRunOpenAICompatibleClient:
    """Small fake client for local schema validation without model downloads."""

    def __init__(self, model_id: str):
        self.model_id = model_id
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self.create_completion)
        )

    def create_completion(self, **kwargs):
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
            model=kwargs.get("model", self.model_id),
            model_extra={"provider": "DRY_RUN_FAKE"},
        )


def make_dry_run_client(model_name: str):
    """Create a fake OpenAI-compatible client for one model."""
    return DryRunOpenAICompatibleClient(get_model(model_name).model_id)


def validate_output_csv(output_csv, model_name: str) -> int:
    """Validate that a single-model output CSV has the expected RadLE columns."""
    output_csv = pathlib.Path(output_csv)
    df = radle_benchmark.pd.read_csv(output_csv, dtype={"Master_Case_ID": str})
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
        f"OpenRouter_Response_Model_{model_name}",
        f"Usage_JSON_{model_name}",
        f"Raw_Response_{model_name}",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Output CSV missing required columns: {missing}")
    return len(df)


def run_medical_model_benchmark(
    client,
    model_name: str,
    image_folder,
    output_csv,
    test_limit: int | None = 1,
    backup_dir=None,
    resume: bool = True,
    max_output_tokens: int = MEDICAL_MAX_OUTPUT_TOKENS,
    universal_temperature: float = radle_benchmark.UNIVERSAL_TEMPERATURE,
):
    """Run RadLE for one experimental medical model through a compatible endpoint."""
    model_config = get_model_config(model_name)
    return radle_benchmark.run_benchmark(
        client=client,
        image_folder=str(image_folder),
        output_csv=str(output_csv),
        test_limit=test_limit,
        models=[model_config],
        backup_dir=backup_dir,
        resume=resume,
        max_output_tokens=max_output_tokens,
        universal_temperature=universal_temperature,
    )


def print_model_roster() -> None:
    """Print a compact non-secret roster summary for notebooks."""
    for model in MEDICAL_CUSTOM_RUNTIME_MODELS:
        gated = "yes" if model.requires_hf_token else "no"
        print(
            f"{model.name}: {model.model_id} | "
            f"engine={model.preferred_engine} | gated={gated}"
        )
