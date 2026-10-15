import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import radle_attempt_artifacts as aa
import radle_job_queue as q
import radle_benchmark as rb
from radle_attempt_ledger import read_ledger
import test_concurrent_collection as fixtures


class ArtifactTests(unittest.TestCase):
    def test_private_full_response_and_small_journal_replay(self):
        f = fixtures.IntegrationTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.client.chat.completions.create.side_effect = lambda **_: f.response('x' * 5000, 'private reasoning')
        with contextlib.redirect_stdout(io.StringIO()):
            f.run_collection(max_attempts=2, concurrency=1)
        journal = Path(str(f.output) + '.concurrent/queue/events.jsonl')
        data = journal.read_bytes()
        self.assertNotIn(b'private reasoning', data)
        self.assertIn(b'value_reference', data)
        manifest = json.loads(data.splitlines()[0])
        states = q.replay(journal, manifest)
        state = next(iter(states.values()))
        envelope = aa.read_verified(state['value']['response_receipt'])
        self.assertGreater(len(envelope['payload']['choices'][0]['message']['content']), 5000)
        self.assertEqual(len(state['value']['fields']['Raw_Response_any_model']), 2000)
        ledger = read_ledger(journal, manifest)
        self.assertEqual(sum(r['event'] == 'start' for r in ledger), 3)
        self.assertTrue(all(not r['remote_execution_proven'] for r in ledger))
        # Both original reasoning settings and request token limit are untouched.
        for call in f.client.chat.completions.create.call_args_list:
            self.assertEqual(call.kwargs['max_tokens'], 16384)
            self.assertEqual(call.kwargs['extra_body'], rb.build_api_params(f.models[0], [], 16384, None)['extra_body'])
        receipt = state['value']['response_receipt']
        Path(receipt['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            aa.read_verified(receipt)

    def test_received_response_survives_local_parser_failure(self):
        f = fixtures.IntegrationTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        with patch.object(rb, 'extract_result', side_effect=ValueError('parser fixture')), contextlib.redirect_stdout(io.StringIO()):
            f.run_collection(max_attempts=2, concurrency=1, allow_partial_result=True)
        self.assertEqual(f.client.chat.completions.create.call_count, 1)
        journal = Path(str(f.output) + '.concurrent/queue/events.jsonl')
        state = next(s for s in q.replay(journal, json.loads(journal.read_bytes().splitlines()[0])).values()
                     if s['status'] == 'blocked')
        self.assertTrue(state['value']['response_received'])
        self.assertEqual(state['value']['execution_stage'], 'local_response_processing')
        self.assertEqual(aa.read_verified(state['value']['response_receipt'])['payload']['id'], 'fixture')

    def test_archive_failure_before_dispatch_sends_no_request(self):
        f = fixtures.IntegrationTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        with patch.object(aa, 'persist', side_effect=OSError('disk fixture')), contextlib.redirect_stdout(io.StringIO()):
            f.run_collection(max_attempts=2, concurrency=1, allow_partial_result=True)
        f.client.chat.completions.create.assert_not_called()

    def test_responses_identity_status_and_original_envelope_survive(self):
        data = dict(id='response-fixture', status='incomplete', model='fixture',
                    incomplete_details={'reason':'max_output_tokens'}, provider='Provider',
                    output=[], usage={'output_tokens':32768,'output_tokens_details':{'reasoning_tokens':32768}})
        normalized = rb.normalize_openrouter_responses_response(data, {})
        self.assertEqual(normalized.id, 'response-fixture')
        self.assertEqual(normalized.response_status, 'incomplete')
        self.assertEqual(normalized._radle_original_response, data)
        metadata = aa.response_metadata(data)
        self.assertEqual(metadata['incomplete_reason'], 'max_output_tokens')
        self.assertEqual(metadata['content_length'], 0)
        self.assertEqual(metadata['reasoning_tokens'], 32768)

    def test_responses_archive_precedes_provider_enrichment(self):
        data = dict(id='response-fixture', status='completed', output=[], usage={})
        client = Mock()
        client.responses.create.return_value = SimpleNamespace(model_dump=lambda **_: data)
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(rb, 'enrich_openrouter_provider', side_effect=ValueError('fixture')):
                with self.assertRaises(ValueError):
                    rb.call_openrouter_responses(client, {}, {'response_archive_dir':folder})
            saved = list(Path(folder).glob('*.response_received.*.json'))
            self.assertEqual(len(saved), 1)
            self.assertEqual(json.loads(saved[0].read_text())['payload']['id'], 'response-fixture')

    def test_content_blocks_and_missing_usage(self):
        self.assertEqual(aa.chat_final_text([{'type':'text','text':'a'}, {'type':'text','text':'b'}]), 'ab')
        self.assertEqual(aa.chat_final_text(None), '')
        with self.assertRaises(ValueError):
            aa.chat_final_text([{'type':'unknown','text':'not an answer'}])
        metadata = aa.response_metadata({'choices':[{'message':{'content':None}}]})
        self.assertIsNone(metadata['completion_tokens'])
        self.assertEqual(metadata['content_length'], 0)

    def test_known_secret_redacted_and_wrong_result_reference_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            ident = aa.new_identity('1', 'm', 1, {})
            receipt = aa.persist(folder, ident, 'response_received',
                                 {'api_key':'key-fixture', 'text':'echo key-fixture'},
                                 sensitive_values=('key-fixture',))
            self.assertNotIn('key-fixture', Path(receipt['path']).read_text())
            with self.assertRaises(ValueError):
                q.resolve_event({'type':'result','key':q.Job('1','m',{}).key,
                                 'attempt':1,'value_reference':{'file':'../escape','sha256':'x'}},
                                Path(folder) / 'queue' / 'events.jsonl')

    def test_exact_token_cap_stop_not_repeated_automatically(self):
        f = fixtures.IntegrationTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        response = f.response()
        response.choices[0].message.content = None
        response.choices[0].finish_reason = 'length'
        response.usage.completion_tokens = 16384
        f.client.chat.completions.create.side_effect = lambda **_: response
        with contextlib.redirect_stdout(io.StringIO()):
            f.run_collection(max_attempts=2, concurrency=1, allow_partial_result=True)
        # One call per case, without consuming a second identical attempt.
        self.assertEqual(f.client.chat.completions.create.call_count, 3)
        journal = Path(str(f.output) + '.concurrent/queue/events.jsonl')
        states = q.replay(journal, json.loads(journal.read_bytes().splitlines()[0]))
        self.assertTrue(all(s['status'] == 'terminal' and s['attempts'] == 1 for s in states.values()))

    def test_ledger_keeps_corruption_finding_and_does_not_double_count_archive(self):
        from radle_journal_recovery import recover, sha
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            queue_dir = root / 'queue'
            jobs = [q.Job('1','m',{})]
            result = q.run(jobs, lambda *_: q.Outcome('terminal', {}), queue_dir, max_attempts=2)
            journal = queue_dir / 'events.jsonl'
            manifest = json.loads(journal.read_bytes().splitlines()[0])
            csv = root / 'results.csv'
            csv.write_text('Master_Case_ID,Diagnosis_m,Raw_Response_m\n1,,\n')
            checkpoint = root / 'checkpoint.json'
            checkpoint.write_text(json.dumps({'csv_sha256':sha(csv),'states':{
                jobs[0].key:{'status':'terminal','attempts':1}}}))
            with journal.open('ab') as stream:
                stream.write(b'broken\n')
            recover(q, journal, manifest, csv, checkpoint)
            before = journal.read_bytes()
            ledger = read_ledger(journal, manifest)
            self.assertEqual(sum(r['event']=='start' for r in ledger), 1)
            self.assertEqual(sum(r['event']=='malformed_line' for r in ledger), 1)
            self.assertEqual(journal.read_bytes(), before)

    def test_compact_results_preserve_all_repair_grants_through_recovery(self):
        from radle_journal_recovery import recover, sha
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            jobs = [q.Job('1', 'm', {})]
            def call(job, attempt):
                ident = aa.new_identity(job.case, job.model, attempt, {})
                receipt = aa.persist(root / 'attempt_artifacts', ident, 'response_received',
                                     {'id':'fixture','choices':[{'message':{'content':''}}]})
                return q.Outcome('retry', {'request_identity':ident, 'response_receipt':receipt,
                                          'response_metadata':{'content_length':0}, 'fields':{}})
            q.run(jobs, call, root / 'queue', max_attempts=2)
            for number in (1, 2, 3, 4):
                q.run(jobs, call, root / 'queue', max_attempts=2, repair_once=True,
                      repair_round=number, resume_blocked=True)
            journal = root / 'queue' / 'events.jsonl'
            manifest = json.loads(journal.read_bytes().splitlines()[0])
            csv = root / 'results.csv'
            csv.write_text('Master_Case_ID,Diagnosis_m,Raw_Response_m\n1,,\n')
            checkpoint = root / 'checkpoint.json'
            checkpoint.write_text(json.dumps({'csv_sha256':sha(csv), 'states':{
                jobs[0].key:{'status':'failed','attempts':6}}}))
            with journal.open('ab') as stream:
                stream.write(b'broken\n')
            states = recover(q, journal, manifest, csv, checkpoint)
            self.assertEqual(states[jobs[0].key]['repair_round'], 4)
            self.assertEqual(states[jobs[0].key]['repair_attempt'], 6)
            self.assertEqual(q.replay(journal, manifest), states)
            q.run(jobs, lambda *_: self.fail('paid retry repeated'), root / 'queue',
                  max_attempts=2, repair_once=True, repair_round=4, resume_blocked=True)

    def test_typed_credit_limit_stops_despite_positive_account_balance(self):
        f = fixtures.IntegrationTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        class LimitError(Exception):
            status_code = 402
            body = {'error':{'metadata':{'limit_source':'openrouter_key_limit'}}}
            response = SimpleNamespace(headers={'retry-after':'12'})
        f.client.chat.completions.create.side_effect = LimitError()
        import radle_concurrent_collection as cc
        with patch.object(cc, 'check_openrouter_funds', return_value={'status':'available'}), contextlib.redirect_stdout(io.StringIO()):
            f.run_collection(max_attempts=2, concurrency=1, allow_partial_result=True)
        self.assertEqual(f.client.chat.completions.create.call_count, 1)
        journal = Path(str(f.output) + '.concurrent/queue/events.jsonl')
        states = q.replay(journal, json.loads(journal.read_bytes().splitlines()[0]))
        state = next(s for s in states.values() if s['status'] == 'quota')
        self.assertEqual(state['value']['limit_source'], 'openrouter_key_limit')
        self.assertEqual(state['value']['retry_after_header'], '12')

    def test_structured_response_envelope_supplies_evidence_without_old_csv_join(self):
        from radle_error_evidence import evidence_record, retry_review
        with tempfile.TemporaryDirectory() as folder:
            ident = aa.new_identity('1','m',1,{})
            receipt = aa.persist(folder, ident, 'response_received',
                                 {'id':'fixture','choices':[{'finish_reason':'length','message':{'content':None}}],
                                  'usage':{'completion_tokens':32768,'completion_tokens_details':{'reasoning_tokens':32768}}})
            state = {'status':'failed','attempts':1,'value':{'response_receipt':receipt}}
            record = evidence_record(q.Job('1','m',{}).key, state)
            self.assertEqual(record['response_evidence_source'], 'verified_response_artifact')
            self.assertEqual(record['content_length'], 0)
            review = retry_review(q.Job('1','m',{}).key, state)
            self.assertEqual(review['review_action'], 'retain_output_limit_failure_no_identical_retry')
            self.assertFalse(review['new_request_authorized'])
