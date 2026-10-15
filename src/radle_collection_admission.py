"""Roster-driven Morning collection admission; preserve prior results and request history."""
import copy
import hashlib
import json
from pathlib import Path
import urllib.request
import urllib.error


def load_config(path):
    from radle_retry_policy import validate
    config = json.loads(Path(path).read_text(encoding='utf-8'))
    names = [model['name'] for model in config['models']]
    if not names or len(set(names)) != len(names):
        raise ValueError('Roster must contain unique model names')
    for key in ('parent_run', 'run_label'):
        if Path(config[key]).name != config[key] or config[key] in {'.', '..'}:
            raise ValueError('Run labels must be single directory names')
    if config['parent_run'] == config['run_label']:
        raise ValueError('Admission must preserve its parent run')
    if (type(config['expected_cases']) is not int or config['expected_cases'] < 1
            or config['ordinary_attempts'] != 2 or config['output_cap'] < 1
            or config['concurrency'] != 1):
        raise ValueError('Invalid collection bounds')
    validate(config['retry_authorization'])
    return config


def added_models(config, parent_models):
    """Derive work from roster difference, never from a model-specific switch."""
    roster = {model['name']: model for model in config['models']}
    parent = {model['name']: model for model in parent_models}
    if len(parent) != len(parent_models) or not set(parent) <= set(roster):
        raise RuntimeError('Roster removed or duplicated an inherited model')
    if any(roster[name] != model for name, model in parent.items()):
        raise RuntimeError('Inherited model settings changed; replacement needs explicit admission')
    new = [copy.deepcopy(model) for model in config['models'] if model['name'] not in parent]
    if not new:
        raise RuntimeError('Roster has no new models to admit')
    if config['retry_authorization']['max_pairs'] != config['expected_cases'] * len(new):
        raise RuntimeError('Retry pair bound must match the newly admitted roster')
    return new


def request_json(url, key=None):
    headers = {'Accept': 'application/json'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=40) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, {}  # Do not echo request headers or arbitrary provider error bodies.


def preflight(config, models, key, request=request_json):
    """Check the selected roster's public capabilities and authenticated privacy metadata."""
    from radle_reasoning_ceiling import effort_profile
    api = 'https://openrouter.ai/api/v1'
    def get(path, authenticated=False):
        status, data = request(api + path, key if authenticated else None)
        if status != 200:
            raise RuntimeError(f'Metadata preflight {path}: HTTP {status}')
        return data
    get('/key', True)
    catalog = {model['id']: model for model in get('/models')['data']}
    zdr = get('/endpoints/zdr', True)['data']
    receipts = []
    for selected in models:
        model_id = selected['id']
        capability = config['capabilities'][model_id]
        live = catalog.get(model_id)
        if not live or live.get('canonical_slug') != capability['canonical_id']:
            raise RuntimeError(f'{model_id}: version changed; review before inference')
        profile = effort_profile(live.get('reasoning') or {})
        if profile['supported_efforts'] != capability['reasoning_efforts']:
            raise RuntimeError(f'{model_id}: reasoning ladder changed')
        reasoning = selected.get('extra', {}).get('reasoning', {})
        if (reasoning.get('exclude') is not False
                or (profile['controllable'] and reasoning.get('effort') != profile['initial_effort'])
                or (not profile['controllable'] and reasoning.get('enabled') is not True)):
            raise RuntimeError(f'{model_id}: highest enabled readable reasoning is required')
        if not {'text', 'image'} <= set(live.get('architecture', {}).get('input_modalities', [])):
            raise RuntimeError(f'{model_id}: text/image support missing')
        routing = selected['provider_routing']
        if (len(routing['only']) != 1 or routing.get('allow_fallbacks') is not False
                or routing.get('require_parameters') is not True or routing.get('data_collection') != 'deny'):
            raise RuntimeError(f'{model_id}: routing/privacy contract is not explicit')
        endpoints = get('/models/' + model_id + '/endpoints')['data']['endpoints']
        matches = [endpoint for endpoint in endpoints if endpoint.get('tag') == routing['only'][0]
                   and endpoint.get('provider_name') == selected['expected_provider']]
        if len(matches) != 1:
            raise RuntimeError(f'{model_id}: exact provider route unavailable')
        endpoint = matches[0]
        required = {'reasoning', 'response_format', selected['output_token_parameter']}
        if profile['controllable']:
            required.add('reasoning_effort')
        if (endpoint.get('status') != 0
                or int(endpoint.get('max_completion_tokens') or 0) < config['output_cap']
                or not required <= set(endpoint.get('supported_parameters', []))):
            raise RuntimeError(f'{model_id}: endpoint status, output cap or parameters changed')
        listed = any(row.get('model_id') == model_id and row.get('tag') == endpoint['tag']
                     and row.get('name') == endpoint['name'] for row in zdr)
        if routing.get('zdr') and not listed:
            raise RuntimeError(f'{model_id}: pinned route is not ZDR listed')
        receipts.append(dict(id=model_id, canonical_id=capability['canonical_id'], endpoint=endpoint,
                             reasoning_profile=profile, zdr_verified=listed))
    return receipts


