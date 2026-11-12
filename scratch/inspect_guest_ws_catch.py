with open('static/js/guest_patient_workspace.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(990, min(1025, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')
