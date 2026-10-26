import sys
sys.path.insert(0, '.')
import re
from utils.supabase_client import supabase

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

tables = sorted(list(set(re.findall(r'table\(["\']([^"\']+)["\']\)', text))))
print('Tables in app.py:', tables)

for table in tables:
    try:
        res = supabase.table(table).select('*').limit(1).execute()
        if res.data:
            print(f"\nTable: {table} -> Columns: {list(res.data[0].keys())}")
        else:
            print(f"\nTable: {table} -> EMPTY (query succeeded)")
    except Exception as e:
        print(f"\nTable: {table} -> ERROR: {e}")
