import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import radle_collection_admission as admission
import radle_job_queue as queue


def model(name):
    return dict(name=name, id='vendor/' + name, provider='openrouter', max_transport_attempts=1,
        output_token_parameter='max_tokens', expected_provider='Vendor', omit_sampling=True,
        expected_returned_model_ids=['vendor/' + name], require_readable_reasoning=True,
        extra=dict(reasoning=dict(effort='high', exclude=False), response_format=dict(type='json_object')),
        provider_routing=dict(only=['vendor/global'], allow_fallbacks=False, require_parameters=True,
                              data_collection='deny', zdr=True))


def config(parent, new, parent_run='parent', run_label='expanded'):
    return dict(schema=1, parent_run=parent_run, run_label=run_label, contract_release='fixture-version',
        expected_cases=3, output_cap=32768, concurrency=1, ordinary_attempts=2, automatic_repair=True,
        models=copy.deepcopy(parent + new), capabilities={m['id']: dict(canonical_id=m['id'] + '-pinned',
        reasoning_efforts=['high', 'medium', 'low']) for m in new},
        retry_authorization=dict(id='fixture-' + run_label, max_pairs=3 * len(new),
            attempts_per_pair=2, spacing_seconds=60, include_uncertain=False,
            include_quota=False, include_exhausted=True))


def metadata(cfg, selected):
    data = {'/key': {}, '/models': {'data': []}, '/endpoints/zdr': {'data': []}}
    for m in selected:
        endpoint = dict(tag='vendor/global', provider_name='Vendor', name=m['id'], status=0,
            max_completion_tokens=65536,
            supported_parameters=['reasoning', 'reasoning_effort', 'max_tokens', 'response_format'])
        data['/models']['data'].append(dict(id=m['id'], canonical_slug=m['id'] + '-pinned',
            architecture=dict(input_modalities=['text', 'image']),
            reasoning=dict(supported_efforts=['high', 'medium', 'low'])))
        data['/models/' + m['id'] + '/endpoints'] = {'data': {'endpoints': [endpoint]}}
        data['/endpoints/zdr']['data'].append(dict(model_id=m['id'], tag=endpoint['tag'], name=endpoint['name']))
    return data


def request_for(data):
    return lambda url, key=None: (200, data[url.removeprefix('https://openrouter.ai/api/v1')])


