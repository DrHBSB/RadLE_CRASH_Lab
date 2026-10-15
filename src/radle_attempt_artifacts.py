"""Private immutable attempt artifacts, staged locally then verified at destination.

No credentials or request image/prompt bodies belong in the stage receipts.
Response envelopes are private research data and stay beside the existing run.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid


def jsonable(value):
    if hasattr(value, 'model_dump'):
        return value.model_dump(mode='json')
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if hasattr(value, '__dict__'):
        return jsonable(vars(value))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError('Unsupported response field type')


def redact(value, sensitive_values=()):
    if isinstance(value, dict):
        return {k: redact(v, sensitive_values) for k, v in value.items()
                if str(k).lower() not in {'authorization', 'api_key', 'api-key', 'headers', 'request'}}
    if isinstance(value, list):
        return [redact(v, sensitive_values) for v in value]
    if isinstance(value, str):
        for secret in sensitive_values:
            if isinstance(secret, str) and secret:
                value = value.replace(secret, '[REDACTED_KEY]')
    return value


def persist(folder, identity, stage, payload, *, sensitive_values=()):
    """Never overwrite. A stage receipt commits only after destination hash check."""
    data = (json.dumps(dict(schema=1, identity=identity, stage=stage,
                          recorded_utc=datetime.now(timezone.utc).isoformat(),
                          payload=redact(jsonable(payload), sensitive_values)), ensure_ascii=False,
                       sort_keys=True, allow_nan=False) + '\n').encode('utf-8')
    digest = hashlib.sha256(data).hexdigest()
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (identity['attempt_id'] + '.' + stage + '.' + digest + '.json')
    with tempfile.TemporaryDirectory(prefix='radle-attempt-') as staging:
        local = Path(staging) / 'artifact.json'
        with local.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        with target.open('xb') as stream:
            with local.open('rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    stream.write(block)
            stream.flush()
            os.fsync(stream.fileno())
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise RuntimeError('Private attempt artifact verification failed')
    return dict(path=str(target), sha256=digest, stage=stage)


def new_identity(case, model, attempt, params):
    data = json.dumps(jsonable(params), sort_keys=True, ensure_ascii=False,
                      allow_nan=False).encode('utf-8')
    return dict(attempt_id=uuid.uuid4().hex, case=case, model=model,
                journal_attempt=attempt, request_sha256=hashlib.sha256(data).hexdigest())


def read_verified(receipt):
    data = Path(receipt['path']).read_bytes()
    if hashlib.sha256(data).hexdigest() != receipt['sha256']:
        raise ValueError('Attempt artifact hash mismatch')
    return json.loads(data)


def chat_final_text(content):
    if content is None:
        return ''
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list) and all(isinstance(p, dict)
            and p.get('type') in {'text', 'output_text'} and isinstance(p.get('text'), str) for p in content):
        return ''.join(p['text'] for p in content).strip()
    raise ValueError('Unrecognized final-content structure; original response retained')


def response_metadata(data):
    """Observe either API envelope without assuming missing values are zero."""
    usage = data.get('usage') or {}
    details = usage.get('completion_tokens_details') or usage.get('output_tokens_details') or {}
    choices = data.get('choices') or []
    choice = choices[0] if choices else {}
    message = choice.get('message') or {}
    content = message.get('content')
    refusal = bool(message.get('refusal'))
    if 'output' in data:
        parts = [part for item in data.get('output') or [] if item.get('type') == 'message'
                 for part in item.get('content') or []]
        content = ''.join(part['text'] for part in parts
                          if part.get('type') == 'output_text' and isinstance(part.get('text'), str))
        refusal = any(part.get('type') == 'refusal' for part in parts)
    elif isinstance(content, list):
        if all(isinstance(p, dict) and p.get('type') in {'text', 'output_text'}
               and isinstance(p.get('text'), str) for p in content):
            content = ''.join(p['text'] for p in content)
    return dict(response_id=data.get('id'), response_status=data.get('status'),
                finish_reason=choice.get('finish_reason') or data.get('finish_reason'),
                native_finish_reason=choice.get('native_finish_reason') or data.get('native_finish_reason'),
                incomplete_reason=(data.get('incomplete_details') or {}).get('reason'),
                content_type=type(message.get('content')).__name__ if choices else 'responses_output',
                content_length=len(content) if isinstance(content, str) else 0 if content is None else None,
                refusal_present=refusal,
                completion_tokens=usage.get('completion_tokens', usage.get('output_tokens')),
                prompt_tokens=usage.get('prompt_tokens', usage.get('input_tokens')),
                reasoning_tokens=details.get('reasoning_tokens'))
