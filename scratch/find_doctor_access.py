with open('app.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'doctor_access' in line and 'def ' in line:
            print(f'{i+1}: {line.strip()}')
        elif 'endpoint="doctor_access"' in line or 'endpoint=\'doctor_access\'' in line:
            print(f'{i+1}: {line.strip()}')
