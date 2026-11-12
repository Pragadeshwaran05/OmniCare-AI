import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

p_res = client.table("patients").select("id, full_name, health_id").limit(5).execute()
print("Sample patients:", p_res.data)

if p_res.data:
    pid = p_res.data[0]["id"]
    mr_res = client.table("medical_records").select("id, record_type, title, description, uploaded_at").eq("patient_id", pid).execute()
    print(f"\nMedical records for patient {pid}:", len(mr_res.data))
    for r in mr_res.data[:3]:
        print(" -", r)

    tl_res = client.table("health_timeline_events").select("id, event_date, event_type, diagnosis, investigations, medications").eq("patient_id", pid).execute()
    print(f"\nTimeline events for patient {pid}:", len(tl_res.data))
    for ev in tl_res.data[:3]:
        print(" -", ev)
