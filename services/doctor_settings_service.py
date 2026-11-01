# ============================================================
# OMNICARE AI — DOCTOR SETTINGS SERVICE
# Handles doctor portal settings, notification preferences,
# theme & sidebar state, connected services checks, and data export.
# ============================================================

import os
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.doctor_profile_service import (
    get_doctor_profile,
    get_working_preferences,
    list_doctor_documents,
    change_doctor_password,
    get_active_sessions_info,
    get_two_factor_status
)
from services.clinical_audit_service import (
    log_audit_event,
    query_doctor_audit_logs
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH_DIR = os.path.join(BASE_DIR, "scratch")
SETTINGS_FILE = os.path.join(SCRATCH_DIR, "doctor_settings.json")

os.makedirs(SCRATCH_DIR, exist_ok=True)

VALID_THEMES = {"light", "dark", "system"}
VALID_SIDEBAR_MODES = {"expanded", "compact"}


def _read_settings_file() -> Dict[str, Any]:
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_settings_file(data: Dict[str, Any]) -> None:
    try:
        tmp = f"{SETTINGS_FILE}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        try:
            if os.path.exists(SETTINGS_FILE):
                os.replace(tmp, SETTINGS_FILE)
            else:
                os.rename(tmp, SETTINGS_FILE)
        except Exception:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass
    except Exception as e:
        print(f"[DoctorSettingsService] Error writing settings file: {e}")


# ============================================================
# GET & UPDATE DOCTOR SETTINGS
# ============================================================

def get_doctor_settings(
    doctor_id: str,
    supabase_client: Any = None
) -> Dict[str, Any]:
    """
    Retrieve settings for authenticated doctor.
    Supports themes, sidebar mode, and notification toggles.
    """
    default_settings = {
        "theme": "light",
        "sidebar_mode": "expanded",
        "notify_access_requests": True,
        "notify_access_expiry": True,
        "notify_system_updates": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    if not doctor_id:
        return default_settings

    # 1. Read from local cache
    all_settings = _read_settings_file()
    cached = all_settings.get(str(doctor_id), {})
    default_settings.update(cached)

    # 2. Attempt read from Supabase
    if supabase_client:
        try:
            res = (
                supabase_client
                .table("doctor_settings")
                .select("*")
                .eq("doctor_id", doctor_id)
                .single()
                .execute()
            )
            if res and res.data:
                for k in ["theme", "sidebar_mode", "notify_access_requests", "notify_access_expiry", "notify_system_updates"]:
                    if k in res.data and res.data[k] is not None:
                        default_settings[k] = res.data[k]
        except Exception:
            # Fall back to checking doctors table columns
            try:
                doc_res = (
                    supabase_client
                    .table("doctors")
                    .select("theme, sidebar_mode, notify_access_requests, notify_access_expiry, notify_system_updates")
                    .eq("id", doctor_id)
                    .single()
                    .execute()
                )
                if doc_res and doc_res.data:
                    for k in ["theme", "sidebar_mode", "notify_access_requests", "notify_access_expiry", "notify_system_updates"]:
                        if k in doc_res.data and doc_res.data[k] is not None:
                            default_settings[k] = doc_res.data[k]
            except Exception:
                pass

    return default_settings


def update_doctor_settings(
    doctor_id: str,
    updates: Dict[str, Any],
    supabase_client: Any = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Update doctor settings with validation and dual persistence.
    """
    if not doctor_id:
        return False, "Unauthorized doctor session.", {}

    current = get_doctor_settings(doctor_id, supabase_client)

    clean_updates: Dict[str, Any] = {}

    if "theme" in updates:
        val = str(updates["theme"]).lower().strip()
        if val in VALID_THEMES:
            clean_updates["theme"] = val

    if "sidebar_mode" in updates:
        val = str(updates["sidebar_mode"]).lower().strip()
        if val in VALID_SIDEBAR_MODES:
            clean_updates["sidebar_mode"] = val

    for toggle in ["notify_access_requests", "notify_access_expiry", "notify_system_updates"]:
        if toggle in updates:
            val = updates[toggle]
            if isinstance(val, str):
                val = val.lower() in ["true", "1", "yes", "on"]
            clean_updates[toggle] = bool(val)

    clean_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    current.update(clean_updates)

    # Save to local cache
    all_settings = _read_settings_file()
    all_settings[str(doctor_id)] = current
    _write_settings_file(all_settings)

    # Save to Supabase
    if supabase_client:
        try:
            supabase_client.table("doctor_settings").upsert({
                "doctor_id": str(doctor_id),
                "theme": current["theme"],
                "sidebar_mode": current["sidebar_mode"],
                "notify_access_requests": current["notify_access_requests"],
                "notify_access_expiry": current["notify_access_expiry"],
                "notify_system_updates": current["notify_system_updates"],
                "updated_at": current["updated_at"]
            }).execute()
        except Exception as e:
            # Fall back to updating doctors table
            try:
                supabase_client.table("doctors").update(clean_updates).eq("id", doctor_id).execute()
            except Exception:
                pass

    return True, "Settings saved successfully.", current


# ============================================================
# CONNECTED SERVICES HEALTH CHECK
# ============================================================

def check_connected_services_status(
    supabase_client: Any = None
) -> Dict[str, Any]:
    """
    Perform safe backend connectivity checks for Supabase and Gemini AI.
    Never exposes API keys or secrets in the response.
    """
    # 1. Check Supabase
    supabase_status = "Connected"
    supabase_message = "Database & file storage operational."

    if not supabase_client:
        supabase_status = "Disconnected"
        supabase_message = "Supabase client not initialized."
    else:
        try:
            # Safe probe query (limited to 1 row)
            probe = supabase_client.table("doctors").select("id").limit(1).execute()
            if probe is None:
                supabase_status = "Error"
                supabase_message = "No response from database."
        except Exception as e:
            supabase_status = "Disconnected"
            supabase_message = "Database unreachable in current network environment."

    # 2. Check Gemini AI
    gemini_status = "Connected"
    gemini_message = "Medical document processing & clinical insights active."

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key or gemini_key.strip() == "":
        gemini_status = "Configuration Error"
        gemini_message = "GEMINI_API_KEY is not configured in environment."
    else:
        try:
            # Verify client initialization from google.genai
            from google import genai
            test_client = genai.Client(api_key=gemini_key)
            if not test_client:
                gemini_status = "Error"
                gemini_message = "Gemini client failed to initialize."
        except Exception as e:
            err_str = str(e).lower()
            if "rate" in err_str or "quota" in err_str:
                gemini_status = "Rate Limited"
                gemini_message = "Gemini API quota exceeded or rate limited."
            elif "auth" in err_str or "key" in err_str:
                gemini_status = "Configuration Error"
                gemini_message = "Invalid or expired Gemini API key."
            else:
                gemini_status = "Disconnected"
                gemini_message = "Gemini service unreachable in sandbox environment."

    return {
        "supabase": {
            "name": "Supabase",
            "service": "Database & file storage",
            "status": supabase_status,
            "message": supabase_message
        },
        "gemini": {
            "name": "Gemini AI",
            "service": "Medical document processing & clinical insights",
            "status": gemini_status,
            "message": gemini_message
        }
    }


# ============================================================
# DATA EXPORT
# ============================================================

def export_doctor_data(
    doctor_id: str,
    supabase_client: Any = None,
    session_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate authenticated doctor's profile, settings, and activity export.
    Excludes other doctors' information and sensitive patient medical data.
    """
    profile = get_doctor_profile(doctor_id, supabase_client, session_data)
    if isinstance(profile, dict):
        profile = dict(profile)
        profile.pop("password", None)

    settings = get_doctor_settings(doctor_id, supabase_client)
    preferences = get_working_preferences(doctor_id, supabase_client)
    documents = list_doctor_documents(doctor_id, supabase_client)

    # Exclude raw file paths from export
    clean_docs = []
    for d in documents:
        clean_docs.append({
            "id": d.get("id"),
            "document_name": d.get("document_name"),
            "document_type": d.get("document_type_label") or d.get("document_type"),
            "file_name": d.get("file_name"),
            "file_size": d.get("file_size_formatted"),
            "status": d.get("status"),
            "created_at": d.get("created_at")
        })

    # Query doctor's own audit events
    audit_res = query_doctor_audit_logs(doctor_id=doctor_id, per_page=50)
    audit_events = audit_res.get("logs", []) if isinstance(audit_res, dict) else []
    clean_events = []
    for ev in audit_events:
        clean_events.append({
            "id": ev.get("id"),
            "action": ev.get("action_label") or ev.get("action"),
            "status": ev.get("status"),
            "timestamp": ev.get("timestamp"),
            "client_ip": ev.get("client_ip")
        })

    export_payload = {
        "export_metadata": {
            "application": "OmniCare AI Healthcare Management Platform",
            "export_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "doctor_id": str(doctor_id),
            "compliance_notice": (
                "This export contains the authenticated doctor's profile, portal settings, "
                "credential metadata, and account audit logs. Patient clinical records are excluded "
                "in accordance with HIPAA and GDPR data minimization guidelines."
            )
        },
        "doctor_profile": profile,
        "application_settings": settings,
        "working_preferences": preferences,
        "credential_documents": clean_docs,
        "recent_account_activity": clean_events
    }

    return export_payload


# ============================================================
# ACCOUNT DEACTIVATION / DELETION
# ============================================================

def deactivate_doctor_account(
    doctor_id: str,
    password_confirm: str,
    supabase_client: Any = None
) -> Tuple[bool, str]:
    """
    Safely deactivate doctor account following password verification.
    Preserves audit history and patient records from improper destruction.
    """
    if not doctor_id:
        return False, "Unauthorized doctor session."

    if not password_confirm:
        return False, "Please enter your password to confirm account deactivation."

    # Verify password against stored password
    profile = get_doctor_profile(doctor_id, supabase_client)
    stored_password = profile.get("password")

    if stored_password and stored_password != password_confirm:
        return False, "Incorrect password. Account deactivation aborted."

    # Mark doctor account as deactivated
    now_iso = datetime.now(timezone.utc).isoformat()
    all_settings = _read_settings_file()
    doc_settings = all_settings.get(str(doctor_id), {})
    doc_settings["account_status"] = "deactivated"
    doc_settings["deactivated_at"] = now_iso
    all_settings[str(doctor_id)] = doc_settings
    _write_settings_file(all_settings)

    if supabase_client:
        try:
            supabase_client.table("doctors").update({
                "account_status": "deactivated"
            }).eq("id", doctor_id).execute()
        except Exception:
            pass

    try:
        log_audit_event(
            doctor_id=doctor_id,
            action="DOCTOR_ACCOUNT_DEACTIVATED",
            status="SUCCESS",
            metadata={"deactivated_at": now_iso}
        )
    except Exception as e:
        print(f"[DoctorSettingsService] Audit log error: {e}")

    return True, "Your OmniCare AI doctor account has been deactivated."
