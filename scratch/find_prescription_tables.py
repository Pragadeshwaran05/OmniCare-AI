import glob

for f in glob.glob('**/*.py', recursive=True):
    if 'venv' in f or '.git' in f: continue
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        for i, line in enumerate(fp):
            if 'table(' in line and 'prescription' in line.lower():
                print(f'{f}:{i+1}: {line.strip()[:100]}')
