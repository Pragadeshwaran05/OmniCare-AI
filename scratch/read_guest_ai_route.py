with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(8945, min(9030, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')
