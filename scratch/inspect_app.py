import re
import os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

tables = sorted(set(re.findall(r'table\(["\']([a-zA-Z0-9_]+)["\']\)', content)))
print("Referenced Supabase Tables:")
for t in tables:
    print(f" - {t}")
