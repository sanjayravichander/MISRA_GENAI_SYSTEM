from pathlib import Path

p = Path(r'..\output_processed_01\misra_kb_output\misra_kb_chunks.jsonl')
print('File exists:', p.exists())

if p.exists():
    print('File size bytes:', p.stat().st_size)
    with p.open('r', encoding='utf-8') as f:
        lines = [l for l in f if l.strip()]
    print('Line count:', len(lines))
    if lines:
        print('First line preview:', lines[0][:120])
    else:
        print('FILE IS EMPTY')
else:
    print('FILE NOT FOUND - checking parent folder...')
    parent = Path(r'..\output_processed_01\misra_kb_output')
    print('Folder exists:', parent.exists())
    if parent.exists():
        print('Files in folder:')
        for f in parent.iterdir():
            print(' ', f.name, f.stat().st_size, 'bytes')