import sys
sys.path.insert(0, '.')
import time
from utils.supabase_client import supabase

def fetch_with_retry(fn, max_retries=4):
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise e

res = fetch_with_retry(lambda: supabase.table('access_requests').select('*').execute())
print(f"Total access requests: {len(res.data or [])}")
for r in (res.data or []):
    print(f"ID: {r['id']} | Patient: {r['patient_id']} | Doctor: {r['doctor_id']} | Status: {r['status']} | Expires: {r.get('expires_at')}")
