import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import radle_job_queue as queue
from radle_journal_recovery import recover, sha


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.key = queue.Job('1', 'model', {}).key
        self.manifest = dict(schema=1, max_attempts=2, contract={}, initial_attempts={},
                             jobs={self.key: hashlib.sha256(queue.encode(dict(case='1', model='model', request={})).encode()).hexdigest()})
        self.journal = self.folder / 'events.jsonl'
        self.csv = self.folder / 'results.csv'
        with self.csv.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['Master_Case_ID', 'Diagnosis_model', 'Raw_Response_model'])
            writer.writeheader()
            writer.writerow(dict(Master_Case_ID='1', Diagnosis_model='saved', Raw_Response_model='answer'))
        self.checkpoint = self.folder / 'checkpoint.json'
        self.write_checkpoint()
        self.original = (queue.encode(self.manifest) + '\ncorrupt fragment\n').encode()
        self.journal.write_bytes(self.original)

    def write_checkpoint(self, status='success', attempts=2):
        self.checkpoint.write_text(json.dumps(dict(csv_sha256=sha(self.csv), states={
            self.key: dict(status=status, attempts=attempts)})))

    def recover(self):
        return recover(queue, self.journal, self.manifest, self.csv, self.checkpoint)

    def test_recovery_preserves_answer_budget_and_original(self):
        states = self.recover()
        self.assertEqual(states[self.key]['attempts'], 2)
        self.assertEqual(states[self.key]['value']['fields']['Raw_Response_model'], 'answer')
        self.assertEqual(queue.replay(self.journal, self.manifest), states)
        archives = list(self.folder.glob('events.original.*.jsonl'))
        self.assertEqual(archives[0].read_bytes(), self.original)
        self.assertEqual(len(archives), 1)
        calls = []
        result = queue.run([queue.Job('1', 'model', {})], lambda *args: calls.append(args),
                           self.folder, max_attempts=2, contract={})
        self.assertEqual(calls, [])
        self.assertEqual(result['states'][self.key]['attempts'], 2)

    def test_hash_mismatch_does_not_modify_journal(self):
        self.csv.write_text('changed')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.recover()
        self.assertEqual(self.journal.read_bytes(), self.original)

    def test_repair_authority_survives_repeated_corruption(self):
        self.journal.unlink()
        jobs = [queue.Job('1', 'model', {})]
        queue.run(jobs, lambda *_: queue.Outcome('terminal', {}), self.folder,
                  max_attempts=2, contract={})
        result = queue.run(jobs, lambda *_: queue.Outcome('retry', {}), self.folder,
                           max_attempts=2, contract={}, repair_once=True)
        self.write_checkpoint('failed', 2)
        with self.journal.open('ab') as handle:
            handle.write(b'corrupted\n')
        states = self.recover()
        self.assertEqual(states[self.key]['repair_attempt'], 2)
        self.assertEqual(states[self.key]['value']['repair_outcome'], 'retry')
        seen = []
        def call(job, attempt):
            seen.append(attempt)
            return queue.Outcome('retry', {})
        queue.run(jobs, call, self.folder, max_attempts=2, contract={}, repair_once=True, repair_round=2)
        self.assertEqual(seen, [3])
        self.write_checkpoint('failed', 3)
        with self.journal.open('ab') as handle:
            handle.write(b'corrupted again\n')
        states = self.recover()
        self.assertEqual(states[self.key]['repair_round'], 2)
        self.assertEqual(states[self.key]['repair_attempt'], 3)
        queue.run(jobs, lambda *_: self.fail('repair sent twice'), self.folder,
                  max_attempts=2, contract={}, repair_once=True, repair_round=2)

    def test_extra_attempt_without_grant_is_refused(self):
        self.write_checkpoint('failed', 3)
        with self.assertRaisesRegex(ValueError, 'invalid checkpoint state'):
            self.recover()
        self.assertEqual(self.journal.read_bytes(), self.original)

    def test_unproven_grant_is_refused(self):
        queue.append(self.journal, dict(type='repair_authorized', key=self.key, attempt=3))
        self.write_checkpoint('failed', 3)
        with self.assertRaisesRegex(ValueError, 'unproven repair authorization'):
            self.recover()

    def test_consumed_repair_with_missing_outcome_stays_held(self):
        queue.append(self.journal, dict(type='result', key=self.key, attempt=2,
                     status='terminal', value={}, ready_at=0))
        queue.append(self.journal, dict(type='repair_authorized', key=self.key, attempt=3))
        self.write_checkpoint('failed', 3)
        states = self.recover()
        self.assertTrue(states[self.key]['value']['remote_outcome_unknown'])
        queue.run([queue.Job('1', 'model', {})], lambda *_: self.fail('unknown outcome resent'),
                  self.folder, max_attempts=2, contract={}, repair_once=True, repair_round=2)

    def test_recover_previously_recovered_log(self):
        self.recover()
        first = self.journal.read_bytes()
        with self.journal.open('ab') as handle:
            handle.write(b'broken fragment\n')
        damaged = self.journal.read_bytes()
        restored = self.recover()
        self.assertEqual(restored[self.key]['attempts'], 2)
        self.assertEqual(queue.replay(self.journal, self.manifest), restored)
        self.assertIn(damaged, [p.read_bytes() for p in self.folder.glob('events.original.*.jsonl')])
        self.assertNotEqual(first, damaged)

    def test_recovery_refuses_damaged_prior_archive(self):
        self.recover()
        next(self.folder.glob('events.original.*.jsonl')).write_bytes(b'tampered')
        with self.journal.open('ab') as handle:
            handle.write(b'broken fragment\n')
        before = self.journal.read_bytes()
        with self.assertRaisesRegex(ValueError, 'prior archive hash'):
            self.recover()
        self.assertEqual(self.journal.read_bytes(), before)

    def test_later_attempt_refuses_stale_checkpoint(self):
        queue.append(self.journal, dict(type='start', key=self.key, attempt=3))
        before = self.journal.read_bytes()
        with self.assertRaisesRegex(ValueError, 'exceeds checkpoint'):
            self.recover()
        self.assertEqual(self.journal.read_bytes(), before)

    def test_identity_conflict_refused(self):
        self.manifest['max_attempts'] = 3
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            self.recover()

    def test_result_conflict_refused(self):
        queue.append(self.journal, dict(type='result', key=self.key, attempt=2,
                                      status='retry', value={}, ready_at=0))
        with self.assertRaisesRegex(ValueError, 'status conflict'):
            self.recover()

    def test_out_of_order_valid_events_corruption_and_missing_starts(self):
        queue.append(self.journal, dict(type='result', key=self.key, attempt=2,
                                      status='success', value={'reason': 'kept'}, ready_at=0))
        queue.append(self.journal, dict(type='start', key=self.key, attempt=2))
        self.assertEqual(self.recover()[self.key]['value']['reason'], 'kept')

    def test_uncertain_stays_held(self):
        self.write_checkpoint('uncertain', 1)
        calls = []
        result = queue.run([queue.Job('1', 'model', {})], lambda *args: calls.append(args),
                           self.folder, max_attempts=2, contract={}, resume_blocked=True,
                           journal_recovery=lambda path, manifest: recover(
                               queue, path, manifest, self.csv, self.checkpoint))
        self.assertEqual(result['states'][self.key]['status'], 'uncertain')
        self.assertEqual(calls, [])

    def test_retry_uses_only_remaining_attempt(self):
        self.write_checkpoint('retry', 1)
        seen = []
        def call(job, attempt):
            seen.append(attempt)
            return queue.Outcome('terminal')
        queue.run([queue.Job('1', 'model', {})], call, self.folder, max_attempts=2,
                  contract={}, resume_blocked=True,
                  journal_recovery=lambda path, manifest: recover(
                      queue, path, manifest, self.csv, self.checkpoint))
        self.assertEqual(seen, [2])

    def test_missing_answer_refused(self):
        self.csv.write_text('Master_Case_ID,Diagnosis_model,Raw_Response_model\n1,saved,\n')
        self.write_checkpoint()
        with self.assertRaisesRegex(ValueError, 'fields missing'):
            self.recover()
        self.assertEqual(self.journal.read_bytes(), self.original)

    def test_archive_tampering_refused_on_replay(self):
        self.recover()
        next(self.folder.glob('events.original.*.jsonl')).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'archive hash'):
            queue.replay(self.journal, self.manifest)

    def test_long_reasoning_fields_preserved(self):
        reasoning = 'r' * 200000
        self.csv.write_text('Master_Case_ID,Diagnosis_model,Raw_Response_model,Reasoning_model\n'
                            '1,saved,answer,' + reasoning + '\n')
        self.write_checkpoint()
        csv.field_size_limit(131072)
        self.assertEqual(self.recover()[self.key]['value']['fields']['Reasoning_model'], reasoning)


if __name__ == '__main__':
    unittest.main()
