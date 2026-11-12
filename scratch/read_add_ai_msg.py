import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'function addDoctorAIMessage(' in l:
        print(f"addDoctorAIMessage starts at line {i+1}")
        for j in range(i, min(i+80, len(lines))):
            print(f'{j+1}: {lines[j]}', end='')
        break
