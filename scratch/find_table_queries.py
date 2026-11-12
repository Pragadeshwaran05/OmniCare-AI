with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

tables = ['medical_records', 'health_timeline_events', 'prescriptions', 'patients', 'doctors']

for t in tables:
    print(f"\n=== Table {t} ===")
    count = 0
    for i, l in enumerate(lines):
        if f'.table("{t}")' in l or f".table('{t}')" in l:
            print(f'Line {i+1}: {l.strip()[:100]}')
            count += 1
            if count >= 6:
                break
