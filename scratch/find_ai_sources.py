with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'ai-sources' in l or 'ai_sources' in l:
        print(f'{i+1}: {l.strip()[:100]}')
