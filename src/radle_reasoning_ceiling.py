"""Per-pair reasoning reductions after distinct, evidenced output-ceiling hits."""
import copy
import hashlib
import json
import math
import threading
import urllib.request

LEVELS = ('minimal', 'low', 'medium', 'high', 'xhigh', 'max')
CATALOG_URL = 'https://openrouter.ai/api/v1/models'


def effort_profile(reasoning_metadata):
    """Admission records can use highest effort plus ordered enabled fallbacks."""
    advertised = reasoning_metadata.get('supported_efforts', [])
    unknown = set(advertised) - set(LEVELS) - {'none'}
    if unknown:
        raise ValueError('Unrecognized reasoning effort levels require capability review')
    ordered = [level for level in reversed(LEVELS) if level in advertised]
    return dict(supported_efforts=ordered, initial_effort=ordered[0] if ordered else None,
                fallback_efforts=ordered[1:], controllable=bool(ordered))


def public_catalog():
    with urllib.request.urlopen(CATALOG_URL, timeout=30) as response:
        data = json.load(response)
    return {item['id']: item.get('reasoning') or {} for item in data['data']}


def confirmed_hit(record):
    if record.get('event') not in {'result', 'artifact_response_received', 'baseline_response'}:
        return False
    if record.get('http_status') is not None or record.get('csv_may_describe_earlier_attempt'):
        return False
    completion, cap = record.get('completion_tokens'), record.get('configured_output_cap')
    try:
        completion, cap = float(completion), float(cap)
    except (TypeError, ValueError):
        return False
    return (math.isfinite(completion) and math.isfinite(cap) and cap > 0 and completion >= cap
            and record.get('finish_reason') in {None, 'length', 'max_tokens'}
            and record.get('incomplete_reason') in {None, 'max_output_tokens'})


class CeilingPolicy:
    def __init__(self, records=(), catalog=None, catalog_loader=None):
        self.catalog, self.catalog_loader = catalog, catalog_loader or public_catalog
        self.hits, self.decisions = {}, {}
        self.lock = threading.Lock()
        for record in records:
            self.observe(record)

    def observe(self, record):
        if 'case' not in record or 'model' not in record:
            return
        pair = (str(record['case']), record['model'])
        attempt = record.get('event_attempt')
        decision = record.get('reasoning_retry')
        if decision and decision.get('policy') == 'ceiling_stepdown_v1' and type(attempt) is int:
            previous = self.decisions.get(pair)
            if previous is None or attempt > previous[0]:
                self.decisions[pair] = (attempt, decision)
            elif attempt == previous[0] and decision != previous[1]:
                raise ValueError('Conflicting reasoning decisions for one request')
        if not confirmed_hit(record):
            return
        response_attempt = record.get('response_attempt')
        if response_attempt is not None and attempt is not None and response_attempt != attempt:
            return
        aliases = set()
        if record.get('response_id'):
            aliases.add(('response', record['response_id']))
        if record.get('csv_response_timestamp'):
            aliases.add(('timestamp', record['csv_response_timestamp']))
        if (record.get('response_evidence_source') != 'csv_fields'
                and record.get('event') != 'baseline_response' and type(attempt) is int):
            aliases.add(('attempt', attempt))
        if not aliases:
            return  # A copied CSV token count without response identity is not another hit.
        groups = self.hits.setdefault(pair, [])
        matches = [group for group in groups if group & aliases]
        if matches:
            for group in matches:
                aliases.update(group)
                groups.remove(group)
        groups.append(aliases)

    def choose(self, model, case, attempt, cap):
        pair = (str(case), model['name'])
        with self.lock:
            prior = self.decisions.get(pair)
            base = (model.get('extra', {}).get('reasoning') or {}).get('effort')
            current = prior[1]['selected_effort'] if prior else base
            count = len(self.hits.get(pair, []))
            handled = prior[1]['ceiling_hits_before'] if prior else 0
            selected, reason, supported = current, 'no_new_ceiling_trigger', []
            if count >= 2 and count > handled:
                if current is None:
                    reason = 'no_explicit_effort_control'
                else:
                    if self.catalog is None:
                        self.catalog = self.catalog_loader()
                    if model['id'] not in self.catalog:
                        raise ValueError('Reasoning capability missing from current catalog')
                    available = effort_profile(self.catalog[model['id']])['supported_efforts']
                    supported = [level for level in LEVELS if level in available]
                    if current not in supported:
                        raise ValueError('Configured reasoning effort absent from supported levels')
                    selected = supported[max(0, supported.index(current) - 1)]
                    reason = 'ceiling_step_down' if selected != current else 'lowest_enabled_effort'
            decision = dict(policy='ceiling_stepdown_v1', ceiling_hits_before=count,
                            previous_effort=current, selected_effort=selected, changed=selected != current,
                            reason=reason, max_output_tokens=cap, supported_efforts=supported)
            if supported:
                decision['capability_source'] = CATALOG_URL
                decision['capability_sha256'] = hashlib.sha256(json.dumps(
                    self.catalog[model['id']], sort_keys=True).encode()).hexdigest()
            self.decisions[pair] = (attempt, decision)
            chosen = copy.deepcopy(model)
            if selected is not None:
                chosen.setdefault('extra', {}).setdefault('reasoning', {})['effort'] = selected
            return chosen, decision

    def received(self, case, model, attempt, cap, metadata):
        with self.lock:
            self.observe(dict(metadata, case=str(case), model=model, event='artifact_response_received',
                              event_attempt=attempt, response_attempt=attempt,
                              configured_output_cap=cap, response_evidence_source='response_metadata'))
