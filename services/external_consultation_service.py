# ============================================================
# OMNICARE AI — EXTERNAL CONSULTATION SERVICE
# ============================================================
"""
Manages external consultation sessions, public QR tokens, 5-minute timed sessions,
and patient early revocation.
"""

import json
import os
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List


DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scratch",
    "external_consultation_sessions.json"
)

QR_TOKENS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scratch",
    "patient_qr_tokens.json"
)

SESSION_DURATION_SECONDS = 300  # 5 minutes


def _load_json(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_json(file_path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    tmp = f"{file_path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        try:
            os.replace(tmp, file_path)
        except OSError:
            # On Windows, os.replace can intermittently raise PermissionError (WinError 5)
            # Fall back to direct write
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
    except Exception:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class ExternalConsultationService:
    """Manages universal QR tokens and 5-minute timed external consultation sessions."""

    @classmethod
    def get_or_create_qr_token(cls, patient_id: str, health_id: Optional[str] = None) -> str:
        """
        Get or generate a secure, non-guessable canonical public QR token for a patient.
        Does not expose database UUID.
        Example: OMC-QR-A9F3E8B1C2D4E5F6
        """
        tokens = _load_json(QR_TOKENS_FILE)
        pid = str(patient_id).strip()

        # Check existing
        for token, record in tokens.items():
            if record.get("patient_id") == pid:
                if not record.get("is_revoked", False):
                    return token

        # Generate a new 16-character alphanumeric non-guessable token
        rand_suffix = secrets.token_hex(8).upper()
        token = f"OMC-QR-{rand_suffix}"

        tokens[token] = {
            "token": token,
            "patient_id": pid,
            "health_id": health_id or "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_revoked": False
        }
        _save_json(QR_TOKENS_FILE, tokens)
        return token

    @classmethod
    def resolve_qr_token(cls, token_or_identifier: str) -> Optional[Dict[str, Any]]:
        """
        Resolve a scanned or typed QR identifier to a patient mapping.
        Supports:
        - Canonical token: OMC-QR-...
        - Health ID fallback: OMC-P...
        """
        ident = (token_or_identifier or "").strip()
        if not ident:
            return None

        tokens = _load_json(QR_TOKENS_FILE)

        # 1. Direct match on token
        if ident in tokens:
            rec = tokens[ident]
            if not rec.get("is_revoked", False):
                return rec
            return None

        # 2. Match on health_id
        for token, rec in tokens.items():
            if rec.get("health_id", "").upper() == ident.upper():
                if not rec.get("is_revoked", False):
                    return rec

        return None

    @classmethod
    def revoke_qr_code(cls, patient_id: str) -> bool:
        """Revoke the current QR code so a new one can be generated."""
        tokens = _load_json(QR_TOKENS_FILE)
        pid = str(patient_id).strip()
        updated = False
        for token, rec in tokens.items():
            if rec.get("patient_id") == pid:
                rec["is_revoked"] = True
                rec["revoked_at"] = datetime.now(timezone.utc).isoformat()
                updated = True
        if updated:
            _save_json(QR_TOKENS_FILE, tokens)
        return updated

    @classmethod
    def create_session(
        cls,
        patient_id: str,
        visitor_details: Dict[str, Any],
        is_internal_doctor: bool = False,
        doctor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new 5-minute read-only external consultation session after OTP verification.
        """
        sessions = _load_json(DATA_FILE)
        session_id = f"ext_cs_{secrets.token_urlsafe(16)}"
        session_token = secrets.token_hex(24)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=SESSION_DURATION_SECONDS)

        session_record = {
            "session_id": session_id,
            "session_token": session_token,
            "patient_id": str(patient_id).strip(),
            "is_internal_doctor": bool(is_internal_doctor),
            "doctor_id": str(doctor_id).strip() if doctor_id else None,
            "visitor_name": visitor_details.get("full_name") or visitor_details.get("name") or "External Doctor",
            "visitor_mobile": visitor_details.get("mobile") or "",
            "visitor_role": visitor_details.get("role") or "Doctor",
            "hospital_name": visitor_details.get("hospital_name") or visitor_details.get("hospital") or "Not provided",
            "location": visitor_details.get("location") or "Not provided",
            "email": visitor_details.get("email") or "",
            "qualification": visitor_details.get("qualification") or "",
            "medical_registration_number": visitor_details.get("medical_registration_number") or "",
            "is_verified_registry": False,  # As required by prompt: marked unverified
            "doctor_verification_label": "Unverified External Doctor",
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "expires_at_timestamp": int(expires_at.timestamp()),
            "status": "active",  # active, expired, revoked
            "read_only": True
        }

        sessions[session_id] = session_record
        _save_json(DATA_FILE, sessions)

        return session_record

    @classmethod
    def get_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve and validate session. Returns session dict with updated status."""
        sessions = _load_json(DATA_FILE)
        session = sessions.get(session_id)
        if not session:
            return None

        # Check expiration
        if session.get("status") == "active":
            now_ts = int(datetime.now(timezone.utc).timestamp())
            exp_ts = session.get("expires_at_timestamp", 0)
            if now_ts >= exp_ts:
                session["status"] = "expired"
                sessions[session_id] = session
                _save_json(DATA_FILE, sessions)

        return session

    @classmethod
    def get_active_sessions_for_patient(cls, patient_id: str) -> List[Dict[str, Any]]:
        """List active or recent external consultation sessions for this patient."""
        sessions = _load_json(DATA_FILE)
        pid = str(patient_id).strip()
        results = []
        now_ts = int(datetime.now(timezone.utc).timestamp())

        updated = False
        for sid, s in sessions.items():
            if s.get("patient_id") == pid:
                # auto expire if needed
                if s.get("status") == "active" and now_ts >= s.get("expires_at_timestamp", 0):
                    s["status"] = "expired"
                    updated = True
                
                # Add human readable remaining seconds
                remaining = max(0, s.get("expires_at_timestamp", 0) - now_ts)
                s_copy = dict(s)
                s_copy["remaining_seconds"] = remaining
                results.append(s_copy)

        if updated:
            _save_json(DATA_FILE, sessions)

        # Sort newest first
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results

    @classmethod
    def revoke_session(cls, session_id: str, patient_id: str) -> Tuple[bool, str]:
        """Patient explicitly terminates an external consultation session early."""
        sessions = _load_json(DATA_FILE)
        session = sessions.get(session_id)
        if not session:
            return False, "Consultation session not found."

        if str(session.get("patient_id")) != str(patient_id).strip():
            return False, "Unauthorized: Session belongs to a different patient."

        session["status"] = "revoked"
        session["revoked_at"] = datetime.now(timezone.utc).isoformat()
        sessions[session_id] = session
        _save_json(DATA_FILE, sessions)

        return True, "Consultation access has been revoked immediately."
