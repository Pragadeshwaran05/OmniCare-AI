import time

def execute_db_query(builder_fn, max_retries=3, delay=0.8):
    """
    Execute a Supabase PostgREST builder call with automatic retries
    to protect against transient Windows socket reset / HTTP2 drops.
    """
    last_err = None
    for attempt in range(max_retries):
        try:
            return builder_fn().execute()
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                raise last_err
