import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
client = create_client(supabase_url, supabase_key)

tables = ["patients", "medical_records", "health_timeline_events", "prescriptions", "doctors", "access_requests"]

for t in tables:
    try:
        res = client.table(t).select("*").limit(1).execute()
        print(f"Table '{t}': EXISTS (sample keys: {list(res.data[0].keys()) if res.data else 'empty table'})")
    except Exception as e:
        print(f"Table '{t}': ERROR -> {repr(e)}")
