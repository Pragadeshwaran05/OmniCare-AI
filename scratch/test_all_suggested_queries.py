import sys
sys.path.insert(0, '.')
from services.clinical_query_service import execute_clinical_query
from utils.supabase_client import supabase

doc_id = "ea83806c-f033-4012-944b-22098514d9e9"

questions = [
    "Which patients have HbA1c above 8%?",
    "Show overdue follow-ups",
    "Which patients have high blood pressure?",
    "Which patients are taking Augmentin?",
    "Which patients are taking Metformin?",
    "Show recent abnormal lab results",
    "Which patients have a documented drug interaction risk?"
]

for q in questions:
    res = execute_clinical_query(doc_id, q, supabase)
    print("=" * 60)
    print("QUERY:", q)
    print("ANSWER:", res.get("answer"))
    print("RESULTS COUNT:", len(res.get("results", [])))
    print("SOURCES COUNT:", len(res.get("sources", [])))
    if res.get("results"):
        print("SAMPLE RESULT:", res["results"][0])
    if res.get("limitations"):
        print("LIMITATIONS:", res["limitations"])
