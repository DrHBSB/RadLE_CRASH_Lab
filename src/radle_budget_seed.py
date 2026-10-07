"""Carry a drained collection into a larger output budget without resetting attempts."""
import csv, hashlib, json, shutil
from pathlib import Path
import pandas as pd

def prepare(rb, old_root, new_csv, models, image_index):
    old_root, new_csv = Path(old_root), Path(new_csv)
    receipt_path = new_csv.parent / 'replacement_history.json'
    if new_csv.exists():
        if not receipt_path.exists():
            raise RuntimeError('Budget migration output exists without receipt')
        return json.loads(receipt_path.read_text(encoding='utf-8'))
    contract = json.loads((old_root/'collection_contract.json').read_text())
    if contract['models'] != models or contract['prompt_sha256'] != hashlib.sha256(rb.PROMPT.encode()).hexdigest():
        raise RuntimeError('Budget migration model or prompt contract differs')
    base = {str(i):rb.rebuild_base_row(str(i), image_index[str(i)]) for i in range(1,201)}
    if contract['images'] != {k:v['Image_SHA256'] for k,v in base.items()}:
        raise RuntimeError('Budget migration image hashes differ')
    source_csv=old_root/'raw/results.csv'
    folder=Path(str(source_csv)+'.concurrent')
    journal=folder/'queue/events.jsonl'
    data=journal.read_bytes()
    if not data.endswith(b'\n'):raise RuntimeError('Incomplete source journal tail')
    events=[json.loads(line) for line in data.splitlines()]
    csv.field_size_limit(20000000)
    with (folder/'baseline.csv').open(encoding='utf-8-sig',newline='') as handle:
        rows={row['Master_Case_ID']:row for row in csv.DictReader(handle)}
    if set(rows)!=set(base):raise RuntimeError('Budget migration case roster differs')
    starts={}; states={}; limits={}
    for event in events:
        kind=event.get('type')
        if kind not in {'start','result'}:continue
        key=event['key']; case,name=json.loads(key)
        if kind=='start':
            starts[key]=starts.get(key,0)+1;states[key]='uncertain'
        else:
            states[key]=event['status']
            rows[case].update(event['value'].get('fields',{}))
            limits[key]=contract['output_cap']
    held=[key for key,status in states.items() if status in {'uncertain','blocked','quota','rejected','failed'}]
    if held:raise RuntimeError('Source requests need review before migration: '+str(held))
    previous=json.loads((source_csv.parent/'replacement_history.json').read_text()).get('previous_attempts',{})
    for key,count in starts.items():previous[key]=previous.get(key,0)+count
    for case,row in rows.items():
        for column,value in base[case].items():
            if str(row.get(column,''))!=str(value):raise RuntimeError('Source case identity differs')
    new_csv.parent.mkdir(parents=True,exist_ok=True)
    rb.atomic_to_csv(pd.DataFrame(list(rows.values())),str(new_csv))
    reused=sum(bool(row.get('Diagnosis_'+model['name'])) and not rb.classify_cell_for_audit(pd.Series(row),model['name'],attempts=0,max_output_tokens=32768,require_token_usage=rb.requires_positive_token_usage(model),require_readable_reasoning=model.get('require_readable_reasoning',False)).get('needs_api_repair') for row in rows.values() for model in models)
    migration={'baseline_sha256':hashlib.sha256(new_csv.read_bytes()).hexdigest(),'initial_attempts':starts,'uncertain_jobs':[]}
    receipt={'old_run':str(old_root),'previous_attempts':previous,'reused_answers':reused,'migration':migration,'baseline_output_cap':contract['output_cap'],'baseline_result_caps':limits,'old_journal_sha256':hashlib.sha256(data).hexdigest(),'policy':'32,768 output tokens; two collection attempts including carried starts; no automatic third attempt; preserve readable-reasoning flags.'}
    archive=new_csv.parent/'superseded_evidence';archive.mkdir(exist_ok=True)
    for file in [source_csv,journal,old_root/'collection_contract.json',source_csv.parent/'replacement_history.json']:
        shutil.copyfile(file,archive/file.name)
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt
