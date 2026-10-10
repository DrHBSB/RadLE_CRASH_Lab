import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import radle_job_queue as q


class RoundTwoTests(unittest.TestCase):
    def test_bounded_rounds_and_zero_call_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs = [q.Job('1', 'model', {})]
            seen = []
            def call(job, attempt):
                seen.append(attempt)
                return q.Outcome('retry', {})
            q.run(jobs, call, folder, max_attempts=2)
            q.run(jobs, call, folder, max_attempts=2, repair_once=True)
            result = q.run(jobs, call, folder, max_attempts=2, repair_once=True, repair_round=2)
            self.assertEqual(seen, [1, 2, 3, 4])
            self.assertEqual(next(iter(result['states'].values()))['repair_round'], 2)
            q.run(jobs, call, folder, max_attempts=2, repair_once=True, repair_round=2)
            q.run(jobs, call, folder, max_attempts=2, repair_once=True)
            self.assertEqual(seen, [1, 2, 3, 4])

    def test_held_repair_outcomes_never_retried(self):
        for outcome in ['uncertain', 'rejected', 'quota', 'blocked', 'success', 'flagged']:
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as folder:
                jobs = [q.Job('1', 'model', {})]
                q.run(jobs, lambda *_: q.Outcome('terminal', {}), folder, max_attempts=2)
                q.run(jobs, lambda *_: q.Outcome(outcome, {}), folder, max_attempts=2, repair_once=True)
                result = q.run(jobs, lambda *_: self.fail('held answer resent'), folder,
                               max_attempts=2, repair_once=True, repair_round=2, resume_blocked=True)
                self.assertEqual(result['calls'], 0)

    def test_interrupted_round2_is_not_resent(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs = [q.Job('1', 'model', {})]
            q.run(jobs, lambda *_: q.Outcome('terminal', {}), folder, max_attempts=2)
            result = q.run(jobs, lambda *_: q.Outcome('retry', {}), folder, max_attempts=2, repair_once=True)
            key = next(iter(result['states']))
            journal = Path(folder) / 'events.jsonl'
            q.append(journal, {'type': 'repair_round2_authorized', 'key': key, 'attempt': 3,
                               'authorization': '20261010-user-round2'})
            q.append(journal, {'type': 'start', 'key': key, 'attempt': 3})
            result = q.run(jobs, lambda *_: self.fail('uncertain repair resent'), folder,
                           max_attempts=2, repair_once=True, repair_round=2)
            self.assertEqual(result['calls'], 0)
            self.assertEqual(result['states'][key]['value']['repair_outcome'], 'uncertain')

    def test_unsupported_round_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                q.run([], lambda *_: None, folder, repair_round=3)

    def test_durable_grant_resumes_once_before_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs = [q.Job('1', 'model', {})]
            q.run(jobs, lambda *_: q.Outcome('terminal', {}), folder, max_attempts=2)
            result = q.run(jobs, lambda *_: q.Outcome('retry', {}), folder, max_attempts=2, repair_once=True)
            key = next(iter(result['states']))
            q.append(Path(folder) / 'events.jsonl', {'type': 'repair_round2_authorized',
                     'key': key, 'attempt': 3, 'authorization': '20261010-user-round2'})
            seen = []
            def call(job, attempt):
                seen.append(attempt)
                return q.Outcome('success', {})
            q.run(jobs, call, folder, max_attempts=2, repair_once=True, repair_round=2)
            q.run(jobs, call, folder, max_attempts=2, repair_once=True, repair_round=2)
            self.assertEqual(seen, [3])


if __name__ == '__main__':
    unittest.main()
