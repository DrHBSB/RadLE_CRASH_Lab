import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import radle_benchmark as rb


class ProviderCaptureTests(unittest.TestCase):
    def setUp(self):
        self.client = SimpleNamespace(base_url='https://openrouter.ai/api/v1/', api_key='test-only')

    def metadata(self, identity='gen-test', provider='OpenAI'):
        return io.StringIO(json.dumps({'data': {'id': identity, 'provider_name': provider}}))

    def test_delayed_metadata_retries_only_lookup(self):
        opener = Mock()
        opener.open.side_effect = [urllib.error.HTTPError('url', 404, 'pending', {}, None), self.metadata()]
        with patch.object(rb.urllib.request, 'build_opener', return_value=opener), patch.object(rb.time, 'sleep') as sleep:
            result = rb.enrich_openrouter_provider({'id': 'gen-test'}, self.client)
        self.assertEqual(result['provider'], 'OpenAI')
        self.assertNotIn('generation_metadata_error', result)
        self.assertEqual(opener.open.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_identity_mismatch_stays_unknown(self):
        opener = Mock(); opener.open.return_value = self.metadata(identity='gen-other')
        with patch.object(rb.urllib.request, 'build_opener', return_value=opener):
            result = rb.enrich_openrouter_provider({'id': 'gen-test'}, self.client)
        self.assertNotIn('provider', result)
        self.assertEqual(result['generation_metadata_error'], 'ValueError')
        self.assertEqual(opener.open.call_count, 1)

    def test_auth_failure_is_not_retried(self):
        opener = Mock(); opener.open.side_effect = urllib.error.HTTPError('url', 401, 'unauthorized', {}, None)
        with patch.object(rb.urllib.request, 'build_opener', return_value=opener):
            result = rb.enrich_openrouter_provider({'id': 'gen-test'}, self.client)
        self.assertNotIn('provider', result)
        self.assertEqual(opener.open.call_count, 1)
        self.assertEqual(result['generation_metadata_lookup_errors'][0]['http_status'], 401)

    def test_unavailable_metadata_is_bounded(self):
        opener = Mock(); opener.open.side_effect = urllib.error.HTTPError('url', 404, 'pending', {}, None)
        with patch.object(rb.urllib.request, 'build_opener', return_value=opener), patch.object(rb.time, 'sleep'):
            result = rb.enrich_openrouter_provider({'id': 'gen-test'}, self.client)
        self.assertNotIn('provider', result)
        self.assertEqual(opener.open.call_count, 4)

    def test_response_provider_is_preserved_without_lookup(self):
        with patch.object(rb.urllib.request, 'build_opener') as opener:
            result = rb.enrich_openrouter_provider({'id': 'gen-test', 'provider': 'Azure'}, self.client)
        self.assertEqual(result['provider'], 'Azure')
        opener.assert_not_called()


if __name__ == '__main__':
    unittest.main()
