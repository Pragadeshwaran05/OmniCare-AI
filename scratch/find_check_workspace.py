with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'def check_workspace_access' in l:
        print(f"Line {i+1}: {l.strip()}")
        for j in range(i, min(i+60, len(lines))):
            print(f'{j+1}: {lines[j]}', end='')
        break
