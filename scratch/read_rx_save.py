with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(6840, min(6900, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')
