import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('static/css/doctor_consultations.css', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(''.join(lines[1010:1150]))
