import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("--- Lines 5800-5840 ---")
for i in range(5800, min(5840, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')

print("\n--- Lines 6740-6830 ---")
for i in range(6740, min(6830, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')
