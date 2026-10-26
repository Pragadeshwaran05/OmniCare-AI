# ============================================================
# OMNICARE AI — CLINICAL COPILOT SERVICE
# ============================================================

import utils.network_config  # Prioritize IPv4 on Windows to prevent SSL EOF drops
import json
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from services.medical_record_normalizer import (
    parse_strict_date,
    format_iso_date,
    normalize_timeline_event,
)
from services.clinical_rules_engine import (
    evaluate_investigation,
    check_followup_overdue,
)
from services.medical_conflict_detector import detect_medical_conflicts
from services.health_trend_analyzer import get_trend_analysis_data
from services.clinical_audit_service import log_clinical_event


def safe_db_call(builder_fn, max_retries=4, initial_delay=1.0):
    """
    Executes a Supabase query builder with retries for transient socket disconnects.
    """
    last_err = None
    for attempt in range(max_retries):
        try:
            return builder_fn().execute()
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(initial_delay * (1.5 ** attempt))
            else:
                print(f"safe_db_call failed after {max_retries} attempts: {repr(e)}")
                return None


# ------------------------------------------------------------
# SCOPE & CONSENT DETERMINATION
# ------------------------------------------------------------

def get_authorized_patient_scope(
    doctor_id: str,
    supabase_client: Any
) -> Dict[str, Any]:
    """
    Retrieve active, consent-authorized patients for the doctor.
    Automatically identifies and marks expired access grants.
    Returns:
      {
        "authorized_patient_ids": List[str],
        "patient_map": Dict[str, Dict[str, Any]],
        "authorized_patient_count": int,
        "expiring_today": List[Dict[str, Any]],
        "expired_count": int,
        "revoked_count": int,
        "note": str
      }
    """
    if not doctor_id:
        return {
            "authorized_patient_ids": [],
            "patient_map": {},
            "authorized_patient_count": 0,
            "expiring_today": [],
            "expired_count": 0,
            "revoked_count": 0,
            "note": "Doctor authentication required."
        }

    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # 1. Fetch all access requests for this doctor
    req_res = safe_db_call(
        lambda: supabase_client.table("access_requests").select("*").eq("doctor_id", doctor_id)
    )
    all_requests = (req_res.data or []) if req_res else []

    active_patient_ids: Set[str] = set()
    expiring_today: List[Dict[str, Any]] = []
    expired_count = 0
    revoked_count = 0

    for req in all_requests:
        status = str(req.get("status") or "").lower()
        patient_id = req.get("patient_id")
        if not patient_id:
            continue

        if status == "revoked":
            revoked_count += 1
            continue

        if status == "expired":
            expired_count += 1
            continue

        if status == "active":
            expires_at = req.get("expires_at")
            if expires_at:
                try:
                    exp_dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                    if now_utc >= exp_dt:
                        # Mark as expired
                        expired_count += 1
                        try:
                            supabase_client.table("access_requests").update({"status": "expired"}).eq("id", req["id"]).execute()
                        except Exception:
                            pass
                        continue
                    elif exp_dt < today_end:
                        # Expiring today
                        expiring_today.append(req)
                except Exception:
                    pass

            active_patient_ids.add(patient_id)

    # 2. Fetch demographic information for authorized patients only
    patient_map: Dict[str, Dict[str, Any]] = {}
    if active_patient_ids:
        pts_res = safe_db_call(
            lambda: supabase_client
            .table("patients")
            .select("id, full_name, health_id, date_of_birth, gender, blood_group")
            .in_("id", list(active_patient_ids))
        )
        for p in ((pts_res.data or []) if pts_res else []):
            patient_map[p["id"]] = p

    # Format expiring today items
    formatted_expiring: List[Dict[str, Any]] = []
    for req in expiring_today:
        pid = req.get("patient_id")
        p_name = patient_map.get(pid, {}).get("full_name") or "Authorized Patient"
        formatted_expiring.append({
            "patient_id": pid,
            "patient_name": p_name,
            "expires_at": req.get("expires_at"),
            "access_type": req.get("access_type") or "temporary",
            "workspace_url": f"/doctor/patient-workspace/{pid}"
        })

    return {
        "authorized_patient_ids": list(active_patient_ids),
        "patient_map": patient_map,
        "authorized_patient_count": len(active_patient_ids),
        "expiring_today": formatted_expiring,
        "expired_count": expired_count,
        "revoked_count": revoked_count,
        "note": "Only patients with active, unexpired consent are included in clinical analysis."
    }


# ------------------------------------------------------------
# CLINICAL BRIEFING GENERATION
# ------------------------------------------------------------

