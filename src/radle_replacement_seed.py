"""Prepare a new provider/reasoning contract without editing the previous run."""
import csv, hashlib, json
from pathlib import Path
import pandas as pd

PREFIXES = ['Diagnosis','Likert','Prompt_Tokens','Total_Tokens_Out','Reasoning_Tokens','Latency','Provider','Timestamp_UTC','Reasoning','Reasoning_Raw','Reasoning_Details','Actual_Request_Extra','Grok_Fallback_Used','OpenRouter_Response_Model','Usage_JSON','Raw_Response']
GPT = {'gpt_6_sol','gpt_6_1_sol_pro'}

def prepare(rb, old_root, new_csv, models, image_index):
    old_root, new_csv = Path(old_root), Path(new_csv)
    receipt_path = new_csv.parent / 'replacement_history.json'
    if new_csv.exists():
        if not receipt_path.exists():
            raise RuntimeError('Replacement output exists without history receipt')
        return json.loads(receipt_path.read_text(encoding='utf-8'))
    csv.field_size_limit(20000000)
    contract = json.loads((old_root/'collection_contract.json').read_text())
    if contract['prompt_sha256'] != hashlib.sha256(rb.PROMPT.encode()).hexdigest() or contract['output_cap'] != 16384:
        raise RuntimeError('Previous prompt or output cap differs')
    base = {str(i): rb.rebuild_base_row(str(i),image_index[str(i)]) for i in range(1,201)}
    if contract['images'] != {k:v['Image_SHA256'] for k,v in base.items()}:
        raise RuntimeError('Previous image hashes differ')
    source_csv = old_root/'raw/results.csv'
    with source_csv.open(encoding='utf-8-sig',newline='') as f:
        rows={r['Master_Case_ID']:r for r in csv.DictReader(f)}
    if set(rows)!=set(base):raise RuntimeError('Previous case roster differs')
    journal=Path(str(source_csv)+'.concurrent')/'queue/events.jsonl'
    events=[json.loads(l) for l in journal.read_text(encoding='utf-8').splitlines()]
    previous={}; ended=set()
    for e in events:
        if e.get('type')=='start':previous[e['key']]=previous.get(e['key'],0)+1
        if e.get('type')=='result':
            ended.add(e['key']);case,name=json.loads(e['key']);rows[case].update(e['value'].get('fields',{}))
    # Pilot history includes one completed call per model and a documented second GPT Sol call.
    pilot=old_root.with_name(old_root.name+'_pilot_1')/'raw/results.csv'
    if pilot.exists():
        with pilot.open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):
                for m in models:
                    name=m['name']
                    if r.get('Diagnosis_'+name):
                        k=json.dumps([r['Master_Case_ID'],name],separators=(',',':'))
                        previous[k]=previous.get(k,0)+(2 if name=='gpt_6_sol' else 1)
    previous={json.dumps(json.loads(k),separators=(',',':')):v for k,v in previous.items()}
    reused=0; cleared=[]
    for case,row in rows.items():
        for m in models:
            n=m['name'];cols=[p+'_'+n for p in PREFIXES];keep=False
            if n not in GPT:
                try:
                    keep=(row.get('Provider_'+n)==m['expected_provider'] and row.get('OpenRouter_Response_Model_'+n) in m['expected_returned_model_ids'] and json.loads(row.get('Actual_Request_Extra_'+n) or '{}')==dict(m['extra'],provider=m['provider_routing']) and rb.classify_cell_for_audit(pd.Series(row),n,attempts=0,max_output_tokens=16384,require_token_usage=True,require_readable_reasoning=True)['bucket']=='accepted')
                except (ValueError,TypeError):pass
            if keep:
                base[case].update({c:row.get(c,'') for c in cols});reused+=1
            else:
                base[case].update({c:'' for c in cols})
                k=json.dumps([case,n],separators=(',',':'))
                if k in previous:cleared.append({'case':case,'model':n,'prior_attempts':previous[k]})
    receipt={'old_run':str(old_root),'old_csv_sha256':hashlib.sha256(source_csv.read_bytes()).hexdigest(),'old_journal_sha256':hashlib.sha256(journal.read_bytes()).hexdigest(),'previous_attempts':previous,'reused_answers':reused,'replacement_pairs':cleared,'unknown_previous_starts':[json.loads(k) for k in previous if k not in {json.dumps(json.loads(x),separators=(',',':')) for x in ended} and json.loads(k)[0]!='1'],'policy':'Both GPT arms replaced from case 1; one new attempt; readable reasoning mandatory; preserve old evidence; no automatic repairs.'}
    new_csv.parent.mkdir(parents=True,exist_ok=True)
    archive=new_csv.parent/'superseded_evidence';archive.mkdir(exist_ok=True)
    (archive/'events.jsonl').write_bytes(journal.read_bytes());(archive/'results.csv').write_bytes(source_csv.read_bytes())
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    rb.atomic_to_csv(__import__('pandas').DataFrame(list(base.values())),str(new_csv))
    return receipt
