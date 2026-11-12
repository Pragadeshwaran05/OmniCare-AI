with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(6705, min(7430, len(lines))):
    l = lines[i].strip()
    if any(k in l for k in ['try {', '} catch', '} finally', 'addDoctorAIMessage', 'fetch(']):
        print(f'{i+1}: {l}')
