import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import radle_job_queue as q
import radle_concurrent_collection as cc
import radle_benchmark as rb
import test_concurrent_collection as fixtures


class PacingTests(unittest.TestCase):
    def test_rate_limit_paces_other_cases_and_replays_without_more_calls(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs = [q.Job('1', 'a', {}), q.Job('2', 'a', {}), q.Job('3', 'b', {})]
            starts = {}
            limited_at = []
            def call(job, attempt):
                starts[job.case] = time.time()
                if job.case == '1':
                    limited_at.append(time.time())
                    return q.Outcome('retry', {'http_status': 429}, .08)
                return q.Outcome('success', {})
            result = q.run(jobs, call, folder, concurrency=1, max_attempts=1)
            self.assertGreaterEqual(starts['2'] - limited_at[0], .07)
            self.assertLess(starts['3'], starts['2'])
            self.assertEqual(result['calls'], 3)
            self.assertEqual(q.run(jobs, lambda *_: self.fail('resent'), folder, max_attempts=1)['calls'], 0)

    def test_failed_repair_preserves_model_cooldown(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs = [q.Job(str(i), 'a', {}) for i in (1, 2)]
            q.run(jobs, lambda *_: q.Outcome('terminal'), folder, max_attempts=1)
            starts = []
            def call(*_):
                starts.append(time.time())
                return q.Outcome('retry', {'http_status': 429}, .06)
            result = q.run(jobs, call, folder, concurrency=1, max_attempts=1, repair_once=True)
            self.assertGreaterEqual(starts[1] - starts[0], .05)
            self.assertTrue(all(s['status'] == 'failed' for s in result['states'].values()))
            self.assertTrue(q.model_pacing(result['states'])['a']['limited'])

    def test_replay_keeps_remaining_cooldown(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs = [q.Job('1', 'a', {}), q.Job('2', 'a', {})]
            q.run(jobs, lambda *_: q.Outcome('retry', {'http_status': 429}, .1), folder,
                  max_attempts=1, selected_keys={jobs[0].key})
            calls = []
            before = time.time()
            q.run(jobs, lambda *_: calls.append(time.time()) or q.Outcome('success'), folder, max_attempts=1)
            self.assertGreaterEqual(calls[0] - before, .07)

    def test_retry_after_formats_and_invalid_values(self):
        self.assertEqual(cc.retry_delay('120', 1, now=0), 120)
        self.assertEqual(cc.retry_delay('Thu, 01 Jan 1970 00:02:00 GMT', 1, now=0), 120)
        for value in (None, 'bad', 'nan', '-1', 'inf'):
            self.assertEqual(cc.retry_delay(value, 1, now=0), 60)

    def test_model_stays_single_slot_after_rate_limit_until_success(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs = [q.Job(str(i), 'a', {}) for i in range(4)]
            q.run(jobs, lambda *_: q.Outcome('retry', {'http_status': 429}, .02), folder,
                  max_attempts=1, selected_keys={jobs[0].key})
            active = 0
            maximum = 0
            lock = threading.Lock()
            def call(*_):
                nonlocal active, maximum
                with lock:
                    active += 1
                    maximum = max(maximum, active)
                time.sleep(.015)
                with lock:
                    active -= 1
                return q.Outcome('terminal')
            q.run(jobs, call, folder, max_attempts=1, concurrency=3)
            self.assertEqual(maximum, 1)

    def test_exhausted_display_and_historical_hold(self):
        states = {'["1","a"]': dict(status='pending', attempts=2, value={}),
                  '["2","a"]': dict(status='quota', attempts=2, value={})}
        self.assertEqual(cc.waiting_counts(states, (), 2), (0, 1))
        with patch.object(cc, 'notebook_display', return_value=None):
            ui = cc.LiveProgress([{'name':'a'}], ['1','2'], [q.Job('1','a',{}),q.Job('2','a',{})],
                                 {'1':['["1","a"]'],'2':['["2","a"]']}, 3, 2, '/absent')
        ui.publisher = lambda *_a, **_k: type('Handle', (), {'update': lambda *_a, **_k: None})()
        ui.update('heartbeat', None, states, ())
        self.assertNotIn('PAUSING', ui.render())
        self.assertIn('1 exhausted', ui.render())


class PartialAuditTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.IntegrationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_partial_return_and_read_only_audit_never_resend(self):
        f = self.fixture
        def wrapped(jobs, call, folder, **options):
            return real_run(jobs, lambda job, attempt: q.Outcome('rejected') if job.case == '1' else call(job, attempt), folder, **options)
        real_run = q.run
        with patch.object(q, 'run', side_effect=wrapped), contextlib.redirect_stdout(io.StringIO()):
            frame = f.run_collection(max_attempts=2, allow_partial_result=True)
        self.assertEqual(len(frame.attrs['unresolved_pairs']), 1)
        before = f.output.read_bytes()
        journal = Path(str(f.output) + '.concurrent/queue/events.jsonl')
        journal_before = journal.read_bytes()
        f.client.chat.completions.create.reset_mock()
        result = rb.audit_saved_collection(f.output, f.models, 3, 16384)
        self.assertEqual(result['inference_calls'], 0)
        self.assertIsNone(result['final_manifest'])
        self.assertEqual(len(result['unresolved_pairs']), 1)
        f.client.chat.completions.create.assert_not_called()
        self.assertEqual(before, f.output.read_bytes())
        self.assertEqual(journal_before, journal.read_bytes())
        with self.assertRaisesRegex(RuntimeError, 'unresolved outcomes'), contextlib.redirect_stdout(io.StringIO()):
            f.run_collection(max_attempts=2)

    def test_audit_refuses_lock_and_hash_mismatch(self):
        f = self.fixture
        with contextlib.redirect_stdout(io.StringIO()):
            f.run_collection(max_attempts=2)
        lock = Path(str(f.output) + '.concurrent/writer.lock')
        lock.write_text('123')
        with self.assertRaisesRegex(RuntimeError, 'writer lock'):
            rb.audit_saved_collection(f.output, f.models, 3, 16384)
        lock.unlink()
        f.output.write_bytes(f.output.read_bytes() + b'\n')
        with self.assertRaisesRegex(RuntimeError, 'hash mismatch'):
            rb.audit_saved_collection(f.output, f.models, 3, 16384)

    def test_audit_workflow_cannot_promote(self):
        with self.assertRaisesRegex(RuntimeError, 'cannot promote'):
            rb.run_autonomous_openrouter_workflow(None, '.', {}, [], 3, {}, {}, 'fixture', audit_only=True, promote_private=True)

    def test_workflow_audits_partial_result_without_clean_gate(self):
        f = self.fixture
        import pandas as pd
        frame = pd.DataFrame({'Master_Case_ID':['1']})
        frame.attrs.update(unresolved_pairs=[{'status':'rejected'}], failed_pairs=[])
        with patch.object(rb, 'run_benchmark', return_value=frame) as collect, \
                patch.object(rb, 'audit_benchmark_output', return_value={'fixture':True}) as audit, \
                patch.object(rb, 'assert_clean_benchmark_audit') as gate, \
                patch.object(rb, 'promote_final_results') as promote:
            result = rb.run_autonomous_openrouter_workflow(None, f.root,
                {'raw_results_csv':str(f.output),'master_images_folder':str(f.images),'raw_backup_dir':str(f.root)},
                f.models, 3, {}, {}, 'fixture', smoke_first=False)
        self.assertEqual(result['status'], 'completed_with_unresolved')
        self.assertTrue(collect.call_args.kwargs['allow_partial_result'])
        audit.assert_called_once()
        gate.assert_not_called()
        promote.assert_not_called()


if __name__ == '__main__':
    unittest.main()
