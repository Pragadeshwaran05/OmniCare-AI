import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(6580, min(6630, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')