class AdmissionTests(unittest.TestCase):
    def test_saved_completion_requires_validated_evidence_and_keeps_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'results.csv'
            output.write_text('saved')
            folder = Path(str(output) + '.concurrent')
            folder.mkdir()
            (folder / 'checkpoint.json').write_text('{}')
            cfg = config([model('past')], [model('new')])
            audit = dict(analysis_flags=['missing_readable_reasoning'])
            result = dict(final_audit=audit, unresolved_pairs=[])
            rb = SimpleNamespace(audit_saved_collection=lambda *a: result,
                audit_repair_target_count=lambda a: 0, audit_accepted_count=lambda a: 2)
            self.assertTrue(admission.saved_collection_complete(rb, {'raw_results_csv':output}, [model('new')], cfg))
            result['unresolved_pairs'] = [{'status':'uncertain'}]
            self.assertFalse(admission.saved_collection_complete(rb, {'raw_results_csv':output}, [model('new')], cfg))
            result['unresolved_pairs'] = []
            rb.audit_saved_collection = lambda *a: (_ for _ in ()).throw(RuntimeError('CSV hash mismatch'))
            with self.assertRaisesRegex(RuntimeError, 'CSV hash mismatch'):
                admission.saved_collection_complete(rb, {'raw_results_csv':output}, [model('new')], cfg)

    def test_current_roster_addition_is_configuration_only(self):
        import radle_openrouter_16
        cfg = admission.load_config(ROOT / 'configs/radle_collection.json')
        new = admission.added_models(cfg, radle_openrouter_16.MODELS)
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]['id'], 'google/gemini-4-argon')
        self.assertEqual(cfg['models'][:-1], radle_openrouter_16.MODELS)
        self.assertEqual(cfg['retry_authorization']['id'], 'radle-argon4-two-repairs-20261016')

    def test_arbitrary_roster_sizes_and_later_addition_need_no_code_change(self):
        parent, new = [model('past')], [model('next'), model('later')]
        cfg = config(parent, new)
        self.assertEqual(admission.added_models(cfg, parent), new)
        next_cfg = config(cfg['models'], [model('future')], 'expanded', 'future_run')
        self.assertEqual(admission.added_models(next_cfg, cfg['models']), [model('future')])
        for bad in ['remove', 'change', 'budget']:
            broken = copy.deepcopy(cfg)
            if bad == 'remove': broken['models'].pop(0)
            if bad == 'change': broken['models'][0]['extra']['reasoning']['effort'] = 'low'
            if bad == 'budget': broken['retry_authorization']['max_pairs'] += 1
            with self.assertRaises(RuntimeError): admission.added_models(broken, parent)

    def test_metadata_works_for_multiple_unrelated_models_and_fails_on_drift(self):
        selected = [model('one'), model('two')]
        cfg = config([model('past')], selected)
        data = metadata(cfg, selected)
        receipts = admission.preflight(cfg, selected, 'fixture-key', request_for(data))
        self.assertEqual(len(receipts), 2)
        self.assertTrue(all(r['zdr_verified'] for r in receipts))
        for kind in ['version', 'reasoning', 'cap', 'privacy', 'image', 'route', 'status']:
            with self.subTest(kind=kind):
                data = metadata(cfg, selected)
                live = data['/models']['data'][0]
                endpoint = data['/models/' + selected[0]['id'] + '/endpoints']['data']['endpoints'][0]
                if kind == 'version': live['canonical_slug'] = 'wrong'
                if kind == 'reasoning': live['reasoning']['supported_efforts'] = ['high']
                if kind == 'cap': endpoint['max_completion_tokens'] = 1024
                if kind == 'privacy': data['/endpoints/zdr']['data'] = []
                if kind == 'image': live['architecture']['input_modalities'] = ['text']
                if kind == 'route': endpoint['tag'] = 'other'
                if kind == 'status': endpoint['status'] = -2
                with self.assertRaises(RuntimeError): admission.preflight(cfg, selected, 'fixture', request_for(data))

    def test_successive_admissions_preserve_parent_values_failures_and_attempts(self):
        import pandas as pd
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = [model('past')]
            new = [model('next')]
            cfg = config(base, new)
            source = root / 'Runs/parent'
            (source / 'raw').mkdir(parents=True)
            images = {str(i): 'image-' + str(i) for i in range(1, 4)}
            (source / 'collection_contract.json').write_text(json.dumps(dict(models=base,
                case_ids=list(images), images=images, prompt_sha256=hashlib.sha256(b'prompt').hexdigest(), output_cap=32768)))
            frame = pd.DataFrame(dict(Master_Case_ID=list(images), Diagnosis_past=['saved', 'ERROR: failed', 'flagged'],
                                      Historical_attempts=['8', '8', '1']))
            frame.to_csv(source / 'raw/results.csv', index=False)
            held = dict(Master_Case_ID='2', model='past', status='failed', attempts=8)
            def journal(path):
                folder = Path(str(path) + '.concurrent')
                (folder / 'queue').mkdir(parents=True)
                (folder / 'queue/events.jsonl').write_text('pinned journal')
                (folder / 'checkpoint.json').write_text('pinned checkpoint')
            journal(source / 'raw/results.csv')
            def paths(dataset, run_label, create_dirs=True):
                run = root / 'Runs' / run_label
                if create_dirs: (run / 'raw').mkdir(parents=True, exist_ok=True)
                return dict(run_root=str(run), raw_results_csv=str(run / 'raw/results.csv'), master_images_folder='images')
            def audit(path, *args):
                unresolved = [held] if Path(path).parent.parent.name == 'parent' else []
                return dict(final_df=pd.read_csv(path, dtype=str), unresolved_pairs=unresolved,
                            failure_inventory=pd.DataFrame(unresolved))
            rb = SimpleNamespace(PROMPT='prompt', build_run_paths=paths, build_image_index=lambda _: images,
                rebuild_base_row=lambda case, _: {'Image_SHA256': images[case]}, make_json_safe=lambda x: x,
                audit_saved_collection=audit, audit_benchmark_output=lambda *args, **kw: {'models': len(kw['models'])})
            source_before = {p: p.read_bytes() for p in source.rglob('*') if p.is_file()}
            args = (rb, root, cfg, request_for(metadata(cfg, new)))
            output, roster, work, receipt = admission.prepare(*args, key='fixture')
            self.assertEqual(work, new)
            self.assertEqual(receipt['inherited_unresolved'], [held])
            self.assertEqual(Path(output['raw_results_csv']).read_bytes(), (source/'raw/results.csv').read_bytes())
            self.assertEqual(admission.prepare(*args, key='fixture')[3], receipt)
            self.assertEqual(admission.combined_audit(rb, output, roster, receipt, cfg)['models'], 2)
            expanded = pd.read_csv(output['raw_results_csv'], dtype=str, keep_default_na=False)
            expanded['Diagnosis_next'] = ['new answer'] * 3
            expanded.to_csv(output['raw_results_csv'], index=False)
            journal(output['raw_results_csv'])
            next_cfg = config(roster, [model('future')], 'expanded', 'future_run')
            output2, roster2, work2, receipt2 = admission.prepare(rb, root, next_cfg,
                request_for(metadata(next_cfg, [model('future')])), key='fixture')
            self.assertEqual(work2, [model('future')])
            self.assertEqual(receipt2['inherited_unresolved'], [held])
            self.assertEqual(receipt2['inherited_model_count'], 2)
            self.assertIn('admission', receipt2['source_hashes'])
            self.assertEqual(admission.combined_audit(rb, output2, roster2, receipt2, next_cfg)['models'], 3)
            changed = pd.read_csv(output2['raw_results_csv'], dtype=str)
            changed.loc[0, 'Historical_attempts'] = '0'
            changed.to_csv(output2['raw_results_csv'], index=False)
            with self.assertRaisesRegex(RuntimeError, 'values changed'):
                admission.combined_audit(rb, output2, roster2, receipt2, next_cfg)
            for path, value in source_before.items(): self.assertEqual(path.read_bytes(), value)

    def test_four_attempt_maximum_and_zero_extra_on_repeated_run(self):
        cfg = config([model('past')], [model('new')])
        with tempfile.TemporaryDirectory() as tmp:
            jobs = [queue.Job('1', 'new', {})]
            seen = []
            def call(job, attempt):
                seen.append(attempt)
                return queue.Outcome('retry', {})
            queue.run(jobs, call, tmp, max_attempts=2)
            clock = int(time.time()) + 100
            with patch.object(queue.time, 'time', side_effect=range(clock, clock + 100000, 70)):
                queue.run(jobs, call, tmp, max_attempts=2, resume_blocked=True,
                          retry_authorization=cfg['retry_authorization'])
            queue.run(jobs, call, tmp, max_attempts=2)
            queue.run(jobs, call, tmp, max_attempts=2, resume_blocked=True,
                      retry_authorization=cfg['retry_authorization'])
            self.assertEqual(seen, [1, 2, 3, 4])

    def test_notebook_has_no_model_special_cases_and_counts_are_dynamic(self):
        nb = json.loads((ROOT/'notebooks/RadLE_v1_5_Morning.ipynb').read_text(encoding='utf-8'))
        self.assertEqual(len(nb['cells']), 4)
        sources = [''.join(cell['source']) for cell in nb['cells']]
        for i, source in enumerate(sources): compile(source, f'cell-{i}', 'exec')
        all_code = '\n'.join(sources)
        for text in ['argon', 'Argon', '17-model', '16-model', '3400', 'smoke_openrouter_16']:
            self.assertNotIn(text, all_code)
        self.assertIn('configs/radle_collection.json', all_code)
        self.assertIn('len(ACTIVE_MODELS)', all_code)
        self.assertIn('run_autonomous_openrouter_workflow', sources[3])
        self.assertIn('PRE-REPAIR AUDIT', sources[3])
        self.assertLess(sources[3].index('PRE-REPAIR AUDIT'), sources[3].index('retry_authorization=RETRY_AUTHORIZATION'))
        self.assertFalse((ROOT/'src/radle_argon4.py').exists())

    def test_notebook_uses_generic_config_and_keeps_inherited_unresolved(self):
        import pandas as pd
        source = ''.join(json.loads((ROOT/'notebooks/RadLE_v1_5_Morning.ipynb').read_text(encoding='utf-8'))['cells'][3]['source'])
        calls = []
        audit = {name: pd.DataFrame() for name in ('dataset_integrity', 'bucket_summary', 'status_summary', 'analysis_flags')}
        def workflow(**options):
            calls.append(options)
            return dict(final_df=pd.DataFrame({'Master_Case_ID':['1']}), final_source_csv='combined.csv',
                        unresolved_pairs=[], final_audit=audit)
        selected = [model('new')]
        cfg = config([model('past')], selected)
        inherited = [dict(Master_Case_ID='2', model='past', status='failed', attempts=8)]
        env = dict(CONFIG=cfg, openrouter_client=object(), dataset_root='dataset', run_paths={},
            COLLECTION_MODELS=selected, ACTIVE_MODELS=cfg['models'], EXPECTED_CASES=3, RUN_LABEL='expanded',
            CONCURRENCY=1, RETRY_AUTHORIZATION=cfg['retry_authorization'], AUTO_SPACED_REPAIR=True,
            ADMISSION_RECEIPT=dict(inherited_unresolved=inherited, inherited_failure_inventory=inherited),
            radle_collection_admission=SimpleNamespace(combined_audit=lambda *args: audit),
            radle_benchmark=object(), run_autonomous_openrouter_workflow=workflow)
        with contextlib.redirect_stdout(io.StringIO()): exec(source, env)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['models'], selected)
        self.assertEqual(env['AUTO_WORKFLOW_RESULT']['unresolved_pairs'], inherited)
        self.assertEqual(env['AUTO_WORKFLOW_RESULT']['status'], 'completed_with_unresolved')


if __name__ == '__main__': unittest.main()
