import sys
sys.path.insert(0, '.')
import socket

orig_getaddrinfo = socket.getaddrinfo

def ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

socket.getaddrinfo = ipv4_only_getaddrinfo

import time
from utils.supabase_client import supabase

t0 = time.time()
print("Attempting Supabase query with IPv4 only...")
res = supabase.table('access_requests').select('*').limit(3).execute()
t1 = time.time()
print(f"Success! Fetched {len(res.data or [])} rows in {t1 - t0:.2f} seconds!")
