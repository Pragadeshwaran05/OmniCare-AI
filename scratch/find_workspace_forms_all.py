with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        low = line.lower()
        if '<form' in low or 'action=' in low or '<button' in low:
            print(f"{i+1}: {line.strip()[:80]}")