def prepare(rb, dataset_root, config, request=request_json, key=None):
    """Validate the parent, derive new work and seed one combined experiment version."""
    import shutil
    dataset_root = Path(dataset_root)
    for label in config.get('incompatible_runs', []):
        obsolete = dataset_root / 'Runs' / label / 'raw/results.csv'
        if obsolete.exists() or Path(str(obsolete) + '.concurrent').exists():
            raise RuntimeError('A superseded run has data; reconcile its attempts before admission')
    source_root = dataset_root / 'Runs' / config['parent_run']
    source_path = source_root / 'collection_contract.json'
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes)
    new_models = added_models(config, source['models'])
    routes = preflight(config, new_models, key, request)
    paths = rb.build_run_paths(dataset_root, run_label=config['run_label'], create_dirs=False)
    image_index = rb.build_image_index(paths['master_images_folder'])
    expected = {str(i) for i in range(1, config['expected_cases'] + 1)}
    prompt_hash = hashlib.sha256(rb.PROMPT.encode()).hexdigest()
    images = {i: rb.rebuild_base_row(i, image_index[i])['Image_SHA256'] for i in sorted(image_index)}
    if (set(image_index) != expected or set(source.get('case_ids', [])) != expected
            or source.get('images') != images or source.get('prompt_sha256') != prompt_hash
            or source.get('output_cap') != config['output_cap']):
        raise RuntimeError('Inherited cases, images, prompt or output cap differ')
    cohort = copy.deepcopy(config['models'])
    contract = dict(models=cohort, prompt_sha256=prompt_hash, output_cap=config['output_cap'],
                    release=config['contract_release'], case_ids=sorted(expected), images=images,
                    source_contract_sha256=hashlib.sha256(source_bytes).hexdigest(),
                    collection_models=[model['name'] for model in new_models],
                    ordinary_attempts=config['ordinary_attempts'], retry_authorization=config['retry_authorization'])
    target = Path(paths['run_root']) / 'collection_contract.json'
    receipt_path = target.parent / 'cohort_admission.json'
    output = Path(paths['raw_results_csv'])
    source_csv = source_root / 'raw/results.csv'
    source_folder = Path(str(source_csv) + '.concurrent')
    source_files = dict(results=source_csv, journal=source_folder / 'queue/events.jsonl',
                        checkpoint=source_folder / 'checkpoint.json', contract=source_path)
    parent_receipt = source_root / 'cohort_admission.json'
    if parent_receipt.exists():
        source_files['admission'] = parent_receipt
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
        audit = rb.audit_saved_collection(source_csv, source['models'], config['expected_cases'], config['output_cap'])
        if before != hashes():
            raise RuntimeError('Parent changed during admission audit')
        if set(audit['final_df']['Master_Case_ID'].astype(str)) != expected:
            raise RuntimeError('Parent CSV cases differ')
        if any(column.endswith('_' + model['name']) for column in audit['final_df'].columns for model in new_models):
            raise RuntimeError('New model columns already exist in parent; review before reuse')
        lineage = json.loads(parent_receipt.read_text()) if parent_receipt.exists() else {}
        unresolved = lineage.get('inherited_unresolved', []) + audit['unresolved_pairs']
        inventory = lineage.get('inherited_failure_inventory', []) + rb.make_json_safe(audit['failure_inventory'].to_dict('records'))
        if len({(row['Master_Case_ID'], row['model']) for row in unresolved}) != len(unresolved):
            raise RuntimeError('Inherited outcome lineage overlaps current journal states')
        receipt = dict(source_run=config['parent_run'], source_hashes=before,
                       source_paths={name: str(path) for name, path in source_files.items()},
                       inherited_unresolved=unresolved, inherited_failure_inventory=inventory,
                       collection_models=[model['name'] for model in new_models], inherited_model_count=len(source['models']),
                       policy='Preserve all old values and evidence; no old-model dispatch or retry grants')
        rb.build_run_paths(dataset_root, run_label=config['run_label'])
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
    (target.parent / ('route_preflight_' + stamp + '.json')).write_text(json.dumps(routes, indent=2) + '\n')
    return paths, cohort, new_models, receipt


def combined_audit(rb, paths, cohort, receipt, config):
    """Audit the full roster and prove every old column still equals the frozen parent."""
    import pandas as pd
    source = Path(paths['run_root']) / 'admission_source/results.csv'
    if hashlib.sha256(source.read_bytes()).hexdigest() != receipt['source_hashes']['results']:
        raise RuntimeError('Frozen parent CSV changed')
    parent = pd.read_csv(source, dtype=str, keep_default_na=False).set_index('Master_Case_ID')
    final = pd.read_csv(paths['raw_results_csv'], dtype=str, keep_default_na=False).set_index('Master_Case_ID')
    if set(parent.index) != set(final.index) or not set(parent.columns) <= set(final.columns):
        raise RuntimeError('Inherited case/column set changed')
    if not parent.equals(final.loc[parent.index, parent.columns]):
        raise RuntimeError('Inherited model values changed')
    audit = rb.audit_benchmark_output(paths['raw_results_csv'], models=cohort,
        expected_case_ids=range(1, config['expected_cases'] + 1), max_output_tokens=config['output_cap'])
    return audit
