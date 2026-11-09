with open('templates/doctor/patient_workspace.html', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    l = line.lower()
    if 'medical records' in l or 'tab-records' in l or 'tab_records' in l or 'data-tab="records"' in l or 'id="records"' in l or 'id="tab-medical-records"' in l:
        print(f"L{idx+1}: {line.strip()[:100]}")
