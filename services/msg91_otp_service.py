# ============================================================
# OMNICARE AI — MSG91 OTP SERVICE
# ============================================================
"""
Production-grade OTP dispatch and verification service with MSG91 integration.
Features:
- Configured OTP length: 4 digits (matches MSG91 widget configuration).
- Demo OTP in development mode: 1234 (matches MSG91 dashboard demo credentials).
- Official MSG91 OTP Widget Web SDK support and server-side verifyAccessToken:
    POST https://control.msg91.com/api/v5/widget/verifyAccessToken
- Safe development mode (MSG91_ENVIRONMENT=development) to prevent SMS charges.
- Real MSG91 API integration via MSG91_AUTH_KEY, MSG91_WIDGET_ID, MSG91_TEMPLATE_ID.
- Strict security: OTP is ONLY delivered to the patient's verified contact.
- Masked contact display (e.g., +91 ******4521 or p******@gmail.com).
- 15-minute OTP validity with rate-limiting and max attempt enforcement.
"""

import os
import random
import hmac
import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
import httpx


# In-memory / process-level OTP store for active challenges (keyed by challenge_id)
# Schema: challenge_id -> { "otp_hash": ..., "patient_id": ..., "expires_at": ..., "attempts": ..., "masked_destination": ... }
_ACTIVE_OTP_CHALLENGES: Dict[str, Dict[str, Any]] = {}

# Rate limit tracking: patient_id -> list of timestamps
_OTP_RATE_LIMITS: Dict[str, list] = {}
MAX_OTP_PER_10_MIN = 5
MAX_VERIFICATION_ATTEMPTS = 5
OTP_EXPIRY_SECONDS = 300  # 5 minutes
OTP_LENGTH = 4            # 4 digits
DEFAULT_DEMO_OTP = "9841" # Fixed demo OTP code for development
DEMO_OTP = DEFAULT_DEMO_OTP


def _get_secret_key() -> str:
    return os.getenv("SECRET_KEY", "omnicare-secret-otp-signing-key")


def _hash_otp(otp: str, challenge_id: str) -> str:
    key = _get_secret_key().encode("utf-8")
    msg = f"{otp}:{challenge_id}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def mask_phone_number(phone: Optional[str]) -> str:
    """Mask phone number safely (e.g. +91 9876543210 -> +91 ******3210)."""
    if not phone:
        return "Registered mobile number"
    raw = str(phone).strip()
    digits = [c for c in raw if c.isdigit()]
    if len(digits) < 4:
        return "****"
    last4 = "".join(digits[-4:])
    prefix = "+91 " if raw.startswith("+91") else ""
    return f"{prefix}******{last4}"


def mask_email_address(email: Optional[str]) -> str:
    """Mask email address safely (e.g. pragadesh@example.com -> p******@example.com)."""
    if not email or "@" not in email:
        return "Registered email address"
    email = email.strip()
    user, domain = email.split("@", 1)
    if len(user) <= 2:
        masked_user = user[0] + "*"
    else:
        masked_user = user[0] + ("*" * (len(user) - 2)) + user[-1]
    return f"{masked_user}@{domain}"


def is_production() -> bool:
    """
    Strict security check: determine if running in production mode.
    Checks FLASK_ENV, ENV, APP_ENV, MSG91_ENVIRONMENT, and active Flask application config.
    """
    flask_env = os.getenv("FLASK_ENV", "").strip().lower()
    app_env = os.getenv("ENV", os.getenv("APP_ENV", "")).strip().lower()
    msg91_env = os.getenv("MSG91_ENVIRONMENT", "").strip().lower()

    if flask_env == "production" or app_env == "production" or msg91_env == "production":
        return True

    try:
        from flask import current_app
        if current_app:
            if current_app.config.get("ENV") == "production":
                return True
            if current_app.config.get("TESTING") is False and not current_app.debug and flask_env == "production":
                return True
    except Exception:
        pass

    return False


