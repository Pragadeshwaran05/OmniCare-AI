import os, sys, io
sys.path.insert(0, os.path.abspath('.'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

from services.doctor_ai_assistant import ask_doctor_ai

# Use patient data that we already verified from Supabase
patient_data = {
    "id": "a8360a17-d8a0-4524-bcc2-b1b4775e5c4f",
    "full_name": "Pragadeshwaran R",
    "health_id": "OMC-P5C4F",
    "gender": "Male",
    "date_of_birth": "1995-04-12",
    "blood_group": "O+"
}

timeline_events = [
    {
        "id": "b4d76898-e953-4c47-8fc9-af491577e88a",
        "event_date": "2026-10-02",
        "event_type": "consultation",
        "provider_name": "Dr. Sarah Jenkins",
        "hospital_name": "Metro Speciality Health Clinic",
        "diagnosis": "Acute Bronchitis with Mild Allergic Rhinitis",
        "clinical_findings": "Dry cough x 4 days, low-grade fever",
        "investigations": [
            {"name": "Complete Blood Count (CBC) with ESR", "unit": None, "result": "Ordered", "reference_range": None},
            {"name": "Chest X-Ray PA View", "unit": None, "result": "Ordered", "reference_range": None}
        ],
        "medications": [
            {"name": "Tab. Augmentin 625 mg (Amoxicillin + Clavulanic Acid)", "dose": "1 Tablet", "frequency": "Twice Daily (1-0-1)", "duration": "5 Days", "instructions": "After Food"},
            {"name": "Tab. Montair-LC (Montelukast 10mg + Levocetirizine 5mg)", "dose": "1 Tablet", "frequency": "Once Daily at Night (0-0-1)", "duration": "7 Days", "instructions": "At bedtime"},
            {"name": "Syp. Ascoril-D Cough Syrup (100 ml)", "dose": "10 ml", "frequency": "Three Times Daily", "duration": "5 Days", "instructions": "After Food"},
            {"name": "Tab. Paracetamol 650 mg (Dolo 650)", "dose": "1 Tablet", "frequency": "SOS", "duration": None, "instructions": "Take only if fever or body pain > 99 deg F"}
        ],
        "follow_up": "09 Oct 2026 (After 7 days) or SOS if breathlessness occurs.",
        "clinical_summary": "Patient presented with acute respiratory symptoms and allergic rhinitis."
    },
    {
        "id": "3fc5d833-e2e7-4505-8262-f514b49a661a",
        "event_date": "2026-09-28",
        "event_type": "investigation",
        "provider_name": "Dr. Pathologist",
        "hospital_name": "City Diagnostic Lab",
        "diagnosis": None,
        "clinical_findings": "Follow-up laboratory investigation for elevated blood glucose.",
        "investigations": [
            {"name": "Fasting Blood Glucose", "unit": "mg/dL", "result": "142", "reference_range": "70 - 99 mg/dL"},
            {"name": "HbA1c", "unit": "%", "result": "7.3", "reference_range": "4.0 - 5.6 %"},
            {"name": "Total Cholesterol", "unit": "mg/dL", "result": "218", "reference_range": "< 200 mg/dL"},
            {"name": "LDL Cholesterol", "unit": "mg/dL", "result": "142", "reference_range": "< 100 mg/dL"},
            {"name": "HDL Cholesterol", "unit": "mg/dL", "result": "43", "reference_range": "> 40 mg/dL"},
            {"name": "Triglycerides", "unit": "mg/dL", "result": "165", "reference_range": "< 150 mg/dL"}
        ],
        "medications": [],
        "follow_up": "12 October 2026",
        "clinical_summary": "Elevated fasting blood glucose and HbA1c indicative of uncontrolled glycemia."
    },
    {
        "id": "f5599f35-79b6-4f60-aa84-b1da7741d56e",
        "event_date": "2026-09-05",
        "event_type": "investigation",
        "provider_name": "Dr. Pathologist",
        "hospital_name": "City Diagnostic Lab",
        "diagnosis": None,
        "clinical_findings": "Fasting blood glucose is slightly elevated. HbA1c is in prediabetic range.",
        "investigations": [
            {"name": "Fasting Blood Glucose (FBS)", "unit": "mg/dL", "result": "108", "reference_range": "70 - 99 mg/dL"},
            {"name": "Post Prandial Blood Glucose (PPBS)", "unit": "mg/dL", "result": "142", "reference_range": "< 140 mg/dL"},
            {"name": "HbA1c (Glycated Hemoglobin)", "unit": "%", "result": "5.8", "reference_range": "4.0 - 5.6 %"},
            {"name": "Total Cholesterol", "unit": "mg/dL", "result": "188", "reference_range": "< 200 mg/dL"},
            {"name": "Serum Creatinine", "unit": "mg/dL", "result": "0.9", "reference_range": "0.6 - 1.2 mg/dL"}
        ],
        "medications": [],
        "follow_up": "Correlate clinically and follow up with your physician.",
        "clinical_summary": "Baseline lab work."
    }
]

medical_records = [
    {
        "id": "3d88acc9-9b8c-42fe-8d2e-265d1f4107b4",
        "title": "Medical Prescription - 28 Sep 2026",
        "record_type": "Prescription",
        "document_date": "2026-09-28",
        "description": "Prescription for Type 2 Diabetes Mellitus with Metformin 500mg BD."
    },
    {
        "id": "a828a5a2-b4d4-44b6-a48d-49609aa8b0d3",
        "title": "ECG Report",
        "record_type": "Medical Scan",
        "document_date": "2026-11-10",
        "description": "Normal sinus rhythm, heart rate 72 bpm, no ischemic changes."
    }
]

questions = [
    "What are the patient's recent diagnoses?",
    "What medications are documented in the patient's medical history?",
    "What investigations are documented in the patient's records?",
    "Compare previous and latest fasting blood glucose results.",
    "What follow-up instructions are documented?",
    "Does the patient have any documented history of asthma or previous surgeries?"
]

for q in questions:
    print(f"\n=======================================================")
    print(f"QUESTION: {q}")
    print(f"=======================================================")
    ans = ask_doctor_ai(
        question=q,
        timeline_events=timeline_events,
        patient_data=patient_data,
        medical_records=medical_records
    )
    print("ANSWER:\n" + ans)

# Empty test
print(f"\n=======================================================")
print(f"TEST EMPTY PATIENT:")
print(f"=======================================================")
ans_empty = ask_doctor_ai(
    question="What are the patient's recent diagnoses?",
    timeline_events=[],
    patient_data={"full_name": "New Patient"},
    medical_records=[]
)
print("EMPTY ANSWER:\n" + ans_empty)
