import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'async function sendDoctorAIMessage(' in l:
        print(f"sendDoctorAIMessage starts at line {i+1}")
        for j in range(i, min(i+400, len(lines))):
            if 'function ' in lines[j] and j > i:
                print(f"Next function at line {j+1}: {lines[j].strip()}")
                break
            print(f'{j+1}: {lines[j]}', end='')
        break
