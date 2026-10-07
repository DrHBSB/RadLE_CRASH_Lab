import unittest, tempfile, json, hashlib, sys
from pathlib import Path
from types import SimpleNamespace
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import radle_budget_seed as seed

class BudgetMigration(unittest.TestCase):
    def test_preserves_answers_flags_attempts_and_old_files(self):
        with tempfile.TemporaryDirectory() as temp:
            old=Path(temp)/'old';raw=old/'raw';raw.mkdir(parents=True)
            models=[{'name':'gpt','require_readable_reasoning':True}]
            rows=[{'Master_Case_ID':str(i),'Image_SHA256':'hash'+str(i),'Diagnosis_gpt':''} for i in range(1,201)]
            rows[0].update(Diagnosis_gpt='saved',Reasoning_gpt='readable')
            rows[1].update(Diagnosis_gpt='flagged',Reasoning_gpt='')
            source=raw/'results.csv';pd.DataFrame(rows).fillna('').to_csv(source,index=False)
            folder=Path(str(source)+'.concurrent');(folder/'queue').mkdir(parents=True)
            (folder/'baseline.csv').write_bytes(source.read_bytes())
            contract={'models':models,'prompt_sha256':hashlib.sha256(b'prompt').hexdigest(),'output_cap':16384,'images':{str(i):'hash'+str(i) for i in range(1,201)}}
            (old/'collection_contract.json').write_text(json.dumps(contract))
            key=json.dumps(['3','gpt'],separators=(',',':'))
            events=[{'type':'start','key':key,'attempt':1},{'type':'result','key':key,'status':'terminal','value':{'fields':{'Diagnosis_gpt':''}}}]
            journal=folder/'queue/events.jsonl';journal.write_text(''.join(json.dumps(e)+'\n' for e in events))
            (raw/'replacement_history.json').write_text(json.dumps({'previous_attempts':{key:2}}))
            rb=SimpleNamespace(PROMPT='prompt',rebuild_base_row=lambda case,images:dict(Master_Case_ID=case,Image_SHA256='hash'+case),atomic_to_csv=lambda df,path:df.to_csv(path,index=False),requires_positive_token_usage=lambda m:True,classify_cell_for_audit=lambda row,*a,**kw:{'needs_api_repair':not bool(row.get('Diagnosis_gpt'))})
            old_bytes=source.read_bytes(),journal.read_bytes()
            output=Path(temp)/'new/raw/results.csv'
            receipt=seed.prepare(rb,old,output,models,{str(i):[] for i in range(1,201)})
            saved=pd.read_csv(output,keep_default_na=False)
            self.assertEqual(saved.iloc[0]['Diagnosis_gpt'],'saved')
            self.assertEqual(saved.iloc[1]['Diagnosis_gpt'],'flagged')
            self.assertEqual(saved.iloc[1]['Reasoning_gpt'],'')
            self.assertEqual(receipt['migration']['initial_attempts'][key],1)
            self.assertEqual(receipt['previous_attempts'][key],3)
            self.assertEqual(receipt['baseline_output_cap'],16384)
            self.assertEqual(receipt['reused_answers'],2)
            self.assertEqual(seed.prepare(rb,old,output,models,{}),receipt)
            self.assertEqual((source.read_bytes(),journal.read_bytes()),old_bytes)

    def test_notebook_uses_two_attempts_without_third(self):
        notebook=json.loads((Path(__file__).resolve().parents[1]/'notebooks/RadLE_v1_5_Morning.ipynb').read_text(encoding='utf-8'))
        source=''.join(notebook['cells'][3]['source'])
        self.assertIn('max_attempts=2, migration=COLLECTION_MIGRATION, repair_once=False',source)
        self.assertIn('max_output_tokens=32768',source)