def get_clinical_briefing(
    doctor_id: str,
    supabase_client: Any
) -> Dict[str, Any]:
    """
    Generate practice-level Clinical Briefing across all authorized patients.
    Returns:
      {
        "abnormal_reports": [...],
        "overdue_followups": [...],
        "access_expiring_today": [...],
        "worsening_trends": [...],
        "trend_summary": {"worsening": X, "improving": Y, "stable": Z},
        "scope": {...},
        "priority_patients": [...],
        "medication_safety": {...},
        "refreshed_at": ISO timestamp
      }
    """
    scope = get_authorized_patient_scope(doctor_id, supabase_client)
    authorized_pids = scope["authorized_patient_ids"]
    patient_map = scope["patient_map"]

    refreshed_at = datetime.now(timezone.utc).isoformat()

    if not authorized_pids:
        log_clinical_event(doctor_id, "COPILOT_BRIEFING_VIEWED", [], "SUCCESS", {"message": "Empty scope"})
        return {
            "abnormal_reports": [],
            "overdue_followups": [],
            "access_expiring_today": [],
            "worsening_trends": [],
            "trend_summary": {"worsening": 0, "improving": 0, "stable": 0},
            "scope": {
                "authorized_patient_count": 0,
                "expired_count": scope["expired_count"],
                "revoked_count": scope["revoked_count"],
                "note": "No patients currently have active consent for your account."
            },
            "priority_patients": [],
            "medication_safety": {
                "total_conflicts": 0,
                "conflicts": [],
                "note": "No active patients to review."
            },
            "refreshed_at": refreshed_at
        }

    # Fetch health_timeline_events for authorized patients
    events_res = safe_db_call(
        lambda: supabase_client
        .table("health_timeline_events")
        .select("*")
        .in_("patient_id", authorized_pids)
        .order("event_date", desc=True)
    )
    raw_events = (events_res.data or []) if events_res else []

    # Fetch medical_records metadata for authorized patients
    records_res = safe_db_call(
        lambda: supabase_client
        .table("medical_records")
        .select("id, patient_id, title, record_type, uploaded_at, file_url")
        .in_("patient_id", authorized_pids)
    )
    raw_records = (records_res.data or []) if records_res else []

    # Group records and timeline events by patient
    patient_events: Dict[str, List[Dict[str, Any]]] = {pid: [] for pid in authorized_pids}
    patient_records: Dict[str, List[Dict[str, Any]]] = {pid: [] for pid in authorized_pids}

    for ev in raw_events:
        pid = ev.get("patient_id")
        if pid in patient_events:
            patient_events[pid].append(ev)

    for rec in raw_records:
        pid = rec.get("patient_id")
        if pid in patient_records:
            patient_records[pid].append(rec)

    abnormal_reports: List[Dict[str, Any]] = []
    overdue_followups: List[Dict[str, Any]] = []
    all_conflicts: List[Dict[str, Any]] = []
    worsening_trends: List[Dict[str, Any]] = []
    total_improving = 0
    total_stable = 0

    now_utc = datetime.now(timezone.utc)

    # Process each patient's data
    for pid in authorized_pids:
        p_name = patient_map.get(pid, {}).get("full_name") or f"Patient {pid[:8]}"
        events = patient_events[pid]
        records = patient_records[pid]

        # 1. Abnormal Reports & Overdue Follow-ups
        for raw_ev in events:
            norm_ev = normalize_timeline_event(raw_ev)
            ev_date = norm_ev["event_date"] or "Unknown date"
            med_rec_id = norm_ev["medical_record_id"] or norm_ev["id"]

            # Evaluate each investigation
            for inv in norm_ev["investigations"]:
                eval_res = evaluate_investigation(
                    inv["name"],
                    inv["raw_result"],
                    inv["unit"]
                )
                if eval_res["is_abnormal"]:
                    abnormal_reports.append({
                        "patient_id": pid,
                        "patient_name": p_name,
                        "test_name": eval_res["test_name"],
                        "value": eval_res["value"],
                        "numeric_value": eval_res["numeric_value"],
                        "unit": eval_res["unit"],
                        "status": eval_res["status"],
                        "severity": eval_res["severity"],
                        "explanation": eval_res["explanation"],
                        "date": ev_date,
                        "medical_record_id": med_rec_id,
                        "workspace_url": f"/doctor/patient-workspace/{pid}"
                    })

            # Check overdue follow-up
            if norm_ev["follow_up_datetime"]:
                f_check = check_followup_overdue(norm_ev["follow_up_datetime"], now_utc)
                if f_check and f_check["is_overdue"]:
                    overdue_followups.append({
                        "patient_id": pid,
                        "patient_name": p_name,
                        "days_overdue": f_check["days_overdue"],
                        "due_date": f_check["due_date"],
                        "date": ev_date,
                        "raw_follow_up": norm_ev["raw_follow_up"],
                        "severity": f_check["severity"],
                        "medical_record_id": med_rec_id,
                        "workspace_url": f"/doctor/patient-workspace/{pid}"
                    })

        # 2. Medication Conflicts
        try:
            conflicts = detect_medical_conflicts(events)
            for c in conflicts:
                all_conflicts.append({
                    "patient_id": pid,
                    "patient_name": p_name,
                    "type": c.get("type", "conflict"),
                    "title": c.get("title") or c.get("medicine", "Medication Concern"),
                    "severity": c.get("severity", "medium"),
                    "description": c.get("message") or c.get("description", ""),
                    "workspace_url": f"/doctor/patient-workspace/{pid}"
                })
        except Exception as e:
            print(f"Error checking conflicts for patient {pid}:", repr(e))

        # 3. Trends across parameters
        try:
            trend_data = get_trend_analysis_data(
                timeline_events=events,
                medical_records=records,
                patient_name=p_name,
                skip_ai=True
            )
            for sm in trend_data.get("summaries", []):
                d_level = str(sm.get("danger_level") or "").lower()
                d_label = str(sm.get("danger_label") or "").lower()
                ch_dir = str(sm.get("change_direction") or "").lower()

                # Flag elevated/critical levels or parameters worsening upward
                is_worsening = d_level in ["red", "critical"] or (d_level == "amber" and ch_dir in ["up", "increase"])

                if is_worsening:
                    worsening_trends.append({
                        "patient_id": pid,
                        "patient_name": p_name,
                        "param_name": sm.get("param_name"),
                        "latest_value": sm.get("latest_value"),
                        "unit": sm.get("unit"),
                        "change_text": sm.get("change_text") or sm.get("danger_label"),
                        "danger_reason": sm.get("danger_reason"),
                        "date": sm.get("latest_date"),
                        "workspace_url": f"/doctor/patient-workspace/{pid}"
                    })
                elif ch_dir in ["down", "decrease"] and d_level == "green":
                    total_improving += 1
                else:
                    total_stable += 1
        except Exception as e:
            print(f"Error analyzing trends for patient {pid}:", repr(e))

    # Sort priorities
    abnormal_reports.sort(
        key=lambda x: (0 if x["severity"] == "high" else 1, x.get("date") or ""),
        reverse=False
    )
    overdue_followups.sort(
        key=lambda x: x.get("days_overdue", 0),
        reverse=True
    )

    trend_summary = {
        "worsening": len(worsening_trends),
        "improving": total_improving,
        "stable": total_stable
    }

    # Log audit trail
    log_clinical_event(
        doctor_id=doctor_id,
        action="COPILOT_BRIEFING_VIEWED",
        patient_ids=authorized_pids,
        status="SUCCESS",
        metadata={
            "abnormal_count": len(abnormal_reports),
            "followup_count": len(overdue_followups),
            "conflict_count": len(all_conflicts),
            "worsening_count": len(worsening_trends)
        }
    )

    return {
        "abnormal_reports": abnormal_reports,
        "overdue_followups": overdue_followups,
        "access_expiring_today": scope["expiring_today"],
        "worsening_trends": worsening_trends,
        "trend_summary": trend_summary,
        "scope": {
            "authorized_patient_count": scope["authorized_patient_count"],
            "expired_count": scope["expired_count"],
            "revoked_count": scope["revoked_count"],
            "note": scope["note"]
        },
        "medication_safety": {
            "total_conflicts": len(all_conflicts),
            "conflicts": all_conflicts,
            "note": "Requires clinician correlation. Interaction checking is limited to documented medications and allergies."
        },
        "refreshed_at": refreshed_at
    }


