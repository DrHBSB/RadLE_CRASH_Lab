import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import radle_gemini_transport as gt
import radle_concurrent_collection as cc
import test_concurrent_collection as fixtures


def model():
    return copy.deepcopy(json.loads((ROOT / 'configs/radle_collection.json').read_text())['models'][-1])


def raw():
    return dict(modelVersion='gemini-4-argon', responseId='fixture',
        candidates=[dict(finishReason='STOP', content=dict(parts=[
            dict(text='visible summary', thought=True),
            dict(text='{"diagnosis":"fixture diagnosis","likert_score":4}')]))],
        usageMetadata=dict(promptTokenCount=10, candidatesTokenCount=20, thoughtsTokenCount=5, totalTokenCount=35))


class GeminiOnlyTests(unittest.TestCase):
    def test_translation_preserves_images_reasoning_cap_and_explicit_route(self):
        import radle_benchmark as rb
        m = model(); original = copy.deepcopy(m)
        client = gt.GeminiOnlyClient('fixture-not-a-real-key')
        parts = [dict(type='text', text='same prompt'),
                 dict(type='image_url', image_url=dict(url='data:image/png;base64,aGVsbG8='))]
        actual, params = client.prepare_request(m, rb.build_api_params(m, parts, 32768, 0))
        self.assertEqual(m, original)
        self.assertEqual(params['native_payload']['contents'][0]['parts'][0]['text'], 'same prompt')
        self.assertEqual(params['native_payload']['generationConfig']['thinkingConfig'],
                         dict(thinkingLevel='HIGH', includeThoughts=True))
        self.assertEqual(params['native_payload']['generationConfig']['maxOutputTokens'], 32768)
        self.assertEqual(actual['expected_provider'], 'Google AI Studio')
        self.assertFalse(params['extra_body']['openrouter_spending_allowed'])
        with patch.object(client, '_request', return_value=raw()) as request:
            response = client.create(**params)
        self.assertEqual(request.call_count, 1)
        fields = rb.extract_result(response, 1, params, False, actual)
        self.assertEqual(fields['Provider_gemini_4_argon'], 'Google AI Studio')
        self.assertEqual(fields['Reasoning_gemini_4_argon'], 'visible summary')
        self.assertEqual(fields['Total_Tokens_Out_gemini_4_argon'], 25)
        self.assertEqual(fields['Reasoning_Tokens_gemini_4_argon'], 5)
        self.assertIn('original_gemini_response', response._radle_original_response)

    def test_unauthorized_models_paths_retries_are_blocked_before_network(self):
        client = gt.GeminiOnlyClient('fixture')
        with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
            with self.assertRaises(ValueError): client._request('https://openrouter.ai/api/v1/chat/completions')
            with self.assertRaises(ValueError): client.prepare_request(dict(id='anthropic/anything'), {})
            with self.assertRaises(ValueError): client.with_options(max_retries=1)
            with self.assertRaises(ValueError): client.create(model='anything', native_payload={}, extra_body={})

    def test_authentication_preflight_is_not_claimed_as_billing_verification(self):
        client = gt.GeminiOnlyClient('fixture')
        live = dict(name='models/gemini-4-argon', thinking=True, outputTokenLimit=32768,
                    supportedGenerationMethods=['generateContent'])
        with patch.object(client, '_request', return_value=live):
            receipt = client.spending_preflight([model()], 32768)
        self.assertEqual(receipt['status'], 'available')
        self.assertFalse(receipt['billing_balance_verified'])
        self.assertFalse(receipt['openrouter_spending_allowed'])

    def test_policy_refusal_and_unknown_response_are_held(self):
        import radle_benchmark as rb
        client = gt.GeminiOnlyClient('fixture'); m = model()
        _, params = client.prepare_request(m, rb.build_api_params(m, [dict(type='text', text='fixture')], 32768, 0))
        blocked = raw(); blocked['candidates'][0]['finishReason'] = 'SAFETY'
        with patch.object(client, '_request', return_value=blocked):
            response = client.create(**params)
            self.assertTrue(response._radle_policy_rejected)
            self.assertEqual(response._radle_original_response['original_gemini_response'], blocked)
        with patch.object(client, '_request', return_value={}):
            self.assertTrue(client.create(**params)._radle_remote_unverified)

    def test_real_collector_retains_contract_and_never_calls_openrouter_on_resume(self):
        import radle_benchmark as rb
        f = fixtures.IntegrationTests(); f.setUp(); self.addCleanup(f.doCleanups)
        m = model(); client = gt.GeminiOnlyClient('fixture')
        def request(path, payload=None):
            if payload is None:
                return dict(name='models/gemini-4-argon', thinking=True, outputTokenLimit=32768,
                            supportedGenerationMethods=['generateContent'])
            return raw()
        with patch.object(client, '_request', side_effect=request) as calls, \
             patch.object(cc, 'check_openrouter_funds', side_effect=AssertionError('OpenRouter forbidden')):
            first = cc.collect(rb, client=client, image_folder=f.images, output_csv=f.output,
                models=[m], test_limit=3, concurrency=1, max_attempts=2, resume_blocked=True,
                max_output_tokens=32768, allow_partial_result=True)
            after = sum(c.kwargs.get('payload') is not None or len(c.args)>1 for c in calls.call_args_list)
            cc.collect(rb, client=client, image_folder=f.images, output_csv=f.output,
                models=[m], test_limit=3, concurrency=1, max_attempts=2, resume_blocked=True,
                max_output_tokens=32768, allow_partial_result=True)
            total = sum(c.kwargs.get('payload') is not None or len(c.args)>1 for c in calls.call_args_list)
        self.assertEqual(after, 3); self.assertEqual(total, 3)
        self.assertTrue(first['Provider_gemini_4_argon'].eq('Google AI Studio').all())
        self.assertTrue(first['Transport_gemini_4_argon'].eq('google_gemini_direct').all())

    def test_unused_bounded_repairs_use_gemini_only_and_stop_at_success(self):
        import radle_benchmark as rb
        import time
        f = fixtures.IntegrationTests(); f.setUp(); self.addCleanup(f.doCleanups)
        client = gt.GeminiOnlyClient('fixture'); seen = []
        def request(path, payload=None):
            if payload is None:
                return dict(name='models/gemini-4-argon', thinking=True, outputTokenLimit=32768,
                            supportedGenerationMethods=['generateContent'])
            seen.append(payload)
            response = raw()
            if len(seen) < 4:
                response['candidates'][0]['content']['parts'] = [dict(text='summary', thought=True)]
            return response
        options = dict(client=client, image_folder=f.images, output_csv=f.output, models=[model()],
                       test_limit=1, concurrency=1, max_attempts=2, resume_blocked=True,
                       max_output_tokens=32768, allow_partial_result=True)
        policy = json.loads((ROOT / 'configs/radle_collection.json').read_text())['retry_authorization']
        clock = int(time.time()) + 100
        with patch.object(client, '_request', side_effect=request), \
             patch.object(cc, 'check_openrouter_funds', side_effect=AssertionError('OpenRouter forbidden')), \
             patch.object(cc.queue.time, 'time', side_effect=range(clock, clock+1000000, 70)):
            cc.collect(rb, **options)
            cc.collect(rb, **options, retry_authorization=policy)
            cc.collect(rb, **options, retry_authorization=policy)
        self.assertEqual(len(seen), 4)

    def test_notebook_never_loads_openrouter_credential(self):
        nb = json.loads((ROOT/'notebooks/RadLE_v1_5_Morning.ipynb').read_text(encoding='utf-8'))
        code = '\n'.join(''.join(c['source']) for c in nb['cells'])
        self.assertNotIn('userdata.get("OPENROUTER_API_KEY")', code)
        self.assertIn('userdata.get("GEMINI_API_KEY")', code)
        self.assertIn('preflight_transport=openrouter_client', code)
        for c in nb['cells']: compile(''.join(c['source']), 'notebook', 'exec')
