import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import radle_benchmark as rb
import radle_concurrent_collection as cc
import test_concurrent_collection as fixtures


class FlaggedCompletionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.IntegrationTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        self.paths = rb.build_run_paths(f.root, run_label='flagged_fixture')
        self.paths.update(raw_results_csv=str(f.output), master_images_folder=str(f.images))
        count = []
        def response(**kwargs):
            count.append(1)
            return f.response(reasoning='' if len(count) == 3 else 'visible returned reasoning')
        f.client.chat.completions.create.side_effect = response

    def workflow(self, **options):
        f = self.fixture
        with patch.object(cc, 'check_openrouter_funds', return_value={'status':'available'}), \
                contextlib.redirect_stdout(io.StringIO()):
            return rb.run_autonomous_openrouter_workflow(
                f.client, f.root, self.paths, f.models, 3,
                {'any_model': {'vendor/any-model'}}, {'any_model':'Fixture Provider'},
                'flagged_fixture', smoke_first=False, concurrency=1,
                max_job_attempts=2, max_repair_passes=0, max_output_tokens=32768, **options)

    def test_completed_flag_is_returned_and_never_resent_on_resume(self):
        with patch.object(rb, 'assert_clean_benchmark_audit') as gate, \
             patch.object(rb, 'promote_final_results') as promote:
            result = self.workflow()
            repeated = self.workflow()
        self.assertEqual(result['status'], 'completed_with_flags')
        self.assertEqual(repeated['status'], 'completed_with_flags')
        self.assertEqual(result['final_source_label'], 'raw_with_flags')
        self.assertEqual(rb.audit_accepted_count(result['final_audit']), 2)
        self.assertEqual(len(result['analysis_flags']), 1)
        self.assertEqual(result['unresolved_pairs'], [])
        self.assertIsNone(result['final_manifest'])
        self.assertTrue(result['gate_receipt'].empty)
        self.fixture.client.chat.completions.create.assert_called()
        self.assertEqual(self.fixture.client.chat.completions.create.call_count, 3)
        gate.assert_not_called(); promote.assert_not_called()

    def test_promotion_keeps_strict_flag_gate_without_extra_requests(self):
        self.workflow()
        with patch.object(rb, 'promote_final_results') as promote:
            with self.assertRaisesRegex(RuntimeError, 'audit not clean'):
                self.workflow(promote_private=True,
                              promote_confirmation='YES_AUTO_PROMOTE_PRIVATE_FINAL')
        self.assertEqual(self.fixture.client.chat.completions.create.call_count, 3)
        promote.assert_not_called()


if __name__ == '__main__': unittest.main()
