import sys, os
sys.path.insert(0, os.path.abspath('.'))

from services.doctor_ai_assistant import build_patient_context, ask_doctor_ai

# Test 1: Empty state
res_empty = ask_doctor_ai("What are the diagnoses?", timeline_events=[], medical_records=[])
print("Empty state response:", res_empty)
assert "No medical records" in res_empty, "Empty state must be handled"

# Test 2: Sample events context
sample_events = [{
    "event_date": "2026-10-02",
    "event_type": "consultation",
    "diagnosis": "Acute Bronchitis",
    "medications": [{"name": "Augmentin", "dosage": "625mg"}],
    "investigations": [{"name": "CBC", "result": "Normal"}]
}]
ctx = build_patient_context(sample_events, {"full_name": "John Doe", "health_id": "OMC-123"})
print("\nGenerated context:\n", ctx)
assert "John Doe" in ctx
assert "Acute Bronchitis" in ctx
assert "Augmentin" in ctx

print("\nSUCCESS: services/doctor_ai_assistant.py logic verified.")
