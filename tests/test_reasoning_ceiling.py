import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from radle_reasoning_ceiling import CeilingPolicy, confirmed_hit, effort_profile


class ReasoningCeilingTests(unittest.TestCase):
    def test_admission_profile_highest_and_fallbacks_without_disabling(self):
        profile = effort_profile({'supported_efforts': ['none', 'low', 'high', 'max']})
        self.assertEqual(profile['initial_effort'], 'max')
        self.assertEqual(profile['fallback_efforts'], ['high', 'low'])
        self.assertEqual(effort_profile({})['controllable'], False)
        with self.assertRaises(ValueError):
            effort_profile({'supported_efforts': ['unverified-new-level']})
    def model(self, name='arm'):
        return dict(name=name, id='vendor/model', extra={'reasoning': {'effort': 'max', 'exclude': False}},
                    provider_routing={'only': ['fixed'], 'allow_fallbacks': False})

    def hit(self, attempt, case='1', model='arm', **kwargs):
        return dict(event='result', case=case, model=model, event_attempt=attempt,
                    response_attempt=attempt, completion_tokens=32768,
                    configured_output_cap=32768, finish_reason='length', **kwargs)

    def policy(self, rows=(), levels=('max', 'xhigh', 'high', 'medium', 'low')):
        return CeilingPolicy(rows, catalog={'vendor/model': {'supported_efforts': list(levels)}})

    def test_threshold_two_and_private_request_copy(self):
        model = self.model(); before = copy.deepcopy(model)
        policy = self.policy([self.hit(1)])
        chosen, decision = policy.choose(model, '1', 2, 32768)
        self.assertEqual(chosen['extra']['reasoning']['effort'], 'max')
        policy.received('1', 'arm', 2, 32768, dict(completion_tokens=32768, finish_reason='length'))
        chosen, decision = policy.choose(model, '1', 3, 32768)
        self.assertEqual(chosen['extra']['reasoning']['effort'], 'xhigh')
        self.assertEqual(chosen['provider_routing'], before['provider_routing'])
        self.assertEqual(model, before)
        self.assertEqual(decision['max_output_tokens'], 32768)
        self.assertEqual(chosen['extra']['reasoning']['exclude'], False)

    def test_many_historical_hits_only_one_first_step_and_no_error_step(self):
        policy = self.policy([self.hit(i) for i in range(1, 7)])
        model = self.model()
        chosen, first = policy.choose(model, '1', 7, 32768)
        self.assertEqual(first['selected_effort'], 'xhigh')
        # A subsequent HTTP error / below-cap response does not create a cap hit.
        policy.received('1', 'arm', 7, 32768, dict(completion_tokens=40, finish_reason='error'))
        _, second = policy.choose(model, '1', 8, 32768)
        self.assertEqual(second['selected_effort'], 'xhigh')
        self.assertFalse(second['changed'])
        policy.received('1', 'arm', 8, 32768, dict(completion_tokens=32768, finish_reason='length'))
        _, third = policy.choose(model, '1', 9, 32768)
        self.assertEqual(third['selected_effort'], 'high')

    def test_pair_isolation_sparse_levels_and_floor(self):
        policy = self.policy([self.hit(1), self.hit(2)], levels=('max', 'high', 'low', 'none'))
        _, first = policy.choose(self.model(), '1', 3, 32768)
        self.assertEqual(first['selected_effort'], 'high')
        _, other_case = policy.choose(self.model(), '2', 3, 32768)
        _, other_model = policy.choose(self.model('different'), '1', 3, 32768)
        self.assertEqual(other_case['selected_effort'], 'max')
        self.assertEqual(other_model['selected_effort'], 'max')
        for attempt in (3, 4, 5):
            policy.received('1', 'arm', attempt, 32768, dict(completion_tokens=32768, finish_reason='length'))
            _, floor = policy.choose(self.model(), '1', attempt + 1, 32768)
        self.assertEqual(floor['selected_effort'], 'low')

    def test_duplicate_archives_artifacts_and_csv_do_not_count_twice(self):
        row = self.hit(1, response_id='generation-1', csv_response_timestamp='timestamp-1')
        artifact = dict(row, event='artifact_response_received')
        baseline = dict(row, event='baseline_response', response_evidence_source='csv_fields', response_id=None)
        policy = self.policy([row, row, artifact, baseline])
        _, decision = policy.choose(self.model(), '1', 2, 32768)
        self.assertEqual(decision['ceiling_hits_before'], 1)
        self.assertFalse(decision['changed'])

    def test_missing_or_contradictory_evidence_is_not_a_ceiling(self):
        for change in [dict(completion_tokens=None), dict(configured_output_cap=None),
                       dict(completion_tokens=32767), dict(finish_reason='error'),
                       dict(finish_reason='stop'), dict(http_status=429),
                       dict(csv_may_describe_earlier_attempt=True)]:
            self.assertFalse(confirmed_hit(self.hit(1) | change))
        policy = self.policy([self.hit(1) | dict(response_attempt=0)])
        self.assertEqual(policy.choose(self.model(), '1', 2, 32768)[1]['ceiling_hits_before'], 0)

    def test_no_effort_control_and_missing_supported_level(self):
        model = self.model(); model['extra']['reasoning'] = {'enabled': True, 'exclude': False}
        policy = self.policy([self.hit(1), self.hit(2)])
        chosen, decision = policy.choose(model, '1', 3, 32768)
        self.assertEqual(chosen, model)
        self.assertEqual(decision['reason'], 'no_explicit_effort_control')
        with self.assertRaisesRegex(ValueError, 'absent'):
            self.policy([self.hit(1), self.hit(2)], levels=('high',)).choose(self.model(), '1', 3, 32768)

    def test_restart_restores_level_and_does_not_lower_twice(self):
        rows = [self.hit(1), self.hit(2)]
        policy = self.policy(rows)
        _, decision = policy.choose(self.model(), '1', 3, 32768)
        prepared = dict(case='1', model='arm', event='artifact_prepared', event_attempt=3, reasoning_retry=decision)
        restored = self.policy(rows + [prepared])
        _, repeated = restored.choose(self.model(), '1', 4, 32768)
        self.assertEqual(repeated['selected_effort'], 'xhigh')
        self.assertFalse(repeated['changed'])
        restored.received('1', 'arm', 4, 32768, dict(completion_tokens=32768, finish_reason='length'))
        self.assertEqual(restored.choose(self.model(), '1', 5, 32768)[1]['selected_effort'], 'high')

    def test_collector_sends_lower_effort_and_records_it_without_extra_grant(self):
        import json
        from unittest.mock import patch
        import pandas as pd
        import radle_concurrent_collection as cc
        from test_concurrent_collection import IntegrationTests
        fixture = IntegrationTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.models[0]['extra']['reasoning'] = {'effort': 'max', 'exclude': False}
        seen = []
        def response(**params):
            seen.append(params)
            result = fixture.response(reasoning='visible reasoning').model_dump()
            result['id'] = 'distinct-response-' + str(len(seen))
            if len(seen) <= 2:
                result['choices'][0]['finish_reason'] = 'length'
                result['choices'][0]['message']['content'] = ''
                result['usage']['completion_tokens'] = 32768
            return type(fixture.response()).model_validate(result)
        fixture.client.chat.completions.create.side_effect = response
        with patch.object(cc, 'check_openrouter_funds', return_value={'status': 'available'}), \
             patch('radle_reasoning_ceiling.public_catalog', return_value={
                 'vendor/any-model': {'supported_efforts': ['max', 'xhigh', 'high']}}):
            with self.assertRaisesRegex(RuntimeError, 'unresolved outcomes'):
                fixture.run_collection(test_limit=1, max_attempts=1, max_output_tokens=32768)
            fixture.run_collection(test_limit=1, max_attempts=1, max_output_tokens=32768,
                                   repair_once=True, resume_blocked=True)
            authorization = dict(id='same-test-budget', max_pairs=1, attempts_per_pair=2,
                                 spacing_seconds=60, include_uncertain=True,
                                 include_quota=True, include_exhausted=True)
            fixture.run_collection(test_limit=1, max_attempts=1, max_output_tokens=32768,
                                   retry_authorization=authorization, resume_blocked=True)
            fixture.run_collection(test_limit=1, max_attempts=1, max_output_tokens=32768,
                                   retry_authorization=authorization, resume_blocked=True)
        self.assertEqual([p['extra_body']['reasoning']['effort'] for p in seen], ['max', 'max', 'xhigh'])
        self.assertTrue(all(p['max_tokens'] == 32768 for p in seen))
        self.assertEqual(fixture.models[0]['extra']['reasoning']['effort'], 'max')
        row = pd.read_csv(fixture.output).iloc[0]
        self.assertEqual(row['Reasoning_Effort_Requested_any_model'], 'xhigh')
        self.assertEqual(json.loads(row['Reasoning_Retry_Metadata_any_model'])['ceiling_hits_before'], 2)


if __name__ == '__main__':
    unittest.main()
