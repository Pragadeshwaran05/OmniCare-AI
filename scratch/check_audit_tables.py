import sys
sys.path.insert(0, '.')
from utils.supabase_client import supabase

candidate_tables = [
    'audit_logs', 'access_audit', 'clinical_alerts', 'alert_reviews', 
    'doctor_audit', 'logs', 'consents', 'patient_consents'
]

for t in candidate_tables:
    try:
        r = supabase.table(t).select('*').limit(1).execute()
        print(f"Candidate {t}: EXISTS! Columns: {list(r.data[0].keys()) if r.data else 'empty'}")
    except Exception as e:
        print(f"Candidate {t}: does not exist ({e})")
