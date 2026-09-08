import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import httpx
from openai import OpenAI, PermissionDeniedError
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import radle_benchmark as rb

class AstraHttpErrorTests(unittest.TestCase):
    def client(self):
        calls=[]
        def refused(request):
            calls.append(request)
            return httpx.Response(403, json={"error": {
                "message": "Provider refused fixture-key data:image/png;base64,YWJj",
                "code": "moderation_blocked", "authorization": "fixture-key",
                "metadata": {"reason": "content_policy", "api_key": "fixture-key"}}})
        return OpenAI(api_key="fixture-key", base_url="https://fixture.invalid/v1", max_retries=0,
                      http_client=httpx.Client(transport=httpx.MockTransport(refused))), calls

    def test_http_rejection_before_stream_is_archived_with_secrets_redacted(self):
        with tempfile.TemporaryDirectory() as folder:
            client,calls=self.client()
            with client, self.assertRaises(PermissionDeniedError) as caught:
                rb.call_openrouter_responses(client, {"model":"fixture-model", "input":"synthetic", "stream":True},
                                             {"response_archive_dir":folder})
            self.assertEqual(len(calls),1)
            path=Path(caught.exception.radle_archive)
            self.assertTrue(path.name.endswith(".error.json"))
            text=path.read_text(encoding="utf-8"); evidence=json.loads(text)
            self.assertEqual(evidence["http_status"],403)
            self.assertEqual(evidence["body"]["code"],"moderation_blocked")
            self.assertNotIn("fixture-key",text)
            self.assertNotIn("YWJj",text)
            self.assertNotIn("authorization",text)
            self.assertNotIn("api_key",text)

    def test_archive_failure_keeps_original_http_exception(self):
        with tempfile.TemporaryDirectory() as folder:
            client,calls=self.client()
            with client, patch.object(Path,"open",side_effect=OSError("disk unavailable")):
                with self.assertRaises(PermissionDeniedError) as caught:
                    rb.call_openrouter_responses(client,{"model":"fixture-model","input":"synthetic","stream":True},
                                                 {"response_archive_dir":folder})
            self.assertEqual(caught.exception.status_code,403)
            self.assertEqual(caught.exception.radle_archive_error,"OSError")
            self.assertEqual(len(calls),1)

    def test_only_explicit_case_errors_are_classified_as_case_rejections(self):
        bodies=[{'error':{'metadata':{'error_type':'content_policy_violation'}}},
                {'error_type':'invalid_image','error':{'code':'server_error'}},
                {'error':{'code':'image_content_policy_violation'}},
                {'error':{'metadata':{'reasons':['flagged'],'flagged_input':'private snippet'}}}]
        for body in bodies:
            with self.subTest(body=body):
                diagnostic=rb.case_rejection_diagnostic(body)
                self.assertEqual(diagnostic['category'],'case_rejected')
                self.assertNotIn('private snippet',str(diagnostic))
        for body in [None, {'error':{'code':403,'message':'Forbidden'}},
                     {'error_type':'permission_denied'}, {'error_type':'payment_required'},
                     {'error_type':'authentication','error':{'code':'image_content_policy_violation'}}]:
            self.assertIsNone(rb.case_rejection_diagnostic(body))

    def test_stream_rejection_preserves_typed_case_reason(self):
        for event in [{'type':'response.failed','response':{'status':'failed','error_type':'content_policy_violation','error':{'code':'server_error'}}},
                      {'type':'response.error','error':{'code':'image_content_policy_violation'}}]:
            with self.subTest(event=event), self.assertRaises(RuntimeError) as caught:
                rb.collect_openrouter_response_stream([event])
            self.assertEqual(caught.exception.radle_diagnostic['category'],'case_rejected')

    def test_without_archive_directory_no_write_or_retry(self):
        client,calls=self.client()
        with client, self.assertRaises(PermissionDeniedError) as caught:
            rb.call_openrouter_responses(client,{"model":"fixture-model","input":"synthetic","stream":True},{})
        self.assertFalse(hasattr(caught.exception,"radle_archive"))
        self.assertEqual(len(calls),1)

if __name__=="__main__":unittest.main()
