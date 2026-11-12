with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(7350, min(7430, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')
