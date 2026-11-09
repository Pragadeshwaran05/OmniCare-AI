import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="modalOptionC"')
if idx != -1:
    print(text[idx:idx+1500])
