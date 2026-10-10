"""Fail-closed recovery from a CSV-bound checkpoint, retaining the original log."""
import csv
import hashlib
import json
import os
from pathlib import Path


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def repair_grants(original, manifest, journal, depth=0):
    """Reconstruct extra-attempt authority from archived durable events, never counts alone."""
    if depth > 16:
        raise ValueError('Recovery refused: archive chain too deep')
    lines = original.splitlines()
    from radle_job_queue import identity
    if not lines or identity(json.loads(lines[0])) != identity(manifest):
        raise ValueError('Recovery refused: archive identity mismatch')
    grants, results = {}, {}
    for number, line in enumerate(lines[1:], 2):
        try:
            event = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            continue
        kind = event.get('type')
        if kind == 'checkpoint_recovery':
            if number != 2:
                raise ValueError('Recovery refused: invalid prior snapshot position')
            archive = journal.with_name('events.original.' + event['original_sha256'] + '.jsonl')
            if sha(archive) != event['original_sha256']:
                raise ValueError('Recovery refused: prior archive hash mismatch')
            grants = repair_grants(archive.read_bytes(), manifest, journal, depth + 1)
            if set(event['states']) != set(manifest['jobs']):
                raise ValueError('Recovery refused: prior snapshot cohort mismatch')
            for key, state in event['states'].items():
                grant = grants.get(key, {})
                if (type(state['attempts']) is not int
                        or not manifest.get('initial_attempts', {}).get(key, 0) <= state['attempts'] <= grant.get('repair_attempt', manifest['max_attempts'])
                        or state['status'] not in {'pending', 'success', 'flagged', 'terminal', 'failed', 'uncertain', 'retry', 'quota', 'blocked', 'rejected'}
                        or any(state.get(field) != grant.get(field) for field in ('repair_attempt', 'repair_round'))):
                    raise ValueError('Recovery refused: invalid prior snapshot state')
                results[key] = dict(attempt=state['attempts'], status=state['status'], value=state.get('value', {}))
        elif kind == 'result':
            key = event['key']
            previous = results.get(key)
            if previous is None or event['attempt'] >= previous['attempt']:
                results[key] = event
        elif kind in {'repair_authorized', 'repair_round2_authorized'}:
            key, attempt = event['key'], event['attempt']
            prior = results.get(key)
            previous_grant = grants.get(key)
            if key not in manifest['jobs'] or type(attempt) is not int or attempt < 1:
                raise ValueError('Recovery refused: invalid repair grant')
            if kind == 'repair_authorized':
                valid = (previous_grant is None and prior is not None
                         and prior['status'] == 'terminal' and prior['attempt'] == attempt - 1
                         and attempt <= manifest['max_attempts'] + 1)
                round_number = 1
            else:
                valid = (previous_grant is not None and previous_grant['repair_round'] == 1
                         and previous_grant['repair_attempt'] == attempt - 1
                         and prior is not None and prior['attempt'] == attempt - 1
                         and prior['status'] == 'failed'
                         and prior['value'].get('repair_outcome') in {'terminal', 'retry'}
                         and not prior['value'].get('remote_outcome_unknown')
                         and event.get('authorization') == '20261010-user-round2')
                round_number = 2
            if not valid:
                raise ValueError('Recovery refused: unproven repair authorization')
            grants[key] = dict(repair_attempt=attempt, repair_round=round_number)
    return grants


