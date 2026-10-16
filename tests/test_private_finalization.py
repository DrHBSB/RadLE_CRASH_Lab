import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import radle_private_finalization as finalizer


class PrivateFinalizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/'raw/results.csv'; self.source.parent.mkdir()
        self.frame = pd.DataFrame({'Master_Case_ID':['1','2','3'],
            'Diagnosis_past':['saved','flagged','API_ERROR'], 'Diagnosis_new':['saved','saved','API_ERROR']})
        self.frame.to_csv(self.source, index=False)
        self.folder = Path(str(self.source)+'.concurrent'); (self.folder/'queue').mkdir(parents=True)
        for p in (self.folder/'checkpoint.json', self.folder/'queue/events.jsonl',
                  self.root/'collection_contract.json', self.root/'cohort_admission.json'):
            p.write_text('fixture evidence')
        parent = self.root/'parent'; parent.mkdir(); old = parent/'results.csv'; old.write_text('frozen parent')
        self.receipt = dict(collection_models=['new'], source_paths={'results':str(old)},
            source_hashes={'results':hashlib.sha256(old.read_bytes()).hexdigest()},
            inherited_unresolved=[dict(Master_Case_ID='3', model='past', status='uncertain', attempts=4)],
            inherited_failure_inventory=[dict(case='3', model='past', classification='remote_outcome_unknown',
                                               root_cause='not_independently_verified', completion_tokens=float('nan'))])
        self.unresolved = [dict(Master_Case_ID='3', model='new', status='rejected', attempts=1)]
        inventory = pd.DataFrame([dict(case='3', model='new', classification='provider_policy_rejection',
                                      root_cause='not_independently_verified')])
        rows = []
        for case in ('1','2','3'):
            for model in ('past','new'):
                bucket = 'paid_repair' if case=='3' else ('analysis_flag' if (case,model)==('2','past') else 'accepted')
                rows.append(dict(Master_Case_ID=case, model=model, bucket=bucket,
                                 status='original_'+bucket, reason='original reason'))
        self.audit = dict(audit=pd.DataFrame(rows))
        self.rb = SimpleNamespace(audit_saved_collection=lambda *a:dict(final_df=self.frame,
            unresolved_pairs=self.unresolved, failure_inventory=inventory), make_json_safe=lambda x:x)
        self.admission = SimpleNamespace(combined_audit=lambda *a:self.audit)
        self.paths = dict(run_root=str(self.root), raw_results_csv=str(self.source),
            final_results_csv=str(self.root/'final/RadLE_v2_results_final.csv'),
            final_manifest_json=str(self.root/'final/RadLE_v2_results_final_manifest.json'))
        self.cfg = dict(run_label='expanded', expected_cases=3, output_cap=32768)
        self.cohort = [dict(name='past'), dict(name='new')]

    def finalize(self):
        return finalizer.finalize(self.rb,self.admission,self.paths,self.cohort,self.receipt,self.cfg)

    def test_snapshot_preserves_bytes_flags_unknown_and_refusal_evidence(self):
        before = self.source.read_bytes()
        manifest = self.finalize()
        self.assertEqual(Path(self.paths['final_results_csv']).read_bytes(), before)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(manifest['outcome_counts'], dict(accepted=3,analysis_flag=1,failed=2))
        self.assertFalse(manifest['clean_publication_gate_passed'])
        self.assertFalse(manifest['public_export_performed'])
        self.assertEqual(manifest['inference_calls'],0)
        table = pd.read_csv(self.root/'final/RadLE_v2_final_outcomes.csv')
        failed = table[table.final_status.eq('failed')]
        self.assertEqual(set(failed.scheduler_status), {'uncertain','rejected'})
        self.assertEqual(set(failed.failure_classification), {'remote_outcome_unknown','provider_policy_rejection'})
        evidence = json.loads((self.root/'final/RadLE_v2_failure_evidence.json').read_text())
        self.assertIsNone(evidence[0]['completion_tokens'])

    def test_matching_rerun_is_idempotent_and_tampering_refuses_overwrite(self):
        first = self.finalize()
        self.assertEqual(self.finalize(),first)
        final = Path(self.paths['final_results_csv']); final.write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError,'refuse overwrite'):self.finalize()
        self.assertEqual(final.read_bytes(),b'changed')

    def test_active_writer_and_partial_final_are_preserved(self):
        lock=self.folder/'writer.lock';lock.write_text('live')
        with self.assertRaisesRegex(RuntimeError,'writer lock'):self.finalize()
        lock.unlink()
        target=Path(self.paths['final_results_csv']);target.parent.mkdir();target.write_text('partial')
        with self.assertRaisesRegex(RuntimeError,'Partial or conflicting'):self.finalize()
        self.assertEqual(target.read_text(),'partial')

    def test_missing_or_duplicate_failure_evidence_fails_closed(self):
        self.receipt['inherited_unresolved']=[]
        with self.assertRaisesRegex(RuntimeError,'disagree'):self.finalize()
        self.assertFalse(Path(self.paths['final_manifest_json']).exists())

    def test_source_change_during_audit_prevents_artifacts(self):
        def changed(*a):
            self.source.write_text('changed during audit')
            return self.audit
        self.admission.combined_audit=changed
        with self.assertRaisesRegex(RuntimeError,'changed during'):self.finalize()
        self.assertFalse(Path(self.paths['final_results_csv']).exists())

    def test_notebook_finalization_mode_is_read_only_and_keyless(self):
        cfg=json.loads((ROOT/'configs/radle_collection.json').read_text())
        self.assertTrue(cfg['finalize_private'])
        nb=json.loads((ROOT/'notebooks/RadLE_v1_5_Morning.ipynb').read_text(encoding='utf-8'))
        self.assertEqual(len(nb['cells']),4)
        code=[''.join(c['source']) for c in nb['cells']]
        for s in code:compile(s,'notebook','exec')
        self.assertIn('if _FINALIZE_PRIVATE:',code[1])
        self.assertIn('openrouter_client = None',code[1])
        self.assertIn('and not CONFIG.get("finalize_private", False)',code[2])
        self.assertIn('audit_only=CONFIG.get("finalize_private", False) or',code[3])
        self.assertIn('radle_private_finalization.finalize(',code[3])
