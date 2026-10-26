import sys
sys.path.insert(0, '.')
from datetime import datetime
from services.medical_record_normalizer import (
    parse_strict_date, format_iso_date, extract_followup_date, normalize_numeric_value
)
from services.clinical_rules_engine import evaluate_investigation, check_followup_overdue
from services.clinical_copilot_service import get_clinical_briefing
from services.clinical_query_service import execute_clinical_query
from utils.supabase_client import supabase

print("=== 1. TEST NORMALIZER ===")
assert format_iso_date("15-10-2026") == "2026-10-15", f"Got {format_iso_date('15-10-2026')}"
assert format_iso_date("09 Oct 2026") == "2026-10-09"
assert format_iso_date("2026-10-02T16:07:33Z") == "2026-10-02"
assert format_iso_date("31-02-2026") is None
print("Normalizer date tests passed!")

f_dt = extract_followup_date("09 Oct 2026 (After 7 days) or SOS if breathlessness occurs.")
assert f_dt == datetime(2026, 10, 9), f"Got {f_dt}"
print("Follow-up date extraction passed!")

print("\n=== 2. TEST RULES ENGINE ===")
inv_eval = evaluate_investigation("Fasting Blood Glucose", "142", "mg/dL")
assert inv_eval["is_abnormal"] is True
assert inv_eval["status"] == "high"
print("Investigation evaluation passed:", inv_eval["explanation"])

f_check = check_followup_overdue("2026-10-09", datetime(2026, 10, 24))
assert f_check["is_overdue"] is True
assert f_check["days_overdue"] == 15
print("Overdue follow-up evaluation passed:", f_check)

print("\n=== 3. TEST BRIEFING WITH REAL DOCTOR ===")
doc_id = "ea83806c-f033-4012-944b-22098514d9e9"
briefing = get_clinical_briefing(doc_id, supabase)
print("Scope authorized count:", briefing["scope"]["authorized_patient_count"])
print("Abnormal reports count:", len(briefing["abnormal_reports"]))
print("Overdue followups count:", len(briefing["overdue_followups"]))
print("Worsening trends count:", len(briefing["worsening_trends"]))
print("Medication safety conflicts:", briefing["medication_safety"]["total_conflicts"])

print("\n=== 4. TEST QUERY SERVICE ===")
q_res1 = execute_clinical_query(doc_id, "Show overdue follow-ups", supabase)
print("Q1 Overdue follow-ups answer:", q_res1["answer"])
print("Q1 results count:", len(q_res1["results"]))
print("Q1 sources count:", len(q_res1["sources"]))

q_res2 = execute_clinical_query(doc_id, "Which patients are taking Augmentin?", supabase)
print("Q2 Augmentin answer:", q_res2["answer"])
print("Q2 results count:", len(q_res2["results"]))

print("\nALL VERIFICATIONS SUCCEEDED!")
