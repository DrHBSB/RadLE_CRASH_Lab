"""Reusable, explicitly authorized spaced retries; never reset history."""
import hashlib
import json


def validate(policy):
    if (not isinstance(policy, dict) or set(policy) !=
            {'id', 'max_pairs', 'attempts_per_pair', 'spacing_seconds',
             'include_uncertain', 'include_quota', 'include_exhausted'}
            or not isinstance(policy['id'], str) or not 1 <= len(policy['id']) <= 128
            or type(policy['max_pairs']) is not int or policy['max_pairs'] < 1
            or type(policy['attempts_per_pair']) is not int or not 1 <= policy['attempts_per_pair'] <= 2
            or type(policy['spacing_seconds']) is not int or policy['spacing_seconds'] < 60
            or any(type(policy[k]) is not bool for k in
                   ('include_uncertain', 'include_quota', 'include_exhausted'))):
        raise ValueError('Invalid explicit retry policy')
    return policy


def basis(state):
    result = {k: state.get(k) for k in ('status', 'attempts', 'repair_attempt', 'repair_round',
                                     'retry_authorizations', 'retry_policy')} | {
        'repair_outcome': state.get('value', {}).get('repair_outcome'),
        'remote_outcome_unknown': bool(state.get('value', {}).get('remote_outcome_unknown'))}
    if state.get('repair_attempt') is not None and not state.get('retry_policy'):
        result['repair_round'] = state.get('repair_round', 1)
    return result


def fingerprint(state):
    return hashlib.sha256(json.dumps(basis(state), sort_keys=True,
                         separators=(',', ':')).encode()).hexdigest()


def eligible(state, policy):
    validate(policy)
    value = state.get('value', {})
    status = state['status']
    if (policy['id'] in state.get('retry_authorizations', [])
            or status in {'success', 'flagged', 'rejected', 'blocked'}
            or value.get('repair_outcome') in {'rejected', 'blocked'}):
        return False
    if (status == 'uncertain' or value.get('remote_outcome_unknown')) and not policy['include_uncertain']:
        return False
    if (status == 'quota' or value.get('repair_outcome') == 'quota') and not policy['include_quota']:
        return False
    if status == 'pending' and not policy['include_exhausted']:
        return False
    return status in {'failed', 'terminal', 'retry', 'uncertain', 'quota', 'pending'}


def event_for(key, state, policy):
    if not eligible(state, policy):
        raise ValueError('Pair is not eligible for this retry policy')
    return dict(type='retry_pass_authorized', key=key, attempt=state['attempts'] + policy['attempts_per_pair'],
                policy=dict(policy), prior_sha256=fingerprint(state))


def apply(state, event):
    policy = validate(event['policy'])
    if (not eligible(state, policy) or event['attempt'] != state['attempts'] + policy['attempts_per_pair']
            or event.get('prior_sha256') != fingerprint(state)):
        raise ValueError('Retry authorization does not match prior evidence')
    state['retry_authorizations'] = list(state.get('retry_authorizations', [])) + [policy['id']]
    if state.get('repair_attempt') is not None and not state.get('retry_policy'):
        state.setdefault('repair_round', 1)
    state['repair_attempt'] = event['attempt']
    state['retry_policy'] = dict(policy)


def resumable(state, policy):
    before_first = state['attempts'] == state.get('repair_attempt', 0) - policy['attempts_per_pair']
    return (state.get('retry_authorizations', [])[-1:] == [policy['id']]
            and state.get('retry_policy') == policy
            and state['attempts'] < state['repair_attempt']
            and (before_first or (not state.get('value', {}).get('remote_outcome_unknown')
                 and state.get('value', {}).get('repair_outcome') not in {'quota', 'blocked', 'rejected', 'uncertain'}))
            and state['status'] not in {'success', 'flagged', 'rejected', 'blocked'})
