from __future__ import annotations

import json
import py_compile
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# The medical helper installs lightweight provider stubs when optional SDKs are
# absent, allowing these runtime-contract tests to run without cloud clients.
import radle_medical_custom_runtime as medical_runtime
import radle_benchmark
import radle_meta_model_api_runtime as meta_runtime


EXPECTED_MODEL_NAMES = [
    "gpt_5_5",
    "gpt_5_6_sol_pro",
    "claude_4_8_opus",
    "claude_fable_5",
    "gemini_3_1_pro",
    "grok_4_3",
    "grok_4_5",
    "qwen_3_7_plus",
    "gemma_4_31b",
    "llama_4_maverick",
    "mistral_large_3_2512",
    "minimax_m3",
    "glm_5v_turbo",
    "nemotron_3_omni",
]


def model_by_name(name: str) -> dict:
    return next(model for model in radle_benchmark.MODELS if model["name"] == name)


def notebook_source(path: Path) -> str:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    chunks = []
    for cell in notebook.get("cells", []):
        source = cell.get("source", "")
        chunks.append("".join(source) if isinstance(source, list) else str(source))
    return "\n".join(chunks)


class RegistryAndRoutingTests(unittest.TestCase):
    def test_unified_fourteen_model_registry(self) -> None:
        self.assertEqual([model["name"] for model in radle_benchmark.MODELS], EXPECTED_MODEL_NAMES)
        self.assertEqual(len({model["id"] for model in radle_benchmark.MODELS}), 14)
        self.assertNotIn("grok_4_20", EXPECTED_MODEL_NAMES)
        self.assertNotIn("glm_4_6v", EXPECTED_MODEL_NAMES)

    def test_gpt_5_6_and_grok_4_5_provider_routes(self) -> None:
        cases = [
            (
                "gpt_5_6_sol_pro",
                {"reasoning": {"effort": "high"}},
                {"only": ["OpenAI"], "allow_fallbacks": False},
            ),
            (
                "grok_4_5",
                None,
                {"only": ["xAI"], "allow_fallbacks": False},
            ),
        ]
        openrouter_client = object()
        for name, reasoning, provider_route in cases:
            with self.subTest(model=name):
                model = model_by_name(name)
                params = radle_benchmark.build_api_params(model, [], 128, 0.01)
                self.assertEqual(params["extra_body"]["provider"], provider_route)
                if reasoning is not None:
                    self.assertEqual(params["extra_body"]["reasoning"], reasoning["reasoning"])
                self.assertIs(
                    radle_benchmark.get_api_client(model, openrouter_client, object()),
                    openrouter_client,
                )

    def test_claude_fable_output_config_omits_temperature(self) -> None:
        params = radle_benchmark.build_api_params(
            model_by_name("claude_fable_5"),
            [{"type": "text", "text": "probe"}],
            128,
            0.01,
        )
        self.assertEqual(params["output_config"], {"effort": "high"})
        self.assertNotIn("temperature", params)

    def test_native_and_meta_clients_are_selected_explicitly(self) -> None:
        openrouter_client = object()
        openai_client = object()
        meta_client = object()
        self.assertIs(
            radle_benchmark.get_api_client(
                model_by_name("gpt_5_5"),
                openrouter_client,
                openai_client,
            ),
            openai_client,
        )
        self.assertIs(
            radle_benchmark.get_api_client(
                meta_runtime.get_model_config(),
                openrouter_client,
                openai_client,
                meta_client=meta_client,
            ),
            meta_client,
        )
        with self.assertRaisesRegex(ValueError, "meta_client is required"):
            radle_benchmark.get_api_client(
                meta_runtime.get_model_config(),
                openrouter_client,
                openai_client,
            )


class ParserProtectionTests(unittest.TestCase):
    def test_closed_think_block_uses_only_final_answer(self) -> None:
        raw = (
            "<think>Findings are consistent with the rejected diagnosis.</think>"
            '{"diagnosis":"Pulmonary embolism","likert_score":3}'
        )
        self.assertEqual(radle_benchmark.extract_json_safely(raw), ("Pulmonary embolism", 3))

    def test_unclosed_think_block_is_parse_failure(self) -> None:
        raw = "<think>Findings are consistent with pulmonary embolism."
        self.assertEqual(
            radle_benchmark.extract_json_safely(raw),
            ("PARSE_FAILED", "PARSE_FAILED"),
        )

    def test_vqa_fallback_prefers_scored_non_abstention(self) -> None:
        raw = "1. I don't know: null\n2. Pulmonary tuberculosis: 3 (high confidence)</s>"
        self.assertEqual(
            radle_benchmark.extract_json_safely(raw),
            ("Pulmonary tuberculosis", 3),
        )

    def test_json_abstention_preserves_null_likert(self) -> None:
        raw = '{"diagnosis":"I don\'t know","likert_score":null}'
        self.assertEqual(radle_benchmark.extract_json_safely(raw), ("I don't know", None))

    def test_conservative_prose_accepts_commitment_only(self) -> None:
        self.assertEqual(
            radle_benchmark.extract_json_safely(
                "The findings are consistent with pulmonary embolism. High confidence."
            ),
            ("pulmonary embolism", 3),
        )
        for raw in (
            "This image demonstrates coronal computed tomography anatomy.",
            "The diagnosis is not provided in this case.",
        ):
            with self.subTest(raw=raw):
                self.assertEqual(
                    radle_benchmark.extract_json_safely(raw),
                    ("PARSE_FAILED", "PARSE_FAILED"),
                )


