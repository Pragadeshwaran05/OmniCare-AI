with open('templates/doctor_base.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '<aside' in line:
        print(f"Aside start: line {i+1}")
    elif '</aside>' in line:
        print(f"Aside end: line {i+1}")
    elif '<nav class="common-bottom-bar">' in line or 'class="common-bottom-bar"' in line:
        print(f"Bottom bar start: line {i+1}")
    elif '</nav>' in line:
        print(f"Nav end: line {i+1}")
