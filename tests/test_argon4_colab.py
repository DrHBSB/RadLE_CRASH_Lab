import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import radle_argon4 as a
import radle_job_queue as q
import radle_retry_policy as rp


class ArgonTests(unittest.TestCase):
    def metadata(self):
        endpoint = dict(tag='google-vertex/global', provider_name='Google', name='pinned endpoint',
                        status=0, max_completion_tokens=65536,
                        supported_parameters=['reasoning', 'reasoning_effort', 'max_tokens', 'response_format'])
        return {
            '/key': {},
            '/models': {'data': [dict(id=a.MODEL_ID, canonical_slug=a.CANONICAL_ID,
                architecture=dict(input_modalities=['text', 'image']),
                reasoning=dict(supported_efforts=['high', 'medium', 'low']))]},
            '/models/' + a.MODEL_ID + '/endpoints': {'data': {'endpoints': [endpoint]}},
            '/endpoints/zdr': {'data': [dict(model_id=a.MODEL_ID, tag=endpoint['tag'], name=endpoint['name'])]},
        }

    def test_live_preflight_exact_route_version_ladder_privacy(self):
        data = self.metadata()
        def request(url, key=None):
            self.assertFalse(url.endswith('/chat/completions'))
            return 200, data[url.removeprefix('https://openrouter.ai/api/v1')]
        receipt = a.preflight('not-a-real-key', request)
        self.assertEqual(receipt['reasoning_profile']['initial_effort'], 'high')
        self.assertTrue(receipt['zdr_verified'])
        for change in ['version', 'ladder', 'privacy', 'cap', 'route', 'status', 'parameters', 'image']:
            with self.subTest(change=change):
                data = self.metadata()
                model = data['/models']['data'][0]
                endpoint = data['/models/' + a.MODEL_ID + '/endpoints']['data']['endpoints'][0]
                if change == 'version': model['canonical_slug'] = 'changed'
                if change == 'ladder': model['reasoning']['supported_efforts'] = ['high', 'low']
                if change == 'privacy': data['/endpoints/zdr']['data'] = []
                if change == 'cap': endpoint['max_completion_tokens'] = 8192
                if change == 'route': endpoint['tag'] = 'another-provider'
                if change == 'status': endpoint['status'] = -2
                if change == 'parameters': endpoint['supported_parameters'] = []
                if change == 'image': model['architecture']['input_modalities'] = ['text']
                with self.assertRaises(RuntimeError): a.preflight('not-a-real-key', request)

    def test_four_attempt_bound_replay_and_protected_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs = [q.Job('1', 'gemini_4_argon', {})]
            seen = []
            def call(job, attempt):
                seen.append(attempt)
                return q.Outcome('retry', {})
            q.run(jobs, call, tmp, max_attempts=2)
            clock = int(time.time()) + 100
            with patch.object(q.time, 'time', side_effect=range(clock, clock + 100000, 70)):
                q.run(jobs, call, tmp, max_attempts=2, resume_blocked=True,
                      retry_authorization=a.RETRY_AUTHORIZATION)
            self.assertEqual(seen, [1, 2, 3, 4])
            q.run(jobs, call, tmp, max_attempts=2)
            q.run(jobs, call, tmp, max_attempts=2, resume_blocked=True,
                  retry_authorization=a.RETRY_AUTHORIZATION)
            self.assertEqual(seen, [1, 2, 3, 4])
        for status in ['success', 'flagged', 'rejected', 'blocked', 'uncertain', 'quota']:
            self.assertFalse(rp.eligible(dict(status=status, attempts=2, value={}), a.RETRY_AUTHORIZATION))

    def test_ceiling_ladder_preserves_cap_and_model(self):
        from radle_reasoning_ceiling import CeilingPolicy
        model = copy.deepcopy(a.MODELS[0])
        policy = CeilingPolicy(catalog={a.MODEL_ID: dict(supported_efforts=['high', 'medium', 'low'])})
        efforts = []
        for attempt in range(1, 5):
            chosen, decision = policy.choose(model, '1', attempt, 32768)
            efforts.append(chosen['extra']['reasoning']['effort'])
            policy.received('1', 'gemini_4_argon', attempt, 32768,
                            dict(completion_tokens=32768, finish_reason='length', response_id=str(attempt)))
        self.assertEqual(efforts, ['high', 'high', 'medium', 'low'])
        self.assertEqual(model, a.MODELS[0])

    def test_admission_carries_every_old_column_and_preserves_evidence(self):
        from types import SimpleNamespace
        import pandas as pd
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'Runs' / a.SOURCE_RUN / 'collection_contract.json'
            source.parent.mkdir(parents=True)
            ids = [str(i) for i in range(1, 201)]
            models = [dict(name='old_' + str(i), id='vendor/' + str(i)) for i in range(16)]
            source.write_text(json.dumps(dict(models=models, case_ids=ids,
                images={i: 'hash-' + i for i in ids},
                prompt_sha256=hashlib.sha256(b'unchanged prompt').hexdigest(), output_cap=32768)))
            raw = source.parent / 'raw/results.csv'
            raw.parent.mkdir()
            frame = pd.DataFrame(dict(Master_Case_ID=ids,
                Diagnosis_old_0=['saved, multiline\nanswer'] * 199 + ['ERROR: held'],
                Old_attempts=['8'] * 200, Old_flag=['missing_reasoning'] * 200))
            frame.to_csv(raw, index=False)
            folder = Path(str(raw) + '.concurrent')
            (folder / 'queue').mkdir(parents=True)
            (folder / 'queue/events.jsonl').write_text('original journal evidence')
            (folder / 'checkpoint.json').write_text('original checkpoint evidence')
            snapshots = {path: path.read_bytes() for path in [source, raw, folder/'queue/events.jsonl', folder/'checkpoint.json']}
            def paths(dataset, run_label, create_dirs=True):
                run = root / 'Runs' / run_label
                if create_dirs: (run / 'raw').mkdir(parents=True, exist_ok=True)
                return dict(run_root=str(run), raw_results_csv=str(run / 'raw/results.csv'),
                            master_images_folder=str(root / 'images'))
            held = [dict(Master_Case_ID='200', model='old_0', status='failed', attempts=8)]
            rb = SimpleNamespace(PROMPT='unchanged prompt', build_run_paths=paths,
                build_image_index=lambda _: {i: i for i in ids},
                rebuild_base_row=lambda i, _: {'Image_SHA256': 'hash-' + i},
                make_json_safe=lambda x: x,
                audit_saved_collection=lambda *args: dict(final_df=frame, unresolved_pairs=held,
                    failure_inventory=pd.DataFrame(held)),
                audit_benchmark_output=lambda *args, **kw: {'models': len(kw['models'])})
            prepared, cohort, receipt = a.prepare(rb, root, dict(verified=True))
            self.assertEqual(len(cohort), 17)
            self.assertEqual(cohort[:16], models)
            self.assertEqual(Path(prepared['raw_results_csv']).read_bytes(), raw.read_bytes())
            self.assertEqual(receipt['inherited_unresolved'], held)
            self.assertEqual(a.combined_audit(rb, prepared, cohort, receipt)['models'], 17)
            self.assertEqual(a.prepare(rb, root, {})[2], receipt)
            target = Path(prepared['run_root']) / 'collection_contract.json'
            self.assertEqual(json.loads(target.read_text())['collection_models'], ['gemini_4_argon'])
            changed = pd.read_csv(prepared['raw_results_csv'], dtype=str, keep_default_na=False)
            changed.loc[0, 'Old_attempts'] = '0'
            changed.to_csv(prepared['raw_results_csv'], index=False)
            with self.assertRaisesRegex(RuntimeError, 'values changed'):
                a.combined_audit(rb, prepared, cohort, receipt)
            rb.PROMPT = 'changed'
            with self.assertRaises(RuntimeError): a.prepare(rb, root, {})
            for path, original in snapshots.items(): self.assertEqual(path.read_bytes(), original)

    def test_collector_adds_new_arm_without_resending_inherited_failures(self):
        import pandas as pd
        from test_concurrent_collection import IntegrationTests
        fixture = IntegrationTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        index = fixture.run_collection.__globals__['rb'].build_image_index(fixture.images)
        import radle_benchmark as rb
        rows = []
        for case in index:
            row = rb.rebuild_base_row(case, index[case])
            for i in range(16): row['Diagnosis_old_' + str(i)] = 'ERROR: preserved' if i == 0 else 'prior answer'
            row['Inherited_attempts'] = '8'
            rows.append(row)
        parent = pd.DataFrame(rows)
        parent.to_csv(fixture.output, index=False)
        fixture.client.chat.completions.create.side_effect = lambda **kw: fixture.response(reasoning='visible reasoning')
        fixture.run_collection(max_attempts=2, concurrency=1, allow_partial_result=True)
        self.assertEqual(fixture.client.chat.completions.create.call_count, 3)
        final = pd.read_csv(fixture.output, dtype=str, keep_default_na=False)
        for column in parent.columns:
            self.assertEqual(parent[column].astype(str).tolist(), final[column].tolist())
        self.assertTrue(all(final['Diagnosis_any_model'] == 'synthetic finding'))

    def test_canonical_workflow_combines_status_but_never_dispatches_old_models(self):
        import contextlib, io
        import pandas as pd
        from types import SimpleNamespace
        notebook = json.loads((ROOT / 'notebooks/RadLE_v1_5_Morning.ipynb').read_text(encoding='utf-8'))
        source = ''.join(notebook['cells'][3]['source'])
        calls = []
        def workflow(**options):
            calls.append(options)
            return dict(final_df=pd.DataFrame({'Master_Case_ID': ['1']}),
                final_source_csv='combined.csv', unresolved_pairs=[], gate_receipt=pd.DataFrame(),
                final_audit={'bucket_summary': pd.DataFrame()})
        audit = {k: pd.DataFrame() for k in ('dataset_integrity', 'bucket_summary', 'status_summary')}
        inherited = [dict(Master_Case_ID='184', model='old_model', status='rejected', attempts=1)]
        env = dict(openrouter_client=object(), dataset_root='dataset', run_paths={},
            COLLECTION_MODELS=a.MODELS, ACTIVE_MODELS=[{}] * 17,
            EXPECTED_CASES=200, RUN_LABEL=a.RUN_LABEL, CONCURRENCY=1,
            RETRY_AUTHORIZATION=a.RETRY_AUTHORIZATION, AUTO_SPACED_REPAIR=True,
            ADMISSION_RECEIPT=dict(inherited_unresolved=inherited, inherited_failure_inventory=inherited),
            radle_argon4=SimpleNamespace(combined_audit=lambda *args: audit),
            radle_benchmark=object(), run_autonomous_openrouter_workflow=workflow)
        with contextlib.redirect_stdout(io.StringIO()): exec(source, env)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['models'], a.MODELS)
        self.assertFalse(calls[0]['promote_private'])
        self.assertEqual(env['AUTO_WORKFLOW_RESULT']['unresolved_pairs'], inherited)
        self.assertEqual(env['AUTO_WORKFLOW_RESULT']['status'], 'completed_with_unresolved')
        self.assertIs(env['AUTO_WORKFLOW_RESULT']['final_audit'], audit)

    def test_canonical_notebook_compiles_and_selects_only_new_arm(self):
        nb = json.loads((ROOT / 'notebooks/RadLE_v1_5_Morning.ipynb').read_text(encoding='utf-8'))
        self.assertEqual(len(nb['cells']), 4)
        sources = [''.join(c['source']) for c in nb['cells']]
        for i, source in enumerate(sources): compile(source, f'cell-{i}', 'exec')
        self.assertIn('codex/radle-17-argon4-20261016', sources[0])
        self.assertNotIn('radle_budget_seed', sources[2])
        self.assertNotIn('retire_legacy_locks', sources[2])
        self.assertIn('max_job_attempts=2', sources[3])
        self.assertIn('promote_private=False, export_public=False', sources[3])
        self.assertIn('run_autonomous_openrouter_workflow', sources[3])
        self.assertIn('models=COLLECTION_MODELS', sources[3])
        self.assertIn('COMBINED_AUDIT', sources[3])
        self.assertFalse((ROOT / 'notebooks/RadLE_Gemini_4_Argon.ipynb').exists())


if __name__ == '__main__': unittest.main()
