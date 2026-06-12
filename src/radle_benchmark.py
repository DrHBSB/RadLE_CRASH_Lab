import base64
import hashlib
import json
import os
import pathlib
import re
import time
from collections import defaultdict
from datetime import datetime, timezone

import pandas as pd


MAX_OUTPUT_TOKENS = 16384
UNIVERSAL_TEMPERATURE = 0.01
EXCLUDED_IMAGE_EXTENSIONS = {".txt", ".csv", ".json", ".docx", ".zip"}

NO_TEMPERATURE_MODELS = {
    "gpt-5.5",
    "anthropic/claude-opus-4.7",
}

MODELS = [
    {
        "name": "gpt_5_5",
        "id": "gpt-5.5",
        "provider": "openai",
        "extra": {"reasoning_effort": "high"},
    },
    {
        "name": "claude_4_7_opus",
        "id": "anthropic/claude-opus-4.7",
        "extra": {
            "reasoning": {"enabled": True},
            "verbosity": "max",
        },
    },
    {
        "name": "gemini_3_1_pro",
        "id": "google/gemini-3.1-pro-preview",
        "extra": {"reasoning": {"effort": "high"}},
    },
    {
        "name": "grok_4_20",
        "id": "x-ai/grok-4.20",
        "extra": {"reasoning": {"effort": "xhigh"}},
    },
    {
        "name": "qwen_vl_max",
        "id": "qwen/qwen-vl-max",
        "extra": None,
    },
    {
        "name": "gemma_4_31b",
        "id": "google/gemma-4-31b-it",
        "extra": {"reasoning": {"enabled": True}},
    },
    {
        "name": "llama_4_maverick",
        "id": "meta-llama/llama-4-maverick",
        "extra": None,
    },
    {
        "name": "pixtral_large",
        "id": "mistralai/pixtral-large-2411",
        "extra": None,
    },
    {
        "name": "glm_4_6v",
        "id": "z-ai/glm-4.6v",
        "extra": {"reasoning": {"enabled": True}},
    },
    {
        "name": "nemotron_3_omni",
        "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "extra": {"reasoning": {"enabled": True}},
    },
]

PROMPT = """
System prompt:

You are a board-certified diagnostic radiologist. Given a medical image, provide the single most specific final diagnosis.

Rules:
	1.	If you can identify a diagnosis, return it. If you truly cannot, return “I don’t know”.
	2.	No abbreviations, use full words only.
	3.	No verbose descriptions of the diagnosis.
	4.	Use the following Likert confidence scale (only when a diagnosis is given) to tell how confident you are in your diagnosis:
	∙	0 = very low confidence (essentially a guess)
	∙	1 = low confidence (weak leading diagnosis, several alternatives similarly plausible)
	∙	2 = moderate confidence (one diagnosis favored, important alternatives remain)
	∙	3 = high confidence (one diagnosis clearly favored, alternatives unlikely)
	∙	4 = very high confidence (classic appearance, essentially certain)
5. If you return “I don’t know”, then return Likert score as “null”.

Final output format:  Respond with this JSON:

{"diagnosis": "<diagnosis in full words or I don't know>", "likert_score": <0-4 or null>}


Example outputs:

{"diagnosis": "Pulmonary tuberculosis", "likert_score": 3}

{"diagnosis": "Von Hippel-Lindau syndrome", "likert_score": 4}

{"diagnosis": "I don't know", "likert_score": null}
""".strip()


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_mime_type(path):
    with open(path, "rb") as image_file:
        header = image_file.read(8)

    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8"):
        return "image/jpeg"
    return "image/jpeg"


