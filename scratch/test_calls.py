import sys
sys.path.insert(0, '.')
import time
from utils.supabase_client import supabase

def robust_call(builder_fn, max_retries=4, initial_delay=1.0):
    last_err = None
    for attempt in range(max_retries):
        try:
            return builder_fn().execute()
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(initial_delay * (1.5 ** attempt))
            else:
                print(f"Failed after {max_retries} attempts: {repr(e)}")
                return None

for i in range(5):
    res = robust_call(lambda: supabase.table('access_requests').select('*').limit(1))
    print(f"Call {i+1}: {'OK' if res and res.data else 'FAIL'}")
