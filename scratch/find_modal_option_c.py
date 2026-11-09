import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('modalOptionC')
while idx != -1:
    line = text[:idx].count('\n') + 1
    print(f"Line {line}: {text[idx:idx+150]}")
    idx = text.find('modalOptionC', idx + 1)
