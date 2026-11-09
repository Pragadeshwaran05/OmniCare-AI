with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """        # -------------------------------------------------
        # 4. GET PATIENT MEDICAL RECORDS
        # -------------------------------------------------

        records_response = (
            supabase_admin
            .table("medical_records")
            .select("*")
            .eq("patient_id", patient_id)
            .order("uploaded_at", desc=True)
            .execute()
        )

        records = records_response.data or []

        # -------------------------------------------------
        # 5. GET AI HEALTH TIMELINE EVENTS
        # -------------------------------------------------

        timeline_response = (
            supabase_admin
            .table("health_timeline_events")
            .select("*")
            .eq("patient_id", patient_id)
            .order("event_date", desc=True)
            .execute()
        )

        timeline_events = timeline_response.data or []"""

replacement = """        # -------------------------------------------------
        # 4. GET PATIENT MEDICAL RECORDS
        # -------------------------------------------------
        try:
            records_response = (
                supabase_admin
                .table("medical_records")
                .select("*")
                .eq("patient_id", patient_id)
                .order("uploaded_at", desc=True)
                .execute()
            )
            records = records_response.data or []
        except Exception as rec_err:
            print("Notice: Medical records fetch:", repr(rec_err))
            records = []

        # -------------------------------------------------
        # 5. GET AI HEALTH TIMELINE EVENTS
        # -------------------------------------------------
        try:
            timeline_response = (
                supabase_admin
                .table("health_timeline_events")
                .select("*")
                .eq("patient_id", patient_id)
                .order("event_date", desc=True)
                .execute()
            )
            timeline_events = timeline_response.data or []
        except Exception as time_err:
            print("Notice: Timeline events fetch:", repr(time_err))
            timeline_events = []"""

assert target in content, "target not found"
content = content.replace(target, replacement, 1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Safeguarded records & timeline fetch in doctor_patient_workspace!")
