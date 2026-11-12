with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'doctorAIPatientId' in l or 'sendDoctorAIMessage' in l or 'ai-assistant-tab' in l:
        print(f'{i+1}: {l.strip()[:100]}')
