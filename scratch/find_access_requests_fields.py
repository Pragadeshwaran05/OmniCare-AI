with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '.table("access_requests")' in line or ".table('access_requests')" in line:
        context = "".join(lines[i:min(i+15, len(lines))])
        if any(op in context for op in ['.insert(', '.update(', '.select(']):
            print(f"--- Line {i+1} ---")
            for j in range(i, min(i+12, len(lines))):
                print(lines[j].rstrip())
