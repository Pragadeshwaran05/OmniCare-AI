with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for j in range(4540, min(4580, len(lines))):
    print(f'{j+1}: {lines[j]}', end='')