def recover(queue, journal, manifest, output_csv, checkpoint_path):
    """Called under both collection and queue writer locks; never resets attempts."""
    original = journal.read_bytes()
    lines = original.splitlines()
    if not lines or queue.identity(json.loads(lines[0])) != queue.identity(manifest):
        raise ValueError('Recovery refused: run identity changed')
    checkpoint_bytes = Path(checkpoint_path).read_bytes()
    checkpoint = json.loads(checkpoint_bytes)
    if sha(output_csv) != checkpoint['csv_sha256']:
        raise ValueError('Recovery refused: checkpoint CSV hash mismatch')
    saved = checkpoint['states']
    if set(saved) != set(manifest['jobs']):
        raise ValueError('Recovery refused: checkpoint cohort mismatch')
    states = {}
    grants = repair_grants(original, manifest, journal)
    for key, item in saved.items():
        attempt = item['attempts']
        inherited = manifest.get('initial_attempts', {}).get(key, 0)
        limit = grants.get(key, {}).get('repair_attempt', manifest['max_attempts'])
        if (type(attempt) is not int or not inherited <= attempt <= limit
                or item['status'] not in queue.STATUSES | {'pending'}):
            raise ValueError('Recovery refused: invalid checkpoint state')
        states[key] = dict(item, ready_at=0, value={})
        if key in grants:
            states[key].update(grants[key])
    invalid = []
    latest = {}
    for number, line in enumerate(lines[1:], 2):
        try:
            event = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            invalid.append(number)
            continue
        kind = event.get('type')
        if kind == 'checkpoint_recovery':
            # A recovered log can itself suffer a later interrupted Drive write.
            # Validate its original receipt rather than treating it as a new call.
            if number != 2:
                raise ValueError('Recovery refused: invalid prior snapshot position')
            archive = journal.with_name('events.original.' + event['original_sha256'] + '.jsonl')
            if sha(archive) != event['original_sha256']:
                raise ValueError('Recovery refused: prior archive hash mismatch')
            prior_states = event['states']
            if set(prior_states) != set(states):
                raise ValueError('Recovery refused: prior snapshot cohort mismatch')
            for key, prior in prior_states.items():
                attempt = prior['attempts']
                inherited = manifest.get('initial_attempts', {}).get(key, 0)
                if (type(attempt) is not int
                        or not inherited <= attempt <= states[key]['attempts']
                        or prior['status'] not in queue.STATUSES | {'pending'}):
                    raise ValueError('Recovery refused: invalid prior snapshot state')
                latest[key] = dict(attempt=attempt, status=prior['status'],
                                   value=prior.get('value', {}), snapshot=True)
            continue
        if kind in {'code_version', 'repair_authorized', 'repair_round2_authorized'}:
            continue
        if kind not in {'start', 'result'}:
            raise ValueError('Recovery refused: unsupported journal event')
        key = event['key']
        if key not in states or type(event['attempt']) is not int or event['attempt'] > states[key]['attempts']:
            raise ValueError('Recovery refused: journal exceeds checkpoint attempts')
        if kind == 'result':
            if event['status'] not in queue.STATUSES:
                raise ValueError('Recovery refused: invalid journal status')
            previous = latest.get(key)
            if previous and previous.get('snapshot') and event['attempt'] == previous['attempt']:
                if (previous['status'] not in {'pending', 'uncertain'}
                        and (event['status'] != previous['status'] or event['value'] != previous['value'])):
                    raise ValueError('Recovery refused: conflicting snapshot result')
                latest[key] = event
                continue
            if previous is None or event['attempt'] > previous['attempt']:
                latest[key] = event
            elif event['attempt'] == previous['attempt'] and event != previous:
                raise ValueError('Recovery refused: conflicting results')
    for key, event in latest.items():
        state = states[key]
        if event['attempt'] == state['attempts']:
            if event['status'] != state['status']:
                raise ValueError('Recovery refused: journal/checkpoint status conflict')
            state['value'] = event['value']
    for key, state in states.items():
        if state['status'] == 'failed' and not state['value'].get('repair_outcome'):
            # Missing outcome evidence must never qualify for another paid repair.
            state['value'] = dict(state['value'], repair_outcome='uncertain', remote_outcome_unknown=True)
    # CSV is authoritative for saved fields only after its exact hash matches.
    # Long reasoning traces can exceed the standard library's 128 KiB default.
    csv.field_size_limit(2**31 - 1)
    with Path(output_csv).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if 'Master_Case_ID' not in (reader.fieldnames or []):
            raise ValueError('Recovery refused: missing case ID')
        rows = {}
        for row in reader:
            case = row['Master_Case_ID']
            if case in rows:
                raise ValueError('Recovery refused: duplicate case ID')
            rows[case] = row
    for key, state in states.items():
        case, model = json.loads(key)
        if case not in rows:
            raise ValueError('Recovery refused: missing case')
        fields = {k: v for k, v in rows[case].items() if k.endswith('_' + model)}
        if state['status'] in {'success', 'flagged'}:
            if not fields.get('Diagnosis_' + model) or not fields.get('Raw_Response_' + model):
                raise ValueError('Recovery refused: saved answer fields missing')
        # Preserve prior fields even for failed/retry jobs, as normal replay does.
        if fields:
            state['value'] = dict(state['value'], fields=fields)
    digest = hashlib.sha256(original).hexdigest()
    archive = journal.with_name('events.original.' + digest + '.jsonl')
    if archive.exists():
        if sha(archive) != digest:
            raise ValueError('Recovery refused: archive mismatch')
    else:
        with archive.open('xb') as handle:
            handle.write(original)
            handle.flush()
            os.fsync(handle.fileno())
    if sha(archive) != digest:
        raise ValueError('Recovery refused: archive verification failed')
    receipt = {'type': 'checkpoint_recovery', 'original_sha256': digest,
               'checkpoint_sha256': hashlib.sha256(checkpoint_bytes).hexdigest(),
               'csv_sha256': checkpoint['csv_sha256'], 'invalid_lines': invalid,
               'states': states}
    candidate = journal.with_name('events.recovery.candidate.jsonl')
    data = (queue.encode(manifest) + '\n' + queue.encode(receipt) + '\n').encode()
    with candidate.open('wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    if queue.replay(candidate, manifest) != states:
        raise ValueError('Recovery refused: replay verification failed')
    if (sha(journal) != digest or Path(checkpoint_path).read_bytes() != checkpoint_bytes
            or sha(output_csv) != checkpoint['csv_sha256']):
        raise ValueError('Recovery refused: files changed during recovery')
    os.replace(candidate, journal)
    if journal.read_bytes() != data:
        raise ValueError('Recovery replacement verification failed; original archive retained')
    print('RECOVERED: CSV-bound checkpoint; original journal archived; attempts unchanged.', flush=True)
    return states
