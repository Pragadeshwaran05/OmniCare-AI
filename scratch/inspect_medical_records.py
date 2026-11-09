with open('app.py', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'medical_records' in l:
        print(f"Line {i+1}: {l.strip()[:100]}")
        for j in range(max(0, i-2), min(len(lines), i+8)):
            if any(k in lines[j] for k in ['insert', 'select', 'record_data', 'record =']):
                print(f"   L{j+1}: {lines[j].strip()[:100]}")
