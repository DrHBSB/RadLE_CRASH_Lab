import json
import csv
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import radle_job_queue as q
import radle_retry_policy as policy
from radle_journal_recovery import repair_grants


class RetryPolicyTests(unittest.TestCase):
    def settings(self, ident='test-pass'):
        return dict(id=ident, max_pairs=10, attempts_per_pair=2, spacing_seconds=60,
                    include_uncertain=True, include_quota=True, include_exhausted=True)

    def seed(self, folder, status='terminal', value=None):
        jobs = [q.Job('1', 'model', {})]
        result = q.run(jobs, lambda *_: q.Outcome(status, value or {}), folder, max_attempts=1)
        return jobs, result

    def run_pass(self, jobs, folder, call, ident='test-pass'):
        return q.run(jobs, call, folder, max_attempts=1, resume_blocked=True,
                     retry_authorization=self.settings(ident))

    def test_two_spaced_attempts_then_zero_on_rerun(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs, _ = self.seed(folder)
            seen = []
            def call(job, attempt):
                seen.append(attempt)
                return q.Outcome('terminal', {})
            clock_start = int(time.time()) + 100
            with patch.object(q.time, 'time', side_effect=range(clock_start, clock_start + 100000, 70)):
                result = self.run_pass(jobs, folder, call)
            self.assertEqual(seen, [2, 3])
            state = next(iter(result['states'].values()))
            self.assertEqual(state['attempts'], 3)
            self.assertGreaterEqual(state['ready_at'], 100060)
            self.run_pass(jobs, folder, lambda *_: self.fail('repeated grant'))

    def test_success_stops_second_attempt_and_is_protected(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs, _ = self.seed(folder)
            result = self.run_pass(jobs, folder, lambda *_: q.Outcome('success', {}))
            self.assertEqual(result['calls'], 1)
            self.run_pass(jobs, folder, lambda *_: self.fail('saved response resent'), 'other-pass')

    def test_new_unknown_quota_rejection_or_block_stops_pair(self):
        for status in ['uncertain', 'quota', 'blocked', 'rejected']:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                jobs, _ = self.seed(folder)
                result = self.run_pass(jobs, folder, lambda *_: q.Outcome(status, {}))
                self.assertEqual(result['calls'], 1)
                self.run_pass(jobs, folder, lambda *_: self.fail('held outcome resent'))

    def test_old_unknown_and_quota_are_explicitly_eligible(self):
        for status in ['uncertain', 'quota', 'terminal']:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                jobs, _ = self.seed(folder, status, {'remote_outcome_unknown': status == 'uncertain'})
                result = self.run_pass(jobs, folder, lambda *_: q.Outcome('success', {}))
                self.assertEqual(result['calls'], 1)

    def test_refusal_flag_and_block_are_protected(self):
        for status in ['rejected', 'flagged', 'blocked', 'success']:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                jobs, _ = self.seed(folder, status)
                self.run_pass(jobs, folder, lambda *_: self.fail('protected pair resent'))

    def test_policy_bound_and_prior_fingerprint_fail_closed(self):
        state = dict(status='terminal', attempts=2, value={})
        event = policy.event_for('key', state, self.settings())
        state['attempts'] = 3
        with self.assertRaises(ValueError):
            policy.apply(state, event)
        with tempfile.TemporaryDirectory() as folder:
            jobs, _ = self.seed(folder)
            bad = self.settings(); bad['attempts_per_pair'] = 3
            with self.assertRaises(ValueError):
                q.run(jobs, lambda *_: self.fail(), folder, resume_blocked=True, retry_authorization=bad)

    def test_archive_grants_preserve_generic_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs, _ = self.seed(folder)
            result = self.run_pass(jobs, folder, lambda *_: q.Outcome('success', {}))
            journal = Path(folder) / 'events.jsonl'
            data = journal.read_bytes(); manifest = json.loads(data.splitlines()[0])
            grants = repair_grants(data, manifest, journal)
            grant = next(iter(grants.values()))
            self.assertEqual(grant['repair_attempt'], 3)
            self.assertEqual(grant['retry_authorizations'], ['test-pass'])
            self.assertEqual(q.replay(journal, manifest), result['states'])

    def test_other_pair_runs_while_first_pair_cools_down(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs = [q.Job(str(i), 'model', {}) for i in (1, 2)]
            q.run(jobs, lambda *_: q.Outcome('terminal', {}), folder, max_attempts=1)
            seen = []
            def call(job, attempt):
                seen.append((job.case, attempt))
                return q.Outcome('terminal', {})
            clock_start = int(time.time()) + 100
            # Clock advances deterministically while real code enforces60second ready_at.
            with patch.object(q.time, 'time', side_effect=range(clock_start, clock_start + 100000, 70)):
                self.run_pass(jobs, folder, call)
            self.assertEqual(seen[:2], [('1', 2), ('2', 2)])
            self.assertEqual(len(seen), 4)

    def test_damaged_journal_recovery_retains_pass_and_never_repeats(self):
        from radle_journal_recovery import recover, sha
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            jobs, _ = self.seed(folder)
            result = self.run_pass(jobs, folder, lambda *_: q.Outcome('success', {}))
            journal = folder / 'events.jsonl'
            manifest = json.loads(journal.read_bytes().splitlines()[0])
            output = folder / 'results.csv'
            with output.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=['Master_Case_ID', 'Diagnosis_model', 'Raw_Response_model'])
                writer.writeheader(); writer.writerow(dict(Master_Case_ID='1', Diagnosis_model='saved', Raw_Response_model='answer'))
            checkpoint = folder / 'checkpoint.json'
            checkpoint.write_text(json.dumps(dict(csv_sha256=sha(output), states=result['states'])))
            with journal.open('ab') as stream:
                stream.write(b'corrupt line\n')
            restored = recover(q, journal, manifest, output, checkpoint)
            self.assertEqual(next(iter(restored.values()))['retry_authorizations'], ['test-pass'])
            self.run_pass(jobs, folder, lambda *_: self.fail('recovered saved pair resent'))

    def test_pending_exhausted_and_max_pair_limit(self):
        state = dict(status='pending', attempts=2, value={})
        event = policy.event_for('key', state, self.settings())
        self.assertEqual(event['attempt'], 4)
        with tempfile.TemporaryDirectory() as folder:
            jobs = [q.Job(str(i), 'model', {}) for i in (1, 2)]
            q.run(jobs, lambda *_: q.Outcome('terminal', {}), folder, max_attempts=1)
            settings = self.settings(); settings['max_pairs'] = 1
            with self.assertRaisesRegex(ValueError, 'maximum pair count'):
                q.run(jobs, lambda *_: self.fail(), folder, max_attempts=1,
                      resume_blocked=True, retry_authorization=settings)

    def test_collector_billing_and_capture_wiring(self):
        import contextlib
        import io
        import test_concurrent_collection as fixtures
        import radle_concurrent_collection as collector
        fixture = fixtures.IntegrationTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        response = fixture.response()
        response.choices[0].message.content = ''
        fixture.client.chat.completions.create.side_effect = lambda **_: response
        with contextlib.redirect_stdout(io.StringIO()):
            fixture.run_collection(max_attempts=1, concurrency=1, allow_partial_result=True)
        fixture.client.chat.completions.create.reset_mock()
        with patch.object(collector, 'check_openrouter_funds', return_value={'status': 'exhausted'}), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'billing check'):
                fixture.run_collection(max_attempts=1, concurrency=1, resume_blocked=True,
                                       allow_partial_result=True, retry_authorization=self.settings())
        fixture.client.chat.completions.create.assert_not_called()
        fixture.client.chat.completions.create.side_effect = lambda **_: fixture.response()
        with patch.object(collector, 'check_openrouter_funds', return_value={'status': 'available'}), contextlib.redirect_stdout(io.StringIO()):
            fixture.run_collection(max_attempts=1, concurrency=1, resume_blocked=True,
                                   allow_partial_result=True, retry_authorization=self.settings())
        self.assertEqual(fixture.client.chat.completions.create.call_count, 3)
        artifacts = list(Path(str(fixture.output) + '.concurrent/attempt_artifacts').glob('*.response_received.*.json'))
        self.assertEqual(len(artifacts), 6)

    def test_legacy_first_repair_can_enter_generic_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs, _ = self.seed(folder)
            q.run(jobs, lambda *_: q.Outcome('terminal', {}), folder, max_attempts=1, repair_once=True)
            self.run_pass(jobs, folder, lambda *_: q.Outcome('success', {}))
            journal = Path(folder) / 'events.jsonl'
            data = journal.read_bytes(); manifest = json.loads(data.splitlines()[0])
            self.assertEqual(next(iter(repair_grants(data, manifest, journal).values()))['retry_authorizations'], ['test-pass'])


if __name__ == '__main__':
    unittest.main()
