import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from radle_lock_recovery import retire_legacy_locks, RUN, AUTHORIZATION


class LockRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.csv = Path(self.tmp.name) / RUN / "raw" / "results.csv"
        self.folder = Path(str(self.csv) + ".concurrent")
        (self.folder / "queue").mkdir(parents=True)

    def recover(self, **kwargs):
        return retire_legacy_locks(self.csv, run_label=kwargs.get("run_label", RUN),
                                   authorization=kwargs.get("authorization", AUTHORIZATION))

    def test_archives_both_locks_and_preserves_data(self):
        self.csv.write_text("saved answers")
        for folder in (self.folder, self.folder / "queue"):
            (folder / "writer.lock").write_bytes(b"3600")
            (folder / "events.jsonl").write_bytes(b"journal")
        result = self.recover()
        self.assertEqual(len(result["locks"]), 2)
        for record in result["locks"]:
            self.assertEqual(Path(record["archive"]).read_bytes(), b"3600")
            self.assertFalse(Path(record["path"]).exists())
        self.assertEqual(self.csv.read_text(), "saved answers")
        self.assertEqual((self.folder / "queue" / "events.jsonl").read_bytes(), b"journal")
        self.assertEqual(self.recover(), result)

    def test_new_lock_after_consumption_is_held(self):
        self.recover()
        lock = self.folder / "writer.lock"
        lock.write_bytes(b"999")
        with self.assertRaisesRegex(RuntimeError, "consumed"):
            self.recover()
        self.assertEqual(lock.read_bytes(), b"999")

    def test_unknown_lock_is_held(self):
        lock = self.folder / "writer.lock"
        lock.write_bytes(b'{"pid":3600}')
        with self.assertRaisesRegex(RuntimeError, "Unknown"):
            self.recover()
        self.assertTrue(lock.exists())

    def test_wrong_authorization_is_held(self):
        with self.assertRaisesRegex(RuntimeError, "authorization"):
            self.recover(authorization="no")

    def test_wrong_run_is_held(self):
        with self.assertRaises(RuntimeError):
            self.recover(run_label="other")


if __name__ == "__main__":
    unittest.main()
