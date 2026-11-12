with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(7550, min(7635, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')
