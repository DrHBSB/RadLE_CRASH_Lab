import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import radle_job_queue as s


def jobs(n=6):
    return [s.Job(str(i), f"unseen_model_{i % 3}", {"input_hash": str(i), "effort": "high"})
            for i in range(n)]


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def test_bounded_overlap_single_writer_and_zero_call_resume(self):
        lock = threading.Lock()
        active = peak = 0
        writes = []
        main = threading.get_ident()
        real_append = s.append
        def append(*args):
            writes.append(threading.get_ident())
            return real_append(*args)
        def call(job, attempt):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(.015)
            with lock:
                active -= 1
            return s.Outcome("success", {"case": job.case})
        with patch.object(s, "append", append):
            result = s.run(jobs(15), call, self.folder, concurrency=3)
        self.assertTrue(result["complete"])
        self.assertEqual(peak, 3)
        self.assertEqual(set(writes), {main})
        again = s.run(jobs(15), lambda *_: self.fail("duplicate request"), self.folder)
        self.assertEqual(again["calls"], 0)
        self.assertEqual(result["states"], again["states"])

    def test_slow_request_does_not_create_case_barrier(self):
        slow_started = threading.Event()
        fast_second = threading.Event()
        def call(job, attempt):
            if job.case == "0":
                slow_started.set()
                self.assertTrue(fast_second.wait(2))
            else:
                self.assertTrue(slow_started.wait(2))
                if job.case == "2":
                    fast_second.set()
            return s.Outcome("success")
        self.assertTrue(s.run(jobs(3), call, self.folder)["complete"])
        self.assertTrue(fast_second.is_set())

    def test_retry_budget_survives_restart_and_delay_does_not_hold_slot(self):
        stop = threading.Event()
        def call(job, attempt):
            return s.Outcome("retry", retry_after=.06)
        def checkpoint(states):
            stop.set()
        first = s.run(jobs(1), call, self.folder, stop=stop, checkpoint=checkpoint)
        self.assertEqual(first["calls"], 1)
        ready = next(iter(first["states"].values()))["ready_at"]
        seen = []
        def resumed(job, attempt):
            self.assertGreaterEqual(time.time(), ready)
            seen.append(attempt)
            return s.Outcome("retry")
        second = s.run(jobs(1), resumed, self.folder)
        self.assertEqual(seen, [2, 3])
        self.assertEqual(next(iter(second["states"].values()))["status"], "terminal")
        self.assertEqual(s.run(jobs(1), resumed, self.folder)["calls"], 0)

    def test_retry_backoff_releases_slot(self):
        seen = []
        def call(job, attempt):
            seen.append((job.case, attempt))
            return s.Outcome("retry", retry_after=.05) if job.case == "0" and attempt == 1 else s.Outcome("success")
        s.run(jobs(3), call, self.folder, concurrency=1)
        self.assertEqual(seen, [("0", 1), ("1", 1), ("2", 1), ("0", 2)])

    def test_quota_stops_dispatch_and_drains_success(self):
        both_started = threading.Barrier(2)
        seen = []
        def call(job, attempt):
            seen.append(job.case)
            both_started.wait(2)
            if job.case == "0":
                return s.Outcome("quota", {"http_status": 403})
            time.sleep(.03)
            return s.Outcome("success", {"saved": True})
        result = s.run(jobs(), call, self.folder)
        self.assertEqual(set(seen), {"0", "1"})
        self.assertTrue(result["paused"])
        self.assertEqual(result["states"][jobs()[1].key]["value"], {"saved": True})
        self.assertEqual(s.run(jobs(), call, self.folder)["calls"], 0)
        resumed = s.run(jobs(), lambda *_: s.Outcome("success"), self.folder, resume_blocked=True)
        self.assertEqual(resumed["calls"], 5)
        self.assertTrue(resumed["complete"])

    def test_quota_never_becomes_technical_zero_when_budget_exhausted(self):
        result = s.run(jobs(1), lambda *_: s.Outcome("quota"), self.folder, max_attempts=1)
        self.assertFalse(result["complete"])
        again = s.run(jobs(1), lambda *_: self.fail(), self.folder, max_attempts=1, resume_blocked=True)
        self.assertFalse(again["complete"])
        self.assertEqual(again["calls"], 0)

    def test_recovery_rechecks_rejection_before_pending_and_preserves_saved(self):
        work = jobs(5)
        def seed(job, attempt):
            return s.Outcome({'0': 'uncertain', '1': 'success', '2': 'blocked'}[job.case])
        first = s.run(work, seed, self.folder, concurrency=1)
        seen = []
        def recover(job, attempt):
            seen.append((job.case, attempt))
            return s.Outcome('success')
        result = s.run(work, recover, self.folder, concurrency=2, resume_blocked=True)
        self.assertEqual(seen[0], ('2', 2))
        self.assertEqual(set(seen[1:]), {('3', 1), ('4', 1)})
        self.assertEqual(result['states'][work[0].key], first['states'][work[0].key])
        self.assertEqual(result['states'][work[1].key], first['states'][work[1].key])

    def test_repeated_rejection_on_resume_makes_only_one_call(self):
        work = jobs(5)
        s.run(work, lambda *_: s.Outcome('blocked'), self.folder, concurrency=1)
        seen = []
        def refused(job, attempt):
            seen.append((job.case, attempt))
            return s.Outcome('blocked')
        result = s.run(work, refused, self.folder, concurrency=3, resume_blocked=True)
        self.assertEqual(seen, [('0', 2)])
        self.assertTrue(result['paused'])
        self.assertEqual(result['states'][work[1].key]['status'], 'pending')
        s.run(work, refused, self.folder, concurrency=3, resume_blocked=True)
        exhausted = s.run(work, lambda *_: self.fail('budget reset'), self.folder,
                          concurrency=3, resume_blocked=True)
        self.assertEqual(exhausted['calls'], 0)
        self.assertTrue(exhausted['paused'])

    def test_inconclusive_recheck_does_not_release_pending(self):
        for outcome in ['retry', 'uncertain', 'terminal']:
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as folder:
                work = jobs(3)
                s.run(work, lambda *_: s.Outcome('quota'), folder, concurrency=1)
                result = s.run(work, lambda *_: s.Outcome(outcome), folder,
                               concurrency=2, resume_blocked=True)
                self.assertEqual(result['calls'], 1)
                self.assertTrue(result['paused'])
                self.assertEqual(result['states'][work[1].key]['status'], 'pending')

    def test_selection_ignores_excluded_block_without_changing_history(self):
        work = jobs(4)
        first = s.run(work, lambda *_: s.Outcome('blocked'), self.folder, concurrency=1)
        journal = self.folder / 'events.jsonl'
        before = journal.read_bytes()
        seen = []
        def call(job, attempt):
            seen.append(job.key)
            return s.Outcome('success')
        result = s.run(work, call, self.folder, resume_blocked=True,
                       selected_keys={j.key for j in work[1:]})
        self.assertEqual(set(seen), {j.key for j in work[1:]})
        self.assertEqual(result['states'][work[0].key], first['states'][work[0].key])
        self.assertTrue(journal.read_bytes().startswith(before))
        self.assertFalse(result['complete'])
        self.assertFalse(result['paused'])
        again = s.run(work, lambda *_: self.fail('duplicate'), self.folder,
                      selected_keys={j.key for j in work[1:]})
        self.assertEqual(again['calls'], 0)
        with self.assertRaisesRegex(ValueError, 'Selected jobs'):
            s.run(work, call, self.folder, selected_keys={'not-in-manifest'})

    def test_stop_drains_and_resume_only_unstarted(self):
        stop = threading.Event()
        both = threading.Barrier(2)
        def call(job, attempt):
            both.wait(2)
            stop.set()
            return s.Outcome("success", {"case": job.case})
        result = s.run(jobs(), call, self.folder, stop=stop)
        self.assertEqual(result["calls"], 2)
        again = s.run(jobs(), lambda *_: s.Outcome("success"), self.folder)
        self.assertEqual(again["calls"], 4)

    def test_keyboard_interrupt_after_save_drains(self):
        raised = False
        def checkpoint(states):
            nonlocal raised
            if not raised:
                raised = True
                raise KeyboardInterrupt
        result = s.run(jobs(4), lambda *_: s.Outcome("success"), self.folder, checkpoint=checkpoint)
        self.assertEqual(result["calls"], 2)
        self.assertEqual(sum(x["status"] == "success" for x in result["states"].values()), 2)

    def test_sigint_at_durable_write_boundary_does_not_duplicate_journal_event(self):
        original_handler = signal.getsignal(signal.SIGINT)
        real_append = s.append
        def append(path, event):
            real_append(path, event)
            if event.get("type") == "result":
                signal.raise_signal(signal.SIGINT)
        with patch.object(s, "append", append):
            result = s.run(jobs(4), lambda *_: s.Outcome("success"), self.folder)
        self.assertEqual(result["calls"], 2)
        resumed = s.run(jobs(4), lambda *_: s.Outcome("success"), self.folder)
        self.assertEqual(resumed["calls"], 2)
        self.assertTrue(resumed["complete"])
        self.assertEqual(signal.getsignal(signal.SIGINT), original_handler)

    def test_uncertain_exception_is_not_retried_or_logged_verbatim(self):
        def call(*_):
            raise TimeoutError("secret-token-should-not-be-saved")
        first = s.run(jobs(2), call, self.folder, concurrency=1)
        self.assertFalse(first["paused"])
        again = s.run(jobs(2), call, self.folder, resume_blocked=True)
        self.assertEqual(again["calls"], 0)
        self.assertNotIn("secret-token", (self.folder / "events.jsonl").read_text())

    def test_missing_reasoning_flag_is_completed(self):
        s.run(jobs(1), lambda *_: s.Outcome("flagged", {"reason": "missing_readable_reasoning"}), self.folder)
        self.assertEqual(s.run(jobs(1), lambda *_: self.fail(), self.folder)["calls"], 0)

    def test_input_or_contract_drift_and_duplicate_jobs_refused(self):
        s.run(jobs(1), lambda *_: s.Outcome("success"), self.folder, contract={"source": "one"})
        with self.assertRaisesRegex(ValueError, "identity"):
            s.run(jobs(1), lambda *_: self.fail(), self.folder, contract={"source": "two"})
        altered = jobs(1)
        altered[0].request["input_hash"] = "changed"
        with self.assertRaisesRegex(ValueError, "identity"):
            s.run(altered, lambda *_: self.fail(), self.folder, contract={"source": "one"})
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            s.run(jobs(1) * 2, lambda *_: self.fail(), self.folder)

    def test_writer_lock_refuses_second_writer(self):
        with s.writer_lock(self.folder):
            with self.assertRaisesRegex(RuntimeError, "Writer lock"):
                s.run(jobs(), lambda *_: self.fail(), self.folder)

    def test_corrupt_or_torn_journal_fails_before_calls(self):
        s.run(jobs(1), lambda *_: s.Outcome("success"), self.folder)
        path = self.folder / "events.jsonl"
        with path.open("ab") as handle:
            handle.write(b'{"type":')
        with self.assertRaisesRegex(ValueError, "Incomplete journal"):
            s.run(jobs(1), lambda *_: self.fail(), self.folder)

    def test_disk_failure_leaves_uncertain_start_not_duplicate_success(self):
        real_append = s.append
        def broken(path, event):
            if event.get("type") == "result":
                raise OSError("simulated disk full")
            real_append(path, event)
        with patch.object(s, "append", broken):
            with self.assertRaises(OSError):
                s.run(jobs(1), lambda *_: s.Outcome("success"), self.folder)
        again = s.run(jobs(1), lambda *_: self.fail(), self.folder)
        self.assertFalse(again["paused"])
        self.assertEqual(again["calls"], 0)

    def test_killed_process_blocks_replay_even_after_verified_lock_removal(self):
        code = '''import os, sys
from pathlib import Path
from radle_job_queue import Job, run
def call(job, attempt):
    Path(sys.argv[1], 'remote_success.txt').write_text('response happened')
    os._exit(17)
run([Job('0', 'unseen_model_0', {'input_hash':'0', 'effort':'high'})], call, sys.argv[1])
'''
        child = subprocess.run([sys.executable, "-B", "-c", code, str(self.folder)],
                               cwd=Path(__file__).resolve().parents[1] / 'src', timeout=10, capture_output=True)
        self.assertEqual(child.returncode, 17, child.stderr)
        self.assertTrue((self.folder / "remote_success.txt").exists())
        with self.assertRaisesRegex(RuntimeError, "Writer lock"):
            s.run(jobs(1), lambda *_: self.fail(), self.folder)
        # subprocess.run returned: this specific local test process is definitely dead.
        (self.folder / "writer.lock").unlink()
        again = s.run(jobs(1), lambda *_: self.fail(), self.folder)
        self.assertFalse(again["paused"])
        self.assertEqual(again["calls"], 0)

    def test_thousand_jobs_no_duplicate_keys_and_serial_parity(self):
        workload = jobs(1000)
        def call(job, attempt):
            return s.Outcome("success", {"case": job.case, "model": job.model})
        parallel = s.run(workload, call, self.folder / "parallel", concurrency=5)
        serial = s.run(workload, call, self.folder / "serial", concurrency=1)
        self.assertEqual(parallel["calls"], 1000)
        self.assertEqual({k: v["value"] for k, v in parallel["states"].items()},
                         {k: v["value"] for k, v in serial["states"].items()})
        self.assertEqual(s.run(workload, call, self.folder / "parallel")["calls"], 0)


if __name__ == "__main__":
    unittest.main()
