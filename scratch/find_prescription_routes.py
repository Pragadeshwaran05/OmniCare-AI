with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'save_prescription' in l.lower() or 'prescription' in l.lower() and ('def ' in l or 'insert' in l or 'route' in l):
        print(f'{i+1}: {l.strip()[:100]}')
