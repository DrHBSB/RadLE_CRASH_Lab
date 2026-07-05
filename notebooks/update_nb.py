import json

filepath = r'c:\Users\thehb\Documents\RadLE v2\notebooks\RadLE_Medical_Workbench_Runtime.ipynb'
with open(filepath, 'r', encoding='utf-8') as f:
    data = json.load(f)

for cell in data.get('cells', []):
    if cell.get('cell_type') == 'code':
        source = cell.get('source', '')
        if isinstance(source, list):
            source_str = ''.join(source)
        else:
            source_str = source
            
        if 'TENSOR_PARALLEL_SIZE = 1' in source_str:
            new_source = source_str.replace('TENSOR_PARALLEL_SIZE = 1', 'TENSOR_PARALLEL_SIZE = 2')
            new_source = new_source.replace('EXTRA_SERVER_ARGS = ["--dtype", "float16"]', 'EXTRA_SERVER_ARGS = ["--dtype", "bfloat16"]')
            new_source = new_source.replace('# T4 has limited VRAM and no BF16 support. Keep the first smoke small.', '# L4 GPUs support bfloat16 and have 24GB VRAM each. Use both GPUs and modern dtype.')
            
            if isinstance(source, list):
                lines = new_source.split('\n')
                cell['source'] = [line + '\n' for line in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
            else:
                cell['source'] = new_source

with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=1)

print('Updated successfully.')