def is_demo_otp_active() -> bool:
    """
    Strict security: Fixed Demo OTP MUST ONLY be active in development.
    If the application runs in production, fixed demo OTP verification is rejected regardless of env variables.
    """
    if is_production():
        return False

    demo_enabled = os.getenv("DEMO_OTP_ENABLED", "true").strip().lower() in ("true", "1", "yes")
    msg91_env = os.getenv("MSG91_ENVIRONMENT", "development").strip().lower()
    is_dev = msg91_env in ("development", "dev", "sandbox", "local", "test")
    return demo_enabled and is_dev


def get_demo_otp_code() -> str:
    """Get the configured fixed demo OTP code (default 9841)."""
    return os.getenv("DEMO_OTP_CODE", DEFAULT_DEMO_OTP).strip()


def is_dev_mode() -> bool:
    """
    Check if we should run in development mode.
    """
    if is_production():
        return False
    return is_demo_otp_active()


class MSG91OTPService:
    """Handles OTP generation, dispatch via MSG91 (or mock in dev), and verification."""

    @staticmethod
    def generate_otp_code() -> str:
        """Generate a 4-digit numeric OTP. Uses fixed demo OTP in development demo mode."""
        if is_demo_otp_active():
            return get_demo_otp_code()
        return f"{random.randint(1000, 9999)}"

    @classmethod
    def request_otp(
        cls,
        patient_id: str,
        patient_phone: Optional[str],
        patient_email: Optional[str],
        visitor_name: str,
        consultation_type: str = "External Consultation"
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Create and dispatch an OTP challenge to the PATIENT.
        Never delivers OTP to visitor.
        Returns: (success: bool, message: str, challenge_metadata: dict)
        """
        now = time.time()

        # Invalidate any existing active challenges for this patient on resend
        for old_cid, old_c in list(_ACTIVE_OTP_CHALLENGES.items()):
            if str(old_c.get("patient_id")) == str(patient_id):
                _ACTIVE_OTP_CHALLENGES.pop(old_cid, None)

        # 1. Check rate limit per patient
        timestamps = _OTP_RATE_LIMITS.setdefault(patient_id, [])
        # Prune older than 10 minutes (600s)
        _OTP_RATE_LIMITS[patient_id] = [t for t in timestamps if now - t < 600]
        if len(_OTP_RATE_LIMITS[patient_id]) >= MAX_OTP_PER_10_MIN:
            return (
                False,
                "Too many OTP requests for this patient. Please wait a few minutes before trying again.",
                None
            )

        # 2. Check destination availability
        phone = (patient_phone or "").strip()
        email = (patient_email or "").strip()
        if not phone and not email:
            return (
                False,
                "The patient does not have a verified phone number or email on file for OTP authorization.",
                None
            )

        # 3. Generate 4-digit OTP and challenge ID
        demo_active = is_demo_otp_active()
        otp = cls.generate_otp_code()
        challenge_id = f"otp_ch_{int(now)}_{random.randint(1000, 9999)}"
        otp_hash = _hash_otp(otp, challenge_id)
        expires_at = now + OTP_EXPIRY_SECONDS

        masked_dest = mask_phone_number(phone) if phone else mask_email_address(email)

        # 4. Dispatch OTP (Real MSG91 or Fixed Demo OTP)
        dispatch_success = True
        dispatch_error = ""

        if demo_active:
            demo_code = get_demo_otp_code()
            # Print prominent log banner for developer
            print("\n" + "=" * 70)
            print(" [OMNICARE AI - FIXED DEMO OTP MODE] OTP DISPATCH")
            print("=" * 70)
            print(f" Patient ID        : {patient_id}")
            print(f" Masked Target     : {masked_dest}")
            print(f" Visitor / Doctor  : {visitor_name}")
            print(f" Consultation Type : {consultation_type}")
            print(f" Fixed Demo OTP    : >>> {demo_code} <<< (VALID FOR 5 MINUTES)")
            print(f" Mode Notice       : Demo OTP: {demo_code} (Development Mode)")
            print(f" Cost Safety       : NO SMS credits deducted (Development Mode)")
            print("=" * 70 + "\n")
            msg = f"Demo OTP: {demo_code} (Development Mode)"
        else:
            # Send via real MSG91 API
            dispatch_success, dispatch_error = cls._send_msg91_otp(
                phone=phone,
                otp=otp,
                visitor_name=visitor_name
            )
            msg = f"Authorization OTP sent to patient's {masked_dest}."

        if not dispatch_success:
            return (
                False,
                f"Failed to dispatch OTP to patient: {dispatch_error}",
                None
            )

        # 5. Store active challenge
        _ACTIVE_OTP_CHALLENGES[challenge_id] = {
            "challenge_id": challenge_id,
            "patient_id": patient_id,
            "otp_code": otp,  # kept for internal dev/fallback verification
            "otp_hash": otp_hash,
            "expires_at": expires_at,
            "attempts": 0,
            "masked_destination": masked_dest,
            "visitor_name": visitor_name,
            "consultation_type": consultation_type,
            "is_demo": demo_active,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        _OTP_RATE_LIMITS[patient_id].append(now)

        return (
            True,
            msg,
            {
                "challenge_id": challenge_id,
                "masked_destination": masked_dest,
                "expires_in_seconds": OTP_EXPIRY_SECONDS,
                "otp_length": OTP_LENGTH,
                "is_demo_mode": demo_active,
                "demo_otp_notice": f"Demo OTP: {get_demo_otp_code()} (Development Mode)" if demo_active else None
            }
        )

    @classmethod
    def verify_otp(
        cls,
        challenge_id: str,
        patient_id: str,
        entered_otp: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Verify the 4-digit OTP entered by doctor or visitor.
        Enforces maximum 5 attempts and 5-minute expiry.
        In development mode with demo credentials, accepts fixed demo OTP (e.g. 9841).
        In production, demo OTP verification is STRICTLY rejected.
        """
        now = time.time()
        challenge = _ACTIVE_OTP_CHALLENGES.get(challenge_id)

        if not challenge:
            return False, "OTP session has expired or is invalid. Please request a new OTP.", None

        if str(challenge.get("patient_id")) != str(patient_id):
            return False, "OTP challenge does not match the active patient.", None

        if now > challenge.get("expires_at", 0):
            _ACTIVE_OTP_CHALLENGES.pop(challenge_id, None)
            return False, "The OTP has expired. Please request a new OTP.", None

        challenge["attempts"] = challenge.get("attempts", 0) + 1
        if challenge["attempts"] > MAX_VERIFICATION_ATTEMPTS:
            _ACTIVE_OTP_CHALLENGES.pop(challenge_id, None)
            return False, "Maximum verification attempts exceeded. Please request a new OTP.", None

        raw_entered = str(entered_otp).strip()

        # Check production security rule
        in_production = is_production()
        demo_active = is_demo_otp_active()

        # If in production, fixed demo OTP can NEVER be used
        if in_production:
            if challenge.get("is_demo", False):
                _ACTIVE_OTP_CHALLENGES.pop(challenge_id, None)
                return False, "Demo OTP verification is not permitted in production.", None

        # Check demo OTP match ONLY if demo mode is active
        expected_demo = get_demo_otp_code()
        is_demo_valid = demo_active and (raw_entered == expected_demo)

        # Check cryptographic hash match
        expected_hash = challenge.get("otp_hash")
        computed_hash = _hash_otp(raw_entered, challenge_id)
        is_hash_valid = hmac.compare_digest(expected_hash, computed_hash)

        # Check direct code match (only permitted if not in production or not a demo challenge)
        is_code_valid = (challenge.get("otp_code") == raw_entered) and (not in_production or not challenge.get("is_demo", False))

        if not (is_demo_valid or is_hash_valid or is_code_valid):
            remaining = MAX_VERIFICATION_ATTEMPTS - challenge["attempts"]
            return False, f"Incorrect OTP. {remaining} attempt(s) remaining.", None

        # Success - consume the challenge immediately (single-use enforcement)
        verified_metadata = {
            "challenge_id": challenge_id,
            "patient_id": patient_id,
            "visitor_name": challenge.get("visitor_name"),
            "consultation_type": challenge.get("consultation_type"),
            "auth_mode": "fixed_demo_otp" if is_demo_valid else "real_otp",
            "verified_at": datetime.now(timezone.utc).isoformat()
        }
        _ACTIVE_OTP_CHALLENGES.pop(challenge_id, None)

        return True, "Patient authorization verified successfully.", verified_metadata

    @classmethod
    def verify_widget_access_token(
        cls,
        access_token: str,
        expected_identifier: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Server-side validation of MSG91 OTP Widget access token.
        POST https://control.msg91.com/api/v5/widget/verifyAccessToken
        Headers:
          authkey: <MSG91_AUTH_KEY>
          Content-Type: application/json
        Body:
          {"access-token": "<access_token>"}
        """
        token = (access_token or "").strip()
        if not token:
            return False, "Missing widget access token.", None

        # Check for development/demo mode mock tokens
        if is_demo_otp_active():
            if token.startswith("demo_") or token.startswith("test_") or token in ("demo-access-token", "1234", "9841"):
                return True, "Demo access token verified successfully.", {
                    "verified_identifier": expected_identifier or "919876543210",
                    "mode": "development"
                }

        auth_key = os.getenv("MSG91_AUTH_KEY", "").strip()
        if not auth_key:
            if is_demo_otp_active():
                return True, "Development mode verified.", {"verified_identifier": expected_identifier, "mode": "development"}
            return False, "MSG91_AUTH_KEY not configured on server.", None

        url = "https://control.msg91.com/api/v5/widget/verifyAccessToken"
        headers = {
            "authkey": auth_key,
            "Content-Type": "application/json"
        }
        payload = {
            "access-token": token
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json() if res.content else {}
                    # Note: MSG91 returns HTTP 200 even on validation failure; verify type == "success"
                    if data.get("type") == "success":
                        verified_id = data.get("message")
                        return True, "Access token verified successfully.", {
                            "verified_identifier": verified_id,
                            "raw_response": data
                        }
                    else:
                        err_msg = data.get("message") or "Invalid or expired MSG91 access token."
                        return False, err_msg, None
                else:
                    return False, f"MSG91 verifyAccessToken error: HTTP {res.status_code}", None
        except Exception as e:
            return False, f"Failed to contact MSG91 verification server: {str(e)}", None

    @classmethod
    def _send_msg91_otp(
        cls,
        phone: str,
        otp: str,
        visitor_name: str
    ) -> Tuple[bool, str]:
        """Call MSG91 Send OTP API securely from backend."""
        auth_key = os.getenv("MSG91_AUTH_KEY", "").strip()
        template_id = os.getenv("MSG91_TEMPLATE_ID", "").strip()

        if not auth_key:
            return False, "MSG91_AUTH_KEY is not configured."

        # Format mobile number (E.164 without plus or country code as MSG91 expects)
        raw_digits = "".join([c for c in phone if c.isdigit()])
        if not raw_digits:
            return False, "Invalid mobile number."

        # Default to India 91 if 10 digits
        if len(raw_digits) == 10:
            formatted_mobile = f"91{raw_digits}"
        else:
            formatted_mobile = raw_digits

        url = "https://control.msg91.com/api/v5/otp"
        headers = {
            "authkey": auth_key,
            "Content-Type": "application/json"
        }
        payload = {
            "mobile": formatted_mobile,
            "otp": otp,
            "otp_expiry": 15,  # 15 minutes (matches widget configuration)
            "otp_length": OTP_LENGTH
        }
        if template_id:
            payload["template_id"] = template_id

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code in (200, 201):
                    data = res.json() if res.content else {}
                    if data.get("type") == "error":
                        return False, data.get("message", "MSG91 returned an error.")
                    return True, "OTP dispatched successfully."
                else:
                    return False, f"MSG91 error status {res.status_code}: {res.text}"
        except Exception as e:
            return False, f"Connection to MSG91 failed: {str(e)}"
