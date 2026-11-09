# ============================================================
# OMNICARE AI — CLINICAL & ACCESS AUDIT SERVICE
# ============================================================

import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional


AUDIT_LOG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scratch",
    "clinical_audit_log.jsonl"
)

NOTIFICATIONS_STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scratch",
    "doctor_notifications_read.json"
)


# Activity Type Definitions & Human-Readable Labels
ACTION_LABELS = {
    "DOCTOR_LOGIN": "Doctor Login",
    "PATIENT_RECORD_VIEWED": "Patient Record Viewed",
    "MEDICAL_HISTORY_VIEWED": "Medical History Viewed",
    "INVESTIGATION_REPORT_VIEWED": "Investigation Report Viewed",
    "PRESCRIPTION_CREATED": "Prescription Created",
    "MEDICAL_RECORD_DOWNLOADED": "Medical Record Downloaded",
    "PATIENT_ACCESS_REQUESTED": "Patient Access Requested",
    "PATIENT_ACCESS_GRANTED": "Patient Access Granted",
    "PATIENT_ACCESS_REVOKED": "Patient Access Revoked",
    "PATIENT_ACCESS_CANCELLED": "Patient Access Cancelled",
    "CLINICAL_COPILOT_QUERY": "Clinical Copilot Query",
    "COPILOT_QUERY_EXECUTED": "Clinical Copilot Query",
    "COPILOT_BRIEFING_VIEWED": "Clinical Briefing Viewed",
    "GUEST_PATIENT_ACCESS": "Guest Patient Record Access",
    "UNAUTHORIZED_ACCESS_ATTEMPT": "Unauthorized Access Attempt",
    "FAILED_ACCESS_ATTEMPT": "Failed Access Attempt",
    "DOCTOR_PROFILE_UPDATED": "Doctor Profile Updated",
    "DOCTOR_PROFILE_PHOTO_UPDATED": "Profile Photograph Updated",
    "DOCTOR_PROFILE_PHOTO_REMOVED": "Profile Photograph Removed",
    "WORKING_PREFERENCES_UPDATED": "Working Preferences Updated",
    "CREDENTIAL_DOCUMENT_UPLOADED": "Credential Document Uploaded",
    "CREDENTIAL_DOCUMENT_DELETED": "Credential Document Deleted",
    "DOCTOR_PASSWORD_CHANGED": "Doctor Password Changed",
    "DOCTOR_SETTINGS_UPDATED": "Doctor Settings Updated",
    "DOCTOR_ACCOUNT_DEACTIVATED": "Doctor Account Deactivated",
    "EXTERNAL_CONSULTATION_REQUESTED": "External Consultation Requested",
    "EXTERNAL_CONSULTATION_OTP_SENT": "Patient OTP Dispatched",
    "EXTERNAL_CONSULTATION_OTP_VERIFIED": "Patient OTP Verified",
    "EXTERNAL_CONSULTATION_SESSION_STARTED": "External Consultation Session Started",
    "EXTERNAL_CONSULTATION_RECORD_VIEWED": "External Consultation Record Viewed",
    "EXTERNAL_CONSULTATION_SESSION_REVOKED": "External Consultation Session Revoked",
    "EXTERNAL_CONSULTATION_SESSION_EXPIRED": "External Consultation Session Expired",
    "INTERNAL_QR_SCAN": "Internal QR Code Scanned",
    "INTERNAL_OTP_ACCESS_GRANTED": "Doctor OTP Access Granted"
}


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
        "doctor_id": str(doctor_id or "").strip(),
        "action": action,
        "patient_ids": [str(pid) for pid in (patient_ids or []) if pid],
        "patient_count": len(patient_ids or []),
        "status": status.upper() if status else "SUCCESS",
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


