import glob

for f in glob.glob('**/*.py', recursive=True):
    if 'venv' in f or '.git' in f: continue
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        for i, line in enumerate(fp):
            if 'ask_doctor_ai' in line:
                print(f'{f}:{i+1}: {line.strip()[:100]}')
