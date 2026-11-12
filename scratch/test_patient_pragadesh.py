import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

pid = "a8360a17-d8a0-4524-bcc2-b1b4775e5c4f"
mr_res = client.table("medical_records").select("id, record_type, title, description, uploaded_at").eq("patient_id", pid).execute()
print(f"Medical records for {pid}:", len(mr_res.data))
for r in mr_res.data:
    print(" -", r)

tl_res = client.table("health_timeline_events").select("id, event_date, event_type, diagnosis, clinical_findings, investigations, medications, follow_up, clinical_summary").eq("patient_id", pid).execute()
print(f"Timeline events for {pid}:", len(tl_res.data))
for ev in tl_res.data:
    print(" -", ev)