def log_audit_event(
    doctor_id: str,
    action: str,
    patient_ids: Optional[List[str]] = None,
    status: str = "SUCCESS",
    metadata: Optional[Dict[str, Any]] = None,
    client_ip: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience alias for log_clinical_event covering all doctor portal operations.
    """
    return log_clinical_event(
        doctor_id=doctor_id,
        action=action,
        patient_ids=patient_ids,
        status=status,
        metadata=metadata,
        client_ip=client_ip
    )


def get_doctor_audit_logs(
    doctor_id: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Retrieve audit history for a specific authenticated doctor.
    """
    result = query_doctor_audit_logs(doctor_id=doctor_id, per_page=limit)
    return result["logs"]


def query_doctor_audit_logs(
    doctor_id: str,
    action: Optional[str] = None,
    patient_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 15
) -> Dict[str, Any]:
    """
    Query, filter, and paginate audit logs for the authenticated doctor.
    Strictly isolates data to doctor_id.
    """
    if not os.path.exists(AUDIT_LOG_FILE):
        return {
            "logs": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 0
        }

    raw_logs = []
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    # Doctor isolation check
                    if str(record.get("doctor_id")) != str(doctor_id):
                        continue
                    raw_logs.append(record)
                except Exception:
                    continue
    except Exception as e:
        print("Error reading audit logs:", repr(e))
        return {
            "logs": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 0
        }

    # Filter by action if provided
    filtered = []
    action_filter = action.strip().upper() if action else ""
    patient_filter = patient_id.strip() if patient_id else ""
    search_term = search.strip().lower() if search else ""

    start_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
        except Exception:
            start_dt = None

    end_dt = None
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            # If end_date is date-only (length <= 10), extend to end of day
            if len(end_date) <= 10:
                end_dt = end_dt + timedelta(days=1) - timedelta(microseconds=1)
        except Exception:
            end_dt = None

    for record in raw_logs:
        # Action filter
        rec_action = (record.get("action") or "").upper()
        if action_filter and action_filter not in rec_action:
            # Also check human label
            human_label = ACTION_LABELS.get(rec_action, "").upper()
            if action_filter not in human_label:
                continue

        # Patient filter
        if patient_filter:
            pids = record.get("patient_ids") or []
            meta_pid = str(record.get("metadata", {}).get("patient_id") or "")
            if patient_filter not in pids and patient_filter != meta_pid:
                continue

        # Date range filter
        ts_str = record.get("timestamp")
        if (start_dt or end_dt) and ts_str:
            try:
                rec_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if rec_dt.tzinfo is None:
                    rec_dt = rec_dt.replace(tzinfo=timezone.utc)
                if start_dt and rec_dt < start_dt:
                    continue
                if end_dt and rec_dt > end_dt:
                    continue
            except Exception:
                pass

        # Text search
        if search_term:
            found = False
            rec_id = str(record.get("id") or "").lower()
            rec_action_str = rec_action.lower()
            human_label = ACTION_LABELS.get(rec_action, "").lower()
            meta_str = json.dumps(record.get("metadata") or {}).lower()
            pids_str = " ".join(record.get("patient_ids") or []).lower()

            if (search_term in rec_id or
                search_term in rec_action_str or
                search_term in human_label or
                search_term in meta_str or
                search_term in pids_str):
                found = True

            if not found:
                continue

        # Format human-friendly action and details
        record_copy = dict(record)
        record_copy["action_display"] = ACTION_LABELS.get(
            record_copy.get("action"),
            record_copy.get("action", "").replace("_", " ").title()
        )
        filtered.append(record_copy)

    # Sort newest first
    filtered.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

    total = len(filtered)
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_logs = filtered[start_idx:end_idx]

    return {
        "logs": paginated_logs,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }


def get_audit_log_by_id(log_id: str, doctor_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve single audit log entry by ID, enforcing doctor ownership.
    """
    if not os.path.exists(AUDIT_LOG_FILE):
        return None

    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if record.get("id") == log_id:
                        if doctor_id and str(record.get("doctor_id")) != str(doctor_id):
                            return None
                        record["action_display"] = ACTION_LABELS.get(
                            record.get("action"),
                            record.get("action", "").replace("_", " ").title()
                        )
                        return record
                except Exception:
                    continue
    except Exception as e:
        print("Error fetching log by id:", repr(e))

    return None


def _load_read_notifications(doctor_id: str) -> set:
    """Load set of read notification IDs for this doctor."""
    try:
        if os.path.exists(NOTIFICATIONS_STATE_FILE):
            with open(NOTIFICATIONS_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get(str(doctor_id), []))
    except Exception as e:
        print("Error loading read notifications:", repr(e))
    return set()


def _save_read_notification(doctor_id: str, notification_id: str) -> bool:
    """Mark a notification as read."""
    try:
        os.makedirs(os.path.dirname(NOTIFICATIONS_STATE_FILE), exist_ok=True)
        data = {}
        if os.path.exists(NOTIFICATIONS_STATE_FILE):
            try:
                with open(NOTIFICATIONS_STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        doc_key = str(doctor_id)
        if doc_key not in data:
            data[doc_key] = []
        if notification_id not in data[doc_key]:
            data[doc_key].append(notification_id)

        with open(NOTIFICATIONS_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return True
    except Exception as e:
        print("Error saving read notification:", repr(e))
        return False


def _save_all_read_notifications(doctor_id: str, notification_ids: List[str]) -> bool:
    """Mark multiple notifications as read."""
    try:
        os.makedirs(os.path.dirname(NOTIFICATIONS_STATE_FILE), exist_ok=True)
        data = {}
        if os.path.exists(NOTIFICATIONS_STATE_FILE):
            try:
                with open(NOTIFICATIONS_STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        doc_key = str(doctor_id)
        existing = set(data.get(doc_key, []))
        existing.update(notification_ids)
        data[doc_key] = list(existing)

        with open(NOTIFICATIONS_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return True
    except Exception as e:
        print("Error saving all read notifications:", repr(e))
        return False


def get_doctor_notifications(
    doctor_id: str,
    access_requests: List[Dict[str, Any]],
    patients_map: Optional[Dict[str, Dict[str, Any]]] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Generate derived, database-backed access notifications for the doctor.
    Evaluates:
      - Access Expiring Soon (active temporary access with expiry < 2 hours)
      - Access Granted (approved active access)
      - Access Revoked (status = 'revoked')
      - Pending Approval (status = 'pending')
      - Access Expired (status = 'expired')
      - Access Request Rejected (status = 'rejected' or 'denied')
      - Unauthorized Access Attempt (logged security events in immutable audit trail)
    """
    read_set = _load_read_notifications(doctor_id)
    patients_map = patients_map or {}
    now = datetime.now(timezone.utc)

    # Load doctor notification preferences
    try:
        from services.doctor_settings_service import get_doctor_settings
        doc_settings = get_doctor_settings(doctor_id)
    except Exception:
        doc_settings = {}

    allow_requests = doc_settings.get("notify_access_requests", True)
    allow_expiry = doc_settings.get("notify_access_expiry", True)
    allow_system = doc_settings.get("notify_system_updates", True)

    notifications = []
    seen_ids = set()

    for req in access_requests:
        req_id = req.get("id")
        patient_id = req.get("patient_id")
        status = (req.get("status") or "").lower()
        patient = patients_map.get(str(patient_id), {})
        patient_name = patient.get("full_name") or patient.get("name") or f"Patient {str(patient_id)[:8]}"
        health_id = patient.get("health_id") or ""
        requested_at = req.get("requested_at") or ""
        approved_at = req.get("approved_at") or ""
        expires_at = req.get("expires_at")

        # 1. Access Expiring Soon
        if allow_expiry and status == "active" and expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                diff = exp_dt - now
                if timedelta(seconds=0) < diff <= timedelta(hours=2):
                    minutes_left = max(1, int(diff.total_seconds() // 60))
                    notif_id = f"exp_soon_{req_id}"
                    if notif_id not in seen_ids:
                        seen_ids.add(notif_id)
                        notifications.append({
                            "id": notif_id,
                            "type": "warning",
                            "badge": "Expiring Soon",
                            "title": f"Access Expiring Soon: {patient_name}",
                            "message": f"Temporary access for {patient_name} will expire in {minutes_left} minutes.",
                            "patient_name": patient_name,
                            "patient_id": patient_id,
                            "health_id": health_id,
                            "request_id": req_id,
                            "icon": "⚠️",
                            "timestamp": expires_at,
                            "is_read": notif_id in read_set,
                            "link": f"/doctor/patient-workspace/{patient_id}"
                        })
            except Exception:
                pass

        # 2. Access Granted / Approved
        if allow_requests and status == "active":
            notif_id = f"granted_{req_id}"
            if notif_id not in seen_ids:
                seen_ids.add(notif_id)
                notifications.append({
                    "id": notif_id,
                    "type": "success",
                    "badge": "Access Granted",
                    "title": f"Access Granted: {patient_name}",
                    "message": f"{patient_name} approved your {req.get('access_type', 'temporary')} access request.",
                    "patient_name": patient_name,
                    "patient_id": patient_id,
                    "health_id": health_id,
                    "request_id": req_id,
                    "icon": "🛡️",
                    "timestamp": approved_at or requested_at or now.isoformat(),
                    "is_read": notif_id in read_set,
                    "link": f"/doctor/patient-workspace/{patient_id}"
                })

        # 3. Access Request Pending / Pending Approval
        elif allow_requests and status == "pending":
            notif_id = f"pending_{req_id}"
            if notif_id not in seen_ids:
                seen_ids.add(notif_id)
                notifications.append({
                    "id": notif_id,
                    "type": "pending",
                    "badge": "Pending Approval",
                    "title": f"Access Request Pending: {patient_name}",
                    "message": f"Access request submitted for {patient_name}. Awaiting patient confirmation.",
                    "patient_name": patient_name,
                    "patient_id": patient_id,
                    "health_id": health_id,
                    "request_id": req_id,
                    "icon": "⏱️",
                    "timestamp": requested_at or now.isoformat(),
                    "is_read": notif_id in read_set,
                    "link": None
                })

        # 4. Access Revoked
        elif allow_expiry and status == "revoked":
            notif_id = f"revoked_{req_id}"
            if notif_id not in seen_ids:
                seen_ids.add(notif_id)
                notifications.append({
                    "id": notif_id,
                    "type": "danger",
                    "badge": "Access Revoked",
                    "title": f"Access Revoked: {patient_name}",
                    "message": f"{patient_name} has revoked record access authorization.",
                    "patient_name": patient_name,
                    "patient_id": patient_id,
                    "health_id": health_id,
                    "request_id": req_id,
                    "icon": "🚫",
                    "timestamp": req.get("revoked_at") or requested_at or now.isoformat(),
                    "is_read": notif_id in read_set,
                    "link": None
                })

        # 5. Access Expired
        elif allow_expiry and status == "expired":
            notif_id = f"expired_{req_id}"
            if notif_id not in seen_ids:
                seen_ids.add(notif_id)
                notifications.append({
                    "id": notif_id,
                    "type": "expired",
                    "badge": "Access Expired",
                    "title": f"Access Expired: {patient_name}",
                    "message": f"Authorized consultation window for {patient_name} has concluded.",
                    "patient_name": patient_name,
                    "patient_id": patient_id,
                    "health_id": health_id,
                    "request_id": req_id,
                    "icon": "⌛",
                    "timestamp": expires_at or requested_at or now.isoformat(),
                    "is_read": notif_id in read_set,
                    "link": None
                })

        # 6. Access Request Rejected / Denied
        elif allow_requests and status in ("rejected", "denied"):
            notif_id = f"rejected_{req_id}"
            if notif_id not in seen_ids:
                seen_ids.add(notif_id)
                notifications.append({
                    "id": notif_id,
                    "type": "danger",
                    "badge": "Access Request Rejected",
                    "title": f"Access Request Rejected: {patient_name}",
                    "message": f"{patient_name} declined the access request.",
                    "patient_name": patient_name,
                    "patient_id": patient_id,
                    "health_id": health_id,
                    "request_id": req_id,
                    "icon": "❌",
                    "timestamp": requested_at or now.isoformat(),
                    "is_read": notif_id in read_set,
                    "link": None
                })

    # 7. Check audit trail for Unauthorized Access Attempts
    if allow_system and os.path.exists(AUDIT_LOG_FILE):
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if str(record.get("doctor_id")) != str(doctor_id):
                            continue
                        action = record.get("action")
                        status_val = str(record.get("status") or "").upper()
                        if action in ("UNAUTHORIZED_ACCESS_ATTEMPT", "FAILED_ACCESS_ATTEMPT") or status_val in ("UNAUTHORIZED", "FAILED", "DENIED"):
                            rec_id = record.get("id")
                            notif_id = f"sec_alert_{rec_id}"
                            if notif_id not in seen_ids:
                                seen_ids.add(notif_id)
                                pids = record.get("patient_ids") or []
                                patient_name = "Restricted Patient Record"
                                pid = None
                                hid = ""
                                if pids:
                                    pid = pids[0]
                                    p = patients_map.get(str(pid), {})
                                    patient_name = p.get("full_name") or f"Patient {str(pid)[:8]}"
                                    hid = p.get("health_id") or ""
                                notifications.append({
                                    "id": notif_id,
                                    "type": "danger",
                                    "badge": "Unauthorized Access Attempt",
                                    "title": f"Unauthorized Access Attempt: {patient_name}",
                                    "message": f"Suspicious or unconsented access attempt recorded. Status: {status_val}.",
                                    "patient_name": patient_name,
                                    "patient_id": pid,
                                    "health_id": hid,
                                    "request_id": None,
                                    "icon": "🚨",
                                    "timestamp": record.get("timestamp") or now.isoformat(),
                                    "is_read": notif_id in read_set,
                                    "link": None
                                })
                    except Exception:
                        continue
        except Exception as e:
            print("Error checking audit log for notifications:", repr(e))

    # Sort notifications by timestamp descending
    notifications.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    unread_count = sum(1 for n in notifications if not n.get("is_read"))

    return {
        "notifications": notifications[:limit],
        "unread_count": unread_count,
        "total": len(notifications)
    }


def mark_notification_as_read(doctor_id: str, notification_id: str) -> bool:
    """Mark a notification as read."""
    return _save_read_notification(doctor_id, notification_id)


def mark_all_notifications_as_read(doctor_id: str, notification_ids: Optional[List[str]] = None) -> bool:
    """Mark all listed notifications as read."""
    if not notification_ids:
        # Load all notifications currently available for this doctor
        try:
            # Mark any unread in doctor_notifications_read
            pass
        except Exception:
            pass
    return _save_all_read_notifications(doctor_id, notification_ids or [])
