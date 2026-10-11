import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import radle_job_queue as q
from radle_journal_recovery import recover, sha


class RoundThreeTests(unittest.TestCase):
    def test_round3_once_and_checkpoint_recovery_preserves_authority(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            jobs = [q.Job('1', 'model', {})]
            seen = []
            def call(job, attempt):
                seen.append(attempt)
                return q.Outcome('retry', {})
            q.run(jobs, call, folder, max_attempts=2)
            for number in (1, 2, 3, 3):
                result = q.run(jobs, call, folder, max_attempts=2,
                               repair_once=True, repair_round=number)
            self.assertEqual(seen, [1, 2, 3, 4, 5])
            journal = path / 'events.jsonl'
            manifest = json.loads(journal.read_bytes().splitlines()[0])
            csv = path / 'results.csv'
            csv.write_text('Master_Case_ID,Diagnosis_model,Raw_Response_model\n1,,\n')
            checkpoint = path / 'checkpoint.json'
            checkpoint.write_text(json.dumps(dict(csv_sha256=sha(csv), states={
                jobs[0].key: dict(status='failed', attempts=5)})))
            # A duplicated result reproduces the production replay failure.
            last_result = next(e for e in reversed([json.loads(x) for x in journal.read_bytes().splitlines()])
                               if e.get('type') == 'result')
            q.append(journal, last_result)
            with self.assertRaisesRegex(ValueError, 'Result without'):
                q.replay(journal, manifest)
            states = recover(q, journal, manifest, csv, checkpoint)
            self.assertEqual(states[jobs[0].key]['repair_round'], 3)
            self.assertEqual(q.replay(journal, manifest), states)
            q.run(jobs, lambda *_: self.fail('round3 repeated'), folder,
                  max_attempts=2, repair_once=True, repair_round=3)

    def test_round3_holds_nonretry_outcomes(self):
        for outcome in ('uncertain', 'rejected', 'quota', 'blocked', 'success', 'flagged'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as folder:
                jobs = [q.Job('1', 'model', {})]
                q.run(jobs, lambda *_: q.Outcome('terminal', {}), folder, max_attempts=2)
                q.run(jobs, lambda *_: q.Outcome('retry', {}), folder, max_attempts=2, repair_once=True)
                q.run(jobs, lambda *_: q.Outcome(outcome, {}), folder, max_attempts=2,
                      repair_once=True, repair_round=2)
                result = q.run(jobs, lambda *_: self.fail('held pair resent'), folder,
                               max_attempts=2, repair_once=True, repair_round=3, resume_blocked=True)
                self.assertEqual(result['calls'], 0)
