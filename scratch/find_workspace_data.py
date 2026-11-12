with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'def doctor_patient_workspace(' in l:
        print(f"Line {i+1}: {l.strip()}")
        for j in range(i, min(i+100, len(lines))):
            print(f'{j+1}: {lines[j]}', end='')
        break
