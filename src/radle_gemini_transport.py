"""Explicit direct-Gemini transport; never holds an OpenRouter credential or fallback."""
import copy
import json
from types import SimpleNamespace
import urllib.request
import urllib.error

BASE = 'https://generativelanguage.googleapis.com/v1beta/'
# A transport authorization, not a replacement collection contract or repair grant.
ALLOWED_MODELS = {'google/gemini-4-argon': 'gemini-4-argon'}


class GeminiRequestError(RuntimeError):
    def __init__(self, status, body, headers):
        super().__init__(f'Direct Gemini request failed: HTTP {status}')
        self.status_code = status
        self.body = body
        self.response = SimpleNamespace(headers=headers)


class GeminiOnlyClient:
    transport_name = 'google_gemini_direct'
    base_url = BASE

    def __init__(self, api_key):
        if not api_key:
            raise ValueError('GEMINI_API_KEY is required; OpenRouter fallback is disabled')
        self.api_key = api_key
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def with_options(self, max_retries=0, timeout=600):
        if max_retries != 0 or timeout != 600:
            raise ValueError('Direct Gemini requires zero SDK retries and 600-second timeout')
        return self

    def _request(self, path, payload=None):
        # Paths are derived only from validated, explicitly allowed model names.
        if path not in {f'models/{m}' for m in ALLOWED_MODELS.values()} | {f'models/{m}:generateContent' for m in ALLOWED_MODELS.values()}:
            raise ValueError('Unauthorized direct Gemini path')
        request = urllib.request.Request(BASE + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={'x-goog-api-key': self.api_key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            # Retain typed code only; do not persist arbitrary provider messages containing credentials.
            try:
                error = json.load(exc).get('error', {})
            except (ValueError, AttributeError):
                error = {}
            typed = GeminiRequestError(exc.code, {'error': {'code': error.get('status') or exc.code}}, dict(exc.headers or {}))
            message = str(error.get('message', '')).lower()
            if any(term in message for term in ('prepayment', 'credits depleted', 'billing', 'daily quota', 'per day')):
                typed.radle_diagnostic = {'category': 'quota'}
            raise typed from None

    def preflight(self, config, models):
        receipts = []
        for model in models:
            native = ALLOWED_MODELS.get(model['id'])
            if not native:
                raise RuntimeError('OpenRouter spending disabled; model has no authorized Gemini route')
            live = self._request('models/' + native)
            if (live.get('name') != 'models/' + native or not live.get('thinking')
                    or 'generateContent' not in live.get('supportedGenerationMethods', [])
                    or int(live.get('outputTokenLimit') or 0) < config['output_cap']):
                raise RuntimeError('Direct Gemini model/capability mismatch')
            receipts.append(dict(transport=self.transport_name, actual_model=native,
                metadata=live, billing_balance_verified=False, openrouter_spending_allowed=False))
        return receipts

    def spending_preflight(self, models, output_cap):
        self.preflight({'output_cap': output_cap}, models)
        return dict(status='available', evidence_basis='direct_gemini_metadata_authentication',
                    billing_balance_verified=False, openrouter_spending_allowed=False)

    def prepare_request(self, model, params):
        native = ALLOWED_MODELS.get(model['id'])
        if not native or params.get('model') != model['id'] or model.get('api_surface') == 'responses':
            raise ValueError('OpenRouter spending disabled; only the authorized direct Gemini model is allowed')
        effort = model.get('extra', {}).get('reasoning', {}).get('effort')
        if effort not in {'high', 'medium', 'low'}:
            raise ValueError('Unsupported enabled Gemini reasoning level')
        parts = []
        for message in params['messages']:
            if message['role'] != 'user':
                raise ValueError('Unexpected benchmark message role')
            for part in message['content']:
                if part['type'] == 'text':
                    parts.append({'text': part['text']})
                elif part['type'] == 'image_url':
                    url = part['image_url']['url']
                    if not url.startswith('data:image/') or ';base64,' not in url:
                        raise ValueError('Only local inline benchmark images are allowed')
                    header, data = url.split(';base64,', 1)
                    parts.append({'inlineData': {'mimeType': header[5:], 'data': data}})
                else:
                    raise ValueError('Unsupported benchmark content')
        cap = params.get('max_tokens')
        if cap != 32768:
            raise ValueError('Authorized output cap must remain 32768')
        generation = dict(maxOutputTokens=cap, responseMimeType='application/json',
                          thinkingConfig=dict(thinkingLevel=effort.upper(), includeThoughts=True))
        if 'temperature' in params:
            generation['temperature'] = params['temperature']
        payload = dict(contents=[dict(role='user', parts=parts)], generationConfig=generation)
        actual = copy.deepcopy(model)
        actual['expected_returned_model_ids'] = [native, 'models/' + native, native + '-20261013']
        actual['expected_provider'] = 'Google AI Studio'
        return actual, dict(model=native, native_payload=payload,
            extra_body=dict(transport=self.transport_name, endpoint=BASE + 'models/' + native + ':generateContent',
                            reasoning=dict(effort=effort, exclude=False), max_output_tokens=cap,
                            credential_name='GEMINI_API_KEY', openrouter_spending_allowed=False))

    def create(self, *, model, native_payload, extra_body):
        if model not in ALLOWED_MODELS.values() or extra_body.get('transport') != self.transport_name:
            raise ValueError('Direct Gemini dispatch refused')
        if native_payload.get('generationConfig', {}).get('maxOutputTokens') != 32768:
            raise ValueError('Direct Gemini output cap mismatch')
        raw = self._request('models/' + model + ':generateContent', native_payload)
        policy_rejected = bool(raw.get('promptFeedback', {}).get('blockReason'))
        candidates = raw.get('candidates', [])
        candidate = candidates[0] if candidates else {}
        parts = candidate.get('content', {}).get('parts', [])
        final = ''.join(p.get('text', '') for p in parts if not p.get('thought'))
        thoughts = ''.join(p.get('text', '') for p in parts if p.get('thought'))
        usage = raw.get('usageMetadata', {})
        finish = candidate.get('finishReason')
        policy_rejected = policy_rejected or finish in {'SAFETY', 'RECITATION', 'PROHIBITED_CONTENT', 'BLOCKLIST', 'SPII', 'IMAGE_SAFETY'}
        unverified = not policy_rejected and finish not in {'STOP', 'MAX_TOKENS'}
        finish = {'STOP':'stop', 'MAX_TOKENS':'length', 'SAFETY':'content_filter',
                  'RECITATION':'content_filter', 'PROHIBITED_CONTENT':'content_filter'}.get(finish, 'content_filter' if policy_rejected else 'error')
        normalized = dict(id=raw.get('responseId', 'gemini-direct'), object='chat.completion', created=0,
            model=raw.get('modelVersion', model), provider='Google AI Studio',
            transport=self.transport_name, original_gemini_response=raw,
            choices=[dict(index=0, finish_reason=finish, message=dict(role='assistant', content=final, reasoning=thoughts))],
            usage=dict(prompt_tokens=usage.get('promptTokenCount', 0),
                completion_tokens=usage.get('candidatesTokenCount', 0) + usage.get('thoughtsTokenCount', 0),
                total_tokens=usage.get('totalTokenCount', 0),
                completion_tokens_details=dict(reasoning_tokens=usage.get('thoughtsTokenCount', 0))))
        response = json.loads(json.dumps(normalized), object_hook=lambda d: SimpleNamespace(**d))
        response.model_extra = {'provider': 'Google AI Studio', 'transport': self.transport_name}
        response._radle_original_response = normalized
        response._radle_policy_rejected = policy_rejected
        response._radle_remote_unverified = unverified
        return response
