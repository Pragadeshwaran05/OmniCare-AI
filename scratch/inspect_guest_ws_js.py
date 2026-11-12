with open('static/js/guest_patient_workspace.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'could not process' in l.lower() or 'ai-assistant' in l:
        print(f'{i+1}: {l.strip()[:100]}')
