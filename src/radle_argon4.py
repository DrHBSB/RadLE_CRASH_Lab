"""Separate Gemini 4 Argon admission; no reuse or mutation of the 16-arm run."""
import copy
import hashlib
import json
from pathlib import Path

MODEL_ID = 'google/gemini-4-argon'
CANONICAL_ID = 'google/gemini-4-argon-20261013'
RUN_LABEL = 'gemini_argon4_32k_20261016'
SOURCE_RUN = 'openrouter_16_32k_20261008'
OUTPUT_CAP = 32768
EXPECTED_CASES = 200
RETRY_AUTHORIZATION = dict(
    id='radle-argon4-two-repairs-20261016', max_pairs=200,
    attempts_per_pair=2, spacing_seconds=60,
    include_uncertain=False, include_quota=False, include_exhausted=True,
)
MODELS = [dict(
    name='gemini_4_argon', id=MODEL_ID, provider='openrouter',
    max_transport_attempts=1, omit_sampling=True,
    require_readable_reasoning=True, output_token_parameter='max_tokens',
    expected_provider='Google', expected_returned_model_ids=[MODEL_ID, CANONICAL_ID],
    extra=dict(reasoning=dict(effort='high', exclude=False),
               response_format=dict(type='json_object')),
    provider_routing=dict(only=['google-vertex/global'], allow_fallbacks=False,
                          require_parameters=True, data_collection='deny', zdr=True),
)]


def preflight(key, request_json):
    """Metadata only: verify exact version, route, privacy and reasoning ladder."""
    from radle_reasoning_ceiling import effort_profile
    api = 'https://openrouter.ai/api/v1'
    def get(path, authenticated=False):
        status, data = request_json(api + path, key if authenticated else None)
        if status != 200:
            raise RuntimeError(f'Argon preflight {path}: HTTP {status}')
        return data
    get('/key', True)
    catalog = get('/models')
    model = next((m for m in catalog['data'] if m['id'] == MODEL_ID), None)
    if not model or model.get('canonical_slug') != CANONICAL_ID:
        raise RuntimeError('Argon version changed; review admission before inference')
    profile = effort_profile(model.get('reasoning') or {})
    if profile['supported_efforts'] != ['high', 'medium', 'low']:
        raise RuntimeError('Argon reasoning ladder changed; review before inference')
    if not {'text', 'image'} <= set(model.get('architecture', {}).get('input_modalities', [])):
        raise RuntimeError('Argon text/image support missing')
    endpoints = get('/models/' + MODEL_ID + '/endpoints')['data']['endpoints']
    matches = [e for e in endpoints if e.get('tag') == 'google-vertex/global'
               and e.get('provider_name') == 'Google']
    if len(matches) != 1:
        raise RuntimeError('Argon exact Google route unavailable')
    endpoint = matches[0]
    required = {'reasoning', 'reasoning_effort', 'response_format', 'max_tokens'}
    if (endpoint.get('status') != 0 or int(endpoint.get('max_completion_tokens') or 0) < OUTPUT_CAP
            or not required <= set(endpoint.get('supported_parameters', []))):
        raise RuntimeError('Argon endpoint status, token cap or parameters changed')
    zdr = get('/endpoints/zdr', True)['data']
    if not any(e.get('model_id') == MODEL_ID and e.get('tag') == endpoint['tag']
               and e.get('name') == endpoint['name'] for e in zdr):
        raise RuntimeError('Argon Google route is not ZDR listed; do not relax privacy')
    return dict(id=MODEL_ID, canonical_id=CANONICAL_ID, endpoint=endpoint,
                reasoning_profile=profile, zdr_verified=True)


def prepare(rb, dataset_root, route):
    """Bind this new run to the original prompt/images without copying answers."""
    dataset_root = Path(dataset_root)
    source_path = dataset_root / 'Runs' / SOURCE_RUN / 'collection_contract.json'
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes)
    paths = rb.build_run_paths(dataset_root, run_label=RUN_LABEL, create_dirs=False)
    image_index = rb.build_image_index(paths['master_images_folder'])
    expected = {str(i) for i in range(1, EXPECTED_CASES + 1)}
    prompt_hash = hashlib.sha256(rb.PROMPT.encode()).hexdigest()
    images = {i: rb.rebuild_base_row(i, image_index[i])['Image_SHA256'] for i in sorted(image_index)}
    if (set(image_index) != expected or set(source.get('case_ids', [])) != expected
            or source.get('images') != images or source.get('prompt_sha256') != prompt_hash
            or source.get('output_cap') != OUTPUT_CAP):
        raise RuntimeError('Original cohort images, prompt or cap differ; refuse admission')
    contract = dict(models=copy.deepcopy(MODELS), prompt_sha256=prompt_hash, output_cap=OUTPUT_CAP,
                    release='codex/radle-argon4-colab-20261016', case_ids=sorted(expected), images=images,
                    source_contract_sha256=hashlib.sha256(source_bytes).hexdigest(),
                    ordinary_attempts=2, retry_authorization=RETRY_AUTHORIZATION)
    target = Path(paths['run_root']) / 'collection_contract.json'
    if target.exists():
        if json.loads(target.read_text()) != contract:
            raise RuntimeError('Existing Argon contract changed; do not reset history')
    else:
        if Path(paths['raw_results_csv']).exists() or Path(str(paths['raw_results_csv']) + '.concurrent').exists():
            raise RuntimeError('Argon output exists without admission contract; review before reuse')
        rb.build_run_paths(dataset_root, run_label=RUN_LABEL)
        with target.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(contract, indent=2) + '\n')
    # Timestamped metadata receipts preserve earlier route observations on resume.
    from datetime import datetime, timezone
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    (target.parent / ('route_preflight_' + stamp + '.json')).write_text(json.dumps(route, indent=2) + '\n')
    return paths
