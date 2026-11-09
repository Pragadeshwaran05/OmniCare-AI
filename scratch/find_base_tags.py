with open('templates/doctor_base.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'class="doctor-sidebar"' in line or 'class="doctor-main"' in line or '<header' in line:
            print(f"{i+1}: {line.strip()[:80]}")
