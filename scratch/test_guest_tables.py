import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

guest_tables = ["guest_patients", "guest_medical_records", "guest_health_timeline_events"]
for t in guest_tables:
    try:
        res = client.table(t).select("*").limit(1).execute()
        print(f"Table '{t}': EXISTS (sample keys: {list(res.data[0].keys()) if res.data else 'empty table'})")
    except Exception as e:
        print(f"Table '{t}': ERROR -> {repr(e)}")
