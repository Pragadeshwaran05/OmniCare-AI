# ============================================================
# OMNICARE AI — NETWORK CONFIGURATION & RELIABILITY
# ============================================================

import socket

# Force IPv4 resolution on Windows to prevent IPv6 SSL handshake drops & EOF violations
_orig_getaddrinfo = socket.getaddrinfo

def _ipv4_preferred_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    try:
        return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    except Exception:
        return _orig_getaddrinfo(host, port, family, type, proto, flags)

if socket.getaddrinfo != _ipv4_preferred_getaddrinfo:
    socket.getaddrinfo = _ipv4_preferred_getaddrinfo
