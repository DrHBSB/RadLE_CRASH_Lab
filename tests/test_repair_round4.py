import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import radle_job_queue as q
from radle_journal_recovery import recover, sha


class RoundFourTests(unittest.TestCase):
    def test_known_quota_round4_once_and_recovery(self):
        for previous_round in (1, 2, 3):
            with self.subTest(previous_round=previous_round), tempfile.TemporaryDirectory() as folder:
                jobs = [q.Job('1', 'model', {})]
                q.run(jobs, lambda *_: q.Outcome('terminal', {}), folder, max_attempts=2)
                for number in range(1, previous_round + 1):
                    outcome = 'quota' if number == previous_round else 'retry'
                    q.run(jobs, lambda *_: q.Outcome(outcome, {}), folder, max_attempts=2,
                          repair_once=True, repair_round=number)
                seen = []
                def call(job, attempt):
                    seen.append(attempt)
                    return q.Outcome('retry', {})
                result = q.run(jobs, call, folder, max_attempts=2, repair_once=True,
                               repair_round=4, resume_blocked=True)
                self.assertEqual(len(seen), 1)
                q.run(jobs, lambda *_: self.fail('round4 repeated'), folder, max_attempts=2,
                      repair_once=True, repair_round=4, resume_blocked=True)
                path = Path(folder)
                journal = path / 'events.jsonl'
                manifest = json.loads(journal.read_bytes().splitlines()[0])
                csv = path / 'results.csv'
                csv.write_text('Master_Case_ID,Diagnosis_model,Raw_Response_model\n1,,\n')
                checkpoint = path / 'checkpoint.json'
                checkpoint.write_text(json.dumps(dict(csv_sha256=sha(csv), states={
                    jobs[0].key: dict(status='failed', attempts=seen[0])})))
                with journal.open('ab') as handle:
                    handle.write(b'broken\n')
                states = recover(q, journal, manifest, csv, checkpoint)
                self.assertEqual(states[jobs[0].key]['repair_round'], 4)
                self.assertEqual(q.replay(journal, manifest), states)

    def test_saved_rejected_unknown_and_blocked_remain_held(self):
        for outcome in ('success', 'flagged', 'uncertain', 'rejected', 'blocked'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as folder:
                jobs = [q.Job('1', 'model', {})]
                q.run(jobs, lambda *_: q.Outcome('terminal', {}), folder, max_attempts=2)
                q.run(jobs, lambda *_: q.Outcome(outcome, {}), folder,
                      max_attempts=2, repair_once=True)
                result = q.run(jobs, lambda *_: self.fail('held request resent'), folder,
                               max_attempts=2, repair_once=True, repair_round=4, resume_blocked=True)
                self.assertEqual(result['calls'], 0)

    def test_original_exhausted_pending_not_granted(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs = [q.Job('1', 'model', {})]
            q.run(jobs, lambda *_: self.fail('exhausted job resent'), folder,
                  max_attempts=2, initial_attempts={jobs[0].key: 2},
                  repair_once=True, repair_round=4, resume_blocked=True)
