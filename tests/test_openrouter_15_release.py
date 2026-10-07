import sys,pathlib,json,copy,tempfile,unittest
from unittest.mock import Mock,patch
root=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
import radle_benchmark as rb
from radle_openrouter_15 import MODELS
from openai.types.chat import ChatCompletion
import pandas as pd

class Contracts(unittest.TestCase):
    def response(self,model,provider=None,returned=None):
        return ChatCompletion.model_validate(dict(id='synthetic',object='chat.completion',created=1,
            model=returned or model['id'],provider=provider or model['expected_provider'],
            choices=[dict(index=0,finish_reason='stop',message=dict(role='assistant',content='{"diagnosis":"synthetic finding","likert_score":3}',reasoning='synthetic summary'))],
            usage=dict(prompt_tokens=10,completion_tokens=20,total_tokens=30,completion_tokens_details=dict(reasoning_tokens=10))))
    def test_all_requests_and_route_guards(self):
        self.assertEqual(len(MODELS),15)
        for m in MODELS:
            p=rb.build_api_params(m,[{'type':'text','text':'synthetic'}],16384,.01)
            self.assertEqual(p[m['output_token_parameter']],16384)
            self.assertEqual(p['extra_body']['provider'],m['provider_routing'])
            self.assertEqual(p['extra_body']['reasoning'],m['extra']['reasoning'])
            self.assertFalse(set(p)&{'temperature','top_p','top_k'})
            fields=rb.extract_result(self.response(m),0,p,False,m)
            self.assertEqual(fields['Provider_'+m['name']],m['expected_provider'])
            with self.assertRaisesRegex(RuntimeError,'provider mismatch'):
                rb.extract_result(self.response(m,provider='Wrong'),0,p,False,m)
            with self.assertRaisesRegex(RuntimeError,'model mismatch'):
                rb.extract_result(self.response(m,returned='wrong/id'),0,p,False,m)
    def test_zero_repair_clean_returns_and_dirty_stops(self):
        kwargs=dict(client=None,image_folder='none',raw_csv='raw',repair_csv='repair',repair_call_log_csv='log',repair_plan_csv='plan',models=MODELS,max_passes=0)
        with patch.object(rb,'choose_repair_input_csv',return_value='raw'),patch.object(rb,'audit_benchmark_output',return_value={}):
            with patch.object(rb,'audit_repair_target_count',return_value=0):
                self.assertEqual(rb.run_repair_cascade_until_clean(**kwargs)['repair_passes'],0)
            with patch.object(rb,'audit_repair_target_count',return_value=1):
                with self.assertRaises(RuntimeError): rb.run_repair_cascade_until_clean(**kwargs)
    def test_notebook_cells(self):
        n=json.loads((root/'notebooks/RadLE_v1_5_Morning.ipynb').read_text(encoding='utf-8'))
        cells=[c for c in n['cells'] if c['cell_type']=='code']
        for c in cells:
            compile(''.join(c['source']),'<cell>','exec')
            self.assertFalse(c['outputs'])
        self.assertIn('max_retries=0',''.join(cells[1]['source']))
        self.assertIn('allow_missing_reasoning=False',''.join(cells[3]['source']))
    def test_config_initialization_resume_and_contract(self):
        import importlib
        from PIL import Image
        sys.path.insert(0,str(root/'scripts'))
        import smoke_openrouter_15_precolab as route
        n=json.loads((root/'notebooks/RadLE_v1_5_Morning.ipynb').read_text(encoding='utf-8'))
        source=''.join([c for c in n['cells'] if c['cell_type']=='code'][2]['source'])
        with tempfile.TemporaryDirectory() as temp:
            dataset=pathlib.Path(temp); images=dataset/'RadLE v2 Master Data'; images.mkdir()
            for i in range(1,201): Image.new('RGB',(2,2),'white').save(images/f'{i}.png')
            source=source.replace('Path("/content/drive/MyDrive/CRASH Lab/RaDLE/CONFIDENTIAL/RadLE v2 Dataset")',repr(str(dataset)))
            source=source.replace('dataset_root = '+repr(str(dataset)), 'dataset_root = Path('+repr(str(dataset))+')')
            ns=dict(importlib=importlib,REPO_DIR=root,REPO_REF='codex/radle-15-20261007',radle_benchmark=rb,_openrouter_key='synthetic')
            live=[dict(id=m['id'],image=True) for m in MODELS]
            with patch.object(route,'request_json',return_value=(200,{})),patch.object(route,'preflight',return_value=live):
                exec(source,ns); exec(source,ns)
                self.assertEqual(len(pd.read_csv(ns['final_output_csv'])),200)
                Image.new('RGB',(2,2),'black').save(images/'1.png')
                with self.assertRaisesRegex(RuntimeError,'contract differs'): exec(source,ns)

if __name__=='__main__': unittest.main()
