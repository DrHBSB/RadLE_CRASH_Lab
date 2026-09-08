import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
import warnings
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import radle_job_queue as q
import radle_concurrent_collection as cc
import radle_benchmark as rb


class MonitoringTests(unittest.TestCase):
    def test_user_summary_distinguishes_active_and_review(self):
        states = {}
        by_case = {}
        for case in range(1, 201):
            keys = [q.encode([str(case), str(m)]) for m in range(5)] if case >= 81 else []
            by_case[str(case)] = keys
            states.update({k: {'status': 'pending'} for k in keys})
        legacy = q.encode(['62', '2'])
        states[legacy] = {'status': 'retry'}
        by_case['62'] = [legacy]
        astra, grok = by_case['81'][:2]
        states[astra] = {'status': 'uncertain'}
        states[grok] = {'status': 'success'}
        text = cc.progress_summary(states, [], by_case, 1000, 200)
        self.assertEqual(text, '400/1000 answers collected | 79/200 cases complete | 0 running | 1 retry waiting | 1 need review | 598 queued')
        active = cc.progress_summary(states, [astra], by_case, 1000, 200)
        self.assertIn('1 running', active)
        self.assertIn('0 need review', active)

    def test_exact_output_limit_reason_without_raw_response(self):
        event = {'type': 'response.incomplete', 'response': {
            'status': 'incomplete', 'incomplete_details': {'reason': 'max_output_tokens'},
            'usage': {'output_tokens': 8192}, 'max_output_tokens': 8192,
            'output': [{'text': 'secret clinical text'}]}}
        with self.assertRaises(RuntimeError) as caught:
            rb.collect_openrouter_response_stream([event])
        result = cc.diagnostic(caught.exception)
        self.assertEqual(result['category'], 'output_limit')
        self.assertEqual(result['output_tokens'], 8192)
        self.assertNotIn('secret clinical', json.dumps(result))

    def test_unrecognized_exception_does_not_leak_body_or_key(self):
        result = cc.diagnostic(RuntimeError('Authorization: Bearer sk-secret clinical private text'))
        self.assertNotIn('sk-secret', json.dumps(result))
        self.assertNotIn('clinical private', json.dumps(result))

    def test_heartbeat_and_broken_display_do_not_change_execution(self):
        job = q.Job('1', 'unknown_model', {})
        events = []
        def call(*_):
            time.sleep(.08)
            return q.Outcome('success')
        def report(event, *args):
            events.append(event)
            if event == 'started':
                raise RuntimeError('display failed')
        with tempfile.TemporaryDirectory() as folder, warnings.catch_warnings(record=True) as recorded:
            result = q.run([job], call, folder, on_event=report, heartbeat_seconds=.01)
        self.assertTrue(result['complete'])
        self.assertIn('heartbeat', events)
        self.assertEqual(len(recorded), 1)

    def test_uncertain_job_does_not_stop_other_jobs_or_repeat(self):
        jobs = [q.Job(str(i), 'any', {}) for i in range(3)]
        def call(job, _):
            return q.Outcome('uncertain') if job.case == '0' else q.Outcome('success')
        with tempfile.TemporaryDirectory() as folder:
            first = q.run(jobs, call, folder, concurrency=1)
            self.assertEqual(first['calls'], 3)
            self.assertEqual(first['states'][jobs[1].key]['status'], 'success')
            self.assertFalse(first['paused'])
            second = q.run(jobs, lambda *_: self.fail('duplicate'), folder)
            self.assertEqual(second['calls'], 0)
            self.assertFalse(second['complete'])

    def test_old_code_hash_upgrade_preserves_uncertainty_and_records_version(self):
        job = q.Job('1', 'any', {})
        with tempfile.TemporaryDirectory() as folder:
            old = {'source_sha256': 'v1', 'adapter_sha256': 'a1', 'scheduler_sha256': 's1', 'prompt': 'fixed'}
            q.run([job], lambda *_: q.Outcome('uncertain'), folder, contract=old)
            new = {**old, 'source_sha256': 'v2', 'adapter_sha256': 'a2'}
            resumed = q.run([job], lambda *_: self.fail('duplicate'), folder, contract=new)
            self.assertEqual(resumed['calls'], 0)
            self.assertEqual(resumed['states'][job.key]['status'], 'uncertain')
            log = Path(folder, 'events.jsonl').read_text()
            self.assertIn('"source_sha256":"v2"', log)
            with self.assertRaisesRegex(ValueError, 'identity changed'):
                q.run([job], lambda *_: self.fail(), folder, contract={**new, 'prompt': 'changed'})


if __name__ == '__main__':
    unittest.main()