# ------------------------------------------------------------
# ALERT REVIEW LEDGER
# ------------------------------------------------------------

ALERT_REVIEWS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scratch",
    "alert_reviews.json"
)

def record_alert_review(
    doctor_id: str,
    alert_id: str,
    alert_type: str,
    patient_id: str,
    review_notes: str = ""
) -> Dict[str, Any]:
    """
    Mark a clinical alert as reviewed by the authorized doctor.
    """
    review_record = {
        "doctor_id": doctor_id,
        "alert_id": alert_id,
        "alert_type": alert_type,
        "patient_id": patient_id,
        "review_notes": review_notes,
        "reviewed_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        os.makedirs(os.path.dirname(ALERT_REVIEWS_FILE), exist_ok=True)
        reviews = []
        if os.path.exists(ALERT_REVIEWS_FILE):
            with open(ALERT_REVIEWS_FILE, "r", encoding="utf-8") as f:
                reviews = json.load(f)
        reviews.append(review_record)
        with open(ALERT_REVIEWS_FILE, "w", encoding="utf-8") as f:
            json.dump(reviews, f, indent=2)
    except Exception as e:
        print("Error saving alert review:", repr(e))

    log_clinical_event(
        doctor_id=doctor_id,
        action="ALERT_REVIEWED",
        patient_ids=[patient_id] if patient_id else [],
        status="SUCCESS",
        metadata={
            "alert_id": alert_id,
            "alert_type": alert_type,
            "notes": review_notes
        }
    )

    return review_record