def extract_json_safely(raw_text):
    """Extract diagnosis JSON while ignoring Markdown fences or reasoning text."""
    clean_text = re.sub(r"```json", "", raw_text, flags=re.IGNORECASE)
    clean_text = re.sub(r"```", "", clean_text)

    match = re.search(r"\{.*\}", clean_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            data_lower = {k.lower(): v for k, v in data.items()}
            diag = data_lower.get("diagnosis", "JSON_MISSING_KEY")
            likert = data_lower.get("likert_score", data_lower.get("likert", "NULL"))
            return diag, likert
        except json.JSONDecodeError:
            pass

    return "PARSE_FAILED", "PARSE_FAILED"


def make_json_safe(obj):
    """Convert OpenAI/Pydantic-style objects into JSON-safe structures."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return make_json_safe(obj.model_dump())
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_json_safe(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def is_grok_xhigh_rejection(model, error_text):
    """Detect likely rejection of reasoning.effort='xhigh' on base Grok 4.20."""
    text = str(error_text).lower()
    return (
        model["name"] == "grok_4_20"
        and "error code: 400" in text
        and (
            "reasoning" in text
            or "effort" in text
            or "unsupported" in text
            or "parameter" in text
        )
    )


def uses_native_openai(model):
    """Return True for models that should bypass OpenRouter."""
    return model.get("provider") == "openai"


def build_api_params(model, content_array, max_output_tokens, universal_temperature):
    """Build provider-specific Chat Completions params for one model request."""
    if uses_native_openai(model):
        api_params = {
            "model": model["id"],
            "messages": [{"role": "user", "content": content_array}],
            "max_completion_tokens": max_output_tokens,
        }

        extra = model.get("extra") or {}
        if extra.get("reasoning_effort"):
            api_params["reasoning_effort"] = extra["reasoning_effort"]

        return api_params

    api_params = {
        "model": model["id"],
        "messages": [{"role": "user", "content": content_array}],
        "max_tokens": max_output_tokens,
    }

    if model["id"] not in NO_TEMPERATURE_MODELS:
        api_params["temperature"] = universal_temperature

    if model.get("extra"):
        api_params["extra_body"] = model.get("extra")

    return api_params


def get_api_client(model, client, openai_client):
    """Select the native OpenAI client only for models explicitly routed there."""
    if uses_native_openai(model):
        if openai_client is None:
            raise ValueError("openai_client is required for native OpenAI models.")
        return openai_client
    return client


def run_benchmark(
    client,
    image_folder,
    output_csv,
    test_limit=None,
    models=None,
    prompt=PROMPT,
    max_output_tokens=MAX_OUTPUT_TOKENS,
    universal_temperature=UNIVERSAL_TEMPERATURE,
    openai_client=None,
):
    """Run the RadLE benchmark against images under image_folder and save CSV output."""
    models = models or MODELS
    image_paths = [
        str(p)
        for p in pathlib.Path(image_folder).rglob("*")
        if p.is_file() and p.suffix.lower() not in EXCLUDED_IMAGE_EXTENSIONS
    ]

    grouped = defaultdict(list)
    for path in image_paths:
        base_key = os.path.basename(path).split(".")[0]
        grouped[base_key].append(path)

    items = list(grouped.items())
    items.sort(key=lambda x: int(x[0]) if x[0].isdigit() else x[0])

    if test_limit:
        print(f"TEST MODE: Running on first {test_limit} cases only.")
        items = items[:test_limit]

    results = []
    print(f"Processing {len(items)} unique cases across {len(models)} models...\n")

    for idx, (case_id, paths) in enumerate(items, 1):
        print(f"[{idx}/{len(items)}] Case ID: {case_id} ({len(paths)} images)")

        row = {
            "Master_Case_ID": case_id,
            "Associated_Images": ", ".join(os.path.basename(p) for p in paths),
            "Image_SHA256": ", ".join(
                hashlib.sha256(open(p, "rb").read()).hexdigest()[:16] for p in paths
            ),
        }

        content_array = [{"type": "text", "text": prompt}]
        paths.sort()
        for path in paths:
            content_array.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{get_mime_type(path)};base64,{encode_image(path)}"
                    },
                }
            )

        for model in models:
            print(f"  -> {model['name']}...", end="")
            api_params = None
            grok_fallback_used = False

            try:
                api_params = build_api_params(
                    model,
                    content_array,
                    max_output_tokens,
                    universal_temperature,
                )
                api_client = get_api_client(model, client, openai_client)

                max_retries = 3
                response = None
                last_error = "Unknown error occurred before execution"

                for attempt in range(max_retries):
                    try:
                        t0 = time.time()
                        response = api_client.chat.completions.create(**api_params)
                        latency = round(time.time() - t0, 1)
                        break
                    except Exception as exc:
                        last_error = str(exc)

                        if is_grok_xhigh_rejection(model, last_error) and not grok_fallback_used:
                            print(
                                "\n    Grok xhigh rejected; "
                                "falling back to reasoning.enabled=True..."
                            )
                            api_params["extra_body"] = {"reasoning": {"enabled": True}}
                            grok_fallback_used = True
                            response = None
                            continue

                        fatal_patterns = [
                            "error code: 404",
                            "error code: 400",
                            "balance",
                            "quota",
                            "insufficient_quota",
                        ]

                        if any(pattern in last_error.lower() for pattern in fatal_patterns):
                            print(f"\n    FATAL ERROR (No Retry): {last_error[:100]}...")
                            break

                        if attempt < max_retries - 1:
                            delay = 5 * (2**attempt)
                            print(
                                f" \n    Attempt {attempt + 1} failed, "
                                f"retrying in {delay}s..."
                            )
                            time.sleep(delay)

                if response is None:
                    raise Exception(last_error)

                msg = response.choices[0].message
                raw_answer = msg.content.strip() if getattr(msg, "content", None) else ""
                diag, likert = extract_json_safely(raw_answer)

                raw_reasoning_text = ""
                raw_reasoning = getattr(msg, "reasoning", None)

                if raw_reasoning is not None:
                    raw_reasoning_text = str(raw_reasoning).strip()
                elif hasattr(msg, "model_extra") and msg.model_extra and "reasoning" in msg.model_extra:
                    ext_reasoning = msg.model_extra["reasoning"]
                    if ext_reasoning is not None:
                        raw_reasoning_text = str(ext_reasoning).strip()

                reasoning_details_obj = getattr(msg, "reasoning_details", None)

                if reasoning_details_obj is None and hasattr(msg, "model_extra") and msg.model_extra:
                    reasoning_details_obj = msg.model_extra.get("reasoning_details")

                reasoning_details_text = ""
                if reasoning_details_obj:
                    reasoning_details_text = json.dumps(
                        make_json_safe(reasoning_details_obj),
                        ensure_ascii=False,
                    )

                if raw_reasoning_text and reasoning_details_text:
                    thoughts = (
                        raw_reasoning_text
                        + "\n\n[reasoning_details]\n"
                        + reasoning_details_text
                    )
                elif reasoning_details_text:
                    thoughts = reasoning_details_text
                else:
                    thoughts = raw_reasoning_text

                reasoning_tokens = 0
                completion_tokens = 0
                prompt_tokens = 0

                if hasattr(response, "usage") and response.usage:
                    usage = response.usage
                    completion_tokens = getattr(usage, "completion_tokens", 0)
                    prompt_tokens = getattr(usage, "prompt_tokens", 0)

                    if hasattr(usage, "completion_tokens_details") and usage.completion_tokens_details:
                        details = usage.completion_tokens_details
                        if hasattr(details, "reasoning_tokens"):
                            reasoning_tokens = details.reasoning_tokens
                        elif isinstance(details, dict):
                            reasoning_tokens = details.get("reasoning_tokens", 0)
                        elif hasattr(details, "__dict__"):
                            reasoning_tokens = vars(details).get("reasoning_tokens", 0)

                provider_used = "OpenAI" if uses_native_openai(model) else "UNKNOWN"
                if (
                    not uses_native_openai(model)
                    and hasattr(response, "model_extra")
                    and response.model_extra
                ):
                    provider_used = response.model_extra.get("provider", "UNKNOWN")

                row[f"Diagnosis_{model['name']}"] = diag
                row[f"Likert_{model['name']}"] = likert
                row[f"Prompt_Tokens_{model['name']}"] = prompt_tokens
                row[f"Total_Tokens_Out_{model['name']}"] = completion_tokens
                row[f"Reasoning_Tokens_{model['name']}"] = reasoning_tokens
                row[f"Latency_{model['name']}"] = latency
                row[f"Provider_{model['name']}"] = provider_used
                row[f"Timestamp_UTC_{model['name']}"] = datetime.now(timezone.utc).isoformat()
                row[f"Reasoning_{model['name']}"] = thoughts
                row[f"Reasoning_Raw_{model['name']}"] = raw_reasoning_text
                row[f"Reasoning_Details_{model['name']}"] = reasoning_details_text
                row[f"Actual_Request_Extra_{model['name']}"] = json.dumps(
                    api_params.get("extra_body", None),
                    ensure_ascii=False,
                )
                row[f"Grok_Fallback_Used_{model['name']}"] = (
                    grok_fallback_used if model["name"] == "grok_4_20" else ""
                )
                row[f"OpenRouter_Response_Model_{model['name']}"] = getattr(
                    response, "model", ""
                )
                row[f"Usage_JSON_{model['name']}"] = json.dumps(
                    make_json_safe(getattr(response, "usage", None)),
                    ensure_ascii=False,
                )
                row[f"Raw_Response_{model['name']}"] = raw_answer[:2000]

                tps = round(completion_tokens / latency, 1) if latency > 0 else 0
                print(
                    f" OK ({latency}s | {completion_tokens} out / "
                    f"{prompt_tokens} in | {tps} tok/sec)"
                )

            except Exception as exc:
                full_error = str(exc)
                print(f" Failed! API Response: {full_error}")
                row[f"Diagnosis_{model['name']}"] = "API_ERROR"
                row[f"Likert_{model['name']}"] = "ERROR"
                row[f"Prompt_Tokens_{model['name']}"] = 0
                row[f"Total_Tokens_Out_{model['name']}"] = 0
                row[f"Reasoning_Tokens_{model['name']}"] = 0
                row[f"Latency_{model['name']}"] = 0
                row[f"Provider_{model['name']}"] = "ERROR"
                row[f"Timestamp_UTC_{model['name']}"] = datetime.now(timezone.utc).isoformat()
                row[f"Reasoning_{model['name']}"] = full_error
                row[f"Reasoning_Raw_{model['name']}"] = ""
                row[f"Reasoning_Details_{model['name']}"] = ""
                row[f"Actual_Request_Extra_{model['name']}"] = json.dumps(
                    api_params.get("extra_body", None) if api_params else None,
                    ensure_ascii=False,
                )
                row[f"Grok_Fallback_Used_{model['name']}"] = (
                    grok_fallback_used if model["name"] == "grok_4_20" else ""
                )
                row[f"OpenRouter_Response_Model_{model['name']}"] = ""
                row[f"Usage_JSON_{model['name']}"] = ""
                row[f"Raw_Response_{model['name']}"] = full_error[:2000]

        results.append(row)

        if idx % 5 == 0:
            pd.DataFrame(results).to_csv(
                output_csv.replace(".csv", "_BACKUP.csv"),
                index=False,
            )

    df = pd.DataFrame(results)
    df.to_csv(output_csv, index=False)
    print(f"\nComplete! Data saved to {output_csv}")
    return df


def create_scorer_view(raw_csv):
    """Create the human-friendly scorer CSV and transposed display dataframe."""
    scorer_csv = raw_csv.replace(".csv", "_SCORER_VIEW.csv")

    if not os.path.exists(raw_csv):
        raise FileNotFoundError(f"Raw CSV not found: {raw_csv}")

    df = pd.read_csv(raw_csv)
    cols = df.columns.tolist()
    id_cols = ["Master_Case_ID", "Associated_Images"]
    diag_cols = [c for c in cols if "Diagnosis_" in c]
    likert_cols = [c for c in cols if "Likert_" in c]

    df_scorer = df[id_cols + diag_cols + likert_cols]
    df_scorer.to_csv(scorer_csv, index=False)

    display_df = df_scorer.set_index("Master_Case_ID").T
    return df_scorer, display_df, scorer_csv
