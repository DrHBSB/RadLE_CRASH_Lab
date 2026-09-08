import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

import pandas as pd
from openai.types.chat import ChatCompletion
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import radle_benchmark as rb
import radle_concurrent_collection as cc
import radle_job_queue as q


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.images = self.root / 'images'
        self.images.mkdir()
        for i in range(1, 4):
            Image.new('RGB', (8, 8), 'red').save(self.images / f'{i}.png')
        self.output = self.root / 'results.csv'
        self.models = [{'name': 'any_model', 'id': 'vendor/any-model',
                        'require_readable_reasoning': True,
                        'extra': {'response_format': {'type': 'json_object'}}}]
        self.client = Mock()
        self.client.with_options.return_value = self.client
        self.client.chat.completions.create.side_effect = lambda **_: self.response()

    def response(self, diagnosis='synthetic finding', reasoning=''):
        return ChatCompletion.model_validate({'id': 'fixture', 'object': 'chat.completion',
            'created': 1, 'model': 'vendor/any-model', 'provider': 'Fixture Provider',
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant',
                'content': json.dumps({'diagnosis': diagnosis, 'likert_score': 3}), 'reasoning': reasoning}}],
            'usage': {'prompt_tokens': 20, 'completion_tokens': 40, 'total_tokens': 60}})

    def run_collection(self, **kwargs):
        return cc.collect(rb, client=self.client, image_folder=self.images,
                          output_csv=self.output, models=self.models, **kwargs)

    def test_resume_preserves_historical_fields_and_skips_flags(self):
        index = rb.build_image_index(self.images)
        params = rb.build_api_params(self.models[0], [], rb.MAX_OUTPUT_TOKENS, .01)
        rows = []
        for case in index:
            base = rb.rebuild_base_row(case, index[case])
            base['Historical_answer'] = 'keep\nthis, exactly'
            if case == '1':
                base.update(rb.extract_result(self.response(), 1, params, False, self.models[0]))
            rows.append(base)
        baseline = pd.DataFrame(rows).fillna('')
        baseline.to_csv(self.output, index=False)
        self.run_collection()
        self.assertEqual(self.client.chat.completions.create.call_count, 2)
        final = pd.read_csv(self.output, dtype=str, keep_default_na=False)
        self.assertEqual(final['Historical_answer'].tolist(), ['keep\nthis, exactly'] * 3)
        self.output.write_text('damaged derived file')
        self.run_collection()
        self.assertEqual(self.client.chat.completions.create.call_count, 2)
        pd.testing.assert_frame_equal(final, pd.read_csv(self.output, dtype=str, keep_default_na=False))
        self.client.with_options.assert_called_with(max_retries=0, timeout=600)

    def test_input_drift_refuses_calls(self):
        self.run_collection()
        Image.new('RGB', (8, 8), 'blue').save(self.images / '1.png')
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            self.run_collection()
        self.assertEqual(self.client.chat.completions.create.call_count, 3)

    def test_inherited_budget_is_not_reset(self):
        index = rb.build_image_index(self.images)
        row = rb.rebuild_base_row('1', index['1'])
        row.update(Diagnosis_any_model='PARSE_FAILED', Raw_Response_any_model='',
                   Prompt_Tokens_any_model=20, Total_Tokens_Out_any_model=16384)
        pd.DataFrame([row]).to_csv(self.output, index=False)
        migration = {'baseline_sha256': cc.digest(self.output), 'initial_attempts': {q.encode(['1', 'any_model']): 3}}
        self.client.chat.completions.create.side_effect = lambda **_: self.response('PARSE_FAILED')
        with self.assertRaisesRegex(RuntimeError, 'unresolved outcomes'):
            self.run_collection(test_limit=1, max_attempts=4, migration=migration)
        self.assertEqual(self.client.chat.completions.create.call_count, 1)
        with self.assertRaisesRegex(RuntimeError, 'unresolved outcomes'):
            self.run_collection(test_limit=1, max_attempts=4, migration=migration)
        self.assertEqual(self.client.chat.completions.create.call_count, 1)

    def test_legacy_failure_retained_without_guessing_history(self):
        row = rb.rebuild_base_row('1', rb.build_image_index(self.images)['1'])
        row['Diagnosis_any_model'] = 'PARSE_FAILED'
        pd.DataFrame([row]).to_csv(self.output, index=False)
        self.run_collection()
        self.assertEqual(self.client.chat.completions.create.call_count, 3)
        status = json.loads(Path(str(self.output) + '.concurrent/status.json').read_text())
        self.assertEqual(status['legacy_failures'], [q.encode(['1', 'any_model'])])
        self.assertEqual(status['attempt_budget_scope'], 'journal')
        self.run_collection()
        self.assertEqual(self.client.chat.completions.create.call_count, 3)

    def test_quota_drain_does_not_write_zero_diagnosis(self):
        barrier = threading.Barrier(2)
        lock = threading.Lock()
        counts = 0
        class Quota(Exception):
            status_code = 403
        def call(**kwargs):
            nonlocal counts
            with lock:
                counts += 1
                current = counts
            barrier.wait(2)
            if current == 1:
                raise Quota('Key limit exceeded (total limit)')
            time.sleep(.05)  # Quota is observed before the other call completes.
            return self.response()
        self.client.chat.completions.create.side_effect = call
        with self.assertRaisesRegex(RuntimeError, 'unresolved outcomes'):
            self.run_collection()
        self.assertEqual(counts, 2)
        frame = pd.read_csv(self.output, dtype=str, keep_default_na=False)
        self.assertEqual((frame['Diagnosis_any_model'] == 'synthetic finding').sum(), 1)
        self.assertEqual((frame['Diagnosis_any_model'] == '').sum(), 2)

    def test_existing_run_benchmark_dispatch(self):
        result = rb.run_benchmark(self.client, self.images, self.output, models=self.models, concurrency=2)
        self.assertEqual(len(result), 3)
        self.assertEqual(self.client.chat.completions.create.call_count, 3)

    def test_existing_workflow_defaults_to_concurrency_without_legacy_retry_reset(self):
        paths = rb.build_run_paths(self.root, run_label='fixture')
        paths['master_images_folder'] = str(self.images)
        paths['raw_results_csv'] = str(self.output)
        with patch.object(rb, 'run_repair_cascade_until_clean', side_effect=AssertionError('retry reset')):
            result = rb.run_autonomous_openrouter_workflow(
                client=self.client, dataset_root=self.root, run_paths=paths,
                models=self.models, expected_cases=3,
                expected_returned_model_ids={'any_model': {'vendor/any-model'}},
                expected_providers={'any_model': 'Fixture Provider'},
                run_label='fixture', smoke_first=False, allow_missing_reasoning=True)
        self.assertEqual(len(result['final_df']), 3)
        self.assertEqual(self.client.chat.completions.create.call_count, 3)
        self.assertIsNone(result['final_manifest'])


if __name__ == '__main__':
    unittest.main()
