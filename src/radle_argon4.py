"""Admit Gemini 4 Argon into the existing Morning experiment, preserving prior columns."""
import copy
import hashlib
import json
from pathlib import Path

MODEL_ID = 'google/gemini-4-argon'
CANONICAL_ID = 'google/gemini-4-argon-20261013'
RUN_LABEL = 'openrouter_17_32k_20261016'
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
    """Carry the complete 16-arm wide dataset forward; collect only the new arm."""
    import shutil
    dataset_root = Path(dataset_root)
    obsolete = dataset_root / 'Runs/gemini_argon4_32k_20261016/raw/results.csv'
    if obsolete.exists() or Path(str(obsolete) + '.concurrent').exists():
        raise RuntimeError('Superseded Argon-only run has data; reconcile its attempts before admission')
    source_root = dataset_root / 'Runs' / SOURCE_RUN
    source_path = source_root / 'collection_contract.json'
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes)
    paths = rb.build_run_paths(dataset_root, run_label=RUN_LABEL, create_dirs=False)
    image_index = rb.build_image_index(paths['master_images_folder'])
    expected = {str(i) for i in range(1, EXPECTED_CASES + 1)}
    prompt_hash = hashlib.sha256(rb.PROMPT.encode()).hexdigest()
    images = {i: rb.rebuild_base_row(i, image_index[i])['Image_SHA256'] for i in sorted(image_index)}
    old_models = source.get('models', [])
    if (set(image_index) != expected or set(source.get('case_ids', [])) != expected
            or source.get('images') != images or source.get('prompt_sha256') != prompt_hash
            or source.get('output_cap') != OUTPUT_CAP or len(old_models) != 16
            or len({m['name'] for m in old_models}) != 16
            or any(m['name'] == MODELS[0]['name'] for m in old_models)):
        raise RuntimeError('Original cohort images, prompt, models or cap differ; refuse admission')
    cohort = copy.deepcopy(old_models + MODELS)
    contract = dict(models=cohort, prompt_sha256=prompt_hash, output_cap=OUTPUT_CAP,
                    release='codex/radle-17-argon4-20261016', case_ids=sorted(expected), images=images,
                    source_contract_sha256=hashlib.sha256(source_bytes).hexdigest(),
                    collection_models=[MODELS[0]['name']], ordinary_attempts=2,
                    retry_authorization=RETRY_AUTHORIZATION)
    target = Path(paths['run_root']) / 'collection_contract.json'
    receipt_path = target.parent / 'cohort_admission.json'
    output = Path(paths['raw_results_csv'])
    source_csv = source_root / 'raw/results.csv'
    source_folder = Path(str(source_csv) + '.concurrent')
    source_files = dict(results=source_csv, journal=source_folder / 'queue/events.jsonl',
                        checkpoint=source_folder / 'checkpoint.json', contract=source_path)
    def hashes():
        return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in source_files.items()}
    if target.exists():
        if json.loads(target.read_text()) != contract or not receipt_path.exists():
            raise RuntimeError('Existing expanded cohort contract/receipt differs; do not reset history')
        receipt = json.loads(receipt_path.read_text())
        if receipt['source_hashes'] != hashes() or not output.exists():
            raise RuntimeError('Frozen parent experiment changed or expanded output missing')
    else:
        if output.exists() or Path(str(output) + '.concurrent').exists() or receipt_path.exists():
            raise RuntimeError('Incomplete cohort admission; review before reinitializing')
        before = hashes()
        # This validates the CSV-bound journal/checkpoint without changing parent bytes.
        audit = rb.audit_saved_collection(source_csv, old_models, EXPECTED_CASES, OUTPUT_CAP)
        if before != hashes():
            raise RuntimeError('Parent changed during admission audit')
        if set(audit['final_df']['Master_Case_ID'].astype(str)) != expected:
            raise RuntimeError('Parent CSV cases differ')
        if any(column.endswith('_' + MODELS[0]['name']) for column in audit['final_df'].columns):
            raise RuntimeError('Argon already exists in parent; do not initialize a duplicate arm')
        receipt = dict(source_run=SOURCE_RUN, source_hashes=before,
                       source_paths={name: str(path) for name, path in source_files.items()},
                       inherited_unresolved=audit['unresolved_pairs'],
                       inherited_failure_inventory=rb.make_json_safe(audit['failure_inventory'].to_dict('records')),
                       collection_models=[MODELS[0]['name']], inherited_model_count=16,
                       policy='Preserve all old values and evidence; no old-model dispatch or retry grants')
        rb.build_run_paths(dataset_root, run_label=RUN_LABEL)
        archive = target.parent / 'admission_source'
        archive.mkdir(exist_ok=False)
        # CSV is copied byte-for-byte. Full historical journals/artifacts remain at hash-pinned paths.
        for name in ('results', 'contract', 'checkpoint'):
            shutil.copyfile(source_files[name], archive / source_files[name].name)
        shutil.copyfile(source_csv, output)
        if hashlib.sha256(output.read_bytes()).hexdigest() != before['results'] or before != hashes():
            raise RuntimeError('Source/copy changed during cohort admission')
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
        with target.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(contract, indent=2) + '\n')
    from datetime import datetime, timezone
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    (target.parent / ('route_preflight_' + stamp + '.json')).write_text(json.dumps(route, indent=2) + '\n')
    return paths, cohort, receipt


def combined_audit(rb, paths, cohort, receipt):
    """Audit all 17 arms and prove every old column still equals the frozen parent."""
    import pandas as pd
    source = Path(paths['run_root']) / 'admission_source/results.csv'
    if hashlib.sha256(source.read_bytes()).hexdigest() != receipt['source_hashes']['results']:
        raise RuntimeError('Frozen parent CSV changed')
    parent = pd.read_csv(source, dtype=str, keep_default_na=False).set_index('Master_Case_ID')
    final = pd.read_csv(paths['raw_results_csv'], dtype=str, keep_default_na=False).set_index('Master_Case_ID')
    if set(parent.index) != set(final.index) or not set(parent.columns) <= set(final.columns):
        raise RuntimeError('Inherited case/column set changed')
    if not parent.equals(final.loc[parent.index, parent.columns]):
        raise RuntimeError('Inherited 16-model values changed')
    audit = rb.audit_benchmark_output(paths['raw_results_csv'], models=cohort,
        expected_case_ids=range(1, EXPECTED_CASES + 1), max_output_tokens=OUTPUT_CAP)
    return audit
