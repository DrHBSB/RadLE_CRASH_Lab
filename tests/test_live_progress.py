import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import radle_concurrent_collection as cc
import radle_job_queue as q


class Handle:
    def __init__(self):
        self.updates = []

    def update(self, data, **kwargs):
        self.updates.append(data['text/plain'])


class LiveProgressTests(unittest.TestCase):
    def fixture(self, publisher):
        models = [{'name': 'model_a'}, {'name': 'model_b'}]
        jobs = [q.Job('2', 'model_a', {}), q.Job('3', 'model_a', {}), q.Job('3', 'model_b', {})]
        by_case = {'1': [], '2': [jobs[0].key], '3': [j.key for j in jobs[1:]]}
        with patch.object(cc, 'notebook_display', return_value=publisher):
            ui = cc.LiveProgress(models, list(by_case), jobs, by_case, 2, 3, '/absent/checkpoint.json')
        states = {j.key: {'status': 'pending', 'attempts': 0, 'ready_at': 0, 'value': {}} for j in jobs}
        return ui, jobs, states

    def test_same_model_parallel_jobs_and_correct_counts(self):
        handle = Handle()
        ui, jobs, states = self.fixture(lambda *a, **kw: handle)
        for job in jobs[:2]:
            states[job.key].update(status='uncertain', attempts=1)
            ui.update('started', job.key, states, [j.key for j in jobs[:2]])
        states[jobs[2].key]['status'] = 'uncertain'
        text = ui.render()
        self.assertIn('Answers saved  3 / 6', text)
        self.assertIn('Cases complete 1 / 3', text)
        self.assertIn('Requests active 2 / 2', text)
        self.assertIn('Case 2 ·', text)
        self.assertIn('Case 3 ·', text)
        self.assertIn('1 need review', text)
        self.assertIn('IST', text)
        self.assertNotIn('3 held', text)

    def test_real_ipython_uses_one_display_id_then_updates(self):
        from IPython.core.interactiveshell import InteractiveShell
        from IPython.display import display
        shell = InteractiveShell.instance()
        published = []
        ui, jobs, states = self.fixture(display)
        with patch.object(shell.display_pub, 'publish', side_effect=lambda **kw: published.append(kw)):
            self.assertTrue(ui.update('resumed', None, states, []))
            self.assertTrue(ui.update('heartbeat', None, states, []))
            self.assertTrue(ui.saved_backup('/tmp/results_BACKUP_0241.csv', '2026-09-08T07:28:00+00:00'))
        self.assertEqual(len(published), 3)
        ids = [p['transient']['display_id'] for p in published]
        self.assertEqual(len(set(ids)), 1)
        self.assertFalse(published[0].get('update', False))
        self.assertTrue(all(p['update'] for p in published[1:]))
        self.assertIn('results_BACKUP_0241.csv at 12:58:00 IST', published[-1]['data']['text/plain'])

    def test_recent_events_bounded_and_timers_advance(self):
        ui, jobs, states = self.fixture(lambda *a, **kw: Handle())
        states[jobs[0].key].update(status='uncertain', attempts=1)
        with patch.object(cc.time, 'monotonic', return_value=100):
            ui.update('started', jobs[0].key, states, [jobs[0].key])
        with patch.object(cc.time, 'monotonic', return_value=115):
            self.assertIn('Case 2 · 15s', ui.render())
        for n in range(8):
            ui.record(f'event {n}')
        self.assertEqual(len(ui.events), 5)
        self.assertNotIn('event 2', ui.render())
        self.assertIn('event 7', ui.render())
        states[jobs[0].key].update(status='flagged', value={'reason': 'missing_readable_reasoning'})
        ui.update('saved', jobs[0].key, states, [])
        self.assertIn('missing readable reasoning', ui.render())
        self.assertIn('Answers saved  4 / 6', ui.render())

    def test_broken_display_does_not_prevent_durable_collection(self):
        def broken(*a, **kw):
            raise RuntimeError('publisher disconnected')
        ui, jobs, _ = self.fixture(broken)
        calls = []
        def call(job, attempt):
            calls.append(job.key)
            return q.Outcome('success')
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()) as output:
            result = q.run(jobs, call, folder, on_event=ui.update)
            records = [json.loads(line) for line in Path(folder, 'events.jsonl').read_text().splitlines()]
        self.assertTrue(result['complete'])
        self.assertEqual(len(calls), 3)
        self.assertEqual(sum(r.get('type') == 'result' for r in records), 3)
        self.assertEqual(output.getvalue().count('Live display unavailable'), 1)
        self.assertIsNone(ui.publisher)

    def test_no_notebook_falls_back_without_error(self):
        ui, _, states = self.fixture(None)
        self.assertFalse(ui.update('resumed', None, states, []))
        self.assertFalse(ui.saved_backup('/tmp/a.csv', '2026-09-08T07:28:00+00:00'))

    def test_heartbeat_during_retry_delay_without_active_requests(self):
        job = q.Job('1', 'any', {})
        observed = []
        def call(job, attempt):
            return q.Outcome('retry', retry_after=.12) if attempt == 1 else q.Outcome('success')
        def progress(event, key, states, active):
            if event == 'heartbeat':
                observed.append((len(active), states[job.key]['status']))
        with tempfile.TemporaryDirectory() as folder:
            result = q.run([job], call, folder, on_event=progress, heartbeat_seconds=.01)
        self.assertTrue(result['complete'])
        self.assertIn((0, 'retry'), observed)


if __name__ == '__main__':
    unittest.main()
