import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(6830, min(6950, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')

print("\n--- Error handling lines 7370-7420 ---")
for i in range(7370, min(7420, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')
