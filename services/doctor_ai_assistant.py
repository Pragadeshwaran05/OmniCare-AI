# ============================================================
# OMNICARE AI - DOCTOR HEALTH ASSISTANT
# Patient-Specific Medical History AI Assistant via Gemini
# ============================================================

import os
import json
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors

# ------------------------------------------------------------
# LOAD ENVIRONMENT
# ------------------------------------------------------------
load_dotenv()

# ------------------------------------------------------------
# GEMINI CONFIGURATION
# ------------------------------------------------------------
MODEL_NAME = "gemini-3.5-flash-lite"
FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        return genai.Client(
            api_key=api_key,
            http_options={"timeout": 30000}
        )
    except Exception as e:
        print("[DoctorAI] Gemini client initialization error:", repr(e))
        return None

# Module-level client instance (backward compatible)
try:
    client = get_gemini_client()
except Exception:
    client = None


# ------------------------------------------------------------
# BUILD PATIENT CONTEXT
# ------------------------------------------------------------

def build_patient_context(timeline_events=None, patient_data=None, medical_records=None):
    """
    Builds a structured clinical history context for Gemini AI.
    Integrates:
    1. Patient Demographics (Name, Health ID, Age/DOB, Gender, Blood Group)
    2. Clinical Timeline Events (Diagnoses, Findings, Medications, Investigations, Follow-ups)
    3. Medical Records / Uploaded Documents (Prescriptions, Lab Reports, Scans, Consultations,
       including unextracted/older records)
    """
    timeline_events = timeline_events or []
    medical_records = medical_records or []
    patient_data = patient_data or {}

    sections = []

    # 1. Patient Profile Header
    if patient_data:
        p_name = patient_data.get("full_name") or patient_data.get("name") or "Authorized Patient"
        p_hid = patient_data.get("health_id") or "N/A"
        p_dob = patient_data.get("date_of_birth") or "N/A"
        p_gender = patient_data.get("gender") or "N/A"
        p_bg = patient_data.get("blood_group") or "N/A"
        sections.append(
            f"=== PATIENT DEMOGRAPHICS ===\n"
            f"Name: {p_name}\n"
            f"Health ID: {p_hid}\n"
            f"Gender: {p_gender}\n"
            f"Date of Birth: {p_dob}\n"
            f"Blood Group: {p_bg}"
        )

    # 2. Clinical Timeline Events
    if timeline_events:
        event_blocks = []
        for index, event in enumerate(timeline_events, start=1):
            meds_list = event.get("medications") or []
            invs_list = event.get("investigations") or []

            event_obj = {
                "event_index": index,
                "event_date": event.get("event_date") or "Undated",
                "event_type": event.get("event_type") or "Clinical Event",
                "provider_name": event.get("provider_name") or "Not Documented",
                "hospital_name": event.get("hospital_name") or "Not Documented",
                "diagnosis": event.get("diagnosis") or "None Documented",
                "clinical_findings": event.get("clinical_findings") or "None Documented",
                "medications": meds_list,
                "investigations": invs_list,
                "follow_up": event.get("follow_up") or "None Documented",
                "clinical_summary": event.get("clinical_summary") or ""
            }
            event_blocks.append(
                f"--- CLINICAL EVENT {index} ({event_obj['event_date']} - {event_obj['event_type']}) ---\n"
                + json.dumps(event_obj, ensure_ascii=False, indent=2, default=str)
            )
        sections.append("=== DOCUMENTED CLINICAL TIMELINE EVENTS ===\n" + "\n\n".join(event_blocks))
    else:
        sections.append("=== DOCUMENTED CLINICAL TIMELINE EVENTS ===\nNo structured clinical timeline events are currently recorded for this patient.")

    # 3. Medical Records / Documents
    if medical_records:
        rec_blocks = []
        # Find which records are already extracted in timeline
        extracted_rec_ids = {
            str(ev.get("medical_record_id"))
            for ev in timeline_events
            if ev.get("medical_record_id")
        }

        for idx, rec in enumerate(medical_records, start=1):
            rec_id = str(rec.get("id", ""))
            is_in_timeline = rec_id in extracted_rec_ids
            status_note = "Extracted in clinical timeline" if is_in_timeline else "Uploaded document (metadata only; content not yet AI-extracted)"

            struct_data = rec.get("structured_data")
            rec_summary = {
                "record_index": idx,
                "record_id": rec_id,
                "title": rec.get("title") or "Medical Record",
                "record_type": rec.get("record_type") or "Document",
                "document_date": rec.get("document_date") or rec.get("uploaded_at") or "Unknown",
                "description": rec.get("description") or "No description provided",
                "status": status_note
            }
            if struct_data and isinstance(struct_data, dict):
                rec_summary["structured_details"] = struct_data

            rec_blocks.append(
                f"--- RECORD {idx}: {rec_summary['title']} ({rec_summary['document_date']}) ---\n"
                + json.dumps(rec_summary, ensure_ascii=False, indent=2, default=str)
            )
        sections.append("=== PATIENT MEDICAL RECORDS & SOURCE DOCUMENTS ===\n" + "\n\n".join(rec_blocks))
    else:
        sections.append("=== PATIENT MEDICAL RECORDS & SOURCE DOCUMENTS ===\nNo medical records or uploaded documents exist for this patient.")

    if not timeline_events and not medical_records:
        return "No medical records, prescriptions, diagnoses, or clinical timeline events are documented in the available patient records."

    return "\n\n".join(sections)


