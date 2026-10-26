import os
import socket
import httpx
from dotenv import load_dotenv
from supabase import create_client

# Prioritize IPv4 on Windows to prevent IPv6 drops
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_preferred_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    try:
        return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    except Exception:
        return _orig_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _ipv4_preferred_getaddrinfo

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is missing in .env")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY is missing in .env")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# Use HTTP/1.1 transport to prevent HTTP/2 Windows socket EOF drops
if hasattr(supabase, "postgrest") and hasattr(supabase.postgrest, "base_url"):
    supabase.postgrest.session = httpx.Client(
        base_url=str(supabase.postgrest.base_url),
        headers=supabase.postgrest.headers,
        timeout=supabase.postgrest.timeout,
        follow_redirects=True,
        http2=False
    )
