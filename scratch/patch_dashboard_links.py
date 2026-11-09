with open('templates/doctor/doctor_dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace url_for('doctor_access') for Search Patient and Find Patient
text = text.replace(
    'href="{{ url_for(\'doctor_access\') }}"\n               class="workspace-card"',
    'href="{{ url_for(\'doctor_patient_access\') }}"\n               class="workspace-card"'
)

text = text.replace(
    'href="{{ url_for(\'doctor_access\') }}"\n               class="primary-button"',
    'href="{{ url_for(\'doctor_patient_access\') }}"\n               class="primary-button"'
)

with open('templates/doctor/doctor_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated doctor_dashboard.html successfully!")
