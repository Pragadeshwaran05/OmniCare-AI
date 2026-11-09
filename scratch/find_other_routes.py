with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '@app.route' in line:
        fn_line = ""
        for j in range(i+1, min(i+5, len(lines))):
            if 'def ' in lines[j]:
                fn_line = lines[j].strip()
                break
        if i >= 4650 and i <= 6400:
            print(f"{i+1}: {line.strip()} -> {fn_line}")
