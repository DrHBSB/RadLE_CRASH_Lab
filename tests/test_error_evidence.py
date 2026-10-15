import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from radle_error_evidence import evidence_record
from radle_benchmark import case_rejection_diagnostic


class EvidenceTests(unittest.TestCase):
    key = json.dumps(['5', 'model'])

    def record(self, value):
        return evidence_record(self.key, dict(status='failed', attempts=6, repair_round=4, value=value))

    def test_empty_answer_at_cap_reports_observations_not_cause(self):
        r = self.record(dict(response_metadata=dict(content_length=0, completion_tokens=32768,
                        reasoning_tokens=32768, finish_reason='length')))
        self.assertEqual(r['classification'], 'empty_final_answer')
        self.assertIn('reached the configured cap', r['observation'])
        self.assertEqual(r['root_cause'], 'not_independently_verified')
        self.assertEqual(r['journal_attempts'], 6)

    def test_subcap_and_missing_usage_are_not_cap_failures(self):
        for count in (6183, None):
            r = self.record(dict(response_metadata=dict(content_length=0, completion_tokens=count)))
            self.assertNotIn('reached', r['observation'])

    def test_http_keeps_old_csv_evidence_separate(self):
        r = self.record(dict(http_status=402, fields={'Total_Tokens_Out_model':32768,
                             'Raw_Response_model':'', 'Timestamp_UTC_model':'old'}))
        self.assertEqual(r['classification'], 'http_error')
        self.assertTrue(r['csv_may_describe_earlier_attempt'])
        self.assertNotIn('no money', r['observation'])

    def test_missing_current_metadata_not_filled_from_old_csv(self):
        r = self.record(dict(response_metadata={'finish_reason':'stop'}, fields={'Total_Tokens_Out_model':32768}))
        self.assertIsNone(r['completion_tokens'])

    def test_typed_image_error_distinct_from_moderation(self):
        for code, expected in [('image_download_failed','image_input_error'), ('refusal','provider_policy_rejection')]:
            d = case_rejection_diagnostic({'error':{'code':code}})
            r = self.record(dict(diagnostic=d))
            self.assertEqual(r['classification'], expected)
            self.assertEqual(r['provider_error_code'], code)

    def test_unknown_and_arbitrary_sensitive_text_not_echoed(self):
        r = self.record(dict(reason='patient secret', diagnostic={'summary':'patient secret',
                             'provider_error_code':'Bearer sk-secret with spaces'}))
        self.assertNotIn('patient secret', json.dumps(r))
        self.assertIsNone(r['provider_error_code'])
        self.assertEqual(r['classification'], 'unknown')
