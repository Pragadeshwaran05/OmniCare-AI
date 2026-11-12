with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("--- Lines 2917-2970 ---")
for i in range(2916, min(2970, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')

print("\n--- Lines 6790-6840 ---")
for i in range(6789, min(6840, len(lines))):
    print(f'{i+1}: {lines[i]}', end='')
