"""Private snapshot of saved collection, with explicit failures and flags; no inference."""
import hashlib
import json
import math
from pathlib import Path
from datetime import datetime, timezone


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe(v) for v in value]
    return value


def finalize(rb, admission, paths, cohort, receipt, config):
    """Validate saved evidence and freeze private results without asserting a clean gate."""
    import pandas as pd
    root = Path(paths['run_root'])
    source = Path(paths['raw_results_csv'])
    folder = Path(str(source) + '.concurrent')
    if not source.exists():
        raise RuntimeError('Private finalization requires an existing saved collection')
    names = {m['name'] for m in cohort}
    new = [m for m in cohort if m['name'] in receipt['collection_models']]
    if not new:
        raise RuntimeError('Missing admitted collection models')
    evidence = dict(receipt['source_paths'])
    evidence.update(current_results=str(source), current_contract=str(root/'collection_contract.json'),
        current_admission=str(root/'cohort_admission.json'),
        current_checkpoint=str(folder/'checkpoint.json'), current_journal=str(folder/'queue/events.jsonl'))
    def hashes():
        return {k: _hash(p) for k, p in evidence.items()}
    def unlocked():
        roots = {folder}
        for key, path in receipt['source_paths'].items():
            if key == 'journal':
                roots.add(Path(path).parent.parent)
        if any((r/'writer.lock').exists() or (r/'queue/writer.lock').exists() for r in roots):
            raise RuntimeError('Private finalization refused while a writer lock exists')
    unlocked()
    before = hashes()
    if any(before[k] != v for k, v in receipt['source_hashes'].items()):
        raise RuntimeError('Frozen parent evidence changed')
    current = rb.audit_saved_collection(source, new, config['expected_cases'], config['output_cap'])
    audit = admission.combined_audit(rb, paths, cohort, receipt, config)
    table = audit['audit'].copy()
    expected_cases = {str(i) for i in range(1, config['expected_cases'] + 1)}
    table['Master_Case_ID'] = table['Master_Case_ID'].astype(str)
    keys = list(zip(table['Master_Case_ID'], table['model']))
    expected_keys = {(c, m) for c in expected_cases for m in names}
    if len(keys) != len(set(keys)) or set(keys) != expected_keys:
        raise RuntimeError('Private final outcome grid differs from the configured cohort')
    unresolved = receipt['inherited_unresolved'] + current.get('unresolved_pairs', [])
    failed = {(str(p['Master_Case_ID']), p['model']): p for p in unresolved}
    if len(failed) != len(unresolved):
        raise RuntimeError('Overlapping unresolved evidence')
    non_answers = {k for k, bucket in zip(keys, table['bucket']) if bucket not in {'accepted', 'analysis_flag'}}
    if set(failed) != non_answers:
        raise RuntimeError('Unresolved evidence and saved-answer audit disagree')
    inventory = receipt['inherited_failure_inventory'] + current.get('failure_inventory', pd.DataFrame()).to_dict('records')
    evidence_rows = {(str(p.get('case', p.get('Master_Case_ID'))), p['model']): p for p in inventory}
    if len(evidence_rows) != len(inventory) or set(evidence_rows) != set(failed):
        raise RuntimeError('Failure evidence inventory differs from unresolved pairs')
    table['final_status'] = ['failed' if k in failed else ('analysis_flag' if b == 'analysis_flag' else 'accepted')
                             for k, b in zip(keys, table['bucket'])]
    table['scheduler_status'] = [failed[k]['status'] if k in failed else '' for k in keys]
    table['journal_attempts'] = [failed[k]['attempts'] if k in failed else None for k in keys]
    table['failure_classification'] = [evidence_rows[k].get('classification', '') if k in failed else '' for k in keys]
    # Raw values and original audit statuses remain unchanged; final_status is a disposition.
    columns = ['Master_Case_ID', 'model', 'final_status', 'bucket', 'status', 'reason',
               'scheduler_status', 'journal_attempts', 'failure_classification']
    outcomes = table[columns]
    flags = table[table['final_status'].eq('analysis_flag')]
    counts = {k: int(table['final_status'].eq(k).sum()) for k in ('accepted', 'analysis_flag', 'failed')}
    source_bytes = source.read_bytes()
    payloads = {
        Path(paths['final_results_csv']).name: source_bytes,
        'RadLE_v2_final_outcomes.csv': outcomes.to_csv(index=False).encode('utf-8'),
        'RadLE_v2_analysis_flags.csv': flags.to_csv(index=False).encode('utf-8'),
        'RadLE_v2_failure_evidence.json': (json.dumps(_safe(rb.make_json_safe(inventory)), indent=2, allow_nan=False)+'\n').encode('utf-8'),
    }
    files = {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()}
    manifest = dict(schema=1, run_id=config['run_label'], status='finalized_private_with_dispositions',
        source_csv=str(source), final_csv=str(paths['final_results_csv']), sha256=_hash(source),
        rows=config['expected_cases'], columns=len(current['final_df'].columns), models=len(cohort),
        expected_case_model_cells=len(expected_keys), outcome_counts=counts,
        clean_publication_gate_passed=False, public_export_performed=False, inference_calls=0,
        source_evidence_hashes=before, artifacts=files,
        failure_policy='Unresolved pairs have final_status=failed; original scheduler status and evidence retained',
        reasoning_policy='Saved reasoning flags retained without replacement requests')
    unlocked()
    if hashes() != before or hashlib.sha256(source_bytes).hexdigest() != before['current_results']:
        raise RuntimeError('Source evidence changed during private finalization')
    destination = Path(paths['final_results_csv']).parent
    manifest_path = Path(paths['final_manifest_json'])
    if manifest_path.parent != destination:
        raise RuntimeError('Final manifest and artifacts must share the final directory')
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding='utf-8'))
        comparable = {k: v for k, v in previous.items() if k != 'created_utc'}
        if comparable != manifest or any(not (destination/n).is_file() or _hash(destination/n) != sha for n, sha in files.items()):
            raise RuntimeError('Existing private final snapshot differs; refuse overwrite')
        return previous
    if any((destination/n).exists() for n in files):
        raise RuntimeError('Partial or conflicting private final snapshot exists; preserve and review')
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in payloads.items():
        with (destination/name).open('xb') as stream:
            stream.write(data)
        if _hash(destination/name) != files[name]:
            raise RuntimeError('Private final artifact verification failed')
    unlocked()
    if hashes() != before:
        raise RuntimeError('Source changed before final manifest; partial artifacts preserved')
    manifest['created_utc'] = datetime.now(timezone.utc).isoformat()
    with manifest_path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(manifest, indent=2, allow_nan=False)+'\n')
    return manifest