class MetaAndMedicalRuntimeTests(unittest.TestCase):
    def test_meta_provider_config_and_client_factory(self) -> None:
        config = meta_runtime.get_model_config()
        self.assertEqual(config["provider"], "meta_model_api")
        self.assertEqual(config["id"], "muse-spark-1.1")
        self.assertIn(config["id"], radle_benchmark.NO_TEMPERATURE_MODELS)

        captured = {}
        sentinel = object()
        fake_openai = types.ModuleType("openai")

        def fake_factory(**kwargs):
            captured.update(kwargs)
            return sentinel

        fake_openai.OpenAI = fake_factory
        with mock.patch.dict(sys.modules, {"openai": fake_openai}):
            client = meta_runtime.make_openai_client(
                api_key="test-key",
                base_url="https://meta.invalid/v1",
            )

        self.assertIs(client, sentinel)
        self.assertEqual(
            captured,
            {"base_url": "https://meta.invalid/v1", "api_key": "test-key"},
        )

    def test_llava_vllm_model_and_command_flags(self) -> None:
        model = medical_runtime.get_model("llava_med_mistral_7b")
        self.assertEqual(model.model_id, "chaoyinshe/llava-med-v1.5-mistral-7b-hf")
        self.assertEqual(model.preferred_engine, "vllm")
        self.assertEqual(model.benchmark_config()["extra"], {"min_tokens": 16})

        command = medical_runtime.build_vllm_command("llava_med_mistral_7b")
        expected_flags = {
            "--chat-template": str(medical_runtime.LLAVA_MED_MISTRAL_CHAT_TEMPLATE_PATH),
            "--chat-template-content-format": "openai",
            "--generation-config": "vllm",
        }
        for flag, expected_value in expected_flags.items():
            with self.subTest(flag=flag):
                self.assertEqual(command.count(flag), 1)
                self.assertEqual(command[command.index(flag) + 1], expected_value)
        self.assertTrue(medical_runtime.LLAVA_MED_MISTRAL_CHAT_TEMPLATE_PATH.is_file())
        self.assertNotIn("--bad-words", command)
        self.assertNotIn("--logit-bias", command)


class ArtifactValidationTests(unittest.TestCase):
    def test_runtime_modules_compile(self) -> None:
        module_paths = [
            SRC_ROOT / "radle_benchmark.py",
            SRC_ROOT / "radle_medical_custom_runtime.py",
            SRC_ROOT / "radle_meta_model_api_runtime.py",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            for module_path in module_paths:
                with self.subTest(module=module_path.name):
                    py_compile.compile(
                        str(module_path),
                        cfile=str(Path(temp_dir) / f"{module_path.stem}.pyc"),
                        doraise=True,
                    )

    def test_notebooks_are_valid_json_with_matching_runtime_contracts(self) -> None:
        append_path = REPO_ROOT / (
            "notebooks/RadLE_v1_5_Morning_Grok45_GPT56_MetaMuse_Append.ipynb"
        )
        meta_path = REPO_ROOT / "notebooks/RadLE_Meta_Muse_Spark_ColabPro.ipynb"

        append_source = notebook_source(append_path)
        meta_source = notebook_source(meta_path)
        self.assertIn("radle_meta_model_api_runtime.make_openai_client()", append_source)
        self.assertIn("meta_client=meta_client", append_source)
        self.assertIn(
            'EXPECTED_MODEL_NAMES = ["grok_4_5", "gpt_5_6_sol_pro", "muse_spark_1_1"]',
            append_source,
        )
        self.assertIn("meta_runtime.make_openai_client", meta_source)
        self.assertIn("meta_runtime.get_model_config()", meta_source)


if __name__ == "__main__":
    unittest.main()
