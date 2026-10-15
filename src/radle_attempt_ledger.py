"""Read-only event ledger. A scheduler start is a reservation, not proof of HTTP."""
import json
from pathlib import Path


def read_ledger(journal, manifest):
    from radle_job_queue import identity, resolve_event, encode
    from radle_journal_recovery import sha
    from radle_error_evidence import evidence_record
    records, seen = [], set()

    def visit(path, depth=0):
        if depth > 16:
            raise ValueError('Ledger archive chain too deep')
        digest = sha(path)
        if digest in seen:
            return
        seen.add(digest)
        with Path(path).open('rb') as stream:
            if identity(json.loads(next(stream))) != identity(manifest):
                raise ValueError('Ledger archive identity mismatch')
            for line_number, line in enumerate(stream, 2):
                source = dict(source_sha256=digest, source_line=line_number)
                try:
                    event = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    records.append(dict(source, event='malformed_line', observation='Unparseable archived bytes; no request outcome inferred.'))
                    continue
                if event.get('type') == 'checkpoint_recovery':
                    archive = Path(journal).with_name('events.original.' + event['original_sha256'] + '.jsonl')
                    if sha(archive) != event['original_sha256']:
                        raise ValueError('Ledger archive hash mismatch')
                    visit(archive, depth + 1)
                    records.append(dict(source, event='checkpoint_snapshot', observation='Recovered state; not an independent provider response.'))
                    continue
                event = resolve_event(event, path)
                kind = event.get('type')
                if 'key' not in event:
                    continue
                if event['key'] not in manifest['jobs']:
                    raise ValueError('Ledger event outside original cohort')
                case, model = json.loads(event['key'])
                row = dict(source, case=case, model=model, event=kind,
                           event_attempt=event.get('attempt'), remote_execution_proven=False)
                if kind == 'result':
                    row.update(evidence_record(event['key'], dict(status=event['status'],
                               attempts=event['attempt'], value=event['value']),
                               max_output_tokens=(event['value'].get('attempt_history') or {}).get(
                                   'max_output_tokens', (manifest.get('contract') or {}).get('max_output_tokens', 32768))))
                    row['reasoning_retry'] = (event['value'].get('attempt_history') or {}).get('reasoning_retry')
                    row['response_received_recorded'] = bool(event['value'].get('response_received'))
                elif kind == 'start':
                    row['observation'] = 'Scheduler reserved attempt before submitting worker; HTTP delivery not established.'
                elif kind and (kind.startswith('repair_') or kind == 'retry_pass_authorized'):
                    row['observation'] = 'Durable permission for an additional attempt; not proof of dispatch.'
                records.append(row)
    visit(Path(journal))
    # A response can be durably archived even if the following journal append
    # was interrupted. Include these receipts rather than inferring a resend.
    from radle_attempt_artifacts import read_verified
    for path in sorted((Path(journal).parent.parent / 'attempt_artifacts').glob('*.json')):
        pieces = path.name.split('.')
        if len(pieces) != 4 or pieces[-1] != 'json':
            raise ValueError('Unrecognized private attempt artifact name')
        digest = pieces[-2]
        artifact = read_verified({'path':str(path),'sha256':digest})
        ident = artifact['identity']
        key = encode([ident['case'], ident['model']])
        if key not in manifest['jobs']:
            raise ValueError('Attempt artifact outside original cohort')
        row = dict(source_sha256=digest, case=ident['case'], model=ident['model'],
                            event='artifact_' + artifact['stage'],
                            event_attempt=ident['journal_attempt'], attempt_id=ident['attempt_id'],
                            request_sha256=ident['request_sha256'], remote_execution_proven=False,
                            response_received_recorded=artifact['stage'] == 'response_received',
                            observation='Verified private stage receipt; inspect lineage before authorizing another call.')
        if artifact['stage'] == 'prepared':
            row['reasoning_retry'] = artifact['payload'].get('reasoning_retry')
        elif artifact['stage'] == 'response_received':
            from radle_attempt_artifacts import response_metadata
            row.update(response_metadata(artifact['payload']))
            row.update(response_attempt=ident['journal_attempt'],
                       configured_output_cap=(manifest.get('contract') or {}).get('max_output_tokens', 32768),
                       response_evidence_source='verified_response_artifact')
        records.append(row)
    return records
