import sys
sys.path.insert(0, '.')
from utils.supabase_client import supabase

for tbl in ['doctors', 'patients', 'access_requests', 'medical_records', 'health_timeline_events', 'patient_emergency_profiles']:
    try:
        res = supabase.table(tbl).select('id', count='exact').execute()
        count = len(res.data) if res.data else 0
        print(f"Table {tbl}: {count} records found.")
    except Exception as e:
        print(f"Table {tbl}: Error {e}")
