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

    def test_admission_matches_images_and_never_changes_source(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'Runs' / a.SOURCE_RUN / 'collection_contract.json'
            source.parent.mkdir(parents=True)
            ids = [str(i) for i in range(1, 201)]
            source.write_text(json.dumps(dict(case_ids=ids, images={i: 'hash-' + i for i in ids},
                prompt_sha256=hashlib.sha256(b'unchanged prompt').hexdigest(), output_cap=32768)))
            original = source.read_bytes()
            def paths(dataset, run_label, create_dirs=True):
                run = root / 'Runs' / run_label
                if create_dirs: (run / 'raw').mkdir(parents=True, exist_ok=True)
                return dict(run_root=str(run), raw_results_csv=str(run / 'raw/results.csv'),
                            master_images_folder=str(root / 'images'))
            rb = SimpleNamespace(PROMPT='unchanged prompt', build_run_paths=paths,
                build_image_index=lambda _: {i: i for i in ids},
                rebuild_base_row=lambda i, _: {'Image_SHA256': 'hash-' + i})
            route = dict(verified=True)
            prepared = a.prepare(rb, root, route)
            a.prepare(rb, root, route)
            self.assertEqual(source.read_bytes(), original)
            self.assertNotEqual(Path(prepared['run_root']), source.parent)
            target = Path(prepared['run_root']) / 'collection_contract.json'
            self.assertEqual(json.loads(target.read_text())['ordinary_attempts'], 2)
            rb.PROMPT = 'changed'
            with self.assertRaises(RuntimeError): a.prepare(rb, root, route)
            self.assertEqual(source.read_bytes(), original)

    def test_notebook_compiles_isolated_and_preserves_old_notebook(self):
        nb = json.loads((ROOT / 'notebooks/RadLE_Gemini_4_Argon.ipynb').read_text(encoding='utf-8'))
        self.assertEqual(len(nb['cells']), 4)
        sources = [''.join(c['source']) for c in nb['cells']]
        for i, source in enumerate(sources): compile(source, f'cell-{i}', 'exec')
        self.assertIn('codex/radle-argon4-colab-20261016', sources[0])
        self.assertNotIn('radle_budget_seed', sources[2])
        self.assertNotIn('retire_legacy_locks', sources[2])
        self.assertIn('max_job_attempts=2', sources[3])
        self.assertIn('promote_private=False, export_public=False', sources[3])
        self.assertIn('run_autonomous_openrouter_workflow', sources[3])


if __name__ == '__main__': unittest.main()
