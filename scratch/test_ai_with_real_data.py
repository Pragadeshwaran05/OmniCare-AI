import os
import json
from dotenv import load_dotenv

load_dotenv()
from supabase import create_client
from google import genai

supabase_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

pid = "a8360a17-d8a0-4524-bcc2-b1b4775e5c4f"

# 1. Patient
p_res = supabase_client.table("patients").select("*").eq("id", pid).single().execute()
patient = p_res.data or {}

# 2. Medical records
mr_res = supabase_client.table("medical_records").select("*").eq("patient_id", pid).execute()
records = mr_res.data or []

# 3. Timeline events
tl_res = supabase_client.table("health_timeline_events").select("*").eq("patient_id", pid).order("event_date", desc=True).execute()
timeline = tl_res.data or []

print("Patient:", patient.get("full_name"))
print("Records count:", len(records))
print("Timeline count:", len(timeline))

from services.doctor_ai_assistant import build_patient_context

ctx = build_patient_context(timeline)
print("\nGenerated context length:", len(ctx))

questions = [
    "What are the patient's recent diagnoses?",
    "What medications are documented in the patient's medical history?",
    "What investigations are documented in the patient's records?"
]

for q in questions:
    print(f"\n====================\nQUESTION: {q}\n====================")
    prompt = f"""You are OmniCare AI, a medical history assistant for authorized doctors.
Answer questions using only the supplied authorized patient medical records.
Do not invent diagnoses, medications, investigation results, dates or treatment information.
If the requested information is unavailable, clearly state that it is not documented in the available records.
When answering, mention relevant dates and source documents wherever available.
Distinguish between historical and current medications.
Do not interpret an undocumented condition as a confirmed diagnosis.
When comparing investigation results, include their dates, values and units.
If information is contradictory, identify the discrepancy and ask the doctor to verify the original documents.
You are an assistant for retrieving and organizing medical information, not a replacement for clinical judgment.
Always remind the doctor to verify important information against original medical documents.

PATIENT INFORMATION:
Name: {patient.get('full_name')}
Health ID: {patient.get('health_id')}
Date of Birth: {patient.get('date_of_birth')}
Gender: {patient.get('gender')}
Blood Group: {patient.get('blood_group')}

PATIENT CLINICAL RECORDS & TIMELINE:
{ctx}

DOCTOR'S QUESTION:
{q}
"""
    try:
        resp = gemini_client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt
        )
        print("ANSWER:\n", resp.text)
    except Exception as e:
        print("ERROR:", repr(e))
