"""Non-clinical, evidence-qualified diagnostics; never infer a remote cause."""
import json
import math
import re


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (TypeError, ValueError):
        return None


def code(value):
    # Do not copy arbitrary provider messages, prompts, refusals or credentials.
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,160}', value) else None


def evidence_record(key, state, max_output_tokens=32768):
    case, model = json.loads(key)
    value = state.get('value') or {}
    fields = value.get('fields') or {}
    metadata = value.get('response_metadata') or {}
    diagnostic = value.get('diagnostic') or {}
    history = value.get('attempt_history') or {}
    response_evidence = bool(metadata)
    csv_evidence = bool(fields)
    def token(name, column):
        # Metadata and CSV can describe different attempts. Never fill a missing
        # metadata field using a possibly older CSV record.
        return number(metadata.get(name)) if response_evidence else number(fields.get(column + '_' + model))
    completion = token('completion_tokens', 'Total_Tokens_Out')
    reasoning = token('reasoning_tokens', 'Reasoning_Tokens')
    raw = fields.get('Raw_Response_' + model)
    content_length = number(metadata.get('content_length')) if response_evidence else (len(raw.strip()) if isinstance(raw, str) else None)
    provider_code = code(diagnostic.get('provider_error_code'))
    finish = code(metadata.get('finish_reason'))
    http = value.get('http_status')
    observation = 'Failure cause not established from retained evidence.'
    classification = 'unknown'
    basis = 'insufficient_evidence'
    if value.get('reason') == 'missing_readable_reasoning':
        classification, observation, basis = 'missing_readable_reasoning', 'Validation flag: missing readable reasoning.', 'response_validation'
    elif value.get('remote_outcome_unknown') or state['status'] == 'uncertain':
        classification, observation = 'remote_outcome_unknown', 'Remote outcome is unverified; this does not establish a model failure cause.'
    elif provider_code:
        technical = {'invalid_image', 'image_too_large', 'image_too_small', 'unsupported_image_format', 'image_not_found', 'image_download_failed'}
        moderation = {'content_policy_violation', 'image_content_policy_violation', 'refusal', 'moderation_flagged'}
        classification = 'image_input_error' if provider_code in technical else 'provider_policy_rejection' if provider_code in moderation else 'provider_error_code'
        observation, basis = 'Provider returned code: ' + provider_code + '.', 'typed_provider_error'
    elif http is not None:
        classification = 'http_error'
        observation, basis = f'HTTP {http} recorded; underlying cause is not independently established.', 'recorded_http_status'
    elif content_length == 0:
        classification, observation = 'empty_final_answer', 'Stored final-answer content is empty.'
        basis = 'response_metadata' if response_evidence else 'csv_fields'
        if completion is not None and completion >= max_output_tokens:
            observation += ' Reported completion-token count reached the configured cap.'
        if reasoning is not None and completion is not None and reasoning == completion and completion > 0:
            observation += ' Reported reasoning tokens equal reported completion tokens.'
        if finish:
            observation += ' Recorded finish reason: ' + finish + '.'
        observation += ' These observations do not independently establish the root cause.'
    elif content_length is not None:
        classification, observation, basis = 'nonempty_final_answer', 'Stored final-answer content is nonempty; see validation status.', 'response_metadata' if response_evidence else 'csv_fields'
    return dict(case=case, model=model, scheduler_status=state['status'],
        journal_attempts=state['attempts'], attempt_count_source='concurrent_journal',
        repair_round=state.get('repair_round'), authorized_attempt_limit=state.get('repair_attempt'),
        cumulative_attempts=history.get('cumulative_attempt'),
        response_attempt=history.get('collection_attempt'),
        csv_response_timestamp=fields.get('Timestamp_UTC_' + model),
        response_evidence_source='response_metadata' if response_evidence else 'csv_fields' if csv_evidence else 'unavailable',
        csv_may_describe_earlier_attempt=bool(http is not None and csv_evidence),
        http_status=http, provider_error_code=provider_code,
        error_type=code(value.get('error_type') or diagnostic.get('error_type')),
        response_id=code(metadata.get('response_id')), finish_reason=finish,
        native_finish_reason=code(metadata.get('native_finish_reason')),
        completion_tokens=completion, reasoning_tokens=reasoning,
        prompt_tokens=token('prompt_tokens', 'Prompt_Tokens'),
        configured_output_cap=max_output_tokens, content_length=content_length,
        content_length_is_csv_truncated=bool(not response_evidence and isinstance(raw, str) and len(raw) >= 2000),
        classification=classification, evidence_basis=basis, observation=observation,
        root_cause='not_independently_verified')


def evidence_summary(key, state):
    record = evidence_record(key, state)
    return record['observation'] + f" Journal attempts: {record['journal_attempts']}."
