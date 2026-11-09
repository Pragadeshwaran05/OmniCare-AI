with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        low = line.lower()
        if any(k in low for k in ['<form', 'upload', 'prescri', 'delete', 'edit', 'modal']):
            if i < 200:
                print(f"{i+1}: {line.strip()}")