# ------------------------------------------------------------
# ASK DOCTOR AI ASSISTANT
# ------------------------------------------------------------

SYSTEM_INSTRUCTION = """You are OmniCare AI, a medical history assistant for authorized doctors.

Answer questions using only the supplied authorized patient medical records.

Do not invent diagnoses, medications, investigation results, dates or treatment information.

If the requested information is unavailable, clearly state that it is not documented in the available records.

When answering, mention relevant dates and source documents wherever available.

Distinguish between historical and current medications.

Do not interpret an undocumented condition as a confirmed diagnosis.

When comparing investigation results, include their dates, values and units.

If information is contradictory, identify the discrepancy and ask the doctor to verify the original documents.

You are an assistant for retrieving and organizing medical information, not a replacement for clinical judgment.

Always remind the doctor to verify important information against original medical documents."""


def ask_doctor_ai(question, timeline_events=None, patient_data=None, medical_records=None, **kwargs):
    """
    Main patient-specific doctor AI query function.
    Strictly answers clinical questions based on verified patient records.
    """
    if not question or not str(question).strip():
        return "Please enter a clinical question about the patient's medical records."

    question = str(question).strip()
    timeline_events = timeline_events or []
    medical_records = medical_records or []
    patient_data = patient_data or {}

    # Handle patient with empty records
    if not timeline_events and not medical_records:
        p_name = patient_data.get("full_name") or patient_data.get("name") or "this patient"
        return (
            f"No medical records, prescriptions, or clinical timeline events are documented for {p_name}. "
            "There is no medical history available in the system yet. "
            "Please verify against original physical medical documents or upload records to establish the clinical timeline."
        )

    patient_context = build_patient_context(
        timeline_events=timeline_events,
        patient_data=patient_data,
        medical_records=medical_records
    )

    prompt = f"""{SYSTEM_INSTRUCTION}

============================================================
PATIENT MEDICAL RECORDS CONTEXT:
============================================================
{patient_context}

============================================================
DOCTOR'S QUESTION:
============================================================
{question}

Provide an accurate, clinically organized answer using only the documented records above. Include relevant dates, dosages, investigation values/units, and source record titles where documented. Remind the doctor to verify against original documents."""

    # Obtain or initialize Gemini client
    ai_client = get_gemini_client()
    if not ai_client:
        print("[DoctorAI Error] Gemini client unavailable - GEMINI_API_KEY missing or invalid.")
        return (
            "The AI Health Assistant is temporarily unavailable because the AI service is not configured. "
            "Please verify the patient's records directly in the Medical Records and Health Timeline tabs."
        )

    # Attempt generation with model fallback and retries
    last_error = None
    for model_candidate in FALLBACK_MODELS:
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                print(f"[DoctorAI] Querying Gemini ({model_candidate}) - attempt {attempt + 1}/{max_attempts}")
                response = ai_client.models.generate_content(
                    model=model_candidate,
                    contents=prompt
                )

                # Extract response text
                answer = getattr(response, "text", None)
                if not answer and hasattr(response, "candidates") and response.candidates:
                    parts = getattr(response.candidates[0].content, "parts", [])
                    text_parts = [p.text for p in parts if hasattr(p, "text") and p.text]
                    if text_parts:
                        answer = "".join(text_parts)

                if answer and answer.strip():
                    return answer.strip()

                print(f"[DoctorAI] Model {model_candidate} returned empty response.")

            except errors.APIError as api_err:
                last_error = api_err
                code = getattr(api_err, "code", None)
                print(f"[DoctorAI APIError] {model_candidate} code={code}: {api_err.message if hasattr(api_err, 'message') else api_err}")
                if code == 429:  # Quota / Rate limit
                    time.sleep(1)
                    break  # Try next model
                elif attempt < max_attempts - 1:
                    time.sleep(2 * (attempt + 1))
                else:
                    break

            except Exception as e:
                last_error = e
                print(f"[DoctorAI Exception] {model_candidate}: {repr(e)}")
                if attempt < max_attempts - 1:
                    time.sleep(1.5)
                else:
                    break

    # If all models/attempts failed
    print("[DoctorAI Final Error] All Gemini model attempts failed:", repr(last_error))
    return (
        "OmniCare AI could not generate an answer right now due to a temporary service issue with the AI provider. "
        "Your patient records are intact. Please review the patient's records directly in the Medical Records or "
        "Health Timeline tabs, or try your question again shortly."
    )
