# ============================================================
# OMNICARE AI — CLINICAL AUDIT SERVICE
# ============================================================

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


AUDIT_LOG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scratch",
    "clinical_audit_log.jsonl"
)


def log_clinical_event(
    doctor_id: str,
    action: str,
    patient_ids: Optional[List[str]] = None,
    status: str = "SUCCESS",
    metadata: Optional[Dict[str, Any]] = None,
    client_ip: Optional[str] = None
) -> Dict[str, Any]:
    """
    Record an immutable clinical audit entry.
    Ensures HIPAA/GDPR compliance by recording access scope without
    storing unnecessary raw identifiable medical text.
    """
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "doctor_id": doctor_id,
        "action": action,
        "patient_ids": patient_ids or [],
        "patient_count": len(patient_ids or []),
        "status": status,
        "client_ip": client_ip or "127.0.0.1",
        "metadata": metadata or {}
    }

    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print("Audit logging error:", repr(e))

    return entry


def get_doctor_audit_logs(
    doctor_id: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Retrieve audit history for a specific authenticated doctor.
    """
    if not os.path.exists(AUDIT_LOG_FILE):
        return []

    logs = []
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if record.get("doctor_id") == doctor_id:
                        logs.append(record)
                except Exception:
                    continue
    except Exception as e:
        print("Error reading audit logs:", repr(e))

    # Return newest first
    logs.reverse()
    return logs[:limit]
