with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'ai-assistant' in l or 'ai-send' in l:
        print(f'{i+1}: {l.strip()[:100]}')
