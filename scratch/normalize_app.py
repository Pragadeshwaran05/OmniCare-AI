with open("app.py", "rb") as f:
    content = f.read()

# Normalize any \r\r\n or \r\n to \n
normalized = content.replace(b"\r\r\n", b"\n").replace(b"\r\n", b"\n")

with open("app.py", "wb") as f:
    f.write(normalized)

with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Normalized app.py. Total lines: {len(lines)}")
